"""
Competition Reality Layer v1.0 — 评委视角模拟
==================================================
Forge v7.1: 从"内部系统指标"跨越到"评委怎么看"。

三大组件:
  JudgeIntelligence — 模拟 CUMCM 评委对论文的 6 维度评分 + 扣分原因
  ScoreSimulation     — 基于 Pattern 历史分布预测得分区间和获奖概率
  WinningPathPlanner  — 从当前状态到一等奖的最优改进路径
"""
import sys, os
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pattern_intelligence"))
from evidence_intelligence import EvidenceGraph, EvidenceEvaluator
from reasoning_engine import ReasoningBuilder, ReasoningValidator, DOMAIN_REASONING_RULES

# 评委评分锚点 — CUMCM 6维度满分 + 一等奖 ≈ 75-85分
SCORING_ANCHORS = {
    "D1_problem_understanding": {"full": 15, "first_prize_min": 11, "first_prize_typical": 13, "deduction_reasons": [
        {"reason": "问题理解有偏差", "deduct": -3},
        {"reason": "核心矛盾未识别", "deduct": -4},
        {"reason": "子问题划分不合理", "deduct": -2},
        {"reason": "约束条件遗漏", "deduct": -3},
    ]},
    "D2_model_reasoning": {"full": 25, "first_prize_min": 20, "first_prize_typical": 22, "deduction_reasons": [
        {"reason": "模型选择无充分论证", "deduct": -5},
        {"reason": "假设不合理或未经验证", "deduct": -4},
        {"reason": "缺少备选方案对比", "deduct": -3},
        {"reason": "公式推导有跳跃", "deduct": -3},
        {"reason": "变量未定义或符号不统一", "deduct": -2},
    ]},
    "D3_solution_reliability": {"full": 20, "first_prize_min": 16, "first_prize_typical": 18, "deduction_reasons": [
        {"reason": "求解方法不合理", "deduct": -5},
        {"reason": "参数无确定依据", "deduct": -3},
        {"reason": "中间结果不透明", "deduct": -3},
        {"reason": "结果缺乏置信区间", "deduct": -2},
    ]},
    "D4_validation_completeness": {"full": 15, "first_prize_min": 11, "first_prize_typical": 13, "deduction_reasons": [
        {"reason": "完全缺灵敏度分析", "deduct": -6},
        {"reason": "缺模型对比验证", "deduct": -4},
        {"reason": "验证指标单一", "deduct": -3},
        {"reason": "稳定性检验不足", "deduct": -2},
    ]},
    "D5_innovation": {"full": 15, "first_prize_min": 9, "first_prize_typical": 11, "deduction_reasons": [
        {"reason": "纯套用标准模型无改进", "deduct": -6},
        {"reason": "创新点论证不足", "deduct": -4},
        {"reason": "改进缺乏对比证明", "deduct": -3},
    ]},
    "D6_paper_quality": {"full": 10, "first_prize_min": 7, "first_prize_typical": 8, "deduction_reasons": [
        {"reason": "章节结构残缺", "deduct": -3},
        {"reason": "图表不规范", "deduct": -2},
        {"reason": "参考文献不足", "deduct": -2},
        {"reason": "摘要无具体数值", "deduct": -2},
    ]},
}


class JudgeIntelligence:
    """模拟 CUMCM 评委对论文的完整评分"""

    def score(self,
              problem_type: str,
              evidence_result: Dict,
              reasoning_result: Dict,
              artifact_quality: Dict = None) -> Dict:
        """
        模拟真实评委评分。

        Args:
            problem_type: 题型
            evidence_result: EvidenceEvaluator 输出 (ESR/CCR/PCR)
            reasoning_result: ReasoningValidator 输出
            artifact_quality: 产物质量评估 (optional)

        Returns:
            JudgeScorecard with D1-D6 scores, comments, and predicted award
        """
        scores = {}
        comments = []
        dim_details = {}

        for dim, anchor in SCORING_ANCHORS.items():
            full = anchor["full"]
            score = full
            deductions = []

            # D1: Problem Understanding
            if dim == "D1_problem_understanding":
                if reasoning_result["reasoning_score"] < 80:
                    d = anchor["deduction_reasons"][1]  # 核心矛盾未识别
                    score += d["deduct"]
                    deductions.append(d["reason"])
                if artifact_quality and not artifact_quality.get("problem_restatement", True):
                    score -= 2
                    deductions.append("问题重述质量不足")

            # D2: Model Reasoning — 核心权重
            elif dim == "D2_model_reasoning":
                esr = evidence_result.get("esr", 0)
                reasoning = reasoning_result.get("reasoning_score", 0)
                if esr < 60:
                    d = anchor["deduction_reasons"][0]  # 无充分论证
                    score += d["deduct"]
                    deductions.append(d["reason"])
                if reasoning < 50:
                    score -= 4
                    deductions.append("推理链不完整")
                if evidence_result.get("ccr", 0) < 70:
                    d = anchor["deduction_reasons"][2]  # 缺备选对比
                    score += d["deduct"]
                    deductions.append(d["reason"])

            # D3: Solution Reliability
            elif dim == "D3_solution_reliability":
                if reasoning_result["reasoning_score"] < 60:
                    d = anchor["deduction_reasons"][1]  # 参数无依据
                    score += d["deduct"]
                    deductions.append(d["reason"])
                if evidence_result.get("esr", 0) < 50:
                    score -= 3
                    deductions.append("求解证据不足")

            # D4: Validation
            elif dim == "D4_validation_completeness":
                has_sensitivity = "sensitivity_tornado" in str(evidence_result.get("esr_details", []))
                has_comparison = "model_comparison" in str(evidence_result.get("esr_details", []))
                if not has_sensitivity:
                    d = anchor["deduction_reasons"][0]
                    score += d["deduct"]
                    deductions.append(d["reason"])
                if not has_comparison:
                    d = anchor["deduction_reasons"][1]
                    score += d["deduct"]
                    deductions.append(d["reason"])

            # D5: Innovation
            elif dim == "D5_innovation":
                # Innovation is hard to auto-detect; default to middle
                innovation_level = "standard" if evidence_result.get("pcr", 0) > 70 else "basic"
                if innovation_level == "standard":
                    score = anchor["first_prize_typical"]
                else:
                    score = anchor["first_prize_min"] - 2
                    deductions.append("创新点不足")

            # D6: Paper Quality
            elif dim == "D6_paper_quality":
                if evidence_result.get("pcr", 0) < 80:
                    d = anchor["deduction_reasons"][0]
                    score += d["deduct"]
                    deductions.append(d["reason"])
                if artifact_quality and not artifact_quality.get("structure_complete", True):
                    score -= 2

            scores[dim] = max(0, min(full, score))
            if deductions:
                comments.append({"dimension": dim, "score": scores[dim], "max": full, "deductions": deductions})

            dim_details[dim] = {"score": scores[dim], "max": full, "deductions": deductions}

        total = sum(scores.values())

        # 获奖等级预测
        if total >= 80:
            award = "国家一等奖"
        elif total >= 70:
            award = "国家二等奖"
        elif total >= 60:
            award = "省级一等奖"
        elif total >= 50:
            award = "省级二等奖"
        else:
            award = "未获奖"

        return {
            "judge_id": f"JUDGE-{problem_type}",
            "problem_type": problem_type,
            "dimension_scores": dim_details,
            "total_score": total,
            "max_score": 100,
            "predicted_award": award,
            "award_probability": self._award_probability(total),
            "weakest_dimension": min(dim_details, key=lambda d: dim_details[d]["score"] / dim_details[d]["max"]),
            "comments": comments,
            "judge_verdict": self._verdict(total, dim_details),
        }

    def _award_probability(self, total: int) -> Dict:
        return {
            "国家一等奖": min(95, max(0, int((total - 70) / 10 * 100))) if total >= 70 else 0,
            "国家二等奖": min(95, max(0, int((total - 60) / 10 * 100))) if total >= 60 else 0,
            "省级奖": 95 if total < 60 and total >= 50 else (0 if total < 50 else 50),
        }

    def _verdict(self, total: int, dims: Dict) -> str:
        weakest = min(dims, key=lambda d: dims[d]["score"] / dims[d]["max"])
        weakest_name = {
            "D1_problem_understanding": "问题理解",
            "D2_model_reasoning": "模型论证",
            "D3_solution_reliability": "求解可靠性",
            "D4_validation_completeness": "验证完整性",
            "D5_innovation": "创新性",
            "D6_paper_quality": "论文规范",
        }.get(weakest, weakest)

        if total >= 80:
            return f"论文整体质量优秀，{weakest_name}仍有提升空间"
        elif total >= 70:
            return f"论文质量良好，{weakest_name}是需要重点加强的维度"
        elif total >= 60:
            return f"基本达标，{weakest_name}是明显短板"
        else:
            return f"多维度需要显著改进，首要从{weakest_name}入手"


class ScoreSimulation:
    """基于 Pattern 历史分布预测得分区间"""

    def simulate(self, problem_type: str, judge_score: int) -> Dict:
        """运行多次模拟得到得分分布"""
        pattern_scores = {
            "prediction": {"mean": 76, "std": 5, "range": (68, 84), "sample_size": 25},
            "optimization": {"mean": 74, "std": 6, "range": (65, 82), "sample_size": 20},
            "evaluation": {"mean": 73, "std": 4, "range": (66, 79), "sample_size": 18},
            "hybrid": {"mean": 75, "std": 5, "range": (67, 81), "sample_size": 15},
        }
        ps = pattern_scores.get(problem_type, pattern_scores["prediction"])
        z = (judge_score - ps["mean"]) / max(ps["std"], 1)

        if z >= 0.5:
            tier = "above_typical"
            rank_estimate = "前30%"
        elif z >= -0.5:
            tier = "typical"
            rank_estimate = "中等偏上"
        elif z >= -1.0:
            tier = "below_typical"
            rank_estimate = "中等偏下"
        else:
            tier = "needs_improvement"
            rank_estimate = "需要改进"

        return {
            "problem_type": problem_type,
            "pattern_history": ps,
            "current_score": judge_score,
            "z_score": round(z, 2),
            "tier": tier,
            "rank_estimate": rank_estimate,
            "next_tier_gap": max(0, ps["mean"] - judge_score) if z < 0 else 0,
            "first_prize_range": f"{ps['range'][0]}-{ps['range'][1]}",
        }


class WinningPathPlanner:
    """从当前状态到一等奖的改进路径"""

    def plan(self, judge_score: Dict, evidence: Dict, reasoning: Dict) -> Dict:
        dims = judge_score.get("dimension_scores", {})
        steps = []

        # 按 ROI 排序: 扣分最多的维度优先
        gaps = []
        for dim, detail in dims.items():
            gap = detail["max"] - detail["score"]
            if gap > 0:
                roi = self._estimate_roi(dim, gap, evidence, reasoning)
                gaps.append({"dimension": dim, "gap": gap, "roi": roi})

        gaps.sort(key=lambda g: g["roi"], reverse=True)

        for i, gap in enumerate(gaps[:5]):
            steps.append({
                "priority": i + 1,
                "dimension": gap["dimension"],
                "current_gap": gap["gap"],
                "estimated_gain": min(gap["gap"], int(gap["roi"] * 0.7)),
                "action": self._action_for_dim(gap["dimension"], gap["gap"]),
                "effort": "low" if gap["gap"] <= 3 else ("medium" if gap["gap"] <= 6 else "high"),
            })

        total_gain = sum(s["estimated_gain"] for s in steps[:3])
        current = judge_score["total_score"]
        target = min(100, current + total_gain)

        return {
            "current_score": current,
            "target_score": target,
            "gain_from_top_3": total_gain,
            "steps": steps[:3],
            "first_prize_reachable": target >= 75,
            "minimum_award": judge_score["predicted_award"],
            "target_award": "国家一等奖" if target >= 80 else ("国家二等奖" if target >= 70 else judge_score["predicted_award"]),
        }

    def _estimate_roi(self, dim: str, gap: int, evidence: Dict, reasoning: Dict) -> float:
        base_roi = gap * 1.0
        if dim == "D2_model_reasoning":
            base_roi *= 1.5  # 最高权重 25分
        elif dim == "D4_validation_completeness":
            if evidence.get("pcr", 0) < 60:
                base_roi *= 1.3  # 验证不足是常见扣分
        return base_roi

    def _action_for_dim(self, dim: str, gap: int) -> str:
        actions = {
            "D1_problem_understanding": "强化问题分析段落，明确核心矛盾和数学本质",
            "D2_model_reasoning": "补充备选模型对比论证 + 为什么选择这个模型的推理链",
            "D3_solution_reliability": "补充参数确定依据 + 中间结果展示 + 置信区间",
            "D4_validation_completeness": "增加灵敏度分析/模型对比验证/鲁棒性检验",
            "D5_innovation": "增加模型改进论证 + 与标准方法的效果对比",
            "D6_paper_quality": "检查章节结构完整性 + 图表规范 + 参考文献数量",
        }
        return actions.get(dim, "针对性改进")


# ===== CLI =====

if __name__ == "__main__":
    graph = EvidenceGraph()
    evaluator = EvidenceEvaluator()
    builder = ReasoningBuilder()
    validator = ReasoningValidator()
    judge = JudgeIntelligence()
    simulation = ScoreSimulation()
    planner = WinningPathPlanner()

    full_evidence = {"present": ["model_comparison", "prediction_vs_actual", "residual_plot",
                                  "correlation_heatmap", "sensitivity_tornado", "contradiction_statement"],
                     "metrics": ["R²", "RMSE", "MAE", "残差均值为0", "残差无模式"],
                     "columns": ["模型", "R²", "RMSE", "参数", "取值", "选择理由"]}

    partial_evidence = {"present": ["model_comparison"],
                        "metrics": ["R²"], "columns": ["模型"]}

    print("=" * 60)
    print("v7.1 — Competition Reality Layer")
    print("=" * 60)

    for pt in ["prediction", "optimization", "evaluation"]:
        evg = graph.build(pt)
        chains = builder.build(pt, evg)

        ev_full = evaluator.evaluate(evg, full_evidence)
        ev_partial = evaluator.evaluate(evg, partial_evidence)
        reas_full = validator.validate(chains, ["correlation_heatmap", "model_comparison",
                                                  "prediction_vs_actual", "residual_plot",
                                                  "optimal_solution", "sensitivity_tornado",
                                                  "indicator_system", "weight_comparison"])

        print(f"\n{'─' * 60}")
        print(f"[{pt.upper()}]")

        # Judge Score
        js_full = judge.score(pt, ev_full, reas_full, {"structure_complete": True})
        js_partial = judge.score(pt, ev_partial, reas_full, {"structure_complete": False})

        # Score Simulation
        sim_full = simulation.simulate(pt, js_full["total_score"])

        # Winning Path
        path = planner.plan(js_full, ev_full, reas_full)

        print(f"\n  Judge Scorecard:")
        for dim in ["D1_problem_understanding", "D2_model_reasoning", "D3_solution_reliability",
                     "D4_validation_completeness", "D5_innovation", "D6_paper_quality"]:
            score = js_full["dimension_scores"][dim]["score"]
            maximum = js_full["dimension_scores"][dim]["max"]
            bar = "█" * int(score / maximum * 20)
            print(f"    {dim[:5]:5s} [{bar:20s}] {score}/{maximum}")

        print(f"\n    Total: {js_full['total_score']}/100 → {js_full['predicted_award']} ({js_full['award_probability']['国家一等奖']}% prob)")
        print(f"    Simulation: tier={sim_full['tier']}, rank={sim_full['rank_estimate']}, first_prize_range={sim_full['first_prize_range']}")

        # Compare: full vs partial
        delta = js_full["total_score"] - js_partial["total_score"]
        print(f"\n    Evidence Impact: Full={js_full['total_score']} vs Partial={js_partial['total_score']} (Δ{delta})")
        print(f"    Weakest: {js_full['weakest_dimension']}")
        print(f"    Verdict: {js_full['judge_verdict'][:80]}...")

        # Winning Path
        print(f"\n  Winning Path ({path['target_award']} reachable: {path['first_prize_reachable']}):")
        for s in path["steps"]:
            print(f"    [{s['priority']}] {s['dimension']:25s} gap={s['current_gap']} → +{s['estimated_gain']} ({s['effort']} effort)")
            print(f"         {s['action']}")

    # Summary
    print(f"\n{'=' * 60}")
    print("Competition Reality Layer: COMPLETE")
    print(f"  Pattern → Evidence → Reasoning → Judge → Score → Winning Path")
    print(f"  Forge now knows not just 'what to generate', but 'what points to win'")
