"""FastAPI entry point for the Forge console."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend import forge_service, review_service
from backend.jobs import jobs

BASE = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = "forge_v7_3_d2026"

app = FastAPI(title="Forge Console", version="0.1.0", docs_url="/api/docs", redoc_url=None)


def _lookup(call, *args):
    try:
        return call(*args)
    except forge_service.LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/projects")
def projects() -> list[dict[str, Any]]:
    return forge_service.list_projects()


@app.get("/api/runs")
def runs(project: str = Query(DEFAULT_PROJECT)) -> list[dict[str, Any]]:
    return _lookup(forge_service.list_runs, project)


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str, project: str = Query(DEFAULT_PROJECT)) -> dict[str, Any]:
    return _lookup(forge_service.get_run, project, run_id)


@app.get("/api/runs/{run_id}/download")
def download(run_id: str, path: str, project: str = Query(DEFAULT_PROJECT)):
    resolved = _lookup(forge_service.resolve_artifact, project, run_id, path)
    return FileResponse(resolved, filename=resolved.name)


@app.get("/api/runs/{run_id}/logs/{stage}/{stream}", response_class=PlainTextResponse)
def log(run_id: str, stage: str, stream: str, project: str = Query(DEFAULT_PROJECT)) -> str:
    return _lookup(forge_service.read_log, project, run_id, stage, stream)


@app.post("/api/jobs", status_code=202)
def create_job(project: str = Query(DEFAULT_PROJECT)) -> dict[str, Any]:
    try:
        forge_service._project_config(project)  # noqa: SLF001 - validation only
    except forge_service.LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return jobs.submit(project)


@app.get("/api/jobs")
def list_jobs() -> list[dict[str, Any]]:
    return jobs.list()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
    return job


def _review_call(call, *args):
    try:
        return call(*args)
    except review_service.ReviewError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/review", status_code=202)
def create_review(run_id: str, project: str = Query(DEFAULT_PROJECT)) -> dict[str, Any]:
    """Queue one review; the worker writes review_report.json and revision_plan.json."""
    return _review_call(review_service.trigger, project, run_id)


@app.get("/api/runs/{run_id}/review")
def get_review(run_id: str, project: str = Query(DEFAULT_PROJECT)) -> dict[str, Any]:
    """Read the persisted status, review report and revision plan."""
    return _review_call(review_service.read, project, run_id)


@app.get("/api/runs/{run_id}/review/trace")
def get_review_trace(run_id: str, project: str = Query(DEFAULT_PROJECT)) -> dict[str, Any]:
    """Tool-call trace of the last review."""
    return _review_call(review_service.trace, project, run_id)


app.mount("/", StaticFiles(directory=BASE / "frontend", html=True), name="frontend")
