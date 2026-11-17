# SciPy 知识提炼：数学建模核心模块

> 来源：https://github.com/scipy/scipy （v1.18.0, 14.9k stars）
>
> 覆盖：optimize / integrate / linalg / stats 四大建模核心模块

---

## 一、`scipy.optimize` — 最优化工具箱 ⭐⭐⭐⭐⭐

### 1.1 `minimize` — 通用函数最小化

```python
from scipy.optimize import minimize, Bounds, LinearConstraint, NonlinearConstraint

# 基本签名
result = minimize(fun, x0, method='...', bounds=bounds, constraints=cons)
# result.x   → 最优解
# result.fun  → 最优值
# result.success → 是否收敛
```

**完整方法选择矩阵（14种+全局）：**

### 局部最小化

| 场景 | 推荐 method | 特点 | 需梯度 | 大规模 |
|------|------------|------|:---:|:---:|
| 无约束+有梯度+快收敛 | `BFGS` | 拟牛顿 | ✓ | |
| 无约束+有Hessian | `Newton-CG` | 二阶收敛 | ✓ | ✓ |
| 无约束+无梯度 | `Nelder-Mead` | 单纯形，不需求导 | | |
| 有界约束+有梯度 | `L-BFGS-B` | **有限内存，首选** | ✓ | ✓ |
| 有界+无梯度 | `Powell` | 更稳定替代NM | | |
| 非线性约束+有梯度 | `SLSQP` | **等式+不等式首选** | ✓ | |
| 非线性约束+无梯度 | `COBYLA` / `COBYQA` | 线性近似 | | |
| 大规模约束，最通用 | `trust-constr` | 信赖域 | ✓ | ✓ |
| 中等规模最少迭代 | `trust-exact` | 精确Hessian | ✓ | |

### 全局优化

| 场景 | 推荐方法 | 特点 |
|------|---------|------|
| 有界,需要所有局部最小值 | `shgo` | 确定性全局 |
| 有界,需要并行 | `differential_evolution` | workers=n 并行 |
| 有界,一般用途 | `dual_annealing` | 模拟退火改进 |
| 单变量 | `minimize_scalar(method='brent')` | |

### 1.2 `linprog` — 线性规划

```python
from scipy.optimize import linprog

# min c^T x  s.t. A_ub x <= b_ub, A_eq x = b_eq, bounds
result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                 bounds=[(0, None), (0, None)], method='highs')
```

建模场景：资源分配、生产计划、运输问题

### 1.3 `curve_fit` — 非线性曲线拟合

```python
from scipy.optimize import curve_fit

# 拟合 y = f(x, *params)
popt, pcov = curve_fit(f, xdata, ydata, p0=initial_guess)
# popt  → 最优参数
# pcov  → 协方差矩阵（对角元素平方根 = 参数标准误）
```

建模场景：趋势预测、参数标定、经验公式拟合

### 1.4 `least_squares` — 非线性最小二乘

```python
from scipy.optimize import least_squares

# min Σ r_i(x)^2, 其中 r_i = f_i(x) - y_i
result = least_squares(residuals, x0, bounds=(lb, ub))
```

建模场景：传感器校准、参数估计（比 curve_fit 更灵活）

### 1.5 全局优化

```python
# 差分进化（不需求导，适合黑箱）
from scipy.optimize import differential_evolution
result = differential_evolution(func, bounds)

# Basin-hopping（随机+局部搜索）
from scipy.optimize import basinhopping
result = basinhopping(func, x0)
```

### 1.6 方程求根

```python
# 标量方程 f(x)=0
from scipy.optimize import root_scalar
sol = root_scalar(f, bracket=[a, b], method='brentq')

# 方程组 F(x)=0
from scipy.optimize import root
sol = root(F, x0)
```

---

## 二、`scipy.integrate` — 积分与微分方程 ⭐⭐⭐⭐

### 2.1 数值积分

```python
from scipy.integrate import quad, dblquad, simpson, trapezoid

# 定积分 ∫_a^b f(x) dx
value, error = quad(f, a, b)

# 二重积分
value, error = dblquad(lambda y, x: f(x, y), x_min, x_max, y_min, y_max)

# 离散数据积分（已有采样点）
area = simpson(y, x=x)  # 或 trapezoid(y, x=x)
```

### 2.2 常微分方程 — `solve_ivp`

```python
from scipy.integrate import solve_ivp

# 求解 dy/dt = f(t, y)，初值 y(t0) = y0
sol = solve_ivp(f, [t0, t_end], y0, method='RK45',
                t_eval=np.linspace(t0, t_end, 1000))
# sol.t → 时间点
# sol.y → 解数组 (n_vars × n_times)
```

**求解器选择（v2.0 验证）：**

| 刚度 | 推荐 | 说明 | 支持雅可比 |
|------|------|------|:---:|
| 非刚性 | `RK45` | 默认，5(4)阶自适应 | |
| 刚性+高精度 | `Radau` | 隐式Runge-Kutta | ✓ |
| 刚性 | `BDF` | 后向差分公式 | |
| 不确定 | `LSODA` | 自动检测并切换 | |

**精度控制**: 默认参数可能不准 → 设 `rtol=1e-8, atol=1e-8`

**大刚性系统加速**: 用 `odeint` + `ml/mu` 带状雅可比 → 性能提升可达 130x

### 2.3 边值问题 — `solve_bvp`

```python
from scipy.integrate import solve_bvp

# 求解 dy/dx = f(x, y)，边界条件 bc(ya, yb) = 0
sol = solve_bvp(f, bc, x, y_guess)
```

---

## 三、`scipy.linalg` — 高级线性代数 ⭐⭐⭐⭐

> SciPy 的 linalg 是 NumPy linalg 的增强版：更多算法、更好的性能、更全面的接口

### 3.1 矩阵分解

```python
from scipy.linalg import lu, qr, cholesky, svd

# LU 分解（求解 Ax=b 更稳定）
P, L, U = lu(A)       # A = P @ L @ U
x = solve(A, b)       # 内部使用 LU

# QR 分解（正交化、最小二乘）
Q, R = qr(A)

# Cholesky 分解（对称正定矩阵）
L = cholesky(A, lower=True)  # A = L @ L^T

# SVD（比 np 版本更多选项）
U, s, Vt = svd(A)
```

### 3.2 矩阵函数

```python
from scipy.linalg import expm, logm, sqrtm

# 矩阵指数（微分方程解析解）
expA = expm(A)   # e^A

# 矩阵对数/平方根
logA = logm(A)
sqrtA = sqrtm(A)
```

### 3.3 特殊求解

```python
# 伪逆（处理奇异矩阵）
A_pinv = pinv(A)           # 或 pinvh（Hermitian）

# 行列式符号/对数（避免溢出）
sign, logdet = slogdet(A)   # det = sign * exp(logdet)

# 子空间
basis = null_space(A)       # 零空间
basis = orth(A)             # 正交基
```

---

## 四、`scipy.stats` — 概率统计工具箱 ⭐⭐⭐⭐⭐

### 4.1 概率分布（100+ 种）

```python
from scipy import stats

# 通用接口（以正态为例）
stats.norm.pdf(x, loc=0, scale=1)   # 概率密度
stats.norm.cdf(x, loc=0, scale=1)   # 累积概率 P(X ≤ x)
stats.norm.ppf(q, loc=0, scale=1)   # 分位数（逆 CDF）
stats.norm.rvs(size=100)            # 随机采样

# 常用分布速查
stats.norm       # 正态（测量误差）
stats.expon      # 指数（等待时间）
stats.uniform    # 均匀（先验）
stats.t          # t 分布（小样本推断）
stats.chi2       # 卡方（拟合优度）
stats.f          # F 分布（方差比）
stats.poisson    # 泊松（事件计数）
stats.binom      # 二项（成功率）
stats.lognorm    # 对数正态（偏态数据）
```

### 4.2 描述性统计

```python
stats.describe(data)     # 一次性返回 n, min, max, mean, var, skewness, kurtosis
stats.zscore(data)       # 标准化 (x - mean) / std
stats.skew(data)         # 偏度
stats.kurtosis(data)     # 峰度
stats.iqr(data)          # 四分位距
stats.sem(data)          # 标准误
```

### 4.3 统计检验

```python
# t 检验（组间均值差异）
t_stat, p_value = stats.ttest_ind(group1, group2)
t_stat, p_value = stats.ttest_1samp(data, popmean)

# ANOVA（多组比较）
f_stat, p_value = stats.f_oneway(g1, g2, g3)

# 非参数检验
u_stat, p_value = stats.mannwhitneyu(g1, g2)   # Mann-Whitney U
h_stat, p_value = stats.kruskal(g1, g2, g3)     # Kruskal-Wallis
w_stat, p_value = stats.wilcoxon(before, after)  # 配对 Wilcoxon

# 相关性
r, p = stats.pearsonr(x, y)      # Pearson 线性相关
rho, p = stats.spearmanr(x, y)   # Spearman 秩相关

# 分布检验
stat, p = stats.normaltest(data)  # 正态性检验
stat, p = stats.kstest(data, 'norm')  # KS 检验
stat, p = stats.shapiro(data)     # Shapiro-Wilk（小样本首选）

# 线性回归
slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
```

### 4.4 建模常用检验场景

| 你想做什么 | 用什么检验 |
|-----------|-----------|
| 判断数据是否符合正态分布 | `normaltest` / `shapiro` |
| 比较两组实验数据的均值差异 | `ttest_ind` |
| 比较三组以上 | `f_oneway` |
| 数据不满足正态假设 | `mannwhitneyu` / `kruskal` |
| 判断两个变量是否相关 | `pearsonr` / `spearmanr` |
| 两分类变量是否独立 | `chi2_contingency` |
| 数据标准化 | `zscore` |

---

## 五、建模最佳实践

1. **先尝试局部优化**：能用 minimize 解决的不上全局优化（差 10-100x 速度）
2. **ODEs 默认用 RK45**：非刚性场景足够，刚性时切换到 Radau/BDF
3. **大规模矩阵用稀疏**：超过 90% 的零元素就值得用 `scipy.sparse`
4. **检验前先做诊断**：做 t 检验前检��正态性；做 ANOVA 前检查方差齐性
5. **可重复性**：随机种子用 `numpy.random.default_rng(seed)`，优化用 `minimize(..., options={'seed': 42})`

---

## 六、`pymoo` — 多目标进化算法 ⭐⭐⭐⭐

> 来源: pymoo v0.6.2 (2026-07 爬取验证)
> 覆盖 scipy 不擅长的多目标/黑箱/离散优化

### 6.1 算法选择矩阵

| 问题类型 | 首选 | 备选 |
|------|------|------|
| 单目标, 连续 | GA / DE | PSO, CMAES |
| 单目标, 组合优化 | BRKGA | GA(custom encoding) |
| 双目标 | **NSGA-II** | SPEA2, MOPSO-CD |
| 三目标+ (many-objective) | **NSGA-III** | MOEAD, AGE-MOEA |
| 用户有偏好 | R-NSGA-II/III | PI-NSGA-II |
| 约束处理 | NSGA-II (支持约束) | C-TAEA |

### 6.2 NSGA-II 关键参数

```python
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.lhs import LHS

algorithm = NSGA2(
    pop_size=100,
    n_offsprings=100,
    sampling=LHS(),           # 拉丁超立方初始采样
    crossover=SBX(prob=0.9, eta=15),
    mutation=PM(prob=0.1, eta=20),
    eliminate_duplicates=True
)
```

**pymoo 陷阱** (来自 memory/mistakes/):
- v0.6.2: `Result.F` 可能为 None → 用 `Result.pop.get("F")`
- 需要终止条件: `('n_gen', 200)` 或 `('n_eval', 10000)`
