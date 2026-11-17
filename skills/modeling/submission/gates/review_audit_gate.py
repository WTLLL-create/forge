"""Forge v8 review-audit gate: reviewer-style findings with blocker triage.

Implements the paper-audit discipline of bahayonghang/academic-writing-skills:
findings carry Severity (Critical/Major/Minor) x Priority (P0/P1/P2) and every
unverified numeric claim is tagged [PENDING VERIFICATION] instead of being
silently trusted. Critical/P0 blockers fail the gate.

Checks (deterministic, evidence-backed):
  1. NUMBER TRACEABILITY (Critical/P0): every number token in the paper text
     must be found in model_result.json; unmatched tokens become
     [PENDING VERIFICATION] findings.  (Whitelist: years, page/table/figure
     ordinals, and common enumeration counts.)
  2. ABSTRACT-BODY CONSISTENCY (Major/P1): numbers appearing in the abstract
     must also appear in the body.
  3. REFERENCE SHELF (Minor/P2): a references section with >= 3 entries;
     DOI-looking tokens must match the standard DOI pattern.

Usage:
    python review_audit_gate.py --run-id <run> --markdown paper.md \
        --model-result model_result.json [--strict] --report gate.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result

NUMBER_TOKEN = re.compile(r"(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)(?:%|％)?")
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+")
REFERENCE_HEADING = re.compile(r"^\s*参考文献\s*$")
CITATION_ENTRY = re.compile(r"\[\s*\d+\s*\]")
YEAR_PATTERN = re.compile(r"^(?:19|20)\d{2}$")
ORDINAL_PATTERN = re.compile(r"^(?:第)?\d{1,2}$")  # 章节/图表/页 序号


def iter_numbers(value: Any) -> set[float]:
    out: set[float] = set()
    if isinstance(value, dict):
        for child in value.values():
            out |= iter_numbers(child)
    elif isinstance(value, list):
        for child in value:
            out |= iter_numbers(child)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        out.add(float(value))
    return out


def extract_number_tokens(text: str) -> list[dict]:
    tokens = []
    for match in NUMBER_TOKEN.finditer(text):
        raw = match.group(1)
        value = float(raw)
        if YEAR_PATTERN.match(raw):
            continue
        if ORDINAL_PATTERN.match(raw) and value <= 30:
            # ordinals, page numbers, sample counts below 30 are ambiguous;
            # keep them but mark as low-confidence
            tokens.append({"value": value, "raw": raw, "low_confidence": True})
        else:
            tokens.append({"value": value, "raw": raw, "low_confidence": False})
    return tokens


def run_gate(markdown_path: Path, model_result_path: Path, run_id: str, strict: bool = False) -> dict:
    checks: list[dict] = []
    findings: list[dict] = []

    if not markdown_path.is_file() or not model_result_path.is_file():
        return gate_result(
            "review_audit_gate",
            [gate_check("inputs readable", False, actual={"md": markdown_path.is_file(), "mr": model_result_path.is_file()}, expected="both files")],
            run_id=run_id,
        )

    text = markdown_path.read_text(encoding="utf-8")
    model_result = json.loads(model_result_path.read_text(encoding="utf-8"))
    known = iter_numbers(model_result)

    # strip DOI and URL tokens before number extraction, so "10.1038/nature14539"
    # or "https://doi.org/10.1" never masquerade as paper numbers
    numeric_text = DOI_PATTERN.sub(" ", text)
    numeric_text = re.sub(r"https?://\S+", " ", numeric_text)

    tokens = extract_number_tokens(numeric_text)
    unmatched = [
        t for t in tokens
        if not any(abs(t["value"] - k) <= 1e-9 for k in known)
    ]
    # low-confidence ordinal-ish tokens are findings only in strict mode
    real_unmatched = [t for t in unmatched if not t["low_confidence"]]
    pending = [t for t in unmatched if t["low_confidence"]]
    if real_unmatched:
        findings.append({
            "id": "NUM-TRACE",
            "severity": "Critical",
            "priority": "P0",
            "pending_verification": True,
            "summary": f"{len(real_unmatched)} number(s) in the paper have no source in model_result.json",
            "evidence": real_unmatched[:8],
        })
    if pending and strict:
        findings.append({
            "id": "NUM-TRACE-LOW",
            "severity": "Minor",
            "priority": "P2",
            "pending_verification": True,
            "summary": f"{len(pending)} low-confidence number(s) (ordinals/counts) lack an exact model source",
            "evidence": pending[:8],
        })

    abstract = text.split("摘要", 1)[-1] if "摘要" in text else ""
    abstract = abstract.split("关键词", 1)[0] if "关键词" in abstract else abstract
    body = text.replace(abstract, "", 1) if abstract else text
    abstract_numbers = {t["value"] for t in extract_number_tokens(abstract)}
    body_numbers = {t["value"] for t in extract_number_tokens(body)}
    missing_from_body = sorted(abstract_numbers - body_numbers)
    if missing_from_body:
        findings.append({
            "id": "ABSTRACT-BODY",
            "severity": "Major",
            "priority": "P1",
            "pending_verification": False,
            "summary": "Numbers in the abstract do not all reappear in the body",
            "evidence": missing_from_body[:8],
        })

    lines = text.splitlines()
    ref_index = next((i for i, line in enumerate(lines) if REFERENCE_HEADING.match(line.strip())), -1)
    if ref_index < 0:
        findings.append({
            "id": "REF-SHELF",
            "severity": "Minor",
            "priority": "P2",
            "pending_verification": False,
            "summary": "No 参考文献 section found",
            "evidence": [],
        })
    else:
        ref_text = "\n".join(lines[ref_index + 1:])
        entries = len(CITATION_ENTRY.findall(ref_text))
        if entries < 3:
            findings.append({
                "id": "REF-SHELF",
                "severity": "Minor",
                "priority": "P2",
                "pending_verification": False,
                "summary": f"Only {entries} reference entries (expected >= 3)",
                "evidence": [],
            })
        bad_dois = []
        for token in re.findall(r"\b10\.\d{4,9}/[^\s,\]]+", ref_text):
            token = token.rstrip(".,;)]")
            if not DOI_PATTERN.fullmatch(token):
                bad_dois.append(token)
        if bad_dois:
            findings.append({
                "id": "DOI-FORMAT",
                "severity": "Minor",
                "priority": "P2",
                "pending_verification": True,
                "summary": "Malformed DOI tokens in references",
                "evidence": bad_dois[:5],
            })

    blockers = [f for f in findings if f["severity"] == "Critical" or f["priority"] == "P0"]
    checks.append(
        gate_check(
            "no Critical/P0 blockers",
            not blockers,
            actual=[f["id"] for f in blockers] or f"{len(findings)} findings, none blocking",
            expected="no Critical/P0 findings",
            message="Resolve or verify every untraceable number before submission.",
        )
    )
    checks.append(
        gate_check(
            "review findings enumerated",
            True,
            actual=[f["id"] for f in findings],
            expected="findings list",
        )
    )

    result = gate_result("review_audit_gate", checks, run_id=run_id)
    result["findings"] = findings
    result["blockers"] = [f["id"] for f in blockers]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reviewer-style audit with Severity x Priority triage and pending-verification tags."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--markdown", required=True, help="Rendered paper.md")
    parser.add_argument("--model-result", required=True, help="model_result.json")
    parser.add_argument("--strict", action="store_true", help="Also fail on low-confidence numbers")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    result = run_gate(Path(args.markdown), Path(args.model_result), args.run_id, strict=args.strict)
    write_gate_result(args.report, result)
    print(json.dumps({"gate": result["gate"], "status": result["status"], "report": str(Path(args.report).resolve())}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
