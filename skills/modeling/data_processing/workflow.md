# 数据处理标准工作流

> 数学建模 6 步标准管道：从原始文件到模型就绪输入
>
> 每一步有明确的输入/输出类型和质检标准
>
> **参考实现**：Pandas 完整 API 速查见 `pandas_integration.md`（IO、groupby、时序、merge 等）

---

## 管道总览

```
Raw Data (CSV/Excel/JSON, 可能来自多个数据源)
    │
    ▼
Step 0: 多源数据合并 (Stage 20.4 新增)
    │  → data_fusion/multi_source_merge.md
    │  输出: 统一的 DataFrame (已合并多源数据)
    ▼
Step 1: 数据读取 — pd.read_csv / read_excel
    │  输出: DataFrame + 基本信息
    ▼
Step 2: 数据检查 — info/describe/isnull/duplicated
    │  输出: 数据质量报告（缺失率、异常值、类型问题）
    ▼
Step 3: 数据清洗 — fillna/dropna/drop_duplicates/clip
    │  输出: 干净的 DataFrame
    ▼
Step 4: 探索分析 — groupby/corr/describe/plot
    │  输出: 变量关系、分布特征、趋势
    ▼
Step 5: 特征构造 — 标准化/编码/组合特征/多项式
    │  输出: 特征矩阵 X + 目标向量 y
    ▼
Step 6: 输出转换 — df.to_numpy() / df.to_csv()
    │  输出: numpy.ndarray → 喂给 numerical_computing Skill
```

---

## Step 1: 数据读取

### 输入

文件路径（CSV/Excel/JSON/数据库连接）

### 操作

```python
import pandas as pd

# CSV（最常见）
df = pd.read_csv('data.csv', encoding='utf-8')

# Excel（多工作表）
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')

# 大文件分块
for chunk in pd.read_csv('large.csv', chunksize=10000):
    process(chunk)
```

### 质检要点

- [ ] 文件是否成功读取（行数 > 0）
- [ ] 列名是否包含乱码（encoding 问题）
- [ ] Excel 多 sheet 是否都已读取
- [ ] 分隔符是否正确（CSV 可能是 tab 或分号）

### 输出

`DataFrame` + `(n_rows, n_cols)` 基本信息

---

## Step 2: 数据检查

### 操作

```python
# 结构检查
print(f"形状: {df.shape}")
print(f"列名: {df.columns.tolist()}")
print(f"类型:\n{df.dtypes}")

# 质量检查
print(f"缺失值:\n{df.isnull().sum()}")
print(f"缺失比例:\n{(df.isnull().sum()/len(df)*100).round(2)}%")
print(f"重复行: {df.duplicated().sum()}")

# 统计描述
print(df.describe(include='all').round(2))
```

### 检查清单

| 检查项 | 方法 | 正常阈值 | 异常处理 |
|--------|------|----------|----------|
| 行列数 | `df.shape` | — | 与预期对比 |
| 列类型 | `df.dtypes` | 数值列应为 float/int | 检查 object 列是否是数字 |
| 缺失比例 | `df.isnull().sum()/len(df)` | < 5% 单列 | >20% 考虑删除该列 |
| 重复行 | `df.duplicated().sum()` | 0 | 检查并删除 |
| 数值范围 | `df.describe()` | 无异常范围 | min/max 超出物理意义上的检查 |
| 唯一值 | `df.nunique()` | — | 唯一值=1 的列是常数列 |

### 输出

数据质量报告（Markdown 格式，可附入论文）

---

## Step 3: 数据清洗

### 3.1 缺失值处理

决策树：
```
缺失比例 < 5%   → fillna(median/mode) 或 dropna
缺失比例 5-20%  → fillna(method='ffill') 或插值
缺失比例 20-50% → 仔细判断，可能用模型预测填充
缺失比例 > 50%  → drop 该列
```

```python
# 数值列: 中位数填充（抗异常值）
df['num_col'].fillna(df['num_col'].median(), inplace=True)

# 分类列: 众数填充
df['cat_col'].fillna(df['cat_col'].mode()[0], inplace=True)

# 时间序列: 前向填充
df['ts_col'].fillna(method='ffill', inplace=True)

# 插值（更平滑）
df['num_col'].interpolate(method='linear', inplace=True)
```

### 3.2 异常值处理

详见 `data_quality/outlier_detection.md`

```python
# IQR 方法
Q1 = df['col'].quantile(0.25)
Q3 = df['col'].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
df_clean = df[(df['col'] >= lower) & (df['col'] <= upper)]

# 截断（不删除）
df['col'] = df['col'].clip(lower, upper)
```

### 3.3 其他清洗

```python
# 去重
df.drop_duplicates(inplace=True)

# 重命名列
df.rename(columns={'中文名': 'english_name'}, inplace=True)

# 类型转换
df['col'] = df['col'].astype('float64')
df['date'] = pd.to_datetime(df['date'])

# 去除空格
df['col'] = df['col'].str.strip()
```

### 输出

干净的 DataFrame，无缺失值、无重复、类型正确

---

## Step 4: 探索分析

### 4.1 单变量分析

```python
# 数值变量: 分布
df['col'].hist(bins=30)
df['col'].describe()

# 分类变量: 频次
df['cat'].value_counts()
df['cat'].value_counts(normalize=True)  # 比例
```

### 4.2 多变量分析

```python
# 相关性矩阵
corr_matrix = df.corr()
# 高相关对 (>0.8 或 <-0.8)

# 分组统计
df.groupby('category')['value'].agg(['mean','std','count','min','max'])

# 交叉表
pd.crosstab(df['cat1'], df['cat2'], normalize='index')
```

### 4.3 趋势分析（时间序列）

```python
# 时间聚合
df_monthly = df.resample('M', on='date')['value'].mean()

# 滑动平均
df['smooth'] = df['value'].rolling(window=7).mean()

# 同比/环比
df['pct_change'] = df['value'].pct_change()
```

### 输出

变量间关系洞察、可用于论文第四章（数据分析）的统计结果

---

## Step 5: 特征构造

详见 `feature_engineering/index.md`

```python
# 标准化 (Z-score)
from scipy import stats
df['z_score'] = stats.zscore(df['value'])

# Min-Max 归一化
df['norm'] = (df['value'] - df['value'].min()) / (df['value'].max() - df['value'].min())

# One-Hot 编码
df_encoded = pd.get_dummies(df, columns=['category'])

# 特征组合
df['ratio'] = df['a'] / df['b']
df['product'] = df['a'] * df['b']

# 时间特征提取
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['day_of_week'] = df['date'].dt.dayofweek
```

### 输出

特征矩阵 X + 目标变量 y，均为 numpy.ndarray 格式

---

## Step 6: 输出转换 — 连接 Numerical Computing

```python
# DataFrame → NumPy（标准输出格式）
X = df[feature_cols].to_numpy(dtype=np.float64)
y = df[target_col].to_numpy(dtype=np.float64)

# 或保留 DataFrame
clean_df.to_csv('clean_data.csv', index=False)
```

### 与阶段 11.1 的接口约定

```
data_processing Skill 输出          numerical_computing Skill 输入
─────────────────────────────────────────────────────────────────
numpy.ndarray (n_samples, n_feat) → scipy.optimize.minimize
numpy.ndarray (n_corr, n_corr)    → numpy.linalg.eig
numpy.ndarray (n_samples,)        → scipy.optimize.curve_fit
pandas.DataFrame (带时间索引)     → 可直接用于 scipy.integrate.solve_ivp 的目标函数
```
