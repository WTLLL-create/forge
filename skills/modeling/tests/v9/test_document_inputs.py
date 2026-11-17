"""Synthetic file fixtures: extraction engineering, not modeling acceptance."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.runtime.problem_package import create_package, verify_package
from core.runtime.data_profile import inspect_package, read_table
from core.schema.artifact_meta import ArtifactIntegrityError


class DocumentInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.statement = self.root / 'statement.txt'
        self.statement.write_text('Q1: Analyze the attachment.', encoding='utf-8')

    def pdf(self, blank=False):
        from reportlab.pdfgen.canvas import Canvas
        path = self.root / 'problem.pdf'
        canvas = Canvas(str(path))
        if not blank:
            canvas.drawString(40, 700, 'Q1: Rank the options.')
        canvas.showPage()
        canvas.save()
        return path

    def workbook(self):
        from openpyxl import Workbook
        path = self.root / 'data.xlsx'
        book = Workbook()
        sheet = book.active
        sheet.title = 'Measurements'
        sheet.append(['id', 'missing', 'zero', 'formula', 'flag'])
        sheet.append(['001', None, 0, '=C2+1', False])
        other = book.create_sheet('Notes')
        other['A1'] = 'Do not fill missing values'
        other.merge_cells('A1:B1')
        book.save(path)
        book.close()
        return path

    def package(self, statement=None, attachments=()):
        try:
            return create_package(self.root / 'run', 'r1', 'test', statement or self.statement, attachments)
        except ValueError as exc:
            self.fail('Valid document input rejected: ' + str(exc))

    def test_pdf_page_line_and_original_hash(self):
        path = self.pdf()
        p = self.package(path)
        asset = p['content']['assets'][0]
        self.assertEqual('Q1: Rank the options.', asset['segments']['P1:L1'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset['sha256'])
        self.assertEqual(1, asset['extraction']['page_count'])
        self.assertTrue(asset['extraction']['parser_version'])
        self.assertEqual('PENDING', asset['extraction']['visual_review'])

    def test_blank_pdf_blocked_not_empty_success(self):
        with self.assertRaisesRegex(ValueError, '^PDF_TEXT_UNAVAILABLE$'):
            create_package(self.root / 'run', 'r1', 'test', self.pdf(blank=True))

    def test_corrupt_pdf_has_safe_specific_error(self):
        path = self.root / 'bad.pdf'
        path.write_bytes(b'%PDF-not-a-document')
        with self.assertRaisesRegex(ValueError, '^PDF_PARSE_ERROR$'):
            create_package(self.root / 'run', 'r1', 'test', path)

    def test_missing_pdf_dependency_explicit(self):
        path = self.pdf()
        with patch.dict(sys.modules, {'pypdf': None}):
            with self.assertRaisesRegex(ValueError, '^PDF_DEPENDENCY_MISSING$'):
                create_package(self.root / 'run', 'r1', 'test', path)

    def test_xlsx_preserves_types_missing_formula_and_coordinates(self):
        path = self.workbook()
        original = path.read_bytes()
        p = self.package(attachments=[path])
        asset = p['content']['assets'][1]
        self.assertEqual('structured', asset['inspection'])
        cells = {c['coordinate']: c for c in asset['extraction']['sheets'][0]['cells']}
        self.assertIsNone(cells['B2']['value'])
        self.assertEqual('blank', cells['B2']['kind'])
        self.assertEqual(0, cells['C2']['value'])
        self.assertEqual('number', cells['C2']['kind'])
        self.assertEqual('001', cells['A2']['value'])
        self.assertEqual('=C2+1', cells['D2']['value'])
        self.assertEqual('formula', cells['D2']['kind'])
        self.assertIs(cells['E2']['value'], False)
        self.assertIn('S1!B2', asset['segments'])
        self.assertEqual(['A1:B1'], asset['extraction']['sheets'][1]['merged_ranges'])
        self.assertEqual(original, path.read_bytes())

    def test_xlsx_profile_not_solver_ready(self):
        p = self.package(attachments=[self.workbook()])
        profile = inspect_package(p, self.root / 'run', 'r1')
        asset = profile['content']['assets'][0]
        self.assertEqual('WORKBOOK_INSPECTED', asset['status'])
        self.assertFalse(asset['solver_ready'])
        self.assertEqual(1, asset['sheets'][0]['missing_count'])
        self.assertEqual(1, asset['sheets'][0]['formula_count'])
        with self.assertRaisesRegex(ValueError, 'DATA_FORMAT_UNSUPPORTED'):
            read_table(p, self.root / 'run', 'r1', 'attachment_1')

    def test_corrupt_workbook_blocked(self):
        path = self.root / 'bad.xlsx'
        path.write_bytes(b'not a zip')
        with self.assertRaisesRegex(ValueError, '^XLSX_PARSE_ERROR$'):
            create_package(self.root / 'run', 'r1', 'test', self.statement, [path])

    def test_workbook_dimension_limit_blocks_sparse_extreme_cell(self):
        from openpyxl import Workbook
        path = self.root / 'huge.xlsx'
        book = Workbook()
        book.active['XFD1048576'] = 1
        book.save(path)
        book.close()
        with self.assertRaisesRegex(ValueError, '^XLSX_SIZE_LIMIT$'):
            create_package(self.root / 'run', 'r1', 'test', self.statement, [path])

    def test_snapshot_tampering_rejected(self):
        p = self.package(attachments=[self.workbook()])
        (self.root / 'run/inputs/attachment_1.xlsx').write_bytes(b'tampered')
        with self.assertRaisesRegex(ArtifactIntegrityError, 'SNAPSHOT_HASH_MISMATCH'):
            verify_package(p, self.root / 'run', 'r1')

    def test_interpreter_receives_compact_typed_evidence_without_mutating_package(self):
        from core.runtime.problem_understanding import interpret
        p = self.package(attachments=[self.workbook()])
        original = json.dumps(p, sort_keys=True)
        class Capture:
            def generate_structured(self, **kwargs):
                return kwargs
        request = interpret(p, Capture())
        content = json.loads(request['prompt'].split('\n', 1)[1])
        asset = content['assets'][1]
        self.assertEqual('null', asset['segments']['S1!B2'])
        self.assertEqual('0', asset['segments']['S1!C2'])
        self.assertNotIn('cells', asset['extraction']['sheets'][0])
        self.assertEqual('formula', asset['extraction']['sheets'][0]['special_cell_types']['D2'])
        self.assertEqual(original, json.dumps(p, sort_keys=True))

    def test_workflow_exposes_parse_error_without_model_call(self):
        from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
        path = self.root / 'bad.pdf'
        path.write_bytes(b'%PDF-bad')
        config = self.root / 'workflow.json'
        config.write_text(json.dumps({'schema': 'forge-problem-understanding/v1', 'problem_id': 'x',
                          'statement': 'bad.pdf', 'provider': {'provider': 'codex', 'model': 'test-model'}}))
        def forbidden(*args, **kwargs):
            self.fail('Malformed document reached model transport')
        result = ProblemUnderstandingWorkflow(config).run(transport=forbidden)
        self.assertEqual('BLOCKED', result['status'])
        self.assertEqual('PDF_PARSE_ERROR', result['failure_code'])

    def test_missing_workbook_dependency_explicit(self):
        path = self.workbook()
        with patch.dict(sys.modules, {'openpyxl': None}):
            with self.assertRaisesRegex(ValueError, '^XLSX_DEPENDENCY_MISSING$'):
                create_package(self.root / 'run', 'r1', 'test', self.statement, [path])

    def test_mixed_pdf_does_not_silently_skip_blank_page(self):
        from reportlab.pdfgen.canvas import Canvas
        path = self.root / 'mixed.pdf'
        canvas = Canvas(str(path))
        canvas.drawString(30, 700, 'Q1: First page')
        canvas.showPage()
        canvas.showPage()
        canvas.save()
        with self.assertRaisesRegex(ValueError, '^PDF_TEXT_UNAVAILABLE$'):
            create_package(self.root / 'run', 'r1', 'test', path)


if __name__ == '__main__':
    unittest.main()
