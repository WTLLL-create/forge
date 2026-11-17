# 特征工程指南

> 从干净数据到模型就绪特征的转换策略

---

## 一、数值特征处理

### 1.1 标准化 (Standardization)

```python
# Z-Score: (x - μ) / σ
from scipy import stats
df['z'] = stats.zscore(df['value'])

# 适用场景：需要均值为0、标准差为1（PCA、距离计算、梯度优化）
```

### 1.2 归一化 (Normalization)

```python
# Min-Max: (x - min) / (max - min)
df['norm'] = (df['value'] - df['value'].min()) / \
             (df['value'].max() - df['value'].min())

# 适用场景：需要值在 [0,1] 范围内（神经网络、某些优化算法）
```

### 1.3 多项式特征

```python
# 创建 x, x², x³ 等（非线性关系建模）
df['x2'] = df['x'] ** 2
df['x3'] = df['x'] ** 3
df['sqrt_x'] = np.sqrt(np.abs(df['x']))  # 开方
df['log_x'] = np.log1p(df['x'])           # log(1+x) 处理零值
```

### 1.4 交互特征

```python
df['ratio'] = df['a'] / df['b']
df['product'] = df['a'] * df['b']
df['diff'] = df['a'] - df['b']
```

---

## 二、分类特征编码

```python
# One-Hot 编码（无序分类）
df_encoded = pd.get_dummies(df, columns=['category'],
                            prefix='cat', drop_first=True)

# 标签编码（有序分类，如低/中/高）
order = {'低': 0, '中': 1, '高': 2}
df['level_code'] = df['level'].map(order)

# 频数编码（高基数分类）
freq_map = df['category'].value_counts(normalize=True)
df['cat_freq'] = df['category'].map(freq_map)
```

---

## 三、时间特征

```python
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['quarter'] = df['date'].dt.quarter
df['dayofweek'] = df['date'].dt.dayofweek
df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)

# 周期性编码（保留循环特性）
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
```

---

## 四、特征选择（建模可用）

```python
# 相关性筛选（低方差过滤）
low_variance_cols = [c for c in df.columns
                     if df[c].nunique() > 1 and df[c].std() > 0.01]

# 高相关特征去重（避免多重共线性）
corr_matrix = df.corr().abs()
high_corr = np.where(corr_matrix > 0.9)
# 保留每组高相关特征中的第一个
```

---

## 五、输出标准化（连接 11.1）

```python
# 最终输出格式
X = df[selected_features].to_numpy(dtype=np.float64)
y = df[target_column].to_numpy(dtype=np.float64)

# 确保无 NaN / Inf
assert not np.any(np.isnan(X)), "X contains NaN"
assert not np.any(np.isinf(X)), "X contains Inf"
```
