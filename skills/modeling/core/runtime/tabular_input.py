"""Deterministic current-run XLSX selection; no joins, inference, or imputation."""
import copy
from pathlib import Path
import re

from core.runtime.artifact_store import ArtifactStore
from core.runtime.data_profile import numeric_cell
from core.runtime.problem_package import verify_package


class TabularInputError(ValueError):
    """Safe input-stage failure code for the workflow manifest."""


def _column_number(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Z]{1,3}', value):
        raise ValueError('TABULAR_COLUMN_INVALID')
    result = 0
    for char in value:
        result = result * 26 + ord(char) - ord('A') + 1
    return result


def validate_selection(selection):
    required = {'asset_id', 'sheet_id', 'header_row', 'first_data_row', 'last_data_row', 'columns'}
    if not isinstance(selection, dict) or not required <= set(selection) or set(selection) - required - {'missing_policy'}:
        raise ValueError('TABULAR_SELECTION_INVALID')
    result = copy.deepcopy(selection)
    result.setdefault('missing_policy', 'reject')
    if result['missing_policy'] not in ('reject', 'drop_row'):
        raise ValueError('TABULAR_MISSING_POLICY_INVALID')
    for key in ('asset_id', 'sheet_id'):
        if not isinstance(result[key], str) or not result[key].strip() or len(result[key]) > 100:
            raise ValueError('TABULAR_SELECTION_INVALID')
    for key in ('header_row', 'first_data_row', 'last_data_row'):
        if type(result[key]) is not int or not 1 <= result[key] <= 10000:
            raise ValueError('TABULAR_ROW_RANGE_INVALID')
    if not result['header_row'] < result['first_data_row'] <= result['last_data_row']:
        raise ValueError('TABULAR_ROW_RANGE_INVALID')
    columns = result['columns']
    if not isinstance(columns, list) or not 1 <= len(columns) <= 256:
        raise ValueError('TABULAR_COLUMNS_INVALID')
    for column in columns:
        if not isinstance(column, dict) or set(column) != {'column', 'name', 'expected_header'}:
            raise ValueError('TABULAR_COLUMNS_INVALID')
        if any(not isinstance(v, str) or not v.strip() or len(v) > 256 for v in column.values()):
            raise ValueError('TABULAR_COLUMNS_INVALID')
        if _column_number(column['column']) > 256:
            raise ValueError('TABULAR_COLUMN_INVALID')
    if len({c['column'] for c in columns}) != len(columns) or len({c['name'] for c in columns}) != len(columns):
        raise ValueError('TABULAR_DUPLICATE_COLUMN')
    return result


def build_tabular_input(package, run_dir, run_id):
    try:
        return _build_tabular_input(package, run_dir, run_id)
    except ValueError as exc:
        code = str(exc)
        if not re.fullmatch(r'(?:TABULAR|DATA)_[A-Z_]+', code):
            code = 'TABULAR_INPUT_INVALID'
        raise TabularInputError(code) from None


def _build_tabular_input(package, run_dir, run_id):
    verify_package(package, run_dir, run_id)
    selection = validate_selection(package['content']['configuration'].get('data_selection'))
    asset = next((a for a in package['content']['assets'] if a['id'] == selection['asset_id']), None)
    if not asset or Path(asset['path']).suffix != '.xlsx':
        raise ValueError('TABULAR_XLSX_ASSET_REQUIRED')
    sheet = next((s for s in asset['extraction']['sheets'] if s['sheet_id'] == selection['sheet_id']), None)
    if sheet is None:
        raise ValueError('TABULAR_SHEET_UNKNOWN')
    if selection['last_data_row'] > sheet['rows']:
        raise ValueError('TABULAR_ROW_RANGE_INVALID')
    columns = selection['columns']
    if any(_column_number(c['column']) > sheet['columns'] for c in columns):
        raise ValueError('TABULAR_COLUMN_UNKNOWN')
    selected_rows = {selection['header_row'], *range(selection['first_data_row'], selection['last_data_row'] + 1)}
    selected_columns = {_column_number(c['column']) for c in columns}
    for merged in sheet['merged_ranges']:
        start, end = merged.split(':')
        first = re.fullmatch(r'([A-Z]+)(\d+)', start)
        last = re.fullmatch(r'([A-Z]+)(\d+)', end)
        if (any(_column_number(first[1]) <= c <= _column_number(last[1]) for c in selected_columns)
                and any(int(first[2]) <= r <= int(last[2]) for r in selected_rows)):
            raise ValueError('TABULAR_MERGED_CELL')
    cells = {c['coordinate']: c for c in sheet['cells']}
    for column in columns:
        cell = cells[column['column'] + str(selection['header_row'])]
        if cell['kind'] != 'text' or cell['value'] != column['expected_header']:
            raise ValueError('TABULAR_HEADER_MISMATCH')
    rows, source_rows, dropped = [], [], []
    for number in range(selection['first_data_row'], selection['last_data_row'] + 1):
        selected = [cells[c['column'] + str(number)] for c in columns]
        # Validate every selected cell before applying a missing-row policy:
        # a blank must not hide a formula/error in the same dropped row.
        if any(c['kind'] not in {'number', 'blank'} for c in selected):
            raise ValueError('TABULAR_NONNUMERIC_CELL')
        values = []
        for cell in selected:
            if cell['kind'] == 'number':
                numeric_cell(str(cell['value']))
                values.append(str(cell['value']))
        missing = [c['coordinate'] for c in selected if c['kind'] == 'blank']
        if missing:
            if selection['missing_policy'] == 'reject':
                raise ValueError('TABULAR_MISSING_VALUE')
            dropped.append({'row': number, 'missing_cells': missing})
            continue
        rows.append(values)
        source_rows.append(number)
    if not rows:
        raise ValueError('TABULAR_EMPTY_RESULT')
    content = {'problem_id': package['content']['problem_id'], 'asset_id': asset['id'],
               'selection': selection, 'source_sha256': asset['sha256'],
               'sheet_id': sheet['sheet_id'], 'sheet_name': sheet['name'],
               'headers': [c['name'] for c in columns], 'rows': rows, 'source_rows': source_rows,
               'source_columns': {c['name']: c['column'] for c in columns},
               'header_sources': {c['name']: f"{sheet['sheet_id']}!{c['column']}{selection['header_row']}" for c in columns},
               'input_row_count': selection['last_data_row'] - selection['first_data_row'] + 1,
               'dropped_rows': dropped, 'semantic_review': 'PENDING',
               'transformation': 'explicit-xlsx-numeric-selection/v1', 'imputation': 'NONE'}
    verify_package(package, run_dir, run_id)
    meta = package['meta']
    return ArtifactStore(run_dir, run_id).register_json(
        artifact_type='tabular_input', version=1, content=content, producer='xlsx-selection/v1',
        input_refs=[meta['artifact_id']], input_hashes={meta['artifact_id']: meta['content_sha256']})
