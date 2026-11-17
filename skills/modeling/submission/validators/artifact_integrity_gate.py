"""Verify that declared paper artifacts are actually present in the DOCX."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from docx import Document

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result
from submission.schema.paper_spec import load_paper_spec


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def embedded_figure_hashes(doc: Document) -> tuple[dict[str, str], list[str]]:
    figures = {}
    errors = []
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-spec", required=True)
    parser.add_argument("--docx", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    spec = load_paper_spec(args.paper_spec)
    doc = Document(args.docx)
    checks = []
    def add(name, actual, expected):
        checks.append(gate_check(name, actual == expected, actual=actual, expected=expected))
    expected_counts = spec["expected_artifacts"]
    add("table count", len(doc.tables), expected_counts["tables"])
    add("figure count", len(doc.inline_shapes), expected_counts["figures"])
    expected_figure_markers = sorted(
        f"FORGE_FIGURE_{block['id']}"
        for section in spec["sections"]
        for block in section["blocks"]
        if block["type"] == "figure"
    )
    actual_figure_markers = sorted(
        shape._inline.docPr.get("descr", "")
        for shape in doc.inline_shapes
        if shape._inline.docPr.get("descr", "").startswith("FORGE_FIGURE_")
    )
    add("figure identities", actual_figure_markers, expected_figure_markers)
    expected_tables = [
        [block["headers"], *block["rows"]]
        for section in spec["sections"]
        for block in section["blocks"]
        if block["type"] in {"ranking_table", "parameter_table"}
    ]
    actual_tables = [[[cell.text for cell in row.cells] for row in table.rows] for table in doc.tables]
    add("table cell contents", actual_tables, expected_tables)
    artifact_root = Path(args.paper_spec).resolve().parent
    expected_hashes = {}
    path_errors = []
    for section in spec["sections"]:
        for block in section["blocks"]:
            if block["type"] != "figure":
                continue
            source = (artifact_root / block["path"]).resolve()
            try:
                source.relative_to(artifact_root)
                expected_hashes[block["id"]] = sha256_file(source)
            except Exception as exc:
                path_errors.append(f"{block.get('id')}: {exc}")
    actual_hashes, embedded_errors = embedded_figure_hashes(doc)
    checks.append(
        gate_check(
            "figure byte hashes",
            not path_errors and not embedded_errors and actual_hashes == expected_hashes,
            actual={"hashes": actual_hashes, "errors": path_errors + embedded_errors},
            expected=expected_hashes,
        )
    )
    equation_markers = sorted(
        node.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}name")
        for node in doc.element.body.iter()
        if node.tag.endswith("bookmarkStart")
        and (node.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}name") or "").startswith("FORGE_EQUATION_")
    )
    add("equation count", len(equation_markers), expected_counts["equations"])
    report = gate_result("artifact_integrity_gate", checks, run_id=args.run_id)
    report["artifacts"] = {"docx_sha256": sha256_file(Path(args.docx))}
    output = Path(args.report)
    write_gate_result(output, report)
    print(json.dumps({"gate": report["gate"], "status": report["status"], "report": str(output.resolve())}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
