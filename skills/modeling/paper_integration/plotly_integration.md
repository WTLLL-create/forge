# Plotly 完整参考 — 数模交互式图表

> 来源：plotly/plotly.py（GitHub ~18.2k stars, MIT）
> 蒸馏自官方 README + Plotly Express API + 静态导出文档
> 服务于 S6 论文交互图表 + 答辩展示

---

## 一、Plotly 定位

```
Matplotlib → 静态图，论文插图主力
Seaborn    → 统计图，一键美观
Plotly     → 交互图，缩放/悬停/导出HTML/答辩展示
```

- 基于 plotly.js，浏览器渲染
- 两张 API：**Plotly Express**（高层，类似 Seaborn）和 **graph_objects**（底层，类似 matplotlib OO）
- 输出：HTML（答辩/网页）、PNG/PDF/SVG（论文插图）、Jupyter 内嵌

---

## 二、Plotly Express — 数模最常用 API

```python
import plotly.express as px
# 所有函数返回 plotly.graph_objects.Figure，天然交互
```

### 2.1 折线图 (px.line) — 趋势、预测序列

```python
fig = px.line(df, x='时间', y='浓度', color='方法',
              line_shape='spline', markers=True,
              title='排放浓度随时间变化')
fig.show()
```

### 2.2 散点图 (px.scatter) — 聚类、相关性

```python
fig = px.scatter(df, x='温度', y='排放', color='工况',
                 size='功率', hover_name='时间',
                 title='工况散点分布', trendline='ols')
```

### 2.3 柱状图 (px.bar) — 对比

```python
fig = px.bar(df, x='算法', y='RMSE', color='数据集',
             barmode='group', title='不同算法 RMSE 对比')
```

### 2.4 箱线图 (px.box) — 分布对比

```python
fig = px.box(df, x='方法', y='误差', color='数据集', points='outliers',
             title='预测误差分布')
```

### 2.5 直方图 (px.histogram)

```python
fig = px.histogram(df, x='值', color='分组', marginal='rug',
                   nbins=30, title='数据分布')
```

### 2.6 热力图 (px.imshow / px.density_heatmap)

```python
# 相关性矩阵
fig = px.imshow(corr_matrix, text_auto='.2f',
                color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                title='特征相关性矩阵')

# 二维密度热力图
fig = px.density_heatmap(df, x='x', y='y', marginal_x='histogram',
                         marginal_y='histogram')
```

### 2.7 散点矩阵 (px.scatter_matrix) — 多变量探索

```python
fig = px.scatter_matrix(df, dimensions=['x1','x2','x3','x4'],
                        color='分类', title='多维特征散点矩阵')
```

### 2.8 3D 散点 (px.scatter_3d)

```python
fig = px.scatter_3d(df, x='x', y='y', z='z', color='cluster',
                    title='三维聚类结果')
```

### 2.9 小提琴图 (px.violin)

```python
fig = px.violin(df, y='得分', x='方法', color='方法',
                box=True, points='all', title='得分分布')
```

---

## 三、静态导出 — 用于论文插图

```bash
pip install kaleido
```

```python
# PNG（论文用）
fig.write_image('figure.png', width=1200, height=800, scale=2)

# PDF（LaTeX用，矢量图）
fig.write_image('figure.pdf', width=1200, height=800)

# SVG（可编辑矢量图）
fig.write_image('figure.svg', width=1200, height=800)

# 全局默认
import plotly.io as pio
pio.defaults.default_width = 1200
pio.defaults.default_height = 800
pio.defaults.default_scale = 2
pio.defaults.default_format = 'png'
```

---

## 四、更新布局 — 论文风格化

```python
fig.update_layout(
    title='图标题',
    title_x=0.5,          # 居中标题
    xaxis_title='X轴标签',
    yaxis_title='Y轴标签',
    font=dict(family='Arial', size=12),
    plot_bgcolor='white',  # 白色背景
    paper_bgcolor='white',
    width=800, height=500,
    margin=dict(l=60, r=30, t=50, b=50),
    legend=dict(x=0.02, y=0.98),
)

# 坐标轴
fig.update_xaxes(gridcolor='lightgray', showline=True, linewidth=1, linecolor='black')
fig.update_yaxes(gridcolor='lightgray', showline=True, linewidth=1, linecolor='black')
```

---

## 五、数模答辩利器

### 5.1 导出为独立 HTML（答辩展示）

```python
fig.write_html('model_result.html')
# 双击即可浏览器打开，支持缩放、悬停、下载为PNG
```

### 5.2 动画时间序列

```python
fig = px.scatter(df, x='x', y='y', animation_frame='time',
                 color='group', size='value',
                 range_x=[x_min, x_max], range_y=[y_min, y_max])
```

### 5.3 双Y轴

```python
from plotly.subplots import make_subplots
import plotly.graph_objects as go

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=x, y=y1, name='排放浓度'), secondary_y=False)
fig.add_trace(go.Scatter(x=x, y=y2, name='功率'), secondary_y=True)
fig.update_yaxes(title_text='排放 (mg/Nm³)', secondary_y=False)
fig.update_yaxes(title_text='功率 (kW)', secondary_y=True)
```

---

## 六、与 JupyterLab 集成

```python
# JupyterLab 中直接渲染交互图
fig.show()
# 或设置默认渲染器
import plotly.io as pio
pio.renderers.default = 'notebook'  # JupyterLab 中
# pio.renderers.default = 'browser'  # 浏览器中打开
```

---

## 七、色阶速查

```python
# 连续色阶
px.colors.sequential.Viridis
px.colors.sequential.Plasma
px.colors.sequential.Blues

# 发散色阶
px.colors.diverging.RdBu
px.colors.diverging.Picnic

# 定性色阶
px.colors.qualitative.Plotly   # 默认10色
px.colors.qualitative.Set2
px.colors.qualitative.Pastel
```

---

## 八、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| 静态导出失败 | `ValueError` | `pip install kaleido`（需 Chrome） |
| HTML 太大 | 文件上百 MB | 用小数据集，或降采样后再画 |
| JupyterLab 不显示 | 空白输出 | `pio.renderers.default = 'notebook'` |
| 论文插图模糊 | 导出 PNG 不清晰 | 设 `scale=2` 或 `scale=3` |
| 中文乱码 | 标题方框 | 用英文标签，或在 layout 中设 `font=dict(family='SimHei')` |
| scatter_3d 卡顿 | 数据太大 | 降采样到 < 5000 点 |

---

## 九、何时用 Plotly vs Matplotlib

| 场景 | 用 |
|------|-----|
| 论文最终插图（.png/.pdf） | Matplotlib（更轻量、更可控） |
| 统计分析图（箱线、热力） | Seaborn |
| 答辩演示（缩放、悬停） | **Plotly** |
| 需要3D图交互旋转 | **Plotly** |
| 导出为独立HTML报告 | **Plotly** |
| 多子图复杂排版 | Matplotlib（更灵活） |
