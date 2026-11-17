"""Read-only service layer over Forge workflow runs.

The console never re-implements the engine: it imports ProductionWorkflow from
``skills/modeling`` to start runs, and reads the on-disk run contract
(``manifest.json`` + ``gates/*.json`` + ``artifacts/``) for everything else.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[3]
MODELING = WORKSPACE / "skills" / "modeling"
PROJECTS = WORKSPACE / "projects"

if str(MODELING) not in sys.path:
    sys.path.insert(0, str(MODELING))

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
STREAM_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

FRESHNESS_PREFIX = "freshness_"
INFRA_GATES = {"code_integrity", "run_integrity"}


class LookupError(ValueError):
    """Raised when a requested project, run, stage, or artifact does not exist."""


def _valid_name(value: str, what: str) -> str:
    if not NAME_RE.fullmatch(value or ""):
        raise LookupError(f"invalid {what}: {value!r}")
    return value


def list_projects() -> list[dict[str, Any]]:
    """Every project directory that declares a workflow.json."""
    items: list[dict[str, Any]] = []
    for config in sorted(PROJECTS.glob("*/workflow.json")):
        entry: dict[str, Any] = {"name": config.parent.name, "config": str(config)}
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            entry.update(
                workflow_id=data.get("workflow_id"),
                stage_count=len(data.get("stages") or []),
                schema=data.get("schema"),
            )
        except (OSError, json.JSONDecodeError) as exc:
            entry["error"] = str(exc)
        items.append(entry)
    return items


def _project_config(project: str) -> Path:
    _valid_name(project, "project")
    config = PROJECTS / project / "workflow.json"
    if not config.is_file():
        raise LookupError(f"unknown project: {project}")
    return config


def _runtime_root(project: str) -> Path:
    config = _project_config(project)
    data = json.loads(config.read_text(encoding="utf-8"))
    setting = Path(data.get("runtime_root") or "runtime/runs")
    return setting.resolve() if setting.is_absolute() else (config.parent / setting).resolve()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LookupError(f"cannot read {path.name}: {exc}") from exc


def _run_dir(project: str, run_id: str) -> Path:
    _valid_name(run_id, "run_id")
    candidate = _runtime_root(project) / run_id
    if not candidate.is_dir() or not (candidate / "manifest.json").is_file():
        raise LookupError(f"unknown run: {run_id}")
    return candidate


def list_runs(project: str) -> list[dict[str, Any]]:
    """Run summaries newest first, derived from each manifest."""
    root = _runtime_root(project)
    if not root.is_dir():
        return []
    runs: list[dict[str, Any]] = []
    for run_dir in root.iterdir():
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        stages = manifest.get("stages") or []
        gates = _gate_summary(run_dir)
        runs.append(
            {
                "run_id": manifest.get("run_id") or run_dir.name,
                "status": manifest.get("status"),
                "workflow_id": manifest.get("workflow_id"),
                "start_time": manifest.get("start_time"),
                "end_time": manifest.get("end_time"),
                "stages_total": len(stages),
                "stages_pass": sum(1 for s in stages if s.get("status") == "PASS"),
                "gates_total": gates["total"],
                "gates_pass": gates["pass"],
            }
        )
    runs.sort(key=lambda item: item.get("start_time") or "", reverse=True)
    return runs


def _gate_reports(run_dir: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    gates_dir = run_dir / "gates"
    if not gates_dir.is_dir():
        return reports
    for path in sorted(gates_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {"gate": path.stem, "status": "UNREADABLE", "checks": [], "errors": []}
        payload["file"] = path.name
        payload["kind"] = (
            "freshness" if path.stem.startswith(FRESHNESS_PREFIX)
            else "infra" if path.stem in INFRA_GATES
            else "gate"
        )
        reports.append(payload)
    return reports


def _gate_summary(run_dir: Path) -> dict[str, int]:
    reports = [r for r in _gate_reports(run_dir) if r["kind"] == "gate"]
    return {
        "total": len(reports),
        "pass": sum(1 for r in reports if r.get("status") == "PASS"),
    }


def _artifact_tree(root: Path, base: Path, depth: int = 0) -> list[dict[str, Any]]:
    if depth > 3 or not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if entry.name == ".store":
            continue
        rel = entry.relative_to(base).as_posix()
        if entry.is_dir():
            rows.append({"path": rel, "type": "dir", "children": _artifact_tree(entry, base, depth + 1)})
        else:
            rows.append({"path": rel, "type": "file", "size": entry.stat().st_size})
    return rows


def get_run(project: str, run_id: str) -> dict[str, Any]:
    run_dir = _run_dir(project, run_id)
    manifest = _read_json(run_dir / "manifest.json")
    stages = []
    for stage in manifest.get("stages") or []:
        stages.append(
            {
                "stage": stage.get("stage"),
                "status": stage.get("status"),
                "start_time": stage.get("start_time"),
                "end_time": stage.get("end_time"),
                "returncode": stage.get("returncode"),
                "freshness_gate": stage.get("freshness_gate"),
                "errors": stage.get("errors") or [],
                "outputs": [o.get("path") for o in (stage.get("outputs") or [])],
                "logs": stage.get("logs") or {},
            }
        )
    gate_reports = _gate_reports(run_dir)
    return {
        "run_id": manifest.get("run_id") or run_id,
        "status": manifest.get("status"),
        "workflow_id": manifest.get("workflow_id"),
        "start_time": manifest.get("start_time"),
        "end_time": manifest.get("end_time"),
        "config_sha256": manifest.get("config_sha256"),
        "stages": stages,
        "gates": gate_reports,
        "artifacts": _artifact_tree(run_dir / "artifacts", run_dir),
        "release": manifest.get("release"),
    }


def resolve_artifact(project: str, run_id: str, relative: str) -> Path:
    """Resolve an artifact path and refuse anything escaping the run directory."""
    run_dir = _run_dir(project, run_id)
    candidate = (run_dir / relative).resolve()
    if run_dir.resolve() not in candidate.parents and candidate != run_dir.resolve():
        raise LookupError("path escapes the run directory")
    if not candidate.is_file():
        raise LookupError(f"artifact not found: {relative}")
    return candidate


def read_log(project: str, run_id: str, stage_name: str, stream: str) -> str:
    _valid_name(stage_name, "stage")
    if not STREAM_RE.fullmatch(stream) or stream not in {"stdout", "stderr"}:
        raise LookupError("stream must be stdout or stderr")
    run_dir = _run_dir(project, run_id)
    manifest = _read_json(run_dir / "manifest.json")
    for stage in manifest.get("stages") or []:
        if stage.get("stage") == stage_name:
            rel = (stage.get("logs") or {}).get(stream)
            if not rel:
                return ""
            return resolve_artifact(project, run_id, rel).read_text(encoding="utf-8", errors="replace")
    raise LookupError(f"unknown stage: {stage_name}")


def start_run(project: str) -> dict[str, Any]:
    """Run the project's workflow synchronously; the job queue calls this."""
    config = _project_config(project)
    from core.runtime.production_workflow import ProductionWorkflow  # noqa: PLC0415

    workflow = ProductionWorkflow(config_path=config, python_executable=sys.executable)
    outcome = workflow.run()
    return {
        "run_id": outcome.get("run_id"),
        "status": outcome.get("status"),
        "run_dir": str(outcome.get("run_dir")),
        "release": outcome.get("release"),
    }
