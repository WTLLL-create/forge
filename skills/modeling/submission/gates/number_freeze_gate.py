"""Forge v8 number-freeze gate: every paper number must trace to a frozen snapshot.

Borrowed design: MathModeling-skills (zhnnky329) frozen_numbers.json discipline,
adapted to the Forge v8 ModelResult chain. The rule: once results are frozen,
any change to a number must be a deliberate re-freeze recorded in the freeze
log; silently drifting numbers block the run.

Inputs:
    --model-result  model_result.json            (current authoritative numbers)
    --frozen        frozen_numbers.json          (frozen snapshot, schema forge-frozen-numbers/v1)
    --freeze-log    freeze_log.jsonl (optional)  (freeze / re-freeze events)

Checks:
    1. frozen snapshot schema valid
    2. every numeric leaf of model_result exists in the frozen snapshot
    3. no numeric leaf drifts from the frozen snapshot
    4. drift is acceptable only when a later re-freeze event re-freezes the
       exact current values (change must be logged, never silently edited)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result
from core.schema.model_result import load_model_result


def iter_numeric_leaves(value: Any, prefix: str = "") -> dict[str, float]:
    leaves: dict[str, float] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            leaves.update(iter_numeric_leaves(child, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaves.update(iter_numeric_leaves(child, f"{prefix}[{index}]" if prefix else f"[{index}]"))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        leaves[prefix] = float(value)
    return leaves


def load_frozen(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("frozen_numbers.json must be an object")
    if raw.get("schema") != "forge-frozen-numbers/v1":
        raise ValueError("frozen_numbers.json schema must be forge-frozen-numbers/v1")
    numbers = raw.get("numbers")
    if not isinstance(numbers, dict):
        raise ValueError("frozen_numbers.json.numbers must be an object")
    return raw


def load_freeze_events(path: Path | None) -> list[dict]:
    if path is None or not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def run_gate(
    model_result_path: Path,
    frozen_path: Path,
    run_id: str,
    freeze_log_path: Path | None = None,
) -> dict:
    checks: list[dict] = []
    try:
        result = load_model_result(model_result_path, expected_run_id=run_id or None)
    except Exception as exc:
        return gate_result(
            "number_freeze_gate",
            [gate_check("model result readable", False, actual=str(exc), expected="valid ModelResult")],
            run_id=run_id or "UNKNOWN-RUN",
        )

    current_leaves = iter_numeric_leaves(result)
    current_key_set = set(current_leaves)

    frozen = None
    try:
        frozen = load_frozen(frozen_path)
    except Exception as exc:
        frozen = None
        checks.append(
            gate_check(
                "frozen snapshot readable and valid",
                False,
                actual=str(exc),
                expected="forge-frozen-numbers/v1",
            )
        )
    if frozen is not None:
        frozen_numbers = frozen.get("numbers", {})
        frozen_key_set = set(frozen_numbers)
        missing = sorted(current_key_set - frozen_key_set)
        checks.append(
            gate_check(
                "every model number exists in frozen snapshot",
                not missing,
                actual=missing[:10] if missing else f"{len(current_key_set)} numbers",
                expected="no missing keys",
                message="Run produced numbers that were never frozen; re-freeze before writing the paper.",
            )
        )
        drifted = {
            key: (current_leaves[key], float(frozen_numbers[key]))
            for key in current_key_set & frozen_key_set
            if abs(float(frozen_numbers[key]) - current_leaves[key]) > 1e-9
        }
        if not drifted:
            checks.append(
                gate_check(
                    "numbers match frozen snapshot",
                    True,
                    actual=f"{len(current_key_set)} numbers match",
                    expected="no drift",
                )
            )
        else:
            events = load_freeze_events(freeze_log_path)
            refrozen = {
                key
                for event in events
                if event.get("event") in {"freeze", "re-freeze"}
                and isinstance(event.get("numbers"), dict)
                for key, value in event["numbers"].items()
                if key in drifted
                and abs(float(value) - current_leaves[key]) <= 1e-9
            }
            unresolved = sorted(set(drifted) - refrozen)
            checks.append(
                gate_check(
                    "no unlogged number drift",
                    not unresolved,
                    actual=[{"key": key, "frozen": drifted[key][1], "current": drifted[key][0]} for key in unresolved[:10]]
                    if unresolved
                    else f"{len(refrozen)} drifted keys re-frozen by logged events",
                    expected="drift requires a logged re-freeze event",
                    message="Paper numbers drifted from the frozen snapshot without a re-freeze record.",
                )
            )
        stale = frozen.get("run_id")
        if stale and stale != run_id:
            checks.append(
                gate_check(
                    "frozen snapshot belongs to current run",
                    False,
                    actual=stale,
                    expected=run_id,
                )
            )

    result = gate_result("number_freeze_gate", checks, run_id=run_id)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify every model number is frozen and drift is logged."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-result", required=True)
    parser.add_argument("--frozen", required=True, help="frozen_numbers.json")
    parser.add_argument("--freeze-log", default=None, help="freeze_log.jsonl (freeze / re-freeze events)")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    result = run_gate(
        Path(args.model_result),
        Path(args.frozen),
        args.run_id,
        Path(args.freeze_log) if args.freeze_log else None,
    )
    write_gate_result(args.report, result)
    print(json.dumps({"gate": result["gate"], "status": result["status"], "report": str(Path(args.report).resolve())}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
