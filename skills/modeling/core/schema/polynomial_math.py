"""Exact, deliberately limited scalar polynomial checks; never evaluate model code."""
import ast
from fractions import Fraction
import re

BASE_UNITS = ('kg', 'm', 's', 'A', 'K', 'mol', 'cd')
DIMENSIONLESS = (0,) * len(BASE_UNITS)


def unit_dimension(unit):
    if unit == '1':
        return DIMENSIONLESS
    result = [0] * len(BASE_UNITS)
    if not isinstance(unit, str) or len(unit) > 100:
        raise ValueError('UNIT_UNSUPPORTED')
    for part in unit.split('*'):
        match = re.fullmatch(r'(kg|m|s|A|K|mol|cd)(?:\^(-?[0-9]{1,2}))?', part)
        if not match:
            raise ValueError('UNIT_UNSUPPORTED')
        exponent = int(match[2] or '1')
        if abs(exponent) > 16:
            raise ValueError('UNIT_UNSUPPORTED')
        result[BASE_UNITS.index(match[1])] += exponent
    return tuple(result)


def _bounded(poly):
    poly = {key: value for key, value in poly.items() if value}
    if len(poly) > 256 or any(sum(p for _, p in key) > 16 for key in poly):
        raise ValueError('MATH_COMPLEXITY_LIMIT')
    if any(max(abs(v.numerator).bit_length(), v.denominator.bit_length()) > 4096 for v in poly.values()):
        raise ValueError('MATH_COMPLEXITY_LIMIT')
    return poly


def _add(left, right, sign=1):
    result = dict(left)
    for key, value in right.items():
        result[key] = result.get(key, Fraction(0)) + sign * value
    return _bounded(result)


def _multiply(left, right):
    if len(left) * len(right) > 4096:
        raise ValueError('MATH_COMPLEXITY_LIMIT')
    result = {}
    for a, x in left.items():
        for b, y in right.items():
            powers = dict(a)
            for symbol, exponent in b:
                powers[symbol] = powers.get(symbol, 0) + exponent
            key = tuple(sorted(powers.items()))
            result[key] = result.get(key, Fraction(0)) + x * y
    return _bounded(result)


def checked_expression(text, symbol_units):
    if not isinstance(text, str) or not text.strip() or len(text) > 2048:
        raise ValueError('MATH_COMPLEXITY_LIMIT')
    try:
        tree = ast.parse(text, mode='eval')
    except (SyntaxError, RecursionError):
        raise ValueError('MATH_SYNTAX_INVALID') from None
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise ValueError('MATH_COMPLEXITY_LIMIT')
    dimensions = {name: unit_dimension(unit) for name, unit in symbol_units.items()}
    used = set()

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = Fraction(ast.get_source_segment(text, node))
            return _bounded({(): value}), DIMENSIONLESS if value else None
        if isinstance(node, ast.Name):
            if node.id not in dimensions:
                raise ValueError('SYMBOL_UNDEFINED')
            used.add(node.id)
            return {((node.id, 1),): Fraction(1)}, dimensions[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            poly, dim = visit(node.operand)
            return ({key: -v for key, v in poly.items()} if isinstance(node.op, ast.USub) else poly), dim
        if not isinstance(node, ast.BinOp):
            raise ValueError('MATH_OPERATION_UNSUPPORTED')
        left, ld = visit(node.left)
        if isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant) or type(node.right.value) is not int or not 0 <= node.right.value <= 8:
                raise ValueError('MATH_OPERATION_UNSUPPORTED')
            exponent = node.right.value
            result = {(): Fraction(1)}
            for _ in range(exponent):
                result = _multiply(result, left)
            return result, tuple(d * exponent for d in ld) if ld is not None else (DIMENSIONLESS if exponent == 0 else None)
        right, rd = visit(node.right)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if ld is not None and rd is not None and ld != rd:
                raise ValueError('UNIT_MISMATCH')
            return _add(left, right, -1 if isinstance(node.op, ast.Sub) else 1), ld if ld is not None else rd
        if isinstance(node.op, ast.Mult):
            return _multiply(left, right), tuple(a+b for a, b in zip(ld, rd)) if ld is not None and rd is not None else None
        if isinstance(node.op, ast.Div) and set(right) == {()} and rd == DIMENSIONLESS:
            return _bounded({key: value / right[()] for key, value in left.items()}), ld
        raise ValueError('MATH_OPERATION_UNSUPPORTED')

    poly, dimension = visit(tree.body)
    return {'polynomial': poly, 'dimension': dimension if poly else None, 'symbols': used}


def differentiate(poly, symbol):
    result = {}
    for key, value in poly.items():
        powers = dict(key)
        exponent = powers.get(symbol, 0)
        if not exponent:
            continue
        if exponent == 1:
            del powers[symbol]
        else:
            powers[symbol] -= 1
        new_key = tuple(sorted(powers.items()))
        result[new_key] = result.get(new_key, Fraction(0)) + exponent * value
    return _bounded(result)


def latex(poly):
    if not poly:
        return '0'
    terms = []
    for key, coefficient in sorted(poly.items(), key=lambda item: (-sum(p for _, p in item[0]), item[0])):
        value = abs(coefficient)
        magnitude = str(value.numerator) if value.denominator == 1 else f'\\frac{{{value.numerator}}}{{{value.denominator}}}'
        factors = [] if key and value == 1 else [magnitude]
        for symbol, exponent in key:
            rendered = symbol if len(symbol) == 1 else '\\mathrm{' + symbol.replace('_', '\\_') + '}'
            factors.append(rendered if exponent == 1 else f'{rendered}^{{{exponent}}}')
        prefix = '-' if coefficient < 0 else '+'
        terms.append((prefix, ' '.join(factors)))
    first_sign, first_text = terms[0]
    return ('-' if first_sign == '-' else '') + first_text + ''.join(f' {s} {t}' for s, t in terms[1:])
