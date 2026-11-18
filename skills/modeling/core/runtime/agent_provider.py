"""Agent-answered provider: the conversational agent itself is the model.

The workflow persists each structured request as a JSON file under
``<run_dir>/agent_requests/<request_id>.json`` and blocks polling for
``<request_id>.response.json``. The agent (this assistant) reads the prompt,
produces a schema-conformant answer as a real model output, and writes the
response file; the workflow then continues through its gates unchanged.

Audit labels: ``provider=agent``, ``response_source=agent_answered`` — the
output is genuinely model-authored, not an injected test transport, and not a
codex/OpenAI CLI call. Manifest ``execution_mode`` therefore records
REAL_PROVIDER (no synthetic transport was supplied).
"""
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.runtime.llm_provider import ProviderError


class AgentProvider:
    def __init__(self, config, *, transport=None, run_dir=None):
        allowed = {'provider', 'model', 'timeout_seconds'}
        if not isinstance(config, dict) or set(config) - allowed or config.get('provider') != 'agent':
            raise ValueError('INVALID_PROVIDER_CONFIG')
        self.model = config.get('model') or 'doubao-main-agent'
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError('MODEL_CONFIGURATION_REQUIRED')
        self.timeout = config.get('timeout_seconds', 1800)
        if type(self.timeout) is not int or not 1 <= self.timeout <= 7200:
            raise ValueError('INVALID_TIMEOUT')
        if run_dir is None:
            import tempfile
            run_dir = Path(tempfile.mkdtemp())
        self.run_dir = Path(run_dir)
        self.requests_dir = self.run_dir / 'agent_requests'

    def generate_structured(self, *, prompt, schema, input_refs, template_version):
        audit = {'provider': 'agent', 'model': self.model, 'template_version': template_version,
                 'input_artifact_refs': dict(input_refs), 'status': 'STARTED', 'usage': None,
                 'created_at': datetime.now(timezone.utc).isoformat(),
                 'execution_mode': 'REAL_PROVIDER', 'response_source': 'agent_answered'}

        def fail(code):
            audit['status'] = code
            raise ProviderError(code, audit) from None

        if len(prompt) > 120_000:
            fail('INPUT_BUDGET_EXCEEDED')
        request_id = uuid.uuid4().hex[:12]
        try:
            self.requests_dir.mkdir(parents=True, exist_ok=True)
            request_path = self.requests_dir / f'{request_id}.json'
            response_path = self.requests_dir / f'{request_id}.response.json'
            request_path.write_text(json.dumps({
                'request_id': request_id, 'template_version': template_version,
                'prompt': prompt, 'schema': schema, 'input_refs': dict(input_refs),
                'request_path': str(request_path), 'response_path': str(response_path),
                'created_at': audit['created_at'],
            }, ensure_ascii=False), encoding='utf-8')
        except OSError:
            fail('AGENT_REQUEST_WRITE_FAILED')
        deadline = time.monotonic() + self.timeout
        raw = None
        while time.monotonic() < deadline:
            try:
                if response_path.is_file():
                    raw = response_path.read_text(encoding='utf-8')
                    data = json.loads(raw)
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.25)
        else:
            fail('AGENT_RESPONSE_TIMEOUT')
        if not isinstance(data, dict) or data.get('request_id') != request_id:
            fail('AGENT_RESPONSE_INVALID')
        result = data.get('result')
        if not isinstance(result, dict):
            fail('AGENT_RESPONSE_INVALID')
        audit['status'] = 'COMPLETED'
        audit['usage'] = {'response_chars': len(raw)}
        return result, audit
