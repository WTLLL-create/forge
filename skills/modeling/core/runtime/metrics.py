"""
Runtime Metrics — 运行时指标系统

不是「代码有多少行」，而是「系统在运行时表现如何」。

四个核心指标组：
  governance —  治理效果（拒绝率/误报率/Memory触发频率）
  reasoning —   推理质量（平均置信度/证据充分率）
  execution —   执行效率（通过率/回退率）
  memory —      经验系统健康（Pattern数量/过期率/冲突率）
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class MetricsSnapshot:
    """一次指标快照"""
    timestamp: str
    category: str
    metrics: Dict[str, float] = field(default_factory=dict)


class MetricsCollector:
    """
    运行时指标收集器。

    设计约束：
    - 不存储原始数据（AuditTrail 负责）
    - 只存储聚合指标
    - 每次采集生成快照
    """

    def __init__(self):
        self.snapshots: Dict[str, List[MetricsSnapshot]] = {
            "governance": [],
            "reasoning": [],
            "execution": [],
            "memory": [],
        }
        self._counters: Dict[str, int] = {}

    def collect_governance(self, decisions: List[Any]) -> MetricsSnapshot:
        """收集治理指标"""
        total = len(decisions)
        if total == 0:
            snap = MetricsSnapshot(timestamp=datetime.now().isoformat(), category="governance")
            self.snapshots["governance"].append(snap)
            return snap

        blocked = sum(1 for d in decisions if getattr(d, 'result', '') == "blocked")
        approved = sum(1 for d in decisions if getattr(d, 'result', '') == "approved")
        warned = sum(1 for d in decisions if getattr(d, 'result', '') == "warned")
        memory_triggered = sum(1 for d in decisions if getattr(d, 'memory_matches', []))

        snap = MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            category="governance",
            metrics={
                "total_decisions": float(total),
                "block_rate": blocked / total,
                "approval_rate": approved / total,
                "warn_rate": warned / total,
                "memory_trigger_rate": memory_triggered / total if total else 0,
                "false_positive_rate": 0.0,  # 需要 Benchmark F1/F2 更新
            },
        )
        self.snapshots["governance"].append(snap)
        return snap

    def collect_reasoning(self, contracts: List[Any]) -> MetricsSnapshot:
        """收集推理质量指标"""
        total = len(contracts)
        if total == 0:
            snap = MetricsSnapshot(timestamp=datetime.now().isoformat(), category="reasoning")
            self.snapshots["reasoning"].append(snap)
            return snap

        confidences = [c.confidence for c in contracts if hasattr(c, 'confidence')]
        claims_counts = [len(c.claims) for c in contracts if hasattr(c, 'claims')]
        alt_counts = [len(c.alternatives_excluded) for c in contracts if hasattr(c, 'alternatives_excluded')]

        snap = MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            category="reasoning",
            metrics={
                "total_contracts": float(total),
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
                "avg_claims": sum(claims_counts) / len(claims_counts) if claims_counts else 0,
                "avg_alternatives": sum(alt_counts) / len(alt_counts) if alt_counts else 0,
                "low_confidence_rate": sum(1 for c in confidences if c < 0.6) / total if total else 0,
                "high_confidence_rate": sum(1 for c in confidences if c >= 0.85) / total if total else 0,
            },
        )
        self.snapshots["reasoning"].append(snap)
        return snap

    def collect_execution(self, sessions: List[Dict]) -> MetricsSnapshot:
        """收集执行效率指标"""
        total = len(sessions)
        if total == 0:
            snap = MetricsSnapshot(timestamp=datetime.now().isoformat(), category="execution")
            self.snapshots["execution"].append(snap)
            return snap

        completed = sum(1 for s in sessions if s.get("status") == "completed")
        errors = sum(1 for s in sessions if s.get("status") == "error")

        snap = MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            category="execution",
            metrics={
                "total_sessions": float(total),
                "completion_rate": completed / total,
                "error_rate": errors / total,
            },
        )
        self.snapshots["execution"].append(snap)
        return snap

    def collect_memory(self, failure_memory: Any) -> MetricsSnapshot:
        """收集经验系统健康指标"""
        if failure_memory is None:
            snap = MetricsSnapshot(timestamp=datetime.now().isoformat(), category="memory")
            self.snapshots["memory"].append(snap)
            return snap

        patterns = failure_memory.patterns if hasattr(failure_memory, 'patterns') else {}
        active = sum(1 for p in patterns.values() if p.status == "active")
        deprecated = sum(1 for p in patterns.values() if p.status == "deprecated")
        avg_confidence = sum(p.confidence for p in patterns.values()) / len(patterns) if patterns else 0

        snap = MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            category="memory",
            metrics={
                "total_patterns": float(len(patterns)),
                "active_patterns": float(active),
                "deprecated_patterns": float(deprecated),
                "avg_confidence": avg_confidence,
            },
        )
        self.snapshots["memory"].append(snap)
        return snap

    def get_latest(self, category: str) -> Optional[MetricsSnapshot]:
        """获取最新的指标快照"""
        snaps = self.snapshots.get(category, [])
        return snaps[-1] if snaps else None

    def get_summary(self) -> Dict[str, Any]:
        """全维度汇总"""
        summary = {}
        for cat in ["governance", "reasoning", "execution", "memory"]:
            latest = self.get_latest(cat)
            summary[cat] = latest.metrics if latest else {}
        return summary


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Runtime Metrics 自检")
    print("=" * 60)

    mc = MetricsCollector()

    # 测试 1: 治理指标
    print("\n[测试 1] 治理指标")
    decisions = [
        type("D", (), {"result": "approved"})(),
        type("D", (), {"result": "blocked"})(),
        type("D", (), {"result": "approved", "memory_matches": [{"pattern": "DG-A2-001"}]})(),
    ]
    snap = mc.collect_governance(decisions)
    assert snap.metrics["block_rate"] == 1/3
    assert snap.metrics["approval_rate"] == 2/3
    assert snap.metrics["memory_trigger_rate"] == 1/3
    print(f"  ✓ block_rate={snap.metrics['block_rate']:.0%}, approval={snap.metrics['approval_rate']:.0%}")

    # 测试 2: 推理指标
    print("\n[测试 2] 推理指标")
    try:
        from core.contracts.decision import DecisionContract, Claim
        from core.contracts.evidence import Evidence
    except ImportError:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from core.contracts.decision import DecisionContract, Claim
        from core.contracts.evidence import Evidence
    contracts = [
        DecisionContract("A", claims=[Claim("v", Evidence.experimental("d"))], confidence=0.9),
        DecisionContract("B", confidence=0.3),
    ]
    snap = mc.collect_reasoning(contracts)
    assert snap.metrics["avg_confidence"] == 0.6
    assert snap.metrics["low_confidence_rate"] == 0.5
    print(f"  ✓ avg_confidence={snap.metrics['avg_confidence']:.1f}, low_conf_rate={snap.metrics['low_confidence_rate']:.0%}")

    # 测试 3: 汇总
    print("\n[测试 3] 全维度汇总")
    summary = mc.get_summary()
    assert "governance" in summary
    assert "reasoning" in summary
    print(f"  ✓ {len(summary)} 个维度")

    # 测试 4: 空数据
    print("\n[测试 4] 空数据")
    snap = mc.collect_governance([])
    assert snap.metrics == {}
    print(f"  ✓ 空数据正常")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
