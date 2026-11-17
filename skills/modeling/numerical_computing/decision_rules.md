# AI 决策规则：根据问题关键词自动选择数值计算工具

> 本文件定义 Agent 的自动判断逻辑。Agent 读取数学建模问题文本后，按以下规则分级匹配，确定应使用的 NumPy/SciPy 工具。

---

## 决策流程

```
输入：建模问题描述文本
  │
  ├─ Level 1: 关键词扫描 → 问题大类识别
  │
  ├─ Level 2: 子特征匹配 → 精确工具定位
  │
  ├─ Level 3: 约束检查 → 方法选择（如 minimize 的 method 参数）
  │
  └─ 输出：推荐工具 + API + 参考案例
```

---

## Level 1: 问题大类识别

扫描问题描述中的关键词，匹配到以下六大类之一：

### 大类 A：优化问题

**触发关键词**（任一命中）：
- 最大、最小、极大化、极小化、最大化、最小化
- 最优、最佳、最省钱、最省时、最省力
- 约束、限制、不超过、不低于、在...条件下
- 资源分配、成本控制、产量规划、投资组合
- 利润最大、成本最低、效率最高、损耗最小
- 线性规划、非线性规划、整数规划

**命中 → 调用 `scipy.optimize`**

**子分类**：
| 子特征 | 关键词 | 推荐 API |
|--------|--------|----------|
| 目标+约束都是线性 | 线性规划、单纯形 | `linprog` |
| 需要整数解 | 整数、0-1、二进制 | `milp` |
| 非线性、有约束 | 非线性、不等式 | `minimize` + constraints |
| 无约束 | 无约束、自由变量 | `minimize` (BFGS/L-BFGS-B) |
| 全局最优 | 全局、多个极值、非凸 | `differential_evolution` |
| 单变量 | 一维、单个参数 | `minimize_scalar` |

---

### 大类 B：拟合/预测问题

**触发关键词**（任一命中）：
- 拟合、回归、预测、趋势、走势
- 历史数据、时间序列、外推、估计参数
- 曲线、散点图、数据点、经验公式
- 增长率、衰减率、指数增长、对数增长
- 标定参数、确定系数、经验常数

**命中 → 调用 `scipy.optimize.curve_fit` 或 `numpy.polyfit`**

**子分类**：
| 子特征 | 关键词 | 推荐 API |
|--------|--------|----------|
| 线性关系 | 线性、直线、正比 | `scipy.stats.linregress` |
| 指数/对数 | 指数、对数、增长率 | `curve_fit` + 自定义函数 |
| 多项式 | 多项式、二次、三次 | `numpy.polyfit` |
| 自定义非线性 | 自定义、特殊函数 | `curve_fit` + 自定义函数 |
| 逻辑增长 | S型、饱和、逻辑 | `curve_fit` + sigmoid/logistic |

---

### 大类 C：微分方程/动力系统

**触发关键词**（任一命中）：
- 微分方程、ODE、常微分、偏微分
- dx/dt、导数、变化率、速率
- 动力系统、动态模型、系统动力学、反馈
- 演化、随时间变化、传播、扩散、增长
- 传染病、种群、化学反应、振动、衰减
- SIR、SEIR、Lotka-Volterra、捕食者

**命中 → 调用 `scipy.integrate.solve_ivp`**

**子分类**：
| 子特征 | 关键词 | 推荐 API |
|--------|--------|----------|
| 初值已知 | 初始条件、t=0时、开始时 | `solve_ivp` |
| 边界条件已知 | 两端已知、边界值 | `solve_bvp` |
| 刚性方程 | 刚性、stiff | `solve_ivp(method='Radau'/'BDF')` |

---

### 大类 D：线性代数/矩阵计算

**触发关键词**（任一命中）：
- 解方程、方程组、线性系统、Ax=b
- 矩阵、向量、行列式、特征值、特征向量
- 分解、SVD、QR、LU、Cholesky
- 求逆、伪逆、秩、范数
- 主成分、降维、正交化
- 最小二乘

**命中 → 调用 `numpy.linalg` 或 `scipy.linalg`**

**子分类**：
| 子特征 | 关键词 | 推荐 API |
|--------|--------|----------|
| 解方程组 | 求解、解方程、未知数 | `numpy.linalg.solve` |
| 超定方程 | 多于方程、近似解 | `numpy.linalg.lstsq` |
| 特征分析 | 特征值、特征向量、固有 | `numpy.linalg.eig` |
| 矩阵分解 | SVD、奇异值、分解 | `numpy.linalg.svd` |
| 对称矩阵 | 对称、Hermite、实对称 | `numpy.linalg.eigh` |

---

### 大类 E：概率统计/随机模拟

**触发关键词**（任一命中）：
- 随机、概率、分布、抽样、采样
- Monte Carlo、蒙特卡洛、模拟、仿真
- 均值、方差、标准差、中位数、分位数
- 正态分布、泊松、二项、均匀分布
- 检验、显著性、假设检验、p值
- 相关、相关系数、独立性
- Bootstrap、置信区间

**命中 → 调用 `numpy.random` + `scipy.stats`**

**子分类**：
| 子特征 | 关键词 | 推荐 API |
|--------|--------|----------|
| 随机采样 | 生成随机数、采样、模拟 | `numpy.random.default_rng()` |
| 分布计算 | 概率密度、累积分布、分位数 | `scipy.stats.<dist>.pdf/cdf/ppf` |
| 描述统计 | 均值、方差、偏度、峰度 | `scipy.stats.describe` |
| 组间比较 | 两组、差异、对比 | `scipy.stats.ttest_ind` |
| 相关性 | 相关系数、关联 | `scipy.stats.pearsonr` / `spearmanr` |
| 分布检验 | 是否符合、正态性 | `scipy.stats.normaltest` / `kstest` |

---

### 大类 F：积分/数值计算

**触发关键词**（任一命中）：
- 积分、积分值、面积、体积
- 曲线下面积、定积分、不定积分
- 累计、累加、累积量
- 插值、内插、外插、平滑
- 求根、零点、解方程 f(x)=0
- 导数、梯度、微分、灵敏度

**命中 → 调用 `scipy.integrate` / `scipy.optimize.root` / `scipy.interpolate`**

---

## Level 2: 精确工具匹配

当 Level 1 确定大类后，根据更具体的特征选择精确 API：

### A 类细化：优化方法选择（scipy.optimize.minimize 的 method 参数）

**来源: scipy v2.0 optimize tutorial (2026-07 爬取验证)**

```
全局 or 局部？
├── 全局优化
│   ├── 仅有界约束 + 需要所有局部最小值 → shgo
│   ├── 仅有界约�� + 需要并行 → differential_evolution (workers=n)
│   ├── 仅有界约束 + 一般用途 → dual_annealing / direct
│   └── 有非线性约束 → shgo(确定性) / differential_evolution(随机)
│
└── 局部优化
    ├── 单变量? → minimize_scalar(method='brent')
    ├── 无约束
    │   ├── 有梯度+有Hessian → Newton-CG / trust-ncg / trust-krylov
    │   ├── 有梯度+无Hessian → BFGS / CG
    │   └── 无梯度 → Nelder-Mead / Powell
    ├── 仅有界约束
    │   ├── 有梯度 → L-BFGS-B / TNC
    │   └── 无梯度 → Nelder-Mead / Powell
    └── 有非线性约束
        ├── 有梯度 → SLSQP / trust-constr
        └── 无梯度 → COBYLA / COBYQA
```

**minimize method 完整矩阵**:

| method | 有界约束 | 非线性约束 | 需要梯度 | 需要Hessian | 大规模 | 数模首选场景 |
|--------|:---:|:---:|:---:|:---:|:---:|------|
| Nelder-Mead | ✓ | | | | | 简单函数, 快速原型 |
| Powell | ✓ | | | | | 替代NM, 更稳定 |
| CG | | | ✓ | | | 共轭梯度, 需梯度 |
| BFGS | | | ✓ | | | 快速收敛, 需梯度 |
| Newton-CG | | | ✓ | ✓ | ✓ | 可提供Hessian |
| L-BFGS-B | ✓ | | ✓ | | ✓ | **有限内存+有界←首选** |
| TNC | ✓ | | ✓ | | | 截断牛顿法 |
| COBYLA | ✓ | ✓ | | | | 非线性约束+无梯度 |
| COBYQA | ✓ | ✓ | | | | COBYLA改进版 |
| SLSQP | ✓ | ✓ | ✓ | | | **等式+不等式约束←首选** |
| trust-constr | ✓ | ✓ | ✓ | ✓ | ✓ | 大规模约束,最通用 |
| dogleg | | | ✓ | ✓ | | 信任域Dogleg |
| trust-ncg | | | ✓ | ✓ | ✓ | Hessian病态优于Newton-CG |
| trust-krylov | | | ✓ | ✓ | ✓ | 不定问题,比trust-ncg精确 |
| trust-exact | | | ✓ | ✓ | | 中等规模, 最少迭代 |

### C 类细化：ODE 求解器选择

**来源: scipy v2.0 integrate tutorial (2026-07 爬取验证)**

```
非刚性      → method='RK45' (默认, 显式, 不支持雅可比)
高精度刚性   → method='Radau' (隐式, 支持雅可比)
刚性         → method='BDF'
自动切换     → method='LSODA'

大刚性系统 + 带状雅可比:
  → 用 odeint (不是 solve_ivp)
  → 设置 ml/mu 带宽参数 → 性能提升可达 130x
```

```
solve_ivp 精度控制:
  默认参数下可能不准 → 设置 rtol=1e-8, atol=1e-8
  指定输出时间点 → t_eval=np.linspace(t0, t_end, 1000)
```

---

## Level 3: 组合调用模式

某些复杂问题需要多个工具的串联使用：

### 模式 1：拟合 + 预测

```
1. scipy.optimize.curve_fit → 得到最优参数
2. numpy.linspace + 拟合函数 → 生成预测值
3. scipy.stats.linregress → 评估拟合优度
```

### 模式 2：优化 + 蒙特卡洛验证

```
1. scipy.optimize.minimize → 得到最优解
2. numpy.random 生成扰动 → 在最优解附近采样
3. scipy.stats.describe → 统计稳健性
```

### 模式 3：ODE + 参数估计

```
1. scipy.integrate.solve_ivp → 定义动力系统
2. scipy.optimize.curve_fit → 用观测数据估计参数
3. scipy.stats.pearsonr → 评估拟合效果
```

---

## 自检清单（Agent 使用后自检）

每完成一次工具选择，Agent 应自查：

- [ ] 问题大类是否正确？（A/B/C/D/E/F）
- [ ] 子特征是否匹配？（线性/非线性/约束/无约束...）
- [ ] API 参数是否合理？（method、bounds、constraints）
- [ ] 是否需要组合调用？
- [ ] 是否有参考案例可复用？
