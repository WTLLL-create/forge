# Mayavi 参考 — 数模 3D 高级可视化

> 来源：enthought/mayavi（GitHub ~1.4k stars, 多许可）
> 蒸馏自官方文档 + README
> 服务于 S6 论文 3D 图表

---

## 一、定位

```
Matplotlib 3D → 简单但粗糙（mplot3d 工具包）
Plotly 3D    → 交互式浏览器渲染
Mayavi        → 专业级 3D 科学可视化（VTK 引擎，GPU 加速）
```

**适合**：复杂 3D 曲面/体渲染/流场/张量可视化。数模中需要"看起来专业"的 3D 图时使用。

```
安装：pip install mayavi
# Windows 需额外：conda install -c conda-forge vtk
```

---

## 二、核心 API：mlab 模块

```python
import numpy as np
from mayavi import mlab

# mlab 提供 MATLAB 风格的简洁接口

# 3D 散点
x, y, z = np.random.randn(3, 100)
mlab.points3d(x, y, z, z, colormap='cool', scale_factor=0.3)

# 3D 曲线
t = np.linspace(0, 4 * np.pi, 100)
mlab.plot3d(np.sin(t), np.cos(t), t, t, tube_radius=0.1)

# 3D 曲面
x, y = np.mgrid[-3:3:100j, -3:3:100j]
z = np.sin(x) * np.cos(y)
mlab.surf(x, y, z, colormap='coolwarm')

# 3D 等高面（体渲染）
mlab.contour3d(x, y, z, scalar_field)

# 流线图
mlab.flow(x, y, z, u, v, w)

# 矢量场（箭头）
mlab.quiver3d(x, y, z, u, v, w)

# 显示
mlab.show()
```

---

## 三、数模常见场景

### 场景 1：优化结果 3D 展示

```python
# 展示两组目标 + 一个决策变量的三维 Pareto 关系
x, y, z = pareto_f1, pareto_f2, decision_var
mlab.points3d(x, y, z, z, colormap='viridis', scale_factor=0.05)
mlab.axes(xlabel='目标1', ylabel='目标2', zlabel='变量')
mlab.colorbar(title='变量值')
```

### 场景 2：物理场可视化

```python
# 温度场/压力场/浓度场 3D 渲染
mlab.contour3d(X, Y, Z, temperature_field, 
               contours=10, transparent=True, opacity=0.3)
mlab.surf(X, Y, surface_z, colormap='hot')
```

---

## 四、导出与保存

```python
mlab.savefig('3d_figure.png', size=(1200, 800))  # PNG
mlab.savefig('3d_figure.pdf')                      # PDF 矢量
```

---

## 五、注意事项

| 注意 | 说明 |
|------|------|
| **安装复杂** | Windows 需额外 VTK 依赖，conda 安装更稳妥 |
| **不适合大规模** | 数据量 >10万点可能卡顿 |
| **论文建议** | Mayavi 出基础图后可在 PS/AI 精修标注 |
| **替代方案** | 简单 3D 用 `matplotlib.mplot3d`，交互用 `plotly.express.scatter_3d` |
