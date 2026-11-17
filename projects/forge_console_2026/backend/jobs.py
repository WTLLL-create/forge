"""Serial job queue for Forge runs.

ProductionWorkflow takes a process-wide file lock per runtime root, so runs are
executed one at a time on a single worker thread instead of in parallel.
"""
from __future__ import annotations

import queue
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from backend import forge_service


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class JobManager:
    def __init__(self, max_jobs: int = 50) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []
        self._max_jobs = max_jobs
        self._lock = threading.Lock()
        self._queue: queue.Queue[str] = queue.Queue()
        self._worker = threading.Thread(target=self._consume, name="forge-job-worker", daemon=True)
        self._worker.start()

    def submit(self, project: str) -> dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        job = {
            "job_id": job_id,
            "project": project,
            "status": "queued",
            "created_at": _now(),
            "started_at": None,
            "finished_at": None,
            "run_id": None,
            "message": None,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._order.append(job_id)
            self._trim()
        self._queue.put(job_id)
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(self._jobs[job_id]) for job_id in reversed(self._order) if job_id in self._jobs]

    def _trim(self) -> None:
        while len(self._order) > self._max_jobs:
            stale = self._order.pop(0)
            self._jobs.pop(stale, None)

    def _consume(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._execute(job_id)
            finally:
                self._queue.task_done()

    def _execute(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["status"] = "running"
            job["started_at"] = _now()
        try:
            outcome = forge_service.start_run(job["project"])
            with self._lock:
                job["run_id"] = outcome.get("run_id")
                job["status"] = outcome.get("status") or "UNKNOWN"
                job["message"] = (outcome.get("release") or {}).get("status")
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI verbatim
            with self._lock:
                job["status"] = "ERROR"
                job["message"] = f"{type(exc).__name__}: {exc}"
        finally:
            with self._lock:
                job["finished_at"] = _now()


jobs = JobManager()
