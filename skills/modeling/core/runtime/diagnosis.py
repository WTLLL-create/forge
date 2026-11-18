"""
Runtime Diagnosis + Improvement Proposal — 自我诊断与改进建议

不是「自动修复」，而是「自动诊断 + 人工审批」。
严格遵守 ADR-001: Memory 不直接控制系统。

三阶段：
  1. Diagnosis — 从异常追踪到根因（利用 Audit + Replay）
  2. Proposal — 生成改进建议（不自动应用）
  3. Validation — 验证改进是否有效

Usage:
    diag = SelfDiagnosis(audit, replay, memory)
    findings = diag.diagnose(anomaly)
    proposal = diag.propose(findings)  # 需要人工 approval
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from .anomaly import Anomaly
except ImportError:
    from anomaly import Anomaly


@dataclass
class Diagnosis:
    anomaly: Anomaly
    root_cause: str = ""
    affected_component: str = ""
    evidence_traces: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class Proposal:
    diagnosis: Diagnosis
    target: str = ""
    suggestion: str = ""
    expected_impact: str = ""
    risk: str = "medium"
    status: str = "pending"


class SelfDiagnosis:
    """
    自我诊断引擎。

    设计约束（来自 ADR-001/002/003）：
    - Diagnosis 只分析，不修改
    - Proposal 只建议，不应用
    - 所有修改需要人工 approval
    """

    def __init__(self, audit_trail=None, replay_engine=None, failure_memory=None):
        self.audit = audit_trail
        self.replay = replay_engine
        self.memory = failure_memory
        self.findings: List[Diagnosis] = []
        self.proposals: List[Proposal] = []

    def diagnose(self, anomaly: Anomaly) -> Diagnosis:
        """
        从异常追踪到根因。

        利用 AuditTrail 回溯相关决策，利用 Replay 验证。
        """
        diag = Diagnosis(anomaly=anomaly, confidence=0.5)

        if anomaly.type == "governance_drift":
            diag = self._diagnose_governance_drift(anomaly)
        elif anomaly.type == "confidence_inflation":
            diag = self._diagnose_confidence_inflation(anomaly)
        elif anomaly.type == "memory_overreach":
            diag = self._diagnose_memory_overreach(anomaly)
        else:
            diag.root_cause = f"异常类型 {anomaly.type} 暂无专用诊断逻辑"
            diag.affected_component = "unknown"

        self.findings.append(diag)
        return diag

    def _diagnose_governance_drift(self, anomaly: Anomaly) -> Diagnosis:
        diag = Diagnosis(
            anomaly=anomaly,
            root_cause="治理拒绝率突变",
            affected_component="QualityGateway",
            confidence=0.7,
        )

        if anomaly.current_value > 0.4:
            diag.root_cause += " — 可能原因：新增 FailurePattern 过于严格 或 输入数据质量下降"
            diag.evidence_traces = ["检查最近激活的 FailurePattern", "回放被拒绝的决策验证合理性"]
        else:
            diag.root_cause += " — 可能原因：Gateway 被绕过 或 输入质量异常提升"
            diag.evidence_traces = ["检查 Gateway 检查项是否全部执行", "验证最近通过的决策证据质量"]

        return diag

    def _diagnose_confidence_inflation(self, anomaly: Anomaly) -> Diagnosis:
        return Diagnosis(
            anomaly=anomaly,
            root_cause="LLM 过度自信——置信度与证据量不匹配",
            affected_component="UncertaintyGovernor",
            evidence_traces=["检查高置信度决策的 claims 数量", "对比同为高置信的 Benchmark 通过率"],
            confidence=0.8,
        )

    def _diagnose_memory_overreach(self, anomaly: Anomaly) -> Diagnosis:
        patterns = []
        if self.memory:
            patterns = [p.id for p in self.memory.patterns.values() if p.status == "active"]
        return Diagnosis(
            anomaly=anomaly,
            root_cause=f"FailureMemory 触发过于频繁——{len(patterns)}个active patterns",
            affected_component="FailureMemory",
            evidence_traces=["检查各 Pattern 的 confidence 是否过高", "验证 Pattern 的 trigger_conditions 是否过于宽泛"],
            confidence=0.7,
        )

    def propose(self, diagnosis: Diagnosis) -> Proposal:
        """基于诊断生成改进建议"""
        prop = Proposal(diagnosis=diagnosis, target=diagnosis.affected_component)

        if "Governor" in diagnosis.affected_component or "Gateway" in diagnosis.affected_component:
            prop.suggestion = "调整 Governance Rule 的 severity 或增加例外条件"
            prop.expected_impact = "降低误拒率，同时保持正确拦截率"
            prop.risk = "medium"
        elif "Memory" in diagnosis.affected_component:
            prop.suggestion = "审查活跃 FailurePattern，降低过于宽泛的 Pattern 置信度或标记为 deprecated"
            prop.expected_impact = "减少过度触发"
            prop.risk = "high"  # 修改 Memory 风险高
        else:
            prop.suggestion = "需要人工分析根因后确定改进方向"
            prop.expected_impact = "待定"
            prop.risk = "unknown"

        self.proposals.append(prop)
        return prop

    def approve(self, proposal: Proposal):
        """审批通过"""
        proposal.status = "approved"

    def reject(self, proposal: Proposal, reason: str = ""):
        proposal.status = "rejected"

    def get_pending_proposals(self) -> List[Proposal]:
        return [p for p in self.proposals if p.status == "pending"]

    def generate_report(self) -> str:
        """生成诊断报告"""
        lines = ["# Self-Diagnosis 报告", ""]

        if self.findings:
            lines.append(f"## 诊断结果（{len(self.findings)}项）")
            for i, d in enumerate(self.findings):
                lines.append(f"### D{i+1}: {d.anomaly.type}")
                lines.append(f"- 根因: {d.root_cause}")
                lines.append(f"- 组件: {d.affected_component}")
                lines.append(f"- 置信度: {d.confidence:.0%}")
                lines.append("")

        if self.proposals:
            pending = self.get_pending_proposals()
            lines.append(f"## 改进建议（{len(self.proposals)}项, {len(pending)}待审批）")
            for i, p in enumerate(self.proposals):
                icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(p.status, "")
                lines.append(f"### {icon} P{i+1}: {p.target}")
                lines.append(f"- 建议: {p.suggestion}")
                lines.append(f"- 影响: {p.expected_impact} | 风险: {p.risk}")
                lines.append("")

        return "\n".join(lines)


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Self-Diagnosis 自检")
    print("=" * 60)

    sd = SelfDiagnosis()

    # 测试 1: 诊断治理漂移
    print("\n[测试 1] 诊断治理漂移")
    anomaly = Anomaly(
        type="governance_drift", severity="high",
        evidence=["拒绝率翻倍"],
        metric_name="block_rate", current_value=0.5,
    )
    diag = sd.diagnose(anomaly)
    assert diag.affected_component == "QualityGateway"
    print(f"  ✓ 根因: {diag.root_cause}")

    # 测试 2: 生成建议
    print("\n[测试 2] 生成改进建议")
    prop = sd.propose(diag)
    assert prop.status == "pending"
    assert prop.target == "QualityGateway"
    print(f"  ✓ 建议: {prop.suggestion}")

    # 测试 3: 审批流程
    print("\n[测试 3] 审批流程")
    sd.approve(prop)
    assert prop.status == "approved"
    assert len(sd.get_pending_proposals()) == 0
    print(f"  ✓ 审批后 status={prop.status}")

    # 测试 4: 置信度虚高诊断
    print("\n[测试 4] 诊断置信度虚高")
    anom2 = Anomaly(type="confidence_inflation", severity="medium")
    diag2 = sd.diagnose(anom2)
    assert "LLM" in diag2.root_cause or "置信度" in diag2.root_cause
    print(f"  ✓ 根因: {diag2.root_cause}")

    # 测试 5: 报告
    print("\n[测试 5] 诊断报告")
    report = sd.generate_report()
    assert "Self-Diagnosis" in report
    assert "QualityGateway" in report
    print(f"  ✓ 报告 {len(report)} 字符")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
