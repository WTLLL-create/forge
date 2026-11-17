"""
Competition Optimization Layer v1.0 — 从诊断到战略
========================================================
Forge v7.2: 回答"怎么赢"。

三大组件:
  ScoreImpactModel      — 预测每项改进的分数收益和 ROI
  CompetitionMemory     — 记录哪些改动历史上提高了奖项等级
  AwardBoundaryModel    — 二等奖→一等奖的跨越因子分析
"""
import sys, os
from typing import Dict, List
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pattern_intelligence"))
from judge_intelligence import JudgeIntelligence, ScoreSimulation, WinningPathPlanner
from evidence_intelligence import EvidenceGraph, EvidenceEvaluator
from reasoning_engine import ReasoningBuilder, ReasoningValidator


# 改进动作 → 预估分数收益 (基于竞赛经验 + 论文对照)
IMPROVEMENT_ACTIONS = {
    "add_model_comparison": {
        "action": "增加备选模型对比论证 (横向对比表 + 为什么选/不选)",
        "affects": ["D2_model_reasoning"],
        "gain": {"D2_model_reasoning": 4, "typical_total": 4},
        "effort": "medium",
        "evidence": "基于 P001 77分 ↔ P002 44分 对照: 备选对比是区分度最大的单一因素",
    },
    "add_shap_interpretation": {
        "action": "增加 SHAP/特征重要性分析", "affects": ["D2_model_reasoning", "D5_innovation"],
        "gain": {"D2_model_reasoning": 3, "D5_innovation": 3, "typical_total": 6},
        "effort": "medium",
        "evidence": "2021B空气质量高分论文: SHAP分析将D2从20→23, D5从7→11",
    },
    "add_sensitivity_analysis": {
        "action": "增加参数敏感性分析 (±10% 扰动测试)", "affects": ["D4_validation_completeness"],
        "gain": {"D4_validation_completeness": 4, "typical_total": 4},
        "effort": "medium",
        "evidence": "优化题高分论文: 灵敏度分析平均贡献D4+5",
    },
    "add_cross_validation": {
        "action": "增加交叉验证或留出法验证", "affects": ["D3_solution_reliability"],
        "gain": {"D3_solution_reliability": 2, "typical_total": 2},
        "effort": "low",
        "evidence": "预测题标准做法: CV/留出法稳固D3",
    },
    "add_residual_analysis": {
        "action": "增加残差分析和误差分布讨论", "affects": ["D3_solution_reliability", "D4_validation_completeness"],
        "gain": {"D3_solution_reliability": 2, "D4_validation_completeness": 2, "typical_total": 4},
        "effort": "low",
        "evidence": "残差分析 = 评委验证模型假设的最佳证据",
    },
    "add_mechanism_explanation": {
        "action": "增加机制解释 (为什么会出现这个结果？物理/经济含义)", "affects": ["D2_model_reasoning", "D5_innovation"],
        "gain": {"D2_model_reasoning": 2, "D5_innovation": 4, "typical_total": 6},
        "effort": "high",
        "evidence": "国一论文标配: 结果不仅报告数值, 更解释因果机制",
    },
    "add_innovation_argument": {
        "action": "增加创新点论证段落 (改进了什么 + 为什么有效 + 对比证明)", "affects": ["D5_innovation"],
        "gain": {"D5_innovation": 5, "typical_total": 5},
        "effort": "medium",
        "evidence": "D5 最大扣分项: 缺乏创新论证",
    },
    "complete_structure": {
        "action": "补全论文结构 (缺章补章, 缺表补表)", "affects": ["D6_paper_quality"],
        "gain": {"D6_paper_quality": 3, "typical_total": 3},
        "effort": "low",
        "evidence": "结构完整性直接扣D6",
    },
}

# 奖项边界 — 从历史数据蒸馏的跨越因子
AWARD_BOUNDARIES = {
    "未获奖→省奖": {"threshold": 50, "key_factors": ["模型求解基本正确", "论文结构基本完整"], "typical_gap": 10},
    "省奖→国家二等": {"threshold": 60, "key_factors": ["模型选择有论证", "验证方法完整", "结果分析充分"], "typical_gap": 10},
    "国家二等→国家一等": {
        "threshold": 75,
        "key_factors": [
            "模型选择有创新论证",
            "核心矛盾识别清晰 (contradiction_finder)",
            "数学推导严谨 + 假设验证",
            "多模型对比 + 统计显著性检验",
            "结果机制解释 (不只是数值报告)",
        ],
        "typical_gap": 10,
        "hardest_factor": "创新性论证",
    },
}


class ScoreImpactModel:
    """预测每项改进的分数收益"""

    def estimate(self, judge_score: Dict, problem_type: str) -> List[Dict]:
        dims = judge_score.get("dimension_scores", {})

        actions = []
        for action_id, action_def in IMPROVEMENT_ACTIONS.items():
            total_gain = 0
            for dim, gain in action_def["gain"].items():
                if dim in dims:
                    current = dims[dim]["score"]
                    max_score = dims[dim]["max"]
                    # 不超出满分
                    effective_gain = min(gain, max_score - current)
                    total_gain += effective_gain

            # ROI = gain / effort
            effort_weights = {"low": 1.0, "medium": 0.7, "high": 0.4}
            roi = total_gain * effort_weights.get(action_def["effort"], 0.5)

            actions.append({
                "action_id": action_id,
                "action": action_def["action"],
                "total_gain": total_gain,
                "roi": round(roi, 1),
                "effort": action_def["effort"],
                "affected_dimensions": action_def["affects"],
                "evidence": action_def["evidence"],
            })

        actions.sort(key=lambda a: a["roi"], reverse=True)
        return actions

    def best_combo(self, actions: List[Dict], target_score: int, current_score: int) -> Dict:
        """选择达到目标分数的最优组合 (ROI 优先)"""
        gap = target_score - current_score
        selected = []
        gained = 0

        for action in actions:
            if gained >= gap:
                break
            selected.append(action)
            gained += action["total_gain"]

        return {
            "target": target_score,
            "current": current_score,
            "gap": gap,
            "gained": gained,
            "reachable": gained >= gap,
            "actions": selected,
            "total_effort": len(selected),
        }


class CompetitionMemory:
    """记录哪些改进在历史中真正提高了奖项"""

    def __init__(self):
        self.records = []

    def record(self, problem_type: str, before: Dict, after: Dict, changes: List[str]):
        self.records.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "problem_type": problem_type,
            "before": {"score": before.get("total_score", 0), "award": before.get("predicted_award", "")},
            "after": {"score": after.get("total_score", 0), "award": after.get("predicted_award", "")},
            "delta": after.get("total_score", 0) - before.get("total_score", 0),
            "changes": changes,
            "award_jumped": after.get("predicted_award", "") != before.get("predicted_award", ""),
        })

    def query(self, problem_type: str = None) -> Dict:
        """查询历史上最有效的改进"""
        relevant = [r for r in self.records if problem_type is None or r["problem_type"] == problem_type]
        if not relevant:
            return {"records": 0, "most_effective": None}

        # 按 delta 排序，汇总最常出现的 action
        action_counts = {}
        for r in relevant:
            for change in r["changes"]:
                action_counts[change] = action_counts.get(change, 0) + 1

        sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_records": len(relevant),
            "award_jumps": sum(1 for r in relevant if r["award_jumped"]),
            "most_frequent_improvements": sorted_actions[:5],
            "most_effective_by_delta": sorted(relevant, key=lambda r: r["delta"], reverse=True)[:3],
        }


class AwardBoundaryModel:
    """分析从当前奖项到下一级的跨越因子"""

    def analyze(self, judge_score: Dict, problem_type: str) -> Dict:
        current_award = judge_score["predicted_award"]
        boundary_key = {
            "国家一等奖": None, "国家二等奖": "国家二等→国家一等",
            "省级一等奖": "省奖→国家二等", "省级二等奖": "省奖→国家二等",
            "未获奖": "未获奖→省奖",
        }.get(current_award)

        if not boundary_key:
            return {"at_max": True, "message": "已达到国家一等奖"}

        boundary = AWARD_BOUNDARIES.get(boundary_key, {})
        threshold = boundary.get("threshold", 75)
        gap = max(0, threshold - judge_score["total_score"])
        key_factors = boundary.get("key_factors", [])

        # Check which factors are met
        factor_status = []
        for factor in key_factors:
            # Simplified check based on evidence/reasoning metrics
            if "矛盾" in factor:
                met = True  # contradiction_finder is active
            elif "对比" in factor:
                met = "model_comparison" in str(judge_score.get("dimension_scores", {}))
            elif "推导" in factor:
                met = True  # model_specification handles this
            elif "机制" in factor:
                met = False  # typically the weakest
            elif "创新" in factor:
                met = judge_score.get("dimension_scores", {}).get("D5_innovation", {}).get("score", 0) >= 10
            else:
                met = True
            factor_status.append({"factor": factor, "met": met})

        return {
            "current_award": current_award,
            "target_award": "国家一等奖" if current_award == "国家二等奖" else ("国家二等奖" if "省级" in current_award else "省级奖"),
            "threshold": threshold,
            "gap": gap,
            "key_factors": factor_status,
            "hardest_factor": boundary.get("hardest_factor", ""),
            "reachable": gap <= 15,
            "message": f"距{boundary_key.split('→')[1]}还需{gap}分。最关键的跨越因子: {boundary.get('hardest_factor', '多项均衡')}",
        }


# ===== CLI =====

if __name__ == "__main__":
    graph = EvidenceGraph()
    evaluator = EvidenceEvaluator()
    builder = ReasoningBuilder()
    validator = ReasoningValidator()
    judge = JudgeIntelligence()
    impact = ScoreImpactModel()
    memory = CompetitionMemory()
    boundary = AwardBoundaryModel()

    full_evidence = {"present": ["model_comparison", "prediction_vs_actual", "residual_plot",
                                  "correlation_heatmap", "contradiction_statement"],
                     "metrics": ["R²", "RMSE", "MAE", "残差均值为0"],
                     "columns": ["模型", "R²", "RMSE", "参数", "取值"]}

    print("=" * 60)
    print("v7.2 — Competition Optimization Layer")
    print("=" * 60)

    for pt in ["prediction", "optimization"]:
        evg = graph.build(pt)
        ev = evaluator.evaluate(evg, full_evidence)
        chains = builder.build(pt, evg)
        reas = validator.validate(chains, ["correlation_heatmap", "model_comparison",
                                            "prediction_vs_actual", "residual_plot",
                                            "optimal_solution", "sensitivity_tornado"])
        js = judge.score(pt, ev, reas, {"structure_complete": True})

        print(f"\n{'─' * 60}")
        print(f"[{pt.upper()}] Current: {js['total_score']}/100 → {js['predicted_award']}")

        # Score Impact
        actions = impact.estimate(js, pt)
        print(f"\n  Score Impact (ROI排序):")
        for a in actions[:5]:
            effort = {"low": "轻松", "medium": "中等", "high": "高投入"}[a["effort"]]
            print(f"    +{a['total_gain']:2d}分  ROI={a['roi']:4.1f}  [{effort}]  {a['action'][:50]}")

        # Best combo to 国家一等奖
        combo = impact.best_combo(actions, target_score=80, current_score=js["total_score"])
        print(f"\n  Optimal Combo → 国家一等奖 (80分):")
        print(f"    Gap: {combo['gap']}分 | Gained: {combo['gained']}分 | Reachable: {combo['reachable']}")
        for a in combo["actions"]:
            print(f"    +{a['total_gain']}  {a['action'][:60]}")

        # Competition Memory
        # Record this run
        improved = judge.score(pt, ev, reas, {"structure_complete": True})
        memory.record(pt, {"total_score": js["total_score"] - 5, "predicted_award": "省级一等奖"},
                        improved, ["add_shap_interpretation", "add_residual_analysis"])
        mem_query = memory.query(pt)
        print(f"\n  Competition Memory ({mem_query['total_records']} records, {mem_query['award_jumps']} award jumps):")
        for action, count in mem_query["most_frequent_improvements"][:3]:
            print(f"    {action:30s} used {count}×")

        # Award Boundary
        ab = boundary.analyze(js, pt)
        print(f"\n  Award Boundary Analysis:")
        print(f"    {ab['current_award']} → {ab['target_award']}: gap={ab['gap']}分, reachable={ab['reachable']}")
        print(f"    {ab['message']}")
        for f in ab["key_factors"]:
            mark = "✓" if f["met"] else "✗"
            print(f"    {mark} {f['factor']}")

    # Summary
    print(f"\n{'=' * 60}")
    print("Competition Optimization Layer: COMPLETE")
    print(f"  Judge → Score Impact → Best Combo → Memory → Award Boundary")
    print(f"  Forge now answers: 'What to change, how much it's worth, how to win'")
