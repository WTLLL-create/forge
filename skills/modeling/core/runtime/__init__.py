"""
Runtime Architecture — 系统运行时

组件：
  orchestrator.py  — 管线调度器（S0-S8 + Governance Checkpoints）
  event_bus.py     — 事件总线（发布/订阅，解耦模块通信）
  lifecycle.py     — 会话生命周期管理（init→running→paused→error→completed）
"""
