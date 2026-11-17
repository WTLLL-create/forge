"""Build the contract-derived CUMCM reference DOCX.

This is a replaceable bootstrap template, not an assertion that it is an
official competition file. A future official template may replace the DOCX
while keeping the same workflow interface.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


def set_font(style, cn: str, en: str, size: float, bold: bool = False) -> None:
    style.font.name = en
    style.font.size = Pt(size)
    style.font.bold = bold
    fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:eastAsia"), cn)
    fonts.set(qn("w:ascii"), en)
    fonts.set(qn("w:hAnsi"), en)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, end])


def build(contract_path: Path, output_path: Path) -> None:
    with contract_path.open("r", encoding="utf-8") as stream:
        contract = json.load(stream)
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    margin = contract["page"]["margin"]
    section.top_margin = Cm(float(margin["top"].removesuffix("cm")))
    section.bottom_margin = Cm(float(margin["bottom"].removesuffix("cm")))
    section.left_margin = Cm(float(margin["left"].removesuffix("cm")))
    section.right_margin = Cm(float(margin["right"].removesuffix("cm")))

    normal = doc.styles["Normal"]
    set_font(normal, contract["font"]["body_cn"], contract["font"]["body_en"], 12)
    normal.paragraph_format.line_spacing = contract["font"]["line_spacing"]
    normal.paragraph_format.first_line_indent = Cm(0.74)
    normal.paragraph_format.space_after = Pt(0)

    set_font(doc.styles["Title"], "黑体", contract["font"]["body_en"], 18, True)
    doc.styles["Title"].paragraph_format.space_after = Pt(12)
    for name, cn, size in (("Heading 1", "黑体", 16), ("Heading 2", "黑体", 14), ("Heading 3", "黑体", 12)):
        style = doc.styles[name]
        set_font(style, cn, contract["font"]["body_en"], size, True)
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True

    header = section.header.paragraphs[0]
    header.text = "[[PAPER_TITLE]]"
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header.style = doc.styles["Normal"]
    header.paragraph_format.first_line_indent = Cm(0)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.first_line_indent = Cm(0)
    add_page_field(footer)

    doc.core_properties.title = "Forge CUMCM reference template"
    doc.core_properties.subject = "Contract-derived bootstrap template"
    doc.core_properties.keywords = "template_id=CUMCM-2024-bootstrap"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build(Path(args.contract), Path(args.output))
    print(f"Template written: {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
