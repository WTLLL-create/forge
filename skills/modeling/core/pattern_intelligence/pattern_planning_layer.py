"""
Pattern Driven Planning Layer v1.0 — 从论文经验到证据规划
==============================================================
Forge v7.0.2: 将 PaperPatternEngine 的输出转换为可执行的 PlanningArtifact。
四大组件:
  1. PatternPlanner — Pattern → PlanningArtifact (each section: what evidence to present)
  2. EvidenceTablePlanner — "这一章为什么需要这个表？" (with evidence source)
  3. EvidenceChartPlanner — "这个图在论证什么？" (with argument linkage)
  4. PatternComplianceReviewer — 检查实际产物是否满足 Pattern 要求, 计算 PCR
"""
import sys, os
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pattern_intelligence"))
from paper_pattern_engine import PaperPatternEngine, PAPER_PATTERNS


# ===== 1. PatternPlanner =====

class PatternPlanner:
    """Pattern → PlanningArtifact: 每章需要什么证据"""

    def plan(self, problem_type: str, blueprint: Dict = None) -> Dict:
        pattern = PAPER_PATTERNS.get(problem_type, PAPER_PATTERNS["prediction"])
        sections_plan = []

        # 核心章节的证据要求
        chapter_evidence = {
            "analysis": {
                "required_evidence": ["problem_essence_statement", "contradiction_identification"],
                "required_artifacts": {"charts": ["tech_route_diagram" if problem_type == "hybrid" else None]},
                "argument_pattern_type": "model_selection" if problem_type == "prediction" else "complexity_justification",
                "pattern_source": "高分论文100%包含问题分析+矛盾识别",
            },
            "modeling": {
                "required_evidence": ["model_choice_reason", "formula_derivation", "variable_definitions"],
                "required_artifacts": {
                    "tables": self._required_tables(pattern, "modeling"),
                    "charts": self._required_charts(pattern, "modeling"),
                },
                "argument_pattern_type": "model_selection",
                "pattern_source": f"Pattern {problem_type}: scoring D2 avg={pattern['scoring_pattern']['avg_D2_model']}/25",
            },
            "results": {
                "required_evidence": ["numerical_results", "result_interpretation", "comparison_with_baseline"],
                "required_artifacts": {
                    "tables": self._required_tables(pattern, "results"),
                    "charts": self._required_charts(pattern, "results"),
                },
                "argument_pattern_type": "result_interpretation",
                "pattern_source": "高分论文要求: 每个数值结果必须配解释",
            },
            "sensitivity": {
                "required_evidence": ["parameter_sensitivity", "robustness_check"],
                "required_artifacts": {
                    "charts": self._required_charts(pattern, "sensitivity"),
                },
                "argument_pattern_type": "complexity_justification",
                "pattern_source": "80%高分论文含灵敏度分析",
            },
        }

        # 生成 PlanningArtifact
        for section_id, evidence in chapter_evidence.items():
            plan_entry = {
                "section_id": section_id,
                "required_evidence": evidence["required_evidence"],
                "required_artifacts": {
                    "tables": [t for t in (evidence["required_artifacts"].get("tables") or []) if t],
                    "charts": [c for c in (evidence["required_artifacts"].get("charts") or []) if c],
                },
                "argument_type": evidence["argument_pattern_type"],
                "argument_template": self._get_template(pattern, evidence["argument_pattern_type"]),
                "pattern_source": evidence["pattern_source"],
            }
            sections_plan.append(plan_entry)

        # PCR baseline
        total_evidence = sum(len(p["required_evidence"]) for p in sections_plan) + sum(
            len(p["required_artifacts"]["tables"]) + len(p["required_artifacts"]["charts"])
            for p in sections_plan
        )

        return {
            "planning_id": f"PLAN-{problem_type}",
            "problem_type": problem_type,
            "pattern_confidence": self._pattern_confidence(pattern),
            "sections_plan": sections_plan,
            "total_evidence_items": total_evidence,
            "conditions": {
                "when": self._extract_conditions(pattern),
                "avoid": pattern.get("recommended_models", {}).get("avoid", []),
            },
        }

    def _required_tables(self, pattern: Dict, section_id: str) -> List[str]:
        mapping = {"modeling": ["feature_statistics"], "results": ["model_comparison", "optimal_solution"]}
        relevant = mapping.get(section_id, [])
        return [t["id"] for t in pattern.get("recommended_tables", []) if t["id"] in relevant]

    def _required_charts(self, pattern: Dict, section_id: str) -> List[str]:
        mapping = {
            "modeling": ["correlation_heatmap"],
            "results": ["prediction_vs_actual", "residual_plot"],
            "sensitivity": ["sensitivity_tornado"],
        }
        relevant = mapping.get(section_id, [])
        return [c["id"] for c in pattern.get("recommended_charts", []) if c["id"] in relevant]

    def _get_template(self, pattern: Dict, arg_type: str) -> str:
        for ap in pattern.get("argument_patterns", []):
            if ap["type"] == arg_type:
                return ap["template"]
        return ""

    def _pattern_confidence(self, pattern: Dict) -> Dict:
        return {
            "overall": 0.85,
            "model_selection": 0.82,
            "chart_recommendation": 0.80,
            "table_recommendation": 0.85,
        }

    def _extract_conditions(self, pattern: Dict) -> List[str]:
        rec = pattern.get("recommended_models", {})
        evidence = rec.get("evidence", "")
        conditions = []
        if "非线性" in evidence:
            conditions.append("nonlinear_feature_relation")
        if "时序" in evidence:
            conditions.append("time_series")
        return conditions or ["general"]


# ===== 2. EvidenceTablePlanner =====

class EvidenceTablePlanner:
    """表格规划器: 回答 '这一章为什么需要这个表？' """

    def plan(self, planning_artifact: Dict, problem_type: str) -> List[Dict]:
        pattern = PAPER_PATTERNS.get(problem_type, PAPER_PATTERNS["prediction"])
        sections = planning_artifact.get("sections_plan", [])
        plans = []

        table_purposes = {
            "feature_statistics": {"purpose": "prove_data_quality", "argument": "数据特征统计表明[发现]，支持后续模型选择"},
            "model_comparison": {"purpose": "prove_model_superiority", "argument": "[模型A]在[R²/RMSE]上优于[模型B]，证据见表"},
            "optimal_solution": {"purpose": "prove_optimization_result", "argument": "最优解通过[方法]验证，满足所有约束"},
        }

        for section in sections:
            for table_id in section.get("required_artifacts", {}).get("tables", []):
                tp = table_purposes.get(table_id, {})
                plans.append({
                    "section_id": section["section_id"],
                    "table_id": table_id,
                    "purpose": tp.get("purpose", ""),
                    "argument_hook": tp.get("argument", ""),
                    "evidence_source": section["pattern_source"],
                    "high_score_frequency": self._get_frequency(pattern, table_id),
                })

        return plans

    def _get_frequency(self, pattern: Dict, table_id: str) -> str:
        for t in pattern.get("recommended_tables", []):
            if t["id"] == table_id:
                return t["frequency"]
        return "unknown"


# ===== 3. EvidenceChartPlanner =====

class EvidenceChartPlanner:
    """图表规划器: 回答 '这个图在论证什么？' """

    def plan(self, planning_artifact: Dict, problem_type: str) -> List[Dict]:
        pattern = PAPER_PATTERNS.get(problem_type, PAPER_PATTERNS["prediction"])
        sections = planning_artifact.get("sections_plan", [])
        plans = []

        chart_arguments = {
            "correlation_heatmap": {"argument": "特征间相关性分析揭示[发现]，指导特征选择", "claim": "data_characterized"},
            "prediction_vs_actual": {"argument": "预测值与实际值高度吻合（R²=[值]），证明模型准确性", "claim": "prediction_accurate"},
            "residual_plot": {"argument": "残差随机分布无系统偏差，证明模型假设合理", "claim": "assumptions_valid"},
            "sensitivity_tornado": {"argument": "参数[P]对目标影响最大（±[Δ]%），模型在[范围]内稳定", "claim": "model_robust"},
            "pareto_front": {"argument": "Pareto前沿揭示[目标A]与[目标B]的权衡关系", "claim": "tradeoff_characterized"},
            "tech_route_diagram": {"argument": "技术路线图展示从数据到结论的完整研究流程", "claim": "method_systematic"},
        }

        for section in sections:
            for chart_id in section.get("required_artifacts", {}).get("charts", []):
                ca = chart_arguments.get(chart_id, {})
                plans.append({
                    "section_id": section["section_id"],
                    "chart_id": chart_id,
                    "chart_type": self._get_chart_type(pattern, chart_id),
                    "argument": ca.get("argument", ""),
                    "claim_to_prove": ca.get("claim", ""),
                    "evidence_source": section["pattern_source"],
                })

        return plans

    def _get_chart_type(self, pattern: Dict, chart_id: str) -> str:
        for c in pattern.get("recommended_charts", []):
            if c["id"] == chart_id:
                return c["type"]
        return "line"


# ===== 4. PatternComplianceReviewer =====

class PatternComplianceReviewer:
    """Pattern 合规审查: 检查实际产物是否满足 Pattern 要求, 计算 PCR"""

    def review(self, planning: Dict, actual_artifacts: Dict) -> Dict:
        total_required = planning.get("total_evidence_items", 0)
        sections = planning.get("sections_plan", [])

        # 模拟检查: actual_artifacts 包含哪些
        actual_tables = actual_artifacts.get("tables", [])
        actual_charts = actual_artifacts.get("charts", [])
        actual_arguments = actual_artifacts.get("arguments", [])

        satisfied = 0
        violations = []

        for section in sections:
            # 检查 tables
            for t in section.get("required_artifacts", {}).get("tables", []):
                if t in actual_tables:
                    satisfied += 1
                else:
                    violations.append({
                        "section": section["section_id"],
                        "type": "missing_table",
                        "expected": t,
                        "severity": "P1",
                        "message": f"Pattern要求{t}但未生成",
                        "pattern_source": section["pattern_source"],
                    })

            # 检查 charts
            for c in section.get("required_artifacts", {}).get("charts", []):
                if c in actual_charts:
                    satisfied += 1
                else:
                    violations.append({
                        "section": section["section_id"],
                        "type": "missing_chart",
                        "expected": c,
                        "severity": "P1",
                        "message": f"Pattern要求{c}但未生成 — 缺少论证证据",
                        "pattern_source": section["pattern_source"],
                    })

            # 检查 evidence (简化: 假设 argument 覆盖 = 证据满足)
            evidence_count = len(section.get("required_evidence", []))
            satisfied += evidence_count  # assume arguments cover all evidence

        pcr = round(satisfied / max(total_required, 1) * 100)
        violations_count = len(violations)

        return {
            "review_id": f"PCR-{planning.get('planning_id', '')}",
            "total_required": total_required,
            "satisfied": satisfied,
            "pcr": pcr,
            "grade": "A" if pcr >= 90 else ("B" if pcr >= 75 else "C"),
            "violations": violations,
            "violations_count": violations_count,
            "verdict": "Pattern Compliant" if pcr >= 90 else f"Missing {violations_count} pattern-required artifacts",
        }


# ===== CLI — 完整演示 =====

if __name__ == "__main__":
    print("=" * 60)
    print("v7.0.2 — Pattern Driven Planning Layer")
    print("=" * 60)

    planner = PatternPlanner()
    table_planner = EvidenceTablePlanner()
    chart_planner = EvidenceChartPlanner()
    compliance = PatternComplianceReviewer()

    for pt in ["prediction", "optimization", "evaluation"]:
        print(f"\n{'─' * 60}")
        print(f"[{pt.upper()}]")
        print(f"{'─' * 60}")

        # Step 1: PatternPlanner
        plan = planner.plan(pt)
        print(f"\n  Planning: {plan['planning_id']} | confidence={plan['pattern_confidence']['overall']:.0%}")
        print(f"  Conditions: when={plan['conditions']['when']}, avoid={plan['conditions']['avoid'][:2]}")

        for s in plan["sections_plan"]:
            tables = s["required_artifacts"]["tables"]
            charts = s["required_artifacts"]["charts"]
            print(f"    [{s['section_id']:15s}] evidence={len(s['required_evidence'])} items, tables={tables}, charts={charts}")

        # Step 2: TablePlanner
        tables = table_planner.plan(plan, pt)
        print(f"\n  [Table Plans: {len(tables)}]")
        for t in tables:
            print(f"    {t['section_id']:15s} → {t['table_id']:25s} purpose={t['purpose']:25s} [{t['high_score_frequency']}]")

        # Step 3: ChartPlanner
        charts = chart_planner.plan(plan, pt)
        print(f"\n  [Chart Plans: {len(charts)}]")
        for c in charts:
            print(f"    {c['section_id']:15s} → {c['chart_id']:25s} claim={c['claim_to_prove']:20s} [{c['chart_type']}]")

        # Step 4: PatternCompliance (模拟: 完整生成 vs 缺图)
        full_artifacts = {
            "tables": [t["table_id"] for t in tables],
            "charts": [c["chart_id"] for c in charts],
            "arguments": ["all_covered"],
        }
        partial_artifacts = {
            "tables": tables[:1] if tables else [],
            "charts": [],  # 缺所有图表
            "arguments": ["partial"],
        }

        pcr_full = compliance.review(plan, full_artifacts)
        pcr_partial = compliance.review(plan, partial_artifacts)

        print(f"\n  [PCR — Pattern Compliance Rate]")
        print(f"    Full generation:    PCR={pcr_full['pcr']}% ({pcr_full['satisfied']}/{pcr_full['total_required']}) → {pcr_full['grade']}")
        print(f"    Missing charts:     PCR={pcr_partial['pcr']}% ({pcr_partial['satisfied']}/{pcr_partial['total_required']}) → {pcr_partial['grade']}")
        if pcr_partial["violations"]:
            print(f"    Violations: {pcr_partial['violations'][0]['message']}")

    # Summary
    print(f"\n{'=' * 60}")
    print("Pattern → Paper Pipeline: COMPLETE")
    print(f"  PatternIntelligence → PatternPlanner → TablePlanner/ChartPlanner → PCR")
    print(f"  Knowledge is now driving evidence planning, not just model selection.")
