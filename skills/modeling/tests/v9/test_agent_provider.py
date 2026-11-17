"""AgentProvider (agent-as-model) unit tests."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.runtime.agent_provider import AgentProvider
from core.runtime.llm_provider import ProviderError, create_provider

SCHEMA = {'type': 'object', 'properties': {'answer': {'type': 'string'}},
          'required': ['answer'], 'additionalProperties': False}


def answer_in_thread(provider, requests_dir):
    """Consume one request file and write a response, mimicking the agent."""
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        pending = sorted(requests_dir.glob('*.json'))
        pending = [p for p in pending if not p.name.endswith('.response.json')]
        if pending:
            req = json.loads(pending[0].read_text(encoding='utf-8'))
            Path(req['response_path']).write_text(
                json.dumps({'request_id': req['request_id'],
                            'result': {'answer': 'ok'}}), encoding='utf-8')
            return True
        time.sleep(0.1)
    return False


class AgentProviderTests(unittest.TestCase):
    def make(self, **overrides):
        cfg = {'provider': 'agent', 'model': 'test-agent'}
        cfg.update(overrides)
        return cfg

    def test_invalid_config(self):
        with self.assertRaisesRegex(ValueError, 'INVALID_PROVIDER_CONFIG'):
            AgentProvider({'provider': 'codex'}, run_dir=Path(tempfile.mkdtemp()))
        with self.assertRaisesRegex(ValueError, 'INVALID_PROVIDER_CONFIG'):
            AgentProvider({'provider': 'agent', 'extra': 1}, run_dir=Path(tempfile.mkdtemp()))

    def test_missing_model(self):
        with self.assertRaisesRegex(ValueError, 'MODEL_CONFIGURATION_REQUIRED'):
            AgentProvider({'provider': 'agent', 'model': 123}, run_dir=Path(tempfile.mkdtemp()))
        # empty string falls back to the documented default
        provider = AgentProvider({'provider': 'agent', 'model': ''}, run_dir=Path(tempfile.mkdtemp()))
        self.assertEqual(provider.model, 'doubao-main-agent')

    def test_request_response_roundtrip(self):
        with tempfile.TemporaryDirectory() as raw:
            provider = AgentProvider(self.make(), run_dir=Path(raw))
            out = {}
            thread = threading.Thread(
                target=lambda: out.update(result=provider.generate_structured(
                    prompt='p', schema=SCHEMA, input_refs={'pkg@1': 'a' * 64},
                    template_version='t/v1')))
            thread.start()
            self.assertTrue(answer_in_thread(provider, provider.requests_dir),
                            'agent never saw the request')
            thread.join(timeout=20)
            result, audit = out['result']
            self.assertEqual(result, {'answer': 'ok'})
            self.assertEqual(audit['status'], 'COMPLETED')
            self.assertEqual(audit['provider'], 'agent')
            self.assertEqual(audit['response_source'], 'agent_answered')
            self.assertEqual(audit['input_artifact_refs'], {'pkg@1': 'a' * 64})

    def test_timeout(self):
        with tempfile.TemporaryDirectory() as raw:
            provider = AgentProvider(self.make(timeout_seconds=1), run_dir=Path(raw))
            with self.assertRaisesRegex(ProviderError, 'AGENT_RESPONSE_TIMEOUT'):
                provider.generate_structured(prompt='p', schema=SCHEMA,
                                             input_refs={}, template_version='t/v1')

    def test_invalid_response(self):
        with tempfile.TemporaryDirectory() as raw:
            provider = AgentProvider(self.make(timeout_seconds=15), run_dir=Path(raw))
            out = {}

            def run():
                out.update(error=None)
                try:
                    out['result'] = provider.generate_structured(
                        prompt='p', schema=SCHEMA, input_refs={}, template_version='t/v1')
                except ProviderError as exc:
                    out['error'] = exc

            thread = threading.Thread(target=run)
            thread.start()
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                pending = [p for p in provider.requests_dir.glob('*.json')
                           if not p.name.endswith('.response.json')]
                if pending:
                    req = json.loads(pending[0].read_text(encoding='utf-8'))
                    Path(req['response_path']).write_text(
                        json.dumps({'request_id': req['request_id'], 'result': 'not-a-dict'}),
                        encoding='utf-8')
                    break
                time.sleep(0.1)
            thread.join(timeout=20)
            self.assertIsInstance(out.get('error'), ProviderError)
            self.assertEqual(out['error'].code, 'AGENT_RESPONSE_INVALID')

    def test_create_provider_branch(self):
        with tempfile.TemporaryDirectory() as raw:
            provider = create_provider(self.make(), run_dir=Path(raw))
            self.assertIsInstance(provider, AgentProvider)
        with self.assertRaisesRegex(ValueError, 'INVALID_PROVIDER_CONFIG'):
            create_provider({'provider': 'unknown'}, run_dir=Path(tempfile.mkdtemp()))


if __name__ == '__main__':
    unittest.main()
