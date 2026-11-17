"""Subscription adapter engineering tests. No Codex inference is launched here."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def events(result=None):
    return '\n'.join(json.dumps(e) for e in [
        {'type': 'thread.started', 'thread_id': 'synthetic-thread'},
        {'type': 'turn.started'},
        {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(result or {'answer': 'ok'})}},
        {'type': 'turn.completed', 'usage': {'input_tokens': 12, 'output_tokens': 8}},
    ]).encode()


class CodexProviderTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module('core.runtime.codex_provider')
        except ImportError:
            self.fail('Subscription provider is not implemented')

    def call(self, runner, root, config=None, prompt='source package'):
        provider = self.module().CodexProvider(config or {'provider': 'codex', 'model': 'test-model'},
                                             transport=runner, run_dir=root)
        with patch('shutil.which', return_value=sys.executable):
            return provider.generate_structured(prompt=prompt,
                schema={'type': 'object', 'properties': {'answer': {'type': 'string'}},
                        'required': ['answer'], 'additionalProperties': False},
                input_refs={'problem_package@1': 'a' * 64}, template_version='problem-interpreter/v1')

    def runner(self, output=None, login=True, version='0.153.4'):
        def run(command, **kwargs):
            if '--version' in command:
                return subprocess.CompletedProcess(command, 0, f'codex-cli {version}'.encode(), b'')
            if 'login' in command:
                return subprocess.CompletedProcess(command, 0 if login else 1, b'',
                    b'Logged in using ChatGPT' if login else b'Not logged in')
            return subprocess.CompletedProcess(command, 0, events() if output is None else output, b'')
        return run

    def test_subscription_command_and_safe_audit(self):
        """Break caught: API fallback, project tools, or secrets enter invocation/audit."""
        seen = []
        base = self.runner()
        def run(command, **kwargs):
            if 'exec' in command:
                seen.append(command)
                self.assertEqual('source package', kwargs['input_text'])
                self.assertNotIn('OPENAI_API_KEY', kwargs['env'])
                self.assertNotIn('ANTHROPIC_AUTH_TOKEN', kwargs['env'])
                self.assertTrue(Path(kwargs['cwd']).is_dir())
                self.assertEqual({'answer': {'type': 'string'}}, json.loads(
                    Path(command[command.index('--output-schema') + 1]).read_text())['properties'])
            return base(command, **kwargs)
        with tempfile.TemporaryDirectory() as raw, patch.dict(os.environ, {'OPENAI_API_KEY': 'private-test-key'}):
            result, audit = self.call(run, Path(raw))
        self.assertEqual({'answer': 'ok'}, result)
        command = seen[0]
        for arg in ('--ignore-user-config', '--ephemeral', '--strict-config', 'forced_login_method="chatgpt"',
                    'features.shell_tool=false', 'features.plugins=false', 'features.multi_agent=false',
                    'web_search="disabled"', 'project_doc_max_bytes=0'):
            self.assertIn(arg, command)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', command)
        self.assertEqual('codex', audit['provider'])
        self.assertEqual('chatgpt', audit['auth_method'])
        self.assertEqual(8, audit['usage']['output_tokens'])
        self.assertEqual('COMPLETED', audit['status'])
        self.assertNotIn('private-test-key', json.dumps(audit))

    def test_no_login_or_unsupported_version_never_launches_inference(self):
        for settings, code in [({'login': False}, 'CODEX_CHATGPT_LOGIN_REQUIRED'),
                               ({'version': '99.0.0'}, 'CODEX_VERSION_UNVERIFIED')]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as raw:
                base = self.runner(**settings)
                def run(command, **kwargs):
                    self.assertNotIn('exec', command)
                    return base(command, **kwargs)
                with self.assertRaisesRegex(RuntimeError, code):
                    self.call(run, Path(raw))

    def test_incomplete_invalid_and_tool_events_fail_closed(self):
        for output in [b'', b'not-json', events().replace(b'turn.completed', b'turn.failed'),
                       events() + b'\n' + json.dumps({'type': 'item.started', 'item': {'type': 'command_execution'}}).encode(),
                       events().replace(b'agent_message', b'mcp_tool_call')]:
            with self.subTest(output=output[:30]), tempfile.TemporaryDirectory() as raw:
                with self.assertRaises(RuntimeError):
                    self.call(self.runner(output), Path(raw))

    def test_timeout_and_transport_error_never_echo_raw_messages(self):
        for error in [subprocess.TimeoutExpired('private-test-key', 1), RuntimeError('private-test-key')]:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as raw:
                base = self.runner()
                def run(command, **kwargs):
                    if 'exec' in command:
                        raise error
                    return base(command, **kwargs)
                with self.assertRaises(RuntimeError) as caught:
                    self.call(run, Path(raw))
                self.assertNotIn('private-test-key', str(caught.exception))
                self.assertNotIn('private-test-key', json.dumps(caught.exception.audit))

    def test_oversized_prompt_rejected_before_transport(self):
        with tempfile.TemporaryDirectory() as raw:
            def forbidden(*args, **kwargs):
                self.fail('Over-budget input reached transport')
            with self.assertRaisesRegex(RuntimeError, 'INPUT_BUDGET_EXCEEDED'):
                self.call(forbidden, Path(raw), prompt='x' * 120001)

    def test_nonzero_exit_and_oversized_response_cannot_return_result(self):
        for bad_code, bad_output, expected in [(1, events(), 'CODEX_EXEC_FAILED'),
                                               (0, b'x' * 262145, 'CODEX_OUTPUT_LIMIT')]:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as raw:
                base = self.runner()
                def run(command, **kwargs):
                    if 'exec' in command:
                        return subprocess.CompletedProcess(command, bad_code, bad_output, b'')
                    return base(command, **kwargs)
                with self.assertRaisesRegex(RuntimeError, expected):
                    self.call(run, Path(raw))

    def test_unknown_provider_does_not_select_api(self):
        from core.runtime.llm_provider import create_provider
        with self.assertRaisesRegex(ValueError, 'INVALID_PROVIDER_CONFIG'):
            create_provider({'provider': 'typo', 'model': 'test-model'})

    def test_config_rejects_keys_and_unenforced_token_limit(self):
        cls = self.module().CodexProvider
        for extra in ({'api_key': 'secret'}, {'max_output_tokens': 999}, {'timeout_seconds': 0},
                      {'model': ''}, {'max_response_bytes': 0}, {'temperature': 0.1}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                cls(dict({'provider': 'codex', 'model': 'test-model'}, **extra))

    def test_real_process_transport_enforces_timeout_and_output_bound(self):
        """Local Python children, not LLM calls, exercise actual process termination."""
        run = self.module()._process_transport
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(subprocess.TimeoutExpired):
                run([sys.executable, '-c', 'import time; time.sleep(30)'], input_text='', cwd=raw,
                    env=dict(os.environ), timeout=0.2, max_bytes=4096)
            with self.assertRaisesRegex(RuntimeError, 'CODEX_OUTPUT_LIMIT'):
                run([sys.executable, '-c', "print('x'*10000)"], input_text='', cwd=raw,
                    env=dict(os.environ), timeout=5, max_bytes=100)


if __name__ == '__main__':
    unittest.main()
