"""Forge v8 writing-quality gate for math-modeling papers.

Brings three evidence-based academic-writing disciplines into the modeling
workflow (borrowed from GitHub 2026 paper-writing skills):

  1. Anti-defensive writing (Adkid-Zephyr/anti-defensive-writing-Skill):
     a paper is a launch event, not a project summary. Self-weakening phrases
     ("遗憾的是/效果有限/有待进一步完善") hand the reviewer the knife;
  2. Measurable-claim writing (zLanqing/codex-claude-academic-skills):
     replace vague words ("显著提升/较好/一定程度") with measurable
     conditions; vague claims without numbers are flagged;
  3. Causal-overclaim guard (fakerqwq/social-science-paper-writing-skill):
     strong causal language ("证明了/必然/导致") must be backed by
     verification sections (检验/灵敏度/对比/误差), otherwise it is an
     Evidence Gap.

Plus the CUMCM abstract contract: the 1-page abstract must cover the four
elements 问题/方法/结果/结论 (2026 abstract rule and structure-consistency
checking). The gate reports hits with example snippets, blocking only when
the violation density exceeds a tunable tolerance.

Usage:
    python writing_quality_gate.py --run-id <run> --markdown paper.md \
        [--tolerance 0.5] --report gate.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, write_gate_result

SELF_WEAKENING = [
    "遗憾的是", "令人遗憾", "效果有限", "提升有限", "较为有限", "仍有不足",
    "仍有待", "有待进一步完善", "有待改进", "只能说明", "不敢断言", "很遗憾",
    "未能达到", "效果欠佳", "存在一定的局限性", "局限性较多",
]
VAGUE_CLAIMS = [
    "显著提升", "显著提高", "显著改善", "有效提升", "有效改善", "效果较好",
    "性能较好", "精度较高", "比较好", "较为理想", "一定程度的", "一定程度上",
    "明显提高", "明显改善", "大幅度提高", "较好效果", "良好效果",
]
CAUSAL_OVERCLAIM = [
    "证明了", "必然导致", "决定了", "完全证明", "毫无疑问", "铁定", "证实了",
]
VERIFICATION_MARKERS = [
    "检验", "灵敏度", "敏感性", "对比", "误差", "验证", "鲁棒", "残差",
    "置信区间", "假设检验",
]
ABSTRACT_ELEMENTS = {
    "problem": ["针对", "研究", "问题", "分析"],
    "method": ["模型", "算法", "方法", "建立", "构建", "采用"],
    "result": ["结果", "得到", "误差", "精度", "指标", "%", "r2", "R2", "RMSE", "MAE"],
    "conclusion": ["结论", "建议", "可为", "提供", "表明"],
}

SENTENCE_SPLIT = re.compile(r"[。！？!?；;\n]+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]


def _hits_with_context(text: str, words: list[str], max_ctx: int = 5) -> list[dict]:
    hits = []
    for word in words:
        for match in re.finditer(re.escape(word), text):
            start = max(0, match.start() - 18)
            end = min(len(text), match.end() + 22)
            snippet = text[start:end].replace("\n", " ")
            hits.append({"word": word, "snippet": snippet})
            if len(hits) >= max_ctx:
                return hits
    return hits


def _has_number_nearby(sentence: str) -> bool:
    return bool(re.search(r"\d+(?:\.\d+)?\s*%?|\d+(?:\.\d+)?\s*(?:km|kg|m|s|元|人|个|次)", sentence))


def run_gate(markdown_path: Path, run_id: str, tolerance: float = 0.5) -> dict:
    if not markdown_path.is_file():
        return gate_result(
            "writing_quality_gate",
            [gate_check("markdown readable", False, actual=str(markdown_path), expected="existing paper.md")],
            run_id=run_id,
        )
    text = markdown_path.read_text(encoding="utf-8")
    sentences = _sentences(text)
    total = max(len(sentences), 1)

    weak = _hits_with_context(text, SELF_WEAKENING)
    weak_density = len(weak) / total
    checks = [
        gate_check(
            "no self-weakening / defensive phrases",
            weak_density <= tolerance * 0.5,
            actual=weak[:5] if weak else f"{len(weak)} hits",
            expected=f"density <= {round(tolerance * 0.5, 2)}",
            message="Defensive writing hands the reviewer reasons to doubt; rewrite as claims with evidence.",
        )
    ]

    vague_hits = []
    for sentence in sentences:
        for word in VAGUE_CLAIMS:
            if word in sentence and not _has_number_nearby(sentence):
                vague_hits.append({"word": word, "sentence": sentence[:80]})
                break
    vague_density = len(vague_hits) / total
    checks.append(
        gate_check(
            "vague claims carry measurable support",
            vague_density <= tolerance * 0.5,
            actual=vague_hits[:5] if vague_hits else f"{len(vague_hits)} hits",
            expected=f"density <= {round(tolerance * 0.5, 2)}",
            message="Replace vague words with measurable conditions and numbers.",
        )
    )

    causal_hits = _hits_with_context(text, CAUSAL_OVERCLAIM, max_ctx=10)
    verification_count = sum(text.count(marker) for marker in VERIFICATION_MARKERS)
    verification_density = verification_count / total
    causal_density = len(causal_hits) / total
    unbalanced = causal_density > tolerance and verification_density < tolerance * 0.8
    checks.append(
        gate_check(
            "causal claims backed by verification evidence",
            not unbalanced,
            actual={"causal_hits": causal_hits[:5], "verification_markers": verification_count},
            expected="verification sections present when causal language is used",
            message="Strong causal claims without verification sections are Evidence Gaps.",
        )
    )

    abstract = text.split("摘要", 1)[-1] if "摘要" in text else text
    abstract = abstract.split("关键词", 1)[0] if "关键词" in abstract else abstract
    if len(abstract) > 1500:
        abstract = abstract[:1500]
    missing_elements = []
    for element, keywords in ABSTRACT_ELEMENTS.items():
        if not any(keyword in abstract for keyword in keywords):
            missing_elements.append(element)
    checks.append(
        gate_check(
            "abstract covers problem/method/result/conclusion",
            not missing_elements,
            actual=missing_elements if missing_elements else "all four elements present",
            expected=["problem", "method", "result", "conclusion"],
            message="The 1-page abstract must state the problem, method, key results, and conclusion.",
        )
    )

    result = gate_result("writing_quality_gate", checks, run_id=run_id)
    result["quality"] = {
        "self_weakening_hits": len(weak),
        "vague_claim_hits": len(vague_hits),
        "causal_hits": len(causal_hits),
        "verification_markers": verification_count,
        "abstract_missing_elements": missing_elements,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Writing-quality gate: anti-defensive, measurable claims, causal-claim safety, abstract contract."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--markdown", required=True, help="Rendered paper.md")
    parser.add_argument("--tolerance", type=float, default=0.5,
                        help="Violation density tolerance (0..1); lower is stricter")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    result = run_gate(Path(args.markdown), args.run_id, tolerance=args.tolerance)
    write_gate_result(args.report, result)
    print(json.dumps({"gate": result["gate"], "status": result["status"], "report": str(Path(args.report).resolve())}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
