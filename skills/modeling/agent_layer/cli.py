"""CLI: run the review agent over one completed run.

Usage (from skills/modeling):
    python -m agent_layer.cli --run <run_dir>
    python -m agent_layer.cli --run <run_dir> --no-index
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_layer.retrieval import build_index
from agent_layer.reviewer import ReviewAgent, write_report

MODELING_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = MODELING_ROOT.parents[1] / "templates" / "document" / "math-modeling"


def main() -> int:
    parser = argparse.ArgumentParser(description="Forge review agent")
    parser.add_argument("--run", required=True, help="completed run directory")
    parser.add_argument("--out", default="", help="output directory (default: <project>/agent_reports/<run_id>)")
    parser.add_argument("--knowledge", default=str(MODELING_ROOT), help="knowledge root for retrieval")
    parser.add_argument("--no-index", action="store_true", help="skip knowledge retrieval")
    parser.add_argument("--pretty", action="store_true", help="print the full report")
    args = parser.parse_args()

    run_dir = Path(args.run).resolve()
    index = None
    if not args.no_index:
        index = build_index(Path(args.knowledge), extra_dirs=[TEMPLATE_ROOT])

    agent = ReviewAgent(run_dir, index=index)
    report = agent.run()

    out_dir = Path(args.out) if args.out else run_dir.parents[1] / "agent_reports" / run_dir.name
    target = write_report(report, out_dir)

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"report: {target}")
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["finished"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
