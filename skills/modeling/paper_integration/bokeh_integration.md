# Bokeh 参考 — 数模交互式 Web 可视化

> 来源：bokeh/bokeh（GitHub ~20.4k stars, BSD-3）
> 蒸馏自官方文档 + 社区最佳实践
> 服务于 S6 交互式答辩图表（Plotly 替代）

---

## 一、定位

```
Plotly → 全功能 API，图表美观，但输出依赖 plotly.js（~3MB）
Bokeh  → 独立 HTML 文件（无外部依赖），更轻量，适合自定义仪表盘
```

**核心价值**：产出独立自包含的 HTML 文件，发给评委直接双击浏览器打开。

```
安装：pip install bokeh
```

---

## 二、核心 API（高级接口 bokeh.plotting）

```python
from bokeh.plotting import figure, show, output_file
from bokeh.models import ColumnDataSource, HoverTool
import numpy as np

# 1. 创建画布
p = figure(title='散点图', x_axis_label='X', y_axis_label='Y',
           width=800, height=500, tools='pan,wheel_zoom,box_zoom,reset,save')

# 2. 绘图
p.scatter(x, y, size=8, color='steelblue', alpha=0.6, legend_label='数据点')
p.line(x_line, y_line, line_width=2, color='red', legend_label='趋势线')

# 3. 输出
output_file('plot.html')  # ⭐ 独立 HTML
show(p)
```

---

## 三、数模常用图表

```python
# 散点图
p.scatter(x, y, size=8, color='color_col', source=source)

# 折线图
p.line(x, y, line_width=2, color='steelblue')

# 柱状图
from bokeh.plotting import figure
p.vbar(x=labels, top=values, width=0.5)

# 直方图
from bokeh.plotting import figure
hist, edges = np.histogram(data, bins=30)
p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:])

# 多线图
p.multi_line(xs=[x1, x2], ys=[y1, y2], color=['blue', 'red'])
```

---

## 四、交互与悬停提示

```python
from bokeh.models import ColumnDataSource, HoverTool

# 数据源
source = ColumnDataSource(data=dict(x=x, y=y, name=names, value=values))

# 悬停提示
hover = HoverTool(tooltips=[
    ('名称', '@name'),
    ('X值', '@x{0.00}'),
    ('Y值', '@y{0.00}'),
])
p.add_tools(hover)
```

---

## 五、Bokeh vs Plotly 选择

| 场景 | 推荐 |
|------|------|
| 快速出图，代码简洁 | Plotly Express |
| 独立 HTML 无外部依赖 | **Bokeh** |
| 3D 图 | Plotly |
| 仪表盘/大屏展示 | Bokeh + Bokeh Server |
| 答辩演示（缩放+悬停） | 两者均可 |
| 论文导出 PNG/PDF | Plotly（kaleido 更成熟） |

---

## 六、导出

```python
from bokeh.io import export_png
# 需先安装 selenium + geckodriver/chromedriver
export_png(p, filename='plot.png')
```

---

## 七、常见坑

| 坑 | 解决 |
|----|------|
| 导出 PNG 需额外依赖 | `pip install selenium` + Chrome |
| ColumnDataSource 数据长度不一致 | 所有列必须等长 |
| 独立 HTML 含 CDN 引用 | 设 `mode='inline'` 完全自包含 |
