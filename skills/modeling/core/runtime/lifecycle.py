"""
Runtime Lifecycle — 会话生命周期管理

管理单个研究会话从初始化到完成的完整生命周期：
  init → running → paused → error → completed

每个状态转换触发事件，供其他模块监听。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

try:
    from .event_bus import EventBus
except ImportError:
    from event_bus import EventBus


class LifecycleState(Enum):
    INIT = "init"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class SessionSnapshot:
    """会话快照"""
    session_id: str
    state: LifecycleState
    current_stage: str
    start_time: str
    last_active: str
    decision_count: int = 0
    error_count: int = 0
    events_emitted: int = 0


class RuntimeLifecycle:
    """
    会话生命周期管理器。

    管理单个会话的状态转换。
    每次转换触发 bus 事件。
    """

    VALID_TRANSITIONS = {
        LifecycleState.INIT: [LifecycleState.RUNNING],
        LifecycleState.RUNNING: [LifecycleState.PAUSED, LifecycleState.ERROR, LifecycleState.COMPLETED],
        LifecycleState.PAUSED: [LifecycleState.RUNNING, LifecycleState.ERROR],
        LifecycleState.ERROR: [LifecycleState.INIT],
        LifecycleState.COMPLETED: [],
    }

    def __init__(self, session_id: str, bus: Optional[EventBus] = None):
        self.session_id = session_id
        self.bus = bus or EventBus()
        self.state = LifecycleState.INIT
        self.current_stage = "S0_INIT"
        self.start_time = datetime.now().isoformat()
        self.last_active = self.start_time
        self._decision_count = 0
        self._error_count = 0
        self._history: List[tuple] = []  # (timestamp, from, to)

    def transition(self, target: LifecycleState) -> bool:
        """执行状态转换"""
        if target not in self.VALID_TRANSITIONS.get(self.state, []):
            return False

        old_state = self.state
        self.state = target
        self.last_active = datetime.now().isoformat()
        self._history.append((self.last_active, old_state, target))

        self.bus.emit(
            "lifecycle.transition",
            {"from": old_state.value, "to": target.value, "stage": self.current_stage},
            source="lifecycle",
        )
        return True

    def increment_decision(self):
        self._decision_count += 1

    def increment_error(self):
        self._error_count += 1

    def snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            session_id=self.session_id,
            state=self.state,
            current_stage=self.current_stage,
            start_time=self.start_time,
            last_active=self.last_active,
            decision_count=self._decision_count,
            error_count=self._error_count,
            events_emitted=sum(1 for _ in self._history),
        )


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Runtime Lifecycle 自检")
    print("=" * 60)

    # 测试 1: 有效转换
    print("\n[测试 1] 正常生命周期")
    lc = RuntimeLifecycle("sess-001")
    assert lc.state == LifecycleState.INIT

    assert lc.transition(LifecycleState.RUNNING)
    assert lc.state == LifecycleState.RUNNING
    print(f"  ✓ INIT → RUNNING")

    assert lc.transition(LifecycleState.PAUSED)
    assert lc.state == LifecycleState.PAUSED
    print(f"  ✓ RUNNING → PAUSED")

    assert lc.transition(LifecycleState.RUNNING)
    print(f"  ✓ PAUSED → RUNNING")

    assert lc.transition(LifecycleState.COMPLETED)
    print(f"  ✓ RUNNING → COMPLETED")

    # 测试 2: 无效转换
    print("\n[测试 2] 无效转换被拒")
    # COMPLETED 不能再转
    assert not lc.transition(LifecycleState.RUNNING)
    print(f"  ✓ COMPLETED → RUNNING 被拒绝")

    # 测试 3: 快照
    print("\n[测试 3] 会话快照")
    snap = lc.snapshot()
    assert snap.decision_count == 0
    print(f"  ✓ sid={snap.session_id}, state={snap.state.value}, events={snap.events_emitted}")

    # 测试 4: 决策计数
    print("\n[测试 4] 决策/错误计数")
    lc.increment_decision()
    lc.increment_decision()
    lc.increment_error()
    assert lc.snapshot().decision_count == 2
    assert lc.snapshot().error_count == 1
    print(f"  ✓ decisions=2, errors=1")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
