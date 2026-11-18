"""Local release receipts. No official upload, signature or reviewer authentication.

All local evidence is trusted only within the user's filesystem trust boundary.
Manual and automatic modes both require human quality/compliance evidence.
Automatic mode removes only the separate publish-button approval.
"""
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

from core.runtime.active_registry import _atomic_write_json
from core.runtime.contest_readiness import PROFILE_PATH, verify_handoff
from core.schema.gate_result import validate_gate_result
from submission.gates.pdf_page_gate import check_pdf_pages

REVIEW_CHECKS = ('paper_quality', 'visual_layout', 'table_spec', 'ai_declaration',
                 'ai_details_pdf', 'aigc_heuristic_review', 'recomputed_results',
                 'anonymity', 'supporting_materials', 'pdf_matches_docx')
V9_GATES = {'problem_schema': 'problem_schema_evidence', 'problem_coverage': 'problem_coverage',
            'model_plan': 'model_plan', 'derivation': 'derivation',
            'quadratic_solution': 'quadratic_solution', 'evidence_paper': 'evidence_paper',
            'docx_candidate': 'docx_candidate'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('RELEASE_PATH_OUTSIDE_RUN')
    return path


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if relative.split('/')[0] == 'release' or path.name.endswith('.lock'):
            continue
        if path.is_file():
            within(root, relative)
            result[relative] = digest(path)
    return result


@contextmanager
def locked(root):
    folder = within(root, 'release')
    folder.mkdir(exist_ok=True)
    path = folder / '.controller.lock'
    handle = path.open('x')
    try:
        with handle:
            yield
    finally:
        path.unlink()


def stage_candidate(run_dir):
    root = Path(run_dir).resolve()
    with locked(root):
        manifest = read(root / 'manifest.json')
        source = next((p for p in ('artifacts/paper_candidate.docx', 'artifacts/submission.docx')
                       if within(root, p).is_file()), None)
        if source is None:
            return {'status': 'NO_CANDIDATE', 'official_submission': 'NOT_PERFORMED'}
        snapshot = {'schema': 'forge-release-candidate/v1', 'run_id': manifest['run_id'],
                    'source': source, 'files': inventory(root), 'status': 'AWAITING_REVIEW',
                    'release_scope': 'V9_REVIEW_REQUIRED' if manifest.get('schema') == 'forge-problem-execution/v1' else 'UNSUPPORTED_OR_REFERENCE_ONLY',
                    'official_submission': 'NOT_PERFORMED'}
        encoded = json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode('utf-8')
        key = hashlib.sha256(encoded).hexdigest()
        target = within(root, 'release/candidates/' + key + '.json')
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            if target.read_bytes() != encoded:
                raise ValueError('CANDIDATE_RECEIPT_CHANGED')
        else:
            with target.open('xb') as stream:
                stream.write(encoded)
        return {'status': 'AWAITING_REVIEW', 'candidate_sha256': key,
                'candidate_path': target.relative_to(root).as_posix(),
                'release_scope': snapshot['release_scope'],
                'official_submission': 'NOT_PERFORMED'}


def reviewed(record, key, run_id):
    try:
        timestamp = datetime.fromisoformat(record['reviewed_at'])
        return (record['status'] == 'APPROVED' and record['candidate_sha256'] == key
                and record['run_id'] == run_id and isinstance(record['reviewer'], str)
                and bool(record['reviewer'].strip()) and timestamp.tzinfo is not None
                and timestamp <= datetime.now(timezone.utc))
    except (KeyError, TypeError, ValueError):
        return False


def qualification_ok(record, root, evidence=None):
    """Check external acceptance records against saved real-run bytes, not their truth."""
    try:
        cases = record['cases']
        if record['status'] != 'APPROVED' or len(cases) != 3:
            return False
        if len({c['problem_id'] for c in cases}) != 3 or len({c['run_id'] for c in cases}) != 3:
            return False
        for case in cases:
            if (case['status'] != 'APPROVED' or not case['reviewer'].strip()
                    or not case['official_source_url'].startswith('https://') or not case['evidence']):
                return False
            for relative, expected in case['evidence'].items():
                if digest(within(root, relative)) != expected:
                    return False
                if evidence is not None:
                    evidence[relative] = expected
            manifest_path = case['manifest_path']
            if manifest_path not in case['evidence']:
                return False
            manifest = read(within(root, manifest_path))
            if (manifest['run_id'] != case['run_id'] or manifest['execution_mode'] != 'REAL_PROVIDER'
                    or manifest['status'] != 'READY_FOR_REVIEW'):
                return False
            audit_path = case['provider_audit_path']
            if audit_path not in case['evidence']:
                return False
            audit = read(within(root, audit_path))
            if audit.get('status') != 'COMPLETED' or not audit.get('model'):
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def release(run_dir, candidate_id, *, mode='manual'):
    root = Path(run_dir).resolve()
    if mode not in ('manual', 'automatic') or not re.fullmatch('[a-f0-9]{64}', candidate_id):
        raise ValueError('INVALID_RELEASE_POLICY_OR_CANDIDATE')
    with locked(root):
        blockers = []
        evidence = {}
        def require(ok, code):
            if not ok: blockers.append(code)
        def review_file(name):
            path = within(root, 'release/reviews/' + name + '.json')
            if not path.is_file(): return {}
            evidence[path.relative_to(root).as_posix()] = digest(path)
            return read(path)
        try:
            candidate_path = within(root, 'release/candidates/' + candidate_id + '.json')
            require(digest(candidate_path) == candidate_id, 'CANDIDATE_RECEIPT_CHANGED')
            candidate = read(candidate_path)
            manifest = read(root / 'manifest.json')
            run_id = manifest['run_id']
            require(candidate['run_id'] == run_id, 'WRONG_RUN')
            require(manifest.get('schema') == 'forge-problem-execution/v1', 'UNSUPPORTED_RUN_SCHEMA_REFERENCE_ONLY')
            require(candidate['files'] == inventory(root), 'CANDIDATE_BYTES_CHANGED')
            require(manifest.get('status') == 'READY_FOR_REVIEW', 'RUN_NOT_REVIEWABLE')
            require(manifest.get('execution_mode') == 'REAL_PROVIDER', 'REAL_EXECUTION_REQUIRED')
            require(not verify_handoff(root), 'HANDOFF_INTEGRITY_FAILED')
            for name in sorted(V9_GATES):
                try:
                    report = read(root / 'gates' / (name + '.json'))
                    validate_gate_result(report)
                    require(report['status'] == 'PASS' and report['run_id'] == run_id and report['gate'] == V9_GATES[name],
                            'GATE_FAILED:' + name)
                except (OSError, ValueError, KeyError, TypeError):
                    blockers.append('GATE_MISSING_OR_INVALID:' + name)
            human = review_file('human')
            require(reviewed(human, candidate_id, run_id) and
                    all(human.get('checks', {}).get(c) is True for c in REVIEW_CHECKS), 'HUMAN_REVIEW_PENDING')
            rules = review_file('rules')
            profile_hash = digest(PROFILE_PATH)
            profile = read(PROFILE_PATH)
            now = datetime.now(timezone.utc)
            try:
                age = (now - datetime.fromisoformat(rules['reviewed_at'])).total_seconds() / 86400
                profile_age = (now.astimezone(timezone(timedelta(hours=8))).date() - date.fromisoformat(profile['verified_on'])).days
                fresh = 0 <= age <= profile['local_max_review_age_days'] and 0 <= profile_age <= profile['local_max_review_age_days']
            except (KeyError, TypeError, ValueError):
                fresh = False
            require(reviewed(rules, candidate_id, run_id)
                    and fresh and rules.get('profile_sha256') == profile_hash
                    and rules.get('seven_days_is_local_policy') is True
                    and rules.get('official_sources_checked') is True, 'RULES_REVIEW_PENDING')
            require(qualification_ok(review_file('acceptance'), root, evidence), 'REAL_ACCEPTANCE_0_OF_3_OR_INVALID')
            pages = check_pdf_pages(run_id, root / 'artifacts/submission.pdf', review_file('pdf_boundaries'))
            require(pages['status'] == 'PASS', 'PDF_PAGE_GATE_FAILED')
            if mode == 'manual':
                require(reviewed(review_file('publish'), candidate_id, run_id), 'PUBLISH_CONFIRMATION_PENDING')
            # Recheck immediately before committing: no stale approved bytes.
            require(candidate['files'] == inventory(root), 'EVIDENCE_CHANGED_DURING_RELEASE')
            require(all(digest(within(root, p)) == h for p, h in evidence.items()), 'REVIEW_CHANGED_DURING_RELEASE')
            require(digest(PROFILE_PATH) == profile_hash, 'RULE_PROFILE_CHANGED_DURING_RELEASE')
        except (OSError, ValueError, KeyError, TypeError):
            blockers.append('RELEASE_EVIDENCE_MISSING_OR_INVALID')
        receipt = {'schema': 'forge-release-receipt/v1', 'candidate_sha256': candidate_id,
                   'status': 'BLOCKED' if blockers else 'RELEASED', 'mode': mode,
                   'blockers': sorted(set(blockers)), 'official_submission': 'NOT_PERFORMED',
                   'created_at': datetime.now(timezone.utc).isoformat(), 'review_sha256': evidence,
                   'trust_boundary': 'Local hash binding; not signatures or authenticated human identity.'}
        event_id = uuid.uuid4().hex
        if not blockers:
            folder = within(root, 'release/versions/' + event_id)
            folder.mkdir(parents=True)
            for relative in (candidate['source'], 'artifacts/submission.pdf'):
                data = within(root, relative).read_bytes()
                if hashlib.sha256(data).hexdigest() != candidate['files'][relative]:
                    raise ValueError('SOURCE_CHANGED_DURING_COPY')
                (folder / Path(relative).name).write_bytes(data)
            receipt['version'] = folder.relative_to(root).as_posix()
            _atomic_write_json(folder / 'receipt.json', receipt)
        _atomic_write_json(within(root, 'release/events/' + event_id + '.json'), receipt)
        if not blockers:
            _atomic_write_json(within(root, 'release/current.json'), receipt)
        return receipt


def execute_request(config_path):
    path = Path(config_path).resolve()
    config = read(path)
    if (set(config) - {'schema', 'run_dir', 'action', 'candidate_sha256', 'mode', 'reason'}
            or config.get('schema') != 'forge-release-request/v1'):
        raise ValueError('INVALID_RELEASE_REQUEST')
    root = (path.parent / config['run_dir']).resolve()
    if config['action'] == 'candidate':
        return stage_candidate(root)
    if config['action'] == 'publish':
        return release(root, config['candidate_sha256'], mode=config.get('mode', 'manual'))
    if config['action'] == 'revoke' and isinstance(config.get('reason'), str) and config['reason'].strip():
        with locked(root):
            receipt = {'status': 'REVOKED', 'reason': config['reason'],
                       'previous': read(root / 'release/current.json'),
                       'created_at': datetime.now(timezone.utc).isoformat(),
                       'official_submission': 'NOT_PERFORMED'}
            _atomic_write_json(root / 'release/events' / (uuid.uuid4().hex + '.json'), receipt)
            _atomic_write_json(root / 'release/current.json', receipt)
            return receipt
    raise ValueError('INVALID_RELEASE_ACTION')
