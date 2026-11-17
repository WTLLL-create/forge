"""Synthetic engineering fixtures, not real-model capability evidence."""
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
import runpy
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class ProblemUnderstandingTests(unittest.TestCase):
    def module(self, name):
        try:
            return importlib.import_module(name)
        except ImportError as exc:
            self.fail(f'WP-02 component missing: {exc}')

    def fixture(self, root):
        statement = root / 'statement.txt'
        statement.write_text('Industry background.\nQ1: Rank the options.\nQ2: Predict next year.\n', encoding='utf-8')
        return self.module('core.runtime.problem_package').create_package(root / 'run', 'run-a', 'synthetic', statement)

    def spec(self, package):
        asset = package['content']['assets'][0]
        def source(line, quote):
            return {'asset_id': 'statement', 'sha256': asset['sha256'], 'locator': f'L{line}', 'quote': quote}
        return {
            'problem_id': 'synthetic', 'background': [{'text': 'Industry background.', 'sources': [source(1, 'Industry background.')]}],
            'questions': [
                {'id': 'Q1', 'task': 'Rank options', 'objective': 'A ranking', 'sources': [source(2, 'Q1: Rank the options.')],
                 'required_outputs': [{'text': 'Ranking', 'sources': [source(2, 'Rank the options.')]}]},
                {'id': 'Q2', 'task': 'Predict next year', 'objective': 'A prediction', 'sources': [source(3, 'Q2: Predict next year.')],
                 'required_outputs': [{'text': 'Prediction', 'sources': [source(3, 'Predict next year.')]}]},
            ], 'data_assets': [], 'constraints': [], 'evaluation_criteria': [],
            'ambiguities': [], 'assumptions_requiring_confirmation': [],
        }

    def reference(self, package):
        return {'problem_id': 'synthetic', 'reviewer': 'independent-test-reviewer', 'status': 'APPROVED',
                'input_hashes': {a['id']: a['sha256'] for a in package['content']['assets']},
                'questions': [{'id': 'Q1', 'required_outputs': [{'asset_id': 'statement', 'locator': 'L2', 'quote': 'Rank the options.'}]},
                              {'id': 'Q2', 'required_outputs': [{'asset_id': 'statement', 'locator': 'L3', 'quote': 'Predict next year.'}]}],
                'background_locators': ['statement:L1']}

    def test_package_is_snapshot_not_live_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package = self.fixture(root)
            (root / 'statement.txt').write_text('changed', encoding='utf-8')
            self.assertEqual('Industry background.', package['content']['assets'][0]['segments']['L1'])
            self.assertTrue((root / 'run/inputs/statement.txt').is_file())
            self.assertEqual('problem_package@1', package['meta']['artifact_id'])

    def test_valid_contract_and_independent_coverage(self):
        with tempfile.TemporaryDirectory() as raw:
            p = self.fixture(Path(raw))
            s = self.spec(p)
            self.assertEqual('PASS', self.module('core.schema.problem_spec').validate_problem_spec(s, p)['status'])
            self.assertEqual('PASS', self.module('core.runtime.problem_understanding').coverage_gate(s, p, self.reference(p))['status'])

    def test_missing_extra_fields_outputs_and_duplicates_fail(self):
        with tempfile.TemporaryDirectory() as raw:
            p = self.fixture(Path(raw))
            for change in ('missing', 'extra', 'empty_outputs', 'duplicate'):
                with self.subTest(change=change):
                    s = self.spec(p)
                    if change == 'missing': del s['ambiguities']
                    if change == 'extra': s['invented'] = True
                    if change == 'empty_outputs': s['questions'][0]['required_outputs'] = []
                    if change == 'duplicate': s['questions'][1]['id'] = 'Q1'
                    self.assertEqual('FAIL', self.module('core.schema.problem_spec').validate_problem_spec(s, p)['status'])

    def test_source_hash_quote_and_locator_tampering_fail(self):
        with tempfile.TemporaryDirectory() as raw:
            p = self.fixture(Path(raw))
            for field, value in [('sha256', '0' * 64), ('quote', 'not in original'), ('locator', 'L99')]:
                with self.subTest(field=field):
                    s = self.spec(p)
                    s['questions'][0]['sources'][0][field] = value
                    self.assertEqual('FAIL', self.module('core.schema.problem_spec').validate_problem_spec(s, p)['status'])

    def test_citation_numeric_coverage_and_structured_render(self):
        # A claim restating a statement parameter (78 cm/min) must quote the sentence that
        # carries that number; otherwise the numeric coverage check fails (2026-09-10 audit).
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            statement = root / 'statement.txt'
            statement.write_text('Industry background.\nQ1: Rank at 78 cm/min.\nQ2: Predict next year.\n', encoding='utf-8')
            p = self.module('core.runtime.problem_package').create_package(root / 'run', 'run-a', 'synthetic', statement)
            asset = p['content']['assets'][0]

            def source(line, quote):
                return {'asset_id': 'statement', 'sha256': asset['sha256'], 'locator': f'L{line}', 'quote': quote}

            r = {'problem_id': 'synthetic', 'reviewer': 'independent-test-reviewer', 'status': 'APPROVED',
                 'input_hashes': {a['id']: a['sha256'] for a in p['content']['assets']},
                 'questions': [{'id': 'Q1', 'required_outputs': [{'asset_id': 'statement', 'locator': 'L2', 'quote': 'Q1: Rank'}]},
                               {'id': 'Q2', 'required_outputs': [{'asset_id': 'statement', 'locator': 'L3', 'quote': 'Predict next year.'}]}],
                 'background_locators': ['statement:L1']}
            s = {'problem_id': 'synthetic',
                 'background': [{'text': 'Industry background.', 'sources': [source(1, 'Industry background.')]}],
                 'questions': [
                     {'id': 'Q1', 'task': 'Rank at 78 cm/min', 'objective': 'A ranking',
                      'sources': [source(2, 'Q1: Rank')],
                      'required_outputs': [{'text': 'Ranking', 'sources': [source(2, 'Q1: Rank')]}]},
                     {'id': 'Q2', 'task': 'Predict next year', 'objective': 'A prediction',
                      'sources': [source(3, 'Q2: Predict next year.')],
                      'required_outputs': [{'text': 'Prediction', 'sources': [source(3, 'Predict next year.')]}]},
                 ], 'data_assets': [], 'constraints': [], 'evaluation_criteria': [],
                 'ambiguities': [], 'assumptions_requiring_confirmation': []}
            gate = self.module('core.runtime.problem_understanding').coverage_gate
            result = gate(s, p, r)
            self.assertEqual('FAIL', result['status'])
            numeric = next(c for c in result['checks'] if c['name'] == 'Q1_citation_numeric_coverage')
            self.assertEqual('FAIL', numeric['status'])
            self.assertIn('78', numeric['message'])
            # Extending the source quote to the number-carrying sentence passes the gate.
            s['questions'][0]['sources'] = [source(2, 'Q1: Rank at 78 cm/min.')]
            self.assertEqual('PASS', gate(s, p, r)['status'])
            # Rendered review keeps structured JSON sources (no legacy text-line citations).
            md = self.module('core.runtime.problem_understanding').render_review(s, p, [])
            self.assertIn('"asset_id"', md)
            self.assertNotIn('statement:L2 [', md)

    def test_omitted_question_and_background_task_fail(self):
        with tempfile.TemporaryDirectory() as raw:
            p = self.fixture(Path(raw))
            gate = self.module('core.runtime.problem_understanding').coverage_gate
            s = self.spec(p)
            s['questions'].pop()
            self.assertEqual('FAIL', gate(s, p, self.reference(p))['status'])
            s = self.spec(p)
            s['questions'][0]['sources'] = s['background'][0]['sources']
            self.assertEqual('FAIL', gate(s, p, self.reference(p))['status'])

    def test_required_output_and_unapproved_reference_fail(self):
        with tempfile.TemporaryDirectory() as raw:
            p = self.fixture(Path(raw))
            gate = self.module('core.runtime.problem_understanding').coverage_gate
            s = self.spec(p)
            s['questions'][0]['required_outputs'] = s['questions'][1]['required_outputs']
            self.assertEqual('FAIL', gate(s, p, self.reference(p))['status'])
            r = self.reference(p)
            r['status'] = 'DRAFT'
            self.assertEqual('FAIL', gate(self.spec(p), p, r)['status'])

    def test_provider_uses_schema_and_records_safe_usage(self):
        m = self.module('core.runtime.llm_provider')
        seen = []
        def transport(request, timeout):
            seen.append(json.loads(request.data))
            return {'status': 'completed', 'model': 'test-model', 'usage': {'input_tokens': 12, 'output_tokens': 9},
                    'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': '{"answer": 7}'}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}, clear=True):
            provider = m.OpenAIProvider({'provider': 'openai', 'model': 'test-model', 'max_output_tokens': 512}, transport=transport)
            result, audit = provider.generate_structured(prompt='test', schema={'type': 'object'}, input_refs={'problem_package@1': 'a' * 64}, template_version='test-v1')
        self.assertEqual({'answer': 7}, result)
        self.assertTrue(seen[0]['text']['format']['strict'])
        self.assertEqual('test-model', seen[0]['model'])
        self.assertEqual(12, audit['usage']['input_tokens'])
        self.assertNotIn('unit-test-secret', json.dumps(audit))
        self.assertNotIn('Authorization', json.dumps(audit))

    def test_provider_missing_key_and_transport_error_do_not_leak(self):
        m = self.module('core.runtime.llm_provider')
        with patch.dict(os.environ, {}, clear=True):
            provider = m.OpenAIProvider({'provider': 'openai', 'model': 'test-model'})
            with self.assertRaises(m.ProviderError) as error:
                provider.generate_structured(prompt='x', schema={}, input_refs={}, template_version='v1')
            self.assertEqual('MISSING_CREDENTIAL', error.exception.code)
        def failing(request, timeout):
            raise RuntimeError('Authorization: unit-test-secret')
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}, clear=True):
            provider = m.OpenAIProvider({'provider': 'openai', 'model': 'test-model'}, transport=failing)
            with self.assertRaises(m.ProviderError) as error:
                provider.generate_structured(prompt='x', schema={}, input_refs={}, template_version='v1')
        self.assertNotIn('unit-test-secret', str(error.exception) + json.dumps(error.exception.audit))

    def test_provider_refusal_incomplete_and_invalid_json_fail(self):
        m = self.module('core.runtime.llm_provider')
        responses = [{'status': 'incomplete', 'output': []},
                     {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'refusal', 'refusal': 'no'}]}]},
                     {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'not-json'}]}]}]
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}, clear=True):
            for response in responses:
                with self.subTest(response=response['status']):
                    p = m.OpenAIProvider({'provider': 'openai', 'model': 'test-model'}, transport=lambda r, t: response)
                    with self.assertRaises(m.ProviderError):
                        p.generate_structured(prompt='x', schema={}, input_refs={}, template_version='v1')

    def test_snapshot_tampering_and_cross_run_verification_fail(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package = self.fixture(root)
            module = self.module('core.runtime.problem_package')
            from core.schema.artifact_meta import ArtifactIntegrityError
            with self.assertRaises(ArtifactIntegrityError):
                module.verify_package(package, root / 'run', 'run-b')
            (root / 'run/inputs/statement.txt').write_text('changed', encoding='utf-8')
            with self.assertRaises(ArtifactIntegrityError):
                module.verify_package(package, root / 'run', 'run-a')

    def test_old_artifact_cannot_be_packaged_as_new_input(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / 'runs/old/artifacts/statement.txt'
            source.parent.mkdir(parents=True)
            source.write_text('old output', encoding='utf-8')
            with self.assertRaises(ValueError):
                self.module('core.runtime.problem_package').create_package(root / 'new', 'new', 'p', source)

    def test_attachment_requires_role_and_uncertainty_if_opaque(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            p = self.fixture(root)
            p['content']['assets'].append({'id': 'attachment_1', 'inspection': 'opaque', 'segments': {}, 'sha256': 'a' * 64})
            validator = self.module('core.schema.problem_spec').validate_problem_spec
            s = self.spec(p)
            self.assertEqual('FAIL', validator(s, p)['status'])
            s['data_assets'] = [{'id': 'attachment_1', 'role': 'Unknown purpose', 'certainty': 'unknown',
                                 'question_ids': ['Q1'], 'sources': s['questions'][0]['sources']}]
            self.assertEqual('FAIL', validator(s, p)['status'])
            s['ambiguities'] = [{'id': 'A1', 'description': 'Attachment contents not inspected', 'sources': s['questions'][0]['sources']}]
            self.assertEqual('PASS', validator(s, p)['status'])

    def test_provider_rejects_inline_key_and_oversized_input_without_transport(self):
        m = self.module('core.runtime.llm_provider')
        with self.assertRaises(ValueError):
            m.OpenAIProvider({'provider': 'openai', 'model': 'test-model', 'api_key': 'do-not-store'})
        def forbidden(request, timeout):
            self.fail('Over-budget request must not reach transport')
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}, clear=True):
            p = m.OpenAIProvider({'provider': 'openai', 'model': 'test-model'}, transport=forbidden)
            with self.assertRaises(m.ProviderError) as error:
                p.generate_structured(prompt='x' * 120001, schema={}, input_refs={}, template_version='v1')
            self.assertEqual('INPUT_BUDGET_EXCEEDED', error.exception.code)

    def workflow_fixture(self, root):
        package = self.fixture(root)
        reference = root / 'reference.json'
        reference.write_text(json.dumps(self.reference(package)), encoding='utf-8')
        config = root / 'workflow.json'
        config.write_text(json.dumps({'schema': 'forge-problem-understanding/v1', 'problem_id': 'synthetic',
                                     'statement': 'statement.txt', 'attachments': [], 'reference': 'reference.json',
                                     'provider': {'provider': 'openai', 'model': 'test-model'}}), encoding='utf-8')
        return package, config

    def test_interpreter_run_is_evidence_bound_and_reference_never_reaches_provider(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package, config = self.workflow_fixture(root)
            def transport(request, timeout):
                body = json.loads(request.data)
                self.assertNotIn('independent-test-reviewer', json.dumps(body))
                self.assertNotIn('background_locators', json.dumps(body))
                return {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(self.spec(package))}]}]}
            module = self.module('core.runtime.problem_understanding')
            self.assertTrue(hasattr(module, 'ProblemUnderstandingWorkflow'), 'Workflow integration missing')
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}, clear=True):
                result = module.ProblemUnderstandingWorkflow(config).run(transport=transport)
            self.assertEqual('READY_FOR_REVIEW', result['status'])
            run = Path(result['run_dir'])
            registry = json.loads((run / 'active_artifacts.json').read_text(encoding='utf-8'))
            self.assertEqual('problem_spec@1', registry['artifacts']['problem_spec']['artifact_id'])
            stored = json.loads((run / registry['artifacts']['problem_spec']['path']).read_text(encoding='utf-8'))
            self.assertEqual(['problem_package@1'], stored['meta']['input_refs'])
            self.assertIn('PENDING', (run / 'artifacts/problem_review.md').read_text(encoding='utf-8'))
            self.assertEqual('INJECTED_TRANSPORT', result['execution_mode'])

    def test_missing_credential_blocks_with_safe_audit_and_no_problem_spec(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, config = self.workflow_fixture(root)
            module = self.module('core.runtime.problem_understanding')
            self.assertTrue(hasattr(module, 'ProblemUnderstandingWorkflow'), 'Workflow integration missing')
            with patch.dict(os.environ, {}, clear=True):
                result = module.ProblemUnderstandingWorkflow(config).run()
            self.assertEqual('BLOCKED', result['status'])
            self.assertEqual('MISSING_CREDENTIAL', result['failure_code'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text(encoding='utf-8'))
            self.assertNotIn('problem_spec', registry['artifacts'])
            audit = json.loads((Path(result['run_dir']) / 'logs/provider.json').read_text(encoding='utf-8'))
            self.assertEqual('MISSING_CREDENTIAL', audit['status'])

    def test_single_entry_dispatches_problem_config_and_no_config_still_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, config = self.workflow_fixture(root)
            env = dict(os.environ)
            env.pop('OPENAI_API_KEY', None)
            entry = ROOT / 'core/runtime/workflow_executor.py'
            process = subprocess.run([sys.executable, str(entry), '--config', str(config)], env=env, capture_output=True, text=True)
            self.assertNotEqual(0, process.returncode)
            self.assertIn('MISSING_CREDENTIAL', process.stdout)
            no_config = subprocess.run([sys.executable, str(entry)], capture_output=True, text=True)
            self.assertNotEqual(0, no_config.returncode)

    def run_entry_with_spec(self, config, spec):
        """Exercise the real entry/workflow/gates; replace only paid HTTP transport."""
        def transport(request, timeout):
            return {'status': 'completed', 'output': [{'type': 'message', 'content': [
                {'type': 'output_text', 'text': json.dumps(spec)}]}]}
        entry = ROOT / 'core/runtime/workflow_executor.py'
        output = io.StringIO()
        with patch.object(sys, 'path', [str(entry.parent), *sys.path]), \
                patch.object(sys, 'argv', [str(entry), '--config', str(config)]), \
                patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}, clear=True), \
                patch('core.runtime.llm_provider._http_transport', side_effect=transport), \
                redirect_stdout(output):
            with self.assertRaises(SystemExit) as stopped:
                runpy.run_path(str(entry), run_name='__main__')
        return stopped.exception.code, json.loads(output.getvalue())

    def test_entry_ready_for_review_exits_zero_without_claiming_benchmark_success(self):
        """Break caught: a validated candidate is misreported as command failure."""
        with tempfile.TemporaryDirectory() as raw:
            package, config = self.workflow_fixture(Path(raw))
            code, result = self.run_entry_with_spec(config, self.spec(package))
            self.assertEqual(0, code)
            self.assertEqual('READY_FOR_REVIEW', result['status'])
            self.assertEqual('PENDING', result['human_review'])
            self.assertEqual('NOT_EVALUATED', result['benchmark_acceptance'])
            self.assertFalse((Path(result['run_dir']) / 'artifacts/published').exists())

    def test_entry_failed_coverage_remains_nonzero_without_active_spec(self):
        """Break caught: treating all interpretation outcomes as successful exits."""
        with tempfile.TemporaryDirectory() as raw:
            package, config = self.workflow_fixture(Path(raw))
            spec = self.spec(package)
            spec['questions'].pop()
            code, result = self.run_entry_with_spec(config, spec)
            self.assertNotEqual(0, code)
            self.assertEqual('GATE_FAILED', result['status'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text(encoding='utf-8'))
            self.assertNotIn('problem_spec', registry['artifacts'])

    def test_failed_coverage_never_activates_problem_spec(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package, config = self.workflow_fixture(root)
            spec = self.spec(package)
            spec['questions'].pop()
            def transport(request, timeout):
                return {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(spec)}]}]}
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}, clear=True):
                result = self.module('core.runtime.problem_understanding').ProblemUnderstandingWorkflow(config).run(transport=transport)
            self.assertEqual('GATE_FAILED', result['status'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text(encoding='utf-8'))
            self.assertNotIn('problem_spec', registry['artifacts'])

    def test_config_is_bound_into_package_identity(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package, config = self.workflow_fixture(root)
            with patch.dict(os.environ, {}, clear=True):
                result = self.module('core.runtime.problem_understanding').ProblemUnderstandingWorkflow(config).run()
            run = Path(result['run_dir'])
            registry = json.loads((run / 'active_artifacts.json').read_text(encoding='utf-8'))
            stored = json.loads((run / registry['artifacts']['problem_package']['path']).read_text(encoding='utf-8'))
            self.assertIn('configuration', stored['content'])
            self.assertEqual('test-model', stored['content']['configuration']['provider']['model'])

    def test_codex_provider_drives_real_workflow_gates_without_api_key(self):
        """Break caught: Interpreter still requires the HTTP provider or bypasses gates."""
        from test_codex_provider import events
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package, config = self.workflow_fixture(root)
            data = json.loads(config.read_text())
            data['provider'] = {'provider': 'codex', 'model': 'test-model'}
            config.write_text(json.dumps(data))
            def runner(command, **kwargs):
                if '--version' in command:
                    return subprocess.CompletedProcess(command, 0, b'codex-cli 0.153.4', b'')
                if 'login' in command:
                    return subprocess.CompletedProcess(command, 0, b'Logged in using ChatGPT', b'')
                self.assertNotIn('independent-test-reviewer', kwargs['input_text'])
                self.assertNotIn('background_locators', kwargs['input_text'])
                return subprocess.CompletedProcess(command, 0, events(self.spec(package)), b'')
            with patch.dict(os.environ, {}, clear=True), patch('shutil.which', return_value=sys.executable):
                result = self.module('core.runtime.problem_understanding').ProblemUnderstandingWorkflow(config).run(transport=runner)
            self.assertEqual('READY_FOR_REVIEW', result['status'])
            self.assertEqual('INJECTED_TRANSPORT', result['execution_mode'])
            self.assertEqual('NOT_EVALUATED', result['benchmark_acceptance'])
            run = Path(result['run_dir'])
            audit = json.loads((run / 'logs/provider.json').read_text())
            self.assertEqual('codex', audit['provider'])
            registry = json.loads((run / 'active_artifacts.json').read_text())
            self.assertEqual('problem_spec@1', registry['artifacts']['problem_spec']['artifact_id'])

    def test_codex_login_failure_blocks_without_api_fallback(self):
        """Break caught: missing subscription login silently triggers an API request."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, config = self.workflow_fixture(root)
            data = json.loads(config.read_text())
            data['provider'] = {'provider': 'codex', 'model': 'test-model'}
            config.write_text(json.dumps(data))
            def runner(command, **kwargs):
                self.assertNotIn('exec', command)
                if '--version' in command:
                    return subprocess.CompletedProcess(command, 0, b'codex-cli 0.153.4', b'')
                return subprocess.CompletedProcess(command, 1, b'', b'Not logged in')
            with patch('shutil.which', return_value=sys.executable):
                result = self.module('core.runtime.problem_understanding').ProblemUnderstandingWorkflow(config).run(transport=runner)
            self.assertEqual('BLOCKED', result['status'])
            self.assertEqual('CODEX_CHATGPT_LOGIN_REQUIRED', result['failure_code'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text())
            self.assertNotIn('problem_spec', registry['artifacts'])

    def test_reference_hash_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            p = self.fixture(Path(raw))
            reference = self.reference(p)
            reference['input_hashes']['statement'] = '0' * 64
            self.assertEqual('FAIL', self.module('core.runtime.problem_understanding').coverage_gate(self.spec(p), p, reference)['status'])

    def test_snapshot_changed_during_provider_call_blocks_activation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package, config = self.workflow_fixture(root)
            def transport(request, timeout):
                snapshot = next((root / 'runtime/runs').glob('*/inputs/statement.txt'))
                snapshot.write_text('changed during execution', encoding='utf-8')
                return {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(self.spec(package))}]}]}
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}, clear=True):
                result = self.module('core.runtime.problem_understanding').ProblemUnderstandingWorkflow(config).run(transport=transport)
            self.assertEqual('BLOCKED', result['status'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text(encoding='utf-8'))
            self.assertNotIn('problem_spec', registry['artifacts'])


if __name__ == '__main__':
    unittest.main()
