"""
Knowledge Quality Intelligence v1.0 — 知识不仅要存在，还要足够好
========================================================================
Forge v7.7: 5维知识质量评分 + Quality Gap Report + Blind Benchmark Readiness。

五个维度:
  mathematical_integrity   — 公式/推导/假设是否完整
  competition_fitness      — 是否适配竞赛题型和评分标准
  case_coverage            — 是否有CUMCM案例支撑
  failure_awareness        — 是否记录已知失败模式
  timeliness               — 知识是否更新

输出 Knowledge Quality Score + Readiness Assessment。
"""
import sys, os
from datetime import datetime, timezone
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "knowledge"))
from model_knowledge_registry import KNOWLEDGE_BASE


QUALITY_RUBRIC = {
    "mathematical_integrity": {
        "weight": 0.30,
        "checks": ["mathematical_core.formula", "mathematical_core.steps", "assumptions"],
        "description": "公式+推导步骤+假设是否完整",
    },
    "competition_fitness": {
        "weight": 0.25,
        "checks": ["competition_pattern.trigger_conditions", "competition_pattern.typical_pairings", "competition_pattern.avoid_combinations"],
        "description": "是否适配竞赛题型和评分标准",
    },
    "case_coverage": {
        "weight": 0.20,
        "checks": ["source_papers", "evidence_links"],
        "description": "是否有CUMCM案例和实践证据",
    },
    "failure_awareness": {
        "weight": 0.15,
        "checks": ["failure_cases", "limitations"],
        "description": "是否记录已知失败模式和限制",
    },
    "timeliness": {
        "weight": 0.10,
        "checks": ["confidence"],
        "description": "知识时效性和置信度",
    },
}


class KnowledgeQualityEvaluator:
    """5维知识质量评分"""

    def evaluate(self, model_id: str) -> Dict:
        knowledge = KNOWLEDGE_BASE.get(model_id, {})
        if not knowledge:
            return {"model_id": model_id, "exists": False, "overall_score": 0, "status": "missing"}

        scores = {}
        details = {}
        gaps = []

        for dim, rubric in QUALITY_RUBRIC.items():
            score = 0
            dim_gaps = []

            for check in rubric["checks"]:
                parts = check.split(".")
                node = knowledge
                for p in parts:
                    if isinstance(node, dict):
                        node = node.get(p, {})
                    elif isinstance(node, list):
                        break
                    else:
                        break

                if (isinstance(node, list) and len(node) > 0) or (isinstance(node, str) and len(node) > 10) or (isinstance(node, dict) and len(node) > 0):
                    score += 1
                else:
                    dim_gaps.append(check)

            max_score = len(rubric["checks"])
            pct = int(score / max(max_score, 1) * 100)
            scores[dim] = pct
            details[dim] = {"score": score, "max": max_score, "pct": pct, "gaps": dim_gaps}
            if dim_gaps:
                gaps.append({"dimension": dim, "gaps": dim_gaps, "impact": "medium" if pct < 67 else "low"})

        overall = sum(scores[d] * QUALITY_RUBRIC[d]["weight"] for d in scores)
        overall = int(overall)

        # Quality status
        if overall >= 85:
            status = "excellent"
            readiness = "ready"
        elif overall >= 70:
            status = "good"
            readiness = "ready_with_caution"
        elif overall >= 50:
            status = "adequate"
            readiness = "needs_improvement"
        else:
            status = "insufficient"
            readiness = "not_ready"

        return {
            "model_id": model_id,
            "model_name": knowledge.get("model_identity", {}).get("name", model_id),
            "exists": True,
            "overall_score": overall,
            "status": status,
            "blind_benchmark_readiness": readiness,
            "dimension_scores": scores,
            "dimension_details": details,
            "gaps": gaps,
            "gap_count": len(gaps),
            "recommendation": self._recommendation(overall, scores, model_id),
        }

    def _recommendation(self, overall: int, scores: dict, model_id: str) -> str:
        weakest = min(scores, key=scores.get)
        weakest_name = {
            "case_coverage": "案例覆盖",
            "failure_awareness": "失败模式记录",
            "competition_fitness": "竞赛适配",
            "mathematical_integrity": "数学完整性",
            "timeliness": "时效性",
        }.get(weakest, weakest)

        if overall >= 85:
            return f"{model_id} 知识质量优秀，可以进入 Blind Benchmark"
        elif overall >= 70:
            return f"{model_id} 基本达标，{weakest_name}需要加强后进入盲测"
        elif overall >= 50:
            return f"{model_id} 需要改进: {weakest_name}是主要短板"
        else:
            return f"{model_id} 知识质量不足，建议先补充核心内容再测试"

    def batch_evaluate(self) -> Dict:
        """批量评估所有注册知识"""
        results = {}
        for mid in KNOWLEDGE_BASE:
            results[mid] = self.evaluate(mid)

        avg_score = sum(r["overall_score"] for r in results.values()) / max(len(results), 1)
        ready = sum(1 for r in results.values() if r["blind_benchmark_readiness"] in ("ready", "ready_with_caution"))
        not_ready = len(results) - ready

        return {
            "total_models": len(results),
            "average_score": round(avg_score),
            "ready_for_blind": ready,
            "needs_improvement": not_ready,
            "overall_readiness": "READY" if avg_score >= 70 else "PARTIAL",
            "human_correction_estimate": self._estimate_correction_cost(avg_score),
            "models": results,
        }

    def _estimate_correction_cost(self, avg_score: float) -> str:
        if avg_score >= 85:
            return "低 (<20% 内容需人工修改)"
        elif avg_score >= 70:
            return "中等 (20-40% 内容需人工修改)"
        elif avg_score >= 50:
            return "较高 (40-60% 内容需人工修改)"
        else:
            return "高 (>60% 需人工重写)"


# ===== CLI =====

if __name__ == "__main__":
    evaluator = KnowledgeQualityEvaluator()

    print("=" * 60)
    print("v7.7 — Knowledge Quality Intelligence")
    print("=" * 60)

    # Individual evaluation
    for mid in ["entropy_weight", "topsis", "critic", "reaction_kinetics"]:
        result = evaluator.evaluate(mid)
        print(f"\n[{mid:20s}] Score={result['overall_score']:3d} [{result['blind_benchmark_readiness']:20s}]")
        for dim, pct in result["dimension_scores"].items():
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            print(f"  {dim:25s} [{bar}] {pct:3d}%")
        if result["gaps"]:
            for g in result["gaps"]:
                print(f"    GAP [{g['dimension']}]: {g['gaps']}")

    # Batch evaluation
    print(f"\n{'=' * 60}")
    print("Batch Quality Assessment")
    print(f"{'=' * 60}")
    batch = evaluator.batch_evaluate()

    print(f"\n  Models: {batch['total_models']}")
    print(f"  Average Score: {batch['average_score']}")
    print(f"  Ready for Blind: {batch['ready_for_blind']}/{batch['total_models']}")
    print(f"  Needs Improvement: {batch['needs_improvement']}")
    print(f"  Human Correction: {batch['human_correction_estimate']}")

    print(f"\n  Summary:")
    for mid, result in batch["models"].items():
        readiness_label = result["blind_benchmark_readiness"]
        mark = "✓" if readiness_label in ("ready", "ready_with_caution") else "✗"
        print(f"    {mark} {result['model_name']:15s} {result['overall_score']:3d} [{readiness_label:20s}] {result['recommendation'][:60]}")

    print(f"\n{'=' * 60}")
    print(f"Blind Benchmark Readiness: {batch['overall_readiness']}")
    print(f"  Ready: {batch['ready_for_blind']}/{batch['total_models']}")
    print(f"  Human correction: {batch['human_correction_estimate']}")
    print(f"\n  Next: Blind CUMCM Benchmark with real unseen problems")
