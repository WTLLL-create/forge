"""General result compatibility; fixture values are not solver execution evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.schema.model_result import validate_model_result, load_model_result, write_model_result


def general_result():
    return {'schema': 'forge-model-result/v2', 'run_id': 'r1', 'problem_id': 'fixture',
            'model_version': 'fixture-only/v1', 'parameters': {'coefficient': 2},
            'metrics': {'error': 0.25}, 'diagnostics': {'predictions': [2, 4]},
            'tables': [{'id': 'T1', 'source_path': '$.diagnostics.predictions', 'rows': [2, 4]}],
            'figures': [], 'rankings': [], 'claims': [{'id': 'C1', 'source_path': '$.metrics.error'}]}


class GeneralModelResultTests(unittest.TestCase):
    def test_general_result_without_entropy_or_rankings_validates(self):
        try:
            validate_model_result(general_result(), 'r1')
        except ValueError as exc:
            self.fail('General result without unrelated rankings rejected: ' + str(exc))

    def test_new_result_round_trip_requires_explicit_consumer_version(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'result.json'
            try:
                write_model_result(path, general_result())
            except ValueError as exc:
                self.fail('General result cannot be written: ' + str(exc))
            with self.assertRaises(ValueError):
                load_model_result(path, 'r1')
            self.assertEqual(general_result(), load_model_result(path, 'r1', expected_schema='forge-model-result/v2'))

    def test_general_result_cannot_be_relabelled_as_legacy(self):
        value = general_result()
        value['schema'] = 'forge-model-result/v1'
        with self.assertRaises(ValueError):
            validate_model_result(value)

    def test_direct_legacy_paper_builder_rejects_general_result(self):
        from submission.schema.build_paper_spec import build_paper_spec
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'result.json'
            path.write_text(json.dumps(general_result()), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'CONSUMER_VERSION_MISMATCH'):
                build_paper_spec(general_result(), path)

    def test_full_tree_rejects_nonfinite_numbers(self):
        for field in ('parameters', 'metrics', 'diagnostics', 'tables', 'figures', 'claims'):
            value = general_result()
            if isinstance(value[field], dict):
                value[field]['bad'] = float('nan')
            else:
                value[field].append({'bad': float('inf')})
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_model_result(value)

    def test_table_values_must_equal_bound_source(self):
        value = general_result()
        value['tables'][0]['rows'] = [20, 40]
        with self.assertRaises(ValueError):
            validate_model_result(value)

    def test_general_rankings_need_no_model_specific_grade(self):
        value = general_result()
        value['rankings'] = [{'sample': 'A', 'score': 0.8, 'rank': 1}]
        value['tables'] = [{'id': 'R', 'source_path': '$.rankings', 'rows': list(value['rankings'])}]
        try:
            validate_model_result(value)
        except ValueError as exc:
            self.fail('Generic ranking still requires model-specific grading: ' + str(exc))

    def test_malformed_identifiers_are_validation_errors(self):
        value = general_result()
        value['tables'][0]['id'] = ['not-an-id']
        with self.assertRaises(ValueError):
            validate_model_result(value)

    def test_claims_cannot_reference_themselves_or_identity(self):
        for source in ('$.claims[0].id', '$.run_id', '$.missing'):
            value = general_result()
            value['claims'][0]['source_path'] = source
            with self.subTest(source=source), self.assertRaises(ValueError):
                validate_model_result(value)

    def test_empty_result_unknown_version_and_wrong_run_are_rejected(self):
        for mutation in ('empty', 'version', 'run'):
            value = general_result()
            if mutation == 'empty':
                value.update(metrics={}, diagnostics={}, tables=[], claims=[])
            if mutation == 'version': value['schema'] = 'forge-model-result/v999'
            if mutation == 'run': value['run_id'] = 'old'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_model_result(value, 'r1')

    def test_unknown_python_values_cannot_be_validated_as_json(self):
        value = general_result()
        value['diagnostics']['bad'] = {1, 2}
        with self.assertRaises(ValueError):
            validate_model_result(value)

    def test_invalid_write_does_not_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'result.json'
            path.write_text('existing', encoding='utf-8')
            value = general_result()
            value['tables'][0]['rows'] = [999]
            with self.assertRaises(ValueError):
                write_model_result(path, value)
            self.assertEqual('existing', path.read_text())
