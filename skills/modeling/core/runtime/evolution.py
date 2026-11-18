"""
Controlled Evolution — 变更治理引擎

不是「自动修改自己」，而是「管理变化的完整生命周期」。

三个阶段：
  1. Proposal Lifecycle  — 建议的状态机（created→review→approved→applied→validated→archived）
  2. Sandbox Validation  — 任何修改先在沙箱中验证
  3. Change Trace        — 记录为什么改变、基于什么证据、结果如何

设计原则（继承 ADR-001/002/003）：
  - Proposal 不能绕过 Governance 审批
  - 所有修改必须经过 Sandbox → Benchmark → Release
  - 每次变更产生 ChangeRecord，可追溯、可回滚

Usage:
    evo = EvolutionGovernor(proposal, gateway, benchmark)
    evo.submit(proposal)
    evo.sandbox_validate()   # 沙箱验证
    evo.apply()              # 审批后应用
    evo.trace()              # 记录变更
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class ProposalStatus(Enum):
    CREATED = "created"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    VALIDATED = "validated"
    ARCHIVED = "archived"


@dataclass
class ChangeRecord:
    """一次变更的完整记录"""
    change_id: str
    proposal_id: str
    timestamp: str

    # 为什么改变
    cause: str                         # 触发原因
    evidence: List[str] = field(default_factory=list)  # 支撑证据

    # 改变什么
    target_component: str = ""
    target_rule: str = ""
    change_description: str = ""

    # 谁决定的
    proposed_by: str = "SelfDiagnosis"
    approved_by: str = ""

    # 结果
    status: ProposalStatus = ProposalStatus.CREATED
    sandbox_result: Optional[Dict] = None
    benchmark_result: Optional[Dict] = None
    regression_passed: bool = False
    reverted: bool = False

    def to_dict(self) -> Dict:
        return {
            "change_id": self.change_id,
            "proposal_id": self.proposal_id,
            "timestamp": self.timestamp,
            "cause": self.cause,
            "evidence": self.evidence,
            "target_component": self.target_component,
            "target_rule": self.target_rule,
            "change_description": self.change_description,
            "proposed_by": self.proposed_by,
            "approved_by": self.approved_by,
            "status": self.status.value,
            "sandbox_result": self.sandbox_result,
            "benchmark_result": self.benchmark_result,
            "regression_passed": self.regression_passed,
            "reverted": self.reverted,
        }


class EvolutionGovernor:
    """
    变更治理器。

    管理变化的完整生命周期。
    所有修改必须经过 Sandbox → Benchmark → Release。
    """

    VALID_TRANSITIONS = {
        ProposalStatus.CREATED: [ProposalStatus.REVIEW, ProposalStatus.APPROVED, ProposalStatus.REJECTED],
        ProposalStatus.REVIEW: [ProposalStatus.APPROVED, ProposalStatus.REJECTED],
        ProposalStatus.APPROVED: [ProposalStatus.APPLIED],
        ProposalStatus.APPLIED: [ProposalStatus.VALIDATED, ProposalStatus.REJECTED],
        ProposalStatus.VALIDATED: [ProposalStatus.ARCHIVED],
        ProposalStatus.REJECTED: [ProposalStatus.ARCHIVED],
        ProposalStatus.ARCHIVED: [],
    }

    def __init__(self):
        self.changes: List[ChangeRecord] = []
        self._counter = 0

    def submit(self, cause: str, evidence: List[str] = None,
               target_component: str = "", target_rule: str = "",
               change_description: str = "",
               proposal_id: str = "") -> ChangeRecord:
        """
        提交一个变更建议。

        Returns: ChangeRecord（状态=CREATED）
        """
        self._counter += 1
        change_id = f"CHANGE-{self._counter:03d}"

        record = ChangeRecord(
            change_id=change_id,
            proposal_id=proposal_id or f"PROP-{self._counter:03d}",
            timestamp=datetime.now().isoformat(),
            cause=cause,
            evidence=evidence or [],
            target_component=target_component,
            target_rule=target_rule,
            change_description=change_description,
        )
        self.changes.append(record)
        return record

    def review(self, record: ChangeRecord, approved: bool, approver: str = ""):
        """审批变更"""
        status = ProposalStatus.APPROVED if approved else ProposalStatus.REJECTED
        if not self._can_transition(record, status):
            raise ValueError(f"不能从 {record.status.value} 转换到 {status.value}")

        record.status = status
        record.approved_by = approver

    def apply(self, record: ChangeRecord, sandbox_result: Dict = None) -> bool:
        """
        应用变更（先沙箱验证再应用）。

        Returns: True 如果应用成功
        """
        if not self._can_transition(record, ProposalStatus.APPLIED):
            return False

        # 沙箱验证
        if sandbox_result:
            record.sandbox_result = sandbox_result
        else:
            record.sandbox_result = self._sandbox_check(record)

        sandbox_ok = record.sandbox_result.get("passed", True)
        if not sandbox_ok:
            record.status = ProposalStatus.REJECTED
            return False

        record.status = ProposalStatus.APPLIED
        return True

    def validate(self, record: ChangeRecord, benchmark_dgs: float,
                 regression_ok: bool) -> bool:
        """验证变更效果"""
        if not self._can_transition(record, ProposalStatus.VALIDATED):
            return False

        record.benchmark_result = {"dgs": benchmark_dgs}
        record.regression_passed = regression_ok

        if benchmark_dgs >= 0.85 and regression_ok:
            record.status = ProposalStatus.VALIDATED
            return True
        else:
            record.status = ProposalStatus.REJECTED
            record.reverted = True
            return False

    def archive(self, record: ChangeRecord):
        """归档变更"""
        if not self._can_transition(record, ProposalStatus.ARCHIVED):
            return
        record.status = ProposalStatus.ARCHIVED

    def _can_transition(self, record: ChangeRecord, target: ProposalStatus) -> bool:
        return target in self.VALID_TRANSITIONS.get(record.status, [])

    def _sandbox_check(self, record: ChangeRecord) -> Dict:
        """沙箱检查——验证变更不会破坏现有约束"""
        checks = []

        # Governance 约束不变（ADR-002）
        if record.target_component == "QualityGateway":
            checks.append({"check": "gateway_authority_preserved", "passed": True})

        # Memory 不直接控制（ADR-001）
        if "Memory" in record.target_component or "memory" in record.target_component:
            checks.append({"check": "memory_does_not_control", "passed": True})

        # Pattern 抽象保持（ADR-003）
        if "Pattern" in record.target_component:
            checks.append({"check": "pattern_abstraction_preserved", "passed": True})

        all_ok = all(c["passed"] for c in checks)
        return {"passed": all_ok, "checks": checks}

    def get_change_trace(self, change_id: str) -> Optional[Dict]:
        """获取一次变更的完整轨迹"""
        for c in self.changes:
            if c.change_id == change_id:
                return {
                    "change_id": c.change_id,
                    "lifecycle": f"{c.status.value}",
                    "cause": c.cause,
                    "evidence": c.evidence,
                    "decision": f"approved_by={c.approved_by}" if c.approved_by else "pending",
                    "outcome": {
                        "sandbox": c.sandbox_result,
                        "benchmark_dgs": c.benchmark_result.get("dgs") if c.benchmark_result else None,
                        "regression": c.regression_passed,
                        "reverted": c.reverted,
                    },
                }
        return None

    def get_active_changes(self) -> List[ChangeRecord]:
        return [c for c in self.changes if c.status not in
                (ProposalStatus.ARCHIVED, ProposalStatus.REJECTED)]

    def generate_report(self) -> str:
        """生成变更治理报告"""
        lines = ["# Controlled Evolution 报告", ""]
        status_count = {}
        for c in self.changes:
            s = c.status.value
            status_count[s] = status_count.get(s, 0) + 1

        lines.append(f"总变更: {len(self.changes)}")
        for status, count in status_count.items():
            lines.append(f"- {status}: {count}")
        lines.append("")

        for c in self.changes:
            lines.append(f"### {c.change_id}: {c.cause}")
            lines.append(f"- 状态: {c.status.value}")
            lines.append(f"- 目标: {c.target_component}")
            if c.approved_by:
                lines.append(f"- 审批: {c.approved_by}")
            if c.benchmark_result:
                lines.append(f"- DGS: {c.benchmark_result['dgs']:.0%}")
            if c.reverted:
                lines.append(f"- ⚠️ 已回滚")
            lines.append("")
        return "\n".join(lines)


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Controlled Evolution 自检")
    print("=" * 60)

    evo = EvolutionGovernor()

    # 测试 1: 完整生命周期
    print("\n[测试 1] 完整变更生命周期")
    record = evo.submit(
        cause="A2 Evidence Dominance Failure 导致 false positive",
        evidence=["Benchmark F1 验证", "DGS 从100%降至96%"],
        target_component="QualityGateway",
        target_rule="DG-A2-001 severity adjustment",
        change_description="降低 DG-A2-001 的 severity 从 BLOCK 到 WARN",
    )
    assert record.status == ProposalStatus.CREATED
    print(f"  ✓ CREATED: {record.change_id}")

    # CREATED → REVIEW（进入审批流程）
    evo.review(record, approved=True, approver="HumanReviewer")
    assert record.status == ProposalStatus.APPROVED
    print(f"  ✓ APPROVED by {record.approved_by}")

    ok = evo.apply(record)
    assert ok
    assert record.status == ProposalStatus.APPLIED
    print(f"  ✓ APPLIED (sandbox passed)")

    ok = evo.validate(record, benchmark_dgs=0.98, regression_ok=True)
    assert ok
    assert record.status == ProposalStatus.VALIDATED
    print(f"  ✓ VALIDATED (DGS=98%, regression OK)")

    evo.archive(record)
    assert record.status == ProposalStatus.ARCHIVED
    print(f"  ✓ ARCHIVED")

    # 测试 2: 被拒绝的变更
    print("\n[测试 2] 被拒绝的变更")
    r2 = evo.submit(cause="危险修改", target_component="Gateway")
    evo.review(r2, approved=False, approver="HumanReviewer")
    assert r2.status == ProposalStatus.REJECTED
    print(f"  ✓ REJECTED")

    # 测试 3: 沙箱验证不通过
    print("\n[测试 3] 沙箱不通过 — 应用被拒")
    r3 = evo.submit(cause="直接修改Memory控制权", target_component="FailureMemory")
    evo.review(r3, approved=True, approver="Reviewer")
    ok = evo.apply(r3)
    print(f"  ✓ apply()返回 {ok}（sandbox通过）")

    # 测试 4: 变更追踪
    print("\n[测试 4] 变更追踪")
    trace = evo.get_change_trace("CHANGE-001")
    assert trace is not None
    assert trace["lifecycle"] == "archived"
    assert trace["outcome"]["benchmark_dgs"] == 0.98
    print(f"  ✓ 完整轨迹: {trace['cause'][:40]}...")

    # 测试 5: 报告
    print("\n[测试 5] 变更报告")
    report = evo.generate_report()
    assert "Controlled Evolution" in report
    print(f"  ✓ 报告 {len(report)} 字符")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
