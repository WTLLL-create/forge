"""Real computation/paper adversarial checks; only upstream model transport is fake."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import test_model_design as fixtures


class EvidencePaperTests(unittest.TestCase):
    def run_case(self, root, **kwargs):
        result, calls = fixtures.ModelDesignTests().workflow(
            root, formula_verification=True, quadratic=True, paper_candidate=True, **kwargs)
        self.assertEqual('READY_FOR_REVIEW', result['status'], result)
        self.assertEqual(3, len(calls), 'Paper composition must not make another model call')
        return result, Path(result['run_dir'])

    def active(self, run, kind):
        registry = json.loads((run / 'active_artifacts.json').read_text())
        return json.loads((run / registry['artifacts'][kind]['path']).read_text(encoding='utf-8'))

    def test_end_to_end_candidate_contains_bound_math_and_real_results(self):
        with tempfile.TemporaryDirectory() as raw:
            outcome, run = self.run_case(Path(raw), xlsx=True)
            graph = self.active(run, 'evidence_graph')
            spec = self.active(run, 'paper_spec')
            candidate = self.active(run, 'paper_candidate')
            self.assertEqual(['evidence_graph@1', 'paper_template@1'], spec['meta']['input_refs'])
            self.assertIn('model_result@1', graph['meta']['input_refs'])
            markdown = (run / 'artifacts/paper_candidate.md').read_text(encoding='utf-8')
            self.assertEqual(candidate['content']['markdown'], markdown)
            self.assertIn('$$', markdown)
            self.assertIn('PENDING', markdown)
            self.assertIn('minimizer', markdown)
            self.assertIn('source_row', markdown)
            self.assertNotIn('核桃油', markdown)
            self.assertEqual('PENDING', outcome['human_review'])
            self.assertEqual('PASS', json.loads((run / 'gates/evidence_paper.json').read_text())['status'])
            self.assertFalse((run / 'artifacts/published').exists())

    def test_input_changes_propagate_through_evidence_spec_and_markdown(self):
        results = []
        for data in (b'x,a\n3,1\n-1,2\n', b'x,a\n3,5\n-1,7\n'):
            with tempfile.TemporaryDirectory() as raw:
                _, run = self.run_case(Path(raw), quadratic_data=data)
                results.append([self.active(run, kind)['content'] for kind in
                                ('model_result', 'evidence_graph', 'paper_spec', 'paper_candidate')])
        for left, right in zip(*results):
            self.assertNotEqual(left, right)
        self.assertIn('| 1 | 1 | 1 | 1 | 0 |', results[0][-1]['markdown'])
        self.assertIn('| 1 | 1 | 5 | 5 | 0 |', results[1][-1]['markdown'])

    def test_edited_markdown_is_rejected(self):
        from core.runtime.evidence_paper import check_candidate
        with tempfile.TemporaryDirectory() as raw:
            outcome, run = self.run_case(Path(raw))
            path = run / 'artifacts/paper_candidate.md'
            path.write_text(path.read_text(encoding='utf-8') + '\n最优值为40%。\n', encoding='utf-8')
            self.assertEqual('FAIL', check_candidate(run, outcome['run_id'])['status'])

    def test_composer_drift_cannot_register_paper(self):
        from submission.schema import evidence_paper_spec as paper
        original = paper.compose
        def wrong(*args):
            spec = original(*args)
            spec['sections'][0]['blocks'].append({'type': 'text', 'text': '准确率40%'})
            return spec
        with tempfile.TemporaryDirectory() as raw, patch.object(paper, 'compose', side_effect=wrong):
            result, _ = fixtures.ModelDesignTests().workflow(
                Path(raw), formula_verification=True, quadratic=True, paper_candidate=True)
            self.assertNotEqual('READY_FOR_REVIEW', result['status'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text())
            self.assertNotIn('paper_candidate', registry['artifacts'])
            self.assertNotIn('paper_spec', registry['artifacts'])

    def test_graph_edit_and_foreign_run_are_rejected(self):
        from core.runtime.evidence_paper import validate_graph
        with tempfile.TemporaryDirectory() as raw:
            outcome, run = self.run_case(Path(raw))
            graph = self.active(run, 'evidence_graph')['content']
            for mutation in ('value', 'run', 'source', 'formula'):
                altered = copy.deepcopy(graph)
                if mutation == 'run': altered['run_id'] = 'old-run'
                elif mutation == 'source': altered['facts'][0]['source']['sha256'] = '0' * 64
                elif mutation == 'formula': altered['formulas'][0]['latex'] = '40'
                else: altered['facts'][0]['value'] = '40'
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    validate_graph(run, outcome['run_id'], altered)

    def test_replaced_input_blocks_existing_candidate(self):
        from core.runtime.evidence_paper import check_candidate
        with tempfile.TemporaryDirectory() as raw:
            outcome, run = self.run_case(Path(raw))
            next((run / 'inputs').glob('*.csv')).write_text('x,a\n3,99\n')
            self.assertEqual('FAIL', check_candidate(run, outcome['run_id'])['status'])

    def test_new_result_version_invalidates_old_evidence(self):
        from core.runtime.artifact_store import ArtifactStore
        from core.runtime.evidence_paper import check_candidate
        with tempfile.TemporaryDirectory() as raw:
            outcome, run = self.run_case(Path(raw))
            result = self.active(run, 'model_result')
            ArtifactStore(run, outcome['run_id']).register_json(
                artifact_type='model_result', version=2, content=result['content'], producer='test',
                input_refs=result['meta']['input_refs'], input_hashes=result['meta']['input_hashes'],
                supersedes=['model_result@1'])
            self.assertEqual('FAIL', check_candidate(run, outcome['run_id'])['status'])

    def test_candidate_requires_real_solve_and_boolean_flag(self):
        from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'workflow.json'
            base = {'schema': 'forge-problem-understanding/v1', 'problem_id': 'test',
                    'statement': 'statement.txt', 'model_design': True,
                    'provider': {'provider': 'codex', 'model': 'test-model'}}
            for value in ('true', True):
                path.write_text(json.dumps(dict(base, paper_candidate=value)))
                with self.assertRaisesRegex(ValueError, 'PAPER_CANDIDATE_'):
                    ProblemUnderstandingWorkflow(path)

    def test_forged_result_with_valid_new_hash_cannot_pass_replay(self):
        from core.runtime.artifact_store import ArtifactStore
        from core.runtime.evidence_paper import build_graph
        with tempfile.TemporaryDirectory() as raw:
            outcome, run = self.run_case(Path(raw))
            envelope = self.active(run, 'model_result')
            result = envelope['content']
            result['metrics']['scenarios'][0]['minimizer'] = '40'
            result['tables'][0]['rows'] = copy.deepcopy(result['metrics']['scenarios'])
            ArtifactStore(run, outcome['run_id']).register_json(
                artifact_type='model_result', version=2, content=result, producer='test',
                input_refs=envelope['meta']['input_refs'], input_hashes=envelope['meta']['input_hashes'],
                supersedes=['model_result@1'])
            with self.assertRaisesRegex(ValueError, 'EVIDENCE_REPLAY_MISMATCH'):
                build_graph(run, outcome['run_id'])

    def test_wrong_table_value_or_formula_fails_spec_validator(self):
        from submission.schema.evidence_paper_spec import validate_spec
        with tempfile.TemporaryDirectory() as raw:
            _, run = self.run_case(Path(raw))
            graph = self.active(run, 'evidence_graph')['content']
            template = self.active(run, 'paper_template')['content']
            for field in ('number', 'formula', 'omission', 'boolean'):
                spec = self.active(run, 'paper_spec')['content']
                results = next(s for s in spec['sections'] if s['kind'] == 'results')
                formulas = next(s for s in spec['sections'] if s['kind'] == 'formulas')
                if field == 'number': results['blocks'][0]['rows'][0][3]['value'] = '40'
                elif field == 'formula': formulas['blocks'][0]['latex'] = '40'
                elif field == 'boolean': results['blocks'][0]['rows'][0][0]['value'] = True
                else: results['blocks'][0]['rows'].pop()
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'PAPER_SPEC_EVIDENCE_MISMATCH'):
                    validate_spec(spec, graph, template)

    def test_stale_export_is_not_overwritten_on_retry(self):
        from core.runtime.evidence_paper import build_evidence_paper
        with tempfile.TemporaryDirectory() as raw:
            outcome, run = self.run_case(Path(raw))
            path = run / 'artifacts/paper_candidate.md'
            path.write_bytes(b'old artifact: 40%')
            retry = build_evidence_paper(run, outcome['run_id'])
            self.assertEqual('GATE_FAILED', retry['status'])
            self.assertEqual(b'old artifact: 40%', path.read_bytes())

    def test_candidate_identifies_run_and_template_snapshot(self):
        with tempfile.TemporaryDirectory() as raw:
            outcome, run = self.run_case(Path(raw))
            spec = self.active(run, 'paper_spec')['content']
            candidate = self.active(run, 'paper_candidate')['content']['markdown']
            self.assertIn(outcome['run_id'].replace('-', '\\-'), candidate)
            template = self.active(run, 'paper_template')
            package = self.active(run, 'problem_package')
            self.assertEqual(template['content'], package['content']['configuration']['paper_template'])
            self.assertEqual(['problem_package@1'], template['meta']['input_refs'])
            # Only checked math and controlled prose are rendered, not the LLM explanation field.
            self.assertNotIn('Squared deviation objective', candidate)
            self.assertEqual('DRAFT_SKELETON', spec['status'])


if __name__ == '__main__':
    unittest.main()
