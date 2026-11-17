"""WF-01/02: real DOCX with synthetic upstream model responses; isolated runs."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
import test_model_design as fixtures
from core.runtime.docx_candidate import build_docx_candidate, check_docx_candidate
from submission.compilers import bound_docx


class TableAcceptanceTests(unittest.TestCase):
    def workflow(self, root):
        return fixtures.ModelDesignTests().workflow(root, formula_verification=True,
            quadratic=True, paper_candidate=True, docx_candidate=True)[0]

    def test_run_saves_locked_spec_and_hash_bound_checks(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.workflow(Path(raw))
            self.assertEqual('READY_FOR_REVIEW', result['status'], result)
            run = Path(result['run_dir'])
            spec = json.loads((run / 'table_spec.json').read_text(encoding='utf-8'))
            self.assertEqual('locked', spec['status'])
            self.assertEqual(3, len(spec['tables']))
            self.assertEqual(3, spec['tables'][1]['columns'][2]['digits'])
            checks = (run / 'table_checks.md').read_text(encoding='utf-8')
            self.assertIn('PASS', checks)
            self.assertIn('PENDING', checks)
            self.assertIn('sha256', checks)
            doc = Document(run / 'artifacts/paper_candidate.docx')
            self.assertEqual('1.000', doc.tables[1].cell(1, 2).text)
            report = json.loads((run / 'gates/table_checks.json').read_text(encoding='utf-8'))
            self.assertEqual(hashlib.sha256((run / 'artifacts/paper_candidate.docx').read_bytes()).hexdigest(), report['docx_sha256'])
            self.assertEqual('READY_FOR_REVIEW', build_docx_candidate(run, result['run_id'])['status'])

    def test_spec_tampering_or_removal_is_not_adopted_on_retry(self):
        for mutation in ('digits', 'remove'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as raw:
                result = self.workflow(Path(raw))
                run = Path(result['run_dir'])
                path = run / 'table_spec.json'
                self.assertTrue(path.exists())
                if mutation == 'remove':
                    path.unlink()
                else:
                    spec = json.loads(path.read_text(encoding='utf-8'))
                    spec['tables'][1]['columns'][2]['digits'] = 1
                    path.write_text(json.dumps(spec), encoding='utf-8')
                self.assertEqual('FAIL', check_docx_candidate(run, result['run_id'])['status'])
                self.assertNotEqual('READY_FOR_REVIEW', build_docx_candidate(run, result['run_id'])['status'])
                if mutation == 'remove': self.assertFalse(path.exists())

    def test_shared_generator_faults_fail_even_when_regeneration_matches(self):
        original = bound_docx._table
        for mutation in ('font', 'border', 'precision', 'alignment', 'shading', 'header', 'width', 'bold', 'caption', 'note', 'row_count', 'indent', 'scale', 'caption_font', 'border_theme', 'border_space', 'keep_next'):
            def faulty(doc, *args, **kwargs):
                original(doc, *args, **kwargs)
                table = doc.tables[-1]
                cell = table.cell(1, 0)
                if mutation == 'font': cell.paragraphs[0].runs[0].font.size = Pt(7)
                elif mutation == 'border':
                    table._tbl.tblPr.find(qn('w:tblBorders')).find(qn('w:top')).set(qn('w:sz'), '2')
                elif mutation == 'precision':
                    if len(doc.tables) == 2: table.cell(1, 2).paragraphs[0].runs[0].text = '1.0'
                elif mutation == 'alignment': cell.paragraphs[0].alignment = 1
                elif mutation == 'shading':
                    shade = OxmlElement('w:shd'); shade.set(qn('w:fill'), 'FF0000')
                    cell._tc.get_or_add_tcPr().append(shade)
                elif mutation == 'header':
                    trpr = table.rows[0]._tr.get_or_add_trPr()
                    trpr.remove(trpr.find(qn('w:tblHeader')))
                elif mutation == 'width': table.columns[0].width = 100
                elif mutation == 'bold': cell.paragraphs[0].runs[0].bold = True
                elif mutation == 'caption': table._tbl.getprevious().find(qn('w:r')).find(qn('w:t')).text = 'wrong'
                elif mutation == 'note': table._tbl.getnext().find(qn('w:r')).find(qn('w:t')).text = 'wrong'
                elif mutation == 'indent': cell.paragraphs[0].paragraph_format.left_indent = Pt(90)
                elif mutation == 'scale':
                    scale = OxmlElement('w:w'); scale.set(qn('w:val'), '5')
                    cell.paragraphs[0].runs[0]._r.get_or_add_rPr().append(scale)
                elif mutation == 'caption_font':
                    run = table._tbl.getprevious().find(qn('w:r'))
                    rp = OxmlElement('w:rPr'); sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '6')
                    rp.append(sz); run.insert(0, rp)
                elif mutation in ('border_theme', 'border_space'):
                    border = table._tbl.tblPr.find(qn('w:tblBorders')).find(qn('w:top'))
                    border.set(qn('w:themeColor') if mutation == 'border_theme' else qn('w:space'),
                               'accent2' if mutation == 'border_theme' else '31')
                elif mutation == 'keep_next':
                    table.cell(0, 0).paragraphs[0].paragraph_format.keep_with_next = False
                else: table.add_row()
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as raw:
                with patch.object(bound_docx, '_table', side_effect=faulty):
                    result = self.workflow(Path(raw))
                self.assertNotEqual('READY_FOR_REVIEW', result['status'], result)
                run = Path(result['run_dir'])
                self.assertTrue((run / 'table_spec.json').exists())
                self.assertIn('FAIL', (run / 'table_checks.md').read_text(encoding='utf-8'))
                report = json.loads((run / 'gates/table_checks.json').read_text(encoding='utf-8'))
                self.assertTrue(any(not c['passed'] and c['code'].startswith('TABLE_') for c in report['checks']), report)
                self.assertFalse((run / 'artifacts/paper_candidate.docx').exists())

    def test_independent_inspector_never_calls_renderer(self):
        from submission.validation.docx_tables import inspect_tables
        with tempfile.TemporaryDirectory() as raw:
            result = self.workflow(Path(raw))
            run = Path(result['run_dir'])
            spec = json.loads((run / 'table_spec.json').read_text(encoding='utf-8'))
            data = (run / 'artifacts/paper_candidate.docx').read_bytes()
            with patch.object(bound_docx, 'render_docx', side_effect=AssertionError('shared renderer')):
                report = inspect_tables(data, spec)
            self.assertEqual('PASS', report['status'], report)

    def test_fraction_rounding_and_nonzero_precision_loss(self):
        from submission.schema.academic_tables import display_value
        from submission.validation.docx_tables import _expected
        column = {'kind': 'number', 'digits': 3, 'missing': '—'}
        for raw, text in [('1/3', '0.333'), ('-1/3', '-0.333'), ('2469/2000', '1.234'),
                          ('2471/2000', '1.236'), ('0', '0.000'), (None, '—')]:
            with self.subTest(value=raw):
                self.assertEqual(text, display_value(raw, column))
                self.assertEqual(text, _expected(raw, column))
        with self.assertRaises(ValueError): display_value('1/100000', column)
        with self.assertRaises(ValueError): _expected('1/100000', column)

    def test_producer_formatter_bug_is_independently_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            with patch.object(bound_docx, 'display_value', return_value='wrong'):
                result = self.workflow(Path(raw))
            self.assertEqual('BLOCKED', result['status'], result)
            report = json.loads((Path(result['run_dir']) / 'gates/table_checks.json').read_text(encoding='utf-8'))
            self.assertTrue(any(c['code'].endswith(':VALUE') and not c['passed'] for c in report['checks']))

    def test_corrupted_check_record_cannot_prevent_failure_recording(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.workflow(Path(raw))
            run = Path(result['run_dir'])
            (run / 'table_spec.json').write_text('{}', encoding='utf-8')
            (run / 'gates/table_checks.json').write_text('{"checks":null}', encoding='utf-8')
            self.assertEqual('FAIL', check_docx_candidate(run, result['run_id'])['status'])
            self.assertEqual('FAIL', json.loads((run / 'gates/docx_candidate.json').read_text(encoding='utf-8'))['status'])

    def test_result_fields_project_by_name_not_position(self):
        # Upstream header/row reordering must not silently swap table columns.
        from copy import deepcopy
        from submission.schema.academic_tables import build_table_spec
        from core.runtime.artifact_store import ArtifactStore
        from core.runtime.evidence_paper import _active
        with tempfile.TemporaryDirectory() as raw:
            result = self.workflow(Path(raw))
            run = Path(result['run_dir'])
            store = ArtifactStore(run, result['run_id'])
            paper = _active(store, 'paper_spec')['content']
            snapshot = _active(store, 'problem_package')['content']['configuration']['docx_template']
            baseline = build_table_spec(paper, snapshot)
            results = next(s for s in paper['sections'] if s['kind'] == 'results')['blocks'][0]
            # Swap minimizer (3) and minimum (4) in BOTH headers and every row.
            reordered = deepcopy(paper)
            block = next(s for s in reordered['sections'] if s['kind'] == 'results')['blocks'][0]
            block['headers'][3], block['headers'][4] = block['headers'][4], block['headers'][3]
            for row in block['rows']:
                row[3], row[4] = row[4], row[3]
            projected = build_table_spec(reordered, snapshot)
            self.assertEqual(baseline['tables'][1]['rows'], projected['tables'][1]['rows'])
            self.assertEqual(baseline['tables'][2]['rows'], projected['tables'][2]['rows'])
            # A dropped/renamed result field fails closed instead of mis-projecting.
            for mutation in ('drop', 'rename'):
                broken = deepcopy(paper)
                block = next(s for s in broken['sections'] if s['kind'] == 'results')['blocks'][0]
                if mutation == 'drop':
                    block['headers'].pop()
                    for row in block['rows']: row.pop()
                else:
                    block['headers'][3] = 'unknown_field'
                with self.subTest(mutation=mutation):
                    with self.assertRaises(ValueError):
                        build_table_spec(broken, snapshot)
            self.assertEqual(results['headers'][3], 'minimizer')

    def test_unsupported_paper_profile_is_rejected_at_spec_build(self):
        from submission.schema.academic_tables import build_table_spec
        with self.assertRaises(ValueError):
            build_table_spec({'schema': 'other', 'status': 'DRAFT_SKELETON', 'sections': []},
                             {'contract': {'page': {'margin': {'left': '2.5cm', 'right': '2.5cm'}}}})


if __name__ == '__main__': unittest.main()
