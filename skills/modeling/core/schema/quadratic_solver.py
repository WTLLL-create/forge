"""Exact unconstrained scalar quadratic minimization and independent AST checks."""
from fractions import Fraction

from core.runtime.data_profile import numeric_cell
from core.schema.gate_result import gate_check, gate_result
from core.schema.polynomial_math import checked_expression, unit_dimension
from core.schema.problem_spec import obj, array, TEXT, _shape
from core.schema.solver_plan import _arithmetic

QUADRATIC_SOLVE_SCHEMA = obj(
    mode={'type': 'string', 'enum': ['strict_convex_quadratic']},
    scenario_mode={'type': 'string', 'enum': ['independent_rows']},
    asset_id=TEXT, objective_id=TEXT, decision_symbol=TEXT,
    bindings=array(obj(symbol=TEXT, column=TEXT, unit=TEXT)))


def validate_config(config):
    _shape(config, QUADRATIC_SOLVE_SCHEMA)


def _solve_coefficients(a, b, c):
    x = -b / (2 * a)
    return x, a * x * x + b * x + c


def solve_scenarios(config, derivation, headers, rows, run_id):
    checks = []
    try:
        validate_config(config)
        objectives = [f for f in derivation['formulas'] if f['role'] == 'objective']
        if (len(objectives) != 1 or objectives[0]['id'] != config['objective_id']
                or derivation['conditions'] or objectives[0].get('condition_refs')
                or any(f['role'] == 'constraint' for f in derivation['formulas'])):
            raise ValueError('QUADRATIC_SCOPE_UNSUPPORTED')
        objective = objectives[0]
        symbols = {s['name']: s for s in derivation['symbols']}
        decision = config['decision_symbol']
        if (decision not in symbols or symbols[decision]['origin'] != 'variable'
                or symbols[decision]['domain'] != 'real'):
            raise ValueError('QUADRATIC_DECISION_DOMAIN_UNSUPPORTED')
        expression = checked_expression(objective['expression'], {n: s['unit'] for n, s in symbols.items()})
        names = [b['symbol'] for b in config['bindings']]
        if len(names) != len(set(names)) or set(names) != expression['symbols'] - {decision}:
            raise ValueError('QUADRATIC_PARAMETER_BINDING')
        if decision not in expression['symbols']:
            raise ValueError('QUADRATIC_DECISION_UNUSED')
        if any(dict(powers).get(decision, 0) > 2 for powers in expression['polynomial']):
            raise ValueError('QUADRATIC_DEGREE_UNSUPPORTED')
        for binding in config['bindings']:
            symbol = symbols[binding['symbol']]
            if symbol['origin'] != 'parameter' or symbol['domain'] != 'real' or binding['column'] not in headers:
                raise ValueError('QUADRATIC_PARAMETER_BINDING')
            if unit_dimension(symbol['unit']) != unit_dimension(binding['unit']):
                raise ValueError('QUADRATIC_UNIT_MISMATCH')
        if not rows or len(rows) > 10000 or len(set(headers)) != len(headers):
            raise ValueError('QUADRATIC_INPUT_SIZE_OR_HEADERS')
        scenarios = []
        for index, row in enumerate(rows, 1):
            if len(row) != len(headers):
                raise ValueError('DATA_ROW_WIDTH_INVALID')
            bound = {b['symbol']: numeric_cell(row[headers.index(b['column'])]) for b in config['bindings']}
            coefficients = [Fraction(0), Fraction(0), Fraction(0)]
            for powers, coefficient in expression['polynomial'].items():
                term = coefficient
                for name, exponent in powers:
                    if name != decision:
                        term *= bound[name] ** exponent
                coefficients[dict(powers).get(decision, 0)] += term
            c, b, a = coefficients
            if a <= 0:
                raise ValueError('QUADRATIC_NOT_STRICTLY_CONVEX')
            x, value = _solve_coefficients(a, b, c)
            # Independent of coefficient reduction and the closed-form solver:
            # exact central differences are derivatives for a degree-2 polynomial.
            center = _arithmetic(objective['expression'], dict(bound, **{decision: x}))
            left = _arithmetic(objective['expression'], dict(bound, **{decision: x - 1}))
            right = _arithmetic(objective['expression'], dict(bound, **{decision: x + 1}))
            residual = (right - left) / 2
            curvature = right - 2 * center + left
            checks.extend([
                gate_check(f'STATIONARITY_{index}', residual == 0, actual=str(residual), expected='0'),
                gate_check(f'POSITIVE_CURVATURE_{index}', curvature > 0, actual=str(curvature)),
                gate_check(f'OBJECTIVE_VALUE_{index}', value == center, actual=str(value), expected=str(center)),
            ])
            scenarios.append({'scenario': index, 'minimizer': str(x), 'minimum': str(value),
                              'parameters': {k: str(v) for k, v in bound.items()},
                              'stationarity_residual': str(residual), 'curvature': str(curvature)})
        report = gate_result('quadratic_solution', checks, run_id=run_id)
        evidence = {'problem_id': derivation['problem_id'], 'run_id': run_id,
                    'solution_status': 'VERIFIED_STRICT_CONVEX_QUADRATIC',
                    'scope': 'single-real-variable-unconstrained-independent-rows',
                    'objective_id': objective['id'], 'decision_symbol': decision,
                    'number_format': 'exact rational strings', 'scenarios': scenarios}
        return report, evidence if report['status'] == 'PASS' else None
    except (ValueError, KeyError, TypeError, ZeroDivisionError, OverflowError, RecursionError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).isidentifier() else 'QUADRATIC_INPUT_INVALID'
        checks.append(gate_check(code, False))
        return gate_result('quadratic_solution', checks, run_id=run_id), None
