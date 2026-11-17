"""
Knowledge Governance Layer v1.0 — 知识也需要治理
======================================================
Forge v7.5: 让知识像 Skill 一样拥有 lifecycle/boundary/validation/failure-linkage。

四大组件:
  KnowledgeLifecycle  — proposed → validated → active → deprecated
  ModelFamilyRouter    — 家族级检索 (evaluation/prediction/optimization family)
  KnowledgeFailureLink — 知识↔FailureMemory 双向联通
  KnowledgeValidator   — 提案 Knowledge 的 Benchmark 验证
"""
import sys, os
from datetime import datetime, timezone
from typing import Dict, List
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "knowledge"))
from model_knowledge_registry import KNOWLEDGE_BASE


# 知识生命周期
class KnowledgeState(Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


# 模型家族定义
MODEL_FAMILIES = {
    "evaluation": {
        "purpose": "多指标综合评价与排序",
        "decision_flow": ["确定指标体系", "选择赋权方法", "选择排序方法", "敏感性验证"],
        "members": {
            "weighting": ["entropy_weight", "critic"],
            "ranking": ["topsis"],
        },
        "selection_logic": {
            "客观数据为主·指标变异大": ["entropy_weight + topsis"],
            "指标间相关性强": ["critic + topsis"],
            "主观经验丰富": ["ahp + topsis"],
            "模糊定性指标": ["fuzzy + topsis"],
        },
    },
    "prediction": {
        "purpose": "连续/离散值预测与趋势分析",
        "decision_flow": ["数据特征分析", "选择模型族", "参数调优", "验证泛化"],
        "members": {
            "linear": ["linear_regression", "ridge"],
            "tree_ensemble": ["random_forest", "xgboost", "lightgbm"],
            "time_series": ["arima", "sarima", "prophet"],
            "deep": ["lstm", "transformer"],
        },
        "selection_logic": {
            "线性·N<200": ["linear_regression", "ridge"],
            "非线性·N>500": ["random_forest", "xgboost"],
            "时序·平稳": ["arima"],
            "时序·非平稳·N>200": ["sarima", "rf+lag"],
            "小样本·需要外推": ["机理模型", "gm(1,1)"],
        },
    },
    "optimization": {
        "purpose": "在约束下寻找最优解",
        "decision_flow": ["建立目标函数", "确定约束", "选择求解器", "可行性验证"],
        "members": {
            "exact": ["lp", "milp"],
            "metaheuristic": ["ga", "nsga_ii", "pso", "differential_evolution"],
            "gradient": ["slsqp", "l_bfgs_b"],
        },
        "selection_logic": {
            "线性·整数": ["lp", "milp"],
            "线性·变量<100": ["milp"],
            "非线性·凸": ["slsqp"],
            "非线性·非凸·变量<10": ["differential_evolution"],
            "多目标": ["nsga_ii", "moea_d"],
        },
    },
}


class KnowledgeLifecycle:
    """知识生命周期管理"""

    def __init__(self):
        self.registry = {
            mid: {"state": KnowledgeState.ACTIVE.value, "since": "2026-08-08",
                  "validated_by": "benchmark_match", "deprecation_reason": None}
            for mid in KNOWLEDGE_BASE
        }

    def propose(self, model_id: str, knowledge: Dict) -> Dict:
        self.registry[model_id] = {"state": KnowledgeState.PROPOSED.value, "since": datetime.now(timezone.utc).isoformat(),
                                     "validated_by": None, "deprecation_reason": None}
        return {"status": "proposed", "model_id": model_id, "message": "Knowledge proposal submitted for validation"}

    def validate(self, model_id: str, benchmark_result: Dict) -> Dict:
        if benchmark_result.get("passed", False):
            self.registry[model_id]["state"] = KnowledgeState.VALIDATED.value
            self.registry[model_id]["validated_by"] = "benchmark"
            return {"status": "validated", "model_id": model_id}
        return {"status": "rejected", "model_id": model_id, "reason": "Failed benchmark validation"}

    def activate(self, model_id: str) -> Dict:
        self.registry[model_id]["state"] = KnowledgeState.ACTIVE.value
        return {"status": "active", "model_id": model_id}

    def deprecate(self, model_id: str, reason: str) -> Dict:
        self.registry[model_id]["state"] = KnowledgeState.DEPRECATED.value
        self.registry[model_id]["deprecation_reason"] = reason
        return {"status": "deprecated", "model_id": model_id, "reason": reason}

    def get_state(self, model_id: str) -> str:
        return self.registry.get(model_id, {}).get("state", "unknown")

    def summary(self) -> Dict:
        states = {}
        for mid, entry in self.registry.items():
            s = entry["state"]
            states[s] = states.get(s, 0) + 1
        return {"total": len(self.registry), "by_state": states, "active_ratio": states.get("active", 0) / max(len(self.registry), 1)}


class ModelFamilyRouter:
    """家族级检索: 不直接推荐单模型，按决策流程推理"""

    def route(self, problem_context: Dict) -> Dict:
        ptype = problem_context.get("problem_type", "evaluation")
        family = MODEL_FAMILIES.get(ptype, MODEL_FAMILIES["evaluation"])
        features = problem_context.get("features", {})

        # 匹配 selection_logic
        matched_rules = []
        for condition, models in family.get("selection_logic", {}).items():
            if self._match_condition(condition, features):
                matched_rules.append({"condition": condition, "models": models})

        # 按决策流程推荐
        flow = []
        for step in family.get("decision_flow", []):
            flow.append({"step": step, "candidates": self._candidates_for_step(ptype, step)})

        return {
            "family": ptype,
            "purpose": family["purpose"],
            "decision_flow": flow,
            "matched_rules": matched_rules,
            "recommended_path": matched_rules[0]["models"] if matched_rules else None,
            "family_members": family["members"],
            "rationale": f"根据{', '.join(r['condition'] for r in matched_rules)}选择{matched_rules[0]['models']}"
                        if matched_rules else "需要更详细的特征信息",
        }

    def _match_condition(self, condition: str, features: Dict) -> bool:
        # 简化匹配
        for key, val in features.items():
            if key in condition or (isinstance(val, bool) and val and key in condition):
                return True
        return False

    def _candidates_for_step(self, ptype: str, step: str) -> List[str]:
        if "赋权" in step:
            return ["entropy_weight", "critic", "ahp"]
        if "排序" in step:
            return ["topsis", "grey_relational"]
        if "特征分析" in step:
            return ["correlation", "pca", "feature_importance"]
        if "选择模型" in step:
            family = MODEL_FAMILIES.get(ptype, {})
            members = family.get("members", {})
            return [m for group in members.values() for m in group]
        return []


class KnowledgeFailureLink:
    """知识↔FailureMemory 双向联通"""

    def __init__(self):
        self.links = []

    def link(self, model_id: str, failure_id: str, description: str):
        self.links.append({
            "model_id": model_id,
            "failure_id": failure_id,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def check(self, model_id: str) -> List[Dict]:
        """查询某个模型关联的所有失败记录"""
        return [l for l in self.links if l["model_id"] == model_id]

    def propose_update(self, model_id: str, failures: List[Dict]) -> Dict:
        """基于关联失败生成知识更新建议"""
        if not failures:
            return {"proposal": None}

        failure_types = [f["description"] for f in failures]
        knowledge = KNOWLEDGE_BASE.get(model_id, {})
        existing_failures = knowledge.get("failure_cases", [])

        new_failures = [f for f in failure_types if f not in existing_failures]

        if new_failures:
            return {
                "action": "update_knowledge",
                "model_id": model_id,
                "add_failure_cases": new_failures,
                "reason": f"Discovered {len(new_failures)} new failure patterns from FailureMemory",
                "confidence": 0.85,
            }
        return {"action": "no_change", "model_id": model_id}


class KnowledgeValidator:
    """提案知识的 Benchmark 验证"""

    def validate(self, model_id: str, tests: List[Dict]) -> Dict:
        passed = 0
        for test in tests:
            if test.get("expect_match", False):
                passed += 1

        return {
            "model_id": model_id,
            "tests": len(tests),
            "passed": passed,
            "all_pass": passed == len(tests),
            "verdict": "validated" if passed == len(tests) else "needs_revision",
        }

    def anti_gaming_check(self, model_id: str, recommendation: Dict) -> Dict:
        """检测是否存在为高分而推荐不适配模型的风险"""
        knowledge = KNOWLEDGE_BASE.get(model_id, {})
        avoid = knowledge.get("competition_pattern", {}).get("avoid_combinations", [])
        rec_models = str(recommendation.get("recommended_path", ""))

        violations = []
        for a in avoid:
            if a.split("(")[0].strip().lower() in rec_models.lower():
                violations.append(a)

        return {
            "safe": len(violations) == 0,
            "violations": violations,
            "verdict": "Safe — no knowledge gaming detected" if not violations else f"WARNING: {violations}",
        }


# ===== CLI =====

if __name__ == "__main__":
    lifecycle = KnowledgeLifecycle()
    router = ModelFamilyRouter()
    fail_link = KnowledgeFailureLink()
    validator = KnowledgeValidator()

    print("=" * 60)
    print("v7.5 — Knowledge Governance Layer")
    print("=" * 60)

    # Test 1: Lifecycle
    print("\n--- Test 1: Knowledge Lifecycle ---")
    lifecycle.propose("new_model", {"name": "Transformer"})
    lifecycle.validate("new_model", {"passed": True})
    lifecycle.activate("new_model")
    print(f"  Transformer: proposed → validated → active = {lifecycle.get_state('new_model')}")
    # Deprecate an existing model
    lifecycle.deprecate("entropy_weight", "被更新的CRITIC方法取代(仅示例)")
    summary = lifecycle.summary()
    print(f"  Registry: {summary['total']} models, {summary['by_state']}")
    print(f"  Active ratio: {summary['active_ratio']:.0%}")

    # Test 2: Model Family Router
    print("\n--- Test 2: Model Family Routing ---")
    for ctx in [
        {"problem_type": "evaluation", "features": {"客观数据": True, "指标变异大": True}},
        {"problem_type": "prediction", "features": {"非线性": True, "N_gt": 500}},
        {"problem_type": "optimization", "features": {"多目标": True}},
    ]:
        result = router.route(ctx)
        print(f"  [{result['family']:12s}] {result['rationale'][:70]}")
        if result["recommended_path"]:
            print(f"    → {result['recommended_path']}")

    # Test 3: Knowledge ↔ FailureMemory
    print("\n--- Test 3: Knowledge ↔ FailureMemory ---")
    fail_link.link("entropy_weight", "EVO-004", "熵权法未归一化导致权重偏差")
    fail_link.link("topsis", "EVO-005", "TOPSIS正负理想解定义颠倒")
    for mid in ["entropy_weight", "topsis"]:
        failures = fail_link.check(mid)
        proposal = fail_link.propose_update(mid, failures)
        print(f"  {mid}: {len(failures)} linked failures → {proposal['action']}")
        if proposal.get("add_failure_cases"):
            print(f"    New failure cases: {proposal['add_failure_cases']}")

    # Test 4: Anti-gaming
    print("\n--- Test 4: Anti-gaming Validation ---")
    rec = {"recommended_path": ["entropy_weight + topsis"]}
    check = validator.anti_gaming_check("entropy_weight", rec)
    print(f"  entropy_weight + topsis: {check['verdict']}")
    bad_rec = {"recommended_path": ["ahp"]}
    check2 = validator.anti_gaming_check("entropy_weight", bad_rec)
    print(f"  entropy_weight + ahp: {check2['verdict']}")

    print(f"\n{'=' * 60}")
    print("Knowledge Governance: COMPLETE")
    print(f"  Lifecycle: {summary['by_state']}")
    print(f"  Model Family Router: {len(MODEL_FAMILIES)} families")
    print(f"  Failure Links: {len(fail_link.links)}")
    print(f"  Anti-gaming: active")
    print(f"\n  Knowledge now has the same governance as Skills:")
    print(f"    proposed → validated → active → deprecated")
