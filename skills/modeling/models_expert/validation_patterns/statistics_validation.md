# Validation Pattern: statistics（统计/数据分析类模型）

> 适用模型: ANOVA, 最小二乘拟合, 分段线性拟合, 相关性分析, 假设检验  
> 核心验证目标: 推断可靠性 — "这个趋势/差异是真实的还是随机波动？"

## required

| 类型 | 方法 | 参数 | 指标 | 原因 |
|------|------|------|------|------|
| goodness_of_fit | R²_compute | 所有拟合曲线 | R², RMSE, MAE | 拟合质量是基础证据 |
| residual_analysis | normality_check | Shapiro-Wilk | p > 0.05 | 验证残差假设 |
| baseline_comparison | criteria_comparison | 单一vs多维准则 | 结果重叠率 | 证明多维准则的必要性（如Q2标志物筛选） |

## recommended

| 类型 | 方法 | 参数 | 指标 | 条件 |
|------|------|------|------|------|
| sensitivity_analysis | parameter_sweep | 阈值参数扫描 | Jaccard相似度 | 筛选类模型含阈值时 |
| cross_validation | leave_one_out | — | CV-RMSE | 时间点 ≥ 5个 |

## blocking_conditions

| 条件 | 替代方案 |
|------|------|
| 数据点 < 4 | goodness_of_fit → 计算但不报告精确R²值（不可靠） |
| 数据点 < 3 | 全部required → not_executable, 仅报告趋势方向 |
