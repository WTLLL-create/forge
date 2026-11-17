# NumPy 完整参考 — 数模计算基础

> 来源：numpy/numpy（GitHub ~32k stars, BSD-3-Clause）
> 蒸馏自官方 Quickstart 完整文档
> 服务于 S3/S4 所有计算的底层数组操作

---

## 一、定位

```
NumPy → 所有 Python 科学计算的基石
Pandas   → 基于 NumPy 的表格数据
SciPy    → 基于 NumPy 的高级数学算法
sklearn  → 基于 NumPy 的机器学习
```

数模中 **一切数据最终都是 NumPy 数组**。`df.to_numpy()` → NumPy → 喂给求解器。

```
安装：pip install numpy
```

---

## 二、数组创建

```python
import numpy as np

# 从列表
np.array([1, 2, 3])                    # [1 2 3]
np.array([[1, 2], [3, 4]])             # 2×2 矩阵

# 常量数组
np.zeros((3, 4))                       # 3×4 全零
np.ones((2, 3))                        # 2×3 全一
np.eye(3)                              # 3×3 单位矩阵

# 序列
np.arange(0, 10, 2)                    # [0 2 4 6 8]
np.linspace(0, 1, 11)                  # 0到1，等距11个点（数模最常用）

# 随机数组
rng = np.random.default_rng(42)        # 新版生成器（推荐）
rng.random((3, 4))                     # [0,1) 均匀分布
rng.normal(0, 1, (100,))              # 正态分布（100个样本）
rng.integers(0, 10, size=(3, 4))      # 整数随机
```

---

## 三、数组属性

```python
a = np.arange(15).reshape(3, 5)

a.shape    # (3, 5)   — 形状
a.ndim     # 2        — 维度数
a.size     # 15       — 元素总数
a.dtype    # int64    — 数据类型
a.T        # 转置
```

---

## 四、索引与切片

```python
a = np.arange(12).reshape(3, 4)

# 基础索引
a[0, 0]          # 第一个元素  → 0
a[0:2, 1:3]      # 切片 → [[1 2], [5 6]]
a[:, 0]           # 第一列    → [0 4 8]
a[..., -1]        # 最后一列  → [3 7 11]

# 布尔索引（最常用于筛选）
mask = a > 5
a[mask]           # [6 7 8 9 10 11]
a[a > 5] = 0      # 将 >5 的元素置零

# 花式索引
idx = [0, 2]
a[idx]            # 第0行和第2行
```

---

## 五、形状操作

```python
a.reshape(4, 3)       # 改变形状（不复制数据）
a.reshape(-1, 2)      # -1 自动推导
a.ravel()             # 展平
a.flatten()           # 展平（返回副本）

# 堆叠
np.vstack([a, b])     # 垂直堆叠
np.hstack([a, b])     # 水平堆叠
np.column_stack([x, y])  # 列堆叠（1D→2D）

# 拆分
np.hsplit(a, 3)       # 水平3等分
```

---

## 六、通用函数 (ufunc) — 逐元素运算

```python
x = np.array([0, 1, 2, 3])

# 数学
np.sin(x)          # 三角函数
np.cos(x)
np.exp(x)          # e^x
np.log(x + 1)      # ln(x+1)（防止 log(0)）
np.sqrt(x)         # √x

# 取整
np.floor(x)        # 向下取整
np.ceil(x)         # 向上取整
np.round(x, 2)     # 四舍五入保留2位

# 裁剪
np.clip(x, 0, 2)   # 限制范围 [0, 2]

# 绝对值
np.abs(x)
```

---

## 七、聚合统计

```python
a = np.random.randn(100)

# 全局
a.sum()            # 求和
a.mean()           # 均值
a.std()            # 标准差
a.var()            # 方差
a.min()            # 最小值
a.max()            # 最大值
np.median(a)       # 中位数

# 按轴（二维数组）
b = np.arange(12).reshape(3, 4)
b.sum(axis=0)      # 每列求和 → [12 15 18 21]
b.mean(axis=1)     # 每行均值 → [1.5 5.5 9.5]

# 位置
a.argmin()         # 最小值索引
a.argmax()         # 最大值索引

# 累计
b.cumsum(axis=1)   # 沿行的累计和

# 相关
np.corrcoef(x, y)  # 相关系数矩阵
np.cov(x, y)       # 协方差矩阵
```

---

## 八、线性代数

```python
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

# 矩阵乘法
A @ B                   # Python 3.5+（推荐）
A.dot(B)                # 等价

# 点积
np.dot(a, b)

# 方程组 Ax = b
x = np.linalg.solve(A, b)

# 求逆
np.linalg.inv(A)

# 特征值/特征向量
vals, vecs = np.linalg.eig(A)

# 奇异值分解
U, S, Vt = np.linalg.svd(A)

# 范数
np.linalg.norm(x, ord=2)  # L2 范数
```

---

## 九、广播 (Broadcasting) — 核心机制

不同形状数组运算时自动对齐维度：

```python
# 标量 × 数组
a = np.array([1, 2, 3])
a * 2              # [2 4 6]

# (3,) × (3,4) → (3,4)
a[:, np.newaxis] + np.zeros((3, 4))

# (1,3) × (3,1) → (3,3)
a[np.newaxis, :] + b[:, np.newaxis]
```

> 广播是替代 Python for 循环进行批量运算的关键机制

---

## 十、条件操作

```python
# where: if-else 的向量化版本
np.where(condition, x, y)       # True→x, False→y
np.where(a > 5)                 # 返回索引元组

# any / all
np.any(a > 0)                   # 是否有任意元素 >0
np.all(a > 0)                   # 是否所有元素 >0

# 副本 vs 视图
b = a.copy()                    # 深复制（安全）
b = a.view()                    # 浅复制
b = a[1:3]                      # 切片返回视图（!会改原数组）
```

---

## 十一、S3→S4 数据交接模板

```python
import numpy as np
import pandas as pd

# S3 输出 → NumPy 数组
df = pd.read_csv('data.csv')
X = df[feature_cols].to_numpy()  # (n_samples, n_features)
y = df[target_col].values         # (n_samples,)

# 确保无 NaN
assert not np.isnan(X).any()

# 标准化（手动）
X_norm = (X - X.mean(axis=0)) / X.std(axis=0)

# 喂给 S4 求解器
```

---

## 十二、数模高频操作速查

| 我��要做... | NumPy 操作 |
|------------|------------|
| 等间距采样 | `np.linspace(0, 10, 100)` |
| 正态随机数 | `rng.normal(0, 1, (100,))` |
| 筛选数据 | `a[a > threshold]` |
| 逐元素计算 | `np.exp(x)`, `np.log(x)` |
| 矩阵乘法 | `A @ B` |
| 解方程组 | `np.linalg.solve(A, b)` |
| 按列统计 | `a.mean(axis=0)` |
| 改变形状 | `a.reshape(2, -1)` |
| 条件替换 | `np.where(a > 0, a, 0)` |

---

## 十三、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| 切片改原数组 | 意外副作用 | `a[1:3].copy()` 深复制 |
| NaN 传播 | sum/mean 变 NaN | `np.nanmean()` 跳过 NaN |
| 类型转换 | 整数存浮点成整数 | `dtype=np.float64` |
| 广播形状不匹配 | ValueError | 用 `np.newaxis` 或 `reshape(-1, 1)` |
| arange 浮点步长 | 元素数不可靠 | 用 `linspace` 代替 |
| @ 和 * 混淆 | 矩阵乘法错了 | `A @ B`=矩阵乘, `A * B`=逐元素 |
