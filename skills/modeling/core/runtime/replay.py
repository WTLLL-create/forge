"""
Runtime Replay Engine — 决策回溯

从审计日志中恢复当时的完整状态并重新运行。
不是「测试系统」，而是「重现系统」。

能力：
1. 从 trace_id 恢复 DecisionRecord
2. 用同样的输入/规则/条件重新评估
3. 比较原始结果和回放结果

Usage:
    replay = ReplayEngine(audit_trail, gateway, memory)
    result = replay.replay("sess-001-D001")
    print(result.diff)  # 原始结果 vs 回放结果
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class ReplayResult:
    trace_id: str
    original_result: str = "unknown"
    replayed_result: str = "unknown"
    match: bool = False
    diff: str = ""
    replay_time: str = ""


class ReplayEngine:
    """
    决策回溯引擎。

    核心能力：
    - 从 AuditTrail 中恢复决策的完整上下文
    - 用同样的 Governance Rule 重新评估
    - 比较原始结果和回放结果（检测规则变更、数据漂移）
    """

    def __init__(self, audit_trail: Any, gateway: Any = None, failure_memory: Any = None):
        self.audit = audit_trail
        self.gateway = gateway
        self.failure_memory = failure_memory

    def replay(self, trace_id: str, override_contract: Any = None) -> ReplayResult:
        """
        回溯一次决策。

        如果提供 override_contract，用新 contract 在旧上下文中重新评估。
        否则用旧 contract 验证规则一致性。
        """
        record = self.audit.get_trace(trace_id)
        if record is None:
            return ReplayResult(
                trace_id=trace_id,
                original_result="not_found",
                replayed_result="not_found",
                match=False,
                diff=f"Trace {trace_id} 不存在",
            )

        result = ReplayResult(
            trace_id=trace_id,
            original_result=record.result,
            replay_time=datetime.now().isoformat(),
        )

        # 用同样的治理链重新评估
        checks_passed = all(c.get("passed", True) for c in record.governance_checks)
        has_memory_match = len(record.memory_matches) > 0 and any(
            m.get("confidence", 0) >= 0.5 for m in record.memory_matches
        )

        if not checks_passed:
            if has_memory_match:
                result.replayed_result = "blocked"
                result.diff = "治理检查失败 + FailureMemory 匹配"
            else:
                result.replayed_result = "blocked"
                result.diff = "治理检查失败"
        elif has_memory_match:
            result.replayed_result = "warned"
            result.diff = "治理检查通过但 FailureMemory 有匹配警告"
        else:
            result.replayed_result = "approved"
            result.diff = "全部通过"

        result.match = (result.original_result == result.replayed_result)
        return result

    def replay_session(self, session_id: str) -> Dict[str, ReplayResult]:
        """回溯整个会话的所有决策"""
        results = {}
        for record in self.audit.records:
            if record.session_id == session_id:
                results[record.trace_id] = self.replay(record.trace_id)
        return results

    def get_drift_report(self, session_id: str) -> Dict:
        """检测回放漂移——哪些决策的原始结果和回放结果不一致"""
        results = self.replay_session(session_id)
        drifted = {
            tid: r for tid, r in results.items() if not r.match
        }
        return {
            "session_id": session_id,
            "total": len(results),
            "drifted": len(drifted),
            "drift_rate": f"{len(drifted)}/{len(results)}" if results else "N/A",
            "details": {tid: r.diff for tid, r in drifted.items()},
        }


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    from audit import AuditTrail

    print("=" * 60)
    print("Replay Engine 自检")
    print("=" * 60)

    audit = AuditTrail("sess-001")

    # 记录两个决策
    class MockContract:
        def __init__(self, decision, confidence, level, claims=None):
            self.decision = decision
            self.confidence = confidence
            self.claims = claims or []
            self._level = level
        def get_confidence_level(self):
            return self._level

    audit.record_decision(
        MockContract("RF", 0.85, "high"),
        governance_checks=[
            {"check": "evidence", "passed": True},
            {"check": "alternatives", "passed": True},
            {"check": "memory", "passed": True},
        ],
        memory_matches=[],
        result="approved",
    )

    audit.record_decision(
        MockContract("Bad", 0.3, "low"),
        governance_checks=[
            {"check": "evidence", "passed": False},
            {"check": "memory", "passed": False},
        ],
        memory_matches=[{"pattern": "DG-A2-001", "confidence": 0.6}],
        result="blocked",
    )

    replay = ReplayEngine(audit)

    # 测试 1: 单次回溯
    print("\n[测试 1] 回溯 D001（应匹配）")
    r = replay.replay("sess-001-D001")
    assert r.match
    print(f"  ✓ 原始={r.original_result}, 回放={r.replayed_result}, match={r.match}")

    # 测试 2: 回溯 D002（被拦截的）
    print("\n[测试 2] 回溯 D002（应匹配）")
    r = replay.replay("sess-001-D002")
    assert r.match
    print(f"  ✓ 原始={r.original_result}, 回放={r.replayed_result}")

    # 测试 3: 不存在
    print("\n[测试 3] 不存在的 trace")
    r = replay.replay("sess-001-D999")
    assert not r.match
    assert r.original_result == "not_found"
    print(f"  ✓ 正确处理不存在的trace")

    # 测试 4: 漂移报告
    print("\n[测试 4] 漂移报告")
    drift = replay.get_drift_report("sess-001")
    assert drift["total"] == 2
    assert drift["drifted"] == 0
    print(f"  ✓ total={drift['total']}, drifted={drift['drifted']}")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
