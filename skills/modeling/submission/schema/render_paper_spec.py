"""Render Markdown deterministically from a validated PaperSpec."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.model_result import load_model_result
from submission.schema.paper_spec import load_paper_spec, validate_paper_spec


def render_markdown(spec: dict) -> str:
    lines = [f"# {spec['title']}", ""]
    for section in spec["sections"]:
        lines.extend([f"## {section['title']}", ""])
        for block in section["blocks"]:
            kind = block["type"]
            if kind == "bound_text":
                lines.extend([block["claim"], ""])
            elif kind == "static_text":
                lines.extend([block["text"], ""])
            elif kind in {"ranking_table", "parameter_table"}:
                lines.append("| " + " | ".join(block["headers"]) + " |")
                lines.append("| " + " | ".join(["---"] * len(block["headers"])) + " |")
                for row in block["rows"]:
                    lines.append("| " + " | ".join(str(value) for value in row) + " |")
                lines.append("")
            elif kind == "figure":
                lines.extend([f"**图{block['id']} {block['caption']}**", ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-spec", required=True)
    parser.add_argument("--model-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    model_path = Path(args.model_result)
    result = load_model_result(model_path)
    spec = load_paper_spec(args.paper_spec)
    validate_paper_spec(spec, result, model_path)
    rendered = render_markdown(spec)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    print(json.dumps({"run_id": spec["run_id"], "output": str(target.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
