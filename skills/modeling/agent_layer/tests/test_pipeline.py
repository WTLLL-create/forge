"""Tests for the Reviewer -> Writer -> Verifier pipeline."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_layer.fault_injector import inject_defects
from agent_layer.pipeline import RevisionPipeline, VerifierAgent, WriterAgent, write_plan
from agent_layer.retrieval import build_index
from agent_layer.reviewer import ReviewAgent
from agent_layer.tools import RunTools

WORKSPACE = Path(__file__).resolve().parents[4]
MODELING = WORKSPACE / "skills" / "modeling"
RUNS_ROOT = WORKSPACE / "projects" / "forge_v7_3_d2026" / "runtime" / "runs"


def latest_run() -> Path:
    candidates = [
        path for path in RUNS_ROOT.iterdir()
        if path.is_dir() and (path / "manifest.json").is_file()
    ]
    if not candidates:
        raise unittest.SkipTest("no run directories available")
    return max(candidates, key=lambda path: (path / "manifest.json").stat().st_mtime)


class RevisionPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = latest_run()
        cls.index = build_index(MODELING)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.broken = inject_defects(cls.run_dir, Path(cls.tmp.name) / "broken_run")
        cls.result = RevisionPipeline(cls.broken, index=cls.index).run()
        cls.clean = RevisionPipeline(cls.run_dir, index=cls.index).run()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_patches_are_generated(self) -> None:
        plan = self.result["plan"]
        self.assertGreaterEqual(len(plan["patches"]), 2)
        self.assertFalse(plan["applied"])

    def test_patches_cover_both_issue_types(self) -> None:
        actions = {patch["action"] for patch in self.result["plan"]["patches"]}
        self.assertIn("replace_number", actions)
        self.assertIn("mark_unsupported", actions)

    def test_verifier_passes(self) -> None:
        verification = self.result["plan"]["verification"]
        self.assertEqual(verification["verdict"], "PASS")
        for row in verification["results"]:
            self.assertEqual(row["status"], "PASS")

    def test_clean_run_has_no_patches(self) -> None:
        plan = self.clean["plan"]
        self.assertEqual(plan["issues"], 0)
        self.assertEqual(plan["patches"], [])
        self.assertEqual(plan["verification"]["verdict"], "EMPTY")

    def test_verifier_rejects_out_of_scope_patch(self) -> None:
        tools = RunTools(self.broken, index=self.index)
        report = ReviewAgent(self.broken, index=self.index).run()
        fake = [
            {
                "patch_id": "P-FAKE",
                "section": "abstract",
                "block_id": "not-an-issue-block",
                "old_claim": "原文",
                "new_claim": "改写",
                "action": "mark_unsupported",
            }
        ]
        verification = VerifierAgent(tools).verify(fake, report)
        self.assertEqual(verification["verdict"], "FAIL")
        self.assertEqual(verification["results"][0]["checks"][0]["status"], "FAIL")

    def test_plan_is_serializable(self) -> None:
        out = Path(__file__).resolve().parent / "_plan_out"
        target = write_plan(self.result["plan"], out)
        self.assertTrue(target.is_file())

    def test_attempts_recorded(self) -> None:
        plan = self.result["plan"]
        self.assertEqual(plan["rounds"], 1)
        self.assertEqual(len(plan["attempts"]), 1)
        self.assertEqual(plan["attempts"][0]["verdict"], "PASS")
        self.assertEqual(plan["attempts"][0]["failed_patches"], [])

    def test_retry_loop_replaces_unfrozen_number(self) -> None:
        tools = RunTools(self.broken, index=self.index)
        writer = WriterAgent(tools)
        patch = {
            "patch_id": "P-BAD",
            "section": "abstract",
            "block_id": "bad-block",
            "old_claim": "原文",
            "new_claim": "新结论：样本纯度达到 9.8765%，显著提升。",
            "action": "mark_unsupported",
        }
        verification = {
            "verdict": "FAIL",
            "results": [{"patch_id": "P-BAD", "status": "FAIL", "checks": []}],
        }
        revised = writer.revise([patch], verification)
        self.assertEqual(len(revised), 1)
        self.assertIn("（数值待核实）", revised[0]["new_claim"])
        self.assertNotIn("9.8765", revised[0]["new_claim"])
        self.assertTrue(revised[0]["revised"])

    def test_unrepairable_patch_is_dropped(self) -> None:
        tools = RunTools(self.broken, index=self.index)
        writer = WriterAgent(tools)
        patch = {
            "patch_id": "P-BAD",
            "section": "abstract",
            "block_id": "bad-block",
            "old_claim": "原文",
            "new_claim": "原文",
            "action": "mark_unsupported",
        }
        verification = {
            "verdict": "FAIL",
            "results": [{"patch_id": "P-BAD", "status": "FAIL", "checks": []}],
        }
        self.assertEqual(writer.revise([patch], verification), [])


if __name__ == "__main__":
    unittest.main()
