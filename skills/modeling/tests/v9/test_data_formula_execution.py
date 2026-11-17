"""Real snapshot/arithmetic tests; synthetic data is not CUMCM capability acceptance."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class DataFormulaTests(unittest.TestCase):
    def module(self, name):
        try:
            return importlib.import_module(name)
        except ImportError:
            self.fail('Missing data/formula execution component: ' + name)

    def package(self, root, data='x,a\n3,1\n-1,2\n', suffix='.csv'):
        from core.runtime.problem_package import create_package
        (root / 'statement.txt').write_text('Evaluate squared deviations.', encoding='utf-8')
        asset = root / ('observations' + suffix)
        asset.write_text(data, encoding='utf-8')
        return create_package(root / 'run', 'r1', 'synthetic', root / 'statement.txt', [asset])

    def contracts(self):
        derivation = {'problem_id': 'synthetic', 'symbols': [
            {'name': 'x', 'unit': 'm'}, {'name': 'a', 'unit': 'm'}], 'formulas': [
            {'id': 'F1', 'expression': '(x-a)**2', 'solver_mapping':
             {'target': 'objective', 'output': 'loss', 'inputs': ['x', 'a']}},
            {'id': 'F2', 'expression': '2*x-2*a', 'solver_mapping':
             {'target': 'gradient', 'output': 'gradient', 'inputs': ['x', 'a']}}]}
        plan = {'problem_id': 'synthetic', 'mode': 'formula_verification', 'asset_id': 'attachment_1',
                'mappings': [{'formula_id': f['id'], 'target': f['solver_mapping']['target'],
                              'output': f['solver_mapping']['output'], 'expression': f['expression'],
                              'bindings': [{'symbol': s, 'column': s, 'unit': 'm'} for s in ['x', 'a']]}
                             for f in derivation['formulas']]}
        return plan, derivation

    def test_profile_reports_measured_rows_missing_and_numeric_range(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package = self.package(root, 'x,a\n3,1\n,2\n-1,NaN\n')
            profile = self.module('core.runtime.data_profile').inspect_package(package, root / 'run', 'r1')
            asset = profile['content']['assets'][0]
            self.assertEqual(3, asset['row_count'])
            self.assertEqual({'name': 'x', 'numeric_count': 2, 'missing_count': 1,
                              'text_count': 0, 'nonfinite_count': 0, 'minimum': '-1', 'maximum': '3'}, asset['columns'][0])
            self.assertEqual(1, asset['columns'][1]['nonfinite_count'])
            self.assertEqual([package['meta']['artifact_id']], profile['meta']['input_refs'])

    def test_malformed_table_is_not_registered_as_inspected(self):
        for data in ('x,x\n1,2\n', 'x,a\n1\n', 'x,a\n', 'x,\n1,2\n'):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                package = self.package(root, data)
                with self.assertRaises(ValueError):
                    self.module('core.runtime.data_profile').inspect_package(package, root / 'run', 'r1')
                registry = json.loads((root / 'run/active_artifacts.json').read_text())
                self.assertNotIn('data_profile', registry['artifacts'])

    def test_snapshot_tamper_is_rejected_before_reading(self):
        from core.schema.artifact_meta import ArtifactError
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package = self.package(root)
            (root / 'run/inputs/attachment_1.csv').write_text('x,a\n99,1\n')
            with self.assertRaises(ArtifactError):
                self.module('core.runtime.data_profile').inspect_package(package, root / 'run', 'r1')

    def test_unsupported_attachment_has_explicit_uninspected_status(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package = self.package(root, suffix='.bin')
            profile = self.module('core.runtime.data_profile').inspect_package(package, root / 'run', 'r1')
            self.assertEqual('UNSUPPORTED', profile['content']['assets'][0]['status'])

    def test_tsv_quoted_fields_are_parsed_not_split_as_lines(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package = self.package(root, 'x\ta\n"3"\t1\n-1\t2\n', '.tsv')
            headers, rows = self.module('core.runtime.data_profile').read_table(package, root / 'run', 'r1', 'attachment_1')
            self.assertEqual(['x', 'a'], headers)
            self.assertEqual([['3', '1'], ['-1', '2']], rows)

    def test_equivalent_implementation_executes_hand_calculated_values(self):
        plan, derivation = self.contracts()
        plan['mappings'][0]['expression'] = 'x*x-2*x*a+a*a'
        gate, evidence = self.module('core.schema.solver_plan').validate_and_execute(
            plan, derivation, ['x', 'a'], [['3', '1'], ['-1', '2']], 'r1')
        self.assertEqual('PASS', gate['status'], gate)
        self.assertEqual(['4', '9'], evidence['formulas'][0]['values'])
        self.assertEqual(['4', '-6'], evidence['formulas'][1]['values'])
        self.assertEqual('NOT_SOLVED', evidence['solution_status'])

    def test_incorrect_mapping_fails_even_when_sample_points_coincide(self):
        plan, derivation = self.contracts()
        plan['mappings'][1]['expression'] = '3*x-2*a'
        gate, evidence = self.module('core.schema.solver_plan').validate_and_execute(
            plan, derivation, ['x', 'a'], [['0', '1']], 'r1')
        self.assertEqual('FAIL', gate['status'])
        self.assertIsNone(evidence)

    def test_parameter_changes_change_execution_and_exact_decimal_values(self):
        plan, derivation = self.contracts()
        module = self.module('core.schema.solver_plan')
        _, first = module.validate_and_execute(plan, derivation, ['x', 'a'], [['0.3', '0.1']], 'r1')
        _, second = module.validate_and_execute(plan, derivation, ['x', 'a'], [['0.3', '0.2']], 'r1')
        self.assertEqual(['1/25'], first['formulas'][0]['values'])
        self.assertEqual(['1/100'], second['formulas'][0]['values'])

    def test_execution_fault_is_detected_by_independent_reference(self):
        from unittest.mock import patch
        from fractions import Fraction
        plan, derivation = self.contracts()
        module = self.module('core.schema.solver_plan')
        with patch.object(module, '_arithmetic', return_value=Fraction(999)):
            gate, evidence = module.validate_and_execute(plan, derivation, ['x', 'a'], [['3', '1']], 'r1')
        self.assertEqual('FAIL', gate['status'])
        self.assertIsNone(evidence)
        self.assertTrue(any(c['name'] == 'SOLVER_EXECUTED_VALUE_MISMATCH' for c in gate['checks']))

    def test_bindings_units_coverage_and_unsafe_code_cannot_pass(self):
        for mutation in ('unit', 'column', 'symbol', 'target', 'missing_formula', 'unsafe', 'fake_pass'):
            plan, derivation = self.contracts()
            m = plan['mappings'][0]
            if mutation == 'unit': m['bindings'][0]['unit'] = 's'
            if mutation == 'column': m['bindings'][0]['column'] = 'absent'
            if mutation == 'symbol': m['bindings'].pop()
            if mutation == 'target': m['target'] = 'other'
            if mutation == 'missing_formula': plan['mappings'].pop()
            if mutation == 'unsafe': m['expression'] = '__import__("os")'
            if mutation == 'fake_pass': plan['status'] = 'PASS'
            with self.subTest(mutation=mutation):
                gate, evidence = self.module('core.schema.solver_plan').validate_and_execute(
                    plan, derivation, ['x', 'a'], [['3', '1']], 'r1')
                self.assertEqual('FAIL', gate['status'])
                self.assertIsNone(evidence)

    def test_missing_nonfinite_and_non_numeric_cells_block_execution(self):
        for value in ('', 'NaN', 'inf', 'text', '1e999999'):
            plan, derivation = self.contracts()
            gate, evidence = self.module('core.schema.solver_plan').validate_and_execute(
                plan, derivation, ['x', 'a'], [[value, '1']], 'r1')
            self.assertEqual('FAIL', gate['status'], value)
            self.assertIsNone(evidence)

    def test_same_symbol_cannot_switch_columns_between_formulas(self):
        plan, derivation = self.contracts()
        plan['mappings'][1]['bindings'][0]['column'] = 'a'
        gate, evidence = self.module('core.schema.solver_plan').validate_and_execute(
            plan, derivation, ['x', 'a'], [['3', '1']], 'r1')
        self.assertEqual('FAIL', gate['status'])
        self.assertIsNone(evidence)

    def test_formula_flag_requires_model_design_and_boolean(self):
        from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
        for enabled, design in [('false', True), (True, False)]:
            with tempfile.TemporaryDirectory() as raw:
                path = Path(raw) / 'workflow.json'
                path.write_text(json.dumps({'schema': 'forge-problem-understanding/v1', 'problem_id': 'p',
                    'statement': 's.txt', 'provider': {'provider': 'codex', 'model': 'test'},
                    'formula_verification': enabled, 'model_design': design}))
                with self.assertRaisesRegex(ValueError, 'FORMULA_VERIFICATION'):
                    ProblemUnderstandingWorkflow(path)

    def test_runtime_registers_only_verified_execution_and_rejects_tampering(self):
        from core.runtime.artifact_store import ArtifactStore
        from core.schema.artifact_meta import content_sha256
        for mutation in (None, 'wrong_expression', 'tamper'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                package = self.package(root)
                store = ArtifactStore(root / 'run', 'r1')
                profile = self.module('core.runtime.data_profile').inspect_package(package, root / 'run', 'r1')
                plan, derivation = self.contracts()
                parents = [package, profile]
                derived = store.register_json(artifact_type='derivation_spec', version=1, content=derivation,
                    producer='test-only-fixture', input_refs=[p['meta']['artifact_id'] for p in parents],
                    input_hashes={p['meta']['artifact_id']: p['meta']['content_sha256'] for p in parents})
                (root / 'run/logs').mkdir()
                (root / 'run/gates').mkdir()
                class Provider:
                    def generate_structured(inner, **kwargs):
                        self.assertEqual(content_sha256(derivation), kwargs['input_refs']['derivation_spec@1'])
                        if mutation == 'wrong_expression': plan['mappings'][0]['expression'] = 'x*x'
                        if mutation == 'tamper': (root / 'run/inputs/attachment_1.csv').write_text('x,a\n9,1\n')
                        return plan, {'provider': 'fixture', 'status': 'completed'}
                result = self.module('core.runtime.formula_execution').build_formula_execution(
                    root / 'run', 'r1', package, profile, derived, Provider())
                registry = json.loads((root / 'run/active_artifacts.json').read_text())
                if mutation:
                    self.assertNotEqual('READY_FOR_REVIEW', result['status'])
                    self.assertNotIn('formula_execution', registry['artifacts'])
                    self.assertNotIn('solver_plan', registry['artifacts'])
                else:
                    self.assertEqual('READY_FOR_REVIEW', result['status'], result)
                    self.assertEqual('FORMULA_VERIFIED_NOT_SOLVED', result['solver_mapping'])
                    self.assertIn('solver_plan', registry['artifacts'])
                    envelope = json.loads((root / 'run' / registry['artifacts']['formula_execution']['path']).read_text())
                    self.assertEqual(['4', '9'], envelope['content']['formulas'][0]['values'])
                    self.assertIn('solver_plan@1', envelope['meta']['input_refs'])
                    self.assertTrue(envelope['content']['engine_sha256'])
                    self.assertNotIn('model_result', registry['artifacts'])


if __name__ == '__main__':
    unittest.main()
