"""Multi-agent revision pipeline: Reviewer -> Writer -> Verifier.

The pipeline never writes back to the paper. It produces a revision plan with
patches and a verification verdict, so a human (or a later stage) decides
whether to apply anything.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_layer.reviewer import ReviewAgent, write_report
from agent_layer.tools import RunTools

PLACEHOLDER = "（数值待核实）"
UNSUPPORTED_MARK = "（该结论尚缺数据支撑，待补。）"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class WriterAgent:
    """Turn review issues into minimal, in-place patches."""

    def __init__(self, tools: RunTools) -> None:
        self.tools = tools
        self._section_cache: dict[str, dict[str, Any]] = {}

    def _section(self, section_id: str) -> dict[str, Any]:
        if section_id not in self._section_cache:
            self._section_cache[section_id] = self.tools.call(
                "get_section", {"section_id": section_id}
            )["result"]
        return self._section_cache[section_id]

    def plan(self, report: dict[str, Any]) -> list[dict[str, Any]]:
        bad_numbers = [
            str(issue["evidence"].get("raw") or "")
            for issue in report.get("issues") or []
            if issue.get("type") == "unmatched_number" and issue.get("evidence")
        ]
        patches: list[dict[str, Any]] = []
        for issue in report.get("issues") or []:
            patch = self._patch_for(issue, bad_numbers)
            if patch:
                patch["patch_id"] = f"P-{len(patches) + 1:02d}"
                patch["source_issue"] = issue.get("id")
                patches.append(patch)
        return patches

    def _patch_for(self, issue: dict[str, Any], bad_numbers: list[str]) -> dict[str, Any] | None:
        kind = issue.get("type")
        section_id = issue.get("section") or ""
        evidence = issue.get("evidence") or {}

        if kind == "unmatched_number":
            raw = str(evidence.get("raw") or "")
            if not raw or not section_id:
                return None
            section = self._section(section_id)
            for block in section.get("blocks") or []:
                claim = block.get("claim") or ""
                if raw in claim:
                    return {
                        "section": section_id,
                        "block_id": block.get("block_id"),
                        "old_claim": claim,
                        "new_claim": claim.replace(raw, PLACEHOLDER),
                        "reason": f"数字 {raw} 不在 frozen_numbers 中，替换为待核实占位。",
                        "action": "replace_number",
                    }
            return None

        if kind == "unsupported_claim":
            block_id = evidence.get("block_id")
            claim = evidence.get("claim") or ""
            if not block_id or not claim:
                return None
            cleaned = claim
            for raw in bad_numbers:
                if raw:
                    cleaned = cleaned.replace(raw, PLACEHOLDER)
            return {
                "section": section_id,
                "block_id": block_id,
                "old_claim": claim,
                "new_claim": cleaned.rstrip("。") + UNSUPPORTED_MARK,
                "reason": "该段落没有数据绑定，补充待补标注，避免无源结论。",
                "action": "mark_unsupported",
            }

        return None

    def revise(self, patches: list[dict[str, Any]], verification: dict[str, Any]) -> list[dict[str, Any]]:
        """Rewrite patches the verifier rejected, without touching the paper.

        The repair is deliberately narrow: a rejected claim has its unfrozen
        numbers swapped for the placeholder. A patch that cannot be repaired
        without inventing data is dropped, and dropping it is a legitimate
        outcome, not a failure to hide.
        """
        failed = {
            row.get("patch_id")
            for row in verification.get("results") or []
            if row.get("status") == "FAIL"
        }
        revised: list[dict[str, Any]] = []
        for patch in patches:
            if patch.get("patch_id") not in failed:
                revised.append(patch)
                continue
            claim = patch.get("new_claim") or ""
            numbers = self.tools.call("verify_numbers", {"text": claim})["result"]
            fixed = claim
            for item in numbers.get("unmatched") or []:
                raw = str(item.get("raw") or "")
                if raw:
                    fixed = fixed.replace(raw, PLACEHOLDER)
            if not fixed.strip() or fixed == claim:
                continue
            patched = dict(patch)
            patched["new_claim"] = fixed
            patched["reason"] = (patch.get("reason") or "") + " 回退环：替换未登记数字后重试。"
            patched["revised"] = True
            revised.append(patched)
        return revised


class VerifierAgent:
    """Check every patch: no new unfrozen numbers, no out-of-scope edits."""

    def __init__(self, tools: RunTools) -> None:
        self.tools = tools

    def verify(self, patches: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            (issue.get("section"), (issue.get("evidence") or {}).get("block_id"))
            for issue in report.get("issues") or []
        }
        results = []
        for patch in patches:
            section = patch["section"]
            block_id = patch["block_id"]
            checks = []

            in_scope = (section, block_id) in allowed or any(
                issue.get("section") == section and (issue.get("evidence") or {}).get("block_id") == block_id
                for issue in report.get("issues") or []
            )
            checks.append({"name": "patch targets an reported issue", "status": "PASS" if in_scope else "FAIL"})

            changed = patch.get("new_claim") != patch.get("old_claim")
            checks.append({"name": "patch changes the claim", "status": "PASS" if changed else "FAIL"})

            numbers = self.tools.call("verify_numbers", {"text": patch.get("new_claim") or ""})["result"]
            checks.append(
                {
                    "name": "no unfrozen number in new claim",
                    "status": "PASS" if not numbers["unmatched"] else "FAIL",
                    "detail": numbers["unmatched"],
                }
            )

            status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
            results.append({"patch_id": patch["patch_id"], "status": status, "checks": checks})

        verdict = "PASS" if results and all(r["status"] == "PASS" for r in results) else ("EMPTY" if not results else "FAIL")
        return {
            "verdict": verdict,
            "patches_checked": len(results),
            "results": results,
        }


class RevisionPipeline:
    def __init__(self, run_dir: Path, index=None, max_rounds: int = 2) -> None:
        self.run_dir = Path(run_dir).resolve()
        self.index = index
        self.tools = RunTools(self.run_dir, index=index)
        self.max_rounds = max(1, int(max_rounds))

    def _verify_with_retry(
        self,
        review: dict[str, Any],
        patches: list[dict[str, Any]],
        writer: WriterAgent,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
        """Verify, then hand failed patches back to the writer, bounded by max_rounds."""
        attempts: list[dict[str, Any]] = []
        verification: dict[str, Any] = {"verdict": "EMPTY", "patches_checked": 0, "results": []}
        for round_no in range(1, self.max_rounds + 1):
            verification = VerifierAgent(self.tools).verify(patches, review)
            failed = [row["patch_id"] for row in verification["results"] if row["status"] == "FAIL"]
            attempts.append(
                {
                    "round": round_no,
                    "verdict": verification["verdict"],
                    "patches": len(patches),
                    "failed_patches": failed,
                }
            )
            if verification["verdict"] in ("PASS", "EMPTY"):
                break
            patches = writer.revise(patches, verification)
        return patches, verification, attempts

    def run(self) -> dict[str, Any]:
        review = ReviewAgent(self.run_dir, index=self.index).run()
        writer = WriterAgent(self.tools)
        patches = writer.plan(review)
        patches, verification, attempts = self._verify_with_retry(review, patches, writer)
        payload = {
            "schema": "forge-revision-plan/v1",
            "run_id": review.get("run_id"),
            "generated_at": _now(),
            "review_ref": review.get("trace_sha256"),
            "issues": len(review.get("issues") or []),
            "patches": patches,
            "verification": verification,
            "rounds": len(attempts),
            "attempts": attempts,
            "applied": False,
            "note": "plan only; nothing is written back to the paper",
        }
        payload["plan_sha256"] = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return {"review": review, "plan": payload}


def write_plan(plan: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "revision_plan.json"
    target.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
