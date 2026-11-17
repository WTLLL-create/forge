"""
Canonical Decision Contract

v4.0 核心数据结构。所有模块统一使用的决策定义。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re
from .evidence import Evidence, EvidenceType


@dataclass
class Claim:
    """一个声明 + 支撑它的证据"""
    statement: str
    evidence: Evidence


@dataclass
class DecisionScope:
    """决策的适用范围"""
    applies_to: List[str] = field(default_factory=list)
    not_applies_to: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)


@dataclass
class ExcludedAlternative:
    """被排除的替代方案"""
    name: str
    reason: str
    evidence: Optional[Evidence] = None


@dataclass
class DecisionContract:
    """
    决策契约 — v4.0 核心数据结构。

    不只是「我做了什么决定」，更是「在什么条件下这个决定成立、
    在什么条件下它会失效、我的确定程度有多高」。
    """

    decision: str
    state: str = ""
    timestamp: str = ""

    claims: List[Claim] = field(default_factory=list)
    alternatives_excluded: List[ExcludedAlternative] = field(default_factory=list)

    confidence: float = 0.0
    uncertainty_sources: List[str] = field(default_factory=list)

    scope: Optional[DecisionScope] = None
    failure_conditions: List[str] = field(default_factory=list)
    criticality: str = "L2"

    key_rule: str = ""
    failure_recovery: Optional[str] = None

    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.85

    def is_medium_confidence(self) -> bool:
        return 0.6 <= self.confidence < 0.85

    def is_low_confidence(self) -> bool:
        return self.confidence < 0.6

    def get_confidence_level(self) -> str:
        if self.is_high_confidence(): return "high"
        elif self.is_medium_confidence(): return "medium"
        return "low"

    def check_scope(self, conditions: Dict[str, Any]) -> List[str]:
        violations = []
        if self.scope and self.scope.not_applies_to:
            for condition in self.scope.not_applies_to:
                for key, value in conditions.items():
                    if key in condition.lower() or str(value) in condition:
                        violations.append(f"当前条件'{key}={value}'匹配排除范围'{condition}'")
        return violations

    def check_failure(self, conditions: Dict[str, Any]) -> List[str]:
        import re
        triggered = []
        key_synonyms = {
            "sample_size": ["样本量", "样本数", "数据量"],
            "data_type": ["数据", "结构"],
            "feature_count": ["特征", "维度"],
            "time_span": ["时间", "周期"],
            "distribution": ["分布", "漂移"],
        }

        for fc in self.failure_conditions:
            for key, value in conditions.items():
                keywords = key_synonyms.get(key.lower(), [key.lower()])
                if not any(kw in fc for kw in keywords):
                    continue

                numbers = re.findall(r'\d+', fc)
                threshold_words = ["超过", "大于", "高于", "不足", "小于", "低于"]
                has_threshold = any(w in fc for w in threshold_words) and numbers

                if has_threshold and isinstance(value, (int, float)):
                    for num_str in numbers:
                        threshold = int(num_str)
                        if any(w in fc for w in ["超过", "大于", "高于"]) and value > threshold:
                            triggered.append(fc); break
                        if any(w in fc for w in ["不足", "小于", "低于"]) and value < threshold:
                            triggered.append(fc); break
                elif isinstance(value, str) and value in fc:
                    triggered.append(fc)
                elif not isinstance(value, str) and not has_threshold:
                    triggered.append(fc)
                if fc in triggered: break
        return triggered

    def to_dict(self) -> Dict:
        return {
            "decision": self.decision,
            "state": self.state,
            "claims": [
                {"statement": c.statement,
                 "evidence": {"description": c.evidence.description,
                              "type": c.evidence.evidence_type.value,
                              "data": c.evidence.data, "source": c.evidence.source}}
                for c in self.claims
            ],
            "alternatives_excluded": [
                {"name": a.name, "reason": a.reason,
                 "evidence": a.evidence.data if a.evidence else None}
                for a in self.alternatives_excluded
            ],
            "confidence": self.confidence,
            "confidence_level": self.get_confidence_level(),
            "uncertainty_sources": self.uncertainty_sources,
            "scope": {"applies_to": self.scope.applies_to,
                      "not_applies_to": self.scope.not_applies_to,
                      "assumptions": self.scope.assumptions} if self.scope else None,
            "failure_conditions": self.failure_conditions,
            "criticality": self.criticality,
        }

    def summary(self) -> str:
        parts = [f"决策：{self.decision}"]
        if self.claims:
            exp = sum(1 for c in self.claims if c.evidence.evidence_type == EvidenceType.EXPERIMENTAL)
            parts.append(f"声明：{len(self.claims)}条（{exp}条实验证据）")
        parts.append(f"置信度：{self.confidence:.0%} [{self.get_confidence_level()}]")
        if self.alternatives_excluded:
            parts.append(f"排除：{', '.join(a.name for a in self.alternatives_excluded)}")
        return " | ".join(parts)
