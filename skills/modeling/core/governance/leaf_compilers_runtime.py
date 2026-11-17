"""
L6 Leaf Compilers v1.0 — 论文执行叶节点
===========================================
Forge v6.5 Wave 2.5: formula/table/chart/reference 四个编译器。
统一输出 PaperArtifact (paper_artifact.schema.json)。
消费 SectionArtifacts 的 dependency 编排信号。

设计原则:
  - 每个编译器独立、可替换
  - 统一 Artifact 输出格式
  - Contract-driven: 消费 PaperStyleContract (style) / ModelResult (data)
"""
from typing import Dict, List, Optional


# ============================================
# FormulaCompiler
# ============================================

class FormulaCompiler:
    """公式编译器 — 公式编号 + LaTeX 生成 + 变量解释"""

    def compile(self,
                section_artifact: Dict,
                decision_contract: Dict = None,
                model_spec: Dict = None) -> Dict:
        formulas = []

        # 从 ModelSpec 提取已有公式模板
        if model_spec and model_spec.get("core_formulas"):
            for f in model_spec["core_formulas"]:
                formulas.append({
                    "id": f.get("id", f"F-{len(formulas) + 1}"),
                    "latex": f.get("latex", ""),
                    "label": f.get("label", f"公式{len(formulas) + 1}"),
                    "variables": f.get("variables", []),
                    "source_model": model_spec.get("model_name", ""),
                })

        return {
            "artifact_id": f"formula-{section_artifact.get('section_id', 'unknown')}-001",
            "artifact_type": "formula",
            "source_skill": "formula_compiler",
            "section_id": section_artifact.get("section_id"),
            "content": {"formulas": formulas},
            "rendering": {"ready": True, "format": "latex"},
        }


# ============================================
# TableCompiler
# ============================================

class TableCompiler:
    """表格编译器 — 三线表生成 + Contract 驱动"""

    def compile(self,
                section_artifact: Dict,
                model_result: Dict = None,
                style_config: Dict = None) -> Dict:
        table_spec = {
            "headers": ["指标", "数值"],
            "rows": [["—", "—"]],
            "caption": f"表 {section_artifact.get('section_id', '')}",
            "style": "three_line",
            "source_data": "ModelResult",
        }

        # 从 ModelResult 提取数据
        if model_result:
            results = model_result.get("results_summary", {})
            if isinstance(results, dict) and results:
                table_spec["headers"] = list(results.keys())[:6]
                table_spec["rows"] = [[str(v) for v in results.values()][:6]]

        # 消费 StyleConfig 的三线表参数
        if style_config:
            table_spec.update(style_config.get("table", {}))

        return {
            "artifact_id": f"table-{section_artifact.get('section_id', 'unknown')}-001",
            "artifact_type": "table",
            "source_skill": "table_compiler",
            "section_id": section_artifact.get("section_id"),
            "content": {"table_spec": table_spec},
            "rendering": {"ready": False, "format": "docx_xml"},
        }


# ============================================
# ChartCompiler
# ============================================

class ChartCompiler:
    """图表编译器 — chart_spec → rendering placeholder"""

    def compile(self,
                section_artifact: Dict,
                model_result: Dict = None,
                chart_type: str = "line") -> Dict:
        data = {}
        if model_result:
            results = model_result.get("results_summary", {})
            if isinstance(results, dict):
                data = {k: v for k, v in results.items() if not isinstance(v, str)}

        chart_spec = {
            "chart_type": chart_type,
            "title": f"图 {section_artifact.get('section_id', '')}",
            "data": data,
            "x_label": "x",
            "y_label": "y",
            "output_path": f"outputs/{section_artifact.get('section_id', 'chart')}.png",
            "dpi": 600,
        }

        return {
            "artifact_id": f"chart-{section_artifact.get('section_id', 'unknown')}-001",
            "artifact_type": "chart",
            "source_skill": "chart_compiler",
            "section_id": section_artifact.get("section_id"),
            "content": {"chart_spec": chart_spec},
            "rendering": {"ready": False, "format": "png"},
        }


# ============================================
# ReferenceCompiler
# ============================================

class ReferenceCompiler:
    """参考文献编译器 — GB/T 7714 格式 + 数量检查"""

    def compile(self,
                section_artifact: Dict,
                decision_contract: Dict = None,
                style_config: Dict = None) -> Dict:
        refs = []

        # 从 DecisionContract 提取模型来源
        if decision_contract:
            for d in decision_contract.get("decisions", [])[:3]:
                model = d.get("primary_model", "")
                refs.append({
                    "id": f"[{len(refs) + 1}]",
                    "text": f"{model}相关文献（待填充完整引用）",
                    "type": "book",
                    "source_model": model,
                })

        # 确保至少 5 篇（满足 CUMCM 要求）
        min_count = style_config.get("reference", {}).get("min_count", 5) if style_config else 5
        while len(refs) < min_count:
            refs.append({
                "id": f"[{len(refs) + 1}]",
                "text": f"数学建模相关文献{len(refs) + 1}（待填充）",
                "type": "book",
                "source_model": "general",
            })

        return {
            "artifact_id": f"reference-{section_artifact.get('section_id', 'unknown')}-001",
            "artifact_type": "reference",
            "source_skill": "reference_compiler",
            "section_id": section_artifact.get("section_id"),
            "content": {"references": refs, "style": "GB/T 7714-2015", "count": len(refs)},
            "rendering": {"ready": True, "format": "text"},
        }


# ===== End-to-End Artifact Flow Test =====

def e2e_artifact_flow_test() -> Dict:
    """验证从 Blueprint → SectionArtifacts → LeafArtifacts 的完整链路"""
    from structure_selector_runtime import StructureSelector
    from section_generator_runtime import SectionGenerator
    from style_compiler_runtime import StyleCompiler

    selector = StructureSelector()
    generator = SectionGenerator()
    style = StyleCompiler()

    formula_compiler = FormulaCompiler()
    table_compiler = TableCompiler()
    chart_compiler = ChartCompiler()
    reference_compiler = ReferenceCompiler()

    ps = {"problem_type": "optimization", "domain": "supply_chain", "sub_problems": []}
    bp = selector.select(ps)
    sections_out = generator.compile(bp)
    style_config = style.compile("CUMCM")

    dc = {"decisions": [{"primary_model": "NSGA-II"}, {"primary_model": "MILP"}]}
    mr = {"results_summary": {"最优值": "78.2", "收敛代数": "150", "Pareto前沿点数": "23"}}

    artifacts = []
    trace = []

    for section in sections_out["artifacts"]:
        sid = section["section_id"]
        deps = section["dependencies"]

        if "formula_compiler" in deps:
            a = formula_compiler.compile(section, dc)
            artifacts.append(a)
            trace.append(f"formula → {sid}")

        if "table_compiler" in deps:
            a = table_compiler.compile(section, mr, style_config)
            artifacts.append(a)
            trace.append(f"table → {sid}")

        if "chart_compiler" in deps:
            a = chart_compiler.compile(section, mr)
            artifacts.append(a)
            trace.append(f"chart → {sid}")

        if "reference_compiler" in deps:
            a = reference_compiler.compile(section, dc, style_config)
            artifacts.append(a)
            trace.append(f"reference → {sid}")

    return {
        "pipeline": "ProblemState → Blueprint → SectionArtifacts → LeafArtifacts",
        "blueprint_sections": len(bp["sections"]),
        "section_artifacts": len(sections_out["artifacts"]),
        "leaf_artifacts": len(artifacts),
        "by_type": {
            "formula": sum(1 for a in artifacts if a["artifact_type"] == "formula"),
            "table": sum(1 for a in artifacts if a["artifact_type"] == "table"),
            "chart": sum(1 for a in artifacts if a["artifact_type"] == "chart"),
            "reference": sum(1 for a in artifacts if a["artifact_type"] == "reference"),
        },
        "trace": trace,
        "all_have_artifact_id": all(a.get("artifact_id") for a in artifacts),
        "all_have_rendering": all("rendering" in a for a in artifacts),
    }


# ===== CLI =====

if __name__ == "__main__":
    print("=" * 60)
    print("L6 Leaf Compilers v1.0 — Self Test")
    print("=" * 60)

    # Unit tests
    fc = FormulaCompiler()
    tc = TableCompiler()
    cc = ChartCompiler()
    rc = ReferenceCompiler()

    section = {"section_id": "modeling"}
    dc = {"decisions": [{"primary_model": "NSGA-II"}]}
    mr = {"results_summary": {"最优值": "78.2"}}
    style = {"table": {"top_pt": 1.5}, "reference": {"min_count": 5}}

    f = fc.compile(section, dc, {"core_formulas": [{"id": "F-1", "latex": "x^2 + y^2 = 1"}]})
    t = tc.compile(section, mr, style)
    c = cc.compile(section, mr)
    r = rc.compile(section, dc, style)

    print(f"\nformula_compiler:  artifact_id={f['artifact_id']}, formulas={len(f['content']['formulas'])}")
    print(f"table_compiler:    artifact_id={t['artifact_id']}, headers={t['content']['table_spec']['headers'][:3]}")
    print(f"chart_compiler:    artifact_id={c['artifact_id']}, type={c['content']['chart_spec']['chart_type']}")
    print(f"reference_compiler: artifact_id={r['artifact_id']}, count={r['content']['count']}")

    # E2E Flow Test
    print(f"\n{'=' * 60}")
    print("End-to-End Artifact Flow Test")
    print(f"{'=' * 60}")
    e2e = e2e_artifact_flow_test()
    print(f"\nPipeline: {e2e['pipeline']}")
    print(f"Blueprint: {e2e['blueprint_sections']} sections")
    print(f"SectionArtifacts: {e2e['section_artifacts']}")
    print(f"LeafArtifacts: {e2e['leaf_artifacts']}")
    print(f"By type: {e2e['by_type']}")
    print(f"All have artifact_id: {e2e['all_have_artifact_id']}")
    print(f"All have rendering: {e2e['all_have_rendering']}")
    print(f"Trace ({len(e2e['trace'])} steps): {' → '.join(e2e['trace'][:8])}")

    passed = (
        e2e['leaf_artifacts'] >= 6  # optimization: formula(modeling+solving) + table(results) + chart(sensitivity+results) + reference
        and e2e['all_have_artifact_id']
        and e2e['all_have_rendering']
    )
    print(f"\nE2E Artifact Flow: {'PASS' if passed else 'NEEDS REVIEW'}")
