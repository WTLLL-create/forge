# NumPy 知识提炼：数学建模核心用法

> 来源：https://github.com/numpy/numpy （v2.5.1, 32.4k stars）
>
> 提炼原则：不复制源码，只提取建模场景中的语义、模式和最佳实践

---

## 一、ndarray — 数学建模的数据基座

### 1.1 核心语义

ndarray 是**同构多维数组** — 所有元素类型相同，内存连续存储。这是数学建模中矩阵、向量、张量的自然表示。

### 1.2 创建方式（建模常用）

```python
import numpy as np

# 从 Python 列表创建
A = np.array([[1, 2], [3, 4]])        # 2x2 矩阵

# 特殊矩阵
I = np.eye(3)                          # 单位矩阵（线性系统）
Z = np.zeros((m, n))                   # 零矩阵（初始化变量矩阵）
O = np.ones((m, n))                    # 全 1 矩阵（权重初始化）

# 序列生成（建模中最常用）
x = np.linspace(0, 10, 100)           # 等间距点（绘图、积分采样）
t = np.arange(0, 100, 0.1)            # 时间序列（动态模拟）

# 随机矩阵
rng = np.random.default_rng(42)
noise = rng.normal(0, 0.1, size=100)  # 测量噪声模拟
samples = rng.uniform(0, 1, (1000, 5))  # Monte Carlo 采样
```

### 1.3 矩阵运算（建模核心操作）

| 运算 | 写法 | 用途 |
|------|------|------|
| 矩阵乘法 | `A @ B` 或 `np.dot(A, B)` | 线性变换、网络传播 |
| 转置 | `A.T` | 矩阵操作 |
| 逐元素乘法 | `A * B` | Hadamard 积 |
| 矩阵求逆 | `np.linalg.inv(A)` | 线性系统求解 |
| 范数 | `np.linalg.norm(A)` | 误差度量、正则化 |

---

## 二、Linear Algebra — `numpy.linalg`

### 2.1 线性方程组求解（Ax = b）

```python
# 标准求解（方阵）
x = np.linalg.solve(A, b)

# 最小二乘（超定方程，m > n）
x, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
```

建模场景：参数估计、平衡方程、电路网络

### 2.2 特征值分解

```python
# 一般矩阵
eigenvalues, eigenvectors = np.linalg.eig(A)

# 对称/Hermitian 矩阵（更快、更稳定、返回实数）
eigenvalues, eigenvectors = np.linalg.eigh(A)
```

建模场景：PCA、稳定性分析、振动模态

### 2.3 奇异值分解（SVD）

```python
U, S, Vt = np.linalg.svd(A, full_matrices=False)
# A ≈ U @ np.diag(S) @ Vt
```

建模场景：降维、矩阵近似、伪逆、条件数估计

### 2.4 行列式与秩

```python
det = np.linalg.det(A)        # 行列式（判断可逆性）
rank = np.linalg.matrix_rank(A)  # 矩阵秩
cond = np.linalg.cond(A)       # 条件数（判断病态程度）
```

---

## 三、Vectorization — 告别 for 循环

### 3.1 核心原则

> 用数组级别的运算代替逐元素的 Python for 循环。

```python
# ❌ Python 循环（慢）
result = []
for x in data:
    result.append(x ** 2 + 3 * x + 1)

# ✅ 向量化（快 10-100x）
result = data ** 2 + 3 * data + 1
```

### 3.2 Broadcasting 规则

不同形状的数组运算时，NumPy 自动"拉伸"小数组：

```python
# 矩阵每一列减去该列均值
X_centered = X - X.mean(axis=0)   # X: (m, n), mean: (n,) → broadcasting

# 每个数据点乘以不同权重
weighted = data * weights          # data: (100, 3), weights: (3,) → broadcasting
```

建模场景：数据标准化、加权求和、批量计算损失函数

---

## 四、Random — 随机数生成

### 4.1 新 API（Generator，推荐）

```python
rng = np.random.default_rng(seed=42)  # 设置种子保证可复现

# 常用分布
rng.normal(mu, sigma, size)     # 正态分布（测量噪声）
rng.uniform(low, high, size)     # 均匀分布（先验分布）
rng.exponential(scale, size)     # 指数分布（等待时间）
rng.poisson(lam, size)           # 泊松分布（事件计数）
rng.choice(a, size, p=probs)    # 离散抽样（Bootstrap）
```

### 4.2 建模场景

- **Monte Carlo 模拟**：大量随机采样求期望/概率
- **Bootstrap**：有放回抽样估计置信区间
- **参数摄动**：在最优解附近随机采样评估稳健性

---

## 五、常用数学函数

### 5.1 逐元素运算

```python
np.exp(x)     # e^x（指数增长/衰减）
np.log(x)     # ln(x)（对数变换、熵）
np.sqrt(x)    # √x
np.abs(x)     # |x|（误差、约束惩罚）
np.sin/cos    # 三角函数（周期性建模）
np.clip(x, a, b)  # 截断到 [a, b]（约束处理）
```

### 5.2 聚合运算

```python
np.sum(x, axis=0)    # 按列求和
np.mean(x, axis=0)   # 均值
np.std(x, axis=0)    # 标准差
np.max(x)            # 最大值
np.argmax(x)         # 最大值位置（最优解索引）
np.cumsum(x)         # 累积和（累计量）
```

---

## 六、建模最佳实践

1. **可复现性**：永远用 `default_rng(seed)` 而非旧 `RandomState`
2. **内存效率**：大数组用 `np.float32` 替代默认的 `float64` 节省一半内存
3. **避免复制**：用 `A.view()` 或切片视图替代不必要的数据拷贝
4. **向量化优先**：能用数组运算绝不用 for 循环
5. **数值稳定性**：`np.linalg.solve(A, b)` 优于 `np.linalg.inv(A) @ b`（更快更稳定）
