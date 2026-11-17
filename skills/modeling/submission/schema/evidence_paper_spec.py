"""Evidence-only PaperSpec v2 skeleton profile; pure functions, no file/tool access."""
import copy
import html
import json

from core.schema.artifact_meta import content_sha256


def template_contract():
    return {'schema': 'forge-paper-template/v1', 'id': 'quadratic-paper-skeleton/v2',
            'title': '数学建模模型与求解报告（候选稿）',
            'notice': '本候选稿呈现题目要求、预计算模型方案、受限求解范围内的公式和计算结果。科学适用性、单位含义与完整论文质量待人工审查。',
            'sections': ['问题与任务', '预计算模型方案', '公式与符号', '求解结果', '验证范围与模型局限'],
            'format': 'markdown', 'full_cumcm_template': False}


def _expected_spec(graph, template):
    if (graph.get('schema') != 'forge-evidence-graph/v1'
            or graph.get('scope') != 'quadratic-paper-skeleton/v2'
            or content_sha256(template) != content_sha256(template_contract())):
        raise ValueError('PAPER_INPUT_PROFILE_INVALID')
    facts = {f['id']: f for f in graph['facts']}
    if len(facts) != len(graph['facts']) or not graph['rows'] or not graph['formulas']:
        raise ValueError('PAPER_EVIDENCE_INCOMPLETE')
    def bound(ref):
        fact = facts[ref]
        return {'evidence_ref': ref, 'value': copy.deepcopy(fact['value'])}
    problems = []
    for problem in graph['problems']:
        problems.append({'type': 'problem_question',
                         'question_id': bound(problem['question_id_ref']),
                         'task': bound(problem['task_ref']),
                         'objective': bound(problem['objective_ref']),
                         'sources': bound(problem['sources_ref']),
                         'outputs': [{'text': bound(item['text_ref']),
                                      'sources': bound(item['sources_ref'])}
                                     for item in problem['outputs']]})
    contexts = {item['label']: item for item in graph['context']}
    model_blocks = [{'type': 'bound_context', 'label': 'selection_phase',
                     'binding': bound(contexts['selection_phase']['ref'])}]
    review_blocks = []
    for model in graph['models']:
        selected = model['selected']
        model_blocks.append({'type': 'selected_model',
            'question_id': bound(model['question_id_ref']),
            'baseline_id': bound(model['baseline_id_ref']),
            'selected_id': bound(model['selected_id_ref']),
            **{key: bound(selected[key + '_ref']) for key in
               ('id', 'name', 'rationale', 'sources', 'assumption_refs', 'data_asset_ids', 'limitations')}})
        review_blocks.append({'type': 'model_limitation',
                              'model_id': bound(selected['id_ref']),
                              'limitations': bound(selected['limitations_ref'])})
        for rejected in model['rejected']:
            model_blocks.append({'type': 'rejected_model',
                **{key: bound(rejected[key + '_ref']) for key in
                   ('id', 'name', 'rejection_reasons', 'sources')}})
    for assumption in graph['assumptions']:
        model_blocks.append({'type': 'assumption', 'binding': bound(assumption['ref'])})
    for validation in graph['validations']:
        model_blocks.append({'type': 'validation_plan', 'binding': bound(validation['ref'])})

    formulas = []
    for formula in graph['formulas']:
        formulas.append({'type': 'formula', 'definition': bound(formula['ref']),
                         'latex': formula['latex'], 'mapping_status': formula['mapping_status'],
                         'parameters': bound(formula['parameter_binding_ref']),
                         'execution': bound(formula['execution_ref']),
                         'symbols': [{key: bound(ref) for key, ref in graph['symbols'][i].items()}
                                     for i in formula['symbol_refs']]})
    fields = ['scenario', 'source_row', 'parameters', 'minimizer', 'minimum', 'stationarity_residual', 'curvature']
    for ambiguity in graph['ambiguities']:
        review_blocks.append({'type': 'ambiguity',
                              **{key: bound(ambiguity[key + '_ref'])
                                 for key in ('id', 'description', 'sources')}})
    for context in graph['context']:
        if context['label'] not in {'selection_phase', 'engine_sha256', 'provenance'}:
            review_blocks.append({'type': 'bound_context', 'label': context['label'],
                                  'binding': bound(context['ref'])})
    sections = [
        {'kind': 'problem', 'title': template['sections'][0], 'blocks': problems},
        {'kind': 'model_design', 'title': template['sections'][1], 'blocks': model_blocks},
        {'kind': 'formulas', 'title': template['sections'][2], 'blocks': formulas},
        {'kind': 'results', 'title': template['sections'][3], 'blocks': [{'type': 'bound_table', 'headers': fields,
         'rows': [[bound(row[field]) for field in fields] for row in graph['rows']]}]},
        {'kind': 'review', 'title': template['sections'][4], 'blocks': review_blocks},
    ]
    required_refs = []
    def collect(value):
        if isinstance(value, dict):
            if set(value) == {'evidence_ref', 'value'}:
                if value['evidence_ref'] not in required_refs:
                    required_refs.append(value['evidence_ref'])
            else:
                for child in value.values(): collect(child)
        elif isinstance(value, list):
            for child in value: collect(child)
    collect(sections)
    return {'schema': 'forge-paper-spec/v2', 'profile': graph['scope'], 'run_id': graph['run_id'],
            'problem_id': graph['problem_id'], 'evidence_sha256': content_sha256(graph),
            'template_sha256': content_sha256(template), 'title': template['title'],
            'notice': template['notice'], 'status': 'DRAFT_SKELETON',
            'sections': sections, 'required_evidence_refs': required_refs,
            'sources': copy.deepcopy(graph['facts']), 'artifact_lineage': copy.deepcopy(graph['artifacts'])}


def compose(graph, template):
    return _expected_spec(graph, template)


def validate_spec(spec, graph, template):
    # Exact profile validation rejects extra prose, omitted rows, altered formulas,
    # changed rounding, forged PASS text, and bindings with copied but stale values.
    if content_sha256(spec) != content_sha256(_expected_spec(graph, template)):
        raise ValueError('PAPER_SPEC_EVIDENCE_MISMATCH')


def _text(value):
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    value = html.escape(value, quote=True)
    # Escape source prose as literal Markdown, including cell separators and math.
    for char in ('\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!', '$', '|'):
        value = value.replace(char, '\\' + char)
    return value.replace('\r', ' ').replace('\n', ' ')


def render(spec):
    lines = ['# ' + _text(spec['title']), '', _text(spec['notice']), '',
             'Run: ' + _text(spec['run_id']), '',
             '人工审查：PENDING；文档范围：证据绑定候选骨架。', '']
    for section in spec['sections']:
        lines.extend(['## ' + _text(section['title']), ''])
        for block in section['blocks']:
            if block['type'] == 'problem_question':
                lines.extend(['### ' + _text(block['question_id']['value']), '',
                              '任务：' + _text(block['task']['value']), '',
                              '目标：' + _text(block['objective']['value']), '',
                              '要求输出：', ''])
                for output in block['outputs']:
                    lines.append('- ' + _text(output['text']['value']))
                lines.append('')
            elif block['type'] == 'selected_model':
                lines.extend(['### ' + _text(block['question_id']['value']) + ' 选定模型', '',
                              '模型：' + _text(block['name']['value']) + '（' + _text(block['id']['value']) + '）', '',
                              '选择理由：' + _text(block['rationale']['value']), '',
                              '基线模型：' + _text(block['baseline_id']['value']) + '；选定模型：' + _text(block['selected_id']['value']), '',
                              '使用数据：' + _text(block['data_asset_ids']['value']), '',
                              '依赖假设：' + _text(block['assumption_refs']['value']), ''])
            elif block['type'] == 'rejected_model':
                lines.extend(['备选模型：' + _text(block['name']['value']) + '（' + _text(block['id']['value']) + '）', '',
                              '未选原因：' + _text(block['rejection_reasons']['value']), ''])
            elif block['type'] == 'assumption':
                value = block['binding']['value']
                lines.extend(['### 模型假设 ' + _text(value['id']), '', _text(value['statement']), '',
                              '依据：' + _text(value['justification']), ''])
            elif block['type'] == 'validation_plan':
                value = block['binding']['value']
                lines.extend(['### 验证计划', '', '方法：' + _text(value['method']), '',
                              '判据：' + _text(value['criteria']), '',
                              '数据划分：' + _text(value['data_partition']), '',
                              '执行状态：' + _text(value['phase']), ''])
            elif block['type'] == 'formula':
                formula = block['definition']['value']
                lines.extend(['### ' + _text(formula['id']), '', '$$', block['latex'], '$$', '',
                              '推导规则：' + _text(formula['rule']) + '；依赖公式：' + _text(formula['depends_on']), '',
                              '求解映射：' + _text(block['mapping_status']) + '；执行目标：' + _text(block['execution']['value']), '',
                              '参数绑定：' + _text(block['parameters']['value']), ''])
                for symbol in block['symbols']:
                    lines.append('- ' + '; '.join(key + ': ' + _text(cell['value']) for key, cell in symbol.items()))
                lines.append('')
            elif block['type'] == 'bound_table':
                lines.extend(['| ' + ' | '.join(block['headers']) + ' |',
                              '| ' + ' | '.join('---' for _ in block['headers']) + ' |'])
                for row in block['rows']:
                    cells = []
                    for header, cell in zip(block['headers'], row):
                        value = cell['value']
                        if header == 'parameters':
                            # Single-parameter rows remain readable; its symbol is in the formula binding.
                            value = next(iter(value.values())) if len(value) == 1 else value
                        cells.append(_text(value))
                    lines.append('| ' + ' | '.join(cells) + ' |')
                lines.append('')
            elif block['type'] == 'bound_context':
                lines.extend([_text(block['label']) + '：' + _text(block['binding']['value']), ''])
            elif block['type'] == 'model_limitation':
                lines.extend(['模型 ' + _text(block['model_id']['value']) + ' 的局限：', ''])
                for limitation in block['limitations']['value']:
                    lines.append('- ' + _text(limitation))
                lines.append('')
            elif block['type'] == 'ambiguity':
                lines.extend(['### 待确认事项 ' + _text(block['id']['value']), '',
                              _text(block['description']['value']), ''])
            else:
                raise ValueError('PAPER_BLOCK_UNSUPPORTED')
    lines.extend(['## 证据索引', ''])
    for fact in spec['sources']:
        source = fact['source']
        lines.append('- ' + _text(fact['id']) + ': ' + _text(source['artifact_id']) + ' ' +
                     _text(source['path']) + ' SHA256=' + source['sha256'])
    lines.extend(['', '## 产物依赖', '', '```json',
                  json.dumps(spec['artifact_lineage'], ensure_ascii=False, indent=2), '```', ''])
    return '\n'.join(lines)
