import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from datetime import timedelta
from unittest.mock import patch
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class ReleaseControllerTests(unittest.TestCase):
    def test_rule_profile_uses_shanghai_calendar_date(self):
        from core.runtime.release_controller import release, read, digest, PROFILE_PATH
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate, review, save = self.complete_fixture(root)
            profile = read(PROFILE_PATH)
            profile['verified_on'] = '2026-09-10'
            save(PROFILE_PATH, profile)
            rules = read(root / 'release/reviews/rules.json')
            rules.update(profile_sha256=digest(PROFILE_PATH), reviewed_at='2026-09-09T17:00:00+00:00')
            save(root / 'release/reviews/rules.json', rules)
            with patch('core.runtime.release_controller.datetime') as clock:
                clock.now.return_value = datetime(2026, 9, 9, 17, tzinfo=timezone.utc)
                clock.fromisoformat.side_effect = datetime.fromisoformat
                result = release(root, candidate['candidate_sha256'], mode='automatic')
            self.assertNotIn('RULES_REVIEW_PENDING', result['blockers'])

    def setUp(self):
        from core.runtime.release_controller import PROFILE_PATH, read
        self.profile_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.profile_tmp.cleanup)
        profile = read(PROFILE_PATH)
        profile['verified_on'] = datetime.now(timezone.utc).date().isoformat()
        path = Path(self.profile_tmp.name) / 'profile.json'
        path.write_text(json.dumps(profile), encoding='utf-8')
        self.profile_patch = patch('core.runtime.release_controller.PROFILE_PATH', path)
        self.profile_patch.start()
        self.addCleanup(self.profile_patch.stop)

    def test_stale_rules_and_nested_evidence_race_block(self):
        from core.runtime.release_controller import release, read
        from submission.gates.pdf_page_gate import check_pdf_pages
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate, review, save = self.complete_fixture(root)
            rules = read(root / 'release/reviews/rules.json')
            original = dict(rules)
            rules['reviewed_at'] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
            save(root / 'release/reviews/rules.json', rules)
            self.assertIn('RULES_REVIEW_PENDING', release(root, candidate['candidate_sha256'], mode='automatic')['blockers'])
            save(root / 'release/reviews/rules.json', original)
            def change_after_qualification(*args):
                (root / 'release/reviews/fixture_0_manifest.json').write_text('{}')
                return check_pdf_pages(*args)
            with patch('core.runtime.release_controller.check_pdf_pages', side_effect=change_after_qualification):
                result = release(root, candidate['candidate_sha256'], mode='automatic')
            self.assertIn('REVIEW_CHANGED_DURING_RELEASE', result['blockers'])

    def complete_fixture(self, root):
        # Synthetic approval records test mechanics only, never contest acceptance.
        from core.runtime.release_controller import stage_candidate, digest, V9_GATES, REVIEW_CHECKS
        from core.runtime.contest_readiness import write_handoff
        from core.runtime.release_controller import PROFILE_PATH
        from core.schema.gate_result import gate_result, gate_check
        self.fixture(root)
        def save(path, data):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding='utf-8')
        manifest = {'schema': 'forge-problem-execution/v1', 'run_id': 'fixture-run', 'status': 'READY_FOR_REVIEW', 'execution_mode': 'REAL_PROVIDER'}
        for name in V9_GATES:
            save(root / 'gates' / (name + '.json'), gate_result(V9_GATES[name], [gate_check('synthetic', True)], run_id='fixture-run'))
        writer = PdfWriter()
        for _ in range(3): writer.add_blank_page(width=595, height=842)
        writer.write(root / 'artifacts/submission.pdf')
        manifest['ai_usage_handoff'] = write_handoff(root, manifest)
        save(root / 'manifest.json', manifest)
        candidate = stage_candidate(root)
        key = candidate['candidate_sha256']
        review = {'status': 'APPROVED', 'reviewer': 'SYNTHETIC TEST ONLY', 'run_id': 'fixture-run',
                  'candidate_sha256': key, 'reviewed_at': datetime.now(timezone.utc).isoformat()}
        reviews = root / 'release/reviews'
        save(reviews / 'human.json', dict(review, checks={c: True for c in REVIEW_CHECKS}))
        save(reviews / 'rules.json', dict(review, profile_sha256=digest(PROFILE_PATH),
                                        seven_days_is_local_policy=True, official_sources_checked=True))
        save(reviews / 'pdf_boundaries.json', {'pdf_sha256': digest(root / 'artifacts/submission.pdf'),
             'abstract_end': 1, 'body_end': 3, 'status': 'APPROVED', 'reviewer': 'SYNTHETIC'})
        cases = []
        for n in range(3):
            m = 'release/reviews/fixture_%s_manifest.json' % n
            a = 'release/reviews/fixture_%s_provider.json' % n
            save(root / m, dict(manifest, run_id=str(n)))
            save(root / a, {'model': 'synthetic', 'status': 'COMPLETED'})
            cases.append({'run_id': str(n), 'problem_id': str(n), 'status': 'APPROVED',
                          'reviewer': 'SYNTHETIC', 'official_source_url': 'https://example.invalid/fixture',
                          'manifest_path': m, 'provider_audit_path': a,
                          'evidence': {m: digest(root / m), a: digest(root / a)}})
        save(reviews / 'acceptance.json', {'status': 'APPROVED', 'cases': cases})
        return candidate, review, save

    def test_manual_approval_automatic_mode_and_revoke(self):
        from core.runtime.release_controller import release, execute_request
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate, review, save = self.complete_fixture(root)
            key = candidate['candidate_sha256']
            self.assertIn('PUBLISH_CONFIRMATION_PENDING', release(root, key)['blockers'])
            self.assertEqual('RELEASED', release(root, key, mode='automatic')['status'])
            save(root / 'release/reviews/publish.json', review)
            self.assertEqual('RELEASED', release(root, key)['status'])
            save(root / 'release/revoke.json', {'schema': 'forge-release-request/v1',
                 'run_dir': '..', 'action': 'revoke', 'reason': 'synthetic test'})
            self.assertEqual('REVOKED', execute_request(root / 'release/revoke.json')['status'])
            self.assertTrue(list((root / 'release/versions').glob('*/receipt.json')))

    def test_wrong_run_human_review_and_changed_qualification_block(self):
        from core.runtime.release_controller import release
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate, review, save = self.complete_fixture(root)
            review['run_id'] = 'wrong'
            save(root / 'release/reviews/human.json', review)
            self.assertIn('HUMAN_REVIEW_PENDING', release(root, candidate['candidate_sha256'], mode='automatic')['blockers'])
            (root / 'release/reviews/fixture_0_manifest.json').write_text('{}')
            self.assertIn('REAL_ACCEPTANCE_0_OF_3_OR_INVALID', release(root, candidate['candidate_sha256'], mode='automatic')['blockers'])

    def fixture(self, root):
        (root / 'artifacts').mkdir()
        (root / 'artifacts/paper_candidate.docx').write_bytes(b'candidate fixture')
        (root / 'manifest.json').write_text(json.dumps({'run_id': 'fixture-run',
            'status': 'READY_FOR_REVIEW', 'execution_mode': 'INJECTED_TRANSPORT'}))

    def test_candidate_is_immutable_and_never_approval(self):
        from core.runtime.release_controller import stage_candidate
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root)
            first = stage_candidate(root)
            self.assertEqual('AWAITING_REVIEW', first['status'])
            self.assertEqual('NOT_PERFORMED', first['official_submission'])
            self.assertEqual(first, stage_candidate(root))
            (root / 'artifacts/paper_candidate.docx').write_bytes(b'changed')
            second = stage_candidate(root)
            self.assertNotEqual(first['candidate_sha256'], second['candidate_sha256'])
            self.assertTrue((root / first['candidate_path']).is_file())

    def test_missing_evidence_blocks_manual_and_automatic(self):
        from core.runtime.release_controller import stage_candidate, release
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root)
            candidate = stage_candidate(root)
            for mode in ('manual', 'automatic'):
                result = release(root, candidate['candidate_sha256'], mode=mode)
                self.assertEqual('BLOCKED', result['status'])
                self.assertFalse((root / 'release/current.json').exists())

    def test_changed_input_and_bad_candidate_id_block(self):
        from core.runtime.release_controller import stage_candidate, release
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.fixture(root)
            candidate = stage_candidate(root)
            (root / 'artifacts/paper_candidate.docx').write_bytes(b'changed')
            result = release(root, candidate['candidate_sha256'])
            self.assertIn('CANDIDATE_BYTES_CHANGED', result['blockers'])
            with self.assertRaises(ValueError):
                release(root, '../escape')
