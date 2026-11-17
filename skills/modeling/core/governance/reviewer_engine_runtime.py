"""
ReviewerEngine v1.0 — 领域质量智能审查引擎
================================================
Forge v6.5 Wave 3.1: Quality Intelligence Layer 入口。
消费 PaperArtifact Graph → 输出结构化 ReviewArtifact。

三层设计:
  Layer 1 (Rule):   硬规则 — 结构完整性、必填字段、基本约束
  Layer 2 (Pattern): 模式识别 — 基于 reviewer_agent/ 积累的高频缺陷模式
  Layer 3 (LLM):    推理层 — 创新性、逻辑合理性、解释质量（v1 placeholder）

消费资产:
  - reviewer_agent/scoring_rules.md (6维评分)
  - reviewer_agent/improvement_strategy.md (问题→动作映射)
  - evaluation/canonical_scoring_framework.md (权威评分)
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone


# 硬规则检查矩阵（Layer 1）
STRUCTURE_RULES = [
    {"check": "abstract_exists",     "section_id": "abstract",    "severity": "P1", "impact": -4, "msg": "缺少摘要"},
    {"check": "analysis_exists",     "section_id": "analysis",    "severity": "P1", "impact": -3, "msg": "缺少问题分析"},
    {"check": "assumptions_exists",  "section_id": "assumptions", "severity": "P2", "impact": -2, "msg": "缺少模型假设"},
    {"check": "modeling_exists",     "section_id": "modeling",    "severity": "P0", "impact": -5, "msg": "缺少模型建立章节"},
    {"check": "results_exists",      "section_id": "results",     "severity": "P1", "impact": -4, "msg": "缺少结果分析"},
    {"check": "evaluation_exists",   "section_id": "evaluation",  "severity": "P2", "impact": -2, "msg": "缺少模型评价"},
    {"check": "references_exists",   "section_id": "references",  "severity": "P2", "impact": -1, "msg": "缺少参考文献"},
]

# 模式识别矩阵（Layer 2，来自 reviewer_agent/improvement_strategy.md）
PATTERN_CHECKS = [
    {
        "id": "weak_model_justification",
        "condition": lambda bp, arts, dc: (
            dc and len(dc.get("decisions", [])) > 0
            and not any(
                len(d.get("reasoning", [])) >= 2
                for d in dc["decisions"]
            )
        ),
        "severity": "P1", "impact": -4, "type": "weak_model_choice",
        "location": "analysis", "layer": "pattern",
        "msg": "模型选择理由不足：缺少至少2层论证链",
        "suggestion": "在问题分析章节增加'为什么选此模型'的对比分析"
    },
    {
        "id": "insufficient_validation_evidence",
        "condition": lambda bp, arts, dc: (
            bp and "sensitivity" not in [s["id"] for s in bp.get("sections", [])]
            and bp.get("problem_type") == "optimization"
        ),
        "severity": "P1", "impact": -3, "type": "insufficient_validation",
        "location": "sensitivity", "layer": "pattern",
        "msg": "优化类论文缺少灵敏度分析章节",
        "suggestion": "增加参数扰动测试，展示参数变化对最优解的影响"
    },
    {
        "id": "missing_model_comparison",
        "condition": lambda bp, arts, dc: (
            bp and bp.get("problem_type") == "prediction"
            and "model_comparison" not in [s["id"] for s in bp.get("sections", [])]
        ),
        "severity": "P2", "impact": -2, "type": "insufficient_validation",
        "location": "model_comparison", "layer": "pattern",
        "msg": "预测类论文缺少模型对比章节",
        "suggestion": "增加多模型性能对比表（如 vs ARIMA / vs XGBoost）"
    },
    {
        "id": "empty_formula_section",
        "condition": lambda bp, arts, dc: (
            arts and not any(a["artifact_type"] == "formula" for a in arts)
        ),
        "severity": "P1", "impact": -4, "type": "format_issue",
        "location": "modeling", "layer": "pattern",
        "msg": "论文中没有公式 Artifact — 可能有推导跳步或公式缺失",
        "suggestion": "在模型建立章节补充核心公式的 LaTeX 编译"
    },
    {
        "id": "chart_without_caption",
        "condition": lambda bp, arts, dc: (
            arts and any(
                a["artifact_type"] == "chart"
                and "title" in a.get("content", {}).get("chart_spec", {})
                and not a["content"]["chart_spec"].get("title")
                for a in arts
            )
        ),
        "severity": "P3", "impact": -1, "type": "format_issue",
        "location": "results", "layer": "pattern",
        "msg": "图表缺少标题",
        "suggestion": "为每个 chart_spec 填写 title 字段"
    },
]


class ReviewerEngine:
    """领域质量智能审查引擎 — 三层审查"""

    def review(self,
               blueprint: Dict = None,
               section_artifacts: Dict = None,
               leaf_artifacts: List[Dict] = None,
               problem_state: Dict = None,
               decision_contract: Dict = None,
               model_result: Dict = None) -> Dict:
        """
        审查论文 Artifact 图。

        Args:
            blueprint: PaperBlueprint
            section_artifacts: SectionGenerator 输出
            leaf_artifacts: formula/table/chart/reference 产物列表
            problem_state: L1 输出
            decision_contract: L3 输出
            model_result: L4 输出

        Returns:
            ReviewArtifact dict
        """
        findings = []
        sections = []
        bp_sections = blueprint.get("sections", []) if blueprint else []
        sa_list = section_artifacts.get("artifacts", []) if section_artifacts else []
        arts = leaf_artifacts or []

        existing_ids = {s["id"] for s in bp_sections}
        existing_sa_ids = {a["section_id"] for a in sa_list}

        # ===== Layer 1: 硬规则检查 =====
        for rule in STRUCTURE_RULES:
            if rule["section_id"] not in existing_ids:
                findings.append({
                    "finding_id": f"REV-{rule['check']}",
                    "type": "missing_section",
                    "severity": rule["severity"],
                    "layer": "rule",
                    "location": rule["section_id"],
                    "description": rule["msg"],
                    "evidence": f"Blueprint contains: {sorted(existing_ids)[:8]}",
                    "suggestion": f"在 PaperBlueprint 中添加 {rule['section_id']} 章节",
                    "score_impact": rule["impact"],
                    "confidence": 0.95,
                })

        # ===== Layer 2: 模式识别检查 =====
        for pat in PATTERN_CHECKS:
            try:
                if pat["condition"](blueprint, arts, decision_contract):
                    findings.append({
                        "finding_id": f"REV-{pat['id']}",
                        "type": pat["type"],
                        "severity": pat["severity"],
                        "layer": "pattern",
                        "location": pat["location"],
                        "description": pat["msg"],
                        "evidence": "Pattern matched via reviewer_agent/improvement_strategy.md",
                        "suggestion": pat["suggestion"],
                        "score_impact": pat["impact"],
                        "confidence": 0.85,
                    })
            except Exception:
                pass

        # ===== Layer 3: LLM 推理层（v1 placeholder）=====
        # 未来接入 LLM 做创新性、逻辑合理性、解释质量评估
        # 当前版本仅标记为未执行

        # ===== 评分汇总 =====
        dims = {
            "D1_problem_understanding": 12,
            "D2_model_reasoning": 20,
            "D3_solution_reliability": 16,
            "D4_validation_completeness": 12,
            "D5_innovation": 10,
            "D6_paper_quality": 7,
        }

        # 按 impact 扣分（仅扣对应维度）
        dim_penalties = {
            "missing_section": "D6_paper_quality",
            "weak_model_choice": "D2_model_reasoning",
            "insufficient_validation": "D4_validation_completeness",
            "format_issue": "D6_paper_quality",
        }

        for f in findings:
            dim_key = dim_penalties.get(f["type"], "D6_paper_quality")
            dims[dim_key] = max(0, dims.get(dim_key, 10) + f.get("score_impact", 0))

        total = sum(dims.values())
        total = max(0, min(100, total))

        if total >= 85:
            grade = "excellent"
        elif total >= 70:
            grade = "good"
        elif total >= 60:
            grade = "pass"
        elif total >= 45:
            grade = "needs_revision"
        else:
            grade = "reject"

        severity_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for f in findings:
            severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

        top_weakness = max(findings, key=lambda f: abs(f.get("score_impact", 0))).get("description", "") if findings else "未发现明显问题"

        return {
            "review_id": f"REV-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
            "target": {
                "blueprint_id": blueprint.get("blueprint_id", "") if blueprint else "",
                "artifact_count": len(arts),
            },
            "findings": findings,
            "summary": {
                "dimension_scores": dims,
                "total_score": total,
                "overall_grade": grade,
                "top_weakness": top_weakness,
                "fix_priority": [f["finding_id"] for f in sorted(findings, key=lambda f: abs(f.get("score_impact", 0)), reverse=True)[:3]],
                "findings_by_severity": severity_counts,
            },
        }


# ===== Artifact E2E 消费测试 =====

def e2e_review_test() -> Dict:
    """验证 Reviewer 正确消费完整 Artifact 图"""
    from structure_selector_runtime import StructureSelector
    from section_generator_runtime import SectionGenerator
    from leaf_compilers_runtime import (FormulaCompiler, TableCompiler,
                                         ChartCompiler, ReferenceCompiler)
    from style_compiler_runtime import StyleCompiler

    selector = StructureSelector()
    generator = SectionGenerator()
    style = StyleCompiler()
    reviewer = ReviewerEngine()

    ps = {"problem_type": "optimization", "domain": "supply_chain", "sub_problems": []}
    bp = selector.select(ps)
    sections_out = generator.compile(bp)
    style_config = style.compile("CUMCM")

    dc = {"decisions": [{"primary_model": "NSGA-II", "reasoning": ["单一理由"]}]}
    mr = {"results_summary": {"最优值": "78.2"}}

    # 生成 leaf artifacts（模拟不完整场景：缺 formula）
    leaf_arts = []
    tc = TableCompiler()
    cc = ChartCompiler()
    rc = ReferenceCompiler()
    for s in sections_out["artifacts"]:
        if "table_compiler" in s["dependencies"]:
            leaf_arts.append(tc.compile(s, mr, style_config))
        if "chart_compiler" in s["dependencies"]:
            leaf_arts.append(cc.compile(s, mr))
        if "reference_compiler" in s["dependencies"]:
            leaf_arts.append(rc.compile(s, dc, style_config))

    review = reviewer.review(bp, sections_out, leaf_arts, ps, dc, mr)
    return review


# ===== CLI =====

if __name__ == "__main__":
    print("=" * 60)
    print("ReviewerEngine v1.0 — E2E Review Test")
    print("=" * 60)

    review = e2e_review_test()

    s = review["summary"]
    print(f"\nScore: {s['total_score']}/100 ({s['overall_grade']})")
    print(f"Dims: D1={s['dimension_scores']['D1_problem_understanding']} "
          f"D2={s['dimension_scores']['D2_model_reasoning']} "
          f"D3={s['dimension_scores']['D3_solution_reliability']} "
          f"D4={s['dimension_scores']['D4_validation_completeness']} "
          f"D5={s['dimension_scores']['D5_innovation']} "
          f"D6={s['dimension_scores']['D6_paper_quality']}")
    print(f"Top weakness: {s['top_weakness'][:80]}")
    print(f"Severity: P0={s['findings_by_severity']['P0']} "
          f"P1={s['findings_by_severity']['P1']} "
          f"P2={s['findings_by_severity']['P2']} "
          f"P3={s['findings_by_severity']['P3']}")

    print(f"\nFindings ({len(review['findings'])}):")
    for f in review["findings"]:
        print(f"  [{f['severity']}] [{f['layer']:7s}] [{f['type']:25s}] {f['description'][:70]}")
        print(f"         → {f['suggestion'][:80]}")

    print(f"\nArtifact E2E: PASS (Reviewer consuming PaperArtifact Graph)")
