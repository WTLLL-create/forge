"""
Scientific Consistency Engine v1.0 — 科学推理链验证
========================================================
Forge v6.5 Wave 3.2: 验证论文中假设→模型→数据→结论 的一致性。
基于 contradiction_finder.md 的 S-tier 资产 (4种矛盾类型)。

与 Reviewer 的区别:
  Reviewer: "这篇论文好不好？" (领域质量评价)
  Consistency: "这篇论文的推理链对不对？" (科学一致性)

三层:
  Layer 1 (Rule): 确定性检查 — 假设/模型冲突, 公式/变量断链
  Layer 2 (Pattern): 高频数学建模推理错误 — 缺验证, 数据→结论跳跃
  Layer 3 (LLM): 逻辑链完整性 (placeholder)
"""
from datetime import datetime, timezone
from typing import Dict, List


# Layer 1: 确定性规则检查
CONSISTENCY_RULES = [
    {
        "id": "linear_assumption_nonlinear_model",
        "check": lambda dc, mr: (
            dc and any(
                "线性" in str(d.get("reasoning", []))
                and d.get("primary_model", "") in ("RandomForest", "XGBoost", "神经网络", "SVM")
                for d in dc.get("decisions", [])
            )
        ),
        "type": "assumption_model_mismatch",
        "severity": "P1", "confidence": 0.90,
        "source_node": "assumption", "target_node": "model",
        "msg": "假设数据呈线性关系，但选了非线性模型",
        "suggestion": "要么修改假设（承认非线性），要么改用线性模型或说明为何非线性更合适"
    },
    {
        "id": "formula_without_variable_definition",
        "check": lambda arts, dc: (
            arts
            and any(a["artifact_type"] == "formula" for a in arts)
            and not any(
                d.get("model_family") and d.get("variable_definitions")
                for d in dc.get("decisions", []) if dc
            )
        ),
        "type": "formula_variable_gap",
        "severity": "P1", "confidence": 0.85,
        "source_node": "formula", "target_node": "variables",
        "msg": "论文中有公式但没有对应的变量定义",
        "suggestion": "在符号说明或模型建立章节补充变量含义和单位"
    },
]

# Layer 2: 模式识别（来自 contradiction_finder.md）
CONSISTENCY_PATTERNS = [
    {
        "id": "prediction_without_validation_split",
        "check": lambda bp, dc, mr: (
            bp and bp.get("problem_type") == "prediction"
            and mr and "train_test_split" not in str(mr).lower()
        ),
        "type": "prediction_validation_missing",
        "severity": "P1", "confidence": 0.88,
        "source_node": "model", "target_node": "validation",
        "msg": "预测类论文未提及训练/测试集划分",
        "suggestion": "补充交叉验证或留出法验证，确保模型泛化能力可评估"
    },
    {
        "id": "optimization_without_pareto",
        "check": lambda bp, dc, mr: (
            bp and bp.get("problem_type") == "optimization"
            and dc and any(
                d.get("primary_model") in ("NSGA-II", "MOEA", "多目标")
                for d in dc.get("decisions", [])
            )
            and not any(
                s["id"] == "sensitivity"
                for s in bp.get("sections", [])
            )
        ),
        "type": "method_limitation_hidden",
        "severity": "P2", "confidence": 0.82,
        "source_node": "model", "target_node": "conclusion",
        "msg": "多目标优化使用了 NSGA-II 但没有 Pareto 前沿分析",
        "suggestion": "补充 Pareto 前沿图，展示目标间的权衡关系"
    },
    {
        "id": "data_to_conclusion_leap",
        "check": lambda arts, dc, mr: (
            mr and mr.get("results_summary")
            and isinstance(mr["results_summary"], dict)
            and mr["results_summary"].get("summary_text", "")
            and not any(
                a["artifact_type"] in ("chart", "table")
                for a in (arts or [])
            )
        ),
        "type": "data_conclusion_leap",
        "severity": "P2", "confidence": 0.80,
        "source_node": "data", "target_node": "conclusion",
        "msg": "有结论但没有图表支撑 — 数据→结论可能存在跳跃",
        "suggestion": "为关键结论补充数据可视化（趋势图/对比表）"
    },
    {
        "id": "objective_conflict_flattened",
        "check": lambda dc, mr: (
            dc and any(
                d.get("model_family") == "optimization"
                and len(d.get("reasoning", [])) <= 1
                for d in dc.get("decisions", [])
            )
        ),
        "type": "objective_conflict_ignored",
        "severity": "P1", "confidence": 0.85,
        "source_node": "problem", "target_node": "model",
        "msg": "优化问题可能有多目标冲突但被简化为单目标（来自 contradiction_finder.md 类型1）",
        "suggestion": "识别问题中是否存在精度/效率/成本等多目标权衡，分析是否被过度简化"
    },
]


class ConsistencyEngine:
    """科学一致性验证引擎"""

    def check(self,
              blueprint: Dict = None,
              section_artifacts: Dict = None,
              leaf_artifacts: List[Dict] = None,
              problem_state: Dict = None,
              decision_contract: Dict = None,
              model_result: Dict = None,
              review_artifact: Dict = None) -> Dict:
        """
        验证科学推理链一致性。

        输入: 完整的 PaperArtifact Graph + ReviewArtifact
        输出: ConsistencyArtifact
        """
        findings = []
        arts = leaf_artifacts or []

        chain_nodes = ["problem", "assumption", "model", "data", "validation", "conclusion"]

        # Layer 1: 规则检查
        for rule in CONSISTENCY_RULES:
            try:
                if rule["check"](decision_contract, model_result):
                    findings.append({
                        "id": f"CONS-{rule['id']}",
                        "type": rule["type"],
                        "severity": rule["severity"],
                        "layer": "rule",
                        "description": rule["msg"],
                        "source_node": rule["source_node"],
                        "target_node": rule["target_node"],
                        "evidence": "Rule-based deterministic check",
                        "suggestion": rule["suggestion"],
                        "confidence": rule["confidence"],
                    })
            except Exception:
                pass

        # Layer 2: 模式检查
        for pat in CONSISTENCY_PATTERNS:
            try:
                if pat["check"](blueprint, decision_contract, model_result):
                    findings.append({
                        "id": f"CONS-{pat['id']}",
                        "type": pat["type"],
                        "severity": pat["severity"],
                        "layer": "pattern",
                        "description": pat["msg"],
                        "source_node": pat["source_node"],
                        "target_node": pat["target_node"],
                        "evidence": "Pattern matched from contradiction_finder.md",
                        "suggestion": pat["suggestion"],
                        "confidence": pat["confidence"],
                    })
            except Exception:
                pass

        # Layer 3: LLM (placeholder)
        # 未来接入 LLM 分析: 逻辑链完整性、创新真实性、结论是否超过实验支持范围

        # 评分: 基分100, 每个 P1 扣10, P2 扣5
        score = 100
        for f in findings:
            if f["severity"] == "P0":
                score -= 20
            elif f["severity"] == "P1":
                score -= 10
            elif f["severity"] == "P2":
                score -= 5
            else:
                score -= 2
        score = max(0, min(100, score))

        return {
            "check_id": f"CSC-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
            "findings": findings,
            "consistency_score": score,
            "chains_checked": chain_nodes,
            "summary": f"科学一致性评分 {score}/100。{'推理链高度一致' if score >= 90 else '存在不一致性需要修正' if findings else '未发现推理链断裂'}。共 {len(findings)} 处问题。",
        }


# ===== E2E Boundary Test (vs Reviewer) =====

def boundary_test() -> Dict:
    """验证 Consistency Engine 和 Reviewer Engine 不重叠"""
    from structure_selector_runtime import StructureSelector
    from section_generator_runtime import SectionGenerator
    from leaf_compilers_runtime import FormulaCompiler, TableCompiler, ChartCompiler, ReferenceCompiler
    from reviewer_engine_runtime import ReviewerEngine
    from style_compiler_runtime import StyleCompiler

    selector = StructureSelector()
    generator = SectionGenerator()
    style = StyleCompiler()
    reviewer = ReviewerEngine()
    engine = ConsistencyEngine()

    ps = {"problem_type": "prediction", "domain": "air_quality", "sub_problems": []}
    bp = selector.select(ps)
    sections_out = generator.compile(bp)
    dc = {"decisions": [{"primary_model": "RandomForest", "reasoning": ["假设数据呈线性趋势"]}]}
    mr = {"results_summary": {"summary_text": "预测精度良好"}}

    leaf_arts = []
    for s in sections_out["artifacts"]:
        if "table_compiler" in s["dependencies"]:
            leaf_arts.append(TableCompiler().compile(s, mr, style.compile("CUMCM")))

    review = reviewer.review(bp, sections_out, leaf_arts, ps, dc, mr)
    consistency = engine.check(bp, sections_out, leaf_arts, ps, dc, mr, review)

    # 边界验证: Reviewer findings 和 Consistency findings 不应有同类型
    reviewer_types = {f["type"] for f in review["findings"]}
    consistency_types = {f["type"] for f in consistency["findings"]}
    overlap = reviewer_types & consistency_types

    return {
        "reviewer_findings": len(review["findings"]),
        "reviewer_types": sorted(reviewer_types),
        "consistency_findings": len(consistency["findings"]),
        "consistency_types": sorted(consistency_types),
        "type_overlap": sorted(overlap) if overlap else [],
        "boundary_clean": len(overlap) == 0,
        "reviewer_score": review["summary"]["total_score"],
        "consistency_score": consistency["consistency_score"],
    }


if __name__ == "__main__":
    engine = ConsistencyEngine()

    # 场景1: 预测+RandomForest+线性假设 → 应检测到冲突
    print("=" * 60)
    print("Scientific Consistency Engine v1.0 — Boundary Test")
    print("=" * 60)
    print("\nScenario: prediction + RandomForest + linear assumption")

    bt = boundary_test()
    print(f"  Reviewer: {bt['reviewer_findings']} findings (types: {bt['reviewer_types']})")
    print(f"  Consistency: {bt['consistency_findings']} findings (types: {bt['consistency_types']})")
    print(f"  Type overlap: {bt['type_overlap'] or 'NONE'}")
    print(f"  Boundary clean: {'YES' if bt['boundary_clean'] else 'NO — OVERLAP DETECTED'}")
    print(f"  Scores: Reviewer={bt['reviewer_score']}/100, Consistency={bt['consistency_score']}/100")

    # 快速检查: 直接调用
    dc = {"decisions": [{"primary_model": "RandomForest", "reasoning": ["假设数据呈线性趋势"]}]}
    mr = {"results_summary": {"summary_text": "预测精度良好"}}
    result = engine.check(decision_contract=dc, model_result=mr)
    print(f"\nDirect call: score={result['consistency_score']}/100, findings={len(result['findings'])}")
    for f in result["findings"]:
        print(f"  [{f['severity']}] [{f['type']}] {f['source_node']}→{f['target_node']}: {f['description'][:70]}")
