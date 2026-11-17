"""A tool-calling review agent over a completed Forge run.

The loop is: planner picks a tool -> executor validates args and runs it ->
result is fed back -> planner picks the next tool -> stop when the plan is
exhausted or the step budget is hit. A model provider can replace the rule
planner without touching the tools or the report contract.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from agent_layer.tools import RunTools, ToolError

MAX_STEPS = 60

CRITICAL_GATES = (
    "scientific_gate",
    "template_compliance_gate",
    "artifact_integrity_gate",
    "number_freeze_gate",
    "publish_gate",
)


class Planner(Protocol):
    def next(self, last: dict[str, Any] | None) -> dict[str, Any] | None:
        """Return {"tool": name, "args": {...}} or None to finish."""


class RulePlanner:
    """Deterministic plan: manifest -> sections -> per-section checks -> gates."""

    def __init__(self) -> None:
        self.stage = "manifest"
        self.sections: list[dict[str, Any]] = []
        self.index = 0
        self.substage = 0
        self.detail: dict[str, Any] | None = None
        self.gate_index = 0

    def next(self, last: dict[str, Any] | None) -> dict[str, Any] | None:
        if self.stage == "manifest":
            self.stage = "inventory"
            return {"tool": "get_run_manifest", "args": {}}

        if self.stage == "inventory":
            self.stage = "sections"
            return {"tool": "list_sections", "args": {}}

        if self.stage == "sections":
            if last and last.get("tool") == "list_sections":
                self.sections = last.get("result") or []
            if not self.sections:
                self.stage = "gates"
                return self.next(last)
            self.stage = "section"
            self.substage = 0
            return self.next(last)

        if self.stage == "section":
            if self.index >= len(self.sections):
                self.stage = "gates"
                return self.next(last)
            section = self.sections[self.index]
            if self.substage == 0:
                self.substage = 1
                return {"tool": "get_section", "args": {"section_id": section["section_id"]}}
            if self.substage == 1:
                if last and last.get("tool") == "get_section":
                    self.detail = last.get("result")
                text = (self.detail or {}).get("text") or ""
                self.substage = 2
                if text.strip():
                    return {"tool": "verify_numbers", "args": {"text": text}}
                return self.next(last)
            if self.substage == 2:
                title = (self.detail or {}).get("title") or section.get("title") or ""
                self.substage = 3
                return {"tool": "search_knowledge", "args": {"query": f"{title} 论文 写法 结构", "top_k": 3}}
            self.index += 1
            self.substage = 0
            self.detail = None
            return self.next(last)

        if self.stage == "gates":
            if self.gate_index >= len(CRITICAL_GATES):
                return None
            gate = CRITICAL_GATES[self.gate_index]
            self.gate_index += 1
            return {"tool": "list_gate_checks", "args": {"gate": gate}}

        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ReviewAgent:
    def __init__(self, run_dir: Path, index=None, planner: Planner | None = None, max_steps: int = MAX_STEPS) -> None:
        self.tools = RunTools(run_dir, index=index)
        self.planner: Planner = planner or RulePlanner()
        self.max_steps = max_steps
        self.run_dir = Path(run_dir).resolve()
        self.issues: list[dict[str, Any]] = []
        self.trace: list[dict[str, Any]] = []
        self.evidence: dict[str, Any] = {"number_checks": [], "gate_failures": [], "knowledge": []}

    # ---- issue builders -------------------------------------------------
    def _issue(self, severity: str, section: str, kind: str, evidence: Any, suggestion: str, rule: str) -> None:
        self.issues.append(
            {
                "id": f"I-{len(self.issues) + 1:02d}",
                "severity": severity,
                "section": section,
                "type": kind,
                "evidence": evidence,
                "suggestion": suggestion,
                "rule": rule,
            }
        )

    def _on_section(self, result: dict[str, Any]) -> None:
        section_id = result.get("section_id") or ""
        for block in result.get("blocks") or []:
            if block.get("type") == "bound_text" and not block.get("has_binding"):
                self._issue(
                    "high",
                    section_id,
                    "unsupported_claim",
                    {"block_id": block.get("block_id"), "claim": block.get("claim")},
                    "该段落没有模板或数据绑定，属于无源断言；改为 bound_text 并绑定 frozen_numbers 或模型结果。",
                    "bound_text_requires_source",
                )

    def _on_verify(self, result: dict[str, Any], section: str, detail: dict[str, Any] | None) -> None:
        unmatched = result.get("unmatched") or []
        self.evidence["number_checks"].append(
            {"section": section, "extracted": result.get("extracted"), "unmatched": len(unmatched)}
        )
        blocks = (detail or {}).get("blocks") or []
        for item in unmatched:
            raw = str(item.get("raw") or "")
            block_id = next(
                (b.get("block_id") for b in blocks if raw and raw in (b.get("claim") or "")),
                None,
            )
            self._issue(
                "high",
                section,
                "unmatched_number",
                {**item, "block_id": block_id},
                f"数字 {item.get('raw')} 未出现在 frozen_numbers 中；确认来源或将其写回冻结表后重新生成。",
                "number_freeze",
            )

    def _on_gate(self, result: list[dict[str, Any]]) -> None:
        failures = [row for row in result if row.get("status") != "PASS"]
        for row in failures:
            self.evidence["gate_failures"].append(row)
            self._issue(
                "high" if row.get("gate") in CRITICAL_GATES else "medium",
                "",
                "gate_failure",
                {"gate": row.get("gate"), "check": row.get("check"), "message": row.get("message")},
                f"门禁 {row.get('gate')} 的检查项「{row.get('check')}」未通过，先修复再重新运行。",
                "gate",
            )

    def _on_search(self, result: list[dict[str, Any]], section: str) -> None:
        self.evidence["knowledge"].append({"section": section, "hits": [h.get("doc_id") for h in result]})

    # ---- main loop ------------------------------------------------------
    def run(self) -> dict[str, Any]:
        last: dict[str, Any] | None = None
        finished = False
        current_section = ""
        current_detail: dict[str, Any] | None = None
        for step in range(1, self.max_steps + 1):
            action = self.planner.next(last)
            if action is None:
                finished = True
                break
            envelope = self.tools.call(action["tool"], action.get("args") or {})
            self.trace.append(
                {
                    "step": step,
                    "tool": envelope["tool"],
                    "args_hash": envelope["args_hash"],
                    "elapsed_ms": envelope["elapsed_ms"],
                    "ok": envelope["ok"],
                }
            )
            tool = envelope["tool"]
            result = envelope["result"]
            if tool == "get_section":
                current_section = result.get("section_id") or ""
                current_detail = result
                self._on_section(result)
            elif tool == "verify_numbers":
                self._on_verify(result, current_section, current_detail)
            elif tool == "list_gate_checks":
                self._on_gate(result)
            elif tool == "search_knowledge":
                self._on_search(result, current_section)
            last = envelope
        return self._report(finished)

    def _report(self, finished: bool) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        for issue in self.issues:
            by_severity[issue["severity"]] = by_severity.get(issue["severity"], 0) + 1
        manifest = json.loads((self.run_dir / "manifest.json").read_text(encoding="utf-8"))
        payload = {
            "schema": "forge-agent-review/v1",
            "run_id": manifest.get("run_id"),
            "generated_at": _now(),
            "planner": type(self.planner).__name__,
            "finished": finished,
            "summary": {
                "steps": len(self.trace),
                "issues": len(self.issues),
                "high": by_severity.get("high", 0),
                "medium": by_severity.get("medium", 0),
                "sections_checked": sum(1 for e in self.trace if e["tool"] == "get_section"),
            },
            "issues": self.issues,
            "evidence": self.evidence,
            "tool_trace": self.trace,
        }
        payload["trace_sha256"] = hashlib.sha256(
            json.dumps(self.trace, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return payload


def write_report(report: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "review_report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "agent_trace.jsonl").write_text(
        "\n".join(json.dumps(entry, ensure_ascii=False) for entry in report["tool_trace"]) + "\n",
        encoding="utf-8",
    )
    return target
