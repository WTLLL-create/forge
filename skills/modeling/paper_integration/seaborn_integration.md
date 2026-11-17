# Seaborn 完整参考 — 数模统计图表

> 来源：mwaskom/seaborn（GitHub ~13.7k stars, BSD-3-Clause）
> 蒸馏自官方 README + 函数概览教程 + API 文档
> 服务于 S6 (PAPER) 统计可视化

---

## 一、Seaborn 定位

```
Matplotlib → 底层画布，控制一切
Seaborn   → 高层封装，一行出图（基于 Matplotlib）
          → 默认配色美观、自动聚合统计量
          → 天然支持 DataFrame 字段名作为输入
          → 论文"统计图形"的首选
```

---

## 二、API 分层：图级 vs 轴级

| 图级 (figure-level) | 轴级 (axes-level) | 何时用 |
|:---|:---|------|
| `relplot()` | `scatterplot()`, `lineplot()` | 关系图 |
| `displot()` | `histplot()`, `kdeplot()`, `ecdfplot()` | 分布图 |
| `catplot()` | `boxplot()`, `violinplot()`, `barplot()`, `stripplot()`, `swarmplot()` | 分类图 |
| `lmplot()` | `regplot()` | 回归图 |
| — | `heatmap()`, `clustermap()` | 矩阵图 |

**核心区别**：
- 图级函数 → 返回 `FacetGrid`，支持 `col`/`row` 分面
- 轴级函数 → 返回 `matplotlib.axes.Axes`，可嵌入 `ax=` 到已有子图中

> **数模建议**：一个子图用轴级，多个分组子图用图级。

---

## 三、关系图 — 散点/折线

### scatterplot — 多维散点

```python
import seaborn as sns

# hue 自动着色 + 图例
sns.scatterplot(data=df, x='温度', y='排放浓度', hue='工况', 
                size='功率', sizes=(10, 200), palette='deep', alpha=0.7)
```

### lineplot — 趋势线（带置信区间）

```python
# 自动计算均值 + 95% CI
sns.lineplot(data=df, x='时间', y='浓度', hue='方法',
             ci='sd', estimator='mean', marker='o')
# ci: 置信区间 ('sd'/'boot'/None)
```

### relplot — 分面关系图

```python
# 按工况分面，一行一个子图
sns.relplot(data=df, x='x', y='y', hue='group',
            col='strategy', kind='scatter')
```

---

## 四、分布图 — 直方图/KDE/箱线

### histplot — 直方图

```python
sns.histplot(data=df, x='值', bins=30, kde=True, 
             hue='分组', element='step', alpha=0.5)
```

### kdeplot — 核密度估计

```python
sns.kdeplot(data=df, x='值', hue='分组', fill=True, alpha=0.3)
```

### boxplot — 箱线图（最常用）

```python
sns.boxplot(data=df, x='组别', y='得分', hue='方法',
            palette='Set2', width=0.6)
```

### violinplot — 小提琴图（展示分布形状）

```python
sns.violinplot(data=df, x='组别', y='得分', hue='方法',
               split=False, inner='quartile', palette='muted')
```

### displot — 分面分布图

```python
sns.displot(data=df, x='flipper_length_mm', hue='species', 
            col='species', kind='kde', fill=True)
```

---

## 五、热力图 — 相关性矩阵

```python
# 相关性热力图（论文必备）
corr = df.corr()
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm',
            center=0, square=True, linewidths=0.5,
            cbar_kws={'shrink': 0.8}, vmin=-1, vmax=1)
```

- `annot=True` — 显示数值
- `fmt='.2f'` — 保留2位小数
- `center=0` — 0 为白色中心
- `cmap='coolwarm'` — 红蓝渐变

---

## 六、回归图 — 拟合直线

```python
# 散点 + 回归直线 + 置信区间
sns.regplot(data=df, x='x', y='y', ci=95, 
            scatter_kws={'alpha': 0.5, 's': 10},
            line_kws={'color': 'red', 'linewidth': 1.5})
```

### lmplot — 分面回归

```python
sns.lmplot(data=df, x='x', y='y', col='group',
           ci=None, height=4, aspect=1)
```

---

## 七、pairplot — 全景矩阵图（数模利器）

```python
# 所有数值列两两散点图 + 对角线直方图
sns.pairplot(df, hue='分类标签', diag_kind='kde',
             corner=True,  # 只显示下三角
             palette='Set2')
```

---

## 八、样式控制

### 全局主题

```python
sns.set_theme(style='whitegrid', font='SimHei', font_scale=1.2)
# style: 'darkgrid' 'whitegrid' 'dark' 'white' 'ticks'
```

### 调色板

```python
sns.color_palette('deep')       # 默认10色
sns.color_palette('husl', 8)    # 均匀色调
sns.color_palette('Set2')       # 柔色8色
sns.color_palette('coolwarm', as_cmap=True)  # 连续色
sns.color_palette('Blues')      # 单色渐变
```

---

## 九、论文高频图表模板

### 模�� 1：多变量相关性热力图

```python
fig, ax = plt.subplots(figsize=(10, 8))
corr = df[cols].corr()
mask = np.triu(np.ones_like(corr, dtype=bool))  # 上三角掩码
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f',
            cmap='RdBu_r', center=0, square=True,
            linewidths=0.5, ax=ax, cbar_kws={'shrink': 0.7})
ax.set_title('特征相关性矩阵', fontsize=14)
```

### 模板 2：对比箱线图

```python
fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(data=df, x='算法', y='RMSE', palette='Set2',
            width=0.5, linewidth=1.2, ax=ax)
sns.stripplot(data=df, x='算法', y='RMSE', color='black',
              size=3, alpha=0.3, ax=ax)  # 叠加原始点
ax.set_ylabel('RMSE')
ax.set_title('不同算法预测误差对比')
```

### 模板 3：分面分布对比

```python
g = sns.displot(data=df, x='误差', hue='工况', col='工况',
                kind='kde', fill=True, height=3, aspect=1.2,
                palette='Set2')
g.set_axis_labels('预测误差', '密度')
g.set_titles('工况 {col_name}')
```

### 模板 4：pairplot 快速探索

```python
# 从 DataFrame 到完整散点矩阵
g = sns.pairplot(df, vars=['x1', 'x2', 'x3', 'x4'], 
                 hue='类别', diag_kind='kde',
                 plot_kws={'alpha': 0.6, 's': 15})
```

---

## 十、与 matplotlib 混用（论文定稿必备）

```python
# Seaborn 出图 → Matplotlib 精修
fig, ax = plt.subplots(figsize=(8, 5))
sns.boxplot(data=df, x='组', y='值', ax=ax)

# Matplotlib 精修
ax.set_ylabel('得分', fontsize=12)
ax.set_xlabel('方法', fontsize=12)
ax.grid(True, axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)   # 去掉上边框
ax.spines['right'].set_visible(False) # 去掉右边框

fig.savefig('boxplot.png', dpi=300, bbox_inches='tight')
```

---

## 十一、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| 图级函数不支持 `ax=` | `AttributeError` | 图级用 `FacetGrid` 方法，轴级才能用 `ax=` |
| 中文不显示 | 标签显示方框 | `sns.set_theme(font='SimHei')` |
| heatmap 上三角多余 | 对称矩阵重复 | `mask=np.triu(...)` 掩码 |
| `palette` 颜色不够 | 多组颜色重复 | `sns.color_palette('husl', n=n_groups)` |
| regplot 拟合线没出来 | 数据有 NaN | 先 `df.dropna(subset=['x','y'])` |
