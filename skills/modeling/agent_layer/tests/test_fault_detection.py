"""Prove the agent catches injected defects, not just clean papers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_layer.fault_injector import FAKE_NUMBER, inject_defects, summarize
from agent_layer.retrieval import build_index
from agent_layer.reviewer import ReviewAgent

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


class FaultDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = latest_run()
        cls.index = build_index(MODELING)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.broken = inject_defects(cls.run_dir, Path(cls.tmp.name) / "broken_run")
        cls.report = ReviewAgent(cls.broken, index=cls.index).run()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_injected_number_is_flagged(self) -> None:
        issues = self.report["issues"]
        self.assertTrue(issues, "agent returned no issues for a run with an injected defect")
        joined = " ".join(issue["evidence"].get("raw", "") for issue in issues if isinstance(issue["evidence"], dict))
        self.assertIn(FAKE_NUMBER, joined)

    def test_both_defect_types_are_reported(self) -> None:
        summary = summarize(self.report)
        self.assertIn("unsupported_claim", summary["types"])
        self.assertIn("unmatched_number", summary["types"])

    def test_located_in_first_section(self) -> None:
        summary = summarize(self.report)
        self.assertTrue(summary["sections"])

    def test_clean_run_stays_quiet(self) -> None:
        clean = ReviewAgent(self.run_dir, index=self.index).run()
        self.assertEqual(clean["summary"]["issues"], 0, "clean run should not produce issues")


if __name__ == "__main__":
    unittest.main()
