"""Current-run DOCX candidate lifecycle; no publication or visual PASS claims."""
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile

from core.runtime.artifact_store import ArtifactStore
from core.runtime.evidence_paper import _active, _register, check_candidate
from core.schema.artifact_meta import ArtifactError, content_sha256
from core.schema.gate_result import gate_check, gate_result, write_gate_result
from submission.compilers.bound_docx import render_docx, validate_docx
from submission.schema.academic_tables import build_table_spec, validate_table_spec
from submission.validation.docx_tables import inspect_tables
from core.runtime.active_registry import _atomic_write_json


def _tables(store, package, paper, snapshot, *, create=False):
    path = store.run_dir / 'table_spec.json'
    stored_path = store.run_dir / 'artifacts/.store/table_spec/000001.json'
    if create and not path.exists() and not stored_path.exists():
        if (store.run_dir / 'artifacts/paper_candidate.docx').exists() or (store.run_dir / 'artifacts/.store/docx_candidate/000001.json').exists():
            raise ValueError('TABLE_LOCK_MISSING_ON_EXISTING_CANDIDATE')
        content = build_table_spec(paper['content'], snapshot)
        envelope = _register(store, 'table_spec', content, [package, paper])
        with path.open('x', encoding='utf-8') as stream:
            json.dump(content, stream, ensure_ascii=False, indent=2)
    else:
        envelope = _active(store, 'table_spec')
    content = json.loads(path.read_text(encoding='utf-8'))
    refs = {e['meta']['artifact_id']: e['meta']['content_sha256'] for e in (package, paper)}
    if (content_sha256(content) != envelope['meta']['content_sha256']
            or envelope['meta']['input_hashes'] != refs or envelope['meta']['input_refs'] != list(refs)):
        raise ValueError('TABLE_LOCK_OR_DEPENDENCY_DRIFT')
    validate_table_spec(content, paper['content'], snapshot)
    return envelope


def _record_tables(run_dir, run_id, report):
    report = dict(report, run_id=run_id)
    _atomic_write_json(Path(run_dir) / 'gates/table_checks.json', report)
    lines = ['# Table checks', '', 'status: ' + report['status'],
             'run_id: ' + run_id, 'docx_sha256: ' + report.get('docx_sha256', 'UNAVAILABLE'),
             'table_spec_sha256: ' + report.get('table_spec_sha256', 'UNAVAILABLE'),
             'visual_review: PENDING', '',
             'Actual DOCX ZIP/XML inspected independently; no visual or publication approval.', '',
             'Detailed evidence: gates/table_checks.json', '']
    lines.extend('- ' + ('PASS' if c['passed'] else 'FAIL') + ' ' + c['code'] for c in report['checks'])
    target = Path(run_dir) / 'table_checks.md'
    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _table_failure(run_dir, run_id, exc):
    # Preserve any independent findings and invalidate previously passing records.
    path = Path(run_dir) / 'gates/table_checks.json'
    try:
        report = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        report = {'checks': []}
    if not isinstance(report, dict): report = {}
    if not isinstance(report.get('checks'), list): report['checks'] = []
    report['checks'] = [c for c in report['checks'] if isinstance(c, dict)
                        and isinstance(c.get('code'), str) and type(c.get('passed')) is bool]
    for key in ('docx_sha256', 'table_spec_sha256'):
        if not isinstance(report.get(key), str): report.pop(key, None)
    report['status'] = 'FAIL'
    report['checks'].append({'code': 'CURRENT_RUN_TABLE_GATE', 'passed': False,
                             'actual': str(exc)})
    _record_tables(run_dir, run_id, report)


def _inputs(run_dir, run_id):
    if check_candidate(run_dir, run_id)['status'] != 'PASS':
        raise ValueError('DOCX_EVIDENCE_CHAIN_INVALID')
    store = ArtifactStore(run_dir, run_id)
    package = _active(store, 'problem_package')
    spec = _active(store, 'paper_spec')
    snapshot = package['content']['configuration']['docx_template']
    return store, package, spec, snapshot


def check_docx_candidate(run_dir, run_id):
    try:
        store, package, spec, snapshot = _inputs(run_dir, run_id)
        table_spec = _tables(store, package, spec, snapshot)
        receipt = _active(store, 'docx_candidate')
        refs = {e['meta']['artifact_id']: e['meta']['content_sha256'] for e in (package, spec, table_spec)}
        if receipt['meta']['input_hashes'] != refs or receipt['meta']['input_refs'] != list(refs):
            raise ValueError('DOCX_DEPENDENCY_NOT_CURRENT')
        data = (Path(run_dir) / 'artifacts/paper_candidate.docx').read_bytes()
        inspection = inspect_tables(data, table_spec['content'])
        _record_tables(run_dir, run_id, inspection)
        if inspection['status'] != 'PASS': raise ValueError('INDEPENDENT_TABLE_CHECK_FAILED')
        metrics = validate_docx(data, spec['content'], snapshot, table_spec['content'])
        expected = {'run_id': run_id, 'path': 'artifacts/paper_candidate.docx',
                    'sha256': metrics['sha256'], 'template_sha256': snapshot['sha256'],
                    'template_contract_sha256': snapshot['contract_sha256'],
                    'paper_spec_sha256': spec['meta']['content_sha256'],
                    'table_spec_sha256': table_spec['meta']['content_sha256'], 'visual_review': 'PENDING'}
        if content_sha256(receipt['content']) != content_sha256(expected):
            raise ValueError('DOCX_RECEIPT_MISMATCH')
        return gate_result('docx_candidate', [gate_check('DOCX_CURRENT_SOURCE_CONTENT_AND_TEMPLATE', True,
                                                        actual=metrics)], run_id=run_id)
    except (ArtifactError, ValueError, OSError, KeyError, TypeError, BadZipFile) as exc:
        _table_failure(run_dir, run_id, exc)
        report = gate_result('docx_candidate', [gate_check('DOCX_CANDIDATE_INVALID', False)], run_id=run_id)
        write_gate_result(Path(run_dir) / 'gates/docx_candidate.json', report)
        return report


def build_docx_candidate(run_dir, run_id):
    try:
        store, package, spec, snapshot = _inputs(run_dir, run_id)
        table_spec = _tables(store, package, spec, snapshot, create=True)
        data = render_docx(spec['content'], snapshot, table_spec['content'])
        inspection = inspect_tables(data, table_spec['content'])
        _record_tables(run_dir, run_id, inspection)
        if inspection['status'] != 'PASS':
            rejected = Path(run_dir) / ('artifacts/rejected_' + hashlib.sha256(data).hexdigest() + '.docx')
            if not rejected.exists():
                with rejected.open('xb') as stream: stream.write(data)
            raise ValueError('INDEPENDENT_TABLE_CHECK_FAILED')
        validate_docx(data, spec['content'], snapshot, table_spec['content'])
        if _inputs(run_dir, run_id)[1:3] != (package, spec):
            raise ValueError('DOCX_INPUT_CHANGED')
        _tables(store, package, spec, snapshot)
        target = Path(run_dir) / 'artifacts/paper_candidate.docx'
        # A retry cannot overwrite a changed file or adopt a foreign artifact.
        if target.exists():
            _active(store, 'docx_candidate')
        else:
            with target.open('xb') as stream:
                stream.write(data)
            _register(store, 'docx_candidate', {
                'run_id': run_id, 'path': 'artifacts/paper_candidate.docx',
                'sha256': hashlib.sha256(data).hexdigest(), 'template_sha256': snapshot['sha256'],
                'template_contract_sha256': snapshot['contract_sha256'],
                'paper_spec_sha256': spec['meta']['content_sha256'],
                'table_spec_sha256': table_spec['meta']['content_sha256'],
                'visual_review': 'PENDING'}, [package, spec, table_spec])
        report = check_docx_candidate(run_dir, run_id)
        write_gate_result(Path(run_dir) / 'gates/docx_candidate.json', report)
        return {'status': 'READY_FOR_REVIEW' if report['status'] == 'PASS' else 'GATE_FAILED',
                'failure_code': None if report['status'] == 'PASS' else 'DOCX_CANDIDATE_INVALID',
                'docx_candidate': 'artifacts/paper_candidate.docx', 'visual_review': 'PENDING'}
    except (ArtifactError, ValueError, OSError, KeyError, TypeError, BadZipFile) as exc:
        _table_failure(run_dir, run_id, exc)
        write_gate_result(Path(run_dir) / 'gates/docx_candidate.json', gate_result(
            'docx_candidate', [gate_check('DOCX_CANDIDATE_INVALID', False)], run_id=run_id))
        return {'status': 'BLOCKED', 'failure_code': 'DOCX_CANDIDATE_INVALID', 'visual_review': 'PENDING'}
