"""
Runtime Orchestrator — 系统运行时调度器

统一入口。将 S0-S8 状态机、QualityGateway、FailureMemory、EventBus 
串联为可执行的完整管线。

这是系统的「操作系统」——负责谁调用谁、什么顺序、何时暂停、何时继续。

Usage:
    orch = Orchestrator(state_manager, gateway, bus)
    result = orch.run(problem_input)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

try:
    from .event_bus import EventBus
except ImportError:
    from event_bus import EventBus


@dataclass
class RuntimeState:
    """运行时状态"""
    session_id: str
    current_stage: str = "S0_INIT"
    status: str = "idle"  # idle / running / paused / error / completed
    error: Optional[str] = None
    decisions: List[Any] = field(default_factory=list)
    start_time: str = ""
    elapsed: float = 0.0


class Orchestrator:
    """
    运行时调度器。

    执行流：
    S0(INIT) → S1(ANALYSIS) → ⚑S2(MODEL) → S3(DATA) → S4(SOLVE)
      → ⚑S5(VALIDATE) → S6(PAPER) → S7(REVIEW) → S8(DONE)

    ⚑ = Governance Checkpoint
    """

    def __init__(
        self,
        state_manager=None,
        gateway=None,
        failure_memory=None,
        logger=None,
        bus: Optional[EventBus] = None,
    ):
        self.state_manager = state_manager
        self.gateway = gateway
        self.failure_memory = failure_memory
        self.logger = logger
        self.bus = bus or EventBus()
        self.runtime = RuntimeState(session_id="")

    def run(self, problem_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行完整管线。

        Args:
            problem_input: 符合 input_schema.json 的赛题数据

        Returns:
            运行结果（状态、决策链、评分）
        """
        sid = problem_input.get("task_id", datetime.now().strftime("%Y%m%d-%H%M"))
        self.runtime = RuntimeState(
            session_id=sid,
            start_time=datetime.now().isoformat(),
            status="running",
        )

        self.bus.emit_state_transition("__start__", "S0_INIT", source="orchestrator")

        # S0: 初始化
        if not self._stage_init(problem_input):
            return self._fail("S0_INIT 失败")

        # S1: 题目分析（调用 Problem Intelligence）
        if not self._stage_analysis(problem_input):
            return self._fail("S1_ANALYSIS 失败")

        # S2: 模型选择 ⚑
        self.runtime.status = "paused"
        self.runtime.current_stage = "S2_MODEL_SELECTION"

        decision = self._stage_model_selection(problem_input)
        if decision is None:
            return self._fail("S2_MODEL_SELECTION 失败")

        # Governance Checkpoint S2
        if self.gateway:
            gate_check = self.gateway.check(
                "MODEL_SELECTION",
                problem_input.get("evidence_pkg", {}),
                decision_contract=decision,
            )
            if not gate_check.passed:
                self.bus.emit_decision_blocked(
                    decision,
                    reason=str(gate_check.blocking_issues),
                    source="orchestrator",
                )
                return self._fail(f"Gateway 阻止：{gate_check.blocking_issues}")

        self.runtime.decisions.append(decision)
        self.bus.emit_decision_made(decision, source="orchestrator")

        # S3-S4-S5: 数据处理 → 求解 → 验证
        if not self._stage_execute(problem_input):
            return self._fail("S3-S5 执行失败")

        # S6: 论文生成
        if not self._stage_paper():
            return self._fail("S6_PAPER 失败")

        # S7: 审查
        score = self._stage_review()

        # 结果评估
        if score >= 85:
            self.bus.emit_state_transition("S7_REVIEW", "S8_DONE", source="orchestrator")
            self.runtime.status = "completed"
        elif score >= 70:
            self.runtime.status = "paused"
            self.runtime.current_stage = "S6_PAPER"  # 修��重审
        else:
            error_diag = {
                "systematic_bias": score < 65,
                "high_sensitivity": False,
                "overfit_detected": False,
            }
            self.bus.emit_error_classified(error_diag, source="orchestrator")
            self.runtime.status = "error"
            self.runtime.error = f"评分={score}，需回退重建"

        return {
            "status": self.runtime.status,
            "session_id": sid,
            "final_stage": self.runtime.current_stage,
            "score": score,
            "decision_count": len(self.runtime.decisions),
        }

    def _stage_init(self, pkg: Dict) -> bool:
        self.bus.emit_state_transition("S0_INIT", "S1_ANALYSIS", source="orchestrator")
        self.runtime.current_stage = "S1_ANALYSIS"
        return True

    def _stage_analysis(self, pkg: Dict) -> bool:
        self.runtime.current_stage = "S1_ANALYSIS"
        return True

    def _stage_model_selection(self, pkg: Dict) -> Any:
        """模型选择阶段——由外部 Agent 注入实际决策"""
        # 如果已注入决策处理器，调用它
        handler = pkg.get("_model_select_handler")
        if handler:
            return handler(pkg)
        # 否则使用默认占位
        try:
            from core.contracts.decision import DecisionContract
        except ImportError:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from core.contracts.decision import DecisionContract
        return DecisionContract(
            decision="待 Agent 填充",
            confidence=0.5,
        )

    def _stage_execute(self, pkg: Dict) -> bool:
        self.runtime.current_stage = "S5_VALIDATION"
        return True

    def _stage_paper(self) -> bool:
        self.runtime.current_stage = "S6_PAPER"
        return True

    def _stage_review(self) -> float:
        self.runtime.current_stage = "S7_REVIEW"
        return 85.0  # 占位——由 reviewer_agent 注入

    def _fail(self, reason: str) -> Dict:
        self.runtime.status = "error"
        self.runtime.error = reason
        return {
            "status": "error",
            "session_id": self.runtime.session_id,
            "error": reason,
            "stage": self.runtime.current_stage,
        }


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Runtime Orchestrator 自检")
    print("=" * 60)

    bus = EventBus()
    events_log = []
    bus.on("state.transition", lambda e: events_log.append(("state", e.data["from"], e.data["to"])))
    bus.on("decision.made", lambda e: events_log.append(("decision", "made")))
    bus.on("decision.blocked", lambda e: events_log.append(("decision", "blocked")))

    orch = Orchestrator(bus=bus)

    # 测试 1: 基本运行
    print("\n[测试 1] 基本管线运行")
    result = orch.run({"task_id": "test-001", "problem_text": "测试问题"})
    assert result["status"] == "completed"  # 默认流程跑完（score=85通过）
    print(f"  ✓ 状态={result['status']}, 阶段={result['final_stage']}")

    # 测试 2: 有决策处理器
    print("\n[测试 2] 注入决策处理器")
    try:
        from core.contracts.decision import DecisionContract, Claim
        from core.contracts.evidence import Evidence, EvidenceType
    except ImportError:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from core.contracts.decision import DecisionContract, Claim
        from core.contracts.evidence import Evidence, EvidenceType

    def fake_handler(pkg):
        return DecisionContract(
            decision="选择线性规划",
            claims=[
                Claim("线性目标", Evidence.experimental("目标系数线性")),
                Claim("线性约束", Evidence.experimental("约束矩阵线性")),
            ],
            confidence=0.9,
        )

    result = orch.run({
        "task_id": "test-002",
        "_model_select_handler": fake_handler,
    })
    print(f"  ✓ 决策已注入：{len(orch.runtime.decisions)}个")

    # 测试 3: 事件量
    print("\n[测试 3] 事件总览")
    print(f"  ✓ 触发 {len(events_log)} 个事件：")
    for e in events_log:
        print(f"    [{e[0]}] {e[1]}→{e[2]}" if len(e) > 2 else f"    [{e[0]}]")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
