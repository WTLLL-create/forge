"""Strict layout/template compliance gate for generated CUMCM DOCX files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cm(value) -> float:
    return round(value.cm, 2) if value is not None else -1


IDENTITY_LEAK_PATTERN = re.compile(
    r"(参赛队号|队伍编号|队号[:：]|学校[:：]|赛区[:：]|指导教师[:：]|"
    r"[一二三四五六七八九十]{1,3}号参赛队|来自.{0,12}(大学|学院|学校))",
    re.IGNORECASE,
)


def run_gate(docx_path: Path, template_path: Path, contract_path: Path, run_id: str = "", policy: str = "cumcm-2026") -> dict:
    doc = Document(docx_path)
    template_sha = sha256_file(template_path)
    contract_sha = sha256_file(contract_path)
    keywords = doc.core_properties.keywords or ""
    checks: list[dict] = []

    def check(name: str, passed: bool, actual, expected) -> None:
        checks.append(gate_check(name, passed, actual=actual, expected=expected))

    check("template SHA recorded", f"template_sha256={template_sha}" in keywords, keywords, template_sha)
    check("style contract SHA recorded", f"style_contract_sha256={contract_sha}" in keywords, keywords, contract_sha)
    for section_index, section in enumerate(doc.sections, 1):
        prefix = f"section {section_index}"
        check(f"{prefix} A4 page width", abs(cm(section.page_width) - 21.0) <= 0.05, cm(section.page_width), 21.0)
        check(f"{prefix} A4 page height", abs(cm(section.page_height) - 29.7) <= 0.05, cm(section.page_height), 29.7)
        for label, actual, expected in (
            ("top margin", cm(section.top_margin), 2.5),
            ("bottom margin", cm(section.bottom_margin), 2.5),
            ("left margin", cm(section.left_margin), 3.0),
            ("right margin", cm(section.right_margin), 3.0),
        ):
            check(f"{prefix} {label}", abs(actual - expected) <= 0.08, actual, expected)
        check(
            f"{prefix} header contains paper title",
            any(p.text.strip() and "[[" not in p.text for p in section.header.paragraphs),
            [p.text for p in section.header.paragraphs],
            "resolved title",
        )
        footer_xml = section.footer._element.xml
        check(f"{prefix} footer has PAGE field", " PAGE " in footer_xml, "PAGE" in footer_xml, True)

    normal = doc.styles["Normal"]
    check("Normal font size", normal.font.size is not None and abs(normal.font.size.pt - 12) < 0.1, normal.font.size.pt if normal.font.size else None, 12)
    check("Normal line spacing", normal.paragraph_format.line_spacing == 1.5, normal.paragraph_format.line_spacing, 1.5)
    for style_name, expected in (("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 12)):
        style = doc.styles[style_name]
        check(f"{style_name} size", style.font.size is not None and abs(style.font.size.pt - expected) < 0.1, style.font.size.pt if style.font.size else None, expected)

    check("document has title", bool(doc.core_properties.title.strip()), doc.core_properties.title, "non-empty")
    substantive = sum(bool(p.text.strip()) for p in doc.paragraphs)
    check("document has substantive paragraphs", substantive >= 8, substantive, ">=8")
    check("no unresolved template marker", all("[[" not in p.text for p in doc.paragraphs), "markers scanned", "none")
    meta_pattern = re.compile(r"(?:三角验证|Quality Gate|纸张状态|^\s*(?:Claim|Evidence|Score)\s*[:：—])", re.IGNORECASE)
    meta_residue = [p.text[:100] for p in doc.paragraphs if meta_pattern.search(p.text)]
    check("no meta review residue", not meta_residue, meta_residue, [])

    table_failures = []
    for index, table in enumerate(doc.tables, 1):
        tbl_pr = table._tbl.tblPr
        borders = tbl_pr.find(qn("w:tblBorders"))
        if borders is None:
            table_failures.append(f"table {index}: no borders definition")
            continue
        def val(edge):
            node = borders.find(qn(f"w:{edge}"))
            return node.get(qn("w:val")) if node is not None else None
        def size(edge):
            node = borders.find(qn(f"w:{edge}"))
            return node.get(qn("w:sz")) if node is not None else None
        header_bottom = []
        for cell in table.rows[0].cells:
            cell_borders = cell._tc.get_or_add_tcPr().find(qn("w:tcBorders"))
            bottom = cell_borders.find(qn("w:bottom")) if cell_borders is not None else None
            header_bottom.append(
                {
                    "val": bottom.get(qn("w:val")) if bottom is not None else None,
                    "size": bottom.get(qn("w:sz")) if bottom is not None else None,
                }
            )
        if (
            val("top") != "single"
            or size("top") != "12"
            or val("bottom") != "single"
            or size("bottom") != "12"
            or val("left") not in ("nil", "none")
            or val("right") not in ("nil", "none")
            or val("insideV") not in ("nil", "none")
            or val("insideH") not in ("nil", "none")
            or any(value != {"val": "single", "size": "6"} for value in header_bottom)
        ):
            table_failures.append(
                f"table {index}: top={val('top')}/{size('top')} bottom={val('bottom')}/{size('bottom')} "
                f"left={val('left')} right={val('right')} insideV={val('insideV')} "
                f"insideH={val('insideH')} headerBottom={header_bottom}"
            )
    check("all tables use three-line borders", not table_failures, table_failures, [])

    if policy == "cumcm-2026":
        # 2026 revision (2026-07-02, in force): no TOC, no identity info,
        # appendix declares support materials / programs, e-version starts at abstract.
        body_xml = doc.element.body.xml
        toc_hits = re.findall(r'instrText[^>]*>([^<]*TOC[^<]*)<', body_xml, re.IGNORECASE)
        check("no table-of-contents field (2026)", not toc_hits, toc_hits[:3], [])
        identity_leaks = [p.text[:120] for p in doc.paragraphs if IDENTITY_LEAK_PATTERN.search(p.text)]
        check("no identity/school/team-number leak (2026)", not identity_leaks, identity_leaks, [])
        full_text = "\n".join(p.text for p in doc.paragraphs)
        appendix_present = bool(re.search(r"^附录", full_text, re.MULTILINE))
        if appendix_present:
            appendix_text = full_text.split("附录", 1)[1]
            has_declaration = bool(
                re.search(r"支撑材料", appendix_text)
                or re.search(r"没有用到程序", appendix_text)
                or re.search(r"本论文没有支撑材料", appendix_text)
            )
            check(
                "appendix declares support materials or programs (2026)",
                has_declaration,
                appendix_text[:80],
                "support-materials list or no-program statement",
            )
        else:
            check("appendix section present (2026)", False, "no 附录 heading", "附录 section")

    report = gate_result("template_compliance_gate", checks, run_id=run_id)
    report["artifacts"] = {"docx_sha256": sha256_file(docx_path)}
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docx", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--style-contract", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--policy", default="cumcm-2026", help="cumcm-2026 (2026 revision checks) or legacy")
    args = parser.parse_args()
    report = run_gate(Path(args.docx), Path(args.template), Path(args.style_contract), args.run_id, args.policy)
    report_path = Path(args.report)
    write_gate_result(report_path, report)
    print(json.dumps({"gate": report["gate"], "status": report["status"], "report": str(report_path.resolve())}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
