"""
Canonical Governance Contract

质量治理层使用的标准类型。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GovernAction:
    """置信度治理的控制动作"""
    level: str
    blocks_progress: bool
    requires_additional_validation: bool
    additional_checks: List[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class GateResult:
    """质量门禁检查结果"""
    gate_name: str
    passed: bool
    checks: List[Dict[str, Any]] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
