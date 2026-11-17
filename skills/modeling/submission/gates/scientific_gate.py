"""Forge v8 scientific consistency gate for ModelResult -> PaperSpec -> paper."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from docx import Document

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result
from core.schema.model_result import json_path_get, load_model_result, sha256_file
from submission.schema.paper_spec import load_paper_spec, render_bound_text, validate_paper_spec
from submission.schema.render_paper_spec import render_markdown
from submission.compilers.template_docx_compiler import (
    AI_DECLARATION_HEADING,
    AI_DECLARATION_TEXT,
    REFERENCES_HEADING,
)

# Fixed paragraphs the template compiler emits as the 2026 AI-compliance
# structure (declaration before references, both before the appendix).
COMPLIANCE_PARAGRAPHS = [AI_DECLARATION_HEADING, AI_DECLARATION_TEXT, REFERENCES_HEADING]

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
VML_NS = "urn:schemas-microsoft-com:vml"
OFFICE_NS = "urn:schemas-microsoft-com:office:office"
WPS_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
FORBIDDEN_OOXML_TAGS = {
    f"{{{W_NS}}}txbxContent",
    f"{{{W_NS}}}pict",
    f"{{{W_NS}}}object",
    f"{{{W_NS}}}altChunk",
    f"{{{W_NS}}}commentReference",
    f"{{{W_NS}}}footnoteReference",
    f"{{{W_NS}}}endnoteReference",
    f"{{{WP_NS}}}anchor",
    f"{{{VML_NS}}}textbox",
    f"{{{VML_NS}}}shape",
    f"{{{OFFICE_NS}}}OLEObject",
    f"{{{WPS_NS}}}txbx",
}


def iter_numeric_metrics(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_numeric_metrics(child, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield prefix, float(value)


def embedded_figure_hashes(doc: Document) -> tuple[dict[str, str], list[str]]:
    figures: dict[str, str] = {}
    errors: list[str] = []
    for shape in doc.inline_shapes:
        marker = shape._inline.docPr.get("descr", "")
        if not marker.startswith("FORGE_FIGURE_"):
            continue
        figure_id = marker.removeprefix("FORGE_FIGURE_")
        try:
            blip = shape._inline.xpath(".//a:blip")[0]
            relationship_id = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            blob = doc.part.related_parts[relationship_id].blob
            if figure_id in figures:
                errors.append(f"duplicate figure marker {figure_id}")
            figures[figure_id] = hashlib.sha256(blob).hexdigest()
        except Exception as exc:
            errors.append(f"{figure_id}: {exc}")
    return figures, errors


def run_scientific_gate(
    model_result_path: Path,
    paper_spec_path: Path,
    markdown_path: Path,
    docx_path: Path,
    expected_run_id: str | None = None,
) -> dict:
    checks = []
    run_id_hint = expected_run_id or ""
    try:
        if not run_id_hint:
            raw_result = json.loads(model_result_path.read_text(encoding="utf-8"))
            run_id_hint = str(raw_result.get("run_id", ""))
        result = load_model_result(model_result_path, expected_run_id or None)
        spec = load_paper_spec(paper_spec_path)
        validate_paper_spec(spec, result, model_result_path)
        checks.append(gate_check("schema and provenance", True, actual=spec["run_id"], expected=result["run_id"]))
    except Exception as exc:
        return gate_result(
            "scientific_gate",
            [gate_check("schema and provenance", False, message=str(exc))],
            run_id=run_id_hint or "UNKNOWN-RUN",
        )

    markdown = markdown_path.read_text(encoding="utf-8")
    expected_markdown = render_markdown(spec)
    checks.append(gate_check("PaperSpec controls Markdown", markdown == expected_markdown, actual="exact" if markdown == expected_markdown else "drift", expected="exact", message="Markdown differs from deterministic PaperSpec rendering"))

    doc = Document(docx_path)
    body_text = (
        [p.text for p in doc.paragraphs]
        + [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
    )
    header_text = []
    footer_text = []
    header_tables = []
    footer_tables = []
    for section in doc.sections:
        header_text.extend(p.text for p in section.header.paragraphs)
        footer_text.extend(p.text for p in section.footer.paragraphs)
        header_tables.extend(
            cell.text for table in section.header.tables for row in table.rows for cell in row.cells
        )
        footer_tables.extend(
            cell.text for table in section.footer.tables for row in table.rows for cell in row.cells
        )
    doc_text = "\n".join(body_text + header_text + footer_text + header_tables + footer_tables)

    header_failures = []
    for index, section in enumerate(doc.sections, 1):
        visible = [p.text for p in section.header.paragraphs if p.text.strip()]
        table_values = [cell.text for table in section.header.tables for row in table.rows for cell in row.cells if cell.text.strip()]
        if visible != [spec["title"]] or table_values:
            header_failures.append({"section": index, "paragraphs": visible, "table_cells": table_values})
    visible_footer = [text for text in footer_text + footer_tables if text.strip()]
    checks.append(
        gate_check(
            "DOCX headers and footers contain only bound content",
            not header_failures and not visible_footer,
            actual={"header_failures": header_failures, "visible_footer": visible_footer},
            expected={"headers": [spec["title"]], "visible_footer": []},
        )
    )

    forbidden_parts = []
    forbidden_markup = []
    with zipfile.ZipFile(docx_path) as archive:
        names = set(archive.namelist())
        forbidden_parts = sorted(
            name for name in names
            if name.startswith("word/")
            and any(token in Path(name).name.lower() for token in ("comment", "footnote", "endnote"))
        )
        for name in sorted(
            n for n in names
            if n.startswith("word/") and Path(n).suffix.lower() in {".xml", ".vml"}
        ):
            try:
                root = ET.fromstring(archive.read(name))
            except ET.ParseError as exc:
                forbidden_markup.append(f"{name}:invalid-xml:{exc}")
                continue
            found = sorted({element.tag for element in root.iter() if element.tag in FORBIDDEN_OOXML_TAGS})
            forbidden_markup.extend(f"{name}:{tag}" for tag in found)
        content_types = ET.fromstring(archive.read("[Content_Types].xml"))
        for element in content_types:
            content_type = str(element.attrib.get("ContentType", "")).lower()
            part_name = str(element.attrib.get("PartName", ""))
            if any(token in content_type for token in ("comments", "footnotes", "endnotes")):
                forbidden_parts.append(part_name or content_type)
        forbidden_parts = sorted(set(forbidden_parts))
    checks.append(
        gate_check(
            "DOCX has no unbound auxiliary story or floating content",
            not forbidden_parts and not forbidden_markup,
            actual={"parts": forbidden_parts, "markup": forbidden_markup},
            expected={"parts": [], "markup": []},
        )
    )
    bound_failures = []
    for section in spec["sections"]:
        for block in section["blocks"]:
            if block["type"] != "bound_text":
                continue
            expected = render_bound_text(block, result)
            if block.get("claim") != expected or expected not in markdown or expected not in doc_text:
                bound_failures.append(block.get("id", "unknown"))
    checks.append(gate_check("numeric claims match ModelResult", not bound_failures, actual=bound_failures, expected=[], message="A paper claim does not match its ModelResult source"))

    ranking_blocks = [block for section in spec["sections"] for block in section["blocks"] if block["type"] == "ranking_table"]
    expected_rank_rows = [[item["sample"], f"{item['score']:.4f}", str(item["rank"]), item["grade"]] for item in result["rankings"]]
    ranking_ok = len(ranking_blocks) == 1 and ranking_blocks[0].get("rows") == expected_rank_rows
    checks.append(gate_check("ranking consistency", ranking_ok, actual=ranking_blocks[0].get("rows") if ranking_blocks else None, expected=expected_rank_rows, message="Paper ranking differs from ModelResult.rankings"))

    parameter_blocks = [block for section in spec["sections"] for block in section["blocks"] if block["type"] == "parameter_table"]
    expected_parameters = [[name, f"{float(value):.4f}"] for name, value in sorted(result["parameters"]["entropy_weights"].items())]
    parameter_ok = len(parameter_blocks) == 1 and parameter_blocks[0].get("rows") == expected_parameters
    checks.append(gate_check("parameter consistency", parameter_ok, actual=parameter_blocks[0].get("rows") if parameter_blocks else None, expected=expected_parameters, message="Paper parameters differ from ModelResult.parameters"))

    expected_docx_tables = [
        [block["headers"], *block["rows"]]
        for section in spec["sections"]
        for block in section["blocks"]
        if block["type"] in {"ranking_table", "parameter_table"}
    ]
    actual_docx_tables = [
        [[cell.text for cell in row.cells] for row in table.rows]
        for table in doc.tables
    ]
    checks.append(gate_check("DOCX table cells match PaperSpec", actual_docx_tables == expected_docx_tables, actual=actual_docx_tables, expected=expected_docx_tables))

    expected_paragraphs = [spec["title"]]
    has_appendix = any(section.get("id") == "appendix" for section in spec["sections"])
    for section in spec["sections"]:
        if section.get("id") == "appendix":
            # The compiler inserts declaration + references immediately before the appendix.
            expected_paragraphs.extend(COMPLIANCE_PARAGRAPHS)
        expected_paragraphs.append(section["title"])
        for block in section["blocks"]:
            if block["type"] == "bound_text":
                expected_paragraphs.append(block["claim"])
            elif block["type"] == "static_text":
                expected_paragraphs.append(block["text"])
            elif block["type"] == "figure":
                expected_paragraphs.append(f"图{block['id']} {block['caption']}")
    if not has_appendix:
        # The compiler appends declaration + references after the body.
        expected_paragraphs.extend(COMPLIANCE_PARAGRAPHS)
    actual_paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
    checks.append(
        gate_check(
            "DOCX paragraph content matches PaperSpec",
            actual_paragraphs == expected_paragraphs,
            actual=actual_paragraphs,
            expected=expected_paragraphs,
        )
    )

    expected_figure_hashes = {}
    figure_path_errors = []
    artifact_root = model_result_path.parent.resolve()
    for figure in result["figures"]:
        source = (artifact_root / figure["path"]).resolve()
        try:
            source.relative_to(artifact_root)
            expected_figure_hashes[figure["id"]] = sha256_file(source)
        except Exception as exc:
            figure_path_errors.append(f"{figure.get('id')}: {exc}")
    actual_figure_hashes, embedded_errors = embedded_figure_hashes(doc)
    figure_errors = figure_path_errors + embedded_errors
    checks.append(
        gate_check(
            "DOCX figure bytes match current-run artifacts",
            not figure_errors and actual_figure_hashes == expected_figure_hashes,
            actual={"hashes": actual_figure_hashes, "errors": figure_errors},
            expected=expected_figure_hashes,
        )
    )

    rankings = result["rankings"]
    ranks = [item["rank"] for item in rankings]
    scores = [item["score"] for item in rankings]
    ranking_valid = ranks == list(range(1, len(rankings) + 1)) and all(scores[index] >= scores[index + 1] for index in range(len(scores) - 1))
    checks.append(gate_check("ranking order is valid", ranking_valid, actual=ranks, expected=list(range(1, len(rankings) + 1))))

    sample_size = result["diagnostics"].get("sample_size")
    ranking_count = result["diagnostics"].get("ranking_count")
    checks.append(gate_check("sample size consistency", isinstance(sample_size, int) and sample_size > 1 and sample_size == ranking_count == len(rankings), actual={"sample_size": sample_size, "ranking_count": ranking_count, "rows": len(rankings)}, expected="same positive count"))

    range_errors = []
    for path, value in iter_numeric_metrics(result["metrics"]):
        key = path.lower()
        if not math.isfinite(value):
            range_errors.append(f"{path}=non-finite")
        elif any(token in key for token in ("score", "spearman", "kendall", "ari_")) and not -1 <= value <= 1:
            range_errors.append(f"{path}={value}")
        elif (key.endswith("pct") or key.endswith("_pct")) and not 0 <= value <= 100:
            range_errors.append(f"{path}={value}")
        elif "p_value" in key and not 0 <= value <= 1:
            range_errors.append(f"{path}={value}")
    checks.append(gate_check("metric ranges", not range_errors, actual=range_errors, expected=[]))

    leakage = result["diagnostics"].get("data_leakage", {})
    leakage_ok = leakage.get("status") in {"PASS", "NOT_APPLICABLE"} and bool(leakage.get("reason"))
    checks.append(gate_check("data leakage assessment", leakage_ok, actual=leakage, expected="PASS or NOT_APPLICABLE with reason"))

    significance = result["diagnostics"].get("significance", {})
    significance_ok = (
        significance.get("status") == "PASS"
        and significance.get("method") == "Kruskal-Wallis"
        and isinstance(significance.get("tests_executed"), int)
        and significance["tests_executed"] > 0
        and significance.get("test_failures") == 0
        and isinstance(significance.get("threshold"), (int, float))
        and 0 < significance["threshold"] < 1
        and isinstance(significance.get("min_p_value"), (int, float))
        and isinstance(significance.get("max_p_value"), (int, float))
        and 0 <= significance["min_p_value"] <= significance["max_p_value"] <= 1
    )
    checks.append(gate_check("statistical significance assessment", significance_ok, actual=significance, expected="executed Kruskal-Wallis tests with valid p-values and no failures"))

    static_numeric = []
    for section in spec["sections"]:
        for block in section["blocks"]:
            if block["type"] == "static_text" and re.search(r"\d", block.get("text", "")):
                static_numeric.append(block.get("id", "unknown"))
    checks.append(gate_check("no unbound numeric prose", not static_numeric, actual=static_numeric, expected=[]))
    numeric_pattern = re.compile(r"(?<![0-9A-Za-z_])[-+]?\d+(?:\.\d+)?(?:[%％])?")
    expected_numbers = Counter(numeric_pattern.findall(expected_markdown))
    actual_numbers = Counter(numeric_pattern.findall(doc_text))
    unbound_numbers = {
        token: count - expected_numbers[token]
        for token, count in actual_numbers.items()
        if count > expected_numbers[token]
    }
    checks.append(gate_check("DOCX numeric content derives from PaperSpec", not unbound_numbers, actual=unbound_numbers, expected={}))
    report = gate_result("scientific_gate", checks, run_id=result["run_id"])
    report["artifacts"] = {
        "model_result_sha256": sha256_file(model_result_path),
        "paper_spec_sha256": sha256_file(paper_spec_path),
        "markdown_sha256": sha256_file(markdown_path),
        "docx_sha256": sha256_file(docx_path),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-result", required=True)
    parser.add_argument("--paper-spec", required=True)
    parser.add_argument("--markdown", required=True)
    parser.add_argument("--docx", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = run_scientific_gate(Path(args.model_result), Path(args.paper_spec), Path(args.markdown), Path(args.docx), args.run_id)
    write_gate_result(args.report, result)
    print(json.dumps({"gate": result["gate"], "status": result["status"], "report": str(Path(args.report).resolve())}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
