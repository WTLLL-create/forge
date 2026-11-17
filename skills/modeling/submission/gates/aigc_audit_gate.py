"""Forge v8 AIGC-audit gate: heuristic detection of AI-generated prose patterns.

Adapted from the objective style metrics of AutoMCM-Pro (style_check.py) and the
AIGC-audit idea of BZD math-modeling skills. The gate does NOT prove human or AI
authorship; it flags six mechanical patterns that correlate with unchecked AI
drafting so the team can rewrite before submission (2026 CUMCM papers are
checked for AI traces and the team is fully responsible for every claim).

The six indicators are computed on the rendered paper Markdown (the
PaperSpec-controlled text), each scored 0..1; the aggregate risk level is
LOW / MEDIUM / HIGH. HIGH blocks the run with a rewrite requirement.

Usage:
    python aigc_audit_gate.py --run-id <run> --markdown paper.md --report gate.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result

CLICHE_WORDS = [
    "综上所述", "值得注意的是", "不难发现", "显而易见", "众所周知",
    "有效提升", "显著提升", "大幅提高", "具有重要意义", "进一步验证了",
    "模型的优劣", "效果良好", "精度较高", "结果表明", "实验证明",
]
MECHANICAL_TRANSITIONS = [
    "一方面", "另一方面", "具体而言", "总体来说", "总的来说", "换言之",
    "需要注意的是", "与此同时", "基于以上分析", "从图中可以看出", "由表可知",
]
ABSOLUTE_WORDS = [
    "完美", "最优", "最佳", "彻底", "完全解决", "毫无", "绝对", "一定正确", "100%",
]
LIST_LEADERS = re.compile(r"^(首先|其次|然后|最后|第一|第二|第三|其一|其二|此外|另外)[,，:：]")
BULLET_PATTERN = re.compile(r"^\s*(?:[-*•]|\d+[.、)])\s+")
SENTENCE_SPLIT = re.compile(r"[。！？!?；;\n]+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]


def _count_hits(text: str, words: list[str]) -> int:
    return sum(len(re.findall(re.escape(word), text)) for word in words)


def run_audit(text: str) -> dict:
    sentences = _sentences(text)
    total = len(sentences)
    total_chars = len(text)

    listy = sum(
        1 for s in sentences
        if LIST_LEADERS.match(s) or BULLET_PATTERN.match(s)
    )
    list_density = listy / total if total else 0.0

    cliche_hits = _count_hits(text, CLICHE_WORDS)
    cliche_density = min(1.0, cliche_hits / max(1.0, total_chars / 1500))

    transition_hits = _count_hits(text, MECHANICAL_TRANSITIONS)
    transition_density = min(1.0, transition_hits / max(1.0, total_chars / 2000))

    absolute_hits = _count_hits(text, ABSOLUTE_WORDS)
    absolute_density = min(1.0, absolute_hits / max(1.0, total_chars / 2500))

    lengths = [len(s) for s in sentences]
    uniformity = 0.0
    if lengths:
        mean_len = sum(lengths) / len(lengths)
        variance = sum((length - mean_len) ** 2 for length in lengths) / len(lengths)
        std = variance ** 0.5
        # extremely regular sentence lengths correlate with templated drafting
        uniformity = max(0.0, min(1.0, 1.0 - std / max(mean_len, 1.0) / 2.2))

    grams = Counter()
    for sentence in sentences:
        chars = list(sentence)
        for i in range(len(chars) - 3):
            grams["".join(chars[i : i + 4])] += 1
    if len(grams) > 1 and total_chars > 0:
        repeated = sum(count - 1 for count in grams.values() if count > 1)
        repetition = min(1.0, repeated / max(1, len(grams) / 8))
    else:
        repetition = 0.0

    score = (
        list_density * 0.15
        + cliche_density * 0.25
        + transition_density * 0.15
        + absolute_density * 0.20
        + uniformity * 0.10
        + repetition * 0.15
    )
    if score >= 0.55:
        level = "HIGH"
    elif score >= 0.35:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {
        "score": round(score, 3),
        "level": level,
        "indicators": {
            "list_density": round(list_density, 3),
            "cliche_density": round(cliche_density, 3),
            "transition_density": round(transition_density, 3),
            "absolute_density": round(absolute_density, 3),
            "sentence_uniformity": round(uniformity, 3),
            "cross_sentence_repetition": round(repetition, 3),
        },
    }


def run_gate(markdown_path: Path, run_id: str, hard_block: bool = True) -> dict:
    if not markdown_path.is_file():
        return gate_result(
            "aigc_audit_gate",
            [gate_check("markdown readable", False, actual=str(markdown_path), expected="existing paper.md")],
            run_id=run_id,
        )
    text = markdown_path.read_text(encoding="utf-8")
    audit = run_audit(text)
    checks = [
        gate_check(
            "aigc risk below hard threshold",
            not hard_block or audit["level"] != "HIGH",
            actual=audit["level"],
            expected="LOW or MEDIUM" if hard_block else "informational",
            message="High AIGC-trace risk: rewrite flagged passages before submission.",
        )
    ]
    for name, value in audit["indicators"].items():
        checks.append(gate_check(f"indicator {name}", True, actual=value, expected="0..1"))
    result = gate_result("aigc_audit_gate", checks, run_id=run_id)
    result["audit"] = audit
    result["artifacts"] = {"markdown_sha256": hashlib.sha256(markdown_path.read_bytes()).hexdigest()}
    result["limitations"] = "Heuristic prose-quality signals only; neither authorship detection nor proof of AI compliance. PASS does not replace human verification and AI-use disclosure."
    result["human_review"] = "PENDING"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Heuristic AIGC-trace audit of the paper Markdown.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--markdown", required=True, help="Rendered paper.md")
    parser.add_argument("--report", required=True)
    parser.add_argument("--no-block", action="store_true", help="Report HIGH risk without failing the gate")
    args = parser.parse_args()

    result = run_gate(Path(args.markdown), args.run_id, hard_block=not args.no_block)
    write_gate_result(args.report, result)
    print(json.dumps({"gate": result["gate"], "status": result["status"], "report": str(Path(args.report).resolve())}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
