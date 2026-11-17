# Matplotlib 完整参考 — 数模论文绘图

> 来源：matplotlib/matplotlib（GitHub ~23k stars, 自定义BSD）
> 蒸馏自官方 README、Pyplot教程、Axes API、savefig 文档
> 服务于 S6 (PAPER) 论文图表生成

---

## 一、两套 API：选哪个？

| API | 风格 | 何时用 |
|-----|------|--------|
| **pyplot** `plt.plot()` | MATLAB 风格，全局状态 | 快速探索、简单图表 |
| **Object-Oriented** `ax.plot()` | 显式 Axes 对象 | 多子图、论文组图、复杂布局（推荐） |

> **论文推荐 OO 风格**：`fig, ax = plt.subplots()` → 一切操作 `ax`

---

## 二、论文常用图表类型速查

### 2.1 折线图 (plot) — 趋势、预测对比

```python
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(x, y_true, 'b-', linewidth=1.5, label='真实值')
ax.plot(x, y_pred, 'r--', linewidth=1.5, label='预测值')
ax.set_xlabel('时间 (s)')
ax.set_ylabel('温度 (℃)')
ax.legend()
ax.grid(True, alpha=0.3)
```

### 2.2 散点图 (scatter) — 预测vs真实、聚类

```python
ax.scatter(y_test, y_pred, c='steelblue', alpha=0.5, s=15, edgecolors='none')
ax.plot([y_min, y_max], [y_min, y_max], 'r--', linewidth=1)  # 对角线
ax.set_xlabel('真实值')
ax.set_ylabel('预测值')
```

### 2.3 柱状图 (bar/barh) — 对比、权重

```python
ax.bar(labels, values, color='steelblue', width=0.6, edgecolor='white')
ax.set_ylabel('得分')
# 水平柱状图
ax.barh(labels, values, color='coral')
```

### 2.4 直方图 (hist) — 数据分布

```python
ax.hist(data, bins=30, density=True, alpha=0.7, color='steelblue', edgecolor='white')
ax.set_xlabel('值')
ax.set_ylabel('频率密度')
```

### 2.5 误差线 (errorbar) — 实验结果+不确定性

```python
ax.errorbar(x, y, yerr=y_std, fmt='o-', capsize=3, markersize=4, linewidth=1.5,
            color='steelblue', ecolor='gray', label='均值±标准差')
```

### 2.6 填充区域 (fill_between) — 置信区间

```python
ax.fill_between(x, y - std, y + std, alpha=0.2, color='steelblue', label='95% 置信区间')
ax.plot(x, y, 'b-', linewidth=1.5)
```

### 2.7 箱线图 (boxplot) — 分布对比

```python
ax.boxplot([group1, group2, group3], labels=['A', 'B', 'C'], patch_artist=True)
ax.set_ylabel('指标值')
```

### 2.8 饼图 (pie) — 构成比例

```python
ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
       colors=['steelblue', 'coral', 'gold', 'seagreen'])
```

### 2.9 等高线/热力图 (contourf / imshow) — 二维分布

```python
# 热力图
im = ax.imshow(matrix, cmap='coolwarm', aspect='auto', origin='lower')
plt.colorbar(im, ax=ax, label='值')

# 等高线
ax.contour(X, Y, Z, levels=10, colors='black', linewidths=0.5)
ax.contourf(X, Y, Z, levels=10, cmap='viridis')
```

### 2.10 帕累托前沿 (scatter + 连接线)

```python
# 多目标优化的 Pareto 前沿
ax.scatter(f1, f2, c='steelblue', s=20, label='可行解')
ax.plot(pareto_f1, pareto_f2, 'r-o', linewidth=1.5, markersize=5, label='Pareto前沿')
```

---

## 三、多子图布局（论文标配）

### 3.1 基础网格

```python
fig, axes = plt.subplots(2, 2, figsize=(10, 8))  # 2×2
axes[0, 0].plot(x, y1); axes[0, 0].set_title('(a) 工况1')
axes[0, 1].plot(x, y2); axes[0, 1].set_title('(b) 工况2')
axes[1, 0].scatter(x, y3); axes[1, 0].set_title('(c) 聚类结果')
axes[1, 1].hist(y4); axes[1, 1].set_title('(d) 分布')
plt.tight_layout(pad=2)
```

### 3.2 不规则布局 (GridSpec)

```python
from matplotlib.gridspec import GridSpec
fig = plt.figure(figsize=(12, 8))
gs = GridSpec(3, 3)
ax1 = fig.add_subplot(gs[0, :])    # 顶行全宽
ax2 = fig.add_subplot(gs[1, :2])   # 左侧
ax3 = fig.add_subplot(gs[1, 2])    # 右侧
ax4 = fig.add_subplot(gs[2, 0])
ax5 = fig.add_subplot(gs[2, 1:])   # 跨两列
```

---

## 四、保存为论文插图

```python
fig.savefig(
    'figure_name.png',       # 支持 .png .pdf .svg .eps
    dpi=300,                 # 分辨率（论文用300+）
    bbox_inches='tight',     # 自动裁剪白边
    pad_inches=0.1,          # 边距
    transparent=False,       # 白底（论文用）
    format='png'
)
```

### 格式选择指南

| 格式 | 特点 | 场景 |
|------|------|------|
| **PNG** | 位图，dpi 决定清晰度 | Word论文插图（最通用） |
| **PDF** | 矢量图，无损无限缩放 | LaTeX 论文 |
| **SVG** | 矢量图，可编辑 | 后期微调、网页 |
| **EPS** | 矢量图，传统格式 | 老派期刊投稿 |

---

## 五、样式与中文支持

### 5.1 中文字体（Windows 环境）

```python
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
```

### 5.2 预设样式

```python
plt.style.use('seaborn-v0_8-whitegrid')  # 论文推荐：干净、有网格
# 其他可选:
# 'seaborn-v0_8-darkgrid', 'ggplot', 'fivethirtyeight', 'classic'
# 查看全部: print(plt.style.available)
```

### 5.3 论文统一风格配置（实用模板）

```python
plt.rcParams.update({
    'figure.dpi': 150,              # 屏幕显示
    'savefig.dpi': 300,             # 保存分辨率
    'font.size': 11,               # 全局字号
    'axes.titlesize': 13,          # 标题字号
    'axes.labelsize': 12,          # 轴标签字号
    'legend.fontsize': 10,         # 图例字号
    'lines.linewidth': 1.5,        # 线宽
    'lines.markersize': 5,         # 标记大小
    'axes.grid': True,             # 显示网格
    'grid.alpha': 0.3,             # 网格透明度
})
```

---

## 六、数学表达式（LaTeX）

```python
ax.set_xlabel(r'$\Delta T$ (℃)')                    # 希腊字母
ax.set_ylabel(r'$R^2$')                              # 上标
ax.set_title(r'$\sum_{i=1}^{n} (y_i - \hat{y}_i)^2$')  # 求和
ax.text(0.5, 0.9, r'$\mu=%.2f,\ \sigma=%.2f$' % (mu, sigma), 
        transform=ax.transAxes)
```

---

## 七、颜色与视觉映射

```python
# 命名颜色
color='steelblue'  # 论文推荐：低饱和专业色

# RGB 元组
color=(0.2, 0.4, 0.6)

# 透明度
alpha=0.7

# Colormap（热力图/散点图映射）
cmap='coolwarm'     # 冷暖（最常用）
cmap='viridis'      # 感知均匀
cmap='RdYlBu'       # 红黄蓝
cmap='Blues'        # 单色渐变

# 论文推荐调色板
colors = ['#2878B5', '#9AC9DB', '#F8AC8C', '#C82423', '#FF8884']
```

---

## 八、常用标注与图例

```python
# 标注
ax.annotate('最优点', xy=(x_opt, y_opt), xytext=(x_opt+0.5, y_opt+0.5),
            arrowprops=dict(arrowstyle='->', color='red'), fontsize=10)

# 文本框
ax.text(0.05, 0.95, f'R² = {r2:.4f}\nRMSE = {rmse:.2f}',
        transform=ax.transAxes, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 图例
ax.legend(loc='best', frameon=True, fancybox=True, framealpha=0.8)
# loc: 'best' 'upper right' 'lower left' 'center' 等

# 双Y轴
ax2 = ax.twinx()
ax2.plot(x, y2, 'r-', label='右轴数据')
ax2.set_ylabel('右轴标签')
```

---

## 九、数模高频图表模板

### 模板 1：预测 vs 真实对比图

```python
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# 左：折线对比
ax1.plot(x, y_true, 'b-', lw=1.5, label='真实')
ax1.plot(x, y_pred, 'r--', lw=1.5, label='预测')
ax1.legend()
ax1.set_title('(a) 预测值对比')

# 右：散点 + 对角线
ax2.scatter(y_true, y_pred, alpha=0.5, s=15)
ax2.plot([y_min, y_max], [y_min, y_max], 'r--', lw=1)
ax2.set_xlabel('真实值'); ax2.set_ylabel('预测值')
ax2.set_title('(b) 预测精度评估')

plt.tight_layout()
plt.savefig('prediction_compare.png', dpi=300, bbox_inches='tight')
```

### 模板 2：特征重要性柱状图

```python
fig, ax = plt.subplots(figsize=(8, 5))
idx = np.argsort(importance)
ax.barh(range(len(idx)), importance[idx], color='steelblue')
ax.set_yticks(range(len(idx)))
ax.set_yticklabels([feature_names[i] for i in idx])
ax.set_xlabel('特征重要性')
ax.set_title('随机森林特征重要性排序')
```

### 模板 3：聚类结果可视化

```python
fig, ax = plt.subplots(figsize=(8, 6))
for i in range(n_clusters):
    mask = (labels == i)
    ax.scatter(X[mask, 0], X[mask, 1], s=15, alpha=0.6, label=f'簇{i+1}')
ax.scatter(centers[:, 0], centers[:, 1], c='red', s=100, marker='X',
           edgecolors='black', label='聚类中心')
ax.legend()
ax.set_xlabel('特征1'); ax.set_ylabel('特征2')
```

### 模板 4：收敛曲线

```python
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(history, 'b-', lw=1, alpha=0.7)
ax.plot(np.minimum.accumulate(history), 'r-', lw=2, label='历史最优')
ax.set_xlabel('迭代次数'); ax.set_ylabel('目标函数值')
ax.legend()
ax.grid(True, alpha=0.3)
```

---

## 十、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| 中文显示方框 | 论文标题□□□ | 设 `rcParams['font.sans-serif']` |
| 负号显示问题 | 轴标签变乱码 | `rcParams['axes.unicode_minus'] = False` |
| 保存后空白 | 图片一片白 | `savefig` 要在 `plt.show()` 之前 |
| 子图重叠 | 标签压一起 | 调用 `plt.tight_layout()` |
| dpi 过低 | 放大模糊 | 论文用 `dpi=300` |
| legend 不显示 | 图例为空 | 检查 plot 时是否传了 `label=` |
| 颜色不够区分 | 多线混一起 | 用 Colormap 或循环颜色列表 |
