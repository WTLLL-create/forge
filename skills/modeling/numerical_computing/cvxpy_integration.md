# CVXPY 完整参考 — 数模凸优化建模

> 来源：cvxpy/cvxpy（GitHub ~6.2k stars, Apache-2.0）
> 蒸馏自官方 Tutorial + API 文档
> 服务于 S4 (SOLVING) 凸优化/二次规划/半定规划

---

## 一、CVXPY 定位

数学风格的优化建模语言。**写出数学公式，CVXPY 自动转化为求解器标准形式。**

```
安装：pip install cvxpy
核心理念：表达式接近数学公式 → 自动验证凸性(DCP) → 调用底层求解器
```

---

## 二、五种变量类型

```python
import cvxpy as cp
import numpy as np

# 标量
x = cp.Variable()

# 向量
x = cp.Variable(5)          # shape (5,)
x = cp.Variable((5, 1))     # 列向量

# 矩阵
A = cp.Variable((4, 7))     # shape (4, 7)

# 整数变量
z = cp.Variable(5, integer=True)

# 布尔变量
b = cp.Variable(5, boolean=True)
```

---

## 三、核心原子函数

```python
# 范数
cp.norm(x, 2)               # L2 范数
cp.norm(x, 1)               # L1 范数（LASSO 正则化）
cp.norm(x, 'inf')           # 无穷范数

# 平方
cp.sum_squares(A @ x - b)   # ||Ax-b||²（最小二乘）
cp.quad_form(x, Sigma)      # x^T Σ x（二次型）

# 其他常用
cp.sum(x)                    # 所有元素求和
cp.max(x)                    # 最大值
cp.abs(x)                    # 绝对值
cp.power(x, 2)               # x²
cp.sqrt(x)                   # √x
cp.log_sum_exp(x)            # log(∑e^xi)

# 矩阵
cp.trace(X)                  # 迹
cp.norm(X, 'nuc')           # 核范数
cp.matrix_frac(x, P)         # x^T P^{-1} x
```

---

## 四、基本模式

```python
import cvxpy as cp
import numpy as np

# 数据
A = np.random.randn(10, 5)
b = np.random.randn(10)

# 变量
x = cp.Variable(5)

# 目标
objective = cp.Minimize(cp.sum_squares(A @ x - b))

# 约束
constraints = [0 <= x, x <= 1, cp.sum(x) == 1]

# 求解
prob = cp.Problem(objective, constraints)
prob.solve()

# 结果
print(prob.status)          # 'optimal'
print(prob.value)           # 最优目标值
print(x.value)              # 最优解（numpy array）
```

---

## 五、参数化求解（敏感性分析）

```python
# 参数对象 — 改变值无需重建问题
gamma = cp.Parameter(nonneg=True)
gamma.value = 0.5

x = cp.Variable(5)
obj = cp.Minimize(cp.sum_squares(A @ x - b) + gamma * cp.norm(x, 1))
prob = cp.Problem(obj)

# 扫描不同 gamma 值（比反复建新问题快很多）
for val in [0.01, 0.1, 1, 10, 100]:
    gamma.value = val
    prob.solve()
    print(f'gamma={val:.2f}, |x|_1={cp.norm(x,1).value:.3f}')
```

---

## 六、经典数模模型模板

### LASSO 回归

```python
lambda_ = cp.Parameter(nonneg=True)
x = cp.Variable(n)
obj = cp.Minimize(cp.sum_squares(A @ x - b) + lambda_ * cp.norm(x, 1))
prob = cp.Problem(obj)
lambda_.value = 0.1
prob.solve()
```

### 投资组合优化（Markowitz）

```python
w = cp.Variable(n)
mu = np.array([...])         # 期望收益
Sigma = np.array([...])      # 协方差矩阵
gamma = cp.Parameter(nonneg=True)

obj = cp.Minimize(cp.quad_form(w, Sigma) - gamma * mu @ w)
constraints = [cp.sum(w) == 1, w >= 0]
prob = cp.Problem(obj, constraints)
```

### 支持向量机（SVM）

```python
w = cp.Variable(d)
b = cp.Variable()
C = cp.Parameter(nonneg=True)
xi = cp.Variable(m)

obj = cp.Minimize(cp.norm(w, 2)**2 + C * cp.sum(xi))
constraints = [xi >= 0,
               yi * (X @ w + b) >= 1 - xi]
```

### 线性规划（标准形式）

```python
x = cp.Variable(n)
obj = cp.Minimize(c @ x)
constraints = [A @ x <= b, x >= 0]
prob = cp.Problem(obj, constraints)
prob.solve()
```

---

## 七、状态值与含义

| 状态 | 含义 |
|------|------|
| `cp.OPTIMAL` | 达到最优解 |
| `cp.INFEASIBLE` | 问题不可行 |
| `cp.UNBOUNDED` | 问题无界 |
| `cp.OPTIMAL_INACCURATE` | 近似最优 |
| `cp.SolverError` | 求解器异常 |

---

## 八、⚠️ DCP 规则（必读）

CVXPY 自动检查凸性（Disciplined Convex Programming）。违反规则会报 `DCPError`。

**常见坑**：
- `x * y` 是非凸（两个变量相乘）→ 不通过
- `max(x, y)` 是凸的 → 通过
- `||x||²` 在目标中必须是 `cp.sum_squares(x)`，不能写 `x.T @ x`
- 非线性约束必须使用 CVXPY 原子函数

---

## 九、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| DCP 错误 | DCPError | 用 CVXPY 原子函数代替自定义表达式 |
| 变量乘法 | `x * y` 违规 | 改写成仿射表达式 |
| 非凸目标 | 求解器拒绝 | 确认问题确实是凸的 |
| 忘记 Parameter | 反复建新问题慢 | 用 Parameter 避免重建 |
| SolverError | 默认求解器不行 | `prob.solve(solver='SCS')` 切换 |
