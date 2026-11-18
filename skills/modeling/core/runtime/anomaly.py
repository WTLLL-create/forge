"""
Runtime Anomaly Detection — 运行时异常检测

不是「监控」，而是「发现系统行为什么时候开始偏离正常」。

检测四类异常：
  1. governance_drift — 治理指标突然变化（拒绝率飙升/骤降）
  2. confidence_inflation — 置信度普遍虚高但证据不足
  3. memory_overreach — FailurePattern 触发频率异常
  4. execution_degradation — 执行通过率持续下降

Usage:
    detector = AnomalyDetector()
    detector.feed(metrics_snapshot)
    alerts = detector.check()
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Anomaly:
    """一个检测到的异常"""
    type: str                          # governance_drift / confidence_inflation / ...
    severity: str                      # critical / high / medium / low
    evidence: List[str] = field(default_factory=list)
    metric_name: str = ""
    current_value: float = 0.0
    expected_range: str = ""
    detected_at: str = ""


class AnomalyDetector:
    """
    异常检测器。

    设计原则：
    - 检测的是「行为变化」，不是「数值超标」
    - 每次 check() 比较最新快照和历史基线
    - 异常是信号，不是结论——需要 Diagnosis 进一步分析
    """

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.governance_history: List[Dict] = []
        self.reasoning_history: List[Dict] = []
        self.execution_history: List[Dict] = []
        self.memory_history: List[Dict] = []
        self.alerts: List[Anomaly] = []

    def feed(self, metrics_snapshot: Dict[str, Any]):
        """喂入一次指标快照"""
        for cat, data in metrics_snapshot.items():
            if cat == "governance":
                self.governance_history.append(data)
                if len(self.governance_history) > self.window_size:
                    self.governance_history.pop(0)
            elif cat == "reasoning":
                self.reasoning_history.append(data)
                if len(self.reasoning_history) > self.window_size:
                    self.reasoning_history.pop(0)
            elif cat == "execution":
                self.execution_history.append(data)
                if len(self.execution_history) > self.window_size:
                    self.execution_history.pop(0)
            elif cat == "memory":
                self.memory_history.append(data)
                if len(self.memory_history) > self.window_size:
                    self.memory_history.pop(0)

    def check(self) -> List[Anomaly]:
        """检查所有维度的异常"""
        self.alerts = []
        self._check_governance()
        self._check_confidence()
        self._check_memory()
        self._check_execution()
        return self.alerts

    def _check_governance(self):
        """治理漂移检测"""
        if len(self.governance_history) < 3:
            return

        recent = self.governance_history[-1]
        earlier = self.governance_history[0]

        block_rate = recent.get("block_rate", 0)
        earlier_block = earlier.get("block_rate", 0)

        # 拒绝率突变
        if earlier_block > 0:
            change = (block_rate - earlier_block) / earlier_block
            if change > 1.0:  # 拒绝率翻倍
                self.alerts.append(Anomaly(
                    type="governance_drift",
                    severity="high",
                    evidence=[
                        f"拒绝率从{earlier_block:.0%}升至{block_rate:.0%}（+{change:.0%}）",
                        "可能的治理规则过强或输入质量下降",
                    ],
                    metric_name="block_rate",
                    current_value=block_rate,
                    expected_range=f"<{earlier_block*1.5:.0%}",
                    detected_at=datetime.now().isoformat(),
                ))
            elif change < -0.5:  # 拒绝率骤降过半
                self.alerts.append(Anomaly(
                    type="governance_drift",
                    severity="medium",
                    evidence=[
                        f"拒绝率从{earlier_block:.0%}降至{block_rate:.0%}（{change:.0%}）",
                        "Gateway 可能被绕过或输入质量异常提升",
                    ],
                    metric_name="block_rate",
                    current_value=block_rate,
                    expected_range=f">{earlier_block*0.5:.0%}",
                    detected_at=datetime.now().isoformat(),
                ))

    def _check_confidence(self):
        """置信度虚高检测"""
        if not self.reasoning_history:
            return

        recent = self.reasoning_history[-1]
        avg_conf = recent.get("avg_confidence", 0)
        claims = recent.get("avg_claims", 0)

        # 高置信度 + 低证据 = 可疑
        if avg_conf > 0.85 and claims < 2:
            self.alerts.append(Anomaly(
                type="confidence_inflation",
                severity="medium",
                evidence=[
                    f"平均置信度={avg_conf:.0%}但平均声明数仅{claims:.1f}",
                    "LLM 可能过度自信——置信度与证据量不匹配",
                ],
                metric_name="avg_confidence",
                current_value=avg_conf,
                expected_range=f"avg_claims should be ≥2 when confidence>{0.85}",
                detected_at=datetime.now().isoformat(),
            ))

    def _check_memory(self):
        """记忆过载检测"""
        if len(self.memory_history) < 2:
            return

        recent = self.memory_history[-1]
        trigger_rate = recent.get("memory_trigger_rate", 0)

        if trigger_rate > 0.5:  # 超过50%的决策触发Memory
            self.alerts.append(Anomaly(
                type="memory_overreach",
                severity="high",
                evidence=[
                    f"FailureMemory触发率={trigger_rate:.0%}，超过50%",
                    "Pattern可能过于宽泛或系统在重复犯同类错误",
                ],
                metric_name="memory_trigger_rate",
                current_value=trigger_rate,
                expected_range="<50%",
                detected_at=datetime.now().isoformat(),
            ))

    def _check_execution(self):
        """执行退化检测"""
        if len(self.execution_history) < 3:
            return

        recent = self.execution_history[-1]
        error_rate = recent.get("error_rate", 0)

        if error_rate > 0.3:  # 超过30%的会话出错
            self.alerts.append(Anomaly(
                type="execution_degradation",
                severity="high",
                evidence=[
                    f"执行错误率={error_rate:.0%}",
                    "需要检查 Runtime/StateManager 是否有回归",
                ],
                metric_name="error_rate",
                current_value=error_rate,
                expected_range="<30%",
                detected_at=datetime.now().isoformat(),
            ))

    def get_alerts_summary(self) -> str:
        """生成告警摘要"""
        if not self.alerts:
            return "✓ 无异常"

        lines = []
        for a in self.alerts:
            lines.append(f"[{a.severity}] {a.type}: {a.evidence[0] if a.evidence else ''}")
        return "\n".join(lines)


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    try:
        from metrics import MetricsCollector
    except ImportError:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from metrics import MetricsCollector

    print("=" * 60)
    print("Anomaly Detection 自检")
    print("=" * 60)

    detector = AnomalyDetector()

    # 测试 1: 正常基线
    print("\n[测试 1] 正常基线 — 无告警")
    detector.feed({
        "governance": {"block_rate": 0.2},
        "reasoning": {"avg_confidence": 0.7, "avg_claims": 2.5},
        "execution": {"error_rate": 0.05},
        "memory": {"memory_trigger_rate": 0.1},
    })
    alerts = detector.check()
    assert len(alerts) == 0
    print(f"  ✓ {detector.get_alerts_summary()}")

    # 测试 2: 治理漂移
    print("\n[测试 2] 治理漂移 — 应告警")
    detector.feed({
        "governance": {"block_rate": 0.2},
        "reasoning": {"avg_confidence": 0.7, "avg_claims": 2.0},
        "execution": {"error_rate": 0.05},
        "memory": {"memory_trigger_rate": 0.1},
    })
    detector.feed({
        "governance": {"block_rate": 0.2},
        "reasoning": {"avg_confidence": 0.7, "avg_claims": 2.0},
        "execution": {"error_rate": 0.05},
        "memory": {"memory_trigger_rate": 0.1},
    })
    # 第三次：拒绝率翻倍
    detector.feed({
        "governance": {"block_rate": 0.5},  # 从0.2跳到0.5
        "reasoning": {"avg_confidence": 0.7, "avg_claims": 2.0},
        "execution": {"error_rate": 0.05},
        "memory": {"memory_trigger_rate": 0.1},
    })
    alerts = detector.check()
    assert len(alerts) >= 1
    drift = [a for a in alerts if a.type == "governance_drift"][0]
    assert drift.severity == "high"
    print(f"  ✓ {drift.evidence[0]}")

    # 测试 3: 置信度虚高
    print("\n[测试 3] 置信度虚高 — 应告警")
    d2 = AnomalyDetector(window_size=2)
    for _ in range(3):
        d2.feed({"governance": {"block_rate": 0.2}, "reasoning": {"avg_confidence": 0.9, "avg_claims": 1.0},
                  "execution": {"error_rate": 0.0}, "memory": {"memory_trigger_rate": 0.0}})
    alerts = d2.check()
    inflation = [a for a in alerts if a.type == "confidence_inflation"]
    assert len(inflation) >= 1
    print(f"  ✓ {inflation[0].evidence[0]}")

    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
