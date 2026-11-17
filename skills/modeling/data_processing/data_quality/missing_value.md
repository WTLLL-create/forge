# 缺失值处理策略

> 数学建模中缺失值的系统性处理方法

---

## 一、缺失值分类

| 类型 | 特征 | 举例 | 策略 |
|------|------|------|------|
| MCAR（完全随机缺失） | 缺失与任何变量无关 | 传感器偶然故障 | 删除/简单填充 |
| MAR（随机缺失） | 缺失与其他观测变量有关 | 低收入者不愿填收入 | 建模填充 |
| MNAR（非随机缺失） | 缺失与自身值有关 | 高收入者隐瞒收入 | 谨慎处理，可能需要引入缺失指示变量 |

---

## 二、处理决策矩阵

```
                   缺失比例
               <5%     5-20%   20-50%   >50%
              ──────  ──────  ──────  ──────
数值列:       中位数   插值    建模填充  删列
分类列:       众数     众数    建模填充  删列
时间序列:     前向填充 插值   建模填充   删列
目标变量:     删行    删行     删行     删行 ← 绝不填充
```

---

## 三、填充方法详解

### 3.1 简单填充

```python
import pandas as pd
import numpy as np

# 数值列
df['num'].fillna(df['num'].median(), inplace=True)   # 中位数（抗异常值）
df['num'].fillna(df['num'].mean(), inplace=True)     # 均值（无异常值时用）

# 分类列
df['cat'].fillna(df['cat'].mode()[0], inplace=True)  # 众数
df['cat'].fillna('Unknown', inplace=True)            # 新类别

# 时间序列
df.fillna(method='ffill', inplace=True)  # 前向（用上一个值）
df.fillna(method='bfill', inplace=True)  # 后向（用下一个值）
```

### 3.2 插值填充

```python
# 线性插值（均匀间隔数据）
df['num'].interpolate(method='linear', inplace=True)

# 时间插值（支持非均匀间隔）
df['num'].interpolate(method='time', inplace=True)

# 三次样条（平滑曲线）
df['num'].interpolate(method='cubic', inplace=True)
```

### 3.3 分组填充

```python
# 按类别填充组内中位数
df['num'] = df.groupby('category')['num'].transform(
    lambda x: x.fillna(x.median())
)
```

### 3.4 建模填充（高级）

```python
# 用其他列预测缺失值
from sklearn.ensemble import RandomForestRegressor

def fill_by_model(df, target_col):
    """用随机森林预测并填充缺失值"""
    train = df[df[target_col].notna()]
    predict = df[df[target_col].isna()]

    if len(predict) == 0 or len(train) < 10:
        return df

    features = [c for c in df.columns if c != target_col
                and df[c].dtype in ['float64', 'int64']]

    model = RandomForestRegressor(n_estimators=100)
    model.fit(train[features], train[target_col])

    df.loc[df[target_col].isna(), target_col] = model.predict(predict[features])
    return df
```

---

## 四、可视化工具

### missingno（推荐）

```python
import missingno as msno

# 缺失矩阵
msno.matrix(df)

# 缺失柱状图
msno.bar(df)

# 缺失相关性热图
msno.heatmap(df)
```

### fg-data-profiling（自动报告）

```python
from data_profiling import ProfileReport

profile = ProfileReport(df, title="Missing Value Report")
profile.to_file("missing_report.html")
```

---

## 五、建模比赛中的最佳实践

1. **先理解再动手**：缺失值处理前先用 missingno 可视化，理解缺失模式
2. **保守填充分类列**：创建 'Unknown' 类而非填众数，保留"未知"信息
3. **时序数据优先用插值**：前向/时间插值比中位数更合理
4. **目标变量绝不填充**：缺失的目标值直接删除
5. **记录处理日志**：每一步处理后记录 `df.shape`，确保数据量变化可追溯
