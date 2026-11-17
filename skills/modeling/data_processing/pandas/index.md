# Pandas 知识提炼：数学建模核心用法

> 来源：https://github.com/pandas-dev/pandas （v2.x, 49.3k stars）
>
> 聚焦建模场景，不做API手册式罗列

---

## 一、数据结构

### DataFrame — 数学建模的数据中心

```python
import pandas as pd
import numpy as np

# 从字典创建（常用于模拟数据生成）
df = pd.DataFrame({
    'x': np.linspace(0, 10, 100),
    'y': np.sin(np.linspace(0, 10, 100)),
    'category': np.random.choice(['A', 'B', 'C'], 100)
})
```

### Series — 单列数据载体

```python
s = df['x']                    # 选择单列得 Series
s = pd.Series([1, 2, 3], name='values')  # 直接创建
```

---

## 二、I/O 操作（建模入口）

```python
# CSV — 竞赛中最常见
df = pd.read_csv('附件1.csv', encoding='utf-8', parse_dates=['日期'])

# Excel — 多工作表附件
sheets = pd.read_excel('附件.xlsx', sheet_name=None)  # 返回 dict
for name, sheet in sheets.items():
    print(f"Sheet: {name}, shape={sheet.shape}")

# 导出
df.to_csv('clean_data.csv', index=False, encoding='utf-8-sig')
df.to_excel('result.xlsx', sheet_name='结果', index=False)
```

---

## 三、数据查看

```python
df.head(10)        # 前10行 — 快速浏览
df.tail(5)         # 后5行 — 检查末尾
df.info()          # 列、类型、非空数、内存 — 必做第一步
df.describe()      # 均值/std/min/25%/50%/75%/max — 必做第二步
df.shape           # (行数, 列数)
df.columns.tolist()  # 列名列表
df.dtypes          # 每列数据类型
df.nunique()       # 每列唯一值数量
```

---

## 四、数据选择

```python
# 基于标签: loc[row, col]
df.loc[0:5, ['A', 'B']]         # 第0-5行，A和B列
df.loc[df['A'] > 0, :]           # A>0的所有行

# 基于位置: iloc[row_pos, col_pos]
df.iloc[:10, :3]                 # 前10行，前3列

# 条件查询: query（可读性强）
df.query('A > 0 and B < 100 and category == "X"')

# 选择特定值
df[df['category'].isin(['A', 'B'])]
```

---

## 五、缺失值处理

```python
# 检测
df.isnull().sum()                    # 每列缺失计数
df.isnull().sum() / len(df) * 100    # 每列缺失比例(%)

# 删除
df.dropna()                           # 删除任何含缺失的行
df.dropna(subset=['关键列'])          # 仅关键列缺失才删除
df.dropna(axis=1, thresh=len(df)*0.5) # 缺失超50%的列删除

# 填充
df['num'].fillna(df['num'].median())        # 中位数（推荐）
df['cat'].fillna(df['cat'].mode()[0])       # 众数
df.fillna(method='ffill')                   # 前向填充（时间序列）
df['num'].interpolate(method='linear')      # 线性插值
```

---

## 六、分组与聚合

```python
# 基础分组
df.groupby('category')['value'].mean()
df.groupby('category')['value'].agg(['mean', 'std', 'count', 'min', 'max'])

# 多重分组
df.groupby(['year', 'month'])['sales'].sum()

# 透视表
pd.pivot_table(df, values='sales', index='year',
               columns='product', aggfunc='sum', fill_value=0)

# 变换（保持原行数）
df['z_score'] = df.groupby('category')['value'].transform(
    lambda x: (x - x.mean()) / x.std()
)
```

---

## 七、合并与连接

```python
# merge — SQL JOIN
pd.merge(df1, df2, on='key', how='left')
pd.merge(df1, df2, left_on='id', right_on='ref_id')

# concat — 行/列拼接
pd.concat([df1, df2], axis=0)      # 上下拼接（行）
pd.concat([df1, df2], axis=1)      # 左右拼接（列）

# join — 索引连接
df1.join(df2, on='key')
```

---

## 八、时间序列

```python
# 转换与索引
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

# 重采样
df.resample('M').mean()           # 月度均值
df.resample('Q').sum()            # 季度总和
df.resample('Y').last()           # 年末值

# 滑动窗口
df['ma7'] = df['value'].rolling(window=7).mean()   # 7日移动平均
df['std30'] = df['value'].rolling(window=30).std()  # 30日波动率

# 时间特征提取
df['year'] = df.index.year
df['month'] = df.index.month
df['quarter'] = df.index.quarter
df['dayofweek'] = df.index.dayofweek
```

---

## 九、数据清洗常用

```python
# 去重
df.drop_duplicates()
df.drop_duplicates(subset=['id'])  # 按特定列去重

# 重命名
df.rename(columns={'旧名': 'new_name'})

# 排序
df.sort_values('value', ascending=False)
df.sort_index()  # 按索引排序

# 类型转换
df['col'] = pd.to_numeric(df['col'], errors='coerce')
df['col'] = df['col'].astype('float32')

# 条件替换
df['col'].clip(lower=0, upper=100)
df['col'].replace({-999: np.nan})  # 特殊值→NaN
```

---

## 十、输出到 NumPy（连接 Numerical Computing Skill）

```python
# DataFrame → NumPy array（最常用）
X = df[['feat1', 'feat2', 'feat3']].to_numpy(dtype=np.float64)
y = df['target'].to_numpy(dtype=np.float64)

# Series → NumPy array
values = df['col'].values  # 或 .to_numpy()

# 保留列名信息
feature_names = df[['feat1', 'feat2']].columns.tolist()
```
