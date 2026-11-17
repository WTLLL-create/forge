"""
Knowledge Router v1.0 — 模型知识检索 + Pattern 匹配
==========================================================
Forge v7.4: 连接 Knowledge Layer 与 Pattern/Strategy 层。
消费 ModelKnowledgeRegistry，输出 KnowledgeRetrievalArtifact。
"""
import sys, os, json
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "knowledge"))
from model_knowledge_registry import KNOWLEDGE_BASE


class KnowledgeRouter:
    """统一模型知识检索 + 触发条件匹配"""

    def retrieve(self, problem_context: Dict) -> Dict:
        """
        根据 ProblemContext 检索匹配的模型知识。

        Args:
            problem_context: {"problem_type": "evaluation", "keywords": ["评价", "权重"], "features": {"客观数据": True, ...}}

        Returns:
            KnowledgeRetrievalArtifact: matched models with confidence and evidence
        """
        ptype = problem_context.get("problem_type", "evaluation")
        keywords = problem_context.get("keywords", [])
        features = problem_context.get("features", {})

        matches = []
        for model_id, model in KNOWLEDGE_BASE.items():
            score = 0

            # 题型匹配
            if ptype in model.get("problem_types", []):
                score += 40

            # 关键词匹配
            for kw in keywords:
                identity = model["model_identity"]
                if kw in identity["name"] or any(kw in a for a in identity["aliases"]):
                    score += 20
                for adv in model.get("advantages", []):
                    if kw in adv:
                        score += 10

            # 特征匹配
            triggers = model.get("competition_pattern", {}).get("trigger_conditions", [])
            for feat_key, feat_val in features.items():
                if feat_val:
                    for trigger in triggers:
                        if feat_key in trigger or str(feat_val) in trigger:
                            score += 15

            if score > 0:
                matches.append({
                    "model_id": model_id,
                    "model_name": model["model_identity"]["name"],
                    "category": model["model_identity"]["category"],
                    "score": score,
                    "confidence": model.get("confidence", 0.8),
                    "typical_pairings": model.get("competition_pattern", {}).get("typical_pairings", []),
                    "avoid_combinations": model.get("competition_pattern", {}).get("avoid_combinations", []),
                    "trigger_conditions": triggers,
                    "source_papers": model.get("source_papers", []),
                    "limitations": model.get("limitations", []),
                })

        matches.sort(key=lambda m: m["score"], reverse=True)
        top = matches[:5] if matches else []

        # Strategy recommendation
        if top:
            primary = top[0]
            pairings = primary.get("typical_pairings", [])
            if pairings:
                parts = pairings[0].replace(" → ", "→").split("→")
                combo_suffix = parts[-1].strip() if len(parts) > 1 else pairings[0]
                recommended_combo = f"{primary['model_name']} + {combo_suffix}"
            else:
                recommended_combo = primary["model_name"]
        else:
            recommended_combo = None

        return {
            "retrieval_id": f"KR-{ptype}",
            "problem_type": ptype,
            "matched_models": top,
            "match_count": len(top),
            "recommended_combo": recommended_combo,
            "confidence": top[0]["confidence"] if top else 0,
            "strategy_hint": self._strategy_hint(top[0]) if top else "No matching model found",
        }

    def _strategy_hint(self, match: Dict) -> str:
        name = match["model_name"]
        pairings = match.get("typical_pairings", [])
        avoid = match.get("avoid_combinations", [])
        hint = f"推荐: {name}"
        if pairings:
            hint += f"。常见组合: {pairings[0]}"
        if avoid:
            hint += f"。避免: {', '.join(avoid[:2])}"
        return hint

    def query_model(self, model_id: str) -> Dict:
        """直接查询单个模型的完整知识"""
        return KNOWLEDGE_BASE.get(model_id, {})


# ===== Benchmark =====

def benchmark():
    router = KnowledgeRouter()
    tests = [
        {
            "name": "城市综合评价",
            "context": {"problem_type": "evaluation", "keywords": ["评价", "权重", "排序", "指标"],
                        "features": {"客观数据": True, "指标变异大": True}},
            "expect": ["entropy_weight", "topsis", "critic"],
            "avoid": ["reaction_kinetics"],
        },
        {
            "name": "化工反应温度优化",
            "context": {"problem_type": "optimization", "keywords": ["反应", "温度", "速率", "活化能"],
                        "features": {"约束": True}},
            "expect": ["reaction_kinetics"],
            "avoid": ["topsis"],
        },
        {
            "name": "预测模型选择(无评价指标)",
            "context": {"problem_type": "prediction", "keywords": ["预测", "回归", "时序"],
                        "features": {"非线性": True}},
            "expect": [],
            "avoid": ["entropy_weight", "topsis", "critic"],
        },
        {
            "name": "客观赋权+方案排序",
            "context": {"problem_type": "evaluation", "keywords": ["赋权", "方案", "对比", "客观"],
                        "features": {"客观数据": True, "指标间相关": True}},
            "expect": ["entropy_weight", "topsis", "critic"],
            "avoid": [],
        },
    ]

    passed = 0
    print("=" * 60)
    print("v7.4 — Knowledge Router Benchmark")
    print("=" * 60)

    for test in tests:
        result = router.retrieve(test["context"])
        matched_ids = [m["model_id"] for m in result["matched_models"]]

        expected_hit = all(e in matched_ids for e in test["expect"]) if test["expect"] else True
        avoid_hit = all(a not in matched_ids for a in test["avoid"]) if test["avoid"] else True
        ok = expected_hit and avoid_hit

        if ok:
            passed += 1

        status = "PASS" if ok else "FAIL"
        print(f"\n[{status}] {test['name']}")
        print(f"  Type: {test['context']['problem_type']}, Keywords: {test['context']['keywords']}")
        print(f"  Expect: {test['expect']}, Avoid: {test['avoid']}")
        print(f"  Matched: {matched_ids}")
        if result["recommended_combo"]:
            print(f"  Strategy: {result['recommended_combo']} (conf={result['confidence']:.0%})")
        if result.get("matched_models"):
            top = result["matched_models"][0]
            print(f"  Hint: {result['strategy_hint'][:80]}")

    print(f"\n{'=' * 60}")
    print(f"Benchmark: {passed}/{len(tests)} passed")
    print(f"Knowledge Router: {'READY' if passed == len(tests) else 'NEEDS TUNING'}")

    return passed


if __name__ == "__main__":
    benchmark()
