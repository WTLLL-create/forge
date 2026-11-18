"""Deterministic current-run evidence and a review-only paper skeleton.

This adapter is deliberately limited to the verified quadratic result producer.
It is not a publication controller or a general scientific validity gate.
"""
import copy
import hashlib
from pathlib import Path

from core.runtime.artifact_store import ArtifactStore
from core.runtime.data_profile import read_table
from core.runtime.problem_package import verify_package
from core.schema.artifact_meta import ArtifactError, content_sha256
from core.schema.gate_result import gate_check, gate_result, write_gate_result
from core.schema.model_design import validate_derivation, validate_model_plan
from core.schema.model_result import json_path_get, validate_model_result
from core.schema.polynomial_math import checked_expression, latex
from core.schema.quadratic_solver import solve_scenarios

VERSION = 'quadratic-evidence/v1'
SOURCE_KINDS = ('problem_package', 'problem_spec', 'data_profile', 'model_plan',
                'derivation_spec', 'solver_plan', 'solver_execution', 'model_result')


def _active(store, kind):
    pointer = store.registry._load()['artifacts'].get(kind)
    if not pointer:
        raise ValueError('EVIDENCE_SOURCE_MISSING')
    return store.registry._stored_envelope(pointer['path'])


def _sources(store):
    store.registry.verify_integrity()
    sources = {kind: _active(store, kind) for kind in SOURCE_KINDS}
    package = sources['problem_package']
    verify_package(package, store.run_dir, store.run_id)
    if 'data_selection' in package['content']['configuration']:
        sources['tabular_input'] = _active(store, 'tabular_input')
    # A superseded dependency cannot become current merely because its file exists.
    current = {e['meta']['artifact_id']: e['meta']['content_sha256'] for e in sources.values()}
    for envelope in sources.values():
        for ref in envelope['meta']['input_refs']:
            if current.get(ref) != envelope['meta']['input_hashes'][ref]:
                raise ValueError('EVIDENCE_DEPENDENCY_NOT_CURRENT')
    return sources


def _verify_computation(sources, store):
    package = sources['problem_package']
    plan = sources['model_plan']['content']
    derivation = sources['derivation_spec']['content']
    result = sources['model_result']['content']
    execution = sources['solver_execution']
    config = package['content']['configuration']['quadratic_solve']
    validate_model_result(result, store.run_id, expected_schema='forge-model-result/v2')
    if (result['problem_id'] != package['content']['problem_id']
            or result['model_version'] != 'strict-convex-quadratic/v1'
            or result['parameters'] != {'solve_config': config}
            or sources['solver_plan']['content'] != config
            or result['diagnostics']['execution_artifact_id'] != execution['meta']['artifact_id']
            or result['diagnostics']['execution_sha256'] != execution['meta']['content_sha256']):
        raise ValueError('EVIDENCE_RESULT_EXECUTION_MISMATCH')
    if (validate_model_plan(plan, sources['problem_spec']['content'], package)['status'] != 'PASS'
            or validate_derivation(derivation, plan, package)['status'] != 'PASS'):
        raise ValueError('EVIDENCE_DERIVATION_INVALID')
    asset = next(a for a in package['content']['assets'] if a['id'] == config['asset_id'])
    if 'tabular_input' in sources:
        table = sources['tabular_input']['content']
        if (table['asset_id'] != config['asset_id'] or table['source_sha256'] != asset['sha256']
                or table['selection'] != package['content']['configuration']['data_selection']):
            raise ValueError('EVIDENCE_TABLE_SOURCE_MISMATCH')
        headers, rows = table['headers'], table['rows']
        provenance = dict(asset_id=config['asset_id'], source_sha256=asset['sha256'],
                          source_rows=table['source_rows'], source_columns=table['source_columns'],
                          sheet_id=table['sheet_id'], sheet_name=table['sheet_name'],
                          dropped_rows=table['dropped_rows'],
                          tabular_input_sha256=sources['tabular_input']['meta']['content_sha256'])
    else:
        headers, rows = read_table(package, store.run_dir, store.run_id, config['asset_id'])
        provenance = dict(asset_id=config['asset_id'], source_sha256=asset['sha256'],
                          source_rows=list(range(1, len(rows) + 1)),
                          row_indexing='1-based CSV/TSV data records excluding header',
                          source_columns={h: i for i, h in enumerate(headers, 1)}, dropped_rows=[])
    report, replay = solve_scenarios(config, derivation, headers, rows, store.run_id)
    if (report['status'] != 'PASS' or any(content_sha256(execution['content'].get(k)) != content_sha256(v) for k, v in replay.items())
            or execution['content']['gate_sha256'] != content_sha256(report)
            or content_sha256(result['metrics']) != content_sha256({'scenario_count': len(rows), 'scenarios': replay['scenarios']})
            or content_sha256(result['diagnostics']['provenance']) != content_sha256(provenance)
            or content_sha256(execution['content']['provenance']) != content_sha256(provenance)
            or any(result['diagnostics'].get(k) != replay[k] for k in ('scope', 'solution_status', 'number_format'))
            or any(result['diagnostics'].get(k) != 'PENDING' for k in ('scientific_review', 'unit_semantics_review'))):
        raise ValueError('EVIDENCE_REPLAY_MISMATCH')
    # Verify named engine files without following arbitrary paths from an artifact.
    from core.schema import quadratic_solver, polynomial_math, solver_plan
    from core.runtime import quadratic_execution, data_profile, document_extraction, tabular_input
    engines = (quadratic_solver, polynomial_math, solver_plan, quadratic_execution,
               data_profile, document_extraction, tabular_input)
    hashes = {Path(m.__file__).name: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in engines}
    if hashes != execution['content']['engine_sha256']:
        raise ValueError('EVIDENCE_SOLVER_CODE_CHANGED')


def build_graph(run_dir, run_id):
    store = ArtifactStore(run_dir, run_id)
    sources = _sources(store)
    _verify_computation(sources, store)
    graph = {'schema': 'forge-evidence-graph/v1', 'run_id': run_id,
             'problem_id': sources['model_result']['content']['problem_id'],
             'scope': 'quadratic-paper-skeleton/v2', 'artifacts': [], 'facts': [],
             'problems': [], 'ambiguities': [], 'models': [], 'assumptions': [], 'validations': [],
             'formulas': [], 'symbols': [], 'rows': [], 'context': []}
    for envelope in sources.values():
        meta = envelope['meta']
        graph['artifacts'].append({k: copy.deepcopy(meta[k]) for k in
                                   ('artifact_id', 'content_sha256', 'producer', 'input_refs', 'input_hashes')})

    def fact(kind, path):
        envelope = sources[kind]
        ident = 'E' + str(len(graph['facts']) + 1)
        graph['facts'].append({'id': ident, 'value': copy.deepcopy(json_path_get(envelope['content'], path)),
                               'source': {'artifact_id': envelope['meta']['artifact_id'],
                                          'sha256': envelope['meta']['content_sha256'], 'path': path}})
        return ident

    problem = sources['problem_spec']['content']
    for index, question in enumerate(problem['questions']):
        base = f'$.questions[{index}]'
        graph['problems'].append({
            'question_id_ref': fact('problem_spec', base + '.id'),
            'task_ref': fact('problem_spec', base + '.task'),
            'objective_ref': fact('problem_spec', base + '.objective'),
            'sources_ref': fact('problem_spec', base + '.sources'),
            'outputs': [
                {'text_ref': fact('problem_spec', base + f'.required_outputs[{j}].text'),
                 'sources_ref': fact('problem_spec', base + f'.required_outputs[{j}].sources')}
                for j in range(len(question['required_outputs']))],
        })
    for index in range(len(problem['ambiguities'])):
        base = f'$.ambiguities[{index}]'
        graph['ambiguities'].append({
            key + '_ref': fact('problem_spec', base + '.' + key)
            for key in ('id', 'description', 'sources')
        })

    plan = sources['model_plan']['content']
    graph['context'].append({'label': 'selection_phase',
                             'ref': fact('model_plan', '$.selection_phase')})
    for index, question in enumerate(plan['questions']):
        base = f'$.questions[{index}]'
        candidates = question['candidates']
        selected_index = next(i for i, item in enumerate(candidates)
                              if item['id'] == question['selected_id'])
        selected_base = base + f'.candidates[{selected_index}]'
        selected = candidates[selected_index]
        model = {
            'ref': fact('model_plan', base),
            'question_id_ref': fact('model_plan', base + '.question_id'),
            'baseline_id_ref': fact('model_plan', base + '.baseline_id'),
            'selected_id_ref': fact('model_plan', base + '.selected_id'),
            'selected': {key + '_ref': fact('model_plan', selected_base + '.' + key)
                         for key in ('id', 'name', 'rationale', 'sources', 'assumption_refs',
                                     'data_asset_ids', 'limitations')},
            'rejected': [],
        }
        for candidate_index, candidate in enumerate(candidates):
            if candidate_index == selected_index:
                continue
            candidate_base = base + f'.candidates[{candidate_index}]'
            model['rejected'].append({key + '_ref': fact('model_plan', candidate_base + '.' + key)
                                      for key in ('id', 'name', 'rejection_reasons', 'sources')})
        graph['models'].append(model)
        graph['validations'].append({'ref': fact('model_plan', base + '.validation')})
    for index in range(len(plan['assumptions'])):
        graph['assumptions'].append({'ref': fact('model_plan', f'$.assumptions[{index}]')})

    for field in ('scope', 'solution_status', 'scientific_review', 'unit_semantics_review', 'provenance'):
        graph['context'].append({'label': field, 'ref': fact('model_result', '$.diagnostics.' + field)})
    graph['context'].append({'label': 'engine_sha256', 'ref': fact('solver_execution', '$.engine_sha256')})
    derivation = sources['derivation_spec']['content']
    config = sources['solver_plan']['content']
    for index, symbol in enumerate(derivation['symbols']):
        graph['symbols'].append({key: fact('derivation_spec', f'$.symbols[{index}].{key}')
                                 for key in ('name', 'meaning', 'unit', 'domain', 'origin', 'sources')})
    units = {s['name']: s['unit'] for s in derivation['symbols']}
    for index, formula in enumerate(derivation['formulas']):
        graph['formulas'].append({
            'ref': fact('derivation_spec', f'$.formulas[{index}]'),
            'latex': latex(checked_expression(formula['expression'], units)['polynomial']),
            'symbol_refs': [i for i, s in enumerate(derivation['symbols']) if s['name'] in formula['symbol_refs']],
            'parameter_binding_ref': fact('solver_plan', '$.bindings'),
            'execution_ref': fact('solver_execution', '$.objective_id'),
            'mapping_status': 'EXECUTED_OBJECTIVE' if formula['id'] == config['objective_id'] else 'CHECKED_DERIVATION_ONLY'})
    for index, scenario in enumerate(sources['model_result']['content']['metrics']['scenarios']):
        base = f'$.metrics.scenarios[{index}]'
        row = {'scenario': fact('model_result', base + '.scenario'),
               'source_row': fact('model_result', f'$.diagnostics.provenance.source_rows[{index}]'),
               'parameters': fact('model_result', base + '.parameters')}
        for field in ('minimizer', 'minimum', 'stationarity_residual', 'curvature'):
            row[field] = fact('model_result', base + '.' + field)
        graph['rows'].append(row)
    # Recheck snapshot/active pointers after replay and projection.
    if _sources(store) != sources:
        raise ValueError('EVIDENCE_SOURCE_CHANGED')
    return graph


def validate_graph(run_dir, run_id, graph):
    if content_sha256(graph) != content_sha256(build_graph(run_dir, run_id)):
        raise ValueError('EVIDENCE_GRAPH_SOURCE_MISMATCH')


def _register(store, kind, content, parents):
    refs = {e['meta']['artifact_id']: e['meta']['content_sha256'] for e in parents}
    return store.register_json(artifact_type=kind, version=1, content=content, producer=VERSION,
                               input_refs=list(refs), input_hashes=refs)


def check_candidate(run_dir, run_id):
    """Read/verify the stored chain and exported bytes; return the existing GateResult."""
    try:
        from submission.schema.evidence_paper_spec import validate_spec, render, template_contract
        store = ArtifactStore(run_dir, run_id)
        store.registry.verify_integrity()
        graph, template, spec, candidate = [_active(store, k) for k in
                                            ('evidence_graph', 'paper_template', 'paper_spec', 'paper_candidate')]
        validate_graph(run_dir, run_id, graph['content'])
        sources = _sources(store)
        package = sources['problem_package']
        if (content_sha256(template['content']) != content_sha256(template_contract())
                or content_sha256(template['content']) != content_sha256(package['content']['configuration']['paper_template'])):
            raise ValueError('PAPER_TEMPLATE_MISMATCH')
        validate_spec(spec['content'], graph['content'], template['content'])
        for child, parents in ((graph, list(sources.values())), (template, [package]),
                               (spec, [graph, template]), (candidate, [spec])):
            refs = {e['meta']['artifact_id']: e['meta']['content_sha256'] for e in parents}
            if child['meta']['input_hashes'] != refs or child['meta']['input_refs'] != list(refs):
                raise ValueError('PAPER_DEPENDENCY_NOT_CURRENT')
        expected = render(spec['content'])
        content = candidate['content']
        actual = (Path(run_dir) / 'artifacts/paper_candidate.md').read_bytes()
        if content_sha256(content) != content_sha256(_candidate_content(run_id, expected)) or actual != expected.encode('utf-8'):
            raise ValueError('PAPER_CANDIDATE_DRIFT')
        return gate_result('evidence_paper', [
            gate_check('CURRENT_SOURCE_AND_REPLAY', True, actual=graph['meta']['content_sha256']),
            gate_check('ALL_FRAGMENT_BINDINGS', True, actual={'paper_spec': spec['meta']['content_sha256'],
                                                             'bound_facts': len(graph['content']['facts'])}),
            gate_check('EXPORTED_MARKDOWN_MATCH', True, actual=hashlib.sha256(actual).hexdigest(),
                       expected=content['sha256'])], run_id=run_id)
    except (ArtifactError, ValueError, OSError, KeyError, TypeError, IndexError, StopIteration) as exc:
        return gate_result('evidence_paper', [gate_check(_failure_code(exc), False)], run_id=run_id)


def _failure_code(exc):
    code = str(exc)
    return code if isinstance(exc, ValueError) and code.startswith(('EVIDENCE_', 'PAPER_')) and code.isidentifier() else 'EVIDENCE_PAPER_INVALID'


def _candidate_content(run_id, markdown):
    return {'schema': 'forge-paper-candidate/v1', 'run_id': run_id, 'format': 'markdown',
            'status': 'DRAFT_SKELETON', 'human_review': 'PENDING', 'markdown': markdown,
            'sha256': hashlib.sha256(markdown.encode('utf-8')).hexdigest()}


def build_evidence_paper(run_dir, run_id):
    try:
        from submission.schema import evidence_paper_spec as paper
        store = ArtifactStore(run_dir, run_id)
        graph_content = build_graph(run_dir, run_id)
        graph = _register(store, 'evidence_graph', graph_content, list(_sources(store).values()))
        package = _sources(store)['problem_package']
        snapshot = package['content']['configuration']['paper_template']
        if content_sha256(snapshot) != content_sha256(paper.template_contract()):
            raise ValueError('PAPER_TEMPLATE_MISMATCH')
        template = _register(store, 'paper_template', snapshot, [package])
        spec_content = paper.compose(graph['content'], template['content'])
        paper.validate_spec(spec_content, graph['content'], template['content'])
        validate_graph(run_dir, run_id, graph_content)
        spec = _register(store, 'paper_spec', spec_content, [graph, template])
        markdown = paper.render(spec_content)
        _register(store, 'paper_candidate', _candidate_content(run_id, markdown), [spec])
        target = Path(run_dir) / 'artifacts/paper_candidate.md'
        # Never overwrite an existing export, including a manually edited candidate.
        if not target.exists():
            with target.open('xb') as stream:
                stream.write(markdown.encode('utf-8'))
        report = check_candidate(run_dir, run_id)
        write_gate_result(Path(run_dir) / 'gates/evidence_paper.json', report)
        if report['status'] != 'PASS':
            return {'status': 'GATE_FAILED', 'failure_code': 'EVIDENCE_PAPER_INVALID'}
        return {'status': 'READY_FOR_REVIEW', 'failure_code': None,
                'paper_candidate': 'artifacts/paper_candidate.md', 'paper_scope': 'DRAFT_SKELETON',
                'paper_review': 'PENDING'}
    except (ArtifactError, ValueError, OSError, KeyError, TypeError, IndexError, StopIteration) as exc:
        code = _failure_code(exc)
        write_gate_result(Path(run_dir) / 'gates/evidence_paper.json', gate_result(
            'evidence_paper', [gate_check(code, False)], run_id=run_id))
        return {'status': 'BLOCKED', 'failure_code': code}
