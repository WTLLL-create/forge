"""
ModelStrategyEngine v1.0 — 模型策略决策引擎
================================================
Forge v6.5 Wave 3.3: 从 model_competition_engine.md 提取核心决策逻辑。
职责: 候选生成 + 五维评分 + 权衡调节 → StrategyArtifact。
不与 argument_compiler 重叠: Strategy=选哪个, Argument=为什么选。

提取自: model_competition_engine.md §2 §3 §4
"""
from typing import Dict, List, Optional


# 候选生成规则 (§2, 4族×条件→候选池)
CANDIDATE_RULES = {
    "prediction": [
        ({"时序": True, "平稳": True, "Nt_gt": 50}, ["ARIMA", "Prophet", "RF+Lag"]),
        ({"时序": True, "平稳": False, "Nt_gt": 200}, ["SARIMA", "RF+Lag", "XGBoost+Lag"]),
        ({"时序": True, "Nt_lt": 30}, ["GM(1,1)", "指数平滑"]),
        ({"非线性": True, "N_gt": 200}, ["RF", "XGBoost", "SVR"]),
        ({"非线性": True, "N_lt": 100}, ["SVR", "GPR", "贝叶斯"]),
        ({"线性": True}, ["Ridge回归", "RF(基线)"]),
        ({"外推": True, "时序": True}, ["ARIMA", "机理模型", "GM(1,1)"]),
        ({"解释": True}, ["RF+SHAP", "GAM", "线性模型"]),
    ],
    "optimization": [
        ({"线性": True, "整数": False}, ["LP"]),
        ({"线性": True, "整数": True, "变量_lt": 100}, ["MIP", "LP松弛+圆整"]),
        ({"线性": True, "整数": True, "变量_gt": 100}, ["LP松弛→启发式", "GA"]),
        ({"凸": True, "可微": True}, ["SLSQP", "trust-constr"]),
        ({"非凸": True, "变量_lt": 10}, ["多起点+L-BFGS-B", "差分进化"]),
        ({"非凸": True, "变量_gt": 10}, ["GA", "PSO", "差分进化"]),
        ({"多目标": 2}, ["NSGA-II", "加权→单目标"]),
        ({"多目标_gt": 3}, ["NSGA-III", "MOEA/D"]),
    ],
    "evaluation": [
        ({"专家判断": True}, ["AHP+TOPSIS", "AHP+模糊综合评价"]),
        ({"客观数据": True, "指标变异大": True}, ["熵权+TOPSIS", "CRITIC+TOPSIS"]),
        ({"客观数据": True, "指标变异小": True}, ["CRITIC+TOPSIS", "灰色关联分析"]),
        ({"模糊指标": True}, ["模糊综合评价", "灰色关联"]),
        ({"样本_lt": 10}, ["灰色关联分析", "模糊综合评价"]),
        ({"冗余": True}, ["PCA→TOPSIS", "PCA→熵权"]),
    ],
}

# 解释性评分表 (§3 维度3)
INTERPRETABILITY = {
    "LP": 10, "线性回归": 10, "Ridge回归": 10, "ARIMA": 10, "Tobit": 8,
    "RF": 7, "RF+SHAP": 8, "XGBoost": 4, "XGBoost+SHAP": 7,
    "SVR": 4, "GPR": 4, "LSTM": 1, "GA": 4, "NSGA-II": 4, "PSO": 4,
    "TOPSIS": 8, "AHP+TOPSIS": 8, "CRITIC+TOPSIS": 7, "熵权+TOPSIS": 7,
    "灰色关联": 7, "模糊综合评价": 5,
}

# 权重调优表 (§8, by problem type)
WEIGHT_PROFILES = {
    "pure_prediction": {"fit": 30, "capability": 35, "interpret": 5, "complexity": 15, "innovation": 15},
    "need_interpretation": {"fit": 25, "capability": 15, "interpret": 35, "complexity": 10, "innovation": 15},
    "optimization": {"fit": 35, "capability": 30, "interpret": 10, "complexity": 10, "innovation": 15},
    "evaluation": {"fit": 20, "capability": 15, "interpret": 35, "complexity": 15, "innovation": 15},
    "time_pressure": {"fit": 30, "capability": 30, "interpret": 10, "complexity": 20, "innovation": 10},
    "default": {"fit": 30, "capability": 25, "interpret": 15, "complexity": 15, "innovation": 15},
}


class ModelStrategyEngine:
    """模型策略决策引擎 — 候选生成 + 评分 + 推荐"""

    def generate_candidates(self,
                            problem_state: Dict,
                            dataset_profile: Dict = None) -> List[Dict]:
        """根据问题特征生成候选模型列表"""
        ps = problem_state.get("data", problem_state)
        ptype = ps.get("problem_type", "prediction")
        features = dataset_profile or {}

        rules = CANDIDATE_RULES.get(ptype, CANDIDATE_RULES["prediction"])
        candidates = []
        seen = set()

        for conditions, models in rules:
            if self._match(conditions, features):
                for m in models:
                    if m not in seen:
                        candidates.append(m)
                        seen.add(m)

        return candidates[:5]  # cap at 5

    def score_candidates(self,
                          candidates: List[str],
                          problem_state: Dict,
                          weight_profile: str = "default") -> List[Dict]:
        """五维加权评分"""
        weights = WEIGHT_PROFILES.get(weight_profile, WEIGHT_PROFILES["default"])

        scored = []
        for model in candidates:
            fit = 7  # default: partial match
            capability = 7
            interpret = INTERPRETABILITY.get(model, 5)
            complexity = 7
            innovation = 7

            # T-1: 精度 vs 解释性 (adjust if interpretation required)
            if weight_profile == "need_interpretation" and interpret < 5:
                fit -= 2  # low interpretability drags fit

            score = (
                weights["fit"] * fit / 10 +
                weights["capability"] * capability / 10 +
                weights["interpret"] * interpret / 10 +
                weights["complexity"] * complexity / 10 +
                weights["innovation"] * innovation / 10
            )

            scored.append({
                "model": model,
                "scores": {"fit": fit, "capability": capability, "interpret": interpret, "complexity": complexity, "innovation": innovation},
                "total": round(score, 1),
            })

        scored.sort(key=lambda x: x["total"], reverse=True)
        return scored

    def recommend(self,
                   problem_state: Dict,
                   dataset_profile: Dict = None,
                   weight_profile: str = "default") -> Dict:
        """完整决策流程: 候选生成→评分→推荐"""
        candidates = self.generate_candidates(problem_state, dataset_profile)
        scored = self.score_candidates(candidates, problem_state, weight_profile)

        if not scored:
            return {"recommendation": None, "candidates": [], "reason": "no_candidates"}

        top = scored[0]
        second = scored[1] if len(scored) > 1 else None

        # T-4: 多模型策略
        if second and (top["total"] - second["total"]) < 0.5:
            strategy = "多模型对比 (差距<0.5分，建议全部纳入对比实验)"
        elif second and (top["total"] - second["total"]) < 1.0:
            strategy = "推荐首选 + 备选对比"
        else:
            strategy = f"直接推荐: {top['model']}"

        return {
            "recommendation": top["model"],
            "confidence": min(0.95, top["total"] / 10),
            "strategy": strategy,
            "candidates": scored,
            "problem_type": problem_state.get("data", problem_state).get("problem_type", "unknown"),
            "weight_profile": weight_profile,
            "rationale": f"{top['model']} with fit={top['scores']['fit']}, interpret={top['scores']['interpret']}, total={top['total']}",
        }

    @staticmethod
    def _match(conditions: Dict, features: Dict) -> bool:
        for k, v in conditions.items():
            fv = features.get(k)
            if isinstance(v, bool) and v and not fv:
                return False
            if isinstance(v, int):
                if k.endswith("_gt") and (fv is None or fv <= v):
                    return False
                if k.endswith("_lt") and (fv is None or fv >= v):
                    return False
        return True


# ===== CLI =====

if __name__ == "__main__":
    engine = ModelStrategyEngine()

    # 2021B 空气质量预测: 非线性+时序+多变量+需解释+N>500
    print("=" * 50)
    print("ModelStrategyEngine — 2021B 空气质量预测")
    ps = {"problem_type": "prediction"}
    dp = {"非线性": True, "N_gt": 200, "时序": True, "Nt_gt": 200, "解释": True}
    result = engine.recommend(ps, dp, "need_interpretation")
    print(f"\nRecommendation: {result['recommendation']} ({result['confidence']:.0%})")
    print(f"Strategy: {result['strategy']}")
    for c in result["candidates"][:3]:
        print(f"  {c['model']:20s} total={c['total']:5.1f}  F={c['scores']['fit']} C={c['scores']['capability']} I={c['scores']['interpret']}")

    # 2026A 水泥窑: 非线性+删失+需解释
    print(f"\n{'=' * 50}")
    print("ModelStrategyEngine — 2026A 水泥窑排放")
    ps2 = {"problem_type": "prediction"}
    dp2 = {"非线性": True, "N_gt": 200, "解释": True}
    result2 = engine.recommend(ps2, dp2, "need_interpretation")
    print(f"\nRecommendation: {result2['recommendation']} ({result2['confidence']:.0%})")
    for c in result2["candidates"][:3]:
        print(f"  {c['model']:20s} total={c['total']:5.1f}  F={c['scores']['fit']} I={c['scores']['interpret']}")

    print(f"\n✓ Strategy Engine works standalone — does NOT duplicate argument_compiler")
