# GitHub 仓库调研结果

> 阶段 11.2 — 第一部分 & 第二部分
>
> 调研日期：2026-07-29

---

## 一、核心仓库：pandas-dev/pandas

| 属性 | 内容 |
|------|------|
| **名称** | pandas |
| **GitHub 地址** | https://github.com/pandas-dev/pandas |
| **Stars** | ~49,300 |
| **Forks** | ~20,100 |
| **提交数** | 38,491 |
| **最新提交** | 2026-07-29 |
| **最新版本** | v2.x (2026活跃发布) |
| **许可证** | BSD-3-Clause |
| **维护状态** | ✅ 极活跃（日级提交） |
| **官网** | https://pandas.pydata.org |
| **文档** | https://pandas.pydata.org/docs/ |

### 核心定位

pandas 是 Python 数据分析的**核心基础设施**。它提供两种主要数据结构：

- **DataFrame** — 带标签的二维表格（类似 R data.frame），数学建模中的数据容器
- **Series** — 带标签的一维数组，DataFrame 的列

### 数学建模关键能力

#### 数据读取（I/O）

| API | 用途 | 建模场景 |
|-----|------|----------|
| `pd.read_csv()` | CSV/文本文件 | 竞赛附件数据（最常见） |
| `pd.read_excel()` | Excel 文件 (.xlsx) | 多工作表附件数据 |
| `pd.read_json()` | JSON 数据 | API 数据、配置文件 |
| `pd.read_sql()` | 数据库查询 | 大型数据集 |

#### 数据查看与理解

| API | 用途 |
|-----|------|
| `df.head(n)` | 查看前 n 行 |
| `df.info()` | 列信息：类型、非空数 |
| `df.describe()` | 描述性统计（均值、标准差、分位数） |
| `df.shape` | 行列数 |
| `df.dtypes` | 每列数据类型 |
| `df.columns` | 列名列表 |

#### 数据选择与过滤

| API | 用途 |
|-----|------|
| `df.loc[row_label, col_label]` | 基于标签索引 |
| `df.iloc[row_pos, col_pos]` | 基于位置索引 |
| `df.query('A > 0 and B < 10')` | 条件查询过滤 |
| `df[df['col'] > threshold]` | 布尔索引筛选 |

#### 数据合并

| API | 用途 | 建模场景 |
|-----|------|----------|
| `pd.merge(df1, df2, on='key')` | SQL 风格连接 | 多表关联 |
| `pd.concat([df1, df2])` | 行/列拼接 | 数据集合并 |
| `df.join(other)` | 基于索引连接 | 时间序列对齐 |

#### 分组聚合

| API | 用途 | 建模场景 |
|-----|------|----------|
| `df.groupby('category').mean()` | 分组统计 | 分类汇总 |
| `df.groupby('category').agg(['mean','std','count'])` | 多重聚合 | 分组描述 |
| `df.pivot_table(values, index, columns, aggfunc)` | 透视表 | 多维汇总 |

#### 缺失值处理

| API | 用途 |
|-----|------|
| `df.isnull().sum()` | 每列缺失计数 |
| `df.isnull().sum() / len(df)` | 缺失比例 |
| `df.dropna()` / `df.dropna(subset=['col'])` | 删除含缺失的行 |
| `df.fillna(value)` / `df.fillna(method='ffill')` | 填充缺失值 |
| `df.interpolate()` | 插值填充 |

#### 时间序列

| API | 用途 | 建模场景 |
|-----|------|----------|
| `pd.to_datetime(df['date'])` | 转换为时间类型 | 日期解析 |
| `df.set_index('date')` | 设置时间索引 | 时间序列基础 |
| `df.resample('M').mean()` | 重采样（降/升频） | 月/季度汇总 |
| `df.rolling(window=7).mean()` | 滑动窗口 | 移动平均、平滑 |
| `df.shift(1)` | 时间平移 | 滞后特征 |

#### 数据清洗

| 操作 | 方法 |
|------|------|
| 重命名列 | `df.rename(columns={'old':'new'})` |
| 删除列 | `df.drop(['col'], axis=1)` |
| 去重 | `df.drop_duplicates()` |
| 类型转换 | `df['col'].astype('float64')` |
| 排序 | `df.sort_values('col')` |
| 应用函数 | `df['col'].apply(func)` |

### 推荐长期保留

✅ **是。** 数学建模数据处理的不二之选。

---

## 二、补充仓库：fg-data-profiling（原 ydata-profiling）

| 属性 | 内容 |
|------|------|
| **名称** | fg-data-profiling |
| **GitHub 地址** | https://github.com/Data-Centric-AI-Community/fg-data-profiling |
| **Stars** | ~13,700 |
| **维护状态** | ✅ 活跃（最近提交 2026-04） |
| **许可证** | MIT |

### 核心能力

一行代码生成完整数据质量报告：类型推断、缺失分析、分布可视化、相关性分析、数据质量警报。

```python
from data_profiling import ProfileReport
profile = ProfileReport(df, title="Data Quality Report")
profile.to_file("report.html")
```

### 数学建模价值 ⭐⭐⭐⭐

自动化 EDA 的第一步：快速了解数据结构、发现质量问题、生成报告附件。建模比赛中可大幅加速"理解数据"阶段。

### 是否纳入 Skill

✅ **工具推荐。** 纳入 `data_quality/` 文档，作为自动质量检测推荐工具。

---

## 三、补充仓库：ResidentMario/missingno

| 属性 | 内容 |
|------|------|
| **名称** | missingno |
| **GitHub 地址** | https://github.com/ResidentMario/missingno |
| **Stars** | ~4,000 |
| **维护状态** | ⚠ 维护模式（最后提交 2023-02） |
| **许可证** | MIT |

### 核心能力

缺失值可视化的专用工具：

- `msno.matrix(df)` — 缺失矩阵图（快速定位缺失模式）
- `msno.bar(df)` — 各列缺失比例柱状图
- `msno.heatmap(df)` — 缺失相关性热图（A列缺失是否与B列缺失相关）
- `msno.dendrogram(df)` — 缺失聚类树状图（发现变量缺失群组）

### 数学建模价值 ⭐⭐⭐

快速可视化缺失模式，帮助选择 drop/fill 策略。特别是在有大量变量的数据集中，missingno 可视化比纯数字表格更直观。

### 是否纳入 Skill

✅ **工具推荐。** 纳入 `data_quality/missing_value.md`。

---

## 四、补充仓库：plotly/plotly.py

| 属性 | 内容 |
|------|------|
| **名称** | plotly.py |
| **GitHub 地址** | https://github.com/plotly/plotly.py |
| **Stars** | ~16,700 |
| **维护状态** | ✅ 极活跃 |
| **许可证** | MIT |

### 核心能力（数据探索相关）

- `plotly.express` — 一行代码生成交互式图表（散点图、折线图、直方图、箱线图、热力图等）
- 交互式缩放/悬停信息 — 比 matplotlib 更适合探索阶段
- `plotly.graph_objects` — 自定义图表

### 数学建模价值 ⭐⭐⭐

EDA 阶段的交互式可视化。本 Skill 只提取其数据探索部分，不涉及复杂图表定制。

### 是否纳入 Skill

✅ **接口推荐。** 在探索分析步骤中推荐，但不深度收录。

---

## 五、补充仓库：jupyter/notebook

| 属性 | 内容 |
|------|------|
| **名称** | Jupyter Notebook |
| **GitHub 地址** | https://github.com/jupyter/notebook |
| **Stars** | ~13,300 |
| **维护状态** | ✅ 极活跃 |

### 数学建模价值 ⭐⭐⭐

Data processing 阶段的标准实验环境。Notebook 的分步执行 + 中间结果可视化，天然适合"数据检查→清洗→探索"的迭代流程。

### 是否纳入 Skill

✅ **环境推荐。** 作为建模工作流的标准工具。

---

## 六、采用仓库列表（最终汇总）

| # | 仓库 | Stars | 角色 | Skill 中处理方式 |
|---|------|-------|------|-----------------|
| 1 | pandas-dev/pandas | ~49.3k | 数据处理核心 | 完整知识提炼 + 案例 |
| 2 | fg-data-profiling | ~13.7k | 自动数据质量报告 | 工具推荐（data_quality/） |
| 3 | missingno | ~4.0k | 缺失值可视化 | 工具推荐（data_quality/） |
| 4 | plotly.py | ~16.7k | EDA 交互可视化 | 接口推荐 |
| 5 | jupyter/notebook | ~13.3k | 实验环境 | 工作流中工具推荐 |

---

## 七、Stars 和活跃度总结

```
仓库                   Stars    活跃度    关键性
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
pandas                 49.3k    每日提交   ⭐⭐⭐⭐⭐  核心
fg-data-profiling      13.7k    月级提交   ⭐⭐⭐⭐   质量报告
plotly.py              16.7k    每日提交   ⭐⭐⭐     EDA 可视化
missingno              4.0k     维护模式   ⭐⭐⭐     缺失可视化
jupyter/notebook       13.3k    每日提交   ⭐⭐⭐     实验环境
```
