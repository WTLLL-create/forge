"""Independent actual-DOCX inspection. No renderer/producer formatter imports.

Explicit formatting is required by this supported profile: unsupported style
inheritance/merges/decoration fail closed rather than guessing Word's cascade.
"""
from fractions import Fraction
import hashlib
from io import BytesIO
import json
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'


def _attr(node, name):
    return None if node is None else node.get(W + name)


def _text(node):
    return ''.join(t.text or '' for t in node.findall('.//w:t', NS))


def _properties(node, allowed):
    if node is None: return False
    tags = [child.tag for child in node]
    return len(tags) == len(set(tags)) and all(tag in {W + name for name in allowed} for tag in tags)


def _plain_paragraph(node, caption=False):
    if node.tag != W + 'p': return False
    props = node.find('w:pPr', NS)
    if caption:
        if not _properties(props, {'keepNext'}) or len(props) != 1: return False
        if _attr(props.find('w:keepNext', NS), 'val') in ('0', 'false', 'off'): return False
    elif props is not None and len(props): return False
    return all(child.tag in {W + 'pPr', W + 'r'} for child in node) and all(
        all(child.tag == W + 't' for child in run) for run in node.findall('w:r', NS))


def _expected(value, col):
    # Independently round exact fractions by integer quotient/remainder,
    # not the producer's Decimal formatting implementation.
    if value is None: return col['missing']
    if col['kind'] == 'identifier': return str(value)
    if col['kind'] == 'parameters': return '，'.join(f'{k}={v}' for k, v in value.items())
    if col['kind'] == 'text': return value
    f = Fraction(str(value))
    digits = col['digits']
    if col['kind'] == 'integer' and f.denominator != 1:
        raise ValueError('noninteger count')
    scale = 10 ** digits
    q, remainder = divmod(abs(f.numerator) * scale, f.denominator)
    if 2 * remainder > f.denominator or (2 * remainder == f.denominator and q % 2): q += 1
    if f and q == 0: raise ValueError('precision erases nonzero value')
    sign = '-' if f < 0 and q else ''
    if not digits: return sign + str(q)
    return f'{sign}{q // scale}.{q % scale:0{digits}d}'


def inspect_tables(data, spec):
    checks = []
    def check(code, ok, actual=None):
        checks.append({'code': code, 'passed': bool(ok), 'actual': actual})
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 256 or len({e.filename for e in entries}) != len(entries) or sum(e.file_size for e in entries) > 20_000_000:
                raise ValueError('package limits')
            root = ET.fromstring(archive.read('word/document.xml'))
        body = root.find('w:body', NS)
        actual = body.findall('w:tbl', NS)
        check('TABLE_COUNT', len(actual) == len(spec['tables']), len(actual))
        check('NO_NESTED_TABLES', len(root.findall('.//w:tbl', NS)) == len(actual))
        style = spec['style']
        children = list(body)
        for table, expected in zip(actual, spec['tables']):
            ident = expected['id']
            position = children.index(table)
            check(ident + ':CAPTION', position > 0 and _text(children[position - 1]) == expected['caption'])
            check(ident + ':NOTE', position + 1 < len(children) and _text(children[position + 1]) == expected['note'])
            check(ident + ':CAPTION_FORMAT', position > 0 and _plain_paragraph(children[position - 1], caption=True))
            check(ident + ':NOTE_FORMAT', position + 1 < len(children) and _plain_paragraph(children[position + 1]))
            props = table.find('w:tblPr', NS)
            check(ident + ':LAYOUT', _attr(props.find('w:tblLayout', NS), 'type') == 'fixed')
            check(ident + ':NO_STYLE', props.find('w:tblStyle', NS) is None)
            check(ident + ':TABLE_PROPERTIES', _properties(props, {'tblW', 'tblLayout', 'tblBorders', 'tblLook'}))
            table_width = props.find('w:tblW', NS)
            check(ident + ':TABLE_WIDTH', _attr(table_width, 'type') == 'auto' and _attr(table_width, 'w') == '0')
            check(ident + ':BORDER_PROPERTIES', _properties(props.find('w:tblBorders', NS), {'top', 'bottom', 'left', 'right', 'insideH', 'insideV'}))
            grid = [int(n.get(W + 'w')) for n in table.findall('w:tblGrid/w:gridCol', NS)]
            widths = [c['width_twips'] for c in expected['columns']]
            check(ident + ':WIDTH', grid == widths and sum(grid) <= spec['available_width_twips'], grid)
            for edge, size in [('top', style['top_eighth_pt']), ('bottom', style['bottom_eighth_pt']),
                               ('left', 0), ('right', 0), ('insideH', 0), ('insideV', 0)]:
                node = props.find('w:tblBorders/w:' + edge, NS)
                check(ident + ':BORDER:' + edge, node is not None and node.attrib == {
                    W + 'val': 'single' if size else 'nil', W + 'sz': str(size), W + 'color': '000000'})
            rows = table.findall('w:tr', NS)
            check(ident + ':ROWS', len(rows) == len(expected['rows']) + 1, len(rows))
            check(ident + ':NO_DECORATION', not any(table.findall('.//w:' + tag, NS) for tag in
                  ('shd', 'drawing', 'pict', 'gridSpan', 'vMerge', 'hMerge', 'tblPrEx', 'trHeight', 'tblStylePr', 'tblInd')))
            for ri, row in enumerate(rows):
                prefix = f'{ident}:R{ri}'
                header = row.find('w:trPr/w:tblHeader', NS)
                check(prefix + ':REPEAT', (header is not None and _attr(header, 'val') not in ('0', 'false', 'off')) == (ri == 0))
                split = row.find('w:trPr/w:cantSplit', NS)
                check(prefix + ':NO_SPLIT', split is not None and _attr(split, 'val') not in ('0', 'false', 'off'))
                check(prefix + ':ROW_PROPERTIES', _properties(row.find('w:trPr', NS), {'cantSplit', 'tblHeader'}))
                cells = row.findall('w:tc', NS)
                check(prefix + ':COLUMNS', len(cells) == len(expected['columns']))
                for ci, (cell, col) in enumerate(zip(cells, expected['columns'])):
                    code = f'{prefix}:C{ci}'
                    if ri > len(expected['rows']): continue
                    value = col['label'] if ri == 0 else _expected(expected['rows'][ri - 1][ci]['value'], col)
                    check(code + ':VALUE', _text(cell) == value, _text(cell))
                    cell_width = cell.find('w:tcPr/w:tcW', NS)
                    check(code + ':CELL_PROPERTIES', _properties(cell.find('w:tcPr', NS), {'tcW', 'tcBorders'}))
                    check(code + ':CELL_CONTENT', all(c.tag in {W + 'tcPr', W + 'p'} for c in cell))
                    check(code + ':WIDTH', _attr(cell_width, 'type') == 'dxa' and _attr(cell_width, 'w') == str(col['width_twips']))
                    borders = cell.find('w:tcPr/w:tcBorders', NS)
                    if ri == 0:
                        bottom = None if borders is None else borders.find('w:bottom', NS)
                        check(code + ':HEADER_LINE', borders is not None and len(borders) == 1
                              and bottom is not None and bottom.attrib == {
                                  W + 'val': 'single', W + 'sz': str(style['middle_eighth_pt']), W + 'color': '000000'})
                    else: check(code + ':NO_CELL_BORDER', borders is None)
                    paragraphs = cell.findall('w:p', NS)
                    check(code + ':PARAGRAPHS', len(paragraphs) == 1)
                    for paragraph in paragraphs:
                        pp = paragraph.find('w:pPr', NS)
                        check(code + ':PARAGRAPH_PROPERTIES', _properties(pp, {'ind', 'spacing', 'jc', 'keepNext'}))
                        indent = paragraph.find('w:pPr/w:ind', NS)
                        spacing = paragraph.find('w:pPr/w:spacing', NS)
                        check(code + ':INDENT', indent is not None and indent.attrib == {W + 'firstLine': '0'})
                        check(code + ':SPACING', spacing is not None and spacing.attrib == {W + 'before': '40', W + 'after': '40'})
                        keep = paragraph.find('w:pPr/w:keepNext', NS)
                        should_keep = len(expected['rows']) <= 8 and ri < len(expected['rows'])
                        check(code + ':KEEP_NEXT', (keep is not None and not keep.attrib) if should_keep else keep is None)
                        check(code + ':PARAGRAPH_CONTENT', all(c.tag in {W + 'pPr', W + 'r'} for c in paragraph))
                        check(code + ':ALIGN', _attr(paragraph.find('w:pPr/w:jc', NS), 'val') == ('left' if ri == 0 else col['alignment']))
                        check(code + ':NO_P_STYLE', paragraph.find('w:pPr/w:pStyle', NS) is None)
                        runs = paragraph.findall('w:r', NS)
                        check(code + ':RUNS', bool(runs))
                        for run in runs:
                            rp = run.find('w:rPr', NS)
                            if rp is None:
                                check(code + ':EXPLICIT_FONT', False); continue
                            check(code + ':RUN_PROPERTIES', _properties(rp, {'rFonts', 'b', 'color', 'sz'}))
                            check(code + ':RUN_CONTENT', all(c.tag in {W + 'rPr', W + 't'} for c in run))
                            size_node = rp.find('w:sz', NS)
                            check(code + ':FONT_SIZE', size_node is not None and size_node.attrib == {W + 'val': str(round(style['font_pt'] * 2))})
                            fonts = rp.find('w:rFonts', NS)
                            check(code + ':FONT', fonts is not None and fonts.attrib == {
                                W + 'ascii': style['font_ascii'], W + 'hAnsi': style['font_ascii'], W + 'eastAsia': style['font_east_asia']})
                            color = rp.find('w:color', NS)
                            check(code + ':COLOR', _attr(color, 'val') == style['color'] and len(color.attrib) == 1)
                            check(code + ':BOLD', _attr(rp.find('w:b', NS), 'val') in ('0', 'false', 'off'))
                            check(code + ':NO_RUN_DECORATION', not any(rp.find('w:' + tag, NS) is not None for tag in
                                  ('rStyle', 'i', 'u', 'highlight', 'strike', 'vanish', 'vertAlign', 'szCs', 'bCs')))
    except Exception as exc:
        check('TABLE_INSPECTION_ERROR', False, type(exc).__name__ + ': ' + str(exc))
    digest = hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return {'schema': 'forge-table-checks/v1', 'status': 'PASS' if checks and all(c['passed'] for c in checks) else 'FAIL',
            'docx_sha256': hashlib.sha256(data).hexdigest(), 'table_spec_sha256': digest,
            'visual_review': 'PENDING', 'checks': checks}
