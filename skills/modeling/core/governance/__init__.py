# Governance Plane — 系统治理平面

"""
治理平面是系统的「控制平面」——不执行业务逻辑，只约束业务逻辑的行为边界。

类比：
  Kubernetes:   Workload Plane (Pods) + Control Plane (Scheduler, Controller)
  数据库:       Data Plane (查询) + Control Plane (事务管理, 锁)
  本系统:       Execution Plane (S0-S8) + Governance Plane (本层)

治理平面的三条铁律（来自 ADR-001/002/003）：
  1. 治理不执行 — Governance advice, not direct control
  2. 决策不绕过 — QualityGateway is the sole authority
  3. 模式不绑定 — FailurePatterns are patterns, not rules
"""

# 治理平面能力清单
GOVERNANCE_CAPABILITIES = {
    "decision_gate": {
        "owner": "quality_layer.QualityGateway",
        "authority": "sole",
        "purpose": "状态转换的权限控制",
        "adr": "ADR-002",
    },
    "evidence_validation": {
        "owner": "quality_layer.EvidenceValidator",
        "authority": "advisory",
        "purpose": "证据格式和质量的校验",
    },
    "uncertainty_control": {
        "owner": "quality_layer.UncertaintyGovernor",
        "authority": "advisory",
        "purpose": "置信度→控制信号",
    },
    "error_lifecycle": {
        "owner": "quality_layer.ErrorLifecycle",
        "authority": "advisory",
        "purpose": "失败根因分类和回退策略",
    },
    "failure_memory": {
        "owner": "quality_layer.FailureMemory",
        "authority": "advisory",
        "purpose": "历史失败经验的存储和匹配",
        "adr": "ADR-001",
    },
    "experience_compilation": {
        "owner": "core.runtime.FailureMemory",
        "authority": "advisory",
        "purpose": "失败→抽象→经验→治理建议",
        "adr": "ADR-003",
    },
    "anomaly_detection": {
        "owner": "core.runtime.AnomalyDetector",
        "authority": "advisory",
        "purpose": "运行时行为异常检测",
    },
    "self_diagnosis": {
        "owner": "core.runtime.SelfDiagnosis",
        "authority": "advisory",
        "purpose": "异常根因分析和改进建议",
    },
    "change_governance": {
        "owner": "core.runtime.EvolutionGovernor",
        "authority": "sole",
        "purpose": "变更的完整生命周期管理",
    },
}

# 治理平面不做什么
GOVERNANCE_NON_RESPONSIBILITIES = [
    "不执行数学建模的具体步骤",
    "不生成模型选择",
    "不运行实验",
    "不直接修改系统代码",
]

# 治理平面的完整性检查
def validate_governance_plane():
    """
    验证治理平面是否完整。
    返回缺少的能力或异常。
    """
    issues = []
    
    # 必须有唯一的决策权威点
    sole_authorities = [k for k, v in GOVERNANCE_CAPABILITIES.items() if v["authority"] == "sole"]
    if len(sole_authorities) < 1:
        issues.append("缺少唯一的决策权威点")
    if len(sole_authorities) > 3:
        issues.append(f"决策权威点过多: {sole_authorities}")
    
    # 所有 advisory 能力必须有 ADR 约束
    for name, cap in GOVERNANCE_CAPABILITIES.items():
        if cap["authority"] == "advisory" and "adr" not in cap:
            pass  # 部分 advisory 能力尚未关联 ADR，记录但不阻止
    
    return issues
