"""Rule-date and AI handoff tests; synthetic runs are not contest acceptance."""
import importlib
import json
import os
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import test_problem_understanding as problem_fixtures


class ContestReadinessTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module('core.runtime.contest_readiness')
        except ImportError as exc:
            self.fail(f'Contest readiness component missing: {exc}')

    def context(self, **changes):
        value = {'profile_id': 'cumcm_2026', 'mode': 'practice',
                 'problem_origin': 'practice', 'external_retrieval': 'disabled'}
        value.update(changes)
        return value

    def evaluate(self, context, now='2026-09-09T16:00:00+08:00'):
        return self.module().evaluate_context(context, now=datetime.fromisoformat(now))

    def test_unbound_is_not_contest_approval(self):
        self.assertEqual('NOT_ASSESSED', self.evaluate(None)['status'])

    def test_practice_binds_dated_official_sources_without_claiming_official_problem(self):
        result = self.evaluate(self.context())
        self.assertEqual('PRECHECK_ONLY', result['status'])
        self.assertFalse(result['submission_ready'])
        self.assertEqual('2026-09-09', result['profile']['verified_on'])

    def test_official_problem_before_release_fails(self):
        with self.assertRaisesRegex(ValueError, 'OFFICIAL_PROBLEM_NOT_RELEASED'):
            self.evaluate(self.context(problem_origin='official',
                                      official_source_url='https://www.mcm.edu.cn/problem.pdf'))

    def test_competition_needs_official_source_and_closed_retrieval(self):
        for context in [self.context(mode='competition'),
                        self.context(mode='competition', problem_origin='official',
                                     official_source_url='https://github.com/example/2026'),
                        self.context(mode='competition', problem_origin='official',
                                     official_source_url='https://www.mcm.edu.cn/problem.pdf',
                                     external_retrieval='contest_discussion')]:
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.evaluate(context, '2026-09-10T18:01:00+08:00')

    def test_valid_competition_metadata_is_still_not_source_or_human_verification(self):
        result = self.evaluate(self.context(mode='competition', problem_origin='official',
                               official_source_url='https://www.mcm.edu.cn/problem.pdf'),
                               '2026-09-10T18:01:00+08:00')
        self.assertEqual('PRECHECK_ONLY', result['status'])
        self.assertEqual('PENDING', result['problem_source_verification'])
        self.assertFalse(result['submission_ready'])

    def test_wrong_profile_future_check_and_stale_competition_fail(self):
        for context, now in [(self.context(profile_id='mcm_2027'), '2026-09-09T16:00:00+08:00'),
                             (self.context(), '2026-09-08T16:00:00+08:00'),
                             (self.context(mode='competition', problem_origin='official',
                              official_source_url='https://www.mcm.edu.cn/problem.pdf'),
                              '2026-09-20T16:00:00+08:00')]:
            with self.subTest(now=now), self.assertRaises(ValueError):
                self.evaluate(context, now)

    def test_unknown_fields_and_boolean_values_rejected(self):
        for changes in [{'mode': True}, {'problem_origin': 'unknown'}, {'approved': True},
                        {'official_source_url': 123}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.evaluate(self.context(**changes))

    def test_workflow_blocks_before_model_call_and_retains_reason(self):
        fixture = problem_fixtures.ProblemUnderstandingTests()
        with tempfile.TemporaryDirectory() as raw:
            _, config = fixture.workflow_fixture(Path(raw))
            data = json.loads(config.read_text())
            data['contest_context'] = self.context(profile_id='unknown')
            config.write_text(json.dumps(data), encoding='utf-8')
            workflow = importlib.import_module('core.runtime.problem_understanding')
            try:
                runner = workflow.ProblemUnderstandingWorkflow(config)
            except ValueError as exc:
                self.fail(f'Contest context integration missing: {exc}')
            result = runner.run(transport=lambda *_: self.fail('Model must not be called'))
            self.assertEqual('BLOCKED', result['status'])
            self.assertEqual('UNKNOWN_CONTEST_PROFILE', result['failure_code'])
            report = json.loads((Path(result['run_dir']) / 'gates/contest_preflight.json').read_text())
            self.assertEqual('BLOCKED', report['status'])

    def test_real_workflow_emits_pending_handoff_and_tampering_invalidates_it(self):
        fixture = problem_fixtures.ProblemUnderstandingTests()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package, config = fixture.workflow_fixture(root)
            def transport(*_):
                return {'status': 'completed', 'output': [{'type': 'message', 'content': [
                    {'type': 'output_text', 'text': json.dumps(fixture.spec(package))}]}]}
            workflow = importlib.import_module('core.runtime.problem_understanding')
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'unit-test-secret'}):
                result = workflow.ProblemUnderstandingWorkflow(config).run(transport=transport)
            self.assertEqual('READY_FOR_REVIEW', result['status'])
            run = Path(result['run_dir'])
            path = run / 'ai_usage_handoff.json'
            self.assertTrue(path.is_file(), 'AI usage handoff is not integrated')
            handoff = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual('PENDING', handoff['human_review'])
            self.assertEqual('INJECTED_TRANSPORT', handoff['execution_mode'])
            self.assertNotIn('unit-test-secret', path.read_text(encoding='utf-8'))
            self.assertFalse(handoff['submission_ready'])
            self.assertEqual(1, len(handoff['calls']))
            self.assertEqual([], self.module().verify_handoff(run))
            original = path.read_bytes()
            handoff['human_review'] = 'APPROVED'
            path.write_text(json.dumps(handoff), encoding='utf-8')
            self.assertTrue(self.module().verify_handoff(run))
            path.write_bytes(original)
            source = run / 'inputs/statement.txt'
            original_source = source.read_bytes()
            source.write_text('changed')
            self.assertTrue(self.module().verify_handoff(run))
            source.write_bytes(original_source)
            (run / 'logs/provider.json').write_text('{}')
            self.assertTrue(self.module().verify_handoff(run))

    def test_missing_rule_snapshot_blocks_with_saved_report(self):
        fixture = problem_fixtures.ProblemUnderstandingTests()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, config = fixture.workflow_fixture(root)
            data = json.loads(config.read_text(encoding='utf-8'))
            data['contest_context'] = self.context()
            config.write_text(json.dumps(data), encoding='utf-8')
            workflow = importlib.import_module('core.runtime.problem_understanding')
            (root / 'invalid.json').write_text('{}')
            for name in ('missing.json', 'invalid.json'):
                with self.subTest(name=name), patch.object(self.module(), 'PROFILE_PATH', root / name):
                    result = workflow.ProblemUnderstandingWorkflow(config).run(
                        transport=lambda *_: self.fail('Model must not be called'))
                self.assertEqual('BLOCKED', result['status'])
                self.assertEqual('CONTEST_PROFILE_UNAVAILABLE', result['failure_code'])
                self.assertTrue((Path(result['run_dir']) / 'gates/contest_preflight.json').is_file())

    def test_preflight_write_failure_blocks_with_manifest(self):
        # Second-round review finding: a disk failure while persisting the successful
        # preflight report must still finalize the run (manifest) and never call a model.
        fixture = problem_fixtures.ProblemUnderstandingTests()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, config = fixture.workflow_fixture(root)
            data = json.loads(config.read_text(encoding='utf-8'))
            data['contest_context'] = self.context()
            config.write_text(json.dumps(data), encoding='utf-8')
            workflow = importlib.import_module('core.runtime.problem_understanding')
            real_write = workflow._atomic_write_json

            def failing_write(path, value):
                if 'contest_preflight' in str(path) and isinstance(value, dict) and 'schema' in value:
                    raise OSError('injected preflight write failure')
                return real_write(path, value)

            with patch.object(workflow, '_atomic_write_json', side_effect=failing_write):
                result = workflow.ProblemUnderstandingWorkflow(config).run(
                    transport=lambda *_: self.fail('Model must not be called'))
            self.assertEqual('BLOCKED', result['status'])
            self.assertEqual('CONTEST_PREFLIGHT_WRITE_FAILED', result['failure_code'])
            self.assertTrue((Path(result['run_dir']) / 'manifest.json').is_file())


if __name__ == '__main__':
    unittest.main()
