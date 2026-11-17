# Validation Pattern: prediction（预测类模型）

> 适用模型: RandomForest, XGBoost, ARIMA, LSTM, SVR, 线性回归  
> 核心验证目标: 泛化能力 — "这个模型在没见过的数据上还能准吗？"

## required（必须执行）

| 类型 | 方法 | 参数 | 指标 | 原因 |
|------|------|------|------|------|
| train_test_split | 80_20 | split_ratio=0.8 | RMSE, MAE, R² | 最基础的泛化验证 |
| baseline_comparison | method_comparison | vs 简单基线(均值/线性) | RMSE ratio < 1 | 证明复杂模型的必要性 |
| residual_analysis | residual_check | 残差vs预测值图 | 正态性, 独立性 | 验证模型假设是否满足 |

## recommended

| 类型 | 方法 | 参数 | 指标 | 条件 |
|------|------|------|------|------|
| cross_validation | k_fold | k=5 | CV-RMSE, CV-MAE | 样本量 ≥ 50 |
| feature_importance | permutation | — | 特征排序 | 模型可解释时 |

## blocking_conditions

| 条件 | 替代方案 |
|------|------|
| 样本量 < 30 | cross_validation → blocked, 替代: leave_one_out |
| 样本量 < 10 | train_test_split → blocked, 仅报告训练集R²并诚实标注 |
| 时序数据 | train_test_split → 改为 time_series_split (不打乱顺序) |
