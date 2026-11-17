"""
Canonical Evidence Contract

所有模块统一使用的证据定义。
任何模块不允许独立定义 Evidence 或 EvidenceType。
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class EvidenceType(Enum):
    EXPERIMENTAL = "experimental"    # 来自实验（数值对比、统计检验）
    THEORETICAL = "theoretical"      # 来自理论（定理、公式推导）
    EMPIRICAL = "empirical"          # 来自经验（文献、领域知识）


class VerificationStatus(Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"


@dataclass
class Evidence:
    """一条可验证的证据"""

    description: str
    evidence_type: EvidenceType
    data: Optional[str] = None
    source: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

    @classmethod
    def experimental(cls, data: str, description: str = "", source: str = ""):
        """创建实验证据（快捷方法）"""
        return cls(
            description=description or data,
            evidence_type=EvidenceType.EXPERIMENTAL,
            data=data,
            source=source,
        )

    @classmethod
    def theoretical(cls, description: str, source: str = ""):
        """创建理论证据（快捷方法）"""
        return cls(
            description=description,
            evidence_type=EvidenceType.THEORETICAL,
            source=source,
        )
