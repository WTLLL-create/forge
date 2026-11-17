# Core Contract Validation — 2020 A 题 Schema 化重跑

> 用 v1 Schema 重新表达之前的人工模拟链，验证每个接口是否能被下游消费。

---

## L1 → L2: ProblemState

```json
{
  "problem_id": "CUMCM_2020_A",
  "problem_type": "hybrid",
  "sub_type": ["physics_modeling", "parameter_identification", "single_objective"],
  "core_contradiction": "焊接质量(温度曲线需在工艺窗口内) vs 生产效率(过炉速度最大化)",
  "domain": "industrial_process",
  "constraints": [
    "峰值温度 240-250°C",
    "170°C以上时间 60-120s",
    "温升速率 < 3°C/s"
  ],
  "data_status": {
    "available": true,
    "format": "CSV",
    "estimated_rows": 500,
    "estimated_columns": 5,
    "has_missing": false,
    "has_time_series": false
  },
  "sub_problems": [
    { "id": "Q1", "task": "建立回流焊炉传热模型", "type": "physics_modeling" },
    { "id": "Q2", "task": "辨识对流换热系数", "type": "parameter_identification" },
    { "id": "Q3", "task": "优化过炉速度", "type": "single_objective" },
    { "id": "Q4", "task": "对称性分析与炉区优化", "type": "evaluation" }
  ]
}
```

**L2 可消费性**: ✅ `problem_type: hybrid, sub_type: [physics_modeling, single_objective]` → 路由到 `strategy_planner/hybrid_pipeline.md` + `optimization_pipeline.md`

---

## L2 → L3: StrategyPlan (在 core/contracts 中未单独定义，使用 ProblemState + 预期 steps)

L2 输出 StrategyPlan 直接进入 L3 Expert Decision。StrategyPlan 由 L3 内部的 `optimization_decision_rules.md` 根据 ProblemState.sub_type 自行推导，不需要单独 Schema。

✅ **简化决策**: 不需要 StrategyPlan Schema——ProblemState 的 sub_type 已足够路由 L3。

---

## L3 → L4: DecisionContract

```json
{
  "contract_id": "DC-CUMCM_2020_A-20240804",
  "problem_summary": {
    "problem_type": "hybrid",
    "sub_types": ["physics_modeling", "single_objective"],
    "n_sub_problems": 4
  },
  "decisions": [
    {
      "sub_problem_id": "Q1",
      "primary_model": "一维非稳态热传导(有限差分法)",
      "model_family": "physics",
      "reasoning": [
        "PCB在炉内匀速运动, x=vt→时间域一维传热",
        "排除集总参数法: Bi数不满足均匀温度假设",
        "排除二维模型: 宽度方向对称性可用一维简化"
      ],
      "alternatives_considered": [
        { "model": "集总参数法", "reason_rejected": "Bi=hL/k≈2.3 > 0.1, 温度梯度不可忽略" },
        { "model": "二维有限元", "reason_rejected": "对称性可用一维简化, 节省计算量" }
      ],
      "mandatory_validations": ["stability_check", "sensitivity_analysis"],
      "risk_flags": [
        { "flag": "显式格式CFL条件", "severity": "high", "mitigation": "Δt需满足 αΔt/Δx² < 0.5" }
      ],
      "expected_output": "温度分布曲线 + 峰值温度位置"
    },
    {
      "sub_problem_id": "Q2",
      "primary_model": "非线性最小二乘",
      "model_family": "statistics",
      "reasoning": [
        "对流系数h未知, 需以实验数据拟合",
        "残差最小化为自然目标",
        "排除网格搜索: h连续, 精度不足"
      ],
      "alternatives_considered": [
        { "model": "网格搜索", "reason_rejected": "h为连续变量, 网格离散化损失精度" }
      ],
      "mandatory_validations": ["residual_check", "cross_validation"],
      "risk_flags": [],
      "expected_output": "h=45.3 W/(m²·K), R²=0.97"
    },
    {
      "sub_problem_id": "Q3",
      "primary_model": "单变量有界优化",
      "model_family": "optimization",
      "reasoning": [
        "仅一个决策变量v, 约束连续可导",
        "scipy.optimize.minimize_scalar 专为此设计",
        "排除GA: 单变量用GA=杀鸡用牛刀+收敛慢"
      ],
      "alternatives_considered": [
        { "model": "GA", "reason_rejected": "单变量优化不需要种群搜索机制" }
      ],
      "mandatory_validations": ["sensitivity_analysis"],
      "risk_flags": [],
      "expected_output": "opt_v=78.5 cm/min, 工艺窗口验证通过"
    },
    {
      "sub_problem_id": "Q4",
      "primary_model": "敏感性分析",
      "model_family": "statistics",
      "reasoning": [
        "分析峰值温度对各炉区设定的敏感性",
        "验证对称性假设"
      ],
      "alternatives_considered": [],
      "mandatory_validations": ["robustness_check"],
      "risk_flags": [],
      "expected_output": "对称性成立(偏差<2%), 各炉区敏感性排序"
    }
  ],
  "cross_problem_consistency": {
    "incremental_approach": true,
    "model_reuse": ["Q1有限差分求解器→Q2拟合→Q3优化→Q4敏感性, 共用温度场计算结果"],
    "conflicts": []
  }
}
```

**L4 可消费性**: ✅ 每个子问题有明确的 `model_family` 和 `primary_model`，可直接路由到对应求解路径。
**断点修复**: 🔴→✅ DecisionContract 从自然语言→结构化 JSON。L4 模块可解析 `model_family: "optimization"` 直接加载对应求解器。

---

## L4 → L5: ModelResult (Q3 示例)

```json
{
  "result_id": "MR-DC-2020A-Q3",
  "sub_problem_id": "Q3",
  "model_used": "scipy.optimize.minimize_scalar(method='bounded')",
  "execution_status": "success",
  "results_summary": {
    "key_metrics": { "opt_v_cm_per_min": 78.5, "peak_temp_C": 243.2 },
    "output_type": "scalar",
    "summary_text": "最优过炉速度 v=78.5 cm/min, 峰值温度 243°C 满足 240-250°C 工艺窗口, 170°C以上时间=86s 满足 60-120s 要求"
  },
  "execution_log": {
    "environment": "Python 3.13, scipy 1.16",
    "runtime_seconds": 0.3,
    "convergence": true,
    "n_iterations": 12,
    "warnings": []
  },
  "issues": [],
  "model_fallback": { "occurred": false },
  "artifacts": {
    "figures": ["figures/Q3_temp_vs_speed.png"],
    "tables": ["results/Q3_validation.csv"],
    "data_outputs": []
  }
}
```

**L5 可消费性**: ✅ `output_type: "scalar"` + `results_summary.summary_text` → Evidence Layer 知道验证什么、论文用什么图。

---

## 总结：Schema 化前后对比

| 维度 | 之前 (Markdown) | 之后 (Schema JSON) |
|------|------|------|
| L1→L2 路由 | AI 读"这是一个优化问题"后手动判断 | `problem_type` 枚举值直接路由 |
| L3→L4 模型选择 | 自然语言 "推荐NSGA-II因为..." | `model_family` + `primary_model` + 结构化 reasoning |
| L4→L5 验证触发 | 人工检查结果后决定验证什么 | `mandatory_validations` 列表自动触发 |
| L5→L6 论文写作 | 人工整理结果后写论文 | `summary_text` 可直接插入摘要 |
| L7→L3 失败反馈 | 口头讨论 | `FailureRecord` 结构化可查询 |

**4 个严重断点修复状态**:
1. 🔴→✅ ProblemState Schema — 可路由
2. 🔴→✅ DecisionContract Schema — 可执行
3. 🔴→⚠️ 物理建模模型卡 — Schema 已定义 model_family: "physics"，但 models_expert/ 仍需补卡
4. 🔴→⚠️ 统一入口 — Schema 链已建，需一个主控脚本读取 contract 并路由
