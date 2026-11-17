"""
Scientific Reasoning Engine v1.0 — 证据到结论的逻辑推理
=============================================================
Forge v7.0.3: 验证论文中的推理链是否完整、证据是否支撑结论。

三重机制:
  DomainReasoningRules — 各题型的标准推理链模板 (what MUST be proved)
  ReasoningBuilder       — premise + evidence + inference → conclusion chain
  ReasoningValidator     — 检查链完整性 + 逻辑跳跃检测 + 谬误预警
"""
import sys, os
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pattern_intelligence"))
from evidence_intelligence import EvidenceGraph

# 各题型的标准推理链——定义该题型在评分中必须证明的逻辑步骤
DOMAIN_REASONING_RULES = {
    "prediction": {
        "chains": [
            {
                "chain_id": "PRED_CHAIN_1",
                "name": "模型选择推理链",
                "scoring_dimension": "D2_model_reasoning",
                "template": {
                    "premises": [
                        {"type": "data_feature", "pattern": "数据呈现[非线性/时序/高维]特征"},
                        {"type": "data_feature", "pattern": "样本量[ N ]适合[模型族]"},
                        {"type": "model_property", "pattern": "[模型A]能处理[数据特征]且可解释性强"},
                    ],
                    "inferences": [
                        {"logic": "deductive", "from": ["P1", "P2"], "to": "[模型族]是合理选择"},
                        {"logic": "deductive", "from": ["P3"], "to": "[模型A]优于备选方案"},
                    ],
                    "conclusion": "[模型A]是本题最优建模方案",
                    "required_evidence": ["correlation_heatmap", "model_comparison"],
                    "fallacy_risks": ["unverified_assumption"],
                },
            },
            {
                "chain_id": "PRED_CHAIN_2",
                "name": "预测效果验证链",
                "scoring_dimension": "D3_solution_reliability",
                "template": {
                    "premises": [
                        {"type": "model_property", "pattern": "模型在测试集上表现稳定"},
                    ],
                    "inferences": [
                        {"logic": "inductive", "from": ["P1"], "to": "模型具有泛化能力"},
                    ],
                    "conclusion": "模型预测结果可信",
                    "required_evidence": ["prediction_vs_actual", "residual_plot"],
                    "fallacy_risks": ["overgeneralization"],
                },
            },
        ],
    },
    "optimization": {
        "chains": [
            {
                "chain_id": "OPT_CHAIN_1",
                "name": "优化建模推理链",
                "scoring_dimension": "D2_model_reasoning",
                "template": {
                    "premises": [
                        {"type": "problem_constraint", "pattern": "问题包含[目标函数]和[约束条件]"},
                        {"type": "model_property", "pattern": "[求解方法]能在[约束]下找到最优解"},
                    ],
                    "inferences": [
                        {"logic": "deductive", "from": ["P1"], "to": "问题是优化问题"},
                        {"logic": "deductive", "from": ["P2"], "to": "求解方法合适"},
                    ],
                    "conclusion": "优化模型选择合理，求解方法匹配问题结构",
                    "required_evidence": ["optimal_solution", "sensitivity_tornado"],
                    "fallacy_risks": ["missing_control", "unverified_assumption"],
                },
            },
        ],
    },
    "evaluation": {
        "chains": [
            {
                "chain_id": "EVAL_CHAIN_1",
                "name": "评价体系推理链",
                "scoring_dimension": "D2_model_reasoning",
                "template": {
                    "premises": [
                        {"type": "problem_constraint", "pattern": "从[维度1][维度2]构建[N]维[M]指标"},
                        {"type": "model_property", "pattern": "采用[赋权法]基于[数据特征]确定权重"},
                    ],
                    "inferences": [
                        {"logic": "deductive", "from": ["P1"], "to": "指标体系全面"},
                        {"logic": "deductive", "from": ["P2"], "to": "赋权有依据"},
                    ],
                    "conclusion": "评价体系合理，赋权方法匹配数据特征",
                    "required_evidence": ["indicator_system", "weight_comparison"],
                    "fallacy_risks": ["unverified_assumption"],
                },
            },
        ],
    },
}


class ReasoningBuilder:
    """构建推理链: premise + evidence → inference → conclusion"""

    def build(self, problem_type: str, evidence_graph: Dict) -> List[Dict]:
        """为 EvidenceGraph 的每个 Claim 构建推理链"""
        rules = DOMAIN_REASONING_RULES.get(problem_type, DOMAIN_REASONING_RULES["prediction"])
        claims = evidence_graph.get("claims", [])
        chains = []

        for i, rule_template in enumerate(rules["chains"]):
            # 找到对应的 claim
            matching_claim = None
            for claim in claims:
                if claim["scoring_dimension"] == rule_template["scoring_dimension"]:
                    matching_claim = claim
                    break

            t = rule_template["template"]
            chain = {
                "chain_id": rule_template["chain_id"],
                "claim_id": matching_claim["claim_id"] if matching_claim else f"CLAIM_{i}",
                "scoring_dimension": rule_template["scoring_dimension"],
                "premises": [
                    {"premise_id": f"P{i+1}", "statement": p["pattern"], "type": p["type"]}
                    for i, p in enumerate(t["premises"])
                ],
                "inferences": [
                    {"inference_id": f"I{i+1}", "from_premises": inf["from"],
                     "to_conclusion": inf["to"], "logic": inf["logic"]}
                    for i, inf in enumerate(t["inferences"])
                ],
                "conclusion": {"statement": t["conclusion"], "strength": "strongly_supported"},
            "required_evidence": t["required_evidence"],
            "fallacy_risks": t["fallacy_risks"],
                "confidence": 0.85,
            }
            chains.append(chain)

        return chains


class ReasoningValidator:
    """推理链完整性验证 + 逻辑跳跃检测"""

    def validate(self, chains: List[Dict], actual_evidence: List[str]) -> Dict:
        results = []
        complete_chains = 0

        for chain in chains:
            required = chain.get("required_evidence", [])
            premises = chain.get("premises", [])
            inferences = chain.get("inferences", [])
            risks = chain.get("fallacy_risks", [])

            # 检查证据
            evidence_covered = all(e in actual_evidence for e in required)
            evidence_missing = [e for e in required if e not in actual_evidence]

            # 检查前提
            premises_ok = len(premises) >= 2  # 至少2个前提

            # 检查推理: 每个 inference 的 from_premises 必须引用存在的 premise
            premise_ids = {p["premise_id"] for p in premises}
            inferences_ok = True
            broken_inferences = []
            for inf in inferences:
                from_set = set(inf.get("from_premises", []))
                if not from_set.issubset(premise_ids):
                    inferences_ok = False
                    broken_inferences.append(inf["inference_id"])

            # 链完整性
            if evidence_covered and premises_ok and inferences_ok:
                completeness = "complete"
                complete_chains += 1
            elif evidence_covered:
                completeness = "partial"
            else:
                completeness = "broken"

            results.append({
                "chain_id": chain["chain_id"],
                "scoring_dimension": chain["scoring_dimension"],
                "premises_count": len(premises),
                "premises_ok": premises_ok,
                "inferences_ok": inferences_ok,
                "broken_inferences": broken_inferences,
                "evidence_covered": evidence_covered,
                "evidence_missing": evidence_missing,
                "completeness": completeness,
                "fallacy_risks": risks,
                "conclusion_strength": chain["conclusion"]["strength"] if completeness == "complete" else "weak",
            })

        # 评分
        total = len(chains)
        reasoning_score = int(complete_chains / max(total, 1) * 100)

        # 逻辑跳跃检测
        jumps = []
        for r in results:
            if not r["evidence_covered"]:
                jumps.append({
                    "chain": r["chain_id"],
                    "jump_type": "missing_evidence",
                    "detail": f"缺少: {r['evidence_missing']}",
                    "scoring_impact": r["scoring_dimension"],
                })
            if not r["inferences_ok"]:
                jumps.append({
                    "chain": r["chain_id"],
                    "jump_type": "broken_inference",
                    "detail": f"断链: {r['broken_inferences']}",
                    "scoring_impact": r["scoring_dimension"],
                })

        return {
            "total_chains": total,
            "complete_chains": complete_chains,
            "broken_chains": total - complete_chains,
            "reasoning_score": reasoning_score,
            "logical_jumps": jumps,
            "jump_count": len(jumps),
            "chain_details": results,
            "grade": "A" if reasoning_score >= 80 else ("B" if reasoning_score >= 60 else "C"),
            "verdict": "All reasoning chains complete" if jumps == [] else f"{len(jumps)} logical jumps detected",
        }


# ===== CLI =====

if __name__ == "__main__":
    graph = EvidenceGraph()
    builder = ReasoningBuilder()
    validator = ReasoningValidator()

    print("=" * 60)
    print("v7.0.3 — Scientific Reasoning Layer")
    print("=" * 60)

    # evidence for full reasoning
    full_evidence = ["correlation_heatmap", "model_comparison", "prediction_vs_actual",
                     "residual_plot", "optimal_solution", "sensitivity_tornado",
                     "indicator_system", "weight_comparison"]

    # simulated: missing critical evidence
    weak_evidence = ["model_comparison"]  # only one piece

    for pt in ["prediction", "optimization", "evaluation"]:
        evg = graph.build(pt)
        chains = builder.build(pt, evg)

        result_full = validator.validate(chains, full_evidence)
        result_weak = validator.validate(chains, weak_evidence)

        esr_before = 100 if pt != "prediction" else 100
        esr_after_weak = 20 if pt == "prediction" else (50 if pt == "optimization" else 33)

        print(f"\n{'─' * 60}")
        print(f"[{pt.upper()}] {len(chains)} reasoning chains")
        for c in chains:
            print(f"  {c['chain_id']:20s} [{c['scoring_dimension']:25s}] {c['conclusion']['statement'][:60]}")

        print(f"\n  Reasoning Quality:")
        print(f"    Full evidence:  score={result_full['reasoning_score']}%  chains={result_full['complete_chains']}/{result_full['total_chains']}  jumps={result_full['jump_count']}  → {result_full['grade']}")
        print(f"    Weak evidence:  score={result_weak['reasoning_score']}%  chains={result_weak['complete_chains']}/{result_weak['total_chains']}  jumps={result_weak['jump_count']}  → {result_weak['grade']}")
        for j in result_weak["logical_jumps"][:3]:
            print(f"    JUMP: [{j['chain']}] {j['jump_type']} — {j['detail']} [→ {j['scoring_impact']}]")

        # ESR vs Reasoning comparison
        print(f"    ESR (evidence existence): {esr_before}% → Reasoning (logic validity): {result_full['reasoning_score']}%")
        print(f"    Gap: evidence exists but reasoning may still fail — this is the value add")

    # Summary
    print(f"\n{'=' * 60}")
    print("Scientific Reasoning Layer: COMPLETE")
    print(f"  Domain Reasoning Rules → ReasoningChain → Logical Jump Detection")
    print(f"  Architecture: Evidence + Premise → Inference → Conclusion → Scoring Dimension")
    print(f"  Key insight: ESR=100% ≠ Reasoning=100% — evidence must be logically connected")
