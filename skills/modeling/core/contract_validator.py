"""
Forge v6.0 — Contract Validator
验证模块间传递的 JSON 是否符合 Schema，以及是否符合注册表中的业务规则。
Level 1: Schema 字段存在性
Level 2: 路由规则匹配
Level 3: 决策规则强制执行
"""
import json
import os
import sys

CONTRACTS_DIR = os.path.dirname(os.path.abspath(__file__))

# 硬编码 registry（避免 yaml 依赖）
REGISTRY = {
    "ProblemState": {
        "routing_rules": {
            "optimization": ["optimization_decision_rules.md", "optimization_pipeline.md"],
            "prediction": ["prediction_decision_rules.md"],
            "evaluation": ["evaluation_decision_rules.md"],
            "mechanism": ["mechanism_problem.md"],
            "hybrid": ["hybrid_pipeline.md"],
            "classification": ["prediction_decision_rules.md"]
        }
    },
    "ModelFamilies": {
        "optimization": ["models_expert/optimization/"],
        "prediction": ["models_expert/prediction/"],
        "evaluation": ["models_expert/evaluation/"],
        "classification": ["models_expert/classification/"],
        "clustering": ["models_expert/clustering/"],
        "statistics": ["models_expert/statistics/"],
        "physics": ["models_expert/physics/"],
        "simulation": ["models_expert/physics/"]  # simulation → physics 卡
    }
}

# ===== Level 1: Schema 字段存在性 =====

def validate_problem_state(data):
    """验证 L1→L2 接口"""
    errors = []
    required = ["problem_id", "problem_type", "sub_type", "core_contradiction"]
    for field in required:
        if field not in data:
            errors.append(f"ProblemState 缺少必填字段: {field}")
    
    valid_types = ["optimization", "prediction", "evaluation", "classification", "mechanism", "hybrid"]
    if data.get("problem_type") not in valid_types:
        errors.append(f"problem_type '{data.get('problem_type')}' 不在有效值 {valid_types}")
    
    if not data.get("core_contradiction"):
        errors.append("core_contradiction 不能为空 — 这是论文开篇的锚点")
    
    return len(errors) == 0, errors

def validate_decision_contract(data):
    """验证 L3→L4 接口，包含 Level 3 决策规则"""
    errors = []
    
    if "contract_id" not in data:
        errors.append("DecisionContract 缺少 contract_id")
    if "decisions" not in data or not data["decisions"]:
        errors.append("DecisionContract.decisions 不能为空")
        return False, errors
    
    for i, d in enumerate(data["decisions"]):
        prefix = f"decisions[{i}]"
        
        # L3 强制规则: 每个子问题 ≥2 个候选模型对比
        alternatives = d.get("alternatives_considered", [])
        if len(alternatives) < 2:
            errors.append(f"{prefix}: alternatives_considered 至少需要 2 个候选模型对比（竞赛论文的核心论证要求）")
        else:
            # 检查候选是否有实际区分度（非同一模型换名字）
            alt_names = [a.get("model", "").lower().replace(" ", "") for a in alternatives]
            unique = set(alt_names)
            if len(unique) < len(alt_names):
                errors.append(f"{prefix}: alternatives_considered 中候选模型名称重复 — 需要实际不同的模型比较")
            
            # 检查每个候选是否有排除理由
            for a in alternatives:
                if not a.get("reason_rejected"):
                    errors.append(f"{prefix}: 候选 '{a.get('model')}' 缺少 reason_rejected — 必须说明为什么排除")
        
        # L3 强制规则: reasoning 至少 3 条
        reasoning = d.get("reasoning", [])
        if len(reasoning) < 2:
            errors.append(f"{prefix}: reasoning 至少需要 2 条论证（推荐 3 条: 匹配特征+排除候选+不适用条件）")
        
        # L3 强制规则: 必做验证非空
        validations = d.get("mandatory_validations", [])
        if not validations:
            errors.append(f"{prefix}: mandatory_validations 不能为空 — 每个模型选择必须指定验证要求")
        
        # L3 强制规则: high severity risk 必须有 mitigation
        for r in d.get("risk_flags", []):
            if r.get("severity") == "high" and not r.get("mitigation"):
                errors.append(f"{prefix}: high severity risk '{r.get('flag')}' 缺少 mitigation")
    
    return len(errors) == 0, errors

def validate_model_result(data):
    """验证 L4→L5 接口"""
    errors = []
    
    if "execution_status" not in data:
        errors.append("ModelResult 缺少 execution_status")
    elif data["execution_status"] == "failed":
        if not data.get("model_fallback", {}).get("occurred"):
            errors.append("execution_status=failed 但没有记录 model_fallback")
    
    if not data.get("results_summary", {}).get("summary_text"):
        errors.append("results_summary.summary_text 不能为空 — 这是论文摘要的素材")
    
    return len(errors) == 0, errors

def validate_paper_section(data):
    """验证 L6→L8 接口"""
    errors = []
    
    trace = data.get("argument_trace", {})
    if not trace.get("contradiction_present"):
        errors.append("argument_trace.contradiction_present 必须为 true — 论文必须有核心矛盾")
    if not trace.get("model_reasoning_complete"):
        errors.append("argument_trace.model_reasoning_complete 必须为 true — 必须有模型选择论证")
    
    return len(errors) == 0, errors

# ===== v6.1: ValidationContract =====

def validate_validation_contract(data):
    """验证 L4→L5 的证据接口。确保模型结果经过充分验证后才进入论文生成。"""
    errors = []
    
    if "evidence_items" not in data or not data["evidence_items"]:
        errors.append("ValidationContract.evidence_items 不能为空 — 必须至少列出验证项")
        return False, errors
    
    items = data["evidence_items"]
    passed = sum(1 for i in items if i.get("status") == "passed")
    missing = sum(1 for i in items if i.get("status") == "missing")
    total = len(items)
    
    # 核心规则: 如果 >30% 的验证项 missing → confidence = low
    if missing > total * 0.3:
        data["confidence_level"] = "low"
        errors.append(f"ValidationContract: {missing}/{total} 验证项 missing — confidence_level 降为 'low'")
    
    # 检查是否有 score_impact
    for i in items:
        if i.get("status") == "missing" and not i.get("score_impact"):
            errors.append(f"验证项 '{i.get('name')}' missing 但未标注 score_impact")
    
    return len(errors) == 0, errors

# ===== Level 2: 路由规则匹配 =====

def validate_routing(problem_state):
    """验证 ProblemState 是否能路由到正确的下游模块"""
    ps_config = REGISTRY["ProblemState"]
    
    ptype = problem_state.get("problem_type")
    routing_rules = ps_config.get("routing_rules", {})
    
    if ptype not in routing_rules:
        return False, [f"problem_type '{ptype}' 不在 registry 中有对应的路由规则"]
    
    target_modules = routing_rules[ptype]
    return True, [f"路由到: {target_modules}"]

# ===== 主验证入口 =====

def validate_chain(problem_state, decision_contract=None, model_result=None, paper_section=None):
    """验证整条链路"""
    report = {"pass": True, "results": []}
    
    # L1
    ok, errs = validate_problem_state(problem_state)
    report["results"].append({"stage": "L1 ProblemState", "pass": ok, "errors": errs})
    if not ok: report["pass"] = False
    
    # L2 路由
    ok, msgs = validate_routing(problem_state)
    report["results"].append({"stage": "L2 Routing", "pass": ok, "messages": msgs})
    if not ok: report["pass"] = False
    
    # L3
    if decision_contract:
        ok, errs = validate_decision_contract(decision_contract)
        report["results"].append({"stage": "L3 DecisionContract", "pass": ok, "errors": errs})
        if not ok: report["pass"] = False
    
    # L4
    if model_result:
        ok, errs = validate_model_result(model_result)
        report["results"].append({"stage": "L4 ModelResult", "pass": ok, "errors": errs})
        if not ok: report["pass"] = False
    
    # L6
    if paper_section:
        ok, errs = validate_paper_section(paper_section)
        report["results"].append({"stage": "L6 PaperSection", "pass": ok, "errors": errs})
        if not ok: report["pass"] = False
    
    return report

# ===== CLI =====

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python contract_validator.py <contract_json_file>")
        print("  contract_json_file: 包含 problem_state + decision_contract 的 JSON")
        sys.exit(1)
    
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    
    report = validate_chain(
        problem_state=data.get("problem_state"),
        decision_contract=data.get("decision_contract"),
        model_result=data.get("model_result"),
        paper_section=data.get("paper_section")
    )
    
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0 if report["pass"] else 1)
