"""Verified quadratic execution → immutable ModelResult v2; no publication."""
import copy
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from core.runtime.artifact_store import ArtifactStore
from core.runtime.data_profile import read_table
from core.runtime.model_design import _verify_active
from core.runtime.problem_package import verify_package
from core.schema.artifact_meta import ArtifactError, content_sha256
from core.schema.gate_result import gate_check, gate_result, write_gate_result
from core.schema.model_result import validate_model_result
from core.schema.quadratic_solver import solve_scenarios


def build_quadratic_execution(run_dir, run_id, package, problem_spec, profile, model_plan, derivation):
    run_dir = Path(run_dir)
    store = ArtifactStore(run_dir, run_id)
    parents = [package, problem_spec, profile, model_plan, derivation]

    def verify():
        verify_package(package, run_dir, run_id)
        for parent in parents:
            _verify_active(store, parent)

    def register(kind, content, producer):
        verify()
        refs = {p['meta']['artifact_id']: p['meta']['content_sha256'] for p in parents}
        envelope = store.register_json(artifact_type=kind, version=1, content=content,
                                      producer=producer, input_refs=list(refs), input_hashes=refs)
        parents.append(envelope)
        return envelope

    try:
        verify()
        if (len(problem_spec['content']['questions']) != 1 or problem_spec['content']['constraints']
                or len(model_plan['content']['questions']) != 1):
            raise ValueError('QUADRATIC_PROBLEM_SCOPE_UNSUPPORTED')
        config = package['content']['configuration']['quadratic_solve']
        question = model_plan['content']['questions'][0]
        candidate = next(c for c in question['candidates'] if c['id'] == question['selected_id'])
        if config['asset_id'] not in candidate['data_asset_ids']:
            raise ValueError('QUADRATIC_MODEL_INPUT_MISMATCH')
        selected = next((a for a in profile['content']['assets'] if a['asset_id'] == config['asset_id']), {})
        provenance = {'asset_id': config['asset_id'], 'source_sha256': selected.get('sha256')}
        if 'data_selection' in package['content']['configuration']:
            from core.runtime.tabular_input import build_tabular_input
            table = build_tabular_input(package, run_dir, run_id)
            parents.append(table)
            data = table['content']
            if data['asset_id'] != config['asset_id'] or selected.get('status') != 'WORKBOOK_INSPECTED':
                raise ValueError('QUADRATIC_ASSET_MISMATCH')
            headers, rows = data['headers'], data['rows']
            provenance.update(source_rows=data['source_rows'], source_columns=data['source_columns'],
                              sheet_id=data['sheet_id'], sheet_name=data['sheet_name'],
                              dropped_rows=data['dropped_rows'], tabular_input_sha256=table['meta']['content_sha256'])
        else:
            if selected.get('status') != 'INSPECTED':
                raise ValueError('QUADRATIC_TABLE_REQUIRED')
            headers, rows = read_table(package, run_dir, run_id, config['asset_id'])
            provenance.update(source_rows=list(range(1, len(rows) + 1)),
                              row_indexing='1-based CSV/TSV data records excluding header',
                              source_columns={h: i for i, h in enumerate(headers, 1)}, dropped_rows=[])
        from core.schema import quadratic_solver, polynomial_math, solver_plan
        from core.runtime import data_profile, document_extraction, tabular_input
        modules = (quadratic_solver, polynomial_math, solver_plan, data_profile, document_extraction, tabular_input)
        paths = [Path(m.__file__) for m in modules] + [Path(__file__)]
        def code_hashes():
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        engines = code_hashes()
        started = datetime.now(timezone.utc).isoformat()
        report, evidence = solve_scenarios(config, derivation['content'], headers, rows, run_id)
        ended = datetime.now(timezone.utc).isoformat()
        write_gate_result(run_dir / 'gates/quadratic_solution.json', report)
        if report['status'] != 'PASS':
            return {'status': 'GATE_FAILED', 'failure_code': 'QUADRATIC_SOLUTION_INVALID'}
        verify()
        if engines != code_hashes():
            raise ValueError('QUADRATIC_ENGINE_CHANGED')
        evidence.update(started_at=started, ended_at=ended, engine_sha256=engines,
                        provenance=provenance, gate_sha256=content_sha256(report))
        result = {'schema': 'forge-model-result/v2', 'run_id': run_id,
                  'problem_id': package['content']['problem_id'], 'model_version': 'strict-convex-quadratic/v1',
                  'parameters': {'solve_config': copy.deepcopy(config)},
                  'metrics': {'scenario_count': len(evidence['scenarios']), 'scenarios': copy.deepcopy(evidence['scenarios'])},
                  'diagnostics': {'solution_status': evidence['solution_status'], 'scope': evidence['scope'],
                                  'scientific_review': 'PENDING', 'unit_semantics_review': 'PENDING',
                                  'number_format': evidence['number_format'], 'provenance': copy.deepcopy(provenance)},
                  'tables': [{'id': 'scenario_optima', 'source_path': '$.metrics.scenarios',
                              'rows': copy.deepcopy(evidence['scenarios'])}],
                  'figures': [], 'rankings': [],
                  'claims': [{'id': 'scenario_optima', 'source_path': '$.metrics.scenarios'}]}
        # Validate before registering any solved execution/result artifact.
        validate_model_result(result, run_id, expected_schema='forge-model-result/v2')
        register('solver_plan', copy.deepcopy(config), 'configured-quadratic-plan/v1')
        execution = register('solver_execution', evidence, 'exact-quadratic-engine/v1')
        result['diagnostics']['execution_artifact_id'] = execution['meta']['artifact_id']
        result['diagnostics']['execution_sha256'] = execution['meta']['content_sha256']
        validate_model_result(result, run_id, expected_schema='forge-model-result/v2')
        registered = register('model_result', result, 'verified-quadratic-result/v1')
        return {'status': 'READY_FOR_REVIEW', 'failure_code': None,
                'solver_mapping': 'VERIFIED_STRICT_CONVEX_QUADRATIC', 'scientific_review': 'PENDING',
                'model_result_artifact': registered['meta']['artifact_id']}
    except (ArtifactError, ValueError, OSError, KeyError, TypeError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).isidentifier() else 'QUADRATIC_INPUT_OR_INTEGRITY_ERROR'
        write_gate_result(run_dir / 'gates/quadratic_solution.json', gate_result(
            'quadratic_solution', [gate_check(code, False)], run_id=run_id))
        return {'status': 'BLOCKED', 'failure_code': code}
