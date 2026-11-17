# Pandas 速查表

## I/O
| 操作 | 代码 |
|------|------|
| 读CSV | `pd.read_csv('f.csv', encoding='utf-8')` |
| 读Excel | `pd.read_excel('f.xlsx', sheet_name='S1')` |
| 读所有Sheet | `pd.read_excel('f.xlsx', sheet_name=None)` |
| 写CSV | `df.to_csv('f.csv', index=False)` |
| 写Excel | `df.to_excel('f.xlsx', index=False)` |

## 查看
| 操作 | 代码 |
|------|------|
| 前n行 | `df.head(10)` |
| 信息 | `df.info()` |
| 统计 | `df.describe()` |
| 形状 | `df.shape` |
| 列名 | `df.columns.tolist()` |
| 类型 | `df.dtypes` |
| 缺失数 | `df.isnull().sum()` |
| 唯一值 | `df.nunique()` |

## 选择
| 操作 | 代码 |
|------|------|
| 标签选 | `df.loc[row, col]` |
| 位置选 | `df.iloc[0:10, 0:3]` |
| 条件查询 | `df.query('A>0 and B<10')` |
| 布尔筛选 | `df[df['A'] > 0]` |
| 选多值 | `df[df['cat'].isin(['A','B'])]` |

## 缺失值
| 操作 | 代码 |
|------|------|
| 检测 | `df.isnull().sum()/len(df)*100` |
| 删行 | `df.dropna()` |
| 删列 | `df.dropna(axis=1, thresh=n)` |
| 中位数填 | `df['c'].fillna(df['c'].median())` |
| 众数填 | `df['c'].fillna(df['c'].mode()[0])` |
| 前向填充 | `df.fillna(method='ffill')` |
| 插值 | `df['c'].interpolate()` |

## 分组
| 操作 | 代码 |
|------|------|
| 分组均值 | `df.groupby('cat')['v'].mean()` |
| 多聚合 | `df.groupby('cat')['v'].agg(['mean','std','count'])` |
| 透视表 | `pd.pivot_table(df, values='v', index='i', columns='c', aggfunc='sum')` |
| 变换 | `df.groupby('cat')['v'].transform(lambda x: (x-x.mean())/x.std())` |

## 合并
| 操作 | 代码 |
|------|------|
| JOIN | `pd.merge(df1, df2, on='key', how='left')` |
| 拼接行 | `pd.concat([df1, df2], axis=0)` |
| 拼接列 | `pd.concat([df1, df2], axis=1)` |

## 时间序列
| 操作 | 代码 |
|------|------|
| 转时间 | `pd.to_datetime(df['d'])` |
| 设索引 | `df.set_index('date', inplace=True)` |
| 月重采样 | `df.resample('M').mean()` |
| 移动均线 | `df['v'].rolling(7).mean()` |
| 滑动标准差 | `df['v'].rolling(30).std()` |
| 同比变化 | `df['v'].pct_change(12)` |
| 年/月/日 | `df.index.year/month/day` |

## 清洗
| 操作 | 代码 |
|------|------|
| 去重 | `df.drop_duplicates()` |
| 重命名 | `df.rename(columns={'old':'new'})` |
| 排序 | `df.sort_values('v', ascending=False)` |
| 类型转换 | `df['c'].astype('float64')` |
| 截断 | `df['c'].clip(lower, upper)` |
| 去空格 | `df['c'].str.strip()` |
| One-Hot | `pd.get_dummies(df, columns=['cat'])` |

## 输出→NumPy
| 操作 | 代码 |
|------|------|
| DF→array | `df[cols].to_numpy(dtype=np.float64)` |
| Series→array | `df['c'].values` |
| 取列名 | `df[cols].columns.tolist()` |
