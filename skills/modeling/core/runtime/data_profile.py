"""Deterministic, non-imputing inspection of current-run UTF-8 tables."""
import csv
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import io
from pathlib import Path

from core.runtime.artifact_store import ArtifactStore
from core.runtime.problem_package import verify_package
from core.schema.artifact_meta import ArtifactIntegrityError


def numeric_cell(value):
    value = value.strip()
    if not value or len(value) > 128:
        raise ValueError('DATA_NUMERIC_CELL_REQUIRED')
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError('DATA_NUMERIC_CELL_REQUIRED') from None
    if not number.is_finite():
        raise ValueError('DATA_NONFINITE')
    if abs(number.adjusted()) > 100 or abs(number.as_tuple().exponent) > 128:
        raise ValueError('DATA_NUMERIC_RANGE_UNSUPPORTED')
    return Fraction(number)


def read_table(package, run_dir, run_id, asset_id):
    verify_package(package, run_dir, run_id)
    asset = next((a for a in package['content']['assets'] if a['id'] == asset_id), None)
    if asset is None or asset_id == 'statement':
        raise ValueError('DATA_ASSET_UNKNOWN')
    path = Path(run_dir) / asset['path']
    if path.suffix not in ('.csv', '.tsv'):
        raise ValueError('DATA_FORMAT_UNSUPPORTED')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != asset['sha256']:
        raise ArtifactIntegrityError('SNAPSHOT_HASH_MISMATCH')
    try:
        reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''),
                            delimiter='\t' if path.suffix == '.tsv' else ',', strict=True)
        headers = next(reader, [])
        if not headers or len(headers) > 256 or any(not h.strip() for h in headers) or len(set(headers)) != len(headers):
            raise ValueError('DATA_HEADERS_INVALID')
        rows = []
        for row in reader:
            if len(row) != len(headers):
                raise ValueError('DATA_ROW_WIDTH_INVALID')
            rows.append(row)
            if len(rows) > 10000 or len(rows) * len(headers) > 100000:
                raise ValueError('DATA_TABLE_SIZE_UNSUPPORTED')
        if not rows:
            raise ValueError('DATA_TABLE_EMPTY')
    except (csv.Error, UnicodeError):
        raise ValueError('DATA_TABLE_PARSE_ERROR') from None
    return headers, rows


def inspect_package(package, run_dir, run_id):
    verify_package(package, run_dir, run_id)
    assets = []
    for asset in package['content']['assets']:
        if asset['id'] == 'statement':
            continue
        item = {'asset_id': asset['id'], 'sha256': asset['sha256'], 'status': 'UNSUPPORTED'}
        if Path(asset['path']).suffix == '.xlsx':
            extraction = asset['extraction']
            summaries = []
            for sheet in extraction['sheets']:
                summaries.append({key: sheet[key] for key in ('sheet_id', 'name', 'rows', 'columns', 'state', 'merged_ranges')})
                summaries[-1].update(missing_count=sum(c['kind'] == 'blank' for c in sheet['cells']),
                                     formula_count=sum(c['kind'] == 'formula' for c in sheet['cells']))
            item.update(status='WORKBOOK_INSPECTED', solver_ready=False, sheets=summaries,
                        extraction_version=extraction['format_version'])
        if Path(asset['path']).suffix in ('.csv', '.tsv'):
            headers, rows = read_table(package, run_dir, run_id, asset['id'])
            columns = []
            for index, name in enumerate(headers):
                column = {'name': name, 'numeric_count': 0, 'missing_count': 0,
                          'text_count': 0, 'nonfinite_count': 0, 'minimum': None, 'maximum': None}
                values = []
                for row in rows:
                    value = row[index].strip()
                    if not value:
                        column['missing_count'] += 1
                        continue
                    try:
                        values.append(numeric_cell(value))
                        column['numeric_count'] += 1
                    except ValueError as exc:
                        if str(exc) == 'DATA_NUMERIC_RANGE_UNSUPPORTED':
                            raise
                        column['nonfinite_count' if str(exc) == 'DATA_NONFINITE' else 'text_count'] += 1
                if values:
                    column.update(minimum=str(min(values)), maximum=str(max(values)))
                columns.append(column)
            item.update(status='INSPECTED', row_count=len(rows), columns=columns)
        assets.append(item)
    verify_package(package, run_dir, run_id)
    meta = package['meta']
    return ArtifactStore(run_dir, run_id).register_json(
        artifact_type='data_profile', version=1,
        content={'problem_id': package['content']['problem_id'], 'assets': assets,
                 'scope': 'csv-tsv-xlsx-inspection/v1' if any(a['status'] == 'WORKBOOK_INSPECTED' for a in assets) else 'utf8-csv-tsv/v1', 'semantic_review': 'PENDING'},
        producer='data-inspector/v1', input_refs=[meta['artifact_id']],
        input_hashes={meta['artifact_id']: meta['content_sha256']})
