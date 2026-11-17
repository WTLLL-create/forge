"""
StructureSelector v1.0 — 论文结构选择器
==========================================
Forge v6.5 Wave 2.3: L6 管线拓扑入口。
消费 ProblemState → 输出 PaperBlueprint（章节骨架）。

设计原则:
  - Structure 负责「论文骨架」，不填充内容（SectionGenerator 的任务）
  - 按 problem_type 路由到不同结构模板
  - 基于 archive/v5 模板 + paper_structure_and_chapter_rules.md 的黄金九章
"""
from typing import Dict, List, Optional


# 黄金九章结构（CUMCM 标准，来自 paper_structure_and_chapter_rules.md）
GOLDEN_NINE = [
    {"id": "abstract",   "title": "摘要",             "mandatory": True,  "pages": "1页",   "info_task": "全篇浓缩：问题→方法→结果→创新"},
    {"id": "restatement", "title": "问题重述",         "mandatory": True,  "pages": "0.5-1页","info_task": "用自己的话重新表述问题"},
    {"id": "analysis",   "title": "问题分析",          "mandatory": True,  "pages": "1-2页",  "info_task": "现实→数学，提炼研究问题+核心矛盾"},
    {"id": "assumptions","title": "模型假设",          "mandatory": True,  "pages": "0.5页",  "info_task": "假设+理由+验证+影响"},
    {"id": "symbols",    "title": "符号说明",          "mandatory": True,  "pages": "0.5-1页","info_task": "全局符号表，三线表格式"},
    {"id": "modeling",   "title": "模型建立",          "mandatory": True,  "pages": "2-4页",  "info_task": "为什么这个模型+公式推导"},
    {"id": "solving",    "title": "模型求解",          "mandatory": True,  "pages": "1-2页",  "info_task": "算法步骤+参数选择+收敛"},
    {"id": "results",    "title": "结果分析",          "mandatory": True,  "pages": "3-5页",  "info_task": "结果→解释→对比→洞察"},
    {"id": "evaluation", "title": "模型评价与推广",    "mandatory": True,  "pages": "0.5-1页","info_task": "优点+缺点+改进方向"},
    {"id": "references", "title": "参考文献",          "mandatory": True,  "pages": "0.5页",  "info_task": "GB/T 7714格式"},
]

# 按题型的结构变体
TYPE_VARIANTS = {
    "optimization": {
        "emphasis": ["modeling", "solving", "results"],
        "extra_sections": [
            {"id": "sensitivity", "title": "灵敏度分析", "mandatory": True, "pages": "1-2页", "info_task": "参数变化对最优解的影响"}
        ],
    },
    "prediction": {
        "emphasis": ["analysis", "modeling", "results"],
        "extra_sections": [
            {"id": "data_preprocessing", "title": "数据预处理", "mandatory": True, "pages": "0.5-1页", "info_task": "缺失值/异常值处理+特征工程"},
            {"id": "model_comparison", "title": "模型对比", "mandatory": True, "pages": "1-2页", "info_task": "多模型性能对比表"},
        ],
    },
    "evaluation": {
        "emphasis": ["analysis", "modeling", "results"],
        "extra_sections": [
            {"id": "indicator_system", "title": "指标体系构建", "mandatory": True, "pages": "1-2页", "info_task": "维度分解+指标选择+赋权方法"},
            {"id": "robustness", "title": "稳健性检验", "mandatory": True, "pages": "1-2页", "info_task": "灵敏度分析+对比验证"},
        ],
    },
    "hybrid": {
        "emphasis": ["analysis", "modeling", "results"],
        "extra_sections": [
            {"id": "tech_route", "title": "技术路线", "mandatory": True, "pages": "1页", "info_task": "分治策略+整体技术路线图"},
        ],
    },
}


class StructureSelector:
    """论文结构选择器 — L6 管线拓扑入口"""

    def select(self,
               problem_state: Dict,
               competition: str = "CUMCM",
               complexity: str = "standard") -> Dict:
        """
        根据 ProblemState 选择论文结构。

        Args:
            problem_state: L1 ProblemState 输出
            competition: "CUMCM" | "MCM"
            complexity: "simple" | "standard" | "complex" (影响章节是否合并)

        Returns:
            PaperBlueprint dict
        """
        ps = problem_state.get("data", problem_state)
        problem_type = ps.get("problem_type", "hybrid")
        domain = ps.get("domain", "")
        n_sub_problems = len(ps.get("sub_problems", []))

        # 基础九章
        sections = [dict(s) for s in GOLDEN_NINE]

        # 按题型增减
        variant = TYPE_VARIANTS.get(problem_type, TYPE_VARIANTS["hybrid"])
        extra = [dict(s) for s in variant.get("extra_sections", [])]

        # 复杂度调整
        if complexity == "simple" and n_sub_problems <= 1:
            # 简单题：模型建立+求解合并
            sections = self._merge_adjacent(sections, ["modeling", "solving"],
                                            {"id": "modeling_and_solving", "title": "模型建立与求解",
                                             "mandatory": True, "pages": "3-5页",
                                             "info_task": "模型推导+求解过程"})

        # 插入题型特有章节（在 results 之前）
        insert_pos = self._find_index(sections, "results")
        for e in reversed(extra):
            sections.insert(insert_pos, e)

        # 多问题：模型建立展开为 问题1/问题2/问题3
        if n_sub_problems >= 2:
            sections = self._expand_multi_problem(sections, ps.get("sub_problems", []))

        # 构建输出
        emphasis = variant.get("emphasis", [])

        return {
            "blueprint_id": f"BP-{problem_type}-{competition}",
            "competition": competition,
            "problem_type": problem_type,
            "domain": domain,
            "n_sub_problems": n_sub_problems,
            "complexity": complexity,
            "template_source": "golden_nine_v1",
            "sections": sections,
            "ordering": [s["id"] for s in sections],
            "required_sections": [s["id"] for s in sections if s["mandatory"]],
            "optional_sections": [s["id"] for s in sections if not s["mandatory"]],
            "emphasis_sections": emphasis,
            "total_estimated_pages": self._estimate_pages(sections),
            "dependency_hints": {
                "abstract_compiler": "abstract",
                "argument_compiler": "analysis",
                "model_specification": "modeling",
                "chart_compiler": "results",
                "reference_compiler": "references",
            },
        }

    def _find_index(self, sections: List, target_id: str) -> int:
        for i, s in enumerate(sections):
            if s["id"] == target_id:
                return i
        return len(sections)

    def _merge_adjacent(self, sections: List, ids: List[str], replacement: Dict) -> List:
        positions = [self._find_index(sections, sid) for sid in ids]
        if -1 in positions:
            return sections
        min_pos = min(positions)
        max_pos = max(positions)
        del sections[min_pos:max_pos + 1]
        sections.insert(min_pos, replacement)
        return sections

    def _expand_multi_problem(self, sections: List, sub_problems: List) -> List:
        """将模型建立章展开为问题1/2/3子节"""
        modeling_idx = self._find_index(sections, "modeling")
        if modeling_idx == -1:
            return sections

        modeling_section = sections[modeling_idx]
        sub_sections = []
        for sp in sub_problems:
            sp_id = sp.get("id", f"{len(sub_sections) + 1}")
            sub_sections.append({
                "id": f"modeling_q{sp_id}",
                "title": f"问题{sp_id}: {sp.get('title', '模型建立')}",
                "mandatory": True,
                "parent": "modeling",
                "pages": "1-2页",
                "info_task": f"问题{sp_id}的模型推导与公式",
            })

        sections[modeling_idx] = dict(modeling_section)
        sections[modeling_idx]["sub_sections"] = sub_sections
        return sections

    def _estimate_pages(self, sections: List) -> str:
        total_min, total_max = 0, 0
        for s in sections:
            pr = s.get("pages", "1页")
            try:
                parts = pr.replace("页", "").split("-")
                if len(parts) == 2:
                    total_min += float(parts[0])
                    total_max += float(parts[1])
                else:
                    total_min += float(parts[0])
                    total_max += float(parts[0])
            except ValueError:
                total_min += 1
                total_max += 2
        return f"{total_min:.0f}-{total_max:.0f}页"


# ===== 自测 =====

if __name__ == "__main__":
    selector = StructureSelector()

    # Case 1: 优化类
    ps_opt = {"problem_type": "optimization", "domain": "supply_chain", "sub_problems": [{"id": "1", "title": "选址优化"}, {"id": "2", "title": "路径规划"}]}
    bp = selector.select(ps_opt)
    print(f"=== {bp['problem_type']} ({bp['n_sub_problems']} sub) ===")
    for s in bp["sections"]:
        sub = f" [{len(s.get('sub_sections', []))} sub]" if s.get("sub_sections") else ""
        print(f"  {s['id']:25s} {s['title']:15s} {s['pages']:8s}{sub}")
    print(f"  Total pages: {bp['total_estimated_pages']}")

    # Case 2: 预测类
    ps_pred = {"problem_type": "prediction", "domain": "air_quality", "sub_problems": []}
    bp2 = selector.select(ps_pred)
    print(f"\n=== {bp2['problem_type']} ({bp2['n_sub_problems']} sub) ===")
    for s in bp2["sections"]:
        print(f"  {s['id']:25s} {s['title']:15s} {s['pages']:8s}")
    print(f"  Dependency hints: {bp2['dependency_hints']}")
