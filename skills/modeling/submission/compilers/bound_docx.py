"""Template-preserving PaperSpec fragment renderer and deterministic package checks."""
import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor, Twips

from core.schema.artifact_meta import content_sha256
from submission.compilers.native_omml import polynomial_omml
from submission.schema.academic_tables import build_table_spec, validate_table_spec, display_value
from submission.validation.docx_tables import inspect_tables

PROFILE = 'paired-cumcm-fragment/v1'


def snapshot_template():
    root = Path(__file__).resolve().parents[1] / 'templates'
    data = (root / 'CUMCM_template.docx').read_bytes()
    contract = json.loads((root / 'cumcm_template.json').read_text(encoding='utf-8'))
    result = {'profile': PROFILE, 'filename': 'CUMCM_template.docx',
              'sha256': hashlib.sha256(data).hexdigest(),
              'base64': base64.b64encode(data).decode('ascii'),
              'contract': contract, 'contract_sha256': content_sha256(contract)}
    decode_snapshot(result)
    return result


def package_parts(data):
    with ZipFile(BytesIO(data)) as archive:
        members = archive.infolist()
        if (len(members) > 256 or len({m.filename for m in members}) != len(members)
                or sum(m.file_size for m in members) > 20_000_000):
            raise ValueError('DOCX_PACKAGE_LIMIT')
        return {m.filename: archive.read(m) for m in members}


def decode_snapshot(snapshot):
    if snapshot['profile'] != PROFILE or len(snapshot['base64']) > 3_000_000:
        raise ValueError('DOCX_TEMPLATE_PROFILE_INVALID')
    data = base64.b64decode(snapshot['base64'], validate=True)
    if (hashlib.sha256(data).hexdigest() != snapshot['sha256']
            or content_sha256(snapshot['contract']) != snapshot['contract_sha256']):
        raise ValueError('DOCX_TEMPLATE_HASH_MISMATCH')
    package_parts(data)
    doc = Document(BytesIO(data))
    contract = snapshot['contract']
    if len(doc.sections) != 1 or contract['equation']['render_engine'] != 'omml':
        raise ValueError('DOCX_TEMPLATE_UNSUPPORTED')
    section = doc.sections[0]
    if (abs(section.page_width.cm - 21) > .01 or abs(section.page_height.cm - 29.7) > .01
            or contract['page']['size'] != 'A4'):
        raise ValueError('DOCX_TEMPLATE_PAGE_MISMATCH')
    for side in ('top', 'bottom', 'left', 'right'):
        target = contract['page']['margin'][side]
        if not target.endswith('cm') or abs(getattr(section, side + '_margin').cm - float(target[:-2])) > .01:
            raise ValueError('DOCX_TEMPLATE_MARGIN_MISMATCH')
    # This first profile supports the retained style contract, not arbitrary templates.
    if (doc.styles['Normal'].font.size != Pt(12) or doc.styles['Normal'].paragraph_format.line_spacing != 1.5
            or contract['table']['style'] != 'three_line'
            or contract['table']['top_border'] != '1.5pt'
            or contract['table']['header_border'] != '0.75pt'
            or contract['table']['bottom_border'] != '1.5pt'):
        raise ValueError('DOCX_TEMPLATE_STYLE_UNSUPPORTED')
    return data


def _plain(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)


def _table(doc, definition, style):
    headers = [c['label'] for c in definition['columns']]
    rows = [[display_value(cell['value'], col) for cell, col in zip(row, definition['columns'])]
            for row in definition['rows']]
    caption = doc.add_paragraph(definition['caption'])
    caption.paragraph_format.keep_with_next = True
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = False
    for column, spec_column in zip(table.columns, definition['columns']):
        column.width = Twips(spec_column['width_twips'])
    for values, row in [(headers, table.rows[0])] + [(values, table.add_row()) for values in rows]:
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for cell, value, spec_column in zip(row.cells, values, definition['columns']):
            cell.width = Twips(spec_column['width_twips'])
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.first_line_indent = Cm(0)
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.paragraph_format.space_before = Pt(2)
            paragraph.alignment = (WD_ALIGN_PARAGRAPH.RIGHT if values is not headers
                                   and spec_column['alignment'] == 'right' else WD_ALIGN_PARAGRAPH.LEFT)
            run = paragraph.add_run(_plain(value))
            run.font.size = Pt(style['font_pt'])
            run.font.name = style['font_ascii']
            run._r.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), style['font_east_asia'])
            run.font.color.rgb = RGBColor.from_string(style['color'])
            run.bold = False
    borders = OxmlElement('w:tblBorders')
    for edge, size in (('top', 12), ('bottom', 12), ('left', 0), ('right', 0), ('insideH', 0), ('insideV', 0)):
        node = OxmlElement('w:' + edge)
        node.set(qn('w:val'), 'single' if size else 'nil')
        node.set(qn('w:sz'), str(size))
        node.set(qn('w:color'), '000000')
        borders.append(node)
    table._tbl.tblPr.append(borders)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    for cell in table.rows[0].cells:
        border = OxmlElement('w:tcBorders')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '6')
        bottom.set(qn('w:color'), '000000')
        border.append(bottom)
        cell._tc.get_or_add_tcPr().append(border)
    # Keep small tables together without forcing long result tables onto one page.
    if len(rows) <= 8:
        for row in table.rows[:-1]:
            for cell in row.cells:
                cell.paragraphs[0].paragraph_format.keep_with_next = True
    doc.add_paragraph(definition['note'])


def _heading(doc, text, style):
    paragraph = doc.add_paragraph(text, style=style)
    # Preserve the named styles, but suppress inherited Office theme decoration
    # in the newly populated formal-paper heading slots.
    border = OxmlElement('w:pBdr')
    for side in ('top', 'bottom', 'left', 'right', 'between', 'bar'):
        node = OxmlElement('w:' + side)
        node.set(qn('w:val'), 'nil')
        border.append(node)
    paragraph._p.get_or_add_pPr().append(border)
    for run in paragraph.runs:
        run.font.color.rgb = RGBColor(0, 0, 0)
    return paragraph


def render_docx(spec, snapshot, table_spec=None):
    """No project reads: input is already-validated PaperSpec plus template snapshot."""
    if spec.get('schema') != 'forge-paper-spec/v2' or spec.get('status') != 'DRAFT_SKELETON':
        raise ValueError('DOCX_SPEC_PROFILE_INVALID')
    template = decode_snapshot(snapshot)
    table_spec = build_table_spec(spec, snapshot) if table_spec is None else table_spec
    validate_table_spec(table_spec, spec, snapshot)
    doc = Document(BytesIO(template))
    for child in list(doc._element.body):
        if child.tag != qn('w:sectPr'):
            doc._element.body.remove(child)
    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            for run in paragraph.runs:
                if '[[PAPER_TITLE]]' in run.text:
                    run.text = run.text.replace('[[PAPER_TITLE]]', spec['title'])
    _heading(doc, spec['title'], 'Title')
    doc.add_paragraph(spec['notice'] + ' 人工审查状态：PENDING。')
    sections = {section['kind']: section for section in spec['sections']}
    if set(sections) != {'problem', 'model_design', 'formulas', 'results', 'review'}:
        raise ValueError('DOCX_SPEC_SECTIONS_INVALID')
    _heading(doc, sections['problem']['title'], 'Heading 1')
    for block in sections['problem']['blocks']:
        _heading(doc, block['question_id']['value'], 'Heading 2')
        doc.add_paragraph('任务：' + block['task']['value'])
        doc.add_paragraph('目标：' + block['objective']['value'])
        doc.add_paragraph('要求输出：' + '；'.join(item['text']['value'] for item in block['outputs']))

    _heading(doc, sections['model_design']['title'], 'Heading 1')
    for block in sections['model_design']['blocks']:
        if block['type'] == 'bound_context':
            doc.add_paragraph('模型选择阶段：' + _plain(block['binding']['value']) + '。')
        elif block['type'] == 'selected_model':
            _heading(doc, block['question_id']['value'] + ' 选定模型', 'Heading 2')
            doc.add_paragraph('选用' + block['name']['value'] + '（' + block['id']['value'] + '）。')
            doc.add_paragraph('选择理由：' + block['rationale']['value'])
            doc.add_paragraph('基线模型为' + block['baseline_id']['value'] + '，使用数据为' +
                              _plain(block['data_asset_ids']['value']) + '。')
        elif block['type'] == 'rejected_model':
            doc.add_paragraph('未选用' + block['name']['value'] + '（' + block['id']['value'] + '）：' +
                              '；'.join(block['rejection_reasons']['value']))
        elif block['type'] == 'assumption':
            value = block['binding']['value']
            _heading(doc, '模型假设 ' + value['id'], 'Heading 2')
            doc.add_paragraph(value['statement'] + '。依据：' + value['justification'])
        elif block['type'] == 'validation_plan':
            value = block['binding']['value']
            _heading(doc, '验证计划', 'Heading 2')
            doc.add_paragraph('计划方法：' + value['method'])
            doc.add_paragraph('计划判据：' + '；'.join(value['criteria']))
            doc.add_paragraph('数据划分：' + value['data_partition'] + '。当前状态：' + value['phase'] + '。')
        else:
            raise ValueError('DOCX_MODEL_BLOCK_UNSUPPORTED')

    formulas = sections['formulas']['blocks']
    _heading(doc, '符号说明', 'Heading 1')
    _table(doc, table_spec['tables'][0], table_spec['style'])
    _heading(doc, sections['formulas']['title'], 'Heading 1')
    for block in formulas:
        formula = block['definition']['value']
        rule = {'definition': '目标函数定义', 'differentiate': '对前式求导',
                'algebraic_equivalence': '等价变形'}[formula['rule']]
        doc.add_paragraph(rule + '，公式标识为 ' + formula['id'] + '。')
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
        paragraph.paragraph_format.line_spacing = Pt(24)
        width = doc.sections[0].page_width - doc.sections[0].left_margin - doc.sections[0].right_margin
        paragraph.paragraph_format.tab_stops.add_tab_stop(int(width / 2), WD_TAB_ALIGNMENT.CENTER)
        paragraph.paragraph_format.tab_stops.add_tab_stop(width, WD_TAB_ALIGNMENT.RIGHT)
        paragraph.add_run('\t')
        paragraph._p.append(polynomial_omml(block['latex']))
        paragraph.add_run('\t(' + formula['id'] + ')')
    _heading(doc, sections['results']['title'], 'Heading 1')
    _table(doc, table_spec['tables'][1], table_spec['style'])
    _heading(doc, '求解核对', 'Heading 2')
    _table(doc, table_spec['tables'][2], table_spec['style'])
    doc.add_page_break()
    _heading(doc, sections['review']['title'], 'Heading 1')
    for block in sections['review']['blocks']:
        if block['type'] == 'model_limitation':
            _heading(doc, '模型局限', 'Heading 2')
            for value in block['limitations']['value']:
                doc.add_paragraph(value, style='List Bullet')
        elif block['type'] == 'ambiguity':
            _heading(doc, '待确认事项 ' + block['id']['value'], 'Heading 2')
            doc.add_paragraph(block['description']['value'])
        elif block['type'] == 'bound_context':
            label = {'scope': '自动验证范围', 'solution_status': '求解状态',
                     'scientific_review': '科学审查',
                     'unit_semantics_review': '单位语义审查'}.get(block['label'], block['label'])
            doc.add_paragraph(label + '：' + _plain(block['binding']['value']))
        else:
            raise ValueError('DOCX_REVIEW_BLOCK_UNSUPPORTED')
    doc.add_paragraph('上述数值来自本轮独立情景求解；计划中的验证不得解释为已经执行。')
    doc.core_properties.title = spec['title']
    doc.core_properties.identifier = spec['run_id']
    doc.core_properties.keywords = 'PaperSpec=' + content_sha256(spec) + ';template=' + snapshot['sha256']
    stream = BytesIO()
    doc.save(stream)
    output = stream.getvalue()
    before, after = package_parts(template), package_parts(output)
    editable = {'word/document.xml', 'docProps/core.xml'} | {n for n in before if n.startswith('word/header')}
    if set(before) != set(after) or any(before[n] != after[n] for n in before if n not in editable):
        raise ValueError('DOCX_TEMPLATE_PRESERVATION_FAILED')
    return output


def validate_docx(data, spec, snapshot, table_spec=None):
    """Compare every uncompressed ZIP part: text, math, styles and auxiliary stories."""
    table_spec = build_table_spec(spec, snapshot) if table_spec is None else table_spec
    validate_table_spec(table_spec, spec, snapshot)
    expected = package_parts(render_docx(spec, snapshot, table_spec))
    actual = package_parts(data)
    if actual != expected:
        raise ValueError('DOCX_CONTENT_OR_TEMPLATE_DRIFT')
    independent = inspect_tables(data, table_spec)
    if independent['status'] != 'PASS':
        raise ValueError('DOCX_CONTENT_OR_TEMPLATE_DRIFT: INDEPENDENT_TABLE_CHECK_FAILED')
    doc = Document(BytesIO(data))
    count = len(doc._element.xpath('.//m:oMath'))
    formulas = next(section for section in spec['sections'] if section['kind'] == 'formulas')
    if count != len(formulas['blocks']):
        raise ValueError('DOCX_FORMULA_COVERAGE_FAILED')
    return {'formula_count': count, 'table_count': len(doc.tables),
            'parts_checked': len(actual), 'sha256': hashlib.sha256(data).hexdigest()}
