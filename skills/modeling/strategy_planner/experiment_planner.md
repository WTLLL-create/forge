# Experiment Planner — 批量实验管理器

> Stage 20.5: 支持 N模型×M指标 的批量实验组织。
> 解决断点 #3: Strategy Planner 缺少并行多模型验证的操作指导。

## 批量实验模板

```python
# 模型列表
models = {
    'ARIMA': ARIMAModel(),
    'RandomForest': RandomForestModel(),
    'XGBoost': XGBoostModel(),
    'LSTM': LSTMModel(),
}

# 统一实验框架
results = []
for name, model in models.items():
    # 训练
    model.fit(X_train, y_train)
    # 预测
    y_pred = model.predict(X_test)
    # 评估
    metrics = {
        '模型': name,
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred)),
        'MAE': mean_absolute_error(y_test, y_pred),
        'R2': r2_score(y_test, y_pred),
    }
    results.append(metrics)

# 对比表
df_results = pd.DataFrame(results).sort_values('RMSE')
```

## Experiment Plan 格式

```json
{
  "experiment_id": "exp_2021B_air_quality",
  "models": [
    {"name": "ARIMA", "params": {"order": "(2,1,2)"}},
    {"name": "XGBoost", "params": {"n_estimators": 200, "max_depth": 6}},
    {"name": "RandomForest", "params": {"n_estimators": 200}}
  ],
  "validation": {
    "method": "time_series_split",
    "test_size": 0.2,
    "metrics": ["RMSE", "MAE", "R2"]
  }
}
```

## 论文表达

多模型对比表 (思路可参考 paper_integration/figure_table_rules.md 增补模板；成稿形式、列结构、是否加粗/排名必须符合 standards/academic_table_standard.md 与锁定的 table_spec.json，模板中的最优值加粗等旧默认已废止)
