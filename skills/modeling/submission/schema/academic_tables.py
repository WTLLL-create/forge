"""Source-bound, fixed provisional table profile for the existing quadratic adapter.

This is not an arbitrary template editor. A changed profile requires a reviewed
adapter/version; an existing run may never silently acquire that new profile.
"""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
from importlib.metadata import version

from core.schema.artifact_meta import content_sha256

PROFILE = 'academic_provisional_v1/quadratic-docx-v1'


def build_table_spec(paper, snapshot):
    if paper['schema'] != 'forge-paper-spec/v2' or paper['status'] != 'DRAFT_SKELETON':
        raise ValueError('TABLE_UNSUPPORTED_PAPER')
    sections = {s['kind']: s for s in paper['sections']}
    symbols = {}
    for block in sections['formulas']['blocks']:
        for symbol in block['symbols']:
            name = symbol['name']['value']
            if name in symbols and symbols[name] != symbol:
                raise ValueError('TABLE_SYMBOL_CONFLICT')
            symbols[name] = symbol
    # Project by field name, never by positional index: an upstream reordering of
    # the evidence PaperSpec result fields must not silently swap table columns.
    # A renamed/dropped/duplicated field fails closed instead of producing a table.
    RESULT_FIELDS = ('scenario', 'source_row', 'parameters',
                     'minimizer', 'minimum', 'stationarity_residual', 'curvature')
    result_block = sections['results']['blocks'][0]
    result_headers = result_block.get('headers')
    if (not isinstance(result_headers, list) or len(result_headers) != len(set(result_headers))
            or set(result_headers) != set(RESULT_FIELDS)):
        raise ValueError('TABLE_RESULTS_FIELDS_INVALID')
    field_index = {name: i for i, name in enumerate(result_headers)}

    def field(row, name):
        return row[field_index[name]]

    raw = result_block['rows']
    available = round((21 - float(snapshot['contract']['page']['margin']['left'][:-2])
                       - float(snapshot['contract']['page']['margin']['right'][:-2])) * 1440 / 2.54)
    width = available // 4
    def column(label, kind='text', digits=None):
        return {'label': label, 'kind': kind, 'digits': digits,
                'alignment': 'right' if kind in ('number', 'integer') else 'left',
                'width_twips': width, 'missing': '—'}
    tables = [
        {'id': 'TABLE_1', 'caption': '表1 符号说明',
         'columns': [column(h) for h in ('符号', '含义', '单位', '定义域')],
         'rows': [[s[k] for k in ('name', 'meaning', 'unit', 'domain')] for s in symbols.values()],
         'note': '注：符号、单位及定义域来自本轮公式定义。'},
        {'id': 'TABLE_2', 'caption': '表2 情景求解结果',
         'columns': [column('情景', 'identifier'), column('参数取值', 'parameters'),
                     column('最优解', 'number', 3), column('目标函数最小值', 'number', 3)],
         'rows': [[field(r, 'scenario'), field(r, 'parameters'),
                   field(r, 'minimizer'), field(r, 'minimum')] for r in raw],
         'note': '注：各行对应独立情景；数值保留3位小数，精确值见本轮求解结果；单位见符号定义。'},
        {'id': 'TABLE_3', 'caption': '表3 求解核对',
         'columns': [column('情景', 'identifier'), column('原始行号', 'integer', 0),
                     column('驻点残差', 'number', 3), column('曲率', 'number', 3)],
         'rows': [[field(r, 'scenario'), field(r, 'source_row'),
                   field(r, 'stationarity_residual'), field(r, 'curvature')] for r in raw],
         'note': '注：行号沿用原始数据；残差与曲率来自实际求解，不代表验证计划已全部执行。'}]
    for table in tables:
        if not table['rows'] or any(len(row) != len(table['columns']) for row in table['rows']):
            raise ValueError('TABLE_SHAPE_INVALID')
        for row in table['rows']:
            for cell, col in zip(row, table['columns']):
                if set(cell) != {'value', 'evidence_ref'} or not cell['evidence_ref']:
                    raise ValueError('TABLE_UNBOUND_VALUE')
                display_value(cell['value'], col)
    return {'schema': 'forge-table-spec/v1', 'policy_version': '1.0', 'profile_id': PROFILE,
            'status': 'locked', 'run_id': paper['run_id'], 'paper_spec_sha256': content_sha256(paper),
            'template_sha256': snapshot['sha256'], 'template_contract_sha256': snapshot['contract_sha256'],
            'template_path': 'submission/templates/CUMCM_template.docx',
            'source': {'policy': 'standards/academic_table_standard.md', 'checked_on': '2026-09-08',
                       'url': 'https://ctan.org/pkg/booktabs',
                       'scope': 'provisional workspace profile; no verified official CUMCM compliance'},
            'generator': {'name': 'bound_docx', 'version': 'table-v1', 'python_docx': version('python-docx')},
            'output_format': 'docx', 'available_width_twips': available,
            'style': {'font_pt': 10.5, 'font_ascii': 'Times New Roman', 'font_east_asia': '宋体',
                      'top_eighth_pt': 12, 'middle_eighth_pt': 6, 'bottom_eighth_pt': 12,
                      'color': '000000', 'bold': False, 'header_repeat': True,
                      'split_rows': False, 'caption_position': 'above', 'note_position': 'below'},
            'changes': [], 'tables': tables}


def display_value(value, column):
    if value is None:
        return column['missing']
    kind = column['kind']
    if kind == 'identifier':
        if type(value) not in (str, int): raise ValueError('TABLE_IDENTIFIER_INVALID')
        return str(value)
    if kind == 'parameters':
        return '，'.join(k + '=' + str(v) for k, v in value.items())
    if kind in ('integer', 'number'):
        number = Fraction(str(value))
        if kind == 'integer':
            if number.denominator != 1: raise ValueError('TABLE_NONINTEGER_COUNT')
            return str(number.numerator)
        with localcontext() as ctx:
            ctx.prec = max(50, len(str(abs(number.numerator))) + len(str(number.denominator)) + 10)
            rounded = (Decimal(number.numerator) / Decimal(number.denominator)).quantize(
                Decimal(1).scaleb(-column['digits']), rounding=ROUND_HALF_EVEN)
        if number and not rounded:
            raise ValueError('TABLE_PRECISION_WOULD_ERASE_VALUE')
        return format(rounded, f'.{column["digits"]}f')
    if not isinstance(value, str): raise ValueError('TABLE_TEXT_TYPE_INVALID')
    return value


def validate_table_spec(table_spec, paper, snapshot):
    if content_sha256(table_spec) != content_sha256(build_table_spec(paper, snapshot)):
        raise ValueError('TABLE_SPEC_SOURCE_OR_PROFILE_DRIFT')
