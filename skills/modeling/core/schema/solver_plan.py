"""Restricted formula-verification plan, not an optimizer or arbitrary code runner."""
import ast
from fractions import Fraction

from core.runtime.data_profile import numeric_cell
from core.schema.artifact_meta import content_sha256
from core.schema.gate_result import gate_check, gate_result
from core.schema.polynomial_math import checked_expression, unit_dimension
from core.schema.problem_spec import obj, array, TEXT, _shape

SOLVER_PLAN_SCHEMA = obj(
    problem_id=TEXT, mode={'type': 'string', 'enum': ['formula_verification']}, asset_id=TEXT,
    mappings=array(obj(formula_id=TEXT, target=TEXT, output=TEXT, expression=TEXT,
                       bindings=array(obj(symbol=TEXT, column=TEXT, unit=TEXT))), 1))


def _arithmetic(expression, bindings):
    """Execute the AST directly, independently of polynomial expansion; no eval/exec."""
    def visit(node):
        if isinstance(node, ast.Name):
            return bindings[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Fraction(ast.get_source_segment(expression, node))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if isinstance(node.op, ast.Div): return left / right
            if isinstance(node.op, ast.Pow) and right.denominator == 1 and 0 <= right <= 8:
                return left ** int(right)
        raise ValueError('SOLVER_OPERATION_UNSUPPORTED')
    return visit(ast.parse(expression, mode='eval').body)


def _polynomial_value(poly, bindings):
    total = Fraction(0)
    for powers, coefficient in poly.items():
        term = coefficient
        for name, exponent in powers:
            term *= bindings[name] ** exponent
        total += term
    return total


def validate_and_execute(plan, derivation, headers, rows, run_id):
    checks = []
    evidence = None
    try:
        _shape(plan, SOLVER_PLAN_SCHEMA)
        if plan['problem_id'] != derivation['problem_id']:
            raise ValueError('SOLVER_PROBLEM_MISMATCH')
        formulas = {f['id']: f for f in derivation['formulas']}
        mappings = plan['mappings']
        ids = [m['formula_id'] for m in mappings]
        if len(ids) != len(set(ids)) or set(ids) != set(formulas):
            raise ValueError('SOLVER_FORMULA_COVERAGE')
        if not rows or len(rows) * len(mappings) > 100000 or len(set(headers)) != len(headers):
            raise ValueError('SOLVER_EXECUTION_SIZE_OR_HEADERS')
        units = {s['name']: s['unit'] for s in derivation['symbols']}
        prepared = []
        symbol_columns = {}
        for mapping in mappings:
            formula = formulas[mapping['formula_id']]
            if any(mapping[k] != formula['solver_mapping'][k] for k in ('target', 'output')):
                raise ValueError('SOLVER_MAPPING_IDENTITY')
            expected = checked_expression(formula['expression'], units)
            executable = checked_expression(mapping['expression'], units)
            bindings = mapping['bindings']
            names = [b['symbol'] for b in bindings]
            if len(names) != len(set(names)) or set(names) != expected['symbols'] | executable['symbols']:
                raise ValueError('SOLVER_SYMBOL_BINDING')
            for binding in bindings:
                if binding['column'] not in headers:
                    raise ValueError('SOLVER_COLUMN_UNKNOWN')
                prior = symbol_columns.setdefault(binding['symbol'], binding['column'])
                if prior != binding['column']:
                    raise ValueError('SOLVER_SYMBOL_COLUMN_CONFLICT')
                if unit_dimension(binding['unit']) != unit_dimension(units[binding['symbol']]):
                    raise ValueError('SOLVER_UNIT_MISMATCH')
            match = expected['polynomial'] == executable['polynomial'] and expected['dimension'] == executable['dimension']
            checks.append(gate_check('SOLVER_EXACT_MAPPING_' + formula['id'], match))
            prepared.append((mapping, expected['polynomial']))
        if any(c['status'] != 'PASS' for c in checks):
            return gate_result('solver_mapping', checks, run_id=run_id), None
        results = []
        for mapping, poly in prepared:
            values = []
            for row in rows:
                if len(row) != len(headers):
                    raise ValueError('DATA_ROW_WIDTH_INVALID')
                bound = {b['symbol']: numeric_cell(row[headers.index(b['column'])]) for b in mapping['bindings']}
                actual = _arithmetic(mapping['expression'], bound)
                if actual != _polynomial_value(poly, bound):
                    raise ValueError('SOLVER_EXECUTED_VALUE_MISMATCH')
                values.append(str(actual))
            results.append({'formula_id': mapping['formula_id'], 'target': mapping['target'],
                            'output': mapping['output'], 'expression_sha256': content_sha256(mapping['expression']),
                            'values': values})
        executed = sum(len(f['values']) for f in results)
        checks.append(gate_check('SOLVER_ROWS_EXECUTED', executed == len(rows) * len(mappings),
                                actual=executed, expected=len(rows) * len(mappings)))
        evidence = {'problem_id': plan['problem_id'], 'run_id': run_id, 'solution_status': 'NOT_SOLVED',
                    'mode': 'formula_verification', 'asset_id': plan['asset_id'],
                    'row_indexing': '1-based CSV data records, excluding header', 'row_count': len(rows),
                    'number_format': 'exact rational strings', 'unit_semantics_review': 'PENDING', 'formulas': results}
    except (ValueError, KeyError, TypeError, ZeroDivisionError, OverflowError, RecursionError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).isidentifier() else 'SOLVER_INPUT_INVALID'
        checks.append(gate_check(code, False))
    report = gate_result('solver_mapping', checks, run_id=run_id)
    return report, evidence if report['status'] == 'PASS' else None
