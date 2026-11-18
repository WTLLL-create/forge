"""Explicit current-run input snapshots; no project or historical output scanning."""
from pathlib import Path
import copy
import hashlib

from core.runtime.artifact_store import ArtifactStore
from core.schema.artifact_meta import ArtifactIntegrityError, content_sha256
from core.runtime.document_extraction import extract_pdf, extract_xlsx, InputExtractionError

TEXT_SUFFIXES = {'.txt', '.md', '.csv', '.tsv', '.json'}


def package_prompt_content(package):
    """Deterministic projection, not a new or mutated source artifact.

Cell values already occur in segments; retain exceptional type and format
annotations without repeating the full cell matrix in model context.
"""
    content = copy.deepcopy(package['content'])
    if 'docx_template' in content.get('configuration', {}):
        content['configuration']['docx_template'].pop('base64', None)
    for asset in content['assets']:
        for sheet in asset.get('extraction', {}).get('sheets', []):
            cells = sheet.pop('cells')
            sheet['special_cell_types'] = {c['coordinate']: c['kind'] for c in cells
                                           if c['kind'] in {'formula', 'error', 'datetime'}}
            sheet['number_formats'] = {c['coordinate']: c['number_format'] for c in cells
                                       if c['number_format'] != 'General'}
    return content


def create_package(run_dir, run_id, problem_id, statement, attachments=(), *, configuration=None):
    run_dir = Path(run_dir).resolve()
    statement = Path(statement).resolve()
    paths = [statement, *(Path(p).resolve() for p in attachments)]
    if not problem_id or len(paths) > 16 or len(set(paths)) != len(paths):
        raise ValueError('INVALID_PACKAGE_INPUTS')
    if statement.suffix.lower() not in {'.txt', '.md', '.pdf'}:
        raise ValueError('STATEMENT_REQUIRES_UTF8_TEXT')
    for path in paths:
        if not path.is_file() or path.stat().st_size > 2_000_000:
            raise ValueError('MISSING_OR_OVERSIZED_INPUT')
        if any(p.lower() in {'runs', 'artifacts', 'gates', 'logs', '.git'} for p in path.parts):
            raise ValueError('HISTORICAL_OR_INTERNAL_INPUT_FORBIDDEN')
        if path.name.lower().startswith('.env') or path.suffix.lower() in {'.key', '.pem'}:
            raise ValueError('SECRET_INPUT_FORBIDDEN')
    input_dir = run_dir / 'inputs'
    input_dir.mkdir(parents=True, exist_ok=False)
    assets = []
    total_chars = 0
    for index, path in enumerate(paths):
        asset_id = 'statement' if index == 0 else f'attachment_{index}'
        data = path.read_bytes()
        if len(data) > 2_000_000:
            raise ValueError('MISSING_OR_OVERSIZED_INPUT')
        target = input_dir / (asset_id + path.suffix.lower())
        with target.open('xb') as handle:
            handle.write(data)
        segments = {}
        extraction = None
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = data.decode('utf-8-sig')
            segments = {f'L{i}': line for i, line in enumerate(text.splitlines(), 1) if line.strip()}
        elif path.suffix.lower() == '.pdf':
            segments, extraction = extract_pdf(data)
        elif path.suffix.lower() == '.xlsx':
            segments, extraction = extract_xlsx(data)
        total_chars += len(text) if path.suffix.lower() in TEXT_SUFFIXES else sum(len(s) for s in segments.values())
        if total_chars > 60_000:
            raise InputExtractionError('INPUT_CONTEXT_BUDGET_EXCEEDED')
        if index == 0 and not segments:
            raise ValueError('EMPTY_STATEMENT')
        asset = {'id': asset_id, 'filename': path.name, 'path': target.relative_to(run_dir).as_posix(),
                       'sha256': hashlib.sha256(data).hexdigest(), 'segments': segments,
                       'inspection': 'text' if segments else 'opaque'}
        if extraction is not None:
            extraction['source_sha256'] = asset['sha256']
            asset['extraction'] = extraction
            asset['inspection'] = 'structured' if path.suffix.lower() == '.xlsx' else 'text'
        assets.append(asset)
    content = {'problem_id': problem_id, 'assets': assets, 'extraction_version': 'document-inputs/v1' if any('extraction' in a for a in assets) else 'utf8-lines/v1',
               'configuration': configuration or {}}
    return ArtifactStore(run_dir, run_id).register_json(
        artifact_type='problem_package', version=1, content=content, producer='problem_packager')


def verify_package(package, run_dir, run_id):
    run_dir = Path(run_dir).resolve()
    meta = package['meta']
    if meta['run_id'] != run_id or meta['content_sha256'] != content_sha256(package['content']):
        raise ArtifactIntegrityError('PACKAGE_IDENTITY_OR_HASH_MISMATCH')
    store = ArtifactStore(run_dir, run_id)
    store.registry.verify_integrity()
    pointer = store.registry._load()['artifacts'].get('problem_package', {})
    if pointer.get('artifact_id') != meta['artifact_id'] or pointer.get('sha256') != meta['content_sha256']:
        raise ArtifactIntegrityError('PACKAGE_NOT_ACTIVE')
    for asset in package['content']['assets']:
        target = (run_dir / asset['path']).resolve()
        if not target.is_relative_to(run_dir / 'inputs'):
            raise ArtifactIntegrityError('PACKAGE_PATH_ESCAPE')
        if hashlib.sha256(target.read_bytes()).hexdigest() != asset['sha256']:
            raise ArtifactIntegrityError('SNAPSHOT_HASH_MISMATCH')
    return True
