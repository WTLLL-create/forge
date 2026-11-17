"""Generate the CUMCM 2026 AI-tool usage statement and supporting detail PDF.

Implements the two artifacts required by 《全国大学生数学建模竞赛人工智能工具
使用规定（2026年试行）》(in force since 2026-09-01):

  1. ai_usage_statement.txt   - the declaration placed BEFORE the references;
  2. AI工具使用详情.pdf        - the supporting-material detail PDF.

Usage:
    python ai_usage_doc.py --usage usage.json --output-dir <dir>

usage.json (schema: forge-ai-usage/v1):
{
  "schema": "forge-ai-usage/v1",
  "used_ai": true,
  "brief_purpose": "代码调试与语言润色",
  "tools": [
    {
      "name": "...", "version": "...",
      "stage": "模型求解/论文润色等",
      "process": "提示方式与使用过程说明",
      "human_review": "对AI输出的采纳、人工修改与核验情况"
    }
  ],
  "typical_interactions": ["典型交互示例1", "典型交互示例2"]
}

The PDF is written with PyMuPDF (the only PDF dependency the workflow
already has); no reportlab or LaTeX is required.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - older PyMuPDF exposes fitz only
    try:
        import fitz
    except ImportError:  # pragma: no cover
        fitz = None  # detail-PDF generation fails explicitly when PyMuPDF is missing

STATEMENT_NOT_USED = "本参赛队在竞赛过程中未使用任何AI工具。"
STATEMENT_USED_TPL = "本参赛队在竞赛过程中使用了AI工具，主要用于{}，详细使用情况见支撑材料。"
DETAIL_PDF_NAME = "AI工具使用详情.pdf"
CJK_FONT = "china-s"


def _parse_usage(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("usage JSON must be an object")
    if raw.get("schema") != "forge-ai-usage/v1":
        raise ValueError("usage JSON schema must be forge-ai-usage/v1")
    if not isinstance(raw.get("used_ai"), bool):
        raise ValueError("usage.used_ai must be boolean")
    if raw["used_ai"]:
        if not isinstance(raw.get("brief_purpose"), str) or not raw["brief_purpose"].strip():
            raise ValueError("usage.brief_purpose is required when used_ai is true")
        if not isinstance(raw.get("tools"), list) or not raw["tools"]:
            raise ValueError("usage.tools must be a non-empty array when used_ai is true")
        for index, tool in enumerate(raw["tools"]):
            for field in ("name", "version", "stage", "process", "human_review"):
                if not isinstance(tool.get(field), str) or not tool[field].strip():
                    raise ValueError(f"usage.tools[{index}].{field} is required")
    return raw


def build_statement(usage: dict) -> str:
    """Return the exact declaration text to place before the references."""
    if not usage["used_ai"]:
        return STATEMENT_NOT_USED
    return STATEMENT_USED_TPL.format(usage["brief_purpose"].strip())


def _line_wrap(text: str, width: int) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        while len(paragraph) > width:
            cut = paragraph[:width]
            lines.append(cut)
            paragraph = paragraph[width:]
        lines.append(paragraph)
    return lines


def build_detail_pdf(usage: dict, output: Path) -> Path:
    """Write AI工具使用详情.pdf covering the four mandatory items."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (pymupdf) not installed; cannot generate the detail PDF")
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 portrait, points
    margin = 48
    width = 595 - 2 * margin
    y = margin
    fontsize = 10.5
    line_height = 15.5

    def emit(text: str, size: float = fontsize, bold: bool = False) -> None:
        nonlocal y, page
        fontname = "china-ss" if bold else CJK_FONT
        lines = _line_wrap(text, 46)
        for line in lines:
            if y > 842 - margin:
                page = doc.new_page(width=595, height=842)
                y = margin
            page.insert_text(
                (margin, y), line, fontname=fontname, fontsize=size
            )
            y += line_height if line else line_height * 0.5

    emit("AI工具使用详情", size=16, bold=True)
    y += 6
    if not usage["used_ai"]:
        emit("本参赛队未使用任何AI工具，无详情需要说明。")
    else:
        emit("一、所用AI工具名称、版本或型号", bold=True)
        for tool in usage["tools"]:
            emit(f"· {tool['name']}（{tool['version']}）")
        y += 4
        emit("二、具体使用目的和环节", bold=True)
        for tool in usage["tools"]:
            emit(f"· {tool['name']}：{tool['stage']}")
        y += 4
        emit("三、主要提示方式与使用过程说明", bold=True)
        for tool in usage["tools"]:
            emit(f"· {tool['name']}：{tool['process']}")
        interactions = usage.get("typical_interactions") or []
        if interactions:
            emit("典型交互示例：")
            for example in interactions:
                emit(f"  {example}")
        y += 4
        emit("四、对AI输出的采纳、人工修改和核验的主要情况（语言润色除外）", bold=True)
        for tool in usage["tools"]:
            emit(f"· {tool['name']}：{tool['human_review']}")
    doc.save(str(output))
    doc.close()
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the 2026 CUMCM AI-tool usage statement and detail PDF."
    )
    parser.add_argument("--usage", required=True, help="Path to forge-ai-usage/v1 JSON")
    parser.add_argument("--output-dir", required=True, help="Directory for generated artifacts")
    args = parser.parse_args()

    usage = _parse_usage(Path(args.usage))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    statement_path = out_dir / "ai_usage_statement.txt"
    statement_path.write_text(build_statement(usage) + "\n", encoding="utf-8")

    detail_path = None
    if usage["used_ai"]:
        detail_path = build_detail_pdf(usage, out_dir / DETAIL_PDF_NAME)

    result = {
        "schema": "forge-ai-usage-artifacts/v1",
        "statement": str(statement_path),
        "statement_text": build_statement(usage),
        "detail_pdf": str(detail_path) if detail_path else None,
    }
    manifest = out_dir / "ai_usage_manifest.json"
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
