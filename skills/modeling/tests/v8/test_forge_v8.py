from __future__ import annotations

import json
import base64
import socket
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm
from lxml import etree


MODELING_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = MODELING_ROOT.parents[1]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, validate_gate_result, write_gate_result
from core.schema.model_result import sha256_file, validate_model_result, write_model_result
from core.runtime.production_workflow import APPENDIX_DECLARATION
from submission.compilers.template_docx_compiler import compile_markdown
from submission.gates.publish_gate import run_publish_gate
from submission.gates.scientific_gate import run_scientific_gate
from submission.schema.build_paper_spec import build_paper_spec
from submission.schema.paper_spec import write_paper_spec
from submission.schema.render_paper_spec import render_markdown
from submission.validators.template_compliance_gate import run_gate as run_template_gate


TEMPLATE = MODELING_ROOT / "submission" / "templates" / "CUMCM_template.docx"
STYLE_CONTRACT = MODELING_ROOT / "submission" / "templates" / "cumcm_template.json"
PYTHON = Path(sys.executable)
TRUST_STAGE_IDS = [
    "model_compute",
    "build_paper_spec",
    "render_markdown",
    "compile_docx",
    "scientific_gate",
    "template_compliance_gate",
    "artifact_integrity_gate",
    "publish_gate",
]
REQUIRED_OUTPUTS = {
    "model_compute": ["artifacts/model_result.json"],
    "build_paper_spec": ["artifacts/paper_spec.json"],
    "render_markdown": ["artifacts/paper.md"],
    "compile_docx": ["artifacts/submission.docx"],
    "scientific_gate": ["gates/scientific_gate.json"],
    "template_compliance_gate": ["gates/template_compliance_gate.json"],
    "artifact_integrity_gate": ["gates/artifact_integrity_gate.json"],
    "publish_gate": ["artifacts/published/submission.docx", "gates/publish_gate.json"],
}
CANONICAL_SCRIPTS = {
    "build_paper_spec": MODELING_ROOT / "submission" / "schema" / "build_paper_spec.py",
    "render_markdown": MODELING_ROOT / "submission" / "schema" / "render_paper_spec.py",
    "compile_docx": MODELING_ROOT / "submission" / "compilers" / "template_docx_compiler.py",
    "scientific_gate": MODELING_ROOT / "submission" / "gates" / "scientific_gate.py",
    "template_compliance_gate": MODELING_ROOT / "submission" / "validators" / "template_compliance_gate.py",
    "artifact_integrity_gate": MODELING_ROOT / "submission" / "validators" / "artifact_integrity_gate.py",
    "publish_gate": MODELING_ROOT / "submission" / "gates" / "publish_gate.py",
}
CANONICAL_ARGS = {
    "model_compute": ["--run-id", "${RUN_ID}", "--problem-source", "${RUN_INPUTS}/source.txt", "--output", "${RUN_ARTIFACTS}/model_result.json"],
    "build_paper_spec": ["--model-result", "${RUN_ARTIFACTS}/model_result.json", "--output", "${RUN_ARTIFACTS}/paper_spec.json", "--appendix-material", APPENDIX_DECLARATION],
    "render_markdown": ["--paper-spec", "${RUN_ARTIFACTS}/paper_spec.json", "--model-result", "${RUN_ARTIFACTS}/model_result.json", "--output", "${RUN_ARTIFACTS}/paper.md"],
    "compile_docx": ["--input", "${RUN_ARTIFACTS}/paper.md", "--output", "${RUN_ARTIFACTS}/submission.docx", "--template", "${RUN_INPUTS}/template/CUMCM_template.docx", "--style-contract", "${RUN_INPUTS}/template/cumcm_template.json", "--figures-dir", "${RUN_ARTIFACTS}/figures"],
    "scientific_gate": ["--run-id", "${RUN_ID}", "--model-result", "${RUN_ARTIFACTS}/model_result.json", "--paper-spec", "${RUN_ARTIFACTS}/paper_spec.json", "--markdown", "${RUN_ARTIFACTS}/paper.md", "--docx", "${RUN_ARTIFACTS}/submission.docx", "--report", "${RUN_GATES}/scientific_gate.json"],
    "template_compliance_gate": ["--run-id", "${RUN_ID}", "--docx", "${RUN_ARTIFACTS}/submission.docx", "--template", "${RUN_INPUTS}/template/CUMCM_template.docx", "--style-contract", "${RUN_INPUTS}/template/cumcm_template.json", "--report", "${RUN_GATES}/template_compliance_gate.json"],
    "artifact_integrity_gate": ["--run-id", "${RUN_ID}", "--paper-spec", "${RUN_ARTIFACTS}/paper_spec.json", "--docx", "${RUN_ARTIFACTS}/submission.docx", "--report", "${RUN_GATES}/artifact_integrity_gate.json"],
    "publish_gate": ["--run-id", "${RUN_ID}", "--gate", "${RUN_GATES}/scientific_gate.json", "--gate", "${RUN_GATES}/template_compliance_gate.json", "--gate", "${RUN_GATES}/artifact_integrity_gate.json", "--gate", "${RUN_GATES}/ai_compliance_gate.json", "--gate", "${RUN_GATES}/number_freeze_gate.json", "--gate", "${RUN_GATES}/human_judgment_gate.json", "--gate", "${RUN_GATES}/aigc_audit_gate.json", "--gate", "${RUN_GATES}/writing_quality_gate.json", "--required-gate", "ai_compliance_gate", "--required-gate", "number_freeze_gate", "--required-gate", "human_judgment_gate", "--required-gate", "aigc_audit_gate", "--required-gate", "writing_quality_gate", "--source", "${RUN_ARTIFACTS}/submission.docx", "--output", "${RUN_ARTIFACTS}/published/submission.docx", "--report", "${RUN_GATES}/publish_gate.json"],
}
CANONICAL_REQUIRES = {
    "model_compute": ["inputs/source.txt"],
    "build_paper_spec": ["artifacts/model_result.json"],
    "render_markdown": ["artifacts/model_result.json", "artifacts/paper_spec.json"],
    "compile_docx": ["artifacts/paper.md", "inputs/template/CUMCM_template.docx", "inputs/template/cumcm_template.json"],
    "scientific_gate": ["artifacts/model_result.json", "artifacts/paper_spec.json", "artifacts/paper.md", "artifacts/submission.docx"],
    "template_compliance_gate": ["artifacts/submission.docx", "inputs/template/CUMCM_template.docx", "inputs/template/cumcm_template.json"],
    "artifact_integrity_gate": ["artifacts/paper_spec.json", "artifacts/submission.docx"],
    "publish_gate": ["gates/scientific_gate.json", "gates/template_compliance_gate.json", "gates/artifact_integrity_gate.json", "gates/ai_compliance_gate.json", "gates/number_freeze_gate.json", "gates/human_judgment_gate.json", "gates/aigc_audit_gate.json", "gates/writing_quality_gate.json", "artifacts/submission.docx"],
}


def make_trust_stages(model_script: Path) -> list[dict]:
    return [
        {
            "id": stage_id,
            "script": str(CANONICAL_SCRIPTS.get(stage_id, model_script)),
            "args": list(CANONICAL_ARGS[stage_id]),
            "requires": list(CANONICAL_REQUIRES[stage_id]),
            "produces": list(REQUIRED_OUTPUTS[stage_id]),
        }
        for stage_id in TRUST_STAGE_IDS
    ]


def make_model_result(run_id: str, weight: float = 0.25, aldehyde_pct: int = 18) -> dict:
    return {
        "schema": "forge-model-result/v1",
        "run_id": run_id,
        "problem_id": "fixture-problem",
        "model_version": "fixture-v1",
        "parameters": {"entropy_weights": {"indicator_a": weight, "indicator_b": 1 - weight}},
        "metrics": {
            "pca": {"n_samples": 2},
            "biomarkers": {"n_core": 1, "aldehyde_pct": aldehyde_pct},
            "evaluation": {
                "best_sample": "sample_a",
                "best_score": 0.8,
                "worst_sample": "sample_b",
                "worst_score": 0.2,
            },
            "sensitivity": {"rank_stability_pct": 100},
        },
        "diagnostics": {
            "sample_size": 2,
            "ranking_count": 2,
            "data_leakage": {"status": "NOT_APPLICABLE", "reason": "Deterministic scoring fixture."},
            "significance": {
                "status": "PASS",
                "method": "Kruskal-Wallis",
                "threshold": 0.05,
                "tests_executed": 1,
                "test_failures": 0,
                "min_p_value": 0.04,
                "max_p_value": 0.04,
            },
        },
        "tables": [],
        "figures": [],
        "rankings": [
            {"sample": "sample_a", "score": 0.8, "rank": 1, "grade": "优"},
            {"sample": "sample_b", "score": 0.2, "rank": 2, "grade": "差"},
        ],
        "claims": [
            {"id": "aldehyde", "source_path": "$.metrics.biomarkers.aldehyde_pct"},
            {"id": "weight", "source_path": "$.parameters.entropy_weights.indicator_a"},
        ],
    }


def build_paper(directory: Path, result: dict, name: str) -> tuple[Path, Path, Path]:
    model_path = directory / f"{name}_model_result.json"
    spec_path = directory / f"{name}_paper_spec.json"
    markdown_path = directory / f"{name}_paper.md"
    docx_path = directory / f"{name}_paper.docx"
    write_model_result(model_path, result)
    spec = build_paper_spec(result, model_path)
    write_paper_spec(spec_path, spec)
    markdown_path.write_text(render_markdown(spec), encoding="utf-8")
    compile_markdown(
        markdown_path,
        docx_path,
        TEMPLATE,
        STYLE_CONTRACT,
        directory / "figures" if result["figures"] else None,
    )
    return spec_path, markdown_path, docx_path


def docx_text(path: Path) -> str:
    document = Document(path)
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return "\n".join(paragraphs + cells)


class ForgeV8AcceptanceTests(unittest.TestCase):
    def test_legacy_paper_entrypoints_are_quarantined(self) -> None:
        """Break caught: fixed-path v7 paper generators remain callable beside production code."""
        legacy_names = {
            "clean_paper_compiler.py",
            "figure_equation_compiler.py",
            "hybrid_docx_compiler.py",
            "pdf_compiler.py",
            "table_compiler.py",
            "blind_benchmark.py",
            "paper_artifact_parser.py",
            "paper_compiler.py",
        }
        exposed = {
            path.name for folder in (
                MODELING_ROOT / "submission" / "compilers",
                MODELING_ROOT / "submission" / "validators",
                MODELING_ROOT / "submission" / "parsers",
                MODELING_ROOT / "core",
            ) for path in folder.glob("*.py")
        }
        self.assertTrue(legacy_names.isdisjoint(exposed))
        legacy_dir = MODELING_ROOT / "core" / "runtime" / "legacy"
        for name in legacy_names:
            path = legacy_dir / name
            self.assertTrue(path.is_file(), name)
            self.assertIn("NOT FOR PRODUCTION", path.read_text(encoding="utf-8")[:500])

    def test_parameter_change_propagates_to_model_spec_and_docx(self) -> None:
        """Break caught: paper remains unchanged after a model parameter changes."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            first = make_model_result("run-a", weight=0.25)
            second = make_model_result("run-b", weight=0.35)
            first_spec, _, first_docx = build_paper(directory, first, "first")
            second_spec, _, second_docx = build_paper(directory, second, "second")

            self.assertNotEqual(
                json.loads(first_spec.read_text(encoding="utf-8")),
                json.loads(second_spec.read_text(encoding="utf-8")),
            )
            first_text = docx_text(first_docx)
            second_text = docx_text(second_docx)
            self.assertIn("0.2500", first_text)
            self.assertIn("0.3500", second_text)
            self.assertNotEqual(first_docx.read_bytes(), second_docx.read_bytes())

    def test_false_paper_claim_fails_science_and_blocks_publish(self) -> None:
        """Break caught: a paper claim can drift from ModelResult and still publish."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-science", aldehyde_pct=18)
            spec_path, markdown_path, docx_path = build_paper(directory, result, "science")
            bad_markdown = markdown_path.read_text(encoding="utf-8").replace("18%", "40%")
            markdown_path.write_text(bad_markdown, encoding="utf-8")
            model_path = directory / "science_model_result.json"
            report = run_scientific_gate(model_path, spec_path, markdown_path, docx_path)
            self.assertEqual("FAIL", report["status"])
            science_report = directory / "scientific.json"
            template_report = directory / "template.json"
            artifact_report = directory / "artifact.json"
            write_gate_result(science_report, report)
            original_hash = sha256_file(docx_path)
            template_gate = gate_result("template_compliance_gate", [gate_check("fixture", True)], run_id="run-science")
            artifact_gate = gate_result("artifact_integrity_gate", [gate_check("fixture", True)], run_id="run-science")
            template_gate["artifacts"] = {"docx_sha256": original_hash}
            artifact_gate["artifacts"] = {"docx_sha256": original_hash}
            write_gate_result(template_report, template_gate)
            write_gate_result(artifact_report, artifact_gate)
            publish_target = directory / "published.docx"
            publish = run_publish_gate(
                "run-science",
                [science_report, template_report, artifact_report],
                docx_path,
                publish_target,
            )
            self.assertEqual("FAIL", publish["status"])
            self.assertFalse(publish_target.exists())

    def test_unbound_numeric_claim_inserted_into_docx_fails_science(self) -> None:
        """Break caught: an extra numeric conclusion is inserted after PaperSpec rendering."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-docx-drift", aldehyde_pct=18)
            spec_path, markdown_path, docx_path = build_paper(directory, result, "docx_drift")
            document = Document(docx_path)
            document.add_paragraph("未经来源绑定的错误占比为40%。")
            document.save(docx_path)
            report = run_scientific_gate(
                directory / "docx_drift_model_result.json",
                spec_path,
                markdown_path,
                docx_path,
            )
            self.assertEqual("FAIL", report["status"])

    def test_unbound_text_claim_inserted_into_docx_fails_science(self) -> None:
        """Break caught: an unsupported qualitative conclusion is inserted into the paper."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-text-drift")
            spec_path, markdown_path, docx_path = build_paper(directory, result, "text_drift")
            document = Document(docx_path)
            document.add_paragraph("未经模型结果支持的样本最优结论。")
            document.save(docx_path)
            report = run_scientific_gate(
                directory / "text_drift_model_result.json",
                spec_path,
                markdown_path,
                docx_path,
            )
            self.assertEqual("FAIL", report["status"])

    def test_document_changed_after_gates_cannot_publish(self) -> None:
        """Break caught: a document is altered after checks and still reaches publish."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-after-gates", aldehyde_pct=18)
            spec_path, markdown_path, docx_path = build_paper(directory, result, "after_gates")
            model_path = directory / "after_gates_model_result.json"
            science = run_scientific_gate(model_path, spec_path, markdown_path, docx_path)
            original_hash = sha256_file(docx_path)
            science["artifacts"] = {"docx_sha256": original_hash}
            reports = []
            for name, report in (
                ("scientific", science),
                ("template", gate_result("template_compliance_gate", [gate_check("fixture", True)], run_id="run-after-gates")),
                ("artifact", gate_result("artifact_integrity_gate", [gate_check("fixture", True)], run_id="run-after-gates")),
            ):
                report.setdefault("artifacts", {})["docx_sha256"] = original_hash
                path = directory / f"{name}.json"
                write_gate_result(path, report)
                reports.append(path)
            document = Document(docx_path)
            document.add_paragraph("tampered after gates")
            document.save(docx_path)
            target = directory / "published.docx"
            publish = run_publish_gate("run-after-gates", reports, docx_path, target)
            self.assertEqual("FAIL", publish["status"])
            self.assertFalse(target.exists())

    def test_gate_result_rejects_empty_or_self_inconsistent_pass(self) -> None:
        """Break caught: an empty or hand-edited GateResult is accepted as evidence."""
        with self.assertRaisesRegex(ValueError, "non-empty"):
            gate_result("empty_gate", [], run_id="run-gate")
        missing_run = {
            "schema": "forge-gate-result/v1",
            "run_id": "",
            "gate": "fake_gate",
            "status": "PASS",
            "checks": [{"name": "fake", "status": "PASS", "actual": None, "expected": None, "message": ""}],
            "errors": [],
        }
        with self.assertRaisesRegex(ValueError, "run_id"):
            validate_gate_result(missing_run)
        inconsistent = dict(missing_run, run_id="run-gate", status="FAIL")
        with self.assertRaisesRegex(ValueError, "derived"):
            validate_gate_result(inconsistent)

    def test_model_result_rejects_invalid_schema_weights_and_rankings(self) -> None:
        """Break caught: malformed scientific output is accepted as a ModelResult."""
        invalid_schema = make_model_result("run-schema")
        invalid_schema["schema"] = "not-forge"
        with self.assertRaisesRegex(ValueError, "schema"):
            validate_model_result(invalid_schema)
        invalid_weights = make_model_result("run-weights")
        invalid_weights["parameters"]["entropy_weights"] = {"a": 0.2, "b": 0.2}
        with self.assertRaisesRegex(ValueError, "sum"):
            validate_model_result(invalid_weights)
        duplicate_rank = make_model_result("run-rank")
        duplicate_rank["rankings"][1]["sample"] = "sample_a"
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_model_result(duplicate_rank)

    def test_docx_ranking_table_reorder_fails_science(self) -> None:
        """Break caught: table cells are reordered while PaperSpec remains untouched."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-table")
            spec_path, markdown_path, docx_path = build_paper(directory, result, "table")
            document = Document(docx_path)
            table = document.tables[0]
            first = [cell.text for cell in table.rows[1].cells]
            second = [cell.text for cell in table.rows[2].cells]
            for cell, value in zip(table.rows[1].cells, second):
                cell.text = value
            for cell, value in zip(table.rows[2].cells, first):
                cell.text = value
            document.save(docx_path)
            report = run_scientific_gate(directory / "table_model_result.json", spec_path, markdown_path, docx_path)
            self.assertEqual("FAIL", report["status"])

    def test_docx_figure_bytes_must_match_current_run_artifact(self) -> None:
        """Break caught: embedded image bytes change while the figure marker stays the same."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            figures = directory / "figures"
            figures.mkdir()
            original_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
            replacement_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII=")
            (figures / "fig2-1.png").write_bytes(original_png)
            result = make_model_result("run-figure")
            result["figures"] = [{"id": "2-1", "caption": "测试图", "path": "figures/fig2-1.png"}]
            spec_path, markdown_path, docx_path = build_paper(directory, result, "figure")
            document = Document(docx_path)
            blip = document.inline_shapes[0]._inline.xpath(".//a:blip")[0]
            image_part = document.part.related_parts[blip.get(qn("r:embed"))]
            image_part._blob = replacement_png
            document.save(docx_path)
            report = run_scientific_gate(directory / "figure_model_result.json", spec_path, markdown_path, docx_path)
            self.assertEqual("FAIL", report["status"])

    def test_template_gate_checks_every_section_and_complete_three_line_borders(self) -> None:
        """Break caught: later sections bypass page-layout validation."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-layout")
            _, _, docx_path = build_paper(directory, result, "layout")
            document = Document(docx_path)
            section = document.add_section(WD_SECTION.NEW_PAGE)
            section.page_width = Cm(20)
            document.save(docx_path)
            report = run_template_gate(docx_path, TEMPLATE, STYLE_CONTRACT, "run-layout")
            self.assertEqual("FAIL", report["status"])

    def test_template_gate_rejects_side_border_and_wrong_rule_width(self) -> None:
        """Break caught: a box border or wrong-width rule is treated as a three-line table."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-borders")
            _, _, docx_path = build_paper(directory, result, "borders")
            document = Document(docx_path)
            borders = document.tables[0]._tbl.tblPr.find(qn("w:tblBorders"))
            borders.find(qn("w:left")).set(qn("w:val"), "single")
            borders.find(qn("w:top")).set(qn("w:sz"), "2")
            document.save(docx_path)
            report = run_template_gate(docx_path, TEMPLATE, STYLE_CONTRACT, "run-borders")
            self.assertEqual("FAIL", report["status"])

    def test_scientific_gate_rejects_unbound_header_claim(self) -> None:
        """Break caught: a false numeric claim is hidden in a DOCX header."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-header")
            spec_path, markdown_path, docx_path = build_paper(directory, result, "header")
            document = Document(docx_path)
            document.sections[0].header.add_paragraph("错误结论：准确率40%")
            document.save(docx_path)
            report = run_scientific_gate(directory / "header_model_result.json", spec_path, markdown_path, docx_path)
            self.assertEqual("FAIL", report["status"])

    def test_scientific_gate_rejects_legacy_ooxml_drawing_container(self) -> None:
        """Break caught: namespace-specific OOXML containers bypass text extraction."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            tags = (
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pict",
                "{urn:schemas-microsoft-com:vml}textbox",
                "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}anchor",
                "{urn:schemas-microsoft-com:office:office}OLEObject",
            )
            for index, tag in enumerate(tags):
                with self.subTest(tag=tag):
                    result = make_model_result(f"run-ooxml-{index}")
                    name = f"ooxml_{index}"
                    spec_path, markdown_path, docx_path = build_paper(directory, result, name)
                    document = Document(docx_path)
                    document.paragraphs[0]._p.append(etree.Element(tag))
                    document.save(docx_path)
                    report = run_scientific_gate(directory / f"{name}_model_result.json", spec_path, markdown_path, docx_path)
                    self.assertEqual("FAIL", report["status"])

    def test_scientific_gate_rejects_standalone_vml_part(self) -> None:
        """Break caught: hidden VML stored in a .vml part is skipped by the OOXML scanner."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = make_model_result("run-vml-part")
            spec_path, markdown_path, docx_path = build_paper(directory, result, "vml_part")
            with zipfile.ZipFile(docx_path, "a") as archive:
                archive.writestr(
                    "word/drawings/vmlDrawing1.vml",
                    '<xml xmlns:v="urn:schemas-microsoft-com:vml"><v:shape/></xml>',
                )
            report = run_scientific_gate(directory / "vml_part_model_result.json", spec_path, markdown_path, docx_path)
            self.assertEqual("FAIL", report["status"])

    def test_executor_without_config_is_a_hard_error(self) -> None:
        """Break caught: missing --config silently enters a legacy or default workflow."""
        executor = MODELING_ROOT / "core" / "runtime" / "workflow_executor.py"
        process = subprocess.run([str(PYTHON), str(executor)], text=True, capture_output=True)
        self.assertNotEqual(0, process.returncode)
        self.assertIn("--config", process.stderr)
        self.assertNotIn("PASSED", process.stdout + process.stderr)

    def test_copied_old_artifact_fails_freshness_gate(self) -> None:
        """Break caught: an artifact copied into a new run is accepted as stage output."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            script = project / "stage.py"
            script.write_text("raise SystemExit('stage must not run when output already exists')\n", encoding="utf-8")
            stages = make_trust_stages(script)
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "freshness-fixture",
                "runtime_root": "runtime/runs",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            config_path = project / "workflow.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            workflow = ProductionWorkflow(config_path, python_executable=PYTHON)
            workflow.prepare()
            old = project / "old_model_result.json"
            old.write_text('{"stale": true}', encoding="utf-8")
            copied = workflow.current_run / "artifacts" / "model_result.json"
            copied.write_bytes(old.read_bytes())
            outcome = workflow.run_prepared()
            self.assertEqual("FAIL", outcome["status"])
            freshness = json.loads((outcome["run_dir"] / "gates" / "freshness_model_compute.json").read_text(encoding="utf-8"))
            self.assertEqual("FAIL", freshness["status"])

    def test_stage_arguments_cannot_point_outside_current_run(self) -> None:
        """Break caught: declared requires are safe but a canonical gate reads an old absolute path."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            stages = make_trust_stages(model_script)
            old_docx = project / "old.docx"
            old_docx.write_bytes(b"old")
            science = next(stage for stage in stages if stage["id"] == "scientific_gate")
            science["args"] = ["--docx", str(old_docx)]
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "argument-escape",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside current run"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_joined_stage_argument_cannot_hide_old_artifact_path(self) -> None:
        """Break caught: --flag=absolute-path bypasses current-run path validation."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            old_docx = project / "old.docx"
            old_docx.write_bytes(b"old")
            stages = make_trust_stages(model_script)
            next(stage for stage in stages if stage["id"] == "scientific_gate")["args"] = [
                f"--docx={old_docx}"
            ]
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "joined-argument-escape",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "flag/value pairs"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_unknown_path_flag_cannot_read_project_file(self) -> None:
        """Break caught: a custom stage hides an old file behind an unknown CLI flag."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            (project / "old.json").write_text('{"old": true}', encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            stages = make_trust_stages(model_script)
            next(stage for stage in stages if stage["id"] == "model_compute")["args"] = [
                "--old-input", "old.json"
            ]
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "unknown-path-flag",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside current run"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_trust_gate_cannot_substitute_alternate_current_run_docx(self) -> None:
        """Break caught: a canonical gate validates an alternate in-run paper instead of compiler output."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            stages = make_trust_stages(model_script)
            science = next(stage for stage in stages if stage["id"] == "scientific_gate")
            science["args"][science["args"].index("--docx") + 1] = "${RUN_ARTIFACTS}/alternate.docx"
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "alternate-trust-chain",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical argument binding"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_trust_stage_rejects_unconsumed_requires_and_extra_produces(self) -> None:
        """Break caught: trust-stage declarations contain files not bound to canonical arguments."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            stages = make_trust_stages(model_script)
            science = next(stage for stage in stages if stage["id"] == "scientific_gate")
            science["requires"].append("artifacts/alternate.docx")
            science["produces"].append("gates/alternate.json")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "extra-trust-paths",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "argument-bound"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_trust_stage_rejects_output_argument_missing_from_produces(self) -> None:
        """Break caught: a trust stage writes an alternate output that the manifest never registers."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            stages = make_trust_stages(model_script)
            model = next(stage for stage in stages if stage["id"] == "model_compute")
            model["args"].extend(["--report", "${RUN_GATES}/alternate.json"])
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "unregistered-output-arg",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "output arguments"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_trust_stage_rejects_open_output_directory(self) -> None:
        """Break caught: an output directory can hide files omitted from produces."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            stages = make_trust_stages(model_script)
            model = next(stage for stage in stages if stage["id"] == "model_compute")
            model["args"].extend(["--output-dir", "${RUN_ARTIFACTS}"])
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "open-output-directory",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "output arguments"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_input_kind_cannot_cross_target_namespace(self) -> None:
        """Break caught: source data is relabelled as the active template inside current_run inputs."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("not a template", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "role-crossing",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "template/CUMCM_template.docx"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "target namespace"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_trust_stage_run_id_must_use_current_run_token(self) -> None:
        """Break caught: a gate is allowed to attest a fake run id."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            source = project / "source_inputs" / "source.txt"
            source.parent.mkdir()
            source.write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            stages = make_trust_stages(model_script)
            next(stage for stage in stages if stage["id"] == "publish_gate")["args"] = ["--run-id", "fake"]
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "fake-run-id",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "RUN_ID"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_derived_project_output_cannot_be_declared_as_input(self) -> None:
        """Break caught: project results are relabeled as current-run source inputs."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            results = project / "results"
            results.mkdir()
            (results / "old.json").write_text('{"old": true}', encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "old-input",
                "inputs": [{"kind": "source", "source": "results/old.json", "target": "old.json"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "derived-output"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_arbitrary_project_file_cannot_be_relabelled_as_source_input(self) -> None:
        """Break caught: a derived artifact avoids a denylist by using an innocent filename."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "innocent.json").write_text('{"old": true}', encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "relabeled-output",
                "inputs": [{"kind": "source", "source": "innocent.json", "target": "old.json"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "approved source directory"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_concurrent_run_cannot_take_over_current_run(self) -> None:
        """Break caught: a second executor renames an active current_run and writes into it."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "concurrency",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            first = ProductionWorkflow(path, python_executable=PYTHON)
            first.prepare()
            second = ProductionWorkflow(path, python_executable=PYTHON)
            with self.assertRaisesRegex(RuntimeError, "active run"):
                second.prepare()

    def test_dead_same_host_lock_is_quarantined_and_run_can_recover(self) -> None:
        """Break caught: a crashed executor leaves a permanent production deadlock."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "stale-lock",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            runtime_root = project / "runtime" / "runs"
            runtime_root.mkdir(parents=True)
            (runtime_root / ".active_run.lock").write_text(
                json.dumps({"pid": 99999999, "host": socket.gethostname()}), encoding="utf-8"
            )
            workflow = ProductionWorkflow(path, python_executable=PYTHON)
            workflow.prepare()
            self.assertTrue(workflow.current_run.is_dir())
            self.assertTrue(any(runtime_root.glob(".stale-lock-*")))
            workflow._release_lock()

    def test_stage_cannot_modify_registered_input(self) -> None:
        """Break caught: a stage mutates an input after its original hash was recorded."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("original", encoding="utf-8")
            model_script = project / "mutate.py"
            model_script.write_text(
                "import os\nfrom pathlib import Path\n"
                "Path(os.environ['FORGE_RUN_INPUTS'], 'source.txt').write_text('changed', encoding='utf-8')\n"
                "Path(os.environ['FORGE_RUN_ARTIFACTS'], 'model_result.json').write_text('{}', encoding='utf-8')\n",
                encoding="utf-8",
            )
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "input-mutation",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            workflow = ProductionWorkflow(path, python_executable=PYTHON)
            outcome = workflow.run()
            self.assertEqual("FAIL", outcome["status"])
            integrity = json.loads((outcome["run_dir"] / "gates" / "run_integrity.json").read_text(encoding="utf-8"))
            self.assertEqual("FAIL", integrity["status"])

    def test_model_compute_cannot_register_malformed_result_as_fresh(self) -> None:
        """Break caught: a fresh file with the right name is accepted without ModelResult validation."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            model_script = project / "malformed.py"
            model_script.write_text(
                "import os\nfrom pathlib import Path\n"
                "Path(os.environ['FORGE_RUN_ARTIFACTS'], 'model_result.json').write_text('{}', encoding='utf-8')\n",
                encoding="utf-8",
            )
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "malformed-model-result",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            outcome = ProductionWorkflow(path, python_executable=PYTHON).run()
            self.assertEqual("FAIL", outcome["status"])
            manifest = json.loads(Path(outcome["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual("model_compute", manifest["stages"][0]["stage"])
            self.assertEqual("FAIL", manifest["stages"][0]["status"])
            freshness = json.loads(
                (Path(outcome["run_dir"]) / "gates" / "freshness_model_compute.json").read_text(encoding="utf-8")
            )
            self.assertEqual("FAIL", freshness["status"])

    def test_configured_script_hash_change_is_detected_before_execution(self) -> None:
        """Break caught: a stage script changes after workflow validation but keeps the trusted path."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('original')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "script-integrity",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            workflow = ProductionWorkflow(path, python_executable=PYTHON)
            model_script.write_text("print('replaced')\n", encoding="utf-8")
            outcome = workflow.run()
            self.assertEqual("FAIL", outcome["status"])
            code_gate = json.loads((Path(outcome["run_dir"]) / "gates" / "code_integrity.json").read_text(encoding="utf-8"))
            self.assertEqual("FAIL", code_gate["status"])

    def test_new_shadow_module_in_stage_directory_is_detected(self) -> None:
        """Break caught: a new sibling module shadows imports without changing an attested script."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "new-shadow-module",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            workflow = ProductionWorkflow(path, python_executable=PYTHON)
            (project / "docx.py").write_text("raise RuntimeError('shadowed')\n", encoding="utf-8")
            outcome = workflow.run()
            code_gate = json.loads((Path(outcome["run_dir"]) / "gates" / "code_integrity.json").read_text(encoding="utf-8"))
            self.assertEqual("FAIL", code_gate["status"])

    def test_new_sourceless_shadow_module_is_detected(self) -> None:
        """Break caught: a new .pyc/.pyd-style module bypasses the .py-only code inventory."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "sourceless-shadow-module",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            workflow = ProductionWorkflow(path, python_executable=PYTHON)
            (project / "docx.pyc").write_bytes(b"untrusted bytecode")
            outcome = workflow.run()
            code_gate = json.loads((Path(outcome["run_dir"]) / "gates" / "code_integrity.json").read_text(encoding="utf-8"))
            self.assertEqual("FAIL", code_gate["status"])

    def test_workflow_config_change_is_detected_after_validation(self) -> None:
        """Break caught: manifest attests a config different from the in-memory config being executed."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "config-integrity",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            workflow = ProductionWorkflow(path, python_executable=PYTHON)
            config["workflow_id"] = "replaced-after-validation"
            path.write_text(json.dumps(config), encoding="utf-8")
            outcome = workflow.run()
            code_gate = json.loads((Path(outcome["run_dir"]) / "gates" / "code_integrity.json").read_text(encoding="utf-8"))
            self.assertEqual("FAIL", code_gate["status"])

    def test_trust_stages_ignore_configured_python_shadow_path(self) -> None:
        """Break caught: configured PYTHONPATH shadows modules imported by canonical gates."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            shadow = project / "shadow_packages"
            (shadow / "docx").mkdir(parents=True)
            (shadow / "docx" / "__init__.py").write_text("raise RuntimeError('shadowed')\n", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "python-shadow",
                "python_paths": ["shadow_packages"],
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": make_trust_stages(model_script),
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            workflow = ProductionWorkflow(path, python_executable=PYTHON)
            trust_path = workflow._stage_environment("scientific_gate").get("PYTHONPATH", "")
            compute_path = workflow._stage_environment("fixture_compute").get("PYTHONPATH", "")
            self.assertNotIn(str(shadow.resolve()), trust_path)
            self.assertIn(str(shadow.resolve()), compute_path)

    def test_unsafe_stage_id_is_rejected_before_paths_are_created(self) -> None:
        """Break caught: stage id path traversal escapes logs or gate filenames."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            model_script = project / "model.py"
            model_script.write_text("print('model')\n", encoding="utf-8")
            stages = make_trust_stages(model_script)
            stages.insert(0, {"id": "../escape", "script": str(model_script), "args": [], "requires": ["inputs/source.txt"], "produces": ["artifacts/escape.txt"]})
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "unsafe-stage-id",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "safe slug"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_incomplete_v2_workflow_is_rejected_before_execution(self) -> None:
        """Break caught: a v2 config omits binding or publish gates and still runs."""
        from core.runtime.production_workflow import ProductionWorkflow

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            (project / "stage.py").write_text("print('should not run')\n", encoding="utf-8")
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "incomplete-fixture",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": [
                    {
                        "id": "model_compute",
                        "script": "stage.py",
                        "requires": ["inputs/source.txt"],
                        "produces": ["artifacts/model_result.json"],
                    }
                ],
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "trust chain"):
                ProductionWorkflow(path, python_executable=PYTHON)
            self.assertFalse((project / "runtime" / "runs" / "current_run").exists())

    def test_trust_gate_ids_cannot_point_to_fake_pass_scripts(self) -> None:
        """Break caught: a config labels a placeholder script as a required gate."""
        from core.runtime.production_workflow import ProductionWorkflow, TRUST_CHAIN_OUTPUTS

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "source_inputs").mkdir()
            (project / "source_inputs" / "source.txt").write_text("input", encoding="utf-8")
            (project / "fake_pass.py").write_text("print('PASS')\n", encoding="utf-8")
            stages = [
                {
                    "id": stage_id,
                    "script": "fake_pass.py",
                    "requires": ["inputs/source.txt"],
                    "produces": sorted(outputs),
                }
                for stage_id, outputs in TRUST_CHAIN_OUTPUTS.items()
            ]
            config = {
                "schema": "forge-project-workflow/v2",
                "workflow_id": "fake-gates",
                "inputs": [{"kind": "source", "source": "source_inputs/source.txt", "target": "source.txt"}],
                "stages": stages,
            }
            path = project / "workflow.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical script"):
                ProductionWorkflow(path, python_executable=PYTHON)

    def test_reference_workflow_publishes_only_from_isolated_bound_run(self) -> None:
        """Break caught: the reference workflow bypasses run isolation or source-bound gates."""
        config = WORKSPACE_ROOT / "projects" / "forge_v7_3_d2026" / "workflow.json"
        executor = MODELING_ROOT / "core" / "runtime" / "workflow_executor.py"
        with tempfile.TemporaryDirectory() as raw:
            process = subprocess.run(
                [str(PYTHON), str(executor), "--config", str(config), "--runtime-root", raw],
                text=True,
                capture_output=True,
                timeout=300,
            )
            self.assertEqual(0, process.returncode, process.stdout + process.stderr)
            outcome = json.loads(process.stdout)
            self.assertEqual("PASS", outcome["status"])
            run_dir = Path(outcome["run_dir"])
            self.assertNotEqual("current_run", run_dir.name)
            self.assertTrue(run_dir.resolve().is_relative_to(Path(raw).resolve()),
                            "reference run must stay inside the isolated runtime root")
            self.assertTrue((run_dir / "artifacts" / "model_result.json").is_file())
            self.assertTrue((run_dir / "artifacts" / "paper_spec.json").is_file())
            self.assertTrue((run_dir / "artifacts" / "published" / "submission.docx").is_file())
            for gate_name in ("scientific_gate", "template_compliance_gate", "artifact_integrity_gate", "publish_gate"):
                report = json.loads((run_dir / "gates" / f"{gate_name}.json").read_text(encoding="utf-8"))
                self.assertEqual("PASS", report["status"], report)
                self.assertEqual(outcome["run_id"], report["run_id"])
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("PASS", manifest["status"])
            self.assertTrue(all(stage["status"] == "PASS" for stage in manifest["stages"]))
            input_hashes = {item["path"]: item["sha256"] for item in manifest["inputs"]}
            self.assertIn("inputs/task_data/problem.docx", input_hashes)
            model_result = json.loads((run_dir / "artifacts" / "model_result.json").read_text(encoding="utf-8"))
            self.assertEqual(
                input_hashes["inputs/task_data/problem.docx"],
                model_result["diagnostics"]["source_problem"]["sha256"],
            )
            significance = model_result["diagnostics"]["significance"]
            self.assertEqual("PASS", significance["status"])
            self.assertGreater(significance["tests_executed"], 0)
            self.assertEqual(0, significance["test_failures"])
            self.assertGreaterEqual(significance["min_p_value"], 0)
            self.assertLessEqual(significance["max_p_value"], 1)


if __name__ == "__main__":
    unittest.main()
