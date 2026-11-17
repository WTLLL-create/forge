"""
Canonical Failure Pattern Contract

经验治理层使用的标准类型。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime


@dataclass
class FailurePattern:
    """
    一个可执行的失败模式。

    不是「这里有个 bug」，而是「这类决策模式曾经导致治理失败，
    在当前条件下有 Y% 的概率再次失败」。
    """

    id: str
    name: str
    category: str
    description: str
    risk_description: str
    recommended_guard: str

    # 治理版本
    created_version: str = "v4.0.1"
    governance_version: str = "gv1"
    status: str = "active"

    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "medium"
    guard_type: str = "completeness"

    confidence: float = 0.5
    occurrence_count: int = 1
    verified_count: int = 0

    discovered_at: str = ""
    last_triggered_at: str = ""

    def verify(self, was_effective: bool):
        self.verified_count += 1
        if was_effective:
            self.confidence = min(0.95, self.confidence + 0.1)
        else:
            self.confidence = max(0.1, self.confidence - 0.05)
        self.last_triggered_at = datetime.now().isoformat()

    def should_apply(self) -> bool:
        return self.confidence >= 0.5 and self.status == "active"

    def to_governance_rule(self) -> Dict:
        return {
            "pattern_id": self.id,
            "risk_level": self.risk_level,
            "confidence": round(self.confidence, 2),
            "guard": self.recommended_guard,
            "guard_type": self.guard_type,
            "should_apply": self.should_apply(),
        }
