"""Tests for the fault-injection matrix: per-kind recall and clean-run false positives."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_layer.fault_injector import evaluate
from agent_layer.retrieval import build_index

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


class FaultMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = latest_run()
        cls.index = build_index(MODELING)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.metrics = evaluate(cls.run_dir, Path(cls.tmp.name) / "matrix", index=cls.index)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_every_injected_kind_is_detected(self) -> None:
        for case in self.metrics["cases"]:
            self.assertTrue(case["detected"], case)

    def test_clean_run_has_no_false_positive(self) -> None:
        self.assertEqual(self.metrics["clean_issues"], 0)
        self.assertFalse(self.metrics["false_positive"])

    def test_recall_is_full(self) -> None:
        self.assertEqual(self.metrics["recall"], 1.0)

    def test_number_only_case_stays_number_only(self) -> None:
        case = next(c for c in self.metrics["cases"] if c["kind"] == "unregistered_number")
        self.assertIn("unmatched_number", case["found"])
        self.assertNotIn("unsupported_claim", case["found"])


if __name__ == "__main__":
    unittest.main()
