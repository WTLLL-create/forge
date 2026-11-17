# SciPy 完整参考 — 数模求解层 (S4)

> 来源：scipy/scipy（GitHub 14.8k+ stars, BSD-3-Clause）
> 蒸馏自官方 optimize / integrate / interpolate / stats 等模块文档
> 服务于状态机 S4 (SOLVING) 的 5 步求解流程

---

## 一、模块速查

| 模块 | 用途 | 数模场景 |
|------|------|----------|
| `scipy.optimize` | 优化、方程求解、曲线拟合 | 优化类、参数估计 |
| `scipy.integrate` | 数值积分、ODE求解 | 机理建模、微分方程 |
| `scipy.interpolate` | 插值 | 数据补全、平滑 |
| `scipy.stats` | 统计检验、分布 | 数据分析、假设检验 |

---

## 二、优化 (scipy.optimize) — 最常用模块

### 2.1 方法选择决策（数模专用）

```
你的优化问题是什么类型？
│
├─ 目标+约束都是线性
│   └─→ linprog (线性规划) 或 milp (有整数变量)
│
├─ 无约束/只有边界约束
│   ├─ 有梯度 or 目标平滑 → L-BFGS-B
│   ├─ 无梯度 or 噪声多 → differential_evolution (全局)
│   │
├─ 有等式/不等式约束
│   ├─ 有梯度 → SLSQP 或 trust-constr
│   ├─ 无梯度 → COBYLA
│
├─ 需要全局最优
│   ├─ 维度 < 10 → differential_evolution (最鲁棒)
│   ├─ 维度 < 5 → brute (暴力网格)
│   ├─ 维度中等 + 连续 → dual_annealing
│   ├─ 维度低 + Lipschitz → direct
│   └─ 有约束 → shgo
│
├─ 曲线拟合/参数估计
│   └─→ curve_fit
│
└─ 单变量标量优化
    └─→ minimize_scalar
```

### 2.2 核心函数详解

#### minimize — 局部优化（全能接口）

```python
from scipy.optimize import minimize

# 函数签名
result = minimize(fun, x0, args=(), method=None,
                  bounds=None, constraints=None,
                  jac=None, hess=None, tol=1e-6)

# 返回 OptimizeResult：
#   result.x      → 最优解
#   result.fun    → 最优目标值
#   result.success → 是否收敛（必须检查！）
#   result.message → 状态说明
#   result.nit    → 迭代次数
```

**方法对比**：

| method | 需要梯度 | 支持边界 | 支持约束 | 推荐场景 |
|--------|:---:|:---:|:---:|----------|
| L-BFGS-B | 是 | 是 | 否 | 大规模有界问题（默认首选） |
| SLSQP | 可选 | 是 | 等式+不等式 | 通用约束优化 |
| trust-constr | 是 | 是 | 线性+非线性 | 最通用的约束求解器 |
| COBYLA | 否 | 否 | 不等式 | 无梯度/黑箱函数 |
| Nelder-Mead | 否 | 否 | 否 | 不光滑函数 |
| BFGS | 是 | 否 | 否 | 无约束中等规模 |

```python
# 示例：有界优化
from scipy.optimize import minimize, Bounds

def objective(x):
    return (x[0] - 1)**2 + (x[1] - 2.5)**2

bounds = Bounds([0, 0], [10, 10])
result = minimize(objective, x0=[5, 5], method='L-BFGS-B', bounds=bounds)
print(result.x)      # array([1., 2.5])
print(result.success) # True
```

#### linprog — 线性规划

```python
from scipy.optimize import linprog

# min c^T x  s.t. A_ub x <= b_ub, A_eq x == b_eq, lb <= x <= ub
result = linprog(
    c,                     # 目标系数 [c1, c2, ...]
    A_ub=A_ub, b_ub=b_ub, # 不等式约束
    A_eq=A_eq, b_eq=b_eq, # 等式约束
    bounds=[(0, None)],    # 变量边界
    method='highs'         # 默认/推荐
)
```

#### milp — 混合整数线性规划

```python
from scipy.optimize import milp, LinearConstraint

# 适用于 0-1 变量、整数变量
# integrality: 0=连续, 1=整数
result = milp(c, integrality=[1, 1, 0], constraints=constraints)
```

#### curve_fit — 曲线拟合

```python
from scipy.optimize import curve_fit

def model(x, a, b, c):
    return a * np.exp(-b * x) + c

popt, pcov = curve_fit(model, xdata, ydata, p0=[1, 0.5, 0])
# popt → 最优参数 [a, b, c]
# pcov → 协方差矩阵（对角线开方 = 参数标准差）
# np.sqrt(np.diag(pcov)) → 各参数的标准误差
```

**论文写法**："使用 Levenberg-Marquardt 算法进行非线性最小二乘拟合，得到参数 a = X, b = Y, c = Z，R² = 0.98。"

#### 全局优化方法

```python
from scipy.optimize import (
    differential_evolution,  # 差分进化（最推荐）
    dual_annealing,          # 对偶退火
    basinhopping,            # 盆地跳跃
    brute,                   # 暴力网格（低维<5）
    direct,                  # DIRECT算法
    shgo                     # SHG优化（支持约束）
)

# 差分进化（最通用）
result = differential_evolution(
    objective,
    bounds=[(0, 10), (0, 10)],
    maxiter=1000,
    popsize=15,
    seed=42
)

# 注意：全局方法计算量大，先在小规模上测试
```

### 2.3 约束类

```python
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint

# 变量边界
Bounds([lb1, lb2], [ub1, ub2])

# 线性约束 lb <= A @ x <= ub
LinearConstraint(A, lb, ub)

# 非线性约束 lb <= fun(x) <= ub
NonlinearConstraint(fun, lb, ub, jac=gradient_func)
```

---

## 三、积分与微分方程 (scipy.integrate) — S4 机理建模

### 3.1 数值积分

```python
from scipy.integrate import quad, dblquad, simpson

# 定积分 ∫_a^b f(x) dx
value, error = quad(lambda x: np.sin(x)**2, 0, np.pi)

# 二重积分
value, error = dblquad(lambda y, x: x*y, 0, 1, 0, lambda x: 1-x)

# 给定离散点的数值积分（Simpson法，比梯形法更精确）
y = np.array([1, 2, 3, 4, 5])
x = np.linspace(0, 1, 5)
area = simpson(y, x=x)

# 梯形法
from scipy.integrate import trapezoid
area = trapezoid(y, x=x)
```

### 3.2 ODE 初值问题 (solve_ivp) — 数模核心

```python
from scipy.integrate import solve_ivp

def ode_system(t, y):
    # y = [S, I, R]  传染病模型
    S, I, R = y
    beta, gamma = 0.3, 0.1
    dSdt = -beta * S * I
    dIdt = beta * S * I - gamma * I
    dRdt = gamma * I
    return [dSdt, dIdt, dRdt]

# 求解
sol = solve_ivp(
    ode_system,
    t_span=(0, 100),      # 时间范围
    y0=[0.99, 0.01, 0],   # 初始值
    method='RK45',         # 方法（见下表）
    t_eval=np.linspace(0, 100, 1000),  # 输出时间点
    rtol=1e-6, atol=1e-9  # 精度
)

print(sol.t)     # 时间点
print(sol.y)     # 解 [S(t), I(t), R(t)]，shape (3, n_t)
```

**方法选择**：

| method | 类型 | 适用场景 |
|--------|------|----------|
| **RK45** | 显式 Runge-Kutta 5(4) | 非刚性 ODE（默认，首选） |
| **DOP853** | 显式 RK 8阶 | 高精度需求 |
| **Radau** | 隐式 RK 5阶 | 刚性 ODE |
| **BDF** | 隐式后向差分 | 强刚性 ODE |
| **LSODA** | 自动切换 Adams/BDF | 不确定是否刚性时 |

> **数模经验**：先用 RK45，如果求解很慢（步长自动缩到极小）则换 Radau 或 BDF

### 3.3 边值问题 (solve_bvp)

```python
from scipy.integrate import solve_bvp

# 适用于两端都有边界条件的 ODE
# 例如：一维稳态热传导 d²T/dx² = 0, T(0)=0, T(L)=100
```

---

## 四、插值 (scipy.interpolate) — S3/S4 数据补充

### 4.1 函数选择

| 场景 | 函数 | 备注 |
|------|------|------|
| 1D 精确插值 | `CubicSpline` | C2平滑，推荐 |
| 1D 平滑（有噪声） | `UnivariateSpline` | s参数控制平滑度 |
| 多维散乱数据 | `griddata` | Delaunay三角剖分 |
| 多维规则网格 | `RegularGridInterpolator` | 高效利用网格结构 |
| 散乱数据高质量 | `RBFInterpolator` | 径向基函数 |
| ⛔ 遗留函数 | `interp1d` | 不推荐新代码使用 |

### 4.2 核心示例

```python
from scipy.interpolate import CubicSpline, UnivariateSpline, griddata, RegularGridInterpolator

# 1D 三次样条（数模最常用）
cs = CubicSpline(x_points, y_points)
y_interp = cs(x_query)           # 插值
y_deriv = cs(x_query, 1)         # 一阶导数
y_integ = cs.integrate(a, b)     # 定积分

# 1D 平滑样条（噪声数据）
spl = UnivariateSpline(x, y, s=0.5)  # s=0 精确插值，s>0 允许偏离
y_smooth = spl(x_query)

# 多维散乱数据插值
xi = np.linspace(x_min, x_max, 100)
grid_x, grid_y = np.meshgrid(xi, xi)
zi = griddata((x_scattered, y_scattered), z_values,
              (grid_x, grid_y), method='cubic')

# 规则网格多维插值
interp = RegularGridInterpolator(
    (x_grid, y_grid, z_grid),  # 各维坐标
    values,                     # N维网格上的值
    method='cubic'
)
result = interp(query_points)
```

---

## 五、统计 (scipy.stats) — S1/S5 数据分析与验证

### 5.1 描述性统计

```python
from scipy.stats import describe, skew, kurtosis, zscore

# 一次性获取：nobs, minmax, mean, variance, skewness, kurtosis
desc = describe(data)

# 偏度和峰度
skewness = skew(data)
kurt = kurtosis(data, fisher=True)  # Fisher 峰度（正态分布=0）

# Z 分数标准化
z_scores = zscore(data)
```

### 5.2 假设检验

```python
from scipy.stats import (
    ttest_1samp,    # 单样本 T 检验
    ttest_ind,      # 独立样本 T 检验（两组比较）
    f_oneway,       # 单因素 ANOVA（多组比较）
    pearsonr,       # Pearson 相关系数
    spearmanr,      # Spearman 秩相关
    chisquare,      # 卡方检验
    shapiro,        # Shapiro-Wilk 正态性检验（小样本 N<50）
    normaltest,     # D'Agostino 检验（大样本）
    kstest,         # K-S 检验
)

# 正态性检验
stat, p = shapiro(data)      # H0: 数据来自正态分布
if p > 0.05:
    print("数据服从正态分布")

# 相关系数
r, p_value = pearsonr(x, y)   # 线性相关
rho, p_value = spearmanr(x, y) # 单调相关

# 两组均值比较
t_stat, p_value = ttest_ind(group_a, group_b)
```

### 5.3 线性回归

```python
from scipy.stats import linregress

# 快速最小二乘回归
slope, intercept, r_value, p_value, std_err = linregress(x, y)
# 论文写法："线性回归结果显示 R² = {r_value**2:.4f}, p = {p_value:.4f}"

# 结果解读
y_pred = slope * x_query + intercept
residuals = y - (slope * x + intercept)
```

### 5.4 正态分布操作

```python
from scipy.stats import norm

norm.pdf(x, loc=0, scale=1)    # 概率密度
norm.cdf(x, loc=0, scale=1)    # 累积分布
norm.ppf(0.95, loc=0, scale=1)  # 分位数（逆CDF）
norm.rvs(loc=0, scale=1, size=100)  # 随机抽样
```

---

## 六、S4 求解流程集成

```
S2 输出: 模型名称 → models/xxx.md
       ↓
Step 1: 模型形式化 → 数学表达式 (变量/参数/目标/约束)
       ↓
Step 2: 参数准备   → S3 输出的 numpy 数组
       ↓
Step 3: 求解器选择 → 查本文档 §2 方法选择决策
       ↓
Step 4: 运行求解   → minimize / linprog / solve_ivp / curve_fit
       ↓          → 必须检查 result.success！
       ↓          → 失败则换方法（Failover）
       ↓
Step 5: 结果输出   → result.x + result.fun + 收敛信息
```

### 论文输出模板

```python
# 优化问题
result = minimize(f, x0, method='SLSQP', bounds=bounds, constraints=cons)
if result.success:
    print(f"最优解: {result.x}")
    print(f"最优目标值: {result.fun:.4f}")
    print(f"迭代次数: {result.nit}")
    print(f"收敛容差: {result.message}")
else:
    print(f"⚠️ 求解不收敛: {result.message}")

# 拟合问题
popt, pcov = curve_fit(model, x, y)
perr = np.sqrt(np.diag(pcov))  # 参数标准差
y_pred = model(x, *popt)
r2 = 1 - np.sum((y - y_pred)**2) / np.sum((y - np.mean(y))**2)
```

---

## 七、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| 初始值不好 | 不收敛 | 尝试多个 x0, 或用全局方法先粗搜 |
| 梯度符号错误 | minimize 发散 | 检查 jac 返回值 |
| 边界未设 | 解跑出物理范围 | 加 bounds 参数 |
| 约束不可行 | linprog 报 INFEASIBLE | 检查约束是否互相矛盾 |
| ODE 刚性 | RK45 步长极小 | 换 Radau 或 BDF |
| curve_fit 不收敛 | 参数跑飞 | 加 bounds + 调 p0 |
| 数据有 NaN | optimization 静默失败 | 先检查 `np.isnan(X).any()` |
