"""The sole Forge v8 production execution entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from production_workflow import ProductionWorkflow


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute one Forge v8 workflow in an isolated, traceable run."
    )
    parser.add_argument("--config", required=True, help="Path to a production or problem-understanding workflow JSON config")
    parser.add_argument(
        "--runtime-root",
        default=None,
        help="Optional runtime root override (absolute, or relative to the config's project dir). "
        "Used for test isolation; production keeps the config value.",
    )
    args = parser.parse_args()
    try:
        config_path = Path(args.config)
        config = json.loads(config_path.read_text(encoding='utf-8'))
        if config.get('schema') == 'forge-release-request/v1':
            from core.runtime.release_controller import execute_request
            result = execute_request(config_path)
            completed_status = result['status'] if result['status'] in ('AWAITING_REVIEW', 'RELEASED', 'REVOKED') else 'RELEASED'
        elif config.get('schema') == 'forge-problem-understanding/v1':
            if args.runtime_root is not None:
                raise ValueError('runtime-root override is not supported for problem workflows')
            from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
            result = ProblemUnderstandingWorkflow(config_path).run()
            completed_status = "READY_FOR_REVIEW"
        else:
            result = ProductionWorkflow(config_path, runtime_root=args.runtime_root).run()
            completed_status = "PASS"
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    printable = {key: str(value) if isinstance(value, Path) else value for key, value in result.items()}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    # Successful execution is not human approval or benchmark acceptance.
    return 0 if result["status"] == completed_status else 1


if __name__ == "__main__":
    raise SystemExit(main())
