"""
Forge v6.2 — Failure Aggregator
将 Benchmark 中分散的 FailureRecord 聚合为可操作的 Pattern。
输出: experience_registry.yaml 的候选条目（需人工审批）。
"""
import json
import os

FEEDBACK_DIR = os.path.dirname(os.path.abspath(__file__))

# ===== 从 Benchmark 三轮结果中收集的所有 FailureRecord =====

ALL_FAILURES = [
    # ---- Round 1 Decision ----
    {"case":"B01","stage":"decision","type":"missing_alternative","detail":"Q3仅1个候选","severity":"medium","dimension":"D2"},
    {"case":"B03","stage":"decision","type":"missing_alternative","detail":"PID仅2候选，未比较参数辨识精度","severity":"medium","dimension":"D2"},
    {"case":"B05","stage":"decision","type":"missing_alternative","detail":"CT反演仅1候选","severity":"high","dimension":"D2"},
    {"case":"B07","stage":"decision","type":"missing_alternative","detail":"系泊系统Q2仅1候选","severity":"medium","dimension":"D2"},
    {"case":"B08","stage":"decision","type":"missing_alternative","detail":"定日镜仅1候选","severity":"medium","dimension":"D2"},
    {"case":"B09","stage":"decision","type":"missing_alternative","detail":"板凳龙仅1候选","severity":"high","dimension":"D2"},
    {"case":"B10","stage":"decision","type":"missing_alternative","detail":"太阳影子仅1候选","severity":"high","dimension":"D2"},
    
    {"case":"B03","stage":"decision","type":"missing_constraint","detail":"电磁阀响应时间未提取","severity":"medium","dimension":"D1"},
    {"case":"B05","stage":"decision","type":"missing_constraint","detail":"探测器噪声模型未建模","severity":"medium","dimension":"D1"},
    {"case":"B08","stage":"decision","type":"missing_constraint","detail":"跟踪精度误差未考虑","severity":"medium","dimension":"D1"},
    {"case":"B09","stage":"decision","type":"missing_constraint","detail":"队员步长/臂长约束遗漏","severity":"medium","dimension":"D1"},
    {"case":"B10","stage":"decision","type":"missing_constraint","detail":"大气折射修正遗漏","severity":"low","dimension":"D1"},
    
    {"case":"B09","stage":"decision","type":"difficulty_misjudged","detail":"板凳龙误判为纯优化，实为多刚体运动学","severity":"high","dimension":"D1"},
    {"case":"B10","stage":"decision","type":"difficulty_misjudged","detail":"太阳影子严重低估不适定性","severity":"critical","dimension":"D1"},
    
    # ---- Round 2 Execution ----
    {"case":"B03","stage":"execution","type":"model_degradation","detail":"optimal_control→离散搜索降级","severity":"medium","dimension":"D4"},
    {"case":"B06","stage":"execution","type":"surrogate_risk","detail":"RF代理外推风险","severity":"medium","dimension":"D4"},
    {"case":"B07","stage":"execution","type":"incomplete_optimization","detail":"三维设计空间未完成遍历","severity":"medium","dimension":"D4"},
    {"case":"B08","stage":"execution","type":"scalability_issue","detail":">1000变量离散优化性能瓶颈","severity":"high","dimension":"D4"},
    {"case":"B09","stage":"execution","type":"incomplete_execution","detail":"仅Q1完成, Q2/Q3仅框架","severity":"high","dimension":"D4"},
    
    # ---- Round 3 Paper ----
    {"case":"B02","stage":"paper","type":"insufficient_validation","detail":"缺网格独立性+Δt消融","severity":"medium","dimension":"D5"},
    {"case":"B04","stage":"paper","type":"insufficient_validation","detail":"缺pop_size消融+柔索假设验证","severity":"medium","dimension":"D5"},
    
    # ---- v6.1 ValidationContract 发现 ----
    {"case":"B02","stage":"validation","type":"missing_grid_independence","detail":"加密网格影响未验证","severity":"medium","dimension":"D5"},
    {"case":"B04","stage":"validation","type":"missing_ablation","detail":"NSGA-II pop_size消融缺失","severity":"medium","dimension":"D5"},
    {"case":"B04","stage":"validation","type":"missing_optimality_check","detail":"Pareto全局性未验证","severity":"medium","dimension":"D5"},
    {"case":"B02","stage":"validation","type":"missing_radiation_check","detail":"辐射传热忽略未量化","severity":"low","dimension":"D5"},
]

# ===== 聚合逻辑 =====

def aggregate(failures):
    patterns = {}
    
    for f in failures:
        # 聚合键：type + dimension
        key = f"{f['type']}#{f['dimension']}"
        if key not in patterns:
            patterns[key] = {
                "type": f["type"],
                "dimension": f["dimension"],
                "stage": f["stage"],
                "cases": [],
                "count": 0,
                "severities": []
            }
        patterns[key]["cases"].append(f["case"])
        patterns[key]["count"] += 1
        patterns[key]["severities"].append(f["severity"])
    
    # 排序
    result = sorted(patterns.values(), key=lambda p: p["count"], reverse=True)
    
    # 生成建议
    for p in result:
        p["frequency"] = f"{p['count']}/25"  # 25 total failure records
        p["recommendation"] = _generate_recommendation(p)
    
    return result

def _generate_recommendation(pattern):
    t = pattern["type"]
    d = pattern["dimension"]
    
    recs = {
        "missing_alternative#D2": "Contract Validator 已强制 alternatives≥2。v6.0 P0修复后此问题应消除。",
        "missing_constraint#D1": "ProblemIntelligence 增加领域隐含约束推导。当前仅从题面文字提取约束。",
        "difficulty_misjudged#D1": "ProblemIntelligence 增加难度预判: 对非常规领域标记 low_confidence，触发降级策略。",
        "model_degradation#D4": "降级路径应写入 ModelResult.honesty。当前已实现，需持续监控。",
        "surrogate_risk#D4": "代理模型外推风险已在 paper_warnings 中标注。v6.1 已覆盖。",
        "incomplete_optimization#D4": "三维及以上设计空间 → 推荐启发式加速 (SA/GA) 而非暴力搜索。需要 models_expert 补卡。",
        "scalability_issue#D4": "大规模离散优化(>1000变量) → 需要 decomposition 或简化搜索策略。当前无覆盖。",
        "incomplete_execution#D4": "复杂综合题 → 分阶段执行+进度报告。当前 forge_runner 无阶段管理。",
        "insufficient_validation#D5": "v6.1 ValidationContract 已覆盖。需确认论文模型评价章是否包含 contract 输出的 paper_warnings。",
        "missing_grid_independence#D5": "physics 模型卡中已列为必做验证(PHYS-03)。需确保 forge_runner L5 步自动触发。",
        "missing_ablation#D5": "optimization 模型卡中已列为必做验证(OPT-04)。同上。",
        "missing_optimality_check#D5": "optimization 模型卡中已列为必做验证(OPT-02)。同上。",
        "missing_radiation_check#D5": "physics 模型卡 GEN-01 假设验证覆盖。影响力 low (辐射<3%)。",
    }
    
    return recs.get(f"{t}#{d}", f"待人工分析: {t}")

if __name__ == "__main__":
    patterns = aggregate(ALL_FAILURES)
    
    print("=" * 70)
    print("Forge v6.2 — Failure Aggregator: 经验聚合报告")
    print("=" * 70)
    print(f"输入: {len(ALL_FAILURES)} 条 FailureRecord (来自 R1/R2/R3 三轮)")
    print(f"输出: {len(patterns)} 个 Pattern")
    print()
    
    for i, p in enumerate(patterns[:12], 1):
        critical = p["severities"].count("critical") + p["severities"].count("high")
        print(f"  EXP-{i:03d} | {p['type']:<30} | {p['dimension']} | {p['frequency']} | {'🔴' if critical>0 else '🟡'}")
        print(f"         cases: {', '.join(sorted(set(p['cases'])))}")
        print(f"         → {p['recommendation']}")
        print()
    
    print("=" * 70)
    print("这些 Pattern 需要人工审批后才能写入 experience_registry.yaml")
    print("审批后，下一次 Benchmark 将自动加载注册的经验。")
