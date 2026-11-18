"""Dated contest metadata checks and evidence-bound AI disclosure drafts.

No network access, human approval, document formatting or release authorization.
The profile is locally maintained evidence, not a live official-rule service.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from core.runtime.active_registry import _atomic_write_json

WORKSPACE = Path(__file__).resolve().parents[4]
PROFILE_PATH = WORKSPACE / 'knowledge/contest_rules/cumcm_2026.json'
AUDITS = {
    'logs/provider.json': '题意分析',
    'logs/model_plan_provider.json': '模型路线与验证计划',
    'logs/derivation_provider.json': '数学推导',
    'logs/solver_plan_provider.json': '计算映射计划',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate_context(context, *, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('CONTEST_TIMEZONE_REQUIRED')
    report = {'schema': 'forge-contest-preflight/v1', 'checked_at': now.isoformat(),
              'status': 'NOT_ASSESSED', 'submission_ready': False,
              'human_review': 'PENDING', 'problem_source_verification': 'PENDING',
              'live_rules_recheck': 'PENDING', 'warnings': []}
    if context is None:
        report['warnings'] = ['CONTEST_CONTEXT_NOT_BOUND']
        return report
    required = {'profile_id', 'mode', 'problem_origin', 'external_retrieval'}
    if (not isinstance(context, dict) or not required <= set(context)
            or set(context) - required - {'official_source_url'}):
        raise ValueError('INVALID_CONTEST_CONTEXT')
    if any(not isinstance(value, str) or not value.strip() for value in context.values()):
        raise ValueError('INVALID_CONTEST_CONTEXT')
    if context['profile_id'] != 'cumcm_2026':
        raise ValueError('UNKNOWN_CONTEST_PROFILE')
    if context['mode'] not in ('practice', 'competition') or context['problem_origin'] not in ('practice', 'official'):
        raise ValueError('INVALID_CONTEST_MODE_OR_ORIGIN')
    # This closed-input implementation has no general-web retrieval adapter.
    if context['external_retrieval'] != 'disabled':
        raise ValueError('EXTERNAL_RETRIEVAL_NOT_SUPPORTED')
    raw = PROFILE_PATH.read_bytes()
    profile = json.loads(raw)
    if profile['schema'] != 'forge-contest-profile/v1' or profile['profile_id'] != context['profile_id']:
        raise ValueError('INVALID_CONTEST_PROFILE')
    today = now.astimezone(timezone(timedelta(hours=8))).date()
    age = (today - date.fromisoformat(profile['verified_on'])).days
    if age < 0:
        raise ValueError('RULE_REVIEW_DATE_IN_FUTURE')
    if age > profile['local_max_review_age_days']:
        if context['mode'] == 'competition':
            raise ValueError('CONTEST_RULES_REQUIRE_RECHECK')
        report['warnings'].append('PRACTICE_RULE_SNAPSHOT_STALE')
    if context['mode'] == 'competition' and context['problem_origin'] != 'official':
        raise ValueError('COMPETITION_REQUIRES_OFFICIAL_PROBLEM')
    if context['problem_origin'] == 'official':
        if now < datetime.fromisoformat(profile['problem_release_at']):
            raise ValueError('OFFICIAL_PROBLEM_NOT_RELEASED')
        url = urlsplit(context.get('official_source_url', ''))
        if (url.scheme != 'https' or url.hostname not in profile['official_problem_hosts']
                or url.username or url.password or not url.path or url.path == '/'):
            raise ValueError('OFFICIAL_PROBLEM_SOURCE_REQUIRED')
    elif 'official_source_url' in context:
        raise ValueError('PRACTICE_MUST_NOT_CLAIM_OFFICIAL_SOURCE')
    report.update(status='PRECHECK_ONLY', context=dict(context), profile=profile,
                  profile_sha256=hashlib.sha256(raw).hexdigest())
    return report


def write_handoff(run_dir, manifest):
    """Collect existing audit evidence without inventing adoption or review."""
    root = Path(run_dir)
    evidence = {}
    calls = []
    for relative, stage in AUDITS.items():
        path = root / relative
        if not path.is_file():
            continue
        audit = json.loads(path.read_text(encoding='utf-8'))
        evidence[relative] = digest(path)
        calls.append({'stage': stage, 'audit_path': relative,
                      'provider': audit.get('provider'), 'model': audit.get('model'),
                      'tool_version': audit.get('cli_version'),
                      'prompt_template_version': audit.get('template_version'),
                      'created_at': audit.get('created_at'), 'status': audit.get('status'),
                      'adoption': None, 'manual_changes': None, 'verification': None,
                      'human_review': 'PENDING'})
    registry = root / 'active_artifacts.json'
    if registry.is_file():
        evidence['active_artifacts.json'] = digest(registry)
        for pointer in json.loads(registry.read_text(encoding='utf-8'))['artifacts'].values():
            relative = pointer['path']
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('HANDOFF_ARTIFACT_MISSING_OR_OUTSIDE_RUN')
            evidence[relative] = digest(path)
    # Bind source bytes and gate bytes as well as their registered metadata.
    for folder in ('inputs', 'gates'):
        for path in (root / folder).rglob('*'):
            if path.is_file():
                if not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError('HANDOFF_EVIDENCE_OUTSIDE_RUN')
                evidence[path.relative_to(root).as_posix()] = digest(path)
    for relative in ('artifacts/paper_candidate.md', 'artifacts/paper_candidate.docx',
                     'table_spec.json', 'table_checks.md'):
        path = root / relative
        if path.is_file():
            evidence[relative] = digest(path)
    record = {'schema': 'forge-ai-usage-handoff/v1', 'run_id': manifest['run_id'],
              'created_at': datetime.now(timezone.utc).isoformat(),
              'status': 'DRAFT', 'human_review': 'PENDING', 'submission_ready': False,
              'execution_mode': manifest['execution_mode'], 'calls': calls,
              'evidence_sha256': evidence,
              'scope': 'Only calls recorded by this run; not a complete team AI declaration.',
              'integrity_boundary': 'Local SHA-256 binding only; not a signature or reviewer identity proof. An actor able to rewrite both manifest and evidence can replace the chain.',
              'official_submission': 'NOT_PERFORMED',
              'required_manual_steps': [
                  '补充团队在本运行之外使用的AI工具、版本、目的和过程。',
                  '逐项填写采纳、人工修改、复算与核验情况；不得由AI冒充人工审核。',
                  '核对当届官方及赛区要求；国赛使用AI时在参考文献前声明，详情PDF放入支撑材料。',
                  '此JSON不替代AI工具使用详情.pdf；生成并检查PDF后方可纳入提交包。',
              ]}
    _atomic_write_json(root / 'ai_usage_handoff.json', record)
    return {'path': 'ai_usage_handoff.json', 'sha256': digest(root / 'ai_usage_handoff.json'),
            'human_review': 'PENDING'}


def verify_handoff(run_dir):
    """Check current bytes against the draft, not the truth of human approval."""
    root = Path(run_dir).resolve()
    try:
        handoff = json.loads((root / 'ai_usage_handoff.json').read_text(encoding='utf-8'))
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        failures = []
        if (handoff['run_id'] != manifest['run_id'] or handoff['schema'] != 'forge-ai-usage-handoff/v1'
                or digest(root / 'ai_usage_handoff.json') != manifest['ai_usage_handoff']['sha256']):
            failures.append('HANDOFF_CHANGED_OR_WRONG_RUN')
        for relative, expected in handoff['evidence_sha256'].items():
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file() or digest(path) != expected:
                failures.append('EVIDENCE_CHANGED:' + relative)
        return failures
    except (OSError, ValueError, KeyError, TypeError):
        return ['HANDOFF_INVALID_OR_MISSING']
