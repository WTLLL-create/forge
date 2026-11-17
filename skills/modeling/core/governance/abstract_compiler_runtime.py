"""
AbstractCompiler v1.0 — 独立摘要编译器
=========================================
Forge v6.5 Wave 2.1: 从 paper_compiler.py 单体中提取出来的独立模块。
消费 ProblemState + DecisionContract + ModelResult，产出符合 abstract_spec.schema.json 的摘要。

5 要素结构（来自 abstract_patterns.md）:
  ① 问题简述  → from ProblemState
  ② 方法概述  → from DecisionContract
  ③ 核心结果  → from ModelResult (必须含具体数值)
  ④ 创新亮点  → 可选，自动检测或用户补充
  ⑤ 结论意义  → 自动生成或用户补充

按题型（optimization/prediction/evaluation/hybrid）选择对应模板。
禁止笼统表述、禁止公式、禁止引用标记。
字数: 700-1000 字 ｜ 关键词: 3-7 个
"""

from typing import Dict, Optional


# 题型 → 模板映射（来自 abstract_patterns.md）
TYPE_TEMPLATES = {
    "optimization": """本文研究了{problem_desc}的数学建模与优化问题。首先通过{analysis_method}分析了{key_variables}对{objective}的影响规律。在此基础上，建立了{model_name}，采用{solution_method}求解得到最优方案。{core_results}进一步通过{sensitivity_analysis}验证了模型的稳定性。{innovation}{significance}""",

    "prediction": """本文针对{problem_desc}，完成了从数据预处理到模型构建的完整分析。数据处理阶段，采用{preprocessing}方法处理了数据质量问题。建立了{primary_model}和{backup_model}进行对比预测，{primary_model}的{primary_metric}优于{backup_model}的{backup_metric}。{core_results}{innovation}{significance}""",

    "evaluation": """本文构建了{domain}的评价指标体系，采用{weighting_method}确定指标权重，利用{evaluation_method}进行综合评价。结果表明{top_finding}。进一步通过{sensitivity_analysis}验证了评价结果的稳定性。{innovation}基于研究结果，提出了{recommendations}。""",

    "hybrid": """本文针对{problem_desc}的复合问题，采用分治策略进行建模。{method_overview}。求解结果表明{core_results}。{innovation}本研究建立的模型体系和分析框架为同类问题的解决提供了系统化的方法论参考，{significance}。""",

    "unknown": """本文针对{problem_desc}，建立了完整的数学模型体系。{method_overview}。{core_results}。{innovation}本研究的方法和结论为{significance}提供了理论依据和定量分析支撑。""",
}


class AbstractCompiler:
    """独立摘要编译器 — 从 Contracts 生成结构化摘要"""

    def __init__(self):
        self.templates = TYPE_TEMPLATES

    def compile(self,
                problem_state: Dict,
                decision_contract: Dict,
                model_result: Dict,
                keywords_override: Optional[list] = None) -> Dict:
        """
        编译摘要。

        Args:
            problem_state: L1 ProblemState 输出
            decision_contract: L3 DecisionContract 输出
            model_result: L4 ModelResult 输出
            keywords_override: 手动指定的关键词列表（可选）

        Returns:
            AbstractSpec dict (符合 abstract_spec.schema.json)
        """
        ps = problem_state.get("data", problem_state)
        dc = decision_contract.get("data", decision_contract)
        mr = model_result

        problem_type = ps.get("problem_type", "unknown")
        problem_id = ps.get("problem_id", "数学建模问题")

        # 元素①: 问题简述
        problem_desc = self._build_problem_desc(ps, problem_id)

        # 元素②: 方法概述
        method_overview = self._build_method_overview(dc)

        # 元素③: 核心结果
        core_results = self._build_core_results(mr)

        # 元素④: 创新亮点
        innovation = self._build_innovation(dc)

        # 元素⑤: 结论意义
        significance = self._build_significance(ps, mr)

        # 选择模板
        template_key = problem_type if problem_type in self.templates else "unknown"
        template = self.templates[template_key]

        # 填充模板
        abstract_text = template.format(
            problem_desc=problem_desc,
            analysis_method=dc.get("analysis_method", "系统分析方法"),
            key_variables=dc.get("key_variables", "关键变量"),
            objective=dc.get("objective", "目标函数"),
            model_name=self._get_primary_model(dc),
            solution_method=dc.get("solution_method", "数值求解方法"),
            core_results=core_results,
            sensitivity_analysis=dc.get("sensitivity_method", "敏感性分析"),
            innovation=innovation,
            significance=significance,
            preprocessing=dc.get("preprocessing", "数据清洗和特征工程"),
            primary_model=self._get_primary_model(dc),
            backup_model=self._get_backup_model(dc),
            primary_metric=mr.get("primary_metric", "R²"),
            backup_metric=mr.get("backup_metric", "R²"),
            domain=ps.get("domain", "相关领域"),
            weighting_method=dc.get("weighting_method", "CRITIC法"),
            evaluation_method=self._get_primary_model(dc),
            top_finding=self._extract_top_finding(mr),
            recommendations=dc.get("recommendations", "相关建议"),
            method_overview=method_overview,
        )

        # 确保字数达标
        abstract_text = self._ensure_word_count(abstract_text, min_chars=700)

        # 推导关键词
        keywords = keywords_override or self._derive_keywords(ps, dc, mr)

        # 质量检查
        quality_flags = self._quality_check(abstract_text, core_results)

        return {
            "abstract_text": abstract_text,
            "word_count": len(abstract_text.replace('\n', '').replace(' ', '')),
            "elements": {
                "problem_statement": {"text": problem_desc, "source_contract": "ProblemState"},
                "method_overview": {"text": method_overview, "models_mentioned": self._list_models(dc), "source_contract": "DecisionContract"},
                "core_results": {"text": core_results, "has_quantitative_data": bool(mr.get("results_summary")), "key_metrics": self._extract_metrics(mr), "source_contract": "ModelResult"},
                "innovation_highlight": {"text": innovation},
                "conclusion_significance": {"text": significance},
            },
            "keywords": keywords,
            "problem_type": problem_type,
            "template_used": template_key,
            "quality_flags": quality_flags,
        }

    # ===== 辅助方法 =====

    def _build_problem_desc(self, ps: Dict, problem_id: str) -> str:
        core_contradiction = ps.get("core_contradiction", "")
        if core_contradiction:
            return f"{problem_id}，围绕核心矛盾「{core_contradiction}」展开研究"
        return f"{problem_id}的数学建模问题"

    def _build_method_overview(self, dc: Dict) -> str:
        decisions = dc.get("decisions", [])
        if not decisions:
            return "采用数学模型方法进行系统分析"
        parts = []
        for d in decisions[:3]:
            model = d.get("primary_model", "数学模型")
            sub_id = d.get("sub_problem_id", "")
            parts.append(f"针对{sub_id}采用{model}")
        return "；".join(parts)

    def _build_core_results(self, mr: Dict) -> str:
        summary = mr.get("results_summary", {})
        if isinstance(summary, dict) and summary:
            text = summary.get("summary_text", "")
            if text:
                return text
        # Fallback: 从 ModelResult 中提取可用数据
        metrics = mr.get("primary_metric", {})
        if metrics:
            return f"模型性能指标为{metrics}"
        return "模型求解取得了预期效果"

    def _build_innovation(self, dc: Dict) -> str:
        innovations = dc.get("innovations", [])
        if innovations:
            return f"本文创新点在于{'; '.join(innovations[:2])}。"
        return ""

    def _build_significance(self, ps: Dict, mr: Dict) -> str:
        domain = ps.get("domain", "相关领域")
        return f"本研究成果对{domain}的决策优化和理论发展具有参考价值。"

    def _get_primary_model(self, dc: Dict) -> str:
        decisions = dc.get("decisions", [])
        if decisions:
            return decisions[0].get("primary_model", "数学模型")
        return "数学模型"

    def _get_backup_model(self, dc: Dict) -> str:
        decisions = dc.get("decisions", [])
        if len(decisions) > 1:
            return decisions[1].get("primary_model", "对比模型")
        if decisions and decisions[0].get("alternatives_considered"):
            alts = decisions[0]["alternatives_considered"]
            if alts:
                return alts[0].get("model", "备选模型")
        return "备选模型"

    def _list_models(self, dc: Dict) -> list:
        decisions = dc.get("decisions", [])
        return [d.get("primary_model", "") for d in decisions[:3] if d.get("primary_model")]

    def _extract_top_finding(self, mr: Dict) -> str:
        summary = mr.get("results_summary", {})
        if isinstance(summary, dict):
            return summary.get("top_finding", "方案综合评价最优")
        return "方案综合评价最优"

    def _extract_metrics(self, mr: Dict) -> list:
        metrics = []
        summary = mr.get("results_summary", {})
        if isinstance(summary, dict):
            for k, v in summary.items():
                if k not in ("summary_text", "top_finding") and v is not None:
                    metrics.append({"metric": k, "value": str(v)})
        return metrics[:5]

    def _ensure_word_count(self, text: str, min_chars: int = 700) -> str:
        """确保摘要字数达标"""
        clean = text.replace('\n', '').replace(' ', '')
        if len(clean) < min_chars:
            text += (
                "本研究建立的模型体系和分析框架为同类问题的解决提供了"
                "系统化的方法论参考，具有一定的理论价值和实际应用前景。"
            )
        return text

    def _derive_keywords(self, ps: Dict, dc: Dict, mr: Dict) -> list:
        keywords = ["数学建模"]
        domain = ps.get("domain", "")
        if domain:
            keywords.append(domain)
        for d in dc.get("decisions", [])[:2]:
            model = d.get("primary_model", "")
            if model and model not in keywords:
                keywords.append(model)
        problem_type = ps.get("problem_type", "")
        type_keywords = {
            "optimization": "优化",
            "prediction": "预测",
            "evaluation": "评价",
            "hybrid": "复合建模",
        }
        if problem_type in type_keywords:
            keywords.append(type_keywords[problem_type])
        return keywords[:7]

    def _quality_check(self, text: str, core_results: str) -> list:
        flags = []
        # 检查笼统表述
        vague_terms = ["效果很好", "结果较好", "有一定改善", "较为理想"]
        for term in vague_terms:
            if term in text:
                flags.append({
                    "flag": "vague_language",
                    "severity": "warning",
                    "message": f"摘要含笼统表述「{term}」，建议替换为具体数值"
                })
        # 检查是否有具体数值
        import re
        has_number = bool(re.search(r'[\d.]+[%％]?', core_results))
        if not has_number:
            flags.append({
                "flag": "no_quantitative_data",
                "severity": "error",
                "message": "核心结果缺少具体数值"
            })
        # 检查字数
        clean_len = len(text.replace('\n', '').replace(' ', ''))
        if clean_len < 600:
            flags.append({
                "flag": "too_short",
                "severity": "error",
                "message": f"摘要仅{clean_len}字，不足600字"
            })
        return flags


# ===== 快速自测 =====

if __name__ == "__main__":
    compiler = AbstractCompiler()

    problem_state = {
        "problem_id": "CUMCM_2020_A",
        "problem_type": "hybrid",
        "core_contradiction": "温度曲线的稳定性与炉温控制精度之间的矛盾",
        "domain": "工业过程控制",
    }

    decision_contract = {
        "decisions": [
            {"sub_problem_id": "Q1", "primary_model": "分段线性拟合", "reasoning": ["理由1", "理由2", "理由3"]},
            {"sub_problem_id": "Q2", "primary_model": "有限差分法", "alternatives_considered": [{"model": "有限元法", "reason_rejected": "计算量大"}]},
            {"sub_problem_id": "Q3", "primary_model": "CRITIC-TOPSIS"},
        ],
        "analysis_method": "机理分析",
        "key_variables": "炉温、传送带速度、焊点温度",
        "objective": "最大允许传送带速度",
    }

    model_result = {
        "results_summary": {
            "summary_text": "求解结果显示，传送带速度可达78.2cm/min，焊点温度均方差从15.3℃降至4.7℃，炉温曲线积分面积偏差减少42%",
            "top_finding": "传送带速度提升至78.2cm/min",
        }
    }

    spec = compiler.compile(problem_state, decision_contract, model_result)
    print(spec["abstract_text"][:200] + "...")
    print(f"\n字数: {spec['word_count']}")
    print(f"关键词: {spec['keywords']}")
    print(f"模板: {spec['template_used']}")
    print(f"质量标记: {len(spec['quality_flags'])}")
    for f in spec["quality_flags"]:
        print(f"  [{f['severity']}] {f['message']}")
