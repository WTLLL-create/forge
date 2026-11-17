# Validation Pattern: optimization（优化类模型）

> 适用模型: LP, MILP, GA, NSGA-II, SA, PSO  
> 核心验证目标: 解的可行性+最优性 — "这个解不仅满足约束，而且在所有可行解中是最优的吗？"

## required

| 类型 | 方法 | 参数 | 指标 | 原因 |
|------|------|------|------|------|
| constraint_feasibility | feasibility_check | 所有约束逐一验证 | 约束违反量=0 | 解必须可行 |
| convergence_check | multi_run | 3-5次独立运行 | 目标值标准差/均值 | 验证算法稳定性 |
| sensitivity_analysis | one_factor | 关键参数扫描 | 最优值变化率 | 参数不确定性对结论的影响 |

## recommended

| 类型 | 方法 | 参数 | 指标 | 条件 |
|------|------|------|------|------|
| baseline_comparison | method_comparison | vs 简单启发式 | 最优值差距 | 证明复杂算法的必要性 |
| parameter_tuning | grid_search | 算法超参数 | 最优参数组合 | 算法参数≤3个时 |
| pareto_analysis | hypervolume | — | HV | 多目标优化 |

## physical_validation（机理类）

| 类型 | 方法 | 参数 | 指标 |
|------|------|------|------|
| dimensional_consistency | unit_analysis | 所有公式 | 量纲一致 |
| boundary_condition | bc_verification | 极值检验 | 物理合理性 |

## blocking_conditions

| 条件 | 替代方案 |
|------|------|
| 单变量优化 | sensitivity_analysis → 改为 parameter_sweep（扫描变量取值范围） |
| 精确算法(LP/MILP) | convergence_check → not_applicable（精确算法天然收敛） |
