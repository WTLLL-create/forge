"""
Forge v6.0 — Runner (最小骨架)
不真正运行模型，只固化调用顺序。
目的: 固定 L0→L7 调用关系，防止未来模块演变成孤岛。

使用方法:
  python forge_runner.py <problem_id>
  python forge_runner.py CUMCM_2020_A

⚠️ DEPRECATED（2026-09-09 标注）：
本文件为 TODO 占位骨架（评分 85 分占位、canonical_scoring_framework 等未实现），
**不当作真实建模、证据链或获奖验收入口**。真实生产入口是
core/runtime/production_workflow.py（v8 信任链）与 core/runtime/problem_understanding.py（v9 竞赛预检）。
保留仅用于历史参考；新工作请勿调用本模块。
"""
import json
import os
import sys

# 假实现 — 每个模块返回符合 Schema 的占位 JSON
# 未来替换为真正的 AI 调用

class ProblemIntelligence:
    """L1: 分析题目 → ProblemState"""
    @staticmethod
    def analyze(problem_id):
        # TODO: 替换为真正的 AI 分析
        return {
            "problem_id": problem_id,
            "problem_type": "hybrid",
            "sub_type": ["physics_modeling", "single_objective"],
            "core_contradiction": "待AI分析: 题目的核心矛盾是什么？",
            "domain": "industrial_process",
            "constraints": [],
            "data_status": {"available": True},
            "sub_problems": []
        }

class ExpertDecision:
    """L3: 基于 ProblemState 生成 DecisionContract"""
    @staticmethod
    def decide(problem_state):
        # TODO: 替换为真正的 expert_decision 模块调用
        return {
            "contract_id": f"DC-{problem_state['problem_id']}-runner",
            "problem_summary": {
                "problem_type": problem_state["problem_type"],
                "sub_types": problem_state["sub_type"],
                "n_sub_problems": len(problem_state.get("sub_problems", []))
            },
            "decisions": [],
            "cross_problem_consistency": {"incremental_approach": True}
        }

class ModelExecutor:
    """L4: 执行模型 → ModelResult"""
    @staticmethod
    def run(decision):
        # TODO: 替换为真正的模型执行
        return {
            "result_id": f"MR-{decision['contract_id']}",
            "sub_problem_id": "Q1",
            "model_used": decision["decisions"][0]["primary_model"] if decision["decisions"] else "unknown",
            "execution_status": "pending",
            "results_summary": {"summary_text": "执行结果待填充"}
        }

class PaperReasoning:
    """L6: 生成论文骨架 → PaperSection"""
    @staticmethod
    def generate(problem_state, decision, model_result):
        # TODO: 替换为真正的 paper_reasoning 模块
        return {
            "paper_id": f"PAPER-{problem_state['problem_id']}",
            "sections": [],
            "argument_trace": {
                "contradiction_present": False,
                "model_reasoning_complete": False,
                "contributions_stated": False,
                "anti_pattern_hits": []
            }
        }

class EvidenceValidator:
    """L5: 验证模型结果 → ValidationContract (v6.1)"""
    @staticmethod
    def validate(model_result, decision_contract):
        # 从 DecisionContract 获取 model_family 来决定需要哪些验证项
        mf = decision_contract["decisions"][0]["model_family"] if decision_contract.get("decisions") else "optimization"
        
        # 从 evidence_checklist.md 加载对应 family 的检查项
        checklist = {
            "optimization": [
                {"check_id":"OPT-01","name":"约束满足","status":"missing","score_impact":5},
                {"check_id":"OPT-02","name":"最优性验证(多起点)","status":"missing","score_impact":3},
                {"check_id":"OPT-03","name":"参数敏感性","status":"missing","score_impact":3},
                {"check_id":"GEN-01","name":"假设验证","status":"missing","score_impact":3},
                {"check_id":"GEN-02","name":"局限性讨论","status":"missing","score_impact":2},
            ],
            "physics": [
                {"check_id":"PHYS-01","name":"量纲检查","status":"missing","score_impact":3},
                {"check_id":"PHYS-02","name":"参数物理合理性","status":"missing","score_impact":5},
                {"check_id":"PHYS-03","name":"网格/步长独立性","status":"missing","score_impact":3},
                {"check_id":"GEN-01","name":"假设验证","status":"missing","score_impact":3},
                {"check_id":"GEN-02","name":"局限性讨论","status":"missing","score_impact":2},
            ],
            "prediction": [
                {"check_id":"PRED-01","name":"训练/测试分割","status":"missing","score_impact":5},
                {"check_id":"PRED-02","name":"误差指标(≥2)","status":"missing","score_impact":3},
                {"check_id":"PRED-03","name":"残差分析","status":"missing","score_impact":3},
                {"check_id":"GEN-01","name":"假设验证","status":"missing","score_impact":3},
            ],
            "statistics": [
                {"check_id":"STAT-02","name":"敏感性分析","status":"missing","score_impact":5},
                {"check_id":"STAT-03","name":"方法对比","status":"missing","score_impact":3},
                {"check_id":"GEN-01","name":"假设验证","status":"missing","score_impact":3},
            ]
        }
        items = checklist.get(mf, checklist["optimization"])
        
        # 自动标记已完成的验证 (来自 ModelResult)
        performed = model_result.get("validations_performed", [])
        for item in items:
            for v in performed:
                if item["check_id"].split("-")[0].lower() in v.lower() or item["name"] in v:
                    item["status"] = "passed"
                    item["evidence"] = v
        
        missing = [i for i in items if i["status"] == "missing"]
        confidence = "high" if not missing else ("medium" if len(missing) <= 2 else ("low" if len(missing) <= len(items)//2 else "critical"))
        
        return {
            "contract_id": model_result.get("result_id", "VC-unknown"),
            "model_family": mf,
            "evidence_items": items,
            "confidence_level": confidence,
            "missing_impact": {
                "d5_estimated_score": max(0, 10 - sum(i.get("score_impact", 0) for i in missing) // 2),
                "can_still_publish": confidence != "critical",
                "blocking_missing": [i["name"] for i in missing if i.get("score_impact", 0) >= 5]
            },
            "paper_warnings": [f"⚠️ 验证缺失: {i['name']} — 论文模型评价章需标注" for i in missing]
        }


class Reviewer:
    """L7: 评分 → ScoreCard + FailureRecord"""
    @staticmethod
    def evaluate(paper):
        # TODO: 替换为真正的 canonical_scoring_framework
        return {
            "total_score": 0,
            "dimensions": {"D1": 0, "D2": 0, "D3": 0, "D4": 0, "D5": 0, "D6": 0},
            "grade": "pending",
            "top_weakness": "未实际评分",
            "fix_priority": []
        }

# ===== 主流程: 固定调用顺序 =====

def run(problem_id):
    """v6.x 核心执行链。v6.1 新增 L5 ValidationContract。"""
    trace = []
    
    # L0: 入口
    trace.append({"stage": "L0", "action": f"接收题目: {problem_id}", "status": "ok"})
    
    # L1: 问题分析
    problem_state = ProblemIntelligence.analyze(problem_id)
    trace.append({"stage": "L1", "action": "ProblemIntelligence.analyze()", "status": "ok", "output_keys": list(problem_state.keys())})
    
    # L2: 路由（注册表查找）
    from contract_validator import validate_routing
    ok, msgs = validate_routing(problem_state)
    trace.append({"stage": "L2", "action": "contract_validator.validate_routing()", "status": "ok" if ok else "fail", "messages": msgs})
    if not ok:
        return {"status": "fail", "stage": "L2", "trace": trace, "error": "路由失败"}
    
    # L3: 决策
    decision_contract = ExpertDecision.decide(problem_state)
    trace.append({"stage": "L3", "action": "ExpertDecision.decide()", "status": "ok", "decisions_count": len(decision_contract.get("decisions", []))})
    
    # L3 验证
    from contract_validator import validate_decision_contract
    ok, errs = validate_decision_contract(decision_contract)
    trace.append({"stage": "L3v", "action": "validate_decision_contract()", "status": "ok" if ok else "fail", "errors": errs})
    
    # L4: 执行
    model_result = ModelExecutor.run(decision_contract)
    trace.append({"stage": "L4", "action": "ModelExecutor.run()", "status": "ok", "execution_status": model_result.get("execution_status")})
    
    # L5: 证据验证 (v6.1 新增)
    validation_contract = EvidenceValidator.validate(model_result, decision_contract)
    trace.append({"stage": "L5", "action": "EvidenceValidator.validate()", 
                  "status": "ok", 
                  "confidence": validation_contract["confidence_level"],
                  "d5_estimated": validation_contract["missing_impact"]["d5_estimated_score"],
                  "warnings": len(validation_contract["paper_warnings"])})
    
    # L6: 论文
    paper_section = PaperReasoning.generate(problem_state, decision_contract, model_result)
    trace.append({"stage": "L6", "action": "PaperReasoning.generate()", "status": "ok", "sections_count": len(paper_section.get("sections", []))})
    
    # L7: 评审
    score = Reviewer.evaluate(paper_section)
    trace.append({"stage": "L7", "action": "Reviewer.evaluate()", "status": "ok", "total_score": score.get("total_score")})
    
    return {
        "status": "ok",
        "problem_id": problem_id,
        "trace": trace,
        "problem_state": problem_state,
        "decision_contract": decision_contract,
        "model_result": model_result,
        "paper_section": paper_section,
        "score": score
    }

if __name__ == "__main__":
    problem_id = sys.argv[1] if len(sys.argv) > 1 else "CUMCM_2020_A"
    result = run(problem_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
