# Pandas 完整参考 — 数模数据处理层 (S3)

> 来源：pandas-dev/pandas（GitHub 49k+ stars, BSD-3-Clause）
> 本文档蒸馏官方 README、10-Minute Guide、IO Guide、GroupBy、Timeseries、Merge 等核心文档
> 服务于 skills/modeling/ 状态机 S3 (DATA_PROCESSING) 的 6 步管道

---

## 一、核心数据结构

| 类型 | 说明 | 创建示例 |
|------|------|----------|
| **Series** | 一维带标签数组 | `pd.Series([1, 3, 5, np.nan, 6, 8])` |
| **DataFrame** | 二维表格，行+列 | `pd.DataFrame(np.random.randn(6,4), index=dates, columns=list("ABCD"))` |
| **Index** | 不可变的轴标签 | `df.index`, `df.columns` |

> `df.to_numpy()` 输出为 NumPy 数组（喂给 S4 求解层）。注意：NumPy 数组只有一种 dtype，而 DataFrame 每列各有一种。

---

## 二、S3 步骤 1：数据读取 (pd.read_*)

### read_csv 核心参数速查

```python
import pandas as pd

# 基本读取
df = pd.read_csv('data.csv', encoding='utf-8')

# 比赛常用组合
df = pd.read_csv(
    'data.csv',
    encoding='utf-8',         # 编码
    sep=',',                  # 分隔符（可用 \t, ;, \s+ 等）
    header=0,                 # 第几行作列名，None=无列名
    index_col=0,              # 索引列（None=自动生成）
    usecols=['A', 'B', 'C'],  # 只读部分列（大文件省内存）
    dtype={'col1': 'float64'},# 显式指定类型
    parse_dates=['date_col'], # 日期解析
    na_values=['NA', 'NULL'], # 自定义缺失值标记
    skiprows=5,               # 跳过行
    nrows=1000,               # 只读前 N 行（预览）
)

# 分块读取大文件（>1GB）
reader = pd.read_csv('large.csv', chunksize=10000)
for chunk in reader:
    process(chunk)

# 从 URL 直接读取
df = pd.read_csv('https://example.com/data.csv')
```

### read_excel

```python
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')
df = pd.read_excel('data.xlsx', sheet_name=None)  # 读取所有sheet → dict
```

### 读取后立即输出

```python
df = pd.read_csv('data.csv')
# 喂给 S4 求解层
X = df.to_numpy()          # 整个DataFrame → numpy array
y = df['target'].values    # 单列 → numpy array
```

---

## 三、S3 步骤 2：数据检查

```python
df.head(10)           # 前10行
df.tail(5)            # 后5行
df.info()             # 数据类型 + 非空计数
df.describe()         # count/mean/std/min/25%/50%/75%/max
df.shape              # (行数, 列数)
df.dtypes             # 每列 dtype
df.isnull().sum()     # 每列缺失值计数
df.duplicated().sum() # 重复行计数
df.nunique()          # 每列唯一值个数
df.columns.tolist()   # 列名列表
```

> **数模论文要求**：info() + describe() 的输出形成"数据概况"表格

---

## 四、S3 步骤 3：数据清洗

### 缺失值处理

```python
df.dropna(how='any')              # 丢弃含缺失的行
df.dropna(subset=['col1','col2']) # 只检查特定列
df.fillna(0)                      # 填0
df.fillna(df.mean())              # 填均值
df.fillna(method='ffill')         # 前向填充（时序适用）
df.fillna(method='bfill')         # 后向填充
```

### 异常值处理

```python
# clip 截断
df['col'] = df['col'].clip(lower=0, upper=100)

# 条件替换
df.loc[df['col'] > 100, 'col'] = 100
```

### 重复/类型

```python
df.drop_duplicates(inplace=True)
df['col'] = df['col'].astype('float64')
```

### ⚠️ 常见坑位

| 问题 | 症状 | 解决 |
|------|------|------|
| 编码乱码 | 中文变?? | `encoding='gbk'` 或 `'utf-8-sig'` |
| 千分位逗号 | "1,234" 被读成字符串 | `thousands=','` |
| 欧洲小数点 | "1.234,5" 无法 parse | `decimal=',', thousands='.'` |
| 混合类型列 | dtype=object | `dtype=float` 强制或 `pd.to_numeric(errors='coerce')` |

---

## 五、数据选择与筛选 (S3 用)

```python
# 选列
df['A']               # 单列 → Series
df[['A', 'B']]         # 多列 → DataFrame

# 按标签选行 (loc)
df.loc[0:10]                         # 行标签0到10（含两端）
df.loc[:, ['A', 'B']]                # 所有行，A、B列
df.loc[df['A'] > 0, ['B', 'C']]      # 条件选行列

# 按位置选 (iloc)
df.iloc[0:5]          # 前5行
df.iloc[:, 0:3]       # 前3列

# 布尔索引（最常用）
df[df['A'] > 0]                       # A列>0的行
df[(df['A'] > 0) & (df['B'] < 10)]   # 多条件：用 & | ~，必须加括号
df[df['col'].isin(['a', 'b', 'c'])]   # 在列表中
```

### ⚠️ 注意

```python
# 错误：这样会报错
if pd.Series([False, True, False]):
    pass
# 正确：用 .any() .all() .empty .bool() .item()
```

---

## 六、S3 步骤 4-5：探索分析与特征构造

### groupby — 分组聚合（数模核心操作）

```python
# 基本分组聚合
df.groupby('A')['C'].sum()
df.groupby(['A', 'B']).mean()

# 命名聚合（推荐写法）
df.groupby('kind').agg(
    min_val=('height', 'min'),
    max_val=('height', 'max'),
    avg_val=('weight', 'mean'),
)

# 多函数
df.groupby('A').agg(['sum', 'mean', 'std'])

# 不同列不同函数
df.groupby('A').agg({'C': 'sum', 'D': 'std'})

# 内置分组方法
.groupby('A').sum()      .groupby('A').mean()
.groupby('A').std()      .groupby('A').count()
.groupby('A').min()      .groupby('A').max()
.groupby('A').median()   .groupby('A').nunique()
.groupby('A').first()    .groupby('A').last()
.groupby('A').size()     # 含NA计数

# transform：结果广播回原始大小
df.groupby('key')['val'].transform('mean')  # 组均值填充
df.groupby('key')['val'].transform('cumsum') # 组内累计

# filter：过滤组
df.groupby('B').filter(lambda x: len(x) > 2)
```

> **性能提示**：拆分多步内置操作 > `apply` + UDF（Python 函数慢 10-100x）

### pivot_table — 透视表

```python
pd.pivot_table(df, values='D', index=['A','B'], columns=['C'])
```

### merge — 表连接（多数据源融合）

```python
# SQL 风格
pd.merge(left, right, on='key')                     # 内连接
pd.merge(left, right, on='key', how='left')         # 左连接
pd.merge(left, right, on='key', how='outer')        # 外连接

# 不同列名
pd.merge(left, right, left_on='lkey', right_on='rkey')

# 索引连接
left.join(right, on='key')

# validate 防范数据错误
pd.merge(left, right, on='key', validate='one_to_one')  # 有重复键会报错

# indicator 追踪来源
pd.merge(df1, df2, on='col', how='outer', indicator=True)  # 添加 _merge 列
```

### concat — 轴向拼接

```python
pd.concat([df1, df2, df3])                # 行堆叠（axis=0）
pd.concat([df1, df4], axis=1)             # 列拼接
pd.concat(frames, keys=['x','y','z'])     # 带分组标签
pd.concat(frames, ignore_index=True)      # 重建索引
```

### 常见特征构造

```python
# 标准化
from scipy.stats import zscore
df['z_col'] = zscore(df['col'])

# 离散化
pd.cut(df['age'], bins=[0, 18, 35, 60, 100], labels=['少年','青年','中年','老年'])
pd.qcut(df['score'], q=4)  # 等频分箱

# 移位（构造滞后特征）
df['lag_1'] = df['col'].shift(1)
df['diff_1'] = df['col'].diff(1)

# 滚动窗口（时序特征）
df['rolling_mean'] = df['col'].rolling(window=7).mean()
df['rolling_std'] = df['col'].rolling(window=7).std()

# 分组排名
df['rank'] = df.groupby('group')['val'].rank()
```

---

## 七、时序专项操作（预测类赛题必需）

```python
# 生成日期范围
pd.date_range('2020-01-01', periods=365, freq='D')     # 日频率
pd.date_range('2020-01', '2020-12', freq='ME')          # 月末

# 频率转换（重采样）
ts.resample('D').mean()      # 秒级 → 日级
ts.resample('W').sum()       # 日级 → 周级
ts.resample('ME').ohlc()     # OHLC 聚合

# 移位（lag/shift）
df['prev'] = df['val'].shift(1)                # 数据平移（索引不变）
df_shifted = df.shift(5, freq='D')              # 索引平移（日期后移）

# 解析日期
pd.to_datetime('2010/11/12', format='%Y/%m/%d')
pd.to_datetime(['2009/07/31', 'asd'], errors='coerce')  # 无效→NaT

# 部分字符串索引（非常方便）
df.loc['2020']           # 整年
df.loc['2020-06']        # 整月
df.loc['2020-01':'2020-03']  # 切片

# ⚠️ 时序验证必须时间切分，不可随机抽样！
```

### 频率偏移别名速查

| 别名 | 含义 | 别名 | 含义 |
|------|------|------|------|
| `D` | 日历日 | `B` | 工作日 |
| `h` | 小时 | `min` | 分钟 |
| `s` | 秒 | `W` | 周 |
| `ME` | 月末 | `MS` | 月初 |
| `QE` | 季末 | `YE` | 年末 |

---

## 八、S3 步骤 6：输出转换 → 喂给 S4

```python
# 特征矩阵 → numpy（S4 求解层入口）
X = df[feature_cols].to_numpy()   # shape (n_samples, n_features)
y = df[target_col].values         # shape (n_samples,)

# 确保无 NaN
assert not np.isnan(X).any(), "X contains NaN"
```

---

## 九、其他实用操作

```python
# 字符串处理
df['col'].str.lower()
df['col'].str.replace('old', 'new')
df['col'].str.extract(r'(\d+)')    # 正则提取

# 排序
df.sort_values(by='col', ascending=False)
df.sort_index(axis=1, ascending=False)

# 值计数
df['col'].value_counts()

# 分类数据（节省内存）
df['grade'] = df['grade'].astype('category')

# I/O 输出
df.to_csv('output.csv', index=False, encoding='utf-8-sig')
df.to_excel('output.xlsx', sheet_name='Sheet1', index=False)
df.to_parquet('output.parquet')  # 高效二进制格式
```

---

## 十、数模场景速查

| 我需要... | Pandas 操作 |
|-----------|------------|
| 读取竞赛附件 .xlsx/.csv | `pd.read_excel()` / `pd.read_csv()` |
| 快速看数据长什么样 | `df.head()` + `df.info()` + `df.describe()` |
| 检查缺失值 | `df.isnull().sum()` |
| 缺失值填充（均值/前向） | `df.fillna(df.mean())` / `df.fillna(method='ffill')` |
| 按类别分组统计 | `df.groupby('category').agg(['mean','std'])` |
| 合并多个数据源 | `pd.merge(df1, df2, on='key', how='left')` |
| 时序数据重采样 | `ts.resample('D').mean()` |
| 构造滞后特征 | `df['col'].shift(1)` |
| 标准化特征 | `from scipy.stats import zscore` |
| 输出给求解器 | `df.to_numpy()` |
