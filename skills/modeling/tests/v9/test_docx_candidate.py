"""Current-run Word export tests; model responses are synthetic, rendering is real."""
import copy
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from docx import Document
from core.runtime.docx_candidate import check_docx_candidate, build_docx_candidate
from submission.compilers.bound_docx import validate_docx, package_parts, decode_snapshot
import test_model_design as fixtures


class DocxCandidateTests(unittest.TestCase):
    def run_case(self, root, **kwargs):
        result, calls = fixtures.ModelDesignTests().workflow(root, formula_verification=True,
            quadratic=True, paper_candidate=True, docx_candidate=True, **kwargs)
        self.assertEqual('READY_FOR_REVIEW', result['status'], result)
        self.assertEqual(3, len(calls))
        self.assertTrue(all('"base64"' not in call['prompt'] for call in calls))
        run = Path(result['run_dir'])
        registry = json.loads((run / 'active_artifacts.json').read_text())
        def active(kind):
            return json.loads((run / registry['artifacts'][kind]['path']).read_text(encoding='utf-8'))
        spec = active('paper_spec')['content']
        snapshot = active('problem_package')['content']['configuration']['docx_template']
        return result, run, spec, snapshot

    def test_real_docx_has_native_math_tables_template_and_pending_review(self):
        with tempfile.TemporaryDirectory() as raw:
            result, run, spec, snapshot = self.run_case(Path(raw), xlsx=True)
            data = (run / result['docx_candidate']).read_bytes()
            metrics = validate_docx(data, spec, snapshot)
            self.assertEqual(2, metrics['formula_count'])
            self.assertEqual(3, metrics['table_count'])
            doc = Document(BytesIO(data))
            self.assertEqual('1.000', doc.tables[1].cell(1, 2).text)
            self.assertEqual('2', doc.tables[2].cell(1, 1).text, 'Original Excel row, not reindexed row')
            self.assertEqual(result['run_id'], doc.core_properties.identifier)
            self.assertEqual('PENDING', result['visual_review'])
            self.assertFalse((run / 'artifacts/published').exists())
            old, new = package_parts(decode_snapshot(snapshot)), package_parts(data)
            for part in ('word/styles.xml', 'word/numbering.xml', 'word/footer1.xml'):
                self.assertEqual(old[part], new[part])

    def test_input_changes_reach_word_numbers(self):
        values = []
        for data in (b'x,a\n3,0.3\n-1,2.75\n', b'x,a\n3,5\n-1,7\n'):
            with tempfile.TemporaryDirectory() as raw:
                result, run, _, _ = self.run_case(Path(raw), quadratic_data=data)
                doc = Document(run / result['docx_candidate'])
                values.append([doc.tables[1].cell(i, 2).text for i in (1, 2)])
        self.assertEqual([['0.300', '2.750'], ['5.000', '7.000']], values)

    def test_word_text_number_formula_and_margin_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            result, run, spec, snapshot = self.run_case(Path(raw))
            original = (run / result['docx_candidate']).read_bytes()
            for mutation in ('number', 'formula', 'text', 'margin', 'footer'):
                doc = Document(BytesIO(original))
                if mutation == 'number': doc.tables[1].cell(1, 2).text = '40'
                elif mutation == 'formula': doc._element.xpath('.//m:oMath//m:t')[0].text = '40'
                elif mutation == 'text': doc.add_paragraph('准确率达到40%')
                elif mutation == 'footer': doc.sections[0].footer.paragraphs[0].text = '40%'
                else: doc.sections[0].left_margin = 100
                buffer = BytesIO()
                doc.save(buffer)
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'DOCX_CONTENT_OR_TEMPLATE_DRIFT'):
                    validate_docx(buffer.getvalue(), spec, snapshot)

    def test_tampered_export_fails_gate_and_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as raw:
            result, run, _, _ = self.run_case(Path(raw))
            path = run / result['docx_candidate']
            doc = Document(path)
            doc.tables[1].cell(1, 2).text = '40'
            doc.save(path)
            before = path.read_bytes()
            self.assertEqual('FAIL', check_docx_candidate(run, result['run_id'])['status'])
            self.assertNotEqual('READY_FOR_REVIEW', build_docx_candidate(run, result['run_id'])['status'])
            self.assertEqual(before, path.read_bytes())

    def test_template_hash_and_current_input_are_checked(self):
        with tempfile.TemporaryDirectory() as raw:
            result, run, spec, snapshot = self.run_case(Path(raw))
            bad = copy.deepcopy(snapshot)
            bad['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'DOCX_TEMPLATE_HASH_MISMATCH'):
                validate_docx((run / result['docx_candidate']).read_bytes(), spec, bad)
            next((run / 'inputs').glob('*.csv')).write_text('x,a\n1,40\n')
            self.assertEqual('FAIL', check_docx_candidate(run, result['run_id'])['status'])

    def test_foreign_run_word_is_rejected(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            a, first, _, _ = self.run_case(Path(one))
            b, second, _, _ = self.run_case(Path(two))
            (second / b['docx_candidate']).write_bytes((first / a['docx_candidate']).read_bytes())
            self.assertEqual('FAIL', check_docx_candidate(second, b['run_id'])['status'])

    def test_docx_flag_requires_boolean_and_paper_stage(self):
        from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'config.json'
            for value in ('true', True):
                path.write_text(json.dumps({'schema': 'forge-problem-understanding/v1', 'problem_id': 'x',
                    'statement': 'x.txt', 'docx_candidate': value, 'provider': {'provider': 'codex', 'model': 'test-model'}}))
                with self.assertRaisesRegex(ValueError, 'DOCX_CANDIDATE_'):
                    ProblemUnderstandingWorkflow(path)


if __name__ == '__main__':
    unittest.main()
