"""Review orchestration for the console.

The console never re-implements the review agent: it imports ``agent_layer``
from ``skills/modeling`` and persists the produced ``review_report.json`` /
``revision_plan.json`` under ``<runtime>/agent_reports/<run_id>`` — the same
location the CLI writes to. Reports stay on disk, so a completed review survives
a server restart and can be re-read without re-running anything.
"""
from __future__ import annotations

import json
import queue
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend import forge_service

REVIEW_DIRNAME = "agent_reports"
STATUS_FILE = "status.json"
REPORT_FILE = "review_report.json"
PLAN_FILE = "revision_plan.json"
TRACE_FILE = "agent_trace.jsonl"


class ReviewError(Exception):
    """Raised when a review cannot be triggered or read."""

    def __init__(self, message: str, status: int = 400) -> None:
        self.status = status
        super().__init__(message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_dir(project: str, run_id: str) -> Path:
    try:
        return forge_service._run_dir(project, run_id)  # noqa: SLF001 - same package, single path check
    except forge_service.LookupError as exc:
        raise ReviewError(str(exc), 404) from exc


def reports_dir(project: str, run_id: str) -> Path:
    """<runtime>/agent_reports/<run_id>, identical to the CLI default."""
    run_dir = _run_dir(project, run_id)
    return run_dir.parents[1] / REVIEW_DIRNAME / run_dir.name


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewError(f"cannot read {path.name}: {exc}", 500) from exc
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _status(directory: Path) -> dict[str, Any] | None:
    return _read_json(directory / STATUS_FILE)


def _set_status(directory: Path, **fields: Any) -> dict[str, Any]:
    current = _status(directory) or {}
    current.update({key: value for key, value in fields.items() if value is not None})
    current["updated_at"] = _now()
    _write_json(directory / STATUS_FILE, current)
    return current


# ---- worker ---------------------------------------------------------------
_LOCK = threading.Lock()
_QUEUE: "queue.Queue[tuple[str, str, str]]" = queue.Queue()
_WORKER: threading.Thread | None = None
_INDEX: Any = None


def _knowledge_index() -> Any:
    """Build the BM25 index once per process; reviews share it."""
    global _INDEX
    if _INDEX is None:
        from agent_layer.cli import MODELING_ROOT, TEMPLATE_ROOT  # noqa: PLC0415
        from agent_layer.retrieval import build_index  # noqa: PLC0415

        _INDEX = build_index(MODELING_ROOT, extra_dirs=[TEMPLATE_ROOT])
    return _INDEX


def _ensure_worker() -> None:
    global _WORKER
    with _LOCK:
        if _WORKER is None or not _WORKER.is_alive():
            _WORKER = threading.Thread(target=_consume, name="forge-review-worker", daemon=True)
            _WORKER.start()


def _consume() -> None:
    while True:
        project, run_id, job_id = _QUEUE.get()
        try:
            _execute(project, run_id, job_id)
        except Exception:  # noqa: BLE001 - the failure is recorded in status.json
            pass
        finally:
            _QUEUE.task_done()


def _execute(project: str, run_id: str, job_id: str) -> None:
    directory = reports_dir(project, run_id)
    _set_status(directory, status="running", job_id=job_id, started_at=_now(), error=None)
    try:
        from agent_layer.pipeline import RevisionPipeline, write_plan  # noqa: PLC0415
        from agent_layer.reviewer import write_report  # noqa: PLC0415

        result = RevisionPipeline(_run_dir(project, run_id), index=_knowledge_index()).run()
        review, plan = result["review"], result["plan"]
        write_report(review, directory)
        write_plan(plan, directory)
        _set_status(
            directory,
            status="completed",
            finished_at=_now(),
            planner="rule",
            steps=(review.get("summary") or {}).get("steps"),
            issues=len(review.get("issues") or []),
            patches=len(plan.get("patches") or []),
            verdict=(plan.get("verification") or {}).get("verdict"),
            trace_sha256=review.get("trace_sha256"),
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI verbatim
        _set_status(
            directory,
            status="failed",
            finished_at=_now(),
            error=f"{type(exc).__name__}: {exc}",
        )


# ---- public API -----------------------------------------------------------
def trigger(project: str, run_id: str) -> dict[str, Any]:
    directory = reports_dir(project, run_id)
    current = _status(directory) or {}
    if current.get("status") == "running":
        raise ReviewError("review already running for this run", 409)
    job_id = uuid.uuid4().hex[:12]
    payload = _set_status(
        directory,
        job_id=job_id,
        project=project,
        run_id=run_id,
        status="queued",
        planner="rule",
        created_at=_now(),
        started_at=None,
        finished_at=None,
        error=None,
    )
    _ensure_worker()
    _QUEUE.put((project, run_id, job_id))
    return payload


def read(project: str, run_id: str) -> dict[str, Any]:
    directory = reports_dir(project, run_id)
    status = _status(directory) or {"status": "none", "run_id": run_id}
    return {
        "status": status,
        "review": _read_json(directory / REPORT_FILE),
        "plan": _read_json(directory / PLAN_FILE),
    }


def trace(project: str, run_id: str) -> dict[str, Any]:
    directory = reports_dir(project, run_id)
    report = _read_json(directory / REPORT_FILE) or {}
    rows = report.get("tool_trace") or []
    if not rows and (directory / TRACE_FILE).is_file():
        rows = [
            json.loads(line)
            for line in (directory / TRACE_FILE).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if not rows:
        raise ReviewError("no trace available; run a review first", 404)
    return {
        "run_id": run_id,
        "steps": len(rows),
        "trace_sha256": report.get("trace_sha256"),
        "trace": rows,
    }
