# 异常值检测方法

> 数学建模中异常值的识别与处理

---

## 一、检测方法

### 1.1 IQR 方法（最通用，推荐首选）

```python
import pandas as pd
import numpy as np

def detect_outliers_iqr(df, column, multiplier=1.5):
    """IQR 方法检测异常值"""
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - multiplier * IQR
    upper = Q3 + multiplier * IQR

    outliers = df[(df[column] < lower) | (df[column] > upper)]
    return outliers, lower, upper
```

### 1.2 Z-Score 方法（正态分布数据）

```python
from scipy import stats

def detect_outliers_zscore(df, column, threshold=3):
    """Z-Score 方法（适用于近似正态分布）"""
    z_scores = np.abs(stats.zscore(df[column].dropna()))
    return df[z_scores > threshold]
```

### 1.3 百分位数法（简单快速）

```python
def detect_outliers_percentile(df, column, lower_pct=1, upper_pct=99):
    """百分位数法"""
    lower = np.percentile(df[column].dropna(), lower_pct)
    upper = np.percentile(df[column].dropna(), upper_pct)
    outliers = df[(df[column] < lower) | (df[column] > upper)]
    return outliers, lower, upper
```

---

## 二、处理策略

### 2.1 方法选择

| 情况 | 方法 | 代码 |
|------|------|------|
| 数据充足，异常值稀疏 | 删除 | `df[df['col'].between(lower, upper)]` |
| 数据不足或需要完整 | 截断 | `df['col'].clip(lower, upper)` |
| 需要保留信息 | 标记 | `df['is_outlier'] = (z > 3)` |

### 2.2 实现

```python
# 删除异常值
Q1, Q3 = df['col'].quantile([0.25, 0.75])
IQR = Q3 - Q1
df_clean = df[(df['col'] >= Q1 - 1.5*IQR) &
              (df['col'] <= Q3 + 1.5*IQR)]

# 截断（保留行数）
df['col'] = df['col'].clip(
    lower=df['col'].quantile(0.01),
    upper=df['col'].quantile(0.99)
)
```

---

## 三、建模注意事项

1. **物理约束优先**：如果已知变量不可能为负（如价格、人口），用 `clip(lower=0)` 而不是统计方法
2. **分组检测**：不同类别的数据可能有不同的正常范围，应分组检测异常值
3. **保留证据**：异常值处理后在论文中说明方法、理由、处理数量
4. **不需要过度清洗**：统计异常≠数据错误，有些"异常"恰恰是模型需要解释的现象
