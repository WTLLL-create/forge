"""Freeze every numeric leaf of model_result.json inside the current run.

Writes a forge-frozen-numbers/v1 snapshot and an initial freeze event so the
number_freeze_gate can verify that the paper's numbers belong to this run and
were frozen (with drift tracking) before writing the paper.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from submission.gates.number_freeze_gate import iter_numeric_leaves


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze model-result numbers inside the current run."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-result", required=True)
    parser.add_argument("--output", required=True, help="frozen_numbers.json (run-local)")
    parser.add_argument("--freeze-log", required=True, help="freeze_log.jsonl (run-local)")
    args = parser.parse_args()

    model_result_path = Path(args.model_result)
    model_result = json.loads(model_result_path.read_text(encoding="utf-8"))
    numbers = iter_numeric_leaves(model_result)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    frozen = {
        "schema": "forge-frozen-numbers/v1",
        "run_id": args.run_id,
        "frozen_at": now,
        "numbers": numbers,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(frozen, ensure_ascii=False, indent=2), encoding="utf-8")

    event = {"event": "freeze", "at": now, "run_id": args.run_id, "numbers": numbers}
    log = Path(args.freeze_log)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"frozen_numbers": len(numbers), "output": str(output.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
