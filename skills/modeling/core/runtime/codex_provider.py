"""Bounded ChatGPT-authenticated Codex CLI adapter; no API credential handling.

The invocation profile disables local tools/context discovery. This is not an OS
read-isolation proof: real deployment must validate the pinned CLI profile.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone

from core.runtime.llm_provider import ProviderError

VERIFIED_CLI_VERSION = '0.153.4'
DISABLED_FEATURES = (
    'shell_tool', 'unified_exec', 'apps', 'plugins', 'browser_use',
    'browser_use_external', 'browser_use_full_cdp_access', 'in_app_browser',
    'computer_use', 'image_generation', 'view_image', 'code_mode',
    'code_mode_host', 'code_mode_only', 'multi_agent', 'multi_agent_v2',
    'memories', 'hooks', 'skill_search', 'skill_mcp_dependency_install',
    'unbounded_connection_retries',
)


def _find_codex():
    """Locate the pinned CLI: PATH first, then the standard Windows install layout."""
    executable = shutil.which('codex')
    if executable and (os.name != 'nt' or Path(executable).suffix.lower() == '.exe'):
        return executable
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', '')) / 'OpenAI' / 'Codex' / 'bin'
        try:
            candidates = [d for d in base.iterdir() if d.is_dir() and (d / 'codex.exe').is_file()]
        except OSError:
            candidates = []
        if candidates:
            latest = max(candidates, key=lambda d: d.stat().st_mtime)
            return str(latest / 'codex.exe')
    return None


def _process_transport(command, *, input_text, cwd, env, timeout, max_bytes):
    """No shell, bounded stdout/stderr, wall-clock deadline, owned-process cleanup."""
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        source.write(input_text.encode('utf-8'))
        source.seek(0)
        process = subprocess.Popen(command, stdin=source, stdout=output, stderr=errors,
                                   cwd=cwd, env=env, creationflags=flags)
        deadline = time.monotonic() + timeout
        try:
            while True:
                if os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size > max_bytes:
                    raise RuntimeError('CODEX_OUTPUT_LIMIT')
                code = process.poll()
                if code is not None:
                    break
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(command[0], timeout)
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
            output.seek(0)
            errors.seek(0)
            stdout, stderr = output.read(max_bytes + 1), errors.read(max_bytes + 1)
            if len(stdout) + len(stderr) > max_bytes:
                raise RuntimeError('CODEX_OUTPUT_LIMIT')
            return subprocess.CompletedProcess(command, code, stdout, stderr)
        finally:
            if process.poll() is None:
                if os.name == 'nt':
                    # Only the process tree this call created, never a name-wide kill.
                    subprocess.run([str(Path(os.environ['SystemRoot']) / 'System32/taskkill.exe'),
                                    '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=5, creationflags=flags)
                else:
                    process.kill()
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)


class CodexProvider:
    def __init__(self, config, *, transport=None, run_dir=None):
        allowed = {'provider', 'model', 'reasoning_effort', 'timeout_seconds', 'max_response_bytes'}
        if not isinstance(config, dict) or set(config) - allowed or config.get('provider') != 'codex':
            raise ValueError('INVALID_CODEX_PROVIDER_CONFIG')
        self.model = config.get('model')
        if not isinstance(self.model, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', self.model) or self.model.startswith('sk-'):
            raise ValueError('MODEL_CONFIGURATION_REQUIRED')
        self.timeout = config.get('timeout_seconds', 60)
        self.limit = config.get('max_response_bytes', 262144)
        self.effort = config.get('reasoning_effort', 'medium')
        if type(self.timeout) is not int or not 1 <= self.timeout <= 120:
            raise ValueError('INVALID_TIMEOUT')
        if type(self.limit) is not int or not 1 <= self.limit <= 1048576:
            raise ValueError('INVALID_OUTPUT_BUDGET')
        if self.effort not in ('low', 'medium', 'high'):
            raise ValueError('INVALID_REASONING_EFFORT')
        self.transport = transport or _process_transport
        self.run_dir = Path(run_dir).resolve() if run_dir is not None else None

    def generate_structured(self, *, prompt, schema, input_refs, template_version):
        audit = {'provider': 'codex', 'auth_method': 'chatgpt', 'model': self.model,
                 'template_version': template_version, 'input_artifact_refs': dict(input_refs),
                 'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'STARTED',
                 'usage': None, 'cli_version': None, 'profile_version': 'codex-closed-input/v1',
                 'execution_mode': 'REAL_PROVIDER' if self.transport is _process_transport else 'INJECTED_TRANSPORT',
                 'timeout_seconds': self.timeout, 'max_response_bytes': self.limit,
                 'token_limit_enforced': False}

        def fail(code):
            audit['status'] = code
            raise ProviderError(code, audit) from None

        if not isinstance(prompt, str) or len(prompt.encode('utf-8')) > 120000:
            fail('INPUT_BUDGET_EXCEEDED')
        if self.run_dir is None or not self.run_dir.is_dir():
            fail('CURRENT_RUN_REQUIRED')
        executable = _find_codex()
        if not executable:
            fail('CODEX_EXECUTABLE_REQUIRED')
        # Inherit only normal host runtime/login locations, not API keys or app-injected secrets.
        keys = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP', 'USERPROFILE',
                'APPDATA', 'LOCALAPPDATA', 'HOMEDRIVE', 'HOMEPATH', 'HOME', 'CODEX_HOME',
                'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'NO_PROXY'}
        env = {key: value for key, value in os.environ.items() if key.upper() in keys}
        deadline = time.monotonic() + self.timeout

        def invoke(command, cwd, text='', limit=16384):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                fail('CODEX_TIMEOUT')
            result = self.transport(command, input_text=text, cwd=str(cwd), env=env,
                                    timeout=remaining, max_bytes=limit)
            if len(result.stdout) + len(result.stderr) > limit:
                fail('CODEX_OUTPUT_LIMIT')
            return result

        try:
            # A fresh directory contains schema only, never a previous reply or reference checklist.
            logs = self.run_dir / 'logs'
            logs.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='codex-call-', dir=logs) as raw:
                cwd = Path(raw)
                version = invoke([executable, '--version'], cwd)
                if version.returncode or version.stdout.decode().strip() != f'codex-cli {VERIFIED_CLI_VERSION}':
                    fail('CODEX_VERSION_UNVERIFIED')
                audit['cli_version'] = VERIFIED_CLI_VERSION
                login = invoke([executable, '-c', 'forced_login_method="chatgpt"', 'login', 'status'], cwd)
                if login.returncode or b'Logged in using ChatGPT' not in login.stdout + login.stderr:
                    fail('CODEX_CHATGPT_LOGIN_REQUIRED')
                schema_path = cwd / 'response.schema.json'
                schema_path.write_text(json.dumps(schema), encoding='utf-8')
                command = [executable, '-a', 'never', 'exec', '--ignore-user-config', '--strict-config',
                           '--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only',
                           '--model', self.model, '--json', '--color', 'never',
                           '--output-schema', str(schema_path), '--cd', str(cwd)]
                settings = ['forced_login_method="chatgpt"', 'web_search="disabled"',
                            'project_doc_max_bytes=0', 'history.persistence="none"',
                            'features.skip_host_skill_discovery=true',
                            f'model_reasoning_effort="{self.effort}"',
                            f'projects.{json.dumps(str(cwd))}.trust_level="untrusted"']
                settings += [f'features.{feature}=false' for feature in DISABLED_FEATURES]
                for setting in settings:
                    command.extend(['-c', setting])
                command.append('-')
                response = invoke(command, cwd, prompt, self.limit)
                if response.returncode:
                    fail('CODEX_EXEC_FAILED')
                messages, completed = [], 0
                for line in response.stdout.decode('utf-8').splitlines():
                    event = json.loads(line)
                    kind = event.get('type')
                    if kind in ('item.started', 'item.updated', 'item.completed'):
                        item = event['item']
                        if item.get('type') not in ('reasoning', 'agent_message'):
                            fail('CODEX_UNEXPECTED_TOOL_EVENT')
                        if kind == 'item.completed' and item['type'] == 'agent_message':
                            messages.append(item['text'])
                    elif kind == 'turn.completed':
                        completed += 1
                        usage = event.get('usage')
                        if isinstance(usage, dict):
                            audit['usage'] = {k: v for k, v in usage.items()
                                              if k in ('input_tokens', 'cached_input_tokens', 'output_tokens')
                                              and type(v) is int and v >= 0}
                    elif kind not in ('thread.started', 'turn.started'):
                        fail('CODEX_INCOMPLETE_OR_UNKNOWN_EVENT')
                if completed != 1 or len(messages) != 1:
                    fail('CODEX_INCOMPLETE')
                result = json.loads(messages[0])
                if not isinstance(result, dict):
                    fail('CODEX_OUTPUT_INVALID')
        except ProviderError:
            raise
        except subprocess.TimeoutExpired:
            fail('CODEX_TIMEOUT')
        except RuntimeError as exc:
            fail('CODEX_OUTPUT_LIMIT' if str(exc) == 'CODEX_OUTPUT_LIMIT' else 'CODEX_REQUEST_FAILED')
        except Exception:
            fail('CODEX_REQUEST_OR_OUTPUT_INVALID')
        audit['status'] = 'COMPLETED'
        return result, audit
