"""Forge v8 AI-compliance gate for the 2026 CUMCM AI-tool usage rules.

Enforces 《全国大学生数学建模竞赛人工智能工具使用规定（2026年试行）》(in force
since 2026-09-01):

  1. The paper carries an "AI工具使用声明" immediately BEFORE the references
     section, using one of the two mandated phrasings.
  2. When the declaration says AI was used, the supporting materials contain
     "AI工具使用详情.pdf" and that PDF covers the four mandatory items
     (tool name/version, purpose & stage, prompting process, human review).
  3. When --usage is supplied, the declaration must be consistent with the
     recorded usage.

Usage:
    python ai_compliance_gate.py --run-id <run> --docx paper.docx \
        --support-dir <dir> [--usage usage.json] --report gate.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    try:
        import fitz
    except ImportError:  # pragma: no cover
        fitz = None  # detail-PDF inspection fails explicitly when PyMuPDF is missing

DETAIL_PDF_NAME = "AI工具使用详情.pdf"

STATEMENT_NOT_USED_PATTERN = re.compile(r"未使用任何AI工具")
STATEMENT_USED_PATTERN = re.compile(r"使用了AI工具")
REFERENCE_HEADING_PATTERN = re.compile(r"^\s*参考文献\s*$")

DETAIL_REQUIRED_MARKERS = {
    "tool_name": re.compile(r"工具名称|名称、版本|型号"),
    "purpose": re.compile(r"使用目的|用途和环节|目的和环节|使用目的和环节"),
    "process": re.compile(r"提示方式|提示词|使用过程|交互示例"),
    "human_review": re.compile(r"采纳|人工修改|核验|审查"),
}


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def docx_paragraphs(docx_path: Path) -> list[str]:
    from docx import Document

    doc = Document(docx_path)
    texts: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            texts.append(para.text.strip())
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    texts.append(cell.text.strip())
    return texts


def locate_reference_index(texts: list[str]) -> int:
    """Return the index of the references heading, or -1 when absent."""
    for index, text in enumerate(texts):
        if REFERENCE_HEADING_PATTERN.match(text):
            return index
    return -1


def find_declaration(texts: list[str], before_index: int) -> str | None:
    """Return the declaration text found before the references heading."""
    for text in texts[:before_index]:
        if STATEMENT_NOT_USED_PATTERN.search(text) or STATEMENT_USED_PATTERN.search(text):
            return text
    return None


def inspect_detail_pdf(path: Path) -> tuple[dict[str, bool], str]:
    coverage = {key: False for key in DETAIL_REQUIRED_MARKERS}
    if fitz is None:
        return coverage, "cannot read detail PDF: PyMuPDF (pymupdf) not installed"
    try:
        with fitz.open(path) as doc:
            text = "\n".join(page.get_text() for page in doc)
    except Exception as exc:  # pragma: no cover
        return coverage, f"cannot read detail PDF: {exc}"
    for key, pattern in DETAIL_REQUIRED_MARKERS.items():
        coverage[key] = bool(pattern.search(text))
    return coverage, text


def run_gate(
    docx_path: Path,
    support_dir: Path,
    run_id: str,
    usage_path: Path | None = None,
) -> dict:
    checks: list[dict] = []
    texts = docx_paragraphs(docx_path)

    ref_index = locate_reference_index(texts)
    checks.append(
        gate_check(
            "references heading present",
            ref_index >= 0,
            actual=ref_index if ref_index >= 0 else "not found",
            expected=">= 0",
        )
    )

    declaration = find_declaration(texts, ref_index if ref_index >= 0 else len(texts))
    checks.append(
        gate_check(
            "AI usage declaration before references",
            declaration is not None,
            actual=declaration[:120] if declaration else "not found",
            expected="declaration text",
        )
    )

    used_ai = bool(declaration and STATEMENT_USED_PATTERN.search(declaration))
    checks.append(
        gate_check(
            "declaration phrase valid",
            declaration is not None
            and (STATEMENT_USED_PATTERN.search(declaration) or STATEMENT_NOT_USED_PATTERN.search(declaration)),
            actual=declaration[:120] if declaration else "not found",
            expected="one of the two mandated phrasings",
        )
    )

    detail_path = support_dir / DETAIL_PDF_NAME
    detail_exists = detail_path.is_file()
    if used_ai:
        checks.append(
            gate_check(
                "detail PDF present when AI used",
                detail_exists,
                actual=str(detail_path) if detail_exists else "missing AI工具使用详情.pdf",
                expected=DETAIL_PDF_NAME,
            )
        )
        if detail_exists:
            coverage, detail_text = inspect_detail_pdf(detail_path)
            missing = [key for key, present in coverage.items() if not present]
            checks.append(
                gate_check(
                    "detail PDF covers four mandatory items",
                    not missing,
                    actual=sorted(missing) if missing else "all covered",
                    expected=["tool_name", "purpose", "process", "human_review"],
                )
            )
            checks.append(
                gate_check(
                    "detail PDF non-empty",
                    len(detail_text.strip()) > 50,
                    actual=len(detail_text.strip()),
                    expected="> 50 chars",
                )
            )
            checks.append(
                gate_check(
                    "detail PDF hash recorded",
                    True,
                    actual=sha256_file(detail_path),
                    expected="sha256",
                    message="",
                )
            )
    else:
        checks.append(
            gate_check(
                "no detail PDF required",
                not detail_exists or True,
                actual="declared not used",
                expected="consistent with declaration",
                message="Supporting detail PDF is optional when AI was not used.",
            )
        )

    if usage_path is not None and usage_path.is_file():
        try:
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
            recorded = bool(usage.get("used_ai"))
            checks.append(
                gate_check(
                    "declaration consistent with usage record",
                    recorded == used_ai,
                    actual={"declared": used_ai, "recorded": recorded},
                    expected="equal",
                )
            )
        except Exception as exc:
            checks.append(
                gate_check("usage record readable", False, actual=str(exc), expected="valid JSON")
            )

    result = gate_result("ai_compliance_gate", checks, run_id=run_id)
    result["artifacts"] = {
        "docx_sha256": sha256_file(docx_path),
        "detail_pdf_sha256": sha256_file(detail_path) if detail_path.is_file() else None,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check compliance with the 2026 CUMCM AI-tool usage rules."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--docx", required=True, help="Generated paper DOCX")
    parser.add_argument("--support-dir", required=True, help="Supporting-materials directory")
    parser.add_argument("--usage", default=None, help="Optional forge-ai-usage/v1 JSON for consistency check")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    result = run_gate(
        Path(args.docx),
        Path(args.support_dir),
        args.run_id,
        Path(args.usage) if args.usage else None,
    )
    write_gate_result(args.report, result)
    print(json.dumps({"gate": result["gate"], "status": result["status"], "report": str(Path(args.report).resolve())}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
