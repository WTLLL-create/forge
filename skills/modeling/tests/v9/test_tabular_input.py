"""Explicit mapping and arithmetic integration; no live model calls."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.runtime.problem_package import create_package
from core.runtime.artifact_store import ArtifactStore
from core.runtime.data_profile import inspect_package
from core.schema.artifact_meta import ArtifactIntegrityError


class TabularInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / 'run'

    def adapter(self):
        try:
            return importlib.import_module('core.runtime.tabular_input')
        except ImportError as exc:
            self.fail('Explicit worksheet mapping is not implemented: ' + str(exc))

    def selection(self):
        return {'asset_id': 'attachment_1', 'sheet_id': 'S1', 'header_row': 1,
                'first_data_row': 2, 'last_data_row': 3,
                'columns': [{'column': 'A', 'name': 'x', 'expected_header': 'Measurement'},
                            {'column': 'B', 'name': 'a', 'expected_header': 'Baseline'}]}

    def fixture(self, selection=None, rows=((3, 1), (-1, 2)), merge=None):
        from openpyxl import Workbook
        source = self.root / 'data.xlsx'
        book = Workbook()
        sheet = book.active
        sheet.title = 'Measurements'
        sheet.append(['Measurement', 'Baseline'])
        for row in rows:
            sheet.append(row)
        # Keep trailing blanks within a real used range for negative fixtures.
        sheet.cell(3, 3, 'unselected note')
        if merge:
            sheet.merge_cells(merge)
        book.create_sheet('Other')['A1'] = 'Different table'
        book.save(source)
        book.close()
        statement = self.root / 'statement.txt'
        statement.write_text('Q1: Evaluate squared deviations.', encoding='utf-8')
        return create_package(self.run, 'r1', 'synthetic', statement, [source],
                              configuration={'data_selection': selection if selection is not None else self.selection()})

    def build(self, package):
        return self.adapter().build_tabular_input(package, self.run, 'r1')

    def test_selected_values_and_lineage_are_registered(self):
        p = self.fixture()
        artifact = self.build(p)
        c = artifact['content']
        self.assertEqual(['x', 'a'], c['headers'])
        self.assertEqual([['3', '1'], ['-1', '2']], c['rows'])
        self.assertEqual([2, 3], c['source_rows'])
        self.assertEqual({'x': 'A', 'a': 'B'}, c['source_columns'])
        self.assertEqual('S1', c['sheet_id'])
        self.assertEqual('Measurements', c['sheet_name'])
        self.assertEqual('reject', c['selection']['missing_policy'])
        self.assertEqual(p['content']['assets'][1]['sha256'], c['source_sha256'])
        self.assertEqual(['problem_package@1'], artifact['meta']['input_refs'])

    def test_blank_rejected_by_default_but_zero_preserved(self):
        p = self.fixture(rows=((0, 1), (None, 2)))
        with self.assertRaisesRegex(ValueError, 'TABULAR_MISSING_VALUE'):
            self.build(p)
        registry = json.loads((self.run / 'active_artifacts.json').read_text())
        self.assertNotIn('tabular_input', registry['artifacts'])

    def test_explicit_drop_preserves_zero_and_records_source_row(self):
        s = self.selection()
        s['missing_policy'] = 'drop_row'
        p = self.fixture(s, rows=((0, 1), (None, 2)))
        c = self.build(p)['content']
        self.assertEqual([['0', '1']], c['rows'])
        self.assertEqual([2], c['source_rows'])
        self.assertEqual([{'row': 3, 'missing_cells': ['A3']}], c['dropped_rows'])
        self.assertEqual(2, c['input_row_count'])

    def test_wrong_sheet_column_header_and_range_fail(self):
        self.adapter()
        for key, value, code in [('sheet_id', 'S99', 'TABULAR_SHEET_UNKNOWN'),
                                 ('header_row', 2, 'TABULAR_ROW_RANGE_INVALID'),
                                 ('last_data_row', 99, 'TABULAR_ROW_RANGE_INVALID')]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as raw:
                prior_root, prior_run = self.root, self.run
                self.root, self.run = Path(raw), Path(raw) / 'run'
                try:
                    s = self.selection(); s[key] = value
                    p = self.fixture(s)
                    with self.assertRaisesRegex(ValueError, code): self.build(p)
                finally:
                    self.root, self.run = prior_root, prior_run

    def test_unknown_column_and_wrong_header_fail(self):
        s = self.selection()
        s['columns'][0]['column'] = 'Z'
        p = self.fixture(s)
        with self.assertRaisesRegex(ValueError, 'TABULAR_COLUMN_UNKNOWN'):
            self.build(p)

    def test_header_mismatch_blocks_wrong_column_semantics(self):
        s = self.selection(); s['columns'][0]['expected_header'] = 'Other header'
        p = self.fixture(s)
        with self.assertRaisesRegex(ValueError, 'TABULAR_HEADER_MISMATCH'):
            self.build(p)

    def test_formula_text_and_boolean_are_not_coerced_even_when_dropping(self):
        self.adapter()
        for value in ('=1+2', '3', True, '#DIV/0!'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as raw:
                prior_root, prior_run = self.root, self.run
                self.root, self.run = Path(raw), Path(raw) / 'run'
                try:
                    s = self.selection(); s['missing_policy'] = 'drop_row'
                    p = self.fixture(s, rows=((value, None), (3, 1)))
                    with self.assertRaisesRegex(ValueError, 'TABULAR_NONNUMERIC_CELL'): self.build(p)
                finally:
                    self.root, self.run = prior_root, prior_run

    def test_merged_selected_cells_blocked(self):
        p = self.fixture(merge='A2:B2')
        with self.assertRaisesRegex(ValueError, 'TABULAR_MERGED_CELL'):
            self.build(p)

    def test_all_rows_dropped_blocked(self):
        s = self.selection(); s['missing_policy'] = 'drop_row'
        p = self.fixture(s, rows=((None, 1), (None, 2)))
        with self.assertRaisesRegex(ValueError, 'TABULAR_EMPTY_RESULT'):
            self.build(p)

    def test_tampered_workbook_rejected(self):
        p = self.fixture()
        (self.run / 'inputs/attachment_1.xlsx').write_bytes(b'tampered')
        with self.assertRaises(ArtifactIntegrityError): self.build(p)

    def test_invalid_config_rejects_fill_and_duplicate_columns(self):
        adapter = self.adapter()
        for change in ('fill', 'duplicate', 'extra', 'bool_row'):
            s = self.selection()
            if change == 'fill': s['missing_policy'] = 'fill_zero'
            if change == 'duplicate': s['columns'][1]['column'] = 'A'
            if change == 'extra': s['code'] = 'anything'
            if change == 'bool_row': s['header_row'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                adapter.validate_selection(s)

    def test_same_data_csv_and_xlsx_have_same_formula_values(self):
        from core.schema.solver_plan import validate_and_execute
        p = self.fixture()
        c = self.build(p)['content']
        plan, derivation = self.contracts()
        csv_report, csv = validate_and_execute(plan, derivation, ['x', 'a'], [['3', '1'], ['-1', '2']], 'r1')
        report, result = validate_and_execute(plan, derivation, c['headers'], c['rows'], 'r1')
        self.assertEqual('PASS', report['status'])
        self.assertEqual('PASS', csv_report['status'])
        self.assertEqual(['4', '9'], result['formulas'][0]['values'])
        self.assertEqual(csv['formulas'], result['formulas'])

    def contracts(self):
        plan = {'problem_id': 'synthetic', 'mode': 'formula_verification', 'asset_id': 'attachment_1',
                'mappings': [{'formula_id': 'F1', 'target': 'objective', 'output': 'loss',
                              'expression': '(x-a)**2', 'bindings': [
                                  {'symbol': 'x', 'column': 'x', 'unit': 'm'},
                                  {'symbol': 'a', 'column': 'a', 'unit': 'm'}]}]}
        derivation = {'problem_id': 'synthetic', 'symbols': [{'name': 'x', 'unit': 'm'}, {'name': 'a', 'unit': 'm'}],
                      'formulas': [{'id': 'F1', 'expression': '(x-a)**2', 'solver_mapping':
                                    {'target': 'objective', 'output': 'loss', 'inputs': ['x', 'a']}}]}
        return plan, derivation

    def test_runtime_registers_xlsx_execution_with_original_row_provenance(self):
        from core.runtime.formula_execution import build_formula_execution
        p = self.fixture()
        profile = inspect_package(p, self.run, 'r1')
        store = ArtifactStore(self.run, 'r1')
        plan, derivation = self.contracts()
        derived = store.register_json(artifact_type='derivation_spec', version=1,
                                      content=derivation, producer='synthetic-fixture')
        for name in ('logs', 'gates'): (self.run / name).mkdir()
        class Provider:
            def generate_structured(inner, **kwargs):
                return copy.deepcopy(plan), {'provider': 'synthetic', 'status': 'completed'}
        result = build_formula_execution(self.run, 'r1', p, profile, derived, Provider())
        self.assertEqual('READY_FOR_REVIEW', result['status'], result)
        registry = store.registry._load()
        evidence = store.registry._stored_envelope(registry['artifacts']['formula_execution']['path'])
        self.assertEqual([2, 3], evidence['content']['source_rows'])
        self.assertIn('tabular_input@1', evidence['meta']['input_refs'])
        self.assertEqual('NOT_SOLVED', evidence['content']['solution_status'])
        self.assertEqual(['4', '9'], evidence['content']['formulas'][0]['values'])
        self.assertNotIn('model_result', registry['artifacts'])

    def test_workflow_config_requires_formula_execution(self):
        from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
        config = {'schema': 'forge-problem-understanding/v1', 'problem_id': 'p',
                  'statement': 'statement.txt', 'provider': {'provider': 'codex', 'model': 'test'},
                  'data_selection': self.selection()}
        path = self.root / 'workflow.json'
        path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'DATA_SELECTION_REQUIRES_FORMULA_VERIFICATION'):
            ProblemUnderstandingWorkflow(path)

    def test_runtime_cannot_switch_asset_or_consume_tampered_table(self):
        from core.runtime.formula_execution import build_formula_execution
        for mutation in ('switch_asset', 'tamper_table'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as raw:
                prior_root, prior_run = self.root, self.run
                self.root, self.run = Path(raw), Path(raw) / 'run'
                try:
                    p = self.fixture()
                    profile = inspect_package(p, self.run, 'r1')
                    store = ArtifactStore(self.run, 'r1')
                    plan, derivation = self.contracts()
                    derived = store.register_json(artifact_type='derivation_spec', version=1,
                                                  content=derivation, producer='synthetic-fixture')
                    for name in ('logs', 'gates'): (self.run / name).mkdir()
                    class Provider:
                        def generate_structured(inner, **kwargs):
                            if mutation == 'switch_asset':
                                plan['asset_id'] = 'attachment_99'
                            else:
                                registry = store.registry._load()
                                path = self.run / registry['artifacts']['tabular_input']['path']
                                data = json.loads(path.read_text())
                                data['content']['rows'][0][0] = '999'
                                path.write_text(json.dumps(data))
                            return plan, {'provider': 'synthetic', 'status': 'completed'}
                    result = build_formula_execution(self.run, 'r1', p, profile, derived, Provider())
                    self.assertEqual('BLOCKED', result['status'], result)
                    registry = store.registry._load()
                    self.assertNotIn('formula_execution', registry['artifacts'])
                    self.assertNotIn('solver_plan', registry['artifacts'])
                finally:
                    self.root, self.run = prior_root, prior_run

    def test_workflow_blocks_missing_data_before_any_model_call(self):
        from core.runtime.problem_understanding import ProblemUnderstandingWorkflow
        self.fixture(rows=((0, 1), (None, 2)))
        config = {'schema': 'forge-problem-understanding/v1', 'problem_id': 'p',
                  'statement': 'statement.txt', 'attachments': ['data.xlsx'],
                  'provider': {'provider': 'codex', 'model': 'test'},
                  'model_design': True, 'formula_verification': True,
                  'data_selection': self.selection()}
        path = self.root / 'workflow.json'
        path.write_text(json.dumps(config))
        try:
            workflow = ProblemUnderstandingWorkflow(path)
        except ValueError as exc:
            self.fail('Mapping configuration rejected before input validation: ' + str(exc))
        def forbidden(*args, **kwargs): self.fail('Bad data reached model transport')
        result = workflow.run(transport=forbidden)
        self.assertEqual('BLOCKED', result['status'])
        self.assertEqual('TABULAR_MISSING_VALUE', result['failure_code'])
        saved = json.loads((Path(result['run_dir']) / 'inputs/workflow_config.json').read_text())
        self.assertEqual('reject', saved['data_selection']['missing_policy'])


if __name__ == '__main__': unittest.main()
