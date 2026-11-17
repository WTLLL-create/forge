"""Tests for the agent layer: tools, retrieval, and the review loop."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent_layer.retrieval import BM25Index, Document, build_index, tokenize
from agent_layer.reviewer import ReviewAgent, RulePlanner, write_report
from agent_layer.tools import RunTools, ToolError

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


class ToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = latest_run()
        cls.tools = RunTools(cls.run_dir)

    def test_schemas_are_wellformed(self) -> None:
        schemas = self.tools.schemas()
        self.assertGreaterEqual(len(schemas), 7)
        for item in schemas:
            self.assertEqual(item["parameters"].get("type"), "object")
            self.assertTrue(item["description"])

    def test_unknown_tool_rejected(self) -> None:
        with self.assertRaises(ToolError):
            self.tools.call("delete_everything", {})

    def test_missing_argument_rejected(self) -> None:
        with self.assertRaises(ToolError):
            self.tools.call("get_section", {})

    def test_unknown_argument_rejected(self) -> None:
        with self.assertRaises(ToolError):
            self.tools.call("get_run_manifest", {"extra": 1})

    def test_manifest_shape(self) -> None:
        result = self.tools.call("get_run_manifest", {})["result"]
        self.assertIn("status", result)
        self.assertGreaterEqual(result["stages_total"], 1)

    def test_section_list_and_read(self) -> None:
        sections = self.tools.call("list_sections", {})["result"]
        self.assertGreaterEqual(len(sections), 2)
        first = sections[0]["section_id"]
        detail = self.tools.call("get_section", {"section_id": first})["result"]
        self.assertEqual(detail["section_id"], first)
        self.assertIn("blocks", detail)

    def test_verify_numbers_matches_frozen_value(self) -> None:
        numbers = self.tools.call("get_frozen_numbers", {})["result"]["numbers"]
        sample = next(v for v in numbers.values() if isinstance(v, (int, float)) and 0 < abs(v) < 1e5)
        text = f"实验得到结果为 {sample}，采样于 2026 年。"
        result = self.tools.call("verify_numbers", {"text": text})["result"]
        self.assertTrue(result["matched"])
        self.assertEqual(result["unmatched"], [])

    def test_verify_numbers_flags_unknown(self) -> None:
        result = self.tools.call("verify_numbers", {"text": "未登记的数字 3.1415926 出现在正文。"})["result"]
        self.assertTrue(result["unmatched"])

    def test_gate_checks(self) -> None:
        rows = self.tools.call("list_gate_checks", {"gate": "publish_gate"})["result"]
        self.assertTrue(rows)
        self.assertTrue(all(row["gate"] == "publish_gate" for row in rows))


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_index(MODELING)

    def test_tokenize_keeps_chinese_bigrams(self) -> None:
        tokens = tokenize("论文结构")
        self.assertIn("论文", tokens)
        self.assertIn("文结", tokens)

    def test_search_returns_ranked_hits(self) -> None:
        hits = self.index.search("论文开头 矛盾 研究问题", top_k=3)
        self.assertTrue(hits)
        self.assertGreaterEqual(hits[0].score, hits[-1].score)

    def test_empty_query_returns_nothing(self) -> None:
        self.assertEqual(self.index.search("   ", top_k=3), [])

    def test_small_index_scores(self) -> None:
        index = BM25Index([
            Document("a", "矛盾分析", "a.md", "论文开头要写核心矛盾，研究问题来自矛盾。"),
            Document("b", "图表规范", "b.md", "图表标题应当给出结论。"),
        ])
        hits = index.search("核心矛盾", top_k=2)
        self.assertEqual(hits[0].doc_id, "a")


class AgentLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_dir = latest_run()
        cls.index = build_index(MODELING)
        cls.agent = ReviewAgent(cls.run_dir, index=cls.index)
        cls.report = cls.agent.run()

    def test_report_contract(self) -> None:
        required = {"schema", "run_id", "summary", "issues", "evidence", "tool_trace", "trace_sha256"}
        self.assertTrue(required.issubset(self.report.keys()))
        self.assertEqual(self.report["schema"], "forge-agent-review/v1")

    def test_loop_finished_within_budget(self) -> None:
        self.assertTrue(self.report["finished"])
        self.assertLessEqual(self.report["summary"]["steps"], 60)

    def test_tools_were_called_in_order(self) -> None:
        tools = [entry["tool"] for entry in self.report["tool_trace"]]
        self.assertEqual(tools[0], "get_run_manifest")
        self.assertIn("list_sections", tools)
        self.assertIn("verify_numbers", tools)
        self.assertIn("search_knowledge", tools)
        self.assertEqual(tools[-1], "list_gate_checks")

    def test_issues_carry_evidence(self) -> None:
        for issue in self.report["issues"]:
            self.assertIn("severity", issue)
            self.assertIn("evidence", issue)
            self.assertIn("suggestion", issue)
            self.assertNotIn("可能", json.dumps(issue["evidence"], ensure_ascii=False))

    def test_step_budget_stops_loop(self) -> None:
        agent = ReviewAgent(self.run_dir, index=self.index, max_steps=3)
        report = agent.run()
        self.assertFalse(report["finished"])
        self.assertEqual(report["summary"]["steps"], 3)

    def test_write_report(self) -> None:
        out = Path(__file__).resolve().parent / "_out"
        target = write_report(self.report, out)
        self.assertTrue(target.is_file())
        payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(payload["run_id"], self.report["run_id"])
        trace = out / "agent_trace.jsonl"
        self.assertTrue(trace.is_file())


if __name__ == "__main__":
    unittest.main()
