"""Forge v8 human-judgment gate: modeling choices must be owned by the team.

Corresponds to the 2026 CUMCM AI rules requirement that 核心建模与分析由参赛队
主导 and to the human-owned decision gates (G2.5 / G4) of MathModeling-skills
(zhnnky329) and the MANUAL mode of AutoMCM-Pro: the AI may propose, but the
team commits the method choice and the acceptance of results.

judgment_records.jsonl, one JSON object per line:
    {"decision_point": "method_selection", "made_by": "user", "decision": "...",
     "at": "2026-09-10T09:00:00+08:00", "run_id": "..."}

Required decision points:
    method_selection   - team commits the modelling method/route
    result_acceptance  - team accepts the numerical results before paper writing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result

REQUIRED_POINTS = ("method_selection", "result_acceptance")
HUMAN_OWNERS = {"user", "human", "team"}


def load_judgments(path: Path) -> list[dict]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"judgment_records.jsonl line {line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"judgment_records.jsonl line {line_number}: not an object")
        records.append(record)
    return records


def run_gate(judgments_path: Path, run_id: str) -> dict:
    checks: list[dict] = []

    if not judgments_path.is_file():
        return gate_result(
            "human_judgment_gate",
            [
                gate_check(
                    "judgment records present",
                    False,
                    actual=str(judgments_path),
                    expected="existing judgment_records.jsonl",
                    message="Modeling decisions must be recorded and owned by the team.",
                )
            ],
            run_id=run_id,
        )

    try:
        records = load_judgments(judgments_path)
    except Exception as exc:
        return gate_result(
            "human_judgment_gate",
            [gate_check("judgment records readable", False, actual=str(exc), expected="valid JSONL")],
            run_id=run_id,
        )

    checks.append(gate_check("judgment records non-empty", bool(records), actual=len(records), expected=">= 1"))

    current_run = [record for record in records if not record.get("run_id") or record.get("run_id") == run_id]
    by_point: dict[str, list[dict]] = {}
    for record in current_run:
        point = record.get("decision_point")
        if isinstance(point, str):
            by_point.setdefault(point, []).append(record)

    for point in REQUIRED_POINTS:
        entries = by_point.get(point, [])
        checks.append(
            gate_check(
                f"decision point recorded: {point}",
                bool(entries),
                actual=len(entries),
                expected=">= 1",
                message="A team-owned decision record is required before this stage may pass.",
            )
        )
        if entries:
            latest = entries[-1]
            owner = str(latest.get("made_by", "")).strip().lower()
            checks.append(
                gate_check(
                    f"{point} decided by the team",
                    owner in HUMAN_OWNERS,
                    actual=latest.get("made_by"),
                    expected="user/human/team",
                    message="AI must not commit the modelling choice or accept results by itself.",
                )
            )
            decision = str(latest.get("decision", "")).strip()
            checks.append(
                gate_check(
                    f"{point} decision content non-empty",
                    bool(decision),
                    actual=decision[:120] if decision else "empty",
                    expected="non-empty decision text",
                )
            )
            checks.append(
                gate_check(
                    f"{point} decision timestamp present",
                    bool(str(latest.get("at", "")).strip()),
                    actual=latest.get("at"),
                    expected="ISO timestamp",
                )
            )

    result = gate_result("human_judgment_gate", checks, run_id=run_id)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the team owns the modelling decisions (2026 CUMCM AI rules)."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--judgments", required=True, help="judgment_records.jsonl")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    result = run_gate(Path(args.judgments), args.run_id)
    write_gate_result(args.report, result)
    print(json.dumps({"gate": result["gate"], "status": result["status"], "report": str(Path(args.report).resolve())}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
