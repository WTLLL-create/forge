"""
core — Canonical Contract Layer

所有跨模块对象必须在此定义。
"""

from .contracts.evidence import Evidence, EvidenceType, VerificationStatus
from .contracts.decision import DecisionContract, Claim, ExcludedAlternative, DecisionScope
from .contracts.governance import GovernAction, GateResult
from .contracts.failure import FailurePattern
