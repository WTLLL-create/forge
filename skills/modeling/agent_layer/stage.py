"""Workflow stage: run the review agent and emit a non-blocking report.

Stage semantics:
- exit code is always 0, so the pipeline continues;
- ``gates/agent_review.json`` records PASS or REVIEW_NEEDED for humans;
- ``artifacts/support/revision_plan.json`` holds the revision plan.

Making it blocking is a deliberate later decision: flip ``ADVISORY`` to False.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[1]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from agent_layer.pipeline import RevisionPipeline, write_plan  # noqa: E402
from agent_layer.retrieval import build_index  # noqa: E402

ADVISORY = True
TEMPLATE_ROOT = MODELING_ROOT.parents[1] / "templates" / "document" / "math-modeling"


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent review stage")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--paper-spec", required=True, help="current-run paper_spec.json")
    parser.add_argument("--report", required=True, help="gate report path")
    parser.add_argument("--output", required=True, help="revision plan path")
    args = parser.parse_args()

    paper_spec = Path(args.paper_spec).resolve()
    run_dir = paper_spec.parents[1]
    index = build_index(MODELING_ROOT, extra_dirs=[TEMPLATE_ROOT])

    result = RevisionPipeline(run_dir, index=index).run()
    review = result["review"]
    plan = result["plan"]

    write_plan(plan, Path(args.output).parent)

    summary = review.get("summary") or {}
    verification = plan.get("verification") or {}
    high = summary.get("high", 0)
    verdict = verification.get("verdict")
    ok = high == 0 and verdict in {"PASS", "EMPTY"}

    gate = {
        "schema": "forge-gate-result/v1",
        "run_id": args.run_id,
        "gate": "agent_review",
        "status": "PASS" if ok else "REVIEW_NEEDED",
        "advisory": ADVISORY,
        "checks": [
            {"name": "agent review completed", "status": "PASS" if review.get("finished") else "FAIL"},
            {"name": "high severity issues", "status": "PASS" if high == 0 else "FAIL", "actual": high, "expected": 0},
            {"name": "revision plan verified", "status": "PASS" if verdict in {"PASS", "EMPTY"} else "FAIL", "actual": verdict},
            {"name": "tools called", "status": "PASS", "actual": summary.get("steps", 0)},
        ],
        "errors": [],
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"gate": gate["status"], "issues": summary.get("issues", 0), "steps": summary.get("steps", 0)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
