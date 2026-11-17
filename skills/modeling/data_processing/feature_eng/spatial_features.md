# Spatial Features — 空间特征工程

> 适用于有多个监测点/站点的场景。
> 核心思想: 邻近站点的信息包含预测目标的额外信号。

## 操作

```python
# 邻近站点加权平均 (距离越近权重越大)
df['O3_neighbor_mean'] = df.groupby('date').apply(
    lambda g: np.average(g['O3'], weights=1/(g['distance']+1))
)

# 邻近站点差值 (本地点-邻近点)
df['O3_local_minus_neighbor'] = df['O3'] - df['O3_neighbor_mean']

# 主导风向的上下游站点
df['upwind_O3'] = ...  # 上风向站点的浓度 (污染传输)
```

## 论文表达

"考虑到大气污染物的空间传输效应，引入邻近监测点作为协同预报因子。以距离倒数加权平均构造空间特征，捕捉区域污染传输对本地的影响。"
