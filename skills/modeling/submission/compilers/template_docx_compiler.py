"""Canonical template-bound Markdown -> DOCX compiler.

Unlike the legacy project renderers, this compiler never creates a blank Word
document. It loads a declared reference DOCX, preserves its styles and section
parts, clears only the document body, and records the template SHA-256 in the
output metadata for the submission gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

if __package__:
    from .native_omml import polynomial_omml
else:
    from native_omml import polynomial_omml


META_HEADINGS = {"三角验证", "Gate", "纸张状态"}

# Fixed compliance structure emitted by this compiler (2026 CUMCM AI-tool rule).
# scientific_gate mirrors these when building the expected paragraph list.
AI_DECLARATION_HEADING = "AI工具使用声明"
AI_DECLARATION_TEXT = (
    "本论文使用了AI工具，其工具名称、版本、使用目的和环节、提示方式与过程、"
    "AI输出的采纳与人工修改核验情况，详见支撑材料《AI工具使用详情.pdf》。"
)
REFERENCES_HEADING = "参考文献"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_body(doc: Document) -> None:
    body = doc._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def set_run_font(run, cn="宋体", en="Times New Roman", size=12, bold=False, italic=False):
    run.font.name = en
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.get_or_add_rFonts()
    fonts.set(qn("w:eastAsia"), cn)
    fonts.set(qn("w:ascii"), en)
    fonts.set(qn("w:hAnsi"), en)


def add_inline_markdown(paragraph, text: str, size: float = 12) -> None:
    parts = re.split(r"(\*\*.+?\*\*|`.+?`|\*[^*]+?\*)", text)
    for part in parts:
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        code = part.startswith("`") and part.endswith("`")
        italic = part.startswith("*") and part.endswith("*") and not bold
        clean = part[2:-2] if bold else (part[1:-1] if code or italic else part)
        run = paragraph.add_run(clean)
        set_run_font(run, cn="宋体", en="Consolas" if code else "Times New Roman", size=size, bold=bold, italic=italic)


def set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_border(parent, edge: str, val: str, size: int):
    borders = parent.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        parent.append(borders)
    node = borders.find(qn(f"w:{edge}"))
    if node is None:
        node = OxmlElement(f"w:{edge}")
        borders.append(node)
    node.set(qn("w:val"), val)
    node.set(qn("w:sz"), str(size))
    node.set(qn("w:space"), "0")
    node.set(qn("w:color"), "000000")


def add_three_line_table(doc, headers: list[str], rows: list[list[str]], caption: str = ""):
    if caption:
        p = doc.add_paragraph(style="Caption" if "Caption" in [s.name for s in doc.styles] else None)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(4)
        add_inline_markdown(p, caption, 10.5)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    usable_cm = 15.0
    weights = [max(2.0, min(12.0, len(re.sub(r"\*", "", h)))) for h in headers]
    total = sum(weights) or 1
    widths = [Cm(usable_cm * weight / total) for weight in weights]
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.width = widths[index]
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        add_inline_markdown(p, header, 10.5)
        for run in p.runs:
            run.bold = True
    for row in rows:
        cells = table.add_row().cells
        normalized = row + [""] * max(0, len(headers) - len(row))
        for index, value in enumerate(normalized[: len(headers)]):
            cell = cells[index]
            cell.width = widths[index]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if len(value) < 24 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.first_line_indent = Cm(0)
            add_inline_markdown(p, value, 10.5)
    tbl_pr = table._tbl.tblPr
    for edge in ("left", "right", "insideH", "insideV"):
        set_border(tbl_pr, edge, "nil", 0)
    set_border(tbl_pr, "top", "single", 12)
    set_border(tbl_pr, "bottom", "single", 12)
    for cell in table.rows[0].cells:
        tc_pr = cell._tc.get_or_add_tcPr()
        tc_borders = tc_pr.find(qn("w:tcBorders"))
        if tc_borders is None:
            tc_borders = OxmlElement("w:tcBorders")
            tc_pr.append(tc_borders)
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:color"), "000000")
        tc_borders.append(bottom)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(3)
    return table


def update_headers(doc: Document, title: str) -> None:
    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            if "[[PAPER_TITLE]]" in paragraph.text:
                paragraph.text = title
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Cm(0)
            for run in paragraph.runs:
                set_run_font(run, size=9)


def add_figure(doc, figure_path: Path, caption: str, figure_id: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run()
    inline_shape = run.add_picture(str(figure_path), width=Cm(14.5))
    marker = f"FORGE_FIGURE_{figure_id}"
    inline_shape._inline.docPr.set("name", marker)
    inline_shape._inline.docPr.set("descr", marker)
    cp = doc.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.first_line_indent = Cm(0)
    cp.paragraph_format.space_before = Pt(3)
    cp.paragraph_format.space_after = Pt(8)
    add_inline_markdown(cp, caption, 10.5)


def mark_equation(paragraph, sequence: int) -> None:
    """Add a non-printing Word bookmark so integrity checks can count equations."""
    bookmark_id = str(9000 + sequence)
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), bookmark_id)
    start.set(qn("w:name"), f"FORGE_EQUATION_{sequence}")
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), bookmark_id)
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def add_ai_compliance(doc, stats: dict) -> None:
    """2026 CUMCM AI-tool rule (in force 2026-09-01): a mandated AI-tool usage
    declaration must appear immediately BEFORE the references section.

    The declaration is the fixed official phrasing; the actual tool list,
    versions, prompting process and human review live in the supporting
    _AI工具使用详情.pdf_. References content is authored by the team.
    """
    declaration_heading = doc.add_paragraph(AI_DECLARATION_HEADING, style="Heading 1")
    stats["headings"] += 1
    declaration = doc.add_paragraph()
    declaration.paragraph_format.first_line_indent = Cm(0)
    add_inline_markdown(declaration, AI_DECLARATION_TEXT, 12)
    ref_heading = doc.add_paragraph(REFERENCES_HEADING, style="Heading 1")
    stats["headings"] += 1
    stats["paragraphs"] += 1


def compile_markdown(input_path: Path, output_path: Path, template_path: Path, contract_path: Path, figures_dir: Path | None = None) -> dict:
    if not template_path.is_file():
        raise FileNotFoundError(f"Reference template missing: {template_path}")
    with contract_path.open("r", encoding="utf-8") as stream:
        contract = json.load(stream)
    lines = input_path.read_text(encoding="utf-8").splitlines()
    doc = Document(template_path)
    clear_body(doc)
    title = next((line[2:].strip() for line in lines if line.startswith("# ") and not re.match(r"# \d+\s", line)), input_path.stem)
    update_headers(doc, title)
    title_p = doc.add_paragraph(style="Title")
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.first_line_indent = Cm(0)
    add_inline_markdown(title_p, title, 18)
    for run in title_p.runs:
        run.bold = True
        set_run_font(run, cn="黑体", size=18, bold=True)

    in_code = False
    skip_meta = False
    pending_caption = ""
    stats = {"paragraphs": 0, "tables": 0, "equations": 0, "headings": 0}
    inserted_figures: set[str] = set()
    compliance_inserted = False
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        if raw.startswith("# ") and raw[2:].strip() == title:
            i += 1
            continue
        if line.startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue
        heading_text = re.sub(r"^#{1,4}\s+", "", line)
        if heading_text == "附录" and not compliance_inserted:
            # Compliance structure: ... body -> AI declaration -> references -> appendix.
            add_ai_compliance(doc, stats)
            compliance_inserted = True
        if any(meta in heading_text for meta in META_HEADINGS):
            skip_meta = True
            i += 1
            continue
        if skip_meta:
            if line == "---":
                skip_meta = False
            i += 1
            continue
        if re.match(r"^\*\*(?:Claim|Evidence|Score|纸张状态)\*\*\s*[:：]", line, re.IGNORECASE):
            i += 1
            continue
        if line == "---" or not line:
            i += 1
            continue

        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            if len(block) >= 2:
                headers = [c.strip() for c in block[0].split("|")[1:-1]]
                start = 2 if "---" in block[1] else 1
                rows = [[c.strip() for c in row.split("|")[1:-1]] for row in block[start:]]
                if headers and rows:
                    add_three_line_table(doc, headers, rows, pending_caption)
                    pending_caption = ""
                    stats["tables"] += 1
            continue

        if line.startswith("$$"):
            equation_parts = [line[2:]]
            while not equation_parts[-1].endswith("$$") and i + 1 < len(lines):
                i += 1
                equation_parts.append(lines[i].strip())
            equation = " ".join(equation_parts)
            if not equation.endswith("$$"):
                raise ValueError('EQUATION_DELIMITER_UNCLOSED')
            equation = equation[:-2]
            tag = re.search(r"\\tag\{([^}]+)\}", equation)
            equation = re.sub(r"\\tag\{[^}]+\}", "", equation).strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(15), WD_TAB_ALIGNMENT.RIGHT)
            engine = contract.get('equation', {}).get('render_engine', 'omml')
            if engine != 'omml':
                raise ValueError('EQUATION_RENDER_ENGINE_UNSUPPORTED')
            p._p.append(polynomial_omml(equation))
            if tag:
                run = p.add_run(f"\t({tag.group(1)})")
                set_run_font(run, cn="Cambria Math", en="Cambria Math", size=11)
            stats["equations"] += 1
            mark_equation(p, stats["equations"])
            i += 1
            continue

        if line.startswith("#### "):
            p = doc.add_paragraph(line[5:].strip(), style="Heading 3")
            stats["headings"] += 1
        elif line.startswith("### "):
            p = doc.add_paragraph(line[4:].strip(), style="Heading 3")
            stats["headings"] += 1
        elif line.startswith("## "):
            text = line[3:].strip()
            p = doc.add_paragraph(text, style="Heading 2" if re.match(r"\d+\.\d+", text) else "Heading 1")
            stats["headings"] += 1
        elif line.startswith("# "):
            p = doc.add_paragraph(line[2:].strip(), style="Heading 1")
            if re.match(r"# \d+\s", line) and int(re.match(r"# (\d+)", line).group(1)) > 1:
                p.paragraph_format.page_break_before = True
            stats["headings"] += 1
        elif re.match(r"\*\*表\d", line):
            pending_caption = line.replace("**", "")
            i += 1
            continue
        elif re.match(r"\*\*图\d+-\d+", line):
            caption = line.replace("**", "")
            figure_id = re.search(r"图(\d+-\d+)", caption).group(1)
            figure_path = figures_dir / f"fig{figure_id}.png" if figures_dir else None
            if figure_id not in inserted_figures and figure_path and figure_path.is_file():
                add_figure(doc, figure_path, caption, figure_id)
                inserted_figures.add(figure_id)
            i += 1
            continue
        elif line.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            p.paragraph_format.first_line_indent = Cm(0)
            add_inline_markdown(p, line.lstrip("> "), 11)
            for run in p.runs:
                run.italic = True
            for figure_id in re.findall(r"图(\d+-\d+)", line):
                if figure_id in inserted_figures:
                    continue
                figure_path = figures_dir / f"fig{figure_id}.png" if figures_dir else None
                if figure_path and figure_path.is_file():
                    add_figure(doc, figure_path, f"图{figure_id}", figure_id)
                    inserted_figures.add(figure_id)
        elif re.match(r"^[-*]\s+", line):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.first_line_indent = Cm(0)
            add_inline_markdown(p, re.sub(r"^[-*]\s+", "", line), 12)
            stats["paragraphs"] += 1
        elif re.match(r"^\d+[.)、]\s*", line):
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.first_line_indent = Cm(0)
            add_inline_markdown(p, re.sub(r"^\d+[.)、]\s*", "", line), 12)
            stats["paragraphs"] += 1
        else:
            p = doc.add_paragraph()
            add_inline_markdown(p, line, 12)
            stats["paragraphs"] += 1
            for figure_id in re.findall(r"图(\d+-\d+)", line):
                if figure_id in inserted_figures:
                    continue
                figure_path = figures_dir / f"fig{figure_id}.png" if figures_dir else None
                if figure_path and figure_path.is_file():
                    add_figure(doc, figure_path, f"图{figure_id}", figure_id)
                    inserted_figures.add(figure_id)
        i += 1

    if not compliance_inserted:
        # No appendix section in the markdown: append compliance after the body.
        add_ai_compliance(doc, stats)

    template_sha = sha256_file(template_path)
    contract_sha = sha256_file(contract_path)
    doc.core_properties.title = title
    doc.core_properties.keywords = (
        f"template_file={template_path.name};template_sha256={template_sha};"
        f"style_contract_sha256={contract_sha}"
    )
    doc.core_properties.comments = "Generated by Forge template-bound compiler v1"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return {**stats, "figures": len(inserted_figures), "template_sha256": template_sha, "contract_sha256": contract_sha, "output": str(output_path.resolve())}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Markdown using an actual DOCX reference template")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--style-contract", required=True)
    parser.add_argument("--figures-dir")
    args = parser.parse_args()
    result = compile_markdown(Path(args.input), Path(args.output), Path(args.template), Path(args.style_contract), Path(args.figures_dir) if args.figures_dir else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
