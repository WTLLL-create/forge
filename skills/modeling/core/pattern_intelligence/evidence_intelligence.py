"""
Evidence Intelligence Layer v1.0 — 从证据链到评分维度的推理
===============================================================
Forge v7.0.2.5: 连接 Pattern Planning 和 Artifact Compilation 的中间层。
每个 Claim 必须能被 Evidence 支撑，每个 Evidence 必须对应评分维度。

核心:
  EvidenceGraph — Claim → Evidence → Artifact → Scoring Dimension 映射
  ESR (Evidence Sufficiency Rate) — 证据是否真的支撑论点
  CCR (Claim Coverage Rate) — 核心结论是否被覆盖
  ClaimCoverageValidator — 检测未支撑的 Claim
"""
import sys, os
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pattern_intelligence"))
from paper_pattern_engine import PAPER_PATTERNS


# 评分维度 → 典型 Claim 映射 (来自 canonical_scoring_framework.md)
SCORING_CLAIMS = {
    "D1_problem_understanding": [
        "问题本质把握准确",
        "子问题分解合理",
        "核心矛盾识别清晰",
    ],
    "D2_model_reasoning": [
        "模型选择有充分理由",
        "假设标注清晰且合理",
        "数学推导完整",
        "变量定义清楚",
        "备选方案对比充分",
    ],
    "D3_solution_reliability": [
        "算法选择恰当",
        "参数确定有依据",
        "求解过程可复现",
        "结果与预期一致",
    ],
    "D4_validation_completeness": [
        "灵敏度分析充分",
        "模型对比全面",
        "验证指标充足",
        "鲁棒性检查完整",
    ],
    "D5_innovation": [
        "方法有改进",
        "组合创新合理",
        "创新论证充分",
    ],
    "D6_paper_quality": [
        "结构完整",
        "图表规范",
        "引用正确",
        "表达清晰",
    ],
}


class EvidenceGraph:
    """Claim → Evidence → Artifact 映射图"""

    def build(self, problem_type: str) -> Dict:
        """为给定题型构建完整的证据图"""
        pattern = PAPER_PATTERNS.get(problem_type, PAPER_PATTERNS["prediction"])
        claims = []

        # 每种证据类型 → 对应的 claim 和评分维度
        evidence_mappings = [
            {
                "claim_id": "MODEL_SUPERIORITY",
                "statement": f"模型选择合理且优于备选方案",
                "scoring_dimension": "D2_model_reasoning",
                "required_evidence": [
                    {"type": "table", "artifact_ref": "model_comparison",
                     "sufficiency_check": {"required_metrics": ["R²", "RMSE", "MAE"], "required_columns": ["模型", "R²", "RMSE"]}},
                    {"type": "chart", "artifact_ref": "prediction_vs_actual",
                     "sufficiency_check": {"required_metrics": ["R²"]}},
                ],
                "confidence": 0.85,
            },
            {
                "claim_id": "MODEL_ASSUMPTIONS_VALID",
                "statement": "模型核心假设经数据验证成立",
                "scoring_dimension": "D3_solution_reliability",
                "required_evidence": [
                    {"type": "chart", "artifact_ref": "residual_plot",
                     "sufficiency_check": {"required_metrics": ["残差均值为0", "残差无模式"]}},
                    {"type": "chart", "artifact_ref": "correlation_heatmap",
                     "sufficiency_check": {"required_metrics": ["最大相关系数"]}},
                ],
                "confidence": 0.82,
            },
            {
                "claim_id": "RESULT_ROBUST",
                "statement": "关键参数变化对结果影响在可接受范围内",
                "scoring_dimension": "D4_validation_completeness",
                "required_evidence": [
                    {"type": "chart", "artifact_ref": "sensitivity_tornado",
                     "sufficiency_check": {"required_metrics": ["参数影响排序", "目标值变化率"]}},
                ],
                "confidence": 0.80,
            },
            {
                "claim_id": "PROBLEM_ESSENCE",
                "statement": "问题本质被准确抽象为数学模型",
                "scoring_dimension": "D1_problem_understanding",
                "required_evidence": [
                    {"type": "argument_text", "artifact_ref": "contradiction_statement",
                     "sufficiency_check": {"required_metrics": ["核心矛盾识别", "数学本质描述"]}},
                ],
                "confidence": 0.83,
            },
            {
                "claim_id": "SOLUTION_REPRODUCIBLE",
                "statement": "求解过程参数透明，结果可复现",
                "scoring_dimension": "D3_solution_reliability",
                "required_evidence": [
                    {"type": "table", "artifact_ref": "parameter_settings",
                     "sufficiency_check": {"required_columns": ["参数", "取值", "选择理由"]}},
                ],
                "confidence": 0.78,
            },
        ]

        claims = [dict(m) for m in evidence_mappings]
        return {
            "evidence_id": f"EVG-{problem_type}",
            "problem_type": problem_type,
            "claims": claims,
            "total_claims": len(claims),
            "scoring_coverage": list(set(m["scoring_dimension"] for m in evidence_mappings)),
        }


class EvidenceEvaluator:
    """ESR + CCR 指标计算"""

    def evaluate(self, evidence_graph: Dict, actual_artifacts: Dict) -> Dict:
        """评估证据充分性和Claim覆盖率"""
        claims = evidence_graph.get("claims", [])

        # ESR: 对每个 claim, 其所有 evidence item 的 sufficiency 是否满足
        esr_scores = []
        esr_violations = []

        for claim in claims:
            for ev in claim.get("required_evidence", []):
                ref = ev["artifact_ref"]
                check = ev.get("sufficiency_check", {})

                # 模拟检查: artifact 是否存在且满足 sufficiency
                artifact_present = ref in actual_artifacts.get("present", [])
                required_metrics_ok = all(
                    m in actual_artifacts.get("metrics", [])
                    for m in check.get("required_metrics", [])
                )
                required_columns_ok = all(
                    c in actual_artifacts.get("columns", [])
                    for c in check.get("required_columns", [])
                )

                sufficient = artifact_present and required_metrics_ok and required_columns_ok
                esr_scores.append({
                    "claim_id": claim["claim_id"],
                    "evidence_ref": ref,
                    "artifact_present": artifact_present,
                    "metrics_sufficient": required_metrics_ok,
                    "columns_sufficient": required_columns_ok,
                    "sufficient": sufficient,
                })

                if not sufficient:
                    esr_violations.append({
                        "claim": claim["claim_id"],
                        "evidence": ref,
                        "missing": (
                            ["artifact"] if not artifact_present
                            else (["metrics"] if not required_metrics_ok else [])
                            + (["columns"] if not required_columns_ok else [])
                        ),
                        "scoring_impact": claim["scoring_dimension"],
                    })

        esr = round(sum(1 for s in esr_scores if s["sufficient"]) / max(len(esr_scores), 1) * 100)

        # CCR: 多少 claim 被至少一个有效 evidence 支撑
        claim_scores = {}
        for s in esr_scores:
            cid = s["claim_id"]
            if cid not in claim_scores:
                claim_scores[cid] = False
            claim_scores[cid] = claim_scores[cid] or s["sufficient"]

        ccr = round(sum(1 for v in claim_scores.values() if v) / max(len(claim_scores), 1) * 100)

        # PCR (保留 — 来自 v7.0.2 的 Pattern Compliance Rate)
        pattern = PAPER_PATTERNS.get(evidence_graph.get("problem_type", "prediction"), {})
        total_pattern_evidence = (
            len(pattern.get("recommended_tables", [])) * 2 +
            len(pattern.get("recommended_charts", [])) * 2
        )
        satisfied = len(actual_artifacts.get("present", []))
        pcr = round(min(satisfied / max(total_pattern_evidence, 1), 1.0) * 100)

        return {
            "evidence_id": evidence_graph.get("evidence_id", ""),
            "esr": esr,
            "ccr": ccr,
            "pcr": pcr,
            "three_star_grade": (
                "A" if esr >= 80 and ccr >= 80 and pcr >= 80
                else ("B" if esr >= 60 and ccr >= 60
                else "C")
            ),
            "esr_details": esr_scores,
            "violations": esr_violations,
            "scoring_dimension_impact": list(set(v["scoring_impact"] for v in esr_violations)),
            "verdict": (
                "All claims sufficiently evidenced" if not esr_violations
                else f"{len(esr_violations)} evidence gaps across {len(set(v['scoring_impact'] for v in esr_violations))} scoring dimensions"
            ),
        }


# ===== CLI =====

if __name__ == "__main__":
    graph = EvidenceGraph()
    evaluator = EvidenceEvaluator()

    print("=" * 60)
    print("v7.0.2.5 — Evidence Intelligence Layer")
    print("=" * 60)

    for pt in ["prediction", "optimization"]:
        evg = graph.build(pt)

        print(f"\n{'─' * 60}")
        print(f"[{pt.upper()}] Evidence Graph: {evg['evidence_id']}")
        print(f"  Claims: {evg['total_claims']} | Scoring coverage: {evg['scoring_coverage']}")

        for claim in evg["claims"]:
            print(f"\n  Claim: {claim['claim_id']:25s} [{claim['scoring_dimension']}]")
            print(f"    \"{claim['statement']}\" (conf={claim['confidence']:.0%})")
            for ev in claim["required_evidence"]:
                metrics = ev["sufficiency_check"].get("required_metrics", [])
                cols = ev["sufficiency_check"].get("required_columns", [])
                print(f"    ← [{ev['type']}] {ev['artifact_ref']:25s} needs: metrics={metrics} cols={cols}")

        # ESR/CCR 模拟
        fully_evidenced = {
            "present": ["model_comparison", "prediction_vs_actual", "residual_plot",
                         "correlation_heatmap", "sensitivity_tornado", "contradiction_statement",
                         "parameter_settings"],
            "metrics": ["R²", "RMSE", "MAE", "残差均值为0", "残差无模式", "最大相关系数",
                         "参数影响排序", "目标值变化率", "核心矛盾识别", "数学本质描述"],
            "columns": ["模型", "R²", "RMSE", "参数", "取值", "选择理由"],
        }

        partially_evidenced = {
            "present": ["model_comparison"],  # 只有模型比较表
            "metrics": ["R²"],
            "columns": ["模型"],
        }

        result_full = evaluator.evaluate(evg, fully_evidenced)
        result_partial = evaluator.evaluate(evg, partially_evidenced)

        print(f"\n  [Evidence Metrics]")
        print(f"    Full evidence:     ESR={result_full['esr']}%  CCR={result_full['ccr']}%  PCR={result_full['pcr']}%  → {result_full['three_star_grade']}")
        print(f"    Partial evidence:  ESR={result_partial['esr']}%  CCR={result_partial['ccr']}%  PCR={result_partial['pcr']}%  → {result_partial['three_star_grade']}")
        if result_partial["violations"]:
            print(f"    Violations: {result_partial['verdict']}")
            for v in result_partial["violations"][:3]:
                print(f"      Claim={v['claim']} → missing {v['missing']} [impacts {v['scoring_impact']}]")

    # Summary
    print(f"\n{'=' * 60}")
    print("Evidence Intelligence Layer: COMPLETE")
    print(f"  Pattern → EvidenceGraph → ESR/CCR/PCR → Scoring Dimension Impact")
    print(f"  ESR = Evidence Sufficiency, CCR = Claim Coverage, PCR = Pattern Compliance")
    print(f"  Three-star grade system: A(80%+) / B(60%+) / C(<60%)")
    print(f"\nArchitecture: Planning → Evidence → Artifact → Review")
    print(f"  Before: 'table generated because pattern says so'")
    print(f"  After:  'model_comparison table generated to prove claim MODEL_SUPERIORITY for D2_model_reasoning'")
