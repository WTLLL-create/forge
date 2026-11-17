"""Evidence-bound paper skeleton tests; upstream model responses are synthetic fixtures."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import test_model_design as fixtures


class FullPaperSkeletonTests(unittest.TestCase):
    def run_case(self, root, *, docx=False):
        outcome, calls = fixtures.ModelDesignTests().workflow(
            root, formula_verification=True, quadratic=True,
            paper_candidate=True, docx_candidate=docx)
        self.assertEqual('READY_FOR_REVIEW', outcome['status'], outcome)
        self.assertEqual(3, len(calls), 'Paper skeleton must not request another model response')
        run = Path(outcome['run_dir'])
        registry = json.loads((run / 'active_artifacts.json').read_text())
        def active(kind):
            return json.loads((run / registry['artifacts'][kind]['path']).read_text(encoding='utf-8'))
        return outcome, run, active

    def test_skeleton_covers_problem_model_assumptions_math_results_and_limits(self):
        with tempfile.TemporaryDirectory() as raw:
            _, run, active = self.run_case(Path(raw))
            graph = active('evidence_graph')['content']
            spec = active('paper_spec')['content']
            self.assertEqual('quadratic-paper-skeleton/v2', graph['scope'])
            self.assertEqual('DRAFT_SKELETON', spec['status'])
            self.assertEqual(['problem', 'model_design', 'formulas', 'results', 'review'],
                             [section['kind'] for section in spec['sections']])
            markdown = (run / 'artifacts/paper_candidate.md').read_text(encoding='utf-8')
            for expected in ('Minimize squared deviation', 'Find a minimizer', 'A minimizer',
                             'Squared loss', 'Task explicitly asks for squared deviation',
                             'Scalar unconstrained setting only', 'x and a are real scalars',
                             'Check the derivative and objective near the solution',
                             'Does not match the requested squared loss',
                             'PENDING'):
                self.assertIn(expected, markdown)
            model_section = next(
                section for section in spec['sections']
                if section['kind'] == 'model_design'
            )
            self.assertEqual(
                'pre_computation',
                model_section['blocks'][0]['binding']['value'],
            )
            review_section = next(
                section for section in spec['sections']
                if section['kind'] == 'review'
            )
            ambiguity = next(
                block for block in review_section['blocks']
                if block['type'] == 'ambiguity'
            )
            self.assertEqual('DATA_ROLE', ambiguity['id']['value'])
            self.assertNotIn('"description"', markdown)
            self.assertLess(markdown.index('预计算模型方案'), markdown.index('求解结果'))

    def test_every_paper_value_binding_resolves_to_graph_fact(self):
        from core.schema.artifact_meta import content_sha256
        with tempfile.TemporaryDirectory() as raw:
            _, _, active = self.run_case(Path(raw))
            graph = active('evidence_graph')['content']
            spec = active('paper_spec')['content']
            facts = {fact['id']: fact for fact in graph['facts']}
            seen = set()
            def visit(value):
                if isinstance(value, dict):
                    if set(value) == {'evidence_ref', 'value'}:
                        fact = facts[value['evidence_ref']]
                        self.assertEqual(content_sha256(fact['value']), content_sha256(value['value']))
                        seen.add(value['evidence_ref'])
                    else:
                        for child in value.values(): visit(child)
                elif isinstance(value, list):
                    for child in value: visit(child)
            visit(spec['sections'])
            self.assertTrue(seen)
            self.assertTrue(set(spec['required_evidence_refs']) <= seen)

    def test_unbound_or_changed_narrative_and_omitted_question_fail(self):
        from submission.schema.evidence_paper_spec import validate_spec, template_contract
        with tempfile.TemporaryDirectory() as raw:
            _, _, active = self.run_case(Path(raw))
            graph = active('evidence_graph')['content']
            template = template_contract()
            for mutation in ('invented', 'rationale', 'omission', 'phase'):
                spec = copy.deepcopy(active('paper_spec')['content'])
                if mutation == 'invented':
                    spec['sections'][1]['blocks'].append({'type': 'text', 'text': '模型准确率为95.2%'})
                elif mutation == 'rationale':
                    spec['sections'][1]['blocks'][1]['rationale']['value'] = 'Results proved it best'
                elif mutation == 'phase':
                    spec['sections'][1]['blocks'][0]['binding']['value'] = 'after_results'
                else:
                    spec['sections'][0]['blocks'].pop()
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'PAPER_SPEC_EVIDENCE_MISMATCH'):
                    validate_spec(spec, graph, template)

    def test_problem_and_model_source_tampering_invalidates_graph(self):
        from core.runtime.evidence_paper import validate_graph
        with tempfile.TemporaryDirectory() as raw:
            outcome, run, active = self.run_case(Path(raw))
            graph = active('evidence_graph')['content']
            for kind in ('problem', 'model', 'assumption', 'validation'):
                altered = copy.deepcopy(graph)
                ref = altered[kind + 's'][0]['ref'] if kind != 'problem' else altered['problems'][0]['task_ref']
                next(f for f in altered['facts'] if f['id'] == ref)['value'] = 'forged 40%'
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    validate_graph(run, outcome['run_id'], altered)

    def test_docx_contains_bound_skeleton_sections_without_a_new_model_call(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as raw:
            outcome, run, _ = self.run_case(Path(raw), docx=True)
            doc = Document(run / outcome['docx_candidate'])
            text = '\n'.join(paragraph.text for paragraph in doc.paragraphs)
            for expected in ('问题与任务', '预计算模型方案', 'Squared loss',
                             '模型假设', '公式与符号', '求解结果', '模型局限',
                             '待确认事项 DATA_ROLE'):
                self.assertIn(expected, text)
            self.assertNotIn('"description"', text)
            self.assertNotIn('95.2%', text)
            with zipfile.ZipFile(run / outcome['docx_candidate']) as package:
                document_xml = package.read('word/document.xml').decode('utf-8')
            self.assertIn('w:type="page"', document_xml)


if __name__ == '__main__':
    unittest.main()
