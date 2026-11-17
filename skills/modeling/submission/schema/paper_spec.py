"""Forge v8 PaperSpec contract: prose facts are bound to ModelResult paths."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.model_result import json_path_get, sha256_file


def format_bound_value(value: Any, format_spec: str = "") -> str:
    if format_spec:
        return format(value, format_spec)
    return str(value)


INFO_CLASSES = {"original", "confirmed", "inferred", "suggestion"}
# Four information classes (borrowed from zLanqing/codex-claude-academic-skills):
#   original   - verbatim from source data / model output (a fact)
#   confirmed  - user/model verified fact
#   inferred   - derived by reasoning, not directly measured
#   suggestion - proposed direction / recommendation, not a claim


def render_bound_text(block: dict[str, Any], model_result: dict[str, Any]) -> str:
    values: dict[str, str] = {}
    for name, binding in block.get("bindings", {}).items():
        if binding.get("artifact") != "model_result.json":
            raise ValueError(f"Binding {name} uses a forbidden artifact")
        value = json_path_get(model_result, binding["path"])
        values[name] = format_bound_value(value, binding.get("format", ""))
    return block["template"].format(**values)


def validate_paper_spec(spec: dict[str, Any], model_result: dict[str, Any], model_result_path: str | Path | None = None) -> None:
    for field in ("run_id", "problem_id", "model_result", "title", "sections", "expected_artifacts"):
        if field not in spec:
            raise ValueError(f"PaperSpec missing field: {field}")
    if spec["run_id"] != model_result["run_id"] or spec["problem_id"] != model_result["problem_id"]:
        raise ValueError("PaperSpec and ModelResult identity mismatch")
    if model_result_path and spec["model_result"].get("sha256") != sha256_file(model_result_path):
        raise ValueError("PaperSpec references a different ModelResult hash")
    for section in spec["sections"]:
        if not isinstance(section.get("blocks"), list):
            raise ValueError("Each PaperSpec section must contain blocks")
        for block in section["blocks"]:
            kind = block.get("type")
            info_class = block.get("info_class", "confirmed")
            if info_class not in INFO_CLASSES:
                raise ValueError(f"Unsupported info_class: {info_class}")
            if kind == "bound_text":
                rendered = render_bound_text(block, model_result)
                if block.get("claim") != rendered:
                    raise ValueError(f"Bound claim drift in block {block.get('id', '?')}")
                if re.search(r"\d", block["template"].replace("{", "").replace("}", "")):
                    raise ValueError("Bound-text templates cannot contain literal digits")
                if info_class not in {"original", "confirmed"}:
                    raise ValueError(
                        f"Bound numeric facts must be original or confirmed, got {info_class}"
                    )
            elif kind == "static_text":
                if re.search(r"\d", block.get("text", "")):
                    raise ValueError("Static paper text cannot contain numeric facts")
                if block.get("info_class") in {"original", "confirmed"} and not block.get("source"):
                    raise ValueError(
                        "Static text claiming original/confirmed status must declare a source"
                    )
            elif kind not in {"ranking_table", "parameter_table", "figure"}:
                raise ValueError(f"Unsupported PaperSpec block type: {kind}")


def load_paper_spec(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_paper_spec(path: str | Path, spec: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
