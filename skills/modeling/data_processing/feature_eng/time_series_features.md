# Time Series Feature Engineering — 时序特征工程

> 时序预测中，特征工程对精度的提升常常超过换模型。
> 参考: architecture_patterns/feature_engineering_pipeline.md

## 标准操作矩阵

### lag feature (滞后特征)

```python
# 捕捉时间滞后效应
for lag in [1, 2, 3, 7, 14]:  # 1天前/2天前/1周前/2周前
    df[f'O3_lag_{lag}'] = df['O3'].shift(lag)
```

适用: 任何时序问题。最基础的特征。

### rolling statistics (滚动统计)

```python
# 捕捉局部趋势和波动
for window in [3, 7, 14]:
    df[f'O3_roll_mean_{window}'] = df['O3'].rolling(window).mean()
    df[f'O3_roll_std_{window}'] = df['O3'].rolling(window).std()
    df[f'O3_roll_max_{window}'] = df['O3'].rolling(window).max()
```

适用: 短期波动 vs 中期趋势 vs 长期趋势。

### diff feature (差分特征)

```python
# 捕捉变化率
df['O3_diff_1'] = df['O3'].diff(1)   # 日变化
df['O3_diff_7'] = df['O3'].diff(7)   # 周变化
df['O3_pct_change'] = df['O3'].pct_change()  # 变化率
```

适用: 平稳性要求 (ARIMA) 或关注变化量而非绝对值。

### season encoding (周期编码)

```python
df['month'] = df['date'].dt.month
df['day_of_week'] = df['date'].dt.dayofweek
df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
df['season'] = df['month'].map({12:'冬', 1:'冬', 2:'冬', 3:'春', ...})
```

适用: 有明显季节性的数据 (空气质量/能源/销售)。

### interaction (交互特征)

```python
# 高温+静风 → 臭氧爆发 (物理机制驱动的交互)
df['temp_x_wind'] = df['temp'] * df['wind_speed']
df['temp_div_humid'] = df['temp'] / (df['humidity'] + 1)
```

适用: 物理/化学机制暗示的联合效应。

## 特征选择

生成大量特征后 → 筛选:
1. 与目标的相关性分析 (Pearson/Spearman)
2. 特征重要性 (RF/XGBoost 的 feature_importances_)
3. 多重共线性检查 (VIF > 10 → 去掉)

## 论文表达

"在原始特征基础上，构造了以下时序特征: 滞后项(捕捉时间依赖)、滚动统计(捕捉局部趋势)、交互项(捕捉物理机制)……经过相关性筛选和VIF检验，最终保留X个特征。"
