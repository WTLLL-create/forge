"""Hand-derived quadratic answers; engineering evidence, not CUMCM acceptance."""
import copy
import importlib
from fractions import Fraction
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class QuadraticSolverTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module('core.schema.quadratic_solver')
        except ImportError as exc:
            self.fail('Actual quadratic solver missing: ' + str(exc))

    def fixture(self):
        config = {'mode': 'strict_convex_quadratic', 'scenario_mode': 'independent_rows',
                  'asset_id': 'attachment_1', 'objective_id': 'F1', 'decision_symbol': 'x',
                  'bindings': [{'symbol': 'a', 'column': 'target', 'unit': '1'},
                               {'symbol': 'b', 'column': 'penalty', 'unit': '1'}]}
        derivation = {'problem_id': 'p', 'conditions': [], 'symbols': [
            {'name': 'x', 'unit': '1', 'origin': 'variable', 'domain': 'real'},
            {'name': 'a', 'unit': '1', 'origin': 'parameter', 'domain': 'real'},
            {'name': 'b', 'unit': '1', 'origin': 'parameter', 'domain': 'real'}],
            'formulas': [{'id': 'F1', 'role': 'objective', 'expression': '(x-a)**2+b*x', 'condition_refs': []}]}
        return config, derivation

    def test_solves_nonzero_minimum_and_parameter_change(self):
        config, derivation = self.fixture()
        gate, result = self.module().solve_scenarios(config, derivation, ['target', 'penalty'],
                                                   [['3', '2'], ['5', '2']], 'r')
        self.assertEqual('PASS', gate['status'], gate)
        self.assertEqual(['2', '4'], [r['minimizer'] for r in result['scenarios']])
        self.assertEqual(['5', '9'], [r['minimum'] for r in result['scenarios']])
        self.assertEqual('VERIFIED_STRICT_CONVEX_QUADRATIC', result['solution_status'])

    def test_rational_solution_not_rounded(self):
        config, derivation = self.fixture()
        gate, result = self.module().solve_scenarios(config, derivation, ['target', 'penalty'], [['0.3', '0.1']], 'r')
        self.assertEqual('PASS', gate['status'])
        self.assertEqual('1/4', result['scenarios'][0]['minimizer'])
        self.assertEqual('11/400', result['scenarios'][0]['minimum'])

    def test_wrong_solution_or_objective_is_rejected_by_independent_checker(self):
        module = self.module()
        config, derivation = self.fixture()
        for candidate in ((Fraction(99), Fraction(5)), (Fraction(2), Fraction(99))):
            with self.subTest(candidate=candidate), patch.object(module, '_solve_coefficients', return_value=candidate):
                gate, result = module.solve_scenarios(config, derivation, ['target', 'penalty'], [['3', '2']], 'r')
                self.assertEqual('FAIL', gate['status'])
                self.assertIsNone(result)

    def test_nonconvex_linear_and_high_degree_never_downgraded(self):
        module = self.module()
        for expr in ('-(x-a)**2+b*x', 'x-a+b', '(x-a)**4+b*x'):
            config, derivation = self.fixture()
            derivation['formulas'][0]['expression'] = expr
            gate, result = module.solve_scenarios(config, derivation, ['target', 'penalty'], [['3', '2']], 'r')
            self.assertEqual('FAIL', gate['status'], expr)
            self.assertIsNone(result)

    def test_constraints_nonreal_domain_and_multiple_objectives_block(self):
        module = self.module()
        for mutation in ('condition', 'constraint', 'domain', 'second_objective'):
            config, derivation = self.fixture()
            if mutation == 'condition': derivation['conditions'] = [{'id': 'C1'}]
            if mutation == 'constraint': derivation['formulas'].append({'id': 'C', 'role': 'constraint'})
            if mutation == 'domain': derivation['symbols'][0]['domain'] = 'positive'
            if mutation == 'second_objective': derivation['formulas'].append(dict(derivation['formulas'][0], id='F2'))
            gate, result = module.solve_scenarios(config, derivation, ['target', 'penalty'], [['3', '2']], 'r')
            self.assertEqual('FAIL', gate['status'], mutation)
            self.assertIsNone(result)

    def test_missing_parameter_unit_mismatch_and_decision_data_binding_block(self):
        module = self.module()
        for mutation in ('column', 'unit', 'decision', 'aggregate'):
            config, derivation = self.fixture()
            if mutation == 'column': config['bindings'][0]['column'] = 'absent'
            if mutation == 'unit': config['bindings'][0]['unit'] = 'm'
            if mutation == 'decision': config['bindings'][0]['symbol'] = 'x'
            if mutation == 'aggregate': config['scenario_mode'] = 'sum_rows'
            gate, result = module.solve_scenarios(config, derivation, ['target', 'penalty'], [['3', '2']], 'r')
            self.assertEqual('FAIL', gate['status'], mutation)
            self.assertIsNone(result)

    def test_invalid_later_row_prevents_partial_result(self):
        config, derivation = self.fixture()
        gate, result = self.module().solve_scenarios(config, derivation, ['target', 'penalty'], [['3', '2'], ['', '2']], 'r')
        self.assertEqual('FAIL', gate['status'])
        self.assertIsNone(result)

    def test_unsupported_parameter_domain_does_not_ignore_assumption(self):
        config, derivation = self.fixture()
        derivation['symbols'][1]['domain'] = 'positive'
        gate, result = self.module().solve_scenarios(config, derivation, ['target', 'penalty'], [['-3', '2']], 'r')
        self.assertEqual('FAIL', gate['status'])
        self.assertIsNone(result)


if __name__ == '__main__': unittest.main()
