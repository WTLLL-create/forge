"""Canonical gate result contract used by every Forge v8 production gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def gate_check(name: str, passed: bool, *, actual: Any = None, expected: Any = None, message: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "actual": actual,
        "expected": expected,
        "message": message,
    }


def gate_result(gate: str, checks: list[dict[str, Any]], *, run_id: str = "") -> dict[str, Any]:
    if not gate.strip():
        raise ValueError("GateResult.gate must be non-empty")
    if not run_id.strip():
        raise ValueError("GateResult.run_id must be non-empty")
    if not checks:
        raise ValueError("GateResult.checks must be non-empty")
    errors = [
        {"check": item["name"], "message": item.get("message") or "check failed"}
        for item in checks
        if item.get("status") != "PASS"
    ]
    return {
        "schema": "forge-gate-result/v1",
        "run_id": run_id,
        "gate": gate,
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
    }


def write_gate_result(path: str | Path, result: dict[str, Any]) -> None:
    validate_gate_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_gate_result(result: dict[str, Any]) -> None:
    required = {"schema", "run_id", "gate", "status", "checks", "errors"}
    missing = sorted(required - set(result))
    if missing:
        raise ValueError(f"GateResult missing fields: {missing}")
    if result["schema"] != "forge-gate-result/v1":
        raise ValueError("GateResult.schema must be forge-gate-result/v1")
    if not isinstance(result["run_id"], str) or not result["run_id"].strip():
        raise ValueError("GateResult.run_id must be non-empty")
    if not isinstance(result["gate"], str) or not result["gate"].strip():
        raise ValueError("GateResult.gate must be non-empty")
    if not isinstance(result["checks"], list) or not result["checks"]:
        raise ValueError("GateResult.checks must be a non-empty array")
    for check in result["checks"]:
        if not isinstance(check, dict) or not check.get("name") or check.get("status") not in {"PASS", "FAIL"}:
            raise ValueError("Every GateResult check needs a name and PASS/FAIL status")
    if result["status"] not in {"PASS", "FAIL"}:
        raise ValueError("GateResult.status must be PASS or FAIL")
    derived_errors = [
        {"check": item["name"], "message": item.get("message") or "check failed"}
        for item in result["checks"]
        if item["status"] == "FAIL"
    ]
    derived_status = "FAIL" if derived_errors else "PASS"
    if result["status"] != derived_status or result["errors"] != derived_errors:
        raise ValueError("GateResult status/errors must be derived from checks")
