"""ModelPlan/DerivationSpec schemas and real structural/algebraic gates.

PASS means the documented checks passed, not scientific approval of assumptions.
"""
import re

from core.schema.gate_result import gate_check, gate_result
from core.schema.problem_spec import obj, array, TEXT, SOURCES, _shape, _sources, validate_problem_spec
from core.schema.polynomial_math import checked_expression, differentiate, latex, unit_dimension


def enum(*values):
    return {'type': 'string', 'enum': list(values)}


MODEL_PLAN_SCHEMA = obj(
    problem_id=TEXT, selection_phase=enum('pre_computation'),
    assumptions=array(obj(id=TEXT, statement=TEXT, justification=TEXT, sources=SOURCES)),
    questions=array(obj(
        question_id=TEXT, output_refs=array(TEXT, 1), baseline_id=TEXT, selected_id=TEXT,
        candidates=array(obj(id=TEXT, name=TEXT, rationale=TEXT, sources=SOURCES,
                             assumption_refs=array(TEXT), data_asset_ids=array(TEXT),
                             rejection_reasons=array(TEXT), limitations=array(TEXT)), 1),
        validation=obj(method=TEXT, criteria=array(TEXT, 1), data_partition=TEXT, phase=enum('planned'))), 1),
)

DERIVATION_SPEC_SCHEMA = obj(
    problem_id=TEXT,
    symbols=array(obj(name=TEXT, meaning=TEXT, unit=TEXT, domain=enum('real'),
                      origin=enum('variable', 'parameter'), sources=SOURCES), 1),
    conditions=array(obj(id=TEXT, statement=TEXT, assumption_refs=array(TEXT))),
    formulas=array(obj(
        id=TEXT, question_id=TEXT, model_id=TEXT,
        role=enum('objective', 'constraint', 'prediction', 'metric', 'optimality', 'intermediate'),
        expression=TEXT, symbol_refs=array(TEXT), assumption_refs=array(TEXT), condition_refs=array(TEXT),
        depends_on=array(TEXT), rule=enum('definition', 'assumption', 'algebraic_equivalence', 'differentiate'),
        differentiate_by=array(TEXT), explanation=TEXT,
        solver_mapping=obj(target=TEXT, inputs=array(TEXT), output=TEXT, status=enum('planned'))), 1),
)


def _source_checks(content, package):
    assets = {a['id']: a for a in package['content']['assets']}
    checks = []
    for i, source in enumerate(_sources(content)):
        asset = assets.get(source['asset_id'], {})
        line = asset.get('segments', {}).get(source['locator'], '')
        checks.append(gate_check(f'SOURCE_BINDING_{i}', source['sha256'] == asset.get('sha256') and source['quote'] in line))
    return checks


def _unique(items):
    return len(items) == len(set(items))


def validate_model_plan(plan, spec, package):
    checks = []
    try:
        _shape(plan, MODEL_PLAN_SCHEMA)
        checks.append(gate_check('PROBLEM_SPEC_VALID', validate_problem_spec(spec, package)['status'] == 'PASS'))
        checks.append(gate_check('MODEL_PROBLEM_IDENTITY', plan['problem_id'] == spec['problem_id']))
        wanted = {q['id']: {f'{q["id"]}:O{i}' for i, _ in enumerate(q['required_outputs'], 1)} for q in spec['questions']}
        actual = [q['question_id'] for q in plan['questions']]
        checks.append(gate_check('MODEL_QUESTION_COVERAGE', _unique(actual) and set(actual) == set(wanted)))
        assumptions = [a['id'] for a in plan['assumptions']]
        checks.append(gate_check('ASSUMPTION_IDS_UNIQUE', _unique(assumptions)))
        assets = {a['id']: a for a in package['content']['assets']}
        for q in plan['questions']:
            prefix = q['question_id']
            checks.append(gate_check('MODEL_OUTPUT_COVERAGE_' + prefix,
                                     _unique(q['output_refs']) and set(q['output_refs']) == wanted.get(prefix)))
            ids = [c['id'] for c in q['candidates']]
            checks.append(gate_check('MODEL_SELECTION_' + prefix,
                                     _unique(ids) and q['selected_id'] in ids and q['baseline_id'] in ids))
            for candidate in q['candidates']:
                tag = prefix + '_' + candidate['id']
                selected = candidate['id'] == q['selected_id']
                checks.append(gate_check('MODEL_REJECTION_REASON_' + tag,
                                         not candidate['rejection_reasons'] if selected else bool(candidate['rejection_reasons'])))
                checks.append(gate_check('MODEL_ASSUMPTION_REFS_' + tag,
                                         set(candidate['assumption_refs']) <= set(assumptions)))
                refs = candidate['data_asset_ids']
                checks.append(gate_check('MODEL_DATA_REFS_' + tag, set(refs) <= set(assets)))
                if selected:
                    relevant = {a['id'] for a in spec['data_assets'] if prefix in a['question_ids']}
                    checks.append(gate_check('MODEL_QUESTION_DATA_COVERAGE_' + tag, relevant <= set(refs)))
                    checks.append(gate_check('MODEL_SELECTED_DATA_INSPECTED_' + tag,
                                             all(_data_inspected(assets.get(ref, {})) for ref in refs)))
        checks.extend(_source_checks(plan, package))
    except (ValueError, KeyError, TypeError):
        checks.append(gate_check('MODEL_PLAN_SCHEMA_INVALID', False))
    return gate_result('model_plan', checks, run_id=package['meta']['run_id'])


def _data_inspected(asset):
    if asset.get('inspection') == 'text':
        return True
    extraction = asset.get('extraction', {})
    return (asset.get('inspection') == 'structured'
            and extraction.get('format_version') == 'xlsx-cells/v1'
            and isinstance(asset.get('sha256'), str)
            and extraction.get('source_sha256') == asset['sha256']
            and bool(extraction.get('sheets')) and bool(asset.get('segments')))


def validate_derivation(derivation, plan, package):
    checks = []
    try:
        _shape(derivation, DERIVATION_SPEC_SCHEMA)
        _shape(plan, MODEL_PLAN_SCHEMA)
        checks.append(gate_check('DERIVATION_PROBLEM_IDENTITY',
                                 derivation['problem_id'] == plan['problem_id'] == package['content']['problem_id']))
        names = [s['name'] for s in derivation['symbols']]
        checks.append(gate_check('SYMBOL_IDS_UNIQUE', _unique(names) and all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', n) for n in names)))
        units = {s['name']: s['unit'] for s in derivation['symbols']}
        for unit in units.values():
            unit_dimension(unit)
        assumption_ids = {a['id'] for a in plan['assumptions']}
        condition_ids = [c['id'] for c in derivation['conditions']]
        conditions = {c['id']: c for c in derivation['conditions']}
        checks.append(gate_check('CONDITION_IDS_UNIQUE', _unique(condition_ids)))
        for condition in derivation['conditions']:
            checks.append(gate_check('CONDITION_ASSUMPTIONS_' + condition['id'],
                                     set(condition['assumption_refs']) <= assumption_ids))
        selected = {(q['question_id'], q['selected_id']):
                    set(next(c for c in q['candidates'] if c['id'] == q['selected_id'])['assumption_refs'])
                    for q in plan['questions']}
        roots, derived = set(), set()
        seen, evaluated, rooted = {}, {}, {}
        for formula in derivation['formulas']:
            fid = formula['id']
            pair = (formula['question_id'], formula['model_id'])
            checks.append(gate_check('FORMULA_ID_UNIQUE_' + fid, fid not in seen))
            checks.append(gate_check('FORMULA_SELECTED_MODEL_' + fid, pair in selected))
            checks.append(gate_check('FORMULA_ASSUMPTIONS_' + fid,
                                     selected.get(pair, set()) <= set(formula['assumption_refs']) <= assumption_ids))
            checks.append(gate_check('FORMULA_CONDITIONS_' + fid, set(formula['condition_refs']) <= set(condition_ids)))
            condition_premises = {a for ref in formula['condition_refs']
                                  for a in conditions.get(ref, {}).get('assumption_refs', [])}
            checks.append(gate_check('FORMULA_CONDITION_PREMISES_' + fid,
                                     condition_premises <= set(formula['assumption_refs'])))
            refs = formula['depends_on']
            dependencies_valid = _unique(refs) and all(r in seen and (seen[r]['question_id'], seen[r]['model_id']) == pair for r in refs)
            checks.append(gate_check('FORMULA_DEPENDENCIES_' + fid, dependencies_valid))
            for ref in refs:
                if ref in seen:
                    checks.append(gate_check('FORMULA_PREMISES_RETAINED_' + fid + '_' + ref,
                        set(seen[ref]['assumption_refs']) <= set(formula['assumption_refs']) and
                        set(seen[ref]['condition_refs']) <= set(formula['condition_refs'])))
            result = checked_expression(formula['expression'], units)
            checks.append(gate_check('FORMULA_SYMBOL_BINDING_' + fid,
                                     _unique(formula['symbol_refs']) and set(formula['symbol_refs']) == result['symbols']))
            mapping = formula['solver_mapping']
            checks.append(gate_check('SOLVER_MAPPING_PLAN_' + fid,
                                     result['symbols'] <= set(mapping['inputs']) <= set(names)))
            rule = formula['rule']
            if rule in ('definition', 'assumption'):
                checks.append(gate_check('FORMULA_PREMISE_' + fid, not refs and not formula['differentiate_by']))
                if formula['role'] in ('objective', 'prediction', 'metric', 'constraint'):
                    roots.add(pair)
                    rooted[fid] = True
                else:
                    rooted[fid] = False
            else:
                parent = evaluated.get(refs[0]) if len(refs) == 1 and dependencies_valid else None
                rooted[fid] = parent is not None and rooted.get(refs[0], False)
                if rooted[fid]:
                    derived.add(pair)
                if rule == 'algebraic_equivalence':
                    same = parent is not None and not formula['differentiate_by'] and parent['polynomial'] == result['polynomial']
                    checks.append(gate_check('ALGEBRAIC_MATCH_' + fid, same))
                    expected_dimension = parent['dimension'] if parent is not None else None
                else:
                    wrt = formula['differentiate_by']
                    variable = wrt[0] if len(wrt) == 1 and wrt[0] in names else None
                    same = parent is not None and variable is not None and differentiate(parent['polynomial'], variable) == result['polynomial']
                    checks.append(gate_check('DERIVATIVE_MATCH_' + fid, same))
                    expected_dimension = (tuple(a-b for a, b in zip(parent['dimension'], unit_dimension(units[variable])))
                                          if parent is not None and parent['dimension'] is not None and variable is not None else None)
                checks.append(gate_check('DERIVED_UNIT_MATCH_' + fid,
                                         result['dimension'] is None or expected_dimension == result['dimension']))
            rendered = latex(result['polynomial'])
            checks.append(gate_check('FORMULA_RENDERING_' + fid, bool(rendered),
                                     actual={'formula_id': fid, 'latex': rendered, 'dimension': result['dimension']},
                                     message='Generated from parsed expression, not supplied by the model.'))
            seen[fid], evaluated[fid] = formula, result
        checks.append(gate_check('MODEL_FORMULA_COVERAGE', roots == set(selected) and derived == set(selected)))
        checks.extend(_source_checks(derivation, package))
    except (ValueError, KeyError, TypeError, StopIteration, RecursionError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc) in {
            'MATH_OPERATION_UNSUPPORTED', 'MATH_COMPLEXITY_LIMIT', 'MATH_SYNTAX_INVALID',
            'SYMBOL_UNDEFINED', 'UNIT_UNSUPPORTED', 'UNIT_MISMATCH'} else 'DERIVATION_SCHEMA_INVALID'
        checks.append(gate_check(code, False))
    return gate_result('derivation', checks, run_id=package['meta']['run_id'])
