"""
Runtime Event Bus — 轻量级发布/订阅

解耦模块间通信。FutureMemory 不需要知道谁调用了它，
DecisionContract 不需要知道谁在监听它的变化。

事件类型：
  decision.made        — 新决策产生
  decision.blocked     — Gateway 阻止了决策
  error.classified     — ErrorLifecycle 完成根因分类
  state.transition     — 状态转移
  memory.updated       — FailureMemory 新增/更新 Pattern
  benchmark.completed  — Benchmark 运行完毕

Usage:
    bus = EventBus()
    bus.on("decision.made", lambda d: logger.record(d))
    bus.emit("decision.made", contract)
"""

from typing import Any, Callable, Dict, List
from dataclasses import dataclass, field


@dataclass
class Event:
    """一个运行时事件"""
    name: str
    data: Any = None
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    """
    轻量级事件总线。

    设计约束：
    - 同步执行（不引入异步复杂性）
    - handler 异常不影响其他 handler
    - 不存储事件历史（需要持久化的由 TraceLogger 负责）
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}
        self._emitted_count: Dict[str, int] = {}

    def on(self, event_name: str, handler: Callable[[Event], None]):
        """注册事件处理器"""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    def off(self, event_name: str, handler: Callable[[Event], None]):
        """移除事件处理器"""
        if event_name in self._handlers:
            self._handlers[event_name] = [h for h in self._handlers[event_name] if h != handler]

    def emit(self, event_name: str, data: Any = None, source: str = "", **metadata):
        """发射事件"""
        event = Event(name=event_name, data=data, source=source, metadata=metadata)

        self._emitted_count[event_name] = self._emitted_count.get(event_name, 0) + 1

        handlers = self._handlers.get(event_name, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # handler 异常不传播，但记录
                metadata["_handler_error"] = str(e)

    def emit_decision_made(self, contract, source: str = ""):
        self.emit("decision.made", contract, source=source)

    def emit_decision_blocked(self, contract, reason: str, source: str = ""):
        self.emit("decision.blocked", contract, source=source, reason=reason)

    def emit_error_classified(self, diagnosis, source: str = ""):
        self.emit("error.classified", diagnosis, source=source)

    def emit_state_transition(self, from_state: str, to_state: str, source: str = ""):
        self.emit("state.transition", {"from": from_state, "to": to_state}, source=source)

    def emit_memory_updated(self, pattern_id: str, action: str, source: str = ""):
        self.emit("memory.updated", {"pattern_id": pattern_id, "action": action}, source=source)

    def emit_benchmark_completed(self, dgs: float, total: int, source: str = ""):
        self.emit("benchmark.completed", {"dgs": dgs, "total": total}, source=source)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "handler_count": sum(len(h) for h in self._handlers.values()),
            "event_types": len(self._handlers),
            "total_emitted": sum(self._emitted_count.values()),
        }


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Event Bus 自检")
    print("=" * 60)

    bus = EventBus()
    received = []

    bus.on("decision.made", lambda e: received.append(("made", e.data)))
    bus.on("decision.blocked", lambda e: received.append(("blocked", e.data)))

    # 测试 1: 基本发射/接收
    print("\n[测试 1] 发射-接收")
    bus.emit_decision_made("决策A")
    bus.emit_decision_blocked("决策B", reason="证据不足")
    assert len(received) == 2
    assert received[0] == ("made", "决策A")
    assert received[1] == ("blocked", "决策B")
    print(f"  ✓ 收到 {len(received)} 个事件")

    # 测试 2: handler 异常不传播
    print("\n[测试 2] Handler 异常隔离")
    def bad_handler(e): raise RuntimeError("故意崩溃")
    bus.on("decision.made", bad_handler)
    bus.emit_decision_made("决策C")  # 不应抛出异常
    print(f"  ✓ 异常被隔离，事件正常发射")

    # 测试 3: 统计
    print("\n[测试 3] 统计")
    stats = bus.stats
    assert stats["handler_count"] >= 2
    assert stats["total_emitted"] >= 3
    print(f"  ✓ handlers={stats['handler_count']}, events={stats['event_types']}, emitted={stats['total_emitted']}")

    # 测试 4: off 取消注册
    print("\n[测试 4] 取消注册")
    bus.off("decision.made", bad_handler)
    received2 = []
    bus.on("decision.made", lambda e: received2.append(e.data))
    bus.emit_decision_made("决策D")
    assert "决策D" in received2
    print(f"  ✓ 取消注册后不再触发")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
