"""Model selection/derivation engineering fixtures, not benchmark capability evidence."""
import copy
import importlib
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class ModelDesignTests(unittest.TestCase):
    def module(self, name):
        try:
            return importlib.import_module(name)
        except ImportError:
            self.fail('Model design component missing: ' + name)

    def fixture(self, root):
        from core.runtime.problem_package import create_package
        statement = root / 'statement.txt'
        statement.write_text('Q1: Minimize squared deviation of real x from target a.\n', encoding='utf-8')
        package = create_package(root / 'fixture_run', 'fixture', 'synthetic-design', statement)
        source = {'asset_id': 'statement', 'sha256': package['content']['assets'][0]['sha256'],
                  'locator': 'L1', 'quote': 'Minimize squared deviation of real x from target a.'}
        spec = {'problem_id': 'synthetic-design', 'background': [], 'questions': [
            {'id': 'Q1', 'task': 'Minimize squared deviation', 'objective': 'Find a minimizer',
             'sources': [source], 'required_outputs': [{'text': 'A minimizer', 'sources': [source]}]}],
            'data_assets': [], 'constraints': [], 'evaluation_criteria': [], 'ambiguities': [],
            'assumptions_requiring_confirmation': []}
        candidate = {'id': 'B1', 'name': 'Squared loss', 'rationale': 'Task explicitly asks for squared deviation',
                     'sources': [source], 'assumption_refs': ['A1'], 'data_asset_ids': [],
                     'rejection_reasons': [], 'limitations': ['Scalar unconstrained setting only']}
        alternative = dict(candidate, id='C1', name='Absolute loss',
                           rejection_reasons=['Does not match the requested squared loss'])
        plan = {'problem_id': 'synthetic-design', 'selection_phase': 'pre_computation',
                'assumptions': [{'id': 'A1', 'statement': 'x and a are real scalars',
                                 'justification': 'Simplified task domain', 'sources': [source]}],
                'questions': [{'question_id': 'Q1', 'output_refs': ['Q1:O1'], 'baseline_id': 'B1',
                               'selected_id': 'B1', 'candidates': [candidate, alternative],
                               'validation': {'method': 'Check the derivative and objective near the solution',
                                              'criteria': ['Stationarity and nonnegative loss'],
                                              'data_partition': 'Analytic fixture; no fitted training data',
                                              'phase': 'planned'}}]}
        formula = {'id': 'F1', 'question_id': 'Q1', 'model_id': 'B1', 'role': 'objective',
                   'expression': '(x-a)**2', 'symbol_refs': ['x', 'a'], 'assumption_refs': ['A1'],
                   'condition_refs': [], 'depends_on': [], 'rule': 'definition', 'differentiate_by': [],
                   'explanation': 'Squared deviation objective',
                   'solver_mapping': {'target': 'objective', 'inputs': ['x', 'a'],
                                      'output': 'loss', 'status': 'planned'}}
        gradient = dict(formula, id='F2', expression='2*x-2*a', role='optimality', depends_on=['F1'],
                        rule='differentiate', differentiate_by=['x'], explanation='Differentiate objective',
                        solver_mapping={'target': 'objective_gradient', 'inputs': ['x', 'a'],
                                        'output': 'gradient', 'status': 'planned'})
        derivation = {'problem_id': 'synthetic-design', 'symbols': [
            {'name': 'x', 'meaning': 'decision', 'unit': 'm', 'domain': 'real', 'origin': 'variable', 'sources': [source]},
            {'name': 'a', 'meaning': 'target', 'unit': 'm', 'domain': 'real', 'origin': 'parameter', 'sources': [source]}],
            'conditions': [], 'formulas': [formula, gradient]}
        return package, spec, plan, derivation

    def test_polynomial_equivalence_derivative_and_latex_are_computed(self):
        m = self.module('core.schema.polynomial_math')
        left = m.checked_expression('x*x + x*x', {'x': 'm'})
        right = m.checked_expression('2*x**2', {'x': 'm'})
        self.assertEqual(left['polynomial'], right['polynomial'])
        self.assertEqual(m.checked_expression('4*x', {'x': 'm'})['polynomial'],
                         m.differentiate(right['polynomial'], 'x'))
        self.assertEqual('2 x^{2}', m.latex(right['polynomial']))

    def test_unsafe_unsupported_and_dimensionally_wrong_math_is_rejected(self):
        m = self.module('core.schema.polynomial_math')
        for expression in ['__import__("os")', 'x+t', 'x**-1', '1/x', 'sin(x)', 'unknown+1', 'x**9999']:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                m.checked_expression(expression, {'x': 'm', 't': 's'})

    def test_exact_rationals_not_floating_tolerance(self):
        m = self.module('core.schema.polynomial_math')
        self.assertEqual(m.checked_expression('x/3+x/3+x/3', {'x': '1'})['polynomial'],
                         m.checked_expression('x', {'x': '1'})['polynomial'])
        self.assertNotEqual(m.checked_expression('0.999*x', {'x': '1'})['polynomial'],
                            m.checked_expression('x', {'x': '1'})['polynomial'])

    def test_valid_plan_and_derivation_generate_real_checks(self):
        with tempfile.TemporaryDirectory() as raw:
            package, spec, plan, derivation = self.fixture(Path(raw))
            m = self.module('core.schema.model_design')
            self.assertEqual('PASS', m.validate_model_plan(plan, spec, package)['status'])
            gate = m.validate_derivation(derivation, plan, package)
            self.assertEqual('PASS', gate['status'], gate)
            self.assertTrue(any(c['name'].startswith('DERIVATIVE_MATCH') for c in gate['checks']))

    def test_plan_coverage_sources_baseline_and_rejected_reasons_are_checked(self):
        with tempfile.TemporaryDirectory() as raw:
            package, spec, plan, _ = self.fixture(Path(raw))
            for mutation in ('question', 'output', 'source', 'baseline', 'rejection', 'posthoc', 'empty_validation'):
                candidate = copy.deepcopy(plan)
                q = candidate['questions'][0]
                if mutation == 'question': q['question_id'] = 'Q9'
                if mutation == 'output': q['output_refs'] = []
                if mutation == 'source': q['candidates'][0]['sources'][0]['sha256'] = '0' * 64
                if mutation == 'baseline': q['baseline_id'] = 'missing'
                if mutation == 'rejection': q['candidates'][1]['rejection_reasons'] = []
                if mutation == 'posthoc': candidate['selection_phase'] = 'after_results'
                if mutation == 'empty_validation': q['validation']['criteria'] = []
                with self.subTest(mutation=mutation):
                    self.assertEqual('FAIL', self.module('core.schema.model_design').validate_model_plan(candidate, spec, package)['status'])

    def test_derivation_rejects_wrong_gradient_symbols_links_and_fake_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            package, _, plan, derivation = self.fixture(Path(raw))
            for mutation in ('gradient', 'undefined', 'model', 'dependency', 'mapping', 'assumption', 'self_pass', 'no_steps'):
                value = copy.deepcopy(derivation)
                f = value['formulas'][1]
                if mutation == 'gradient': f['expression'] = '3*x-2*a'
                if mutation == 'undefined': f['expression'] = '2*z'
                if mutation == 'model': f['model_id'] = 'C1'
                if mutation == 'dependency': f['depends_on'] = ['F2']
                if mutation == 'mapping': f['solver_mapping']['inputs'] = []
                if mutation == 'assumption': f['assumption_refs'] = []
                if mutation == 'self_pass': value['verified'] = True
                if mutation == 'no_steps': value['formulas'].pop()
                with self.subTest(mutation=mutation):
                    self.assertEqual('FAIL', self.module('core.schema.model_design').validate_derivation(value, plan, package)['status'])

    def test_opaque_attachment_cannot_support_selected_model(self):
        with tempfile.TemporaryDirectory() as raw:
            package, spec, plan, _ = self.fixture(Path(raw))
            package['content']['assets'].append({'id': 'attachment_1', 'inspection': 'opaque'})
            plan['questions'][0]['candidates'][0]['data_asset_ids'] = ['attachment_1']
            self.assertEqual('FAIL', self.module('core.schema.model_design').validate_model_plan(plan, spec, package)['status'])

    def test_structured_label_alone_or_wrong_source_hash_cannot_prove_inspection(self):
        with tempfile.TemporaryDirectory() as raw:
            package, spec, plan, _ = self.fixture(Path(raw))
            asset = {'id': 'attachment_1', 'inspection': 'structured', 'sha256': 'a' * 64,
                     'segments': {'S1!A1': '1'}}
            package['content']['assets'].append(asset)
            plan['questions'][0]['candidates'][0]['data_asset_ids'] = ['attachment_1']
            for extraction in (None, {'format_version': 'xlsx-cells/v1', 'source_sha256': 'b' * 64,
                                      'sheets': [{'sheet_id': 'S1'}]}):
                if extraction is not None: asset['extraction'] = extraction
                self.assertEqual('FAIL', self.module('core.schema.model_design').validate_model_plan(plan, spec, package)['status'])

    def test_selected_model_cannot_hide_an_uninspected_question_attachment(self):
        with tempfile.TemporaryDirectory() as raw:
            package, spec, plan, _ = self.fixture(Path(raw))
            source = spec['questions'][0]['sources'][0]
            package['content']['assets'].append({'id': 'attachment_1', 'inspection': 'opaque',
                                                 'segments': {}, 'sha256': 'a' * 64})
            spec['data_assets'] = [{'id': 'attachment_1', 'role': 'Required input', 'certainty': 'unknown',
                                   'question_ids': ['Q1'], 'sources': [source]}]
            spec['ambiguities'] = [{'id': 'U1', 'description': 'Input not inspected', 'sources': [source]}]
            from core.schema.problem_spec import validate_problem_spec
            self.assertEqual('PASS', validate_problem_spec(spec, package)['status'])
            self.assertEqual('FAIL', self.module('core.schema.model_design').validate_model_plan(plan, spec, package)['status'])

    def test_unrelated_derivative_does_not_complete_model_derivation(self):
        with tempfile.TemporaryDirectory() as raw:
            package, _, plan, derivation = self.fixture(Path(raw))
            unrelated = copy.deepcopy(derivation['formulas'][0])
            unrelated.update(id='UNRELATED', role='intermediate', expression='x', symbol_refs=['x'])
            derivation['formulas'].insert(1, unrelated)
            derivation['formulas'][-1].update(expression='1', symbol_refs=[], depends_on=['UNRELATED'])
            self.assertEqual('FAIL', self.module('core.schema.model_design').validate_derivation(derivation, plan, package)['status'])

    def test_condition_assumptions_cannot_disappear_from_formula(self):
        with tempfile.TemporaryDirectory() as raw:
            package, _, plan, derivation = self.fixture(Path(raw))
            extra = copy.deepcopy(plan['assumptions'][0])
            extra['id'] = 'A2'
            plan['assumptions'].append(extra)
            derivation['conditions'] = [{'id': 'C1', 'statement': 'Additional domain premise', 'assumption_refs': ['A2']}]
            derivation['formulas'][0]['condition_refs'] = ['C1']
            derivation['formulas'][1]['condition_refs'] = ['C1']
            self.assertEqual('FAIL', self.module('core.schema.model_design').validate_derivation(derivation, plan, package)['status'])

    def workflow(self, root, mutation=None, formula_verification=False, xlsx=False, quadratic=False, quadratic_data=None, paper_candidate=False, docx_candidate=False):
        package, spec, plan, derivation = self.fixture(root)
        solver_plan = None
        if formula_verification:
            import hashlib
            data = b'x,a\n3,1\n-1,2\n'
            if quadratic_data is not None:
                data = quadratic_data
            if mutation == 'malformed_data':
                data = b'x,a\n3\n'
            (root / 'observations.csv').write_bytes(data)
            if xlsx:
                from openpyxl import Workbook
                book = Workbook()
                for row in (['x', 'a'], [3, 1], [-1, 2]): book.active.append(row)
                book.save(root / 'observations.xlsx')
                book.close()
                data = (root / 'observations.xlsx').read_bytes()
            spec['data_assets'] = [{'id': 'attachment_1', 'role': 'Evaluation points',
                'certainty': 'inferred', 'question_ids': ['Q1'], 'sources': spec['questions'][0]['sources']}]
            spec['ambiguities'] = [{'id': 'DATA_ROLE', 'description': 'Evaluation role and units require confirmation',
                                    'sources': spec['questions'][0]['sources']}]
            plan['questions'][0]['candidates'][0]['data_asset_ids'] = ['attachment_1']
            solver_plan = {'problem_id': spec['problem_id'], 'mode': 'formula_verification',
                          'asset_id': 'attachment_1', 'mappings': [
                              {'formula_id': f['id'], 'target': f['solver_mapping']['target'],
                               'output': f['solver_mapping']['output'], 'expression': f['expression'],
                               'bindings': [{'symbol': s, 'column': s, 'unit': 'm'} for s in ['x', 'a']]}
                              for f in derivation['formulas']]}
        reference = {'problem_id': spec['problem_id'], 'reviewer': 'independent-fixture-reviewer', 'status': 'APPROVED',
                     'input_hashes': {'statement': package['content']['assets'][0]['sha256']},
                     'questions': [{'id': 'Q1', 'required_outputs': [
                         {k: v for k, v in spec['questions'][0]['sources'][0].items() if k != 'sha256'}]}],
                     'background_locators': []}
        if formula_verification:
            reference['input_hashes']['attachment_1'] = hashlib.sha256(data).hexdigest()
        (root / 'reference.json').write_text(json.dumps(reference), encoding='utf-8')
        config = {'schema': 'forge-problem-understanding/v1', 'problem_id': spec['problem_id'],
                  'statement': 'statement.txt', 'attachments': [], 'reference': 'reference.json',
                  'provider': {'provider': 'codex', 'model': 'test-model'}, 'model_design': True}
        if formula_verification:
            config.update(formula_verification=True, attachments=['observations.csv'])
            if xlsx:
                config.update(attachments=['observations.xlsx'], data_selection={
                    'asset_id': 'attachment_1', 'sheet_id': 'S1', 'header_row': 1,
                    'first_data_row': 2, 'last_data_row': 3,
                    'columns': [{'column': 'A', 'name': 'x', 'expected_header': 'x'},
                                {'column': 'B', 'name': 'a', 'expected_header': 'a'}]})
        path = root / 'workflow.json'
        if paper_candidate:
            config['paper_candidate'] = True
        if docx_candidate:
            config['docx_candidate'] = True
        if quadratic:
            config.pop('formula_verification', None)
            config['quadratic_solve'] = {'mode': 'strict_convex_quadratic',
                'scenario_mode': 'independent_rows', 'asset_id': 'attachment_1',
                'objective_id': 'F1', 'decision_symbol': 'x',
                'bindings': [{'symbol': 'a', 'column': 'a', 'unit': 'm'}]}
        path.write_text(json.dumps(config), encoding='utf-8')
        calls = []
        def transport(command, **kwargs):
            if '--version' in command:
                return subprocess.CompletedProcess(command, 0, b'codex-cli 0.153.4', b'')
            if 'login' in command:
                return subprocess.CompletedProcess(command, 0, b'Logged in using ChatGPT', b'')
            body = {'prompt': kwargs['input_text'], 'schema': json.loads(Path(command[command.index('--output-schema')+1]).read_text())}
            self.assertNotIn('independent-fixture-reviewer', json.dumps(body))
            self.assertNotIn('background_locators', json.dumps(body))
            calls.append(body)
            response = copy.deepcopy([spec, plan, derivation, solver_plan][len(calls)-1])
            if mutation == 'undeclared_solver_input' and len(calls) == 1:
                response['data_assets'][0]['question_ids'] = []
            if mutation == 'undeclared_solver_input' and len(calls) == 2:
                response['questions'][0]['candidates'][0]['data_asset_ids'] = []
            if mutation == 'bad_solver' and len(calls) == 4:
                response['mappings'][0]['expression'] = 'x*x'
            if mutation == 'bad_plan' and len(calls) == 2:
                response['questions'][0]['output_refs'] = []
            if mutation == 'bad_gradient' and len(calls) == 3:
                response['formulas'][1]['expression'] = '3*x'
            if mutation == 'unsupported' and len(calls) == 3:
                response['formulas'][1]['expression'] = 'sin(x)'
            if mutation == 'tamper' and len(calls) == 2:
                next((root / 'runtime/runs').glob('*/inputs/statement.txt')).write_text('tampered')
            from test_codex_provider import events
            return subprocess.CompletedProcess(command, 0, events(response), b'')
        from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
        with patch.dict(os.environ, {}, clear=True), patch('shutil.which', return_value=sys.executable):
            outcome = ProblemUnderstandingWorkflow(path).run(transport=transport)
        return outcome, calls

    def test_full_workflow_executes_formulas_and_blocks_bad_solver(self):
        for mutation in (None, 'bad_solver'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as raw:
                result, calls = self.workflow(Path(raw), mutation, formula_verification=True)
                run = Path(result['run_dir'])
                registry = json.loads((run / 'active_artifacts.json').read_text())
                self.assertEqual(4, len(calls), result)
                if mutation:
                    self.assertEqual('GATE_FAILED', result['status'], result)
                    self.assertNotIn('formula_execution', registry['artifacts'])
                else:
                    self.assertEqual('READY_FOR_REVIEW', result['status'], result)
                    self.assertEqual('FORMULA_VERIFIED_NOT_SOLVED', result['solver_mapping'])
                    self.assertIn('formula_execution', registry['artifacts'])
                    self.assertIn('data_profile', calls[1]['prompt'])
                    self.assertNotIn('formula_execution', calls[1]['prompt'])

    def test_full_workflow_xlsx_selection_reaches_verified_arithmetic(self):
        with tempfile.TemporaryDirectory() as raw:
            result, calls = self.workflow(Path(raw), formula_verification=True, xlsx=True)
            self.assertEqual('READY_FOR_REVIEW', result['status'], result)
            self.assertEqual(4, len(calls))
            run = Path(result['run_dir'])
            registry = json.loads((run / 'active_artifacts.json').read_text())
            result_path = run / registry['artifacts']['formula_execution']['path']
            evidence = json.loads(result_path.read_text())
            self.assertEqual(['4', '9'], evidence['content']['formulas'][0]['values'])
            self.assertEqual([2, 3], evidence['content']['source_rows'])
            self.assertIn('tabular_input@1', evidence['meta']['input_refs'])
            self.assertEqual('NOT_SOLVED', evidence['content']['solution_status'])
            self.assertNotIn('model_result', registry['artifacts'])

    def test_actual_solver_produces_v2_from_csv_and_xlsx(self):
        from core.schema.model_result import validate_model_result
        for xlsx in (False, True):
            with self.subTest(xlsx=xlsx), tempfile.TemporaryDirectory() as raw:
                try:
                    result, calls = self.workflow(Path(raw), formula_verification=True, xlsx=xlsx, quadratic=True)
                except ValueError as exc:
                    self.fail('Real solve mode is not connected: ' + str(exc))
                self.assertEqual('READY_FOR_REVIEW', result['status'], result)
                self.assertEqual(3, len(calls), 'A configured deterministic solver needs no fourth LLM call')
                run = Path(result['run_dir'])
                registry = json.loads((run / 'active_artifacts.json').read_text())
                envelope = json.loads((run / registry['artifacts']['model_result']['path']).read_text())
                model = envelope['content']
                validate_model_result(model, result['run_id'], expected_schema='forge-model-result/v2')
                self.assertEqual(['1', '2'], [s['minimizer'] for s in model['metrics']['scenarios']])
                self.assertEqual(['0', '0'], [s['minimum'] for s in model['metrics']['scenarios']])
                self.assertIn('solver_execution@1', envelope['meta']['input_refs'])
                self.assertEqual('PENDING', model['diagnostics']['scientific_review'])
                self.assertNotIn('formula_execution', registry['artifacts'])

    def test_injected_wrong_optimum_never_registers_result(self):
        from fractions import Fraction
        try:
            from core.schema import quadratic_solver
        except ImportError as exc:
            self.fail(str(exc))
        with tempfile.TemporaryDirectory() as raw, patch.object(quadratic_solver, '_solve_coefficients',
                                                               return_value=(Fraction(99), Fraction(0))):
            try:
                result, _ = self.workflow(Path(raw), formula_verification=True, quadratic=True)
            except ValueError as exc:
                self.fail('Real solve mode is not connected: ' + str(exc))
            self.assertEqual('GATE_FAILED', result['status'], result)
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text())
            self.assertNotIn('model_result', registry['artifacts'])
            self.assertNotIn('solver_execution', registry['artifacts'])

    def test_parameter_changes_change_real_model_result_and_source_hash(self):
        models = []
        for data in (b'x,a\n3,1\n-1,2\n', b'x,a\n3,5\n-1,7\n'):
            with tempfile.TemporaryDirectory() as raw:
                outcome, _ = self.workflow(Path(raw), formula_verification=True, quadratic=True, quadratic_data=data)
                self.assertEqual('READY_FOR_REVIEW', outcome['status'], outcome)
                run = Path(outcome['run_dir'])
                registry = json.loads((run / 'active_artifacts.json').read_text())
                models.append(json.loads((run / registry['artifacts']['model_result']['path']).read_text())['content'])
        self.assertEqual(['1', '2'], [s['minimizer'] for s in models[0]['metrics']['scenarios']])
        self.assertEqual(['5', '7'], [s['minimizer'] for s in models[1]['metrics']['scenarios']])
        self.assertNotEqual(models[0]['diagnostics']['provenance']['source_sha256'],
                            models[1]['diagnostics']['provenance']['source_sha256'])

    def test_solver_path_rejects_snapshot_tampering(self):
        with tempfile.TemporaryDirectory() as raw:
            result, _ = self.workflow(Path(raw), mutation='tamper', formula_verification=True, quadratic=True)
            self.assertNotEqual('READY_FOR_REVIEW', result['status'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text())
            self.assertNotIn('model_result', registry['artifacts'])

    def test_solver_cannot_use_input_absent_from_selected_model(self):
        with tempfile.TemporaryDirectory() as raw:
            outcome, _ = self.workflow(Path(raw), mutation='undeclared_solver_input', formula_verification=True, quadratic=True)
            self.assertEqual('BLOCKED', outcome['status'], outcome)
            self.assertEqual('QUADRATIC_MODEL_INPUT_MISMATCH', outcome['failure_code'])

    def test_malformed_data_stops_planning_with_real_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            result, calls = self.workflow(Path(raw), 'malformed_data', formula_verification=True)
            self.assertEqual('BLOCKED', result['status'])
            self.assertEqual(1, len(calls))
            run = Path(result['run_dir'])
            gate_path = run / 'gates/data_profile.json'
            self.assertTrue(gate_path.exists(), 'Inspection failure must leave an actual gate result')
            self.assertEqual('FAIL', json.loads(gate_path.read_text())['status'])
            registry = json.loads((run / 'active_artifacts.json').read_text())
            self.assertNotIn('model_plan', registry['artifacts'])

    def test_opt_in_workflow_registers_linked_contracts_and_review_not_publication(self):
        with tempfile.TemporaryDirectory() as raw:
            result, calls = self.workflow(Path(raw))
            self.assertEqual('READY_FOR_REVIEW', result['status'], result)
            self.assertEqual(3, len(calls))
            self.assertEqual('PLANNED_NOT_EXECUTED', result['solver_mapping'])
            run = Path(result['run_dir'])
            registry = json.loads((run / 'active_artifacts.json').read_text())
            self.assertIn('data_profile', registry['artifacts'])
            self.assertEqual('model_plan@1', registry['artifacts']['model_plan']['artifact_id'])
            self.assertEqual('derivation_spec@1', registry['artifacts']['derivation_spec']['artifact_id'])
            envelope = json.loads((run / registry['artifacts']['derivation_spec']['path']).read_text())
            self.assertIn('model_plan@1', envelope['meta']['input_refs'])
            self.assertIn('PENDING', (run / 'artifacts/model_design_review.md').read_text())
            self.assertFalse((run / 'artifacts/published').exists())

    def test_invalid_plan_stops_before_derivation_and_preserves_candidate(self):
        with tempfile.TemporaryDirectory() as raw:
            result, calls = self.workflow(Path(raw), 'bad_plan')
            self.assertEqual('GATE_FAILED', result['status'])
            self.assertEqual(2, len(calls))
            run = Path(result['run_dir'])
            registry = json.loads((run / 'active_artifacts.json').read_text())
            self.assertNotIn('model_plan', registry['artifacts'])
            self.assertTrue((run / 'artifacts/model_plan.rejected.json').exists())

    def test_wrong_derivative_never_activates_derivation(self):
        with tempfile.TemporaryDirectory() as raw:
            result, _ = self.workflow(Path(raw), 'bad_gradient')
            self.assertEqual('GATE_FAILED', result['status'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text())
            self.assertNotIn('derivation_spec', registry['artifacts'])

    def test_mutating_snapshot_during_planning_blocks_activation(self):
        with tempfile.TemporaryDirectory() as raw:
            result, calls = self.workflow(Path(raw), 'tamper')
            self.assertEqual('BLOCKED', result['status'])
            self.assertEqual(2, len(calls))
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text())
            self.assertNotIn('model_plan', registry['artifacts'])

    def test_unsupported_mathematics_is_blocked_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as raw:
            result, _ = self.workflow(Path(raw), 'unsupported')
            self.assertEqual('BLOCKED', result['status'])
            self.assertEqual('MATHEMATICS_UNSUPPORTED', result['failure_code'])
            registry = json.loads((Path(result['run_dir']) / 'active_artifacts.json').read_text())
            self.assertNotIn('derivation_spec', registry['artifacts'])

    def test_model_design_flag_cannot_be_enabled_by_truthy_string(self):
        from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'workflow.json'
            path.write_text(json.dumps({'schema': 'forge-problem-understanding/v1', 'problem_id': 'test',
                                        'statement': 'statement.txt', 'model_design': 'false',
                                        'provider': {'provider': 'codex', 'model': 'test-model'}}))
            with self.assertRaisesRegex(ValueError, 'MODEL_DESIGN_MUST_BE_BOOLEAN'):
                ProblemUnderstandingWorkflow(path)


if __name__ == '__main__':
    unittest.main()
