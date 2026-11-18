"""
Runtime Audit Trail — 统一审计日志

不是「记录结果」，而是「记录因果链」。
每个决策的完整推理路径：问题→证据→推理→治理→结论。

当系统出错时，可以从审计日志中回溯：
  1. 当时输入了什么？
  2. 什么证据支撑了决策？
  3. 什么治理规则检查了它？
  4. 为什么最终通过/拒绝？

Usage:
    audit = AuditTrail(session_id="sess-001")
    audit.record_decision(contract, reasoning, governance, result)
    audit.replay(trace_id)  # 回溯某次决策
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


@dataclass
class DecisionRecord:
    """一个决策的完整审计记录"""
    trace_id: str
    session_id: str
    timestamp: str

    # 决策本身
    decision: str
    claims: List[Dict] = field(default_factory=list)

    # 推理链（为什么）
    problem_context: Dict[str, Any] = field(default_factory=dict)  # 问题特征
    evidence_chain: List[Dict] = field(default_factory=list)       # 证据→结论的步骤
    alternatives: List[Dict] = field(default_factory=list)         # 排除的替代方案

    # 治理链（怎么检查的）
    governance_checks: List[Dict] = field(default_factory=list)    # Gateway 检查项+结果
    memory_matches: List[Dict] = field(default_factory=list)       # FailureMemory 匹配
    confidence: float = 0.0
    confidence_level: str = ""

    # 结果
    result: str = ""           # approved / blocked / warned
    result_reason: str = ""

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "decision": self.decision,
            "claims": self.claims,
            "problem_context": self.problem_context,
            "evidence_chain": self.evidence_chain,
            "alternatives": self.alternatives,
            "governance_checks": self.governance_checks,
            "memory_matches": self.memory_matches,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "result": self.result,
            "result_reason": self.result_reason,
        }


class AuditTrail:
    """
    统一审计日志。

    核心原则：
    - 每个决策产生一条 DecisionRecord
    - Record 包含完整的因果链：问题→证据→推理→治理→结论
    - 可以通过 trace_id 回溯任意决策的完整上下文
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.records: List[DecisionRecord] = []
        self._counter = 0

    def record_decision(
        self,
        contract: Any,
        evidence_chain: List[Dict] = None,
        governance_checks: List[Dict] = None,
        memory_matches: List[Dict] = None,
        problem_context: Dict = None,
        result: str = "approved",
        result_reason: str = "",
    ) -> DecisionRecord:
        """记录一个决策的完整审计信息"""
        self._counter += 1
        trace_id = f"{self.session_id}-D{self._counter:03d}"

        # 提取 claims
        claims = []
        if hasattr(contract, 'claims'):
            for c in contract.claims:
                claims.append({
                    "statement": c.statement,
                    "evidence_type": c.evidence.evidence_type.value if hasattr(c.evidence, 'evidence_type') else "unknown",
                    "evidence_data": c.evidence.data if hasattr(c.evidence, 'data') else None,
                })

        # 提取 alternatives
        alternatives = []
        if hasattr(contract, 'alternatives_excluded'):
            for a in contract.alternatives_excluded:
                alternatives.append({
                    "name": a.name,
                    "reason": a.reason,
                })

        record = DecisionRecord(
            trace_id=trace_id,
            session_id=self.session_id,
            timestamp=datetime.now().isoformat(),
            decision=contract.decision if hasattr(contract, 'decision') else str(contract),
            claims=claims,
            problem_context=problem_context or {},
            evidence_chain=evidence_chain or [],
            alternatives=alternatives,
            governance_checks=governance_checks or [],
            memory_matches=memory_matches or [],
            confidence=contract.confidence if hasattr(contract, 'confidence') else 0.0,
            confidence_level=contract.get_confidence_level() if hasattr(contract, 'get_confidence_level') else "unknown",
            result=result,
            result_reason=result_reason,
        )

        self.records.append(record)
        return record

    def get_trace(self, trace_id: str) -> Optional[DecisionRecord]:
        """通过 trace_id 检索决策记录"""
        for r in self.records:
            if r.trace_id == trace_id:
                return r
        return None

    def get_session_summary(self) -> Dict:
        """会话摘要"""
        approved = sum(1 for r in self.records if r.result == "approved")
        blocked = sum(1 for r in self.records if r.result == "blocked")
        warned = sum(1 for r in self.records if r.result == "warned")

        return {
            "session_id": self.session_id,
            "total_decisions": len(self.records),
            "approved": approved,
            "blocked": blocked,
            "warned": warned,
            "block_rate": f"{blocked}/{len(self.records)}" if self.records else "0/0",
            "avg_confidence": sum(r.confidence for r in self.records) / len(self.records) if self.records else 0,
        }

    def export(self) -> str:
        """导出为 JSON"""
        return json.dumps({
            "session_id": self.session_id,
            "records": [r.to_dict() for r in self.records],
            "summary": self.get_session_summary(),
        }, ensure_ascii=False, indent=2)


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    try:
        from core.contracts.decision import DecisionContract, Claim
        from core.contracts.evidence import Evidence, EvidenceType
    except ImportError:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from core.contracts.decision import DecisionContract, Claim
        from core.contracts.evidence import Evidence, EvidenceType

    print("=" * 60)
    print("Audit Trail 自检")
    print("=" * 60)

    audit = AuditTrail("sess-001")

    # 测试 1: 记录决策
    print("\n[测试 1] 记录完整决策")
    contract = DecisionContract(
        decision="选择 RF",
        claims=[
            Claim("非线性", Evidence.experimental("Spearman r=0.78")),
            Claim("优于基线", Evidence.experimental("CV:0.23 vs 0.41")),
        ],
        confidence=0.85,
    )
    rec = audit.record_decision(
        contract,
        evidence_chain=[
            {"step": 1, "action": "Spearman相关性检验", "result": "r=0.78，非线性显著"},
            {"step": 2, "action": "3折CV对比", "result": "RF:0.23, ARIMA:0.41, LR:0.38"},
        ],
        governance_checks=[
            {"check": "evidence_backed", "passed": True},
            {"check": "alternatives_excluded", "passed": True},
            {"check": "memory_governance", "passed": True},  # F1: no pattern match
        ],
        memory_matches=[],
        problem_context={"problem_type": "预测", "sample_size": 200},
        result="approved",
    )
    assert rec.trace_id == "sess-001-D001"
    print(f"  ✓ trace_id={rec.trace_id}, result={rec.result}, confidence={rec.confidence}")

    # 测试 2: 记录被拦截的决策
    print("\n[测试 2] 记录被拦截决策")
    bad_contract = DecisionContract(decision="选 XGBoost（无证据）", confidence=0.3)
    rec2 = audit.record_decision(
        bad_contract,
        governance_checks=[
            {"check": "evidence_backed", "passed": False, "detail": "无实验证据"},
            {"check": "memory_governance", "passed": False, "detail": "DG-A2-001 matched"},
        ],
        memory_matches=[{"pattern": "DG-A2-001", "confidence": 0.6}],
        result="blocked",
        result_reason="缺少实验证据 + Evidence Dominance Failure",
    )
    assert rec2.result == "blocked"
    print(f"  ✓ trace_id={rec2.trace_id}, result={rec2.result}")

    # 测试 3: 会话摘要
    print("\n[测试 3] 会话摘要")
    summary = audit.get_session_summary()
    assert summary["total_decisions"] == 2
    assert summary["approved"] == 1
    assert summary["blocked"] == 1
    print(f"  ✓ total={summary['total_decisions']}, approved={summary['approved']}, blocked={summary['blocked']}")

    # 测试 4: 回溯
    print("\n[测试 4] 回溯决策")
    r = audit.get_trace("sess-001-D001")
    assert r is not None
    assert r.decision == "选择 RF"
    assert len(r.evidence_chain) == 2
    print(f"  ✓ 回溯成功: {r.trace_id}, 证据链={len(r.evidence_chain)}步")

    # 测试 5: 导出
    print("\n[测试 5] JSON 导出")
    data = audit.export()
    assert "sess-001" in data
    assert "D001" in data
    print(f"  ✓ 导出 {len(data)} 字符")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
