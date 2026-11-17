"""Build deliberately broken copies of a run to prove the review agent detects defects.

The real workflow has a precedent for this: audit/table_acceptance keeps
``faulty_generator`` and ``valid`` runs side by side. This module follows that
same idea at the paper level, and extends it from one hand-made case to a small
matrix with per-kind recall and a clean-run false-positive check.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

FAKE_NUMBER = "3.1415926"
FAKE_CLAIM = f"本研究进一步发现，样本纯度达到 {FAKE_NUMBER}%，显著优于同类研究。"

KINDS = ("unsupported_claim", "unregistered_number", "both")

EXPECTED_TYPES = {
    "unsupported_claim": {"unsupported_claim"},
    "unregistered_number": {"unmatched_number"},
    "both": {"unsupported_claim", "unmatched_number"},
}


def _copy_run(source_run: Path, target_dir: Path) -> Path:
    source_run = Path(source_run).resolve()
    target_dir = Path(target_dir).resolve()
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_run, target_dir)
    return target_dir


def _spec(target_dir: Path) -> tuple[Path, dict[str, Any]]:
    spec_path = target_dir / "artifacts" / "paper_spec.json"
    return spec_path, json.loads(spec_path.read_text(encoding="utf-8"))


def _append_unsupported_block(spec: dict[str, Any], claim: str) -> None:
    sections = spec.get("sections") or []
    if not sections:
        raise ValueError("paper_spec has no sections to inject into")
    blocks = sections[0].setdefault("blocks", [])
    blocks.append(
        {
            "id": "injected_unsupported_claim",
            "type": "bound_text",
            "info_class": "confirmed",
            "claim": claim,
        }
    )


def _append_number_to_bound_block(spec: dict[str, Any], sentence: str) -> None:
    for section in spec.get("sections") or []:
        for block in section.get("blocks") or []:
            if block.get("type") == "bound_text" and (block.get("template") or block.get("source")):
                block["claim"] = (block.get("claim") or "") + " " + sentence
                return
    raise ValueError("no bound_text block with a binding to inject into")


def inject_variant(source_run: Path, target_dir: Path, kind: str = "unsupported_claim") -> Path:
    """Copy a run and inject one defect kind.

    - unsupported_claim: append a bound_text block with no source and a fake number
    - unregistered_number: append a fake number to an existing bound block (binding kept)
    - both: do both, so one case exercises both issue types
    """
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind}")
    target = _copy_run(source_run, target_dir)
    spec_path, spec = _spec(target)

    if kind in ("unsupported_claim", "both"):
        _append_unsupported_block(spec, FAKE_CLAIM)
    if kind in ("unregistered_number", "both"):
        _append_number_to_bound_block(spec, f"该指标已提升至 {FAKE_NUMBER}%。")

    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def inject_defects(source_run: Path, target_dir: Path) -> Path:
    """Backward-compatible single case: one unsupported claim carrying a fake number."""
    return inject_variant(source_run, target_dir, kind="unsupported_claim")


def evaluate(source_run: Path, parent_dir: Path, index=None) -> dict[str, Any]:
    """Run every injected kind plus the clean run, and report recall and false positives."""
    from agent_layer.reviewer import ReviewAgent

    parent_dir = Path(parent_dir).resolve()
    parent_dir.mkdir(parents=True, exist_ok=True)

    cases = []
    for kind in KINDS:
        target = inject_variant(source_run, parent_dir / f"broken_{kind}", kind=kind)
        report = ReviewAgent(target, index=index).run()
        found = sorted({issue["type"] for issue in report.get("issues") or []})
        expected = sorted(EXPECTED_TYPES[kind])
        cases.append(
            {
                "kind": kind,
                "expected": expected,
                "found": found,
                "detected": set(expected) <= set(found),
                "issues": len(report.get("issues") or []),
            }
        )

    clean_report = ReviewAgent(Path(source_run), index=index).run()
    clean_issues = len(clean_report.get("issues") or [])
    detected = sum(1 for case in cases if case["detected"])
    return {
        "schema": "forge-fault-eval/v1",
        "cases": cases,
        "total": len(cases),
        "detected": detected,
        "recall": round(detected / len(cases), 3),
        "clean_issues": clean_issues,
        "false_positive": clean_issues > 0,
    }


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    types = sorted({issue["type"] for issue in report.get("issues") or []})
    severities = sorted({issue["severity"] for issue in report.get("issues") or []})
    return {
        "issues": len(report.get("issues") or []),
        "types": types,
        "severities": severities,
        "sections": sorted({issue["section"] for issue in report.get("issues") or []}),
    }
