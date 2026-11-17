"""
SectionGenerator v1.0 — 章节编排器（非内容生成器）
=====================================================
Forge v6.5 Wave 2.4: L6 内容编排节点。
消费 PaperBlueprint + Contracts → 输出 SectionArtifact 列表。

原则:
  - 不生成章节文本 → 那是 formula/table/chart/reference compilers 的工作
  - 负责「章节组织和内容槽位生成」→ 编排 downstream skills
  - 110行规则映射为 SectionRuleRegistry，不是 500行 if-else
"""
from typing import Dict, List, Optional


# 章节规则注册表（来自 section_generation_rules.md）
SECTION_RULES = {
    "abstract": {
        "title": "摘要",
        "purpose": "全篇浓缩：问题→方法→结果→创新，30秒决定评委是否继续读",
        "required_blocks": ["problem_statement", "method_summary", "core_results", "innovation", "significance"],
        "dependencies": ["abstract_compiler"],
        "validation": {"word_count": (700, 1000), "no_formulas": True, "no_citations": True},
    },
    "restatement": {
        "title": "问题重述",
        "purpose": "用自己的话重新表述问题，不是照抄题目原文",
        "required_blocks": ["background", "problem_statement", "sub_problems"],
        "dependencies": [],
        "validation": {"max_copy_rate": 0.30},
    },
    "analysis": {
        "title": "问题分析",
        "purpose": "把评委从'知道题目'带到'理解你为什么这样研究'",
        "required_blocks": ["core_contradiction", "mathematical_essence", "traditional_method_limits", "research_strategy", "tech_route_diagram"],
        "dependencies": ["argument_compiler", "contradiction_finder"],
        "validation": {"require_flowchart": True, "require_contradiction": True},
    },
    "assumptions": {
        "title": "模型假设",
        "purpose": "列出假设 + 每条的理由、验证、影响",
        "required_blocks": ["assumption_list"],
        "dependencies": ["model_specification"],
        "validation": {"min_assumptions": 5, "max_assumptions": 8, "require_justification": True},
    },
    "symbols": {
        "title": "符号说明",
        "purpose": "全局符号表，三线表格式",
        "required_blocks": ["symbol_table"],
        "dependencies": ["model_specification"],
        "validation": {"require_table_format": "three_line", "require_grouping": True},
    },
    "data_preprocessing": {
        "title": "数据预处理",
        "purpose": "数据清洗、缺失值处理、特征工程",
        "required_blocks": ["data_source", "missing_values", "outliers", "feature_engineering"],
        "dependencies": [],
        "validation": {"require_chart": True, "require_reproducibility": True},
    },
    "indicator_system": {
        "title": "指标体系构建",
        "purpose": "维度分解 + 指标选择 + 赋权方法",
        "required_blocks": ["dimensions", "indicator_selection", "weighting_method"],
        "dependencies": [],
        "validation": {"min_dimensions": 3, "require_table": True},
    },
    "modeling": {
        "title": "模型建立",
        "purpose": "为什么这个模型 + 公式推导 + 符号统一",
        "required_blocks": ["model_choice_reason", "variable_definitions", "core_formulas", "constraint_explanation"],
        "dependencies": ["argument_compiler", "model_specification", "formula_compiler"],
        "validation": {"require_numbered_formulas": True, "require_explanation": True},
    },
    "solving": {
        "title": "模型求解",
        "purpose": "算法步骤 + 参数选择 + 收敛性",
        "required_blocks": ["algorithm_description", "parameter_settings", "convergence_analysis"],
        "dependencies": [],
        "validation": {"require_algorithm_flowchart": True},
    },
    "results": {
        "title": "结果分析",
        "purpose": "结果→解释→对比→洞察",
        "required_blocks": ["numerical_results", "visualization", "interpretation", "comparison"],
        "dependencies": ["chart_compiler", "table_compiler"],
        "validation": {"require_charts": True, "require_tables": True, "require_quantitative": True},
    },
    "sensitivity": {
        "title": "灵敏度分析",
        "purpose": "参数变化对最优解的影响",
        "required_blocks": ["parameter_range", "sensitivity_chart", "interpretation"],
        "dependencies": ["chart_compiler"],
        "validation": {"require_chart": True, "require_quantitative": True},
    },
    "model_comparison": {
        "title": "模型对比",
        "purpose": "多模型性能对比表",
        "required_blocks": ["comparison_table", "performance_metrics", "best_model_selection"],
        "dependencies": ["table_compiler", "argument_compiler"],
        "validation": {"require_table": True, "require_metrics": True},
    },
    "robustness": {
        "title": "稳健性检验",
        "purpose": "灵敏度分析 + 对比验证",
        "required_blocks": ["robustness_test", "alternative_methods", "result_stability"],
        "dependencies": ["chart_compiler"],
        "validation": {"require_chart": True},
    },
    "tech_route": {
        "title": "技术路线",
        "purpose": "分治策略 + 整体技术路线图",
        "required_blocks": ["strategy_description", "route_diagram"],
        "dependencies": [],
        "validation": {"require_diagram": True},
    },
    "modeling_and_solving": {
        "title": "模型建立与求解",
        "purpose": "简单题的模型+求解合并章",
        "required_blocks": ["model_choice_reason", "core_formulas", "algorithm_description", "numerical_results"],
        "dependencies": ["argument_compiler", "model_specification", "formula_compiler", "chart_compiler"],
        "validation": {"require_numbered_formulas": True, "require_algorithm": True},
    },
    "evaluation": {
        "title": "模型评价与推广",
        "purpose": "优点+缺点+改进方向",
        "required_blocks": ["advantages", "limitations", "future_work"],
        "dependencies": [],
        "validation": {"require_balanced": True},
    },
    "references": {
        "title": "参考文献",
        "purpose": "GB/T 7714 格式",
        "required_blocks": ["reference_list"],
        "dependencies": ["reference_compiler"],
        "validation": {"min_count": 5, "require_format": "GB/T 7714-2015"},
    },
}


class SectionGenerator:
    """章节编排器 — 不生成文本，只编排 downstream skills"""

    def compile(self,
                blueprint: Dict,
                problem_state: Dict = None,
                decision_contract: Dict = None,
                model_result: Dict = None) -> List[Dict]:
        """
        编译论文的所有章节工件。

        Args:
            blueprint: StructureSelector.select() 的输出 (PaperBlueprint)
            problem_state: L1 ProblemState
            decision_contract: L3 DecisionContract
            model_result: L4 ModelResult

        Returns:
            List[SectionArtifact]

        Raises:
            ValueError: 如果 paper_structure 未运行（无 Blueprint）
        """
        if not blueprint or "sections" not in blueprint:
            raise ValueError("SectionGenerator requires a PaperBlueprint from paper_structure. Run StructureSelector first.")

        sections = blueprint.get("sections", [])
        artifacts = []

        for section in sections:
            sid = section.get("id", "unknown")
            rule = SECTION_RULES.get(sid, {})
            if not rule:
                rule = self._derive_rule(section)

            # 展开子节
            sub_artifacts = []
            for sub in section.get("sub_sections", []):
                sub_artifacts.append({
                    "section_id": sub["id"],
                    "title": sub["title"],
                    "parent_section": sid,
                    "purpose": sub.get("info_task", ""),
                    "required_blocks": rule.get("required_blocks", []),
                    "dependencies": rule.get("dependencies", []),
                    "validation_rules": rule.get("validation", {}),
                    "contract_inputs": self._infer_inputs(sid, problem_state, decision_contract, model_result),
                })

            artifact = {
                "section_id": sid,
                "title": rule.get("title", section.get("title", sid)),
                "purpose": rule.get("purpose", section.get("info_task", "")),
                "mandatory": section.get("mandatory", True),
                "required_blocks": rule.get("required_blocks", []),
                "dependencies": rule.get("dependencies", []),
                "validation_rules": rule.get("validation", {}),
                "sub_artifacts": sub_artifacts if sub_artifacts else None,
                "contract_inputs": self._infer_inputs(sid, problem_state, decision_contract, model_result),
            }
            artifacts.append(artifact)

        # 校验完整性
        completeness = self._check_completeness(artifacts)

        return {
            "blueprint_id": blueprint.get("blueprint_id", "unknown"),
            "problem_type": blueprint.get("problem_type", "unknown"),
            "total_sections": len(artifacts),
            "mandatory_sections": sum(1 for a in artifacts if a["mandatory"]),
            "total_blocks": sum(len(a["required_blocks"]) for a in artifacts),
            "all_dependencies": list(set(dep for a in artifacts for dep in a["dependencies"])),
            "artifacts": artifacts,
            "completeness": completeness,
        }

    def _derive_rule(self, section: Dict) -> Dict:
        """为没有在 SECTION_RULES 中注册的章节推导基本规则"""
        return {
            "title": section.get("title", section.get("id", "")),
            "purpose": section.get("info_task", ""),
            "required_blocks": [],
            "dependencies": [],
            "validation": {},
        }

    def _infer_inputs(self, sid: str, ps: Dict, dc: Dict, mr: Dict) -> Dict:
        """根据章节类型推断所需的 contract 输入"""
        inputs = {}
        if ps and sid in ("abstract", "restatement", "analysis", "assumptions"):
            inputs["problem_state"] = True
        if dc and sid in ("modeling", "solving", "analysis"):
            inputs["decision_contract"] = True
        if mr and sid in ("results", "solving", "abstract"):
            inputs["model_result"] = True
        return inputs

    def _check_completeness(self, artifacts: List[Dict]) -> Dict:
        issues = []
        for a in artifacts:
            if a["mandatory"] and not a["required_blocks"]:
                issues.append(f"{a['section_id']}: mandatory section has no required_blocks")
            if a["mandatory"] and not a["dependencies"]:
                pass  # 不是所有章节都需要 dependency
        return {
            "all_mandatory_have_blocks": not any(
                a["mandatory"] and not a["required_blocks"] for a in artifacts
            ),
            "issues": issues,
        }


# ===== Blueprint Compatibility Test =====

def blueprint_compatibility_test(generator: SectionGenerator) -> Dict:
    """验证 SectionGenerator 正确消费 4 种 PaperBlueprint"""
    from structure_selector_runtime import StructureSelector

    selector = StructureSelector()
    results = {"total": 0, "passed": 0, "failures": []}

    cases = [
        ("optimization", {"problem_type": "optimization", "domain": "supply_chain", "sub_problems": []}),
        ("prediction",   {"problem_type": "prediction", "domain": "air_quality", "sub_problems": []}),
        ("evaluation",   {"problem_type": "evaluation", "domain": "education", "sub_problems": []}),
        ("hybrid",       {"problem_type": "hybrid", "domain": "industrial", "sub_problems": []}),
    ]

    for ptype, ps in cases:
        results["total"] += 1
        try:
            bp = selector.select(ps)
            output = generator.compile(bp)
            if output["total_sections"] >= 10:
                results["passed"] += 1
            else:
                results["failures"].append(f"{ptype}: only {output['total_sections']} sections")
        except Exception as e:
            results["failures"].append(f"{ptype}: {e}")

    results["all_pass"] = results["passed"] == results["total"]
    return results


# ===== Dependency Test =====

def dependency_test(generator: SectionGenerator):
    """验证 SectionGenerator 拒绝无 Blueprint 的调用"""
    try:
        generator.compile(None)
        return {"pass": False, "error": "Should have raised ValueError"}
    except ValueError as e:
        return {"pass": True, "reason": str(e)}


# ===== CLI =====

if __name__ == "__main__":
    from structure_selector_runtime import StructureSelector

    generator = SectionGenerator()
    selector = StructureSelector()

    # 测试 1: Optimization Blueprint
    print("=" * 60)
    print("SectionGenerator v1.0 — Blueprint Compatibility Test")
    print("=" * 60)

    for ptype, ps in [
        ("optimization", {"problem_type": "optimization", "domain": "supply_chain", "sub_problems": []}),
        ("prediction",   {"problem_type": "prediction",   "domain": "air_quality", "sub_problems": []}),
        ("evaluation",   {"problem_type": "evaluation",   "domain": "education", "sub_problems": []}),
        ("hybrid",       {"problem_type": "hybrid",       "domain": "industrial", "sub_problems": []}),
    ]:
        bp = selector.select(ps)
        out = generator.compile(bp)
        print(f"\n[{ptype}] {out['total_sections']} sections, {out['total_blocks']} blocks")
        print(f"  Dependencies: {out['all_dependencies']}")
        for a in out["artifacts"]:
            deps = a["dependencies"]
            dep_str = f" → needs [{', '.join(deps)}]" if deps else ""
            print(f"  {a['section_id']:25s} [{a['title']:12s}] {len(a['required_blocks'])} blocks{dep_str}")

    # Dependency Test
    print(f"\n{'=' * 60}")
    print("Dependency Test: rejects call without Blueprint")
    dt = dependency_test(generator)
    print(f"  {'PASS' if dt['pass'] else 'FAIL'}: {dt.get('reason', dt.get('error', ''))}")

    # Blueprint Compatibility
    print(f"\n{'=' * 60}")
    print("Blueprint Compatibility Test")
    bct = blueprint_compatibility_test(generator)
    print(f"  {bct['passed']}/{bct['total']} passed: {'ALL PASS' if bct['all_pass'] else 'FAILURES: ' + str(bct['failures'])}")
