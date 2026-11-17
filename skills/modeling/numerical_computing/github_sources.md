# GitHub 仓库调研结果

> 阶段 11.1 — 第一部分 & 第二部分
>
> 调研日期：2026-07-29

---

## 一、核心仓库：NumPy

| 属性 | 内�� |
|------|------|
| **名称** | NumPy |
| **GitHub 地址** | https://github.com/numpy/numpy |
| **Stars** | ~32,400 |
| **Forks** | ~12,600 |
| **提交数** | 41,631 |
| **最新提���** | 2026-07-29 |
| **最新版本** | v2.5.1 |
| **许可证** | BSD-3-Clause |
| **维护状态** | ✅ 极活跃（��均多 commits） |
| **官网** | https://numpy.org |
| **文档** | https://numpy.org/doc |

### 核心内容

NumPy 是 Python 科学计算的**基础包**，提供：

- **ndarray** — 强大的 N 维数组对象，所有科学计算的数据载体
- **broadcasting** — 不同形状数组间的矢量化运算机制
- **vectorization** — 用数组操作替代 Python 循环，性能提升 10-100x
- **linear algebra** (`numpy.linalg`) — solve, inv, eig, svd, det, norm, qr, cholesky 等
- **random** (`numpy.random`) — 20+ 概率分布的随机采样，Monte Carlo 模拟基础
- **FFT** (`numpy.fft`) — 快速傅里叶变换，信号处理与频域分析
- **mathematical functions** — 逐元素数学运算（三角函数、指数对数、统计函数）
- **C/C++/Fortran 集成** — 与本地代码互操作

### 数学建模价值 ⭐⭐⭐⭐⭐

**所有优化、预测、统计模型的底层计算依赖。** 任何数学建模都离不开 ndarray 作为数据容器和矢量化计算引擎。

### 重点提取

针对数学建模场景，重点关注：

| 特性 | 建模用途 | 优先级 |
|------|----------|--------|
| ndarray 创建与操作 | 数据加载、矩阵构造 | 必须 |
| broadcasting | 高效逐元素运算 | 必须 |
| vectorization | 替代循环，加速计算 | 必须 |
| `numpy.linalg.solve` | 线性方程组求解 | 高 |
| `numpy.linalg.eig/eigh` | 特征值分析、PCA | 高 |
| `numpy.linalg.svd` | 降维、矩阵压缩 | 高 |
| `numpy.random` | 蒙特卡洛模拟、Bootstrap | 高 |
| `numpy.polyfit` | 多项式拟合 | 中 |
| `numpy.fft` | 信号/周期数据分析 | 低 |

### 推荐长期保留

✅ **是。** 作为 Python 数值计算的基石，NumPy 是数学建模的必备技能。

---

## 二、核心仓库：SciPy

| 属性 | 内容 |
|------|------|
| **名称** | SciPy |
| **GitHub 地址** | https://github.com/scipy/scipy |
| **Stars** | ~14,900 |
| **Forks** | ~5,800 |
| **提交数** | 37,961 |
| **最新提交** | 2026-07-29 |
| **最新版本** | v1.18.0 |
| **许可证** | BSD-3-Clause |
| **维护状态** | ✅ 极活跃 |
| **官网** | https://scipy.org |
| **文档** | https://docs.scipy.org/doc/scipy/ |

### 核心内容

SciPy 是建立在 NumPy 之上的科学计算库，共 18 个子包：

| 子包 | 用途 | 建模优先级 |
|------|------|-----------|
| `scipy.optimize` | 优化：minimize, linprog, least_squares, curve_fit, milp | ⭐⭐⭐⭐⭐ |
| `scipy.integrate` | 积分与ODE：quad, solve_ivp, solve_bvp | ⭐⭐⭐⭐ |
| `scipy.linalg` | 高级线性代数：solve, eig, svd, lu, qr, expm | ⭐⭐⭐⭐ |
| `scipy.stats` | 统计：分布、检验、描述统计 | ⭐⭐⭐⭐⭐ |
| `scipy.interpolate` | 插值：样条、网格插值 | ⭐⭐⭐ |
| `scipy.fft` | 快速傅里叶变换 | ⭐⭐ |
| `scipy.sparse` | 稀疏矩阵 | ⭐⭐ |
| `scipy.spatial` | 空间算法（KDTree, Delaunay, 凸包） | ⭐⭐ |
| `scipy.signal` | 信号处理 | ⭐ |
| `scipy.cluster` | 聚类算法 | ⭐⭐ |
| `scipy.constants` | 物理/数学常数 | ⭐⭐ |
| `scipy.special` | 特殊函数（Bessel, Gamma 等） | ⭐ |
| `scipy.ndimage` | N 维图像处理 | ⭐ |
| `scipy.odr` | 正交距离回归 | ⭐ |
| `scipy.datasets` | 内置数据集 | ⭐ |
| `scipy.differentiate` | 数值微分 | ⭐⭐ |
| `scipy.fftpack` | 传统 FFT（已弃用） | ⭐ |
| `scipy.io` | 文件 I/O（MATLAB, wav） | ⭐⭐ |

### 数学建模价值 ⭐⭐⭐⭐⭐

**建模核心工具库。** optimize 解决最优化问题，integrate 求解微分方程，linalg 处理矩阵分解，stats 做统计推断和概率建模。

### 重点提取

#### scipy.optimize（最重要）

| API | 用途 | 建模场景 |
|-----|------|----------|
| `minimize` | 通用函数最小化（支持 14 种算法） | 参数估计、最优设计 |
| `linprog` | 线性规划 | 资源分配、生产计划 |
| `milp` | 混合整数线性规划 | 选址、调度 |
| `curve_fit` | 非线性曲线拟合 | 趋势预测、参数标定 |
| `least_squares` | 非线性最小二乘 | 数据拟合、参数估计 |
| `differential_evolution` | 全局优化（不需要梯度） | 非凸问题、黑箱优化 |
| `basinhopping` | 全局优化（随机+局部） | 多极值函数 |
| `root` | 方程求根 | 平衡点计算 |
| `minimize_scalar` | 单变量优化 | 一维搜索 |
| `NonlinearConstraint` | 非线性约束 | 复杂约束建模 |
| `LinearConstraint` | 线性约束 | 资源约束 |
| `Bounds` | 变量范围约束 | 物理限制 |

#### scipy.integrate

| API | 用途 | 建模场景 |
|-----|------|----------|
| `quad` | 定积分 | 概率/期望计算 |
| `dblquad` | 二重积分 | 面积/体积 |
| `solve_ivp` | ODE 初值问题 | 动力系统（SIR, Lotka-Volterra） |
| `solve_bvp` | ODE 边值问题 | 稳态分布 |
| `simpson` | 辛普森积分（离散数据） | 不规则数据积分 |
| `trapezoid` | 梯形积分 | 离散数据积分 |

#### scipy.linalg（NumPy linalg 的增强版）

| API | 用途 | 建模场景 |
|-----|------|----------|
| `solve` | Ax=b 求解 | 线性方程组 |
| `eig` / `eigh` | 特征值/特征向量 | 主成分分析、稳定性分析 |
| `svd` | 奇异值分解 | 降维、伪逆 |
| `lu` / `qr` / `cholesky` | 矩阵分解 | 数值稳定性增强 |
| `lstsq` | 最小二乘解 | 超定方程组 |
| `inv` / `pinv` | 逆/伪逆 | 矩阵求逆 |
| `det` | 行列式 | 矩阵性质判断 |
| `norm` | 矩阵/向量范数 | 误差度量 |
| `expm` / `logm` / `sqrtm` | 矩阵函数 | 微分方程解析解 |

#### scipy.stats

| API | 用途 | 建模场景 |
|-----|------|----------|
| `norm`, `t`, `chi2`, `f` 等 | 100+ 概率分布 | 随机模拟、假设检验 |
| `describe` | 描述性统计 | 数据探索 |
| `ttest_ind` / `ttest_1samp` | t 检验 | 组间差异比较 |
| `f_oneway` | 方差分析 | 多组比较 |
| `pearsonr` / `spearmanr` | 相关性检验 | 变量关系分析 |
| `kstest` / `shapiro` / `normaltest` | 正态性/分布检验 | 模型假设验证 |
| `mannwhitneyu` / `kruskal` | 非参数检验 | 非正态数据 |
| `linregress` | 线性回归 | 简单回归分析 |
| `chi2_contingency` | 卡方检验 | 分类变量独立性 |
| `zscore` / `skew` / `kurtosis` / `iqr` | 标准化/形态统计 | 数据预处理 |

### 推荐长期保留

✅ **是。** SciPy 是数学建模中优化、统计、积分、微分方程求解的标准工具。

---

## 三、补充仓库：TheAlgorithms/Python

| 属性 | 内容 |
|------|------|
| **名称** | TheAlgorithms/Python |
| **GitHub 地址** | https://github.com/TheAlgorithms/Python |
| **Stars** | ~222,900 |
| **Forks** | ~50,900 |
| **提交数** | 3,666 |
| **最新提交** | 2026-07-21 |
| **许可证** | MIT |
| **维护状态** | ✅ 活跃 |

### 核心内容

- 800+ 算法实现，覆盖 40+ 类别
- 面向学习，不是生产级代码
- 含 linear_algebra, maths, dynamic_programming, genetic_algorithm, graphs 等子模块

### 数学建模价值 ⭐⭐⭐

**算法思想参考源**，而非直接调用库。建模中的特殊算法（如遗传算法、动态规划变体）可参考其实现思路。

与建模直接相关的子目录：
- `linear_algebra/` — 矩阵运算的纯 Python 实现（教学用途）
- `maths/` — 数值方法、素数、数列等
- `dynamic_programming/` — DP 模式参考
- `genetic_algorithm/` — 遗传算法参考实现

### 推荐长期保留

✅ **参考保留。** 非直接使用，但作为算法理解的教学资源有价值。**不在 Skill 中收录源码。**

---

## 四、补充仓库：Jupyter Notebook

| 属性 | 内容 |
|------|------|
| **名称** | Jupyter Notebook |
| **GitHub 地址** | https://github.com/jupyter/notebook |
| **Stars** | ~13,300 |
| **Forks** | ~5,700 |
| **提交数** | 13,803 |
| **最新提交** | 2026-07-29 |
| **最新版本** | v7.7.0a1 |
| **许可证** | BSD-3-Clause |
| **维护状态** | ✅ 极活跃 |

### 核心内容

基于 Web 的交互式计算笔记本环境，支持 Notebook v7（基于 JupyterLab）和 Classic Notebook v6。

### 数学建模价值 ⭐⭐⭐

**实验流程载体和数据分析记录工具。** 建模过程中的数据探索、模型迭代、结果可视化适合用 Jupyter Notebook 组织和记录。

### 推荐长期保留

✅ **工具保留。** 不直接收录到 Skill 代码中，但作为建模工作流的标准工具环境推荐。

---

## 五、补充仓库：scikit-learn（关联参考）

| 属性 | 内容 |
|------|------|
| **名称** | scikit-learn |
| **GitHub 地址** | https://github.com/scikit-learn/scikit-learn |
| **Stars** | ~66,800 |
| **Forks** | ~27,200 |
| **许可证** | BSD-3-Clause |
| **维护状态** | ✅ 极活跃 |

### 数学建模价值 ⭐⭐（本期）

**不作为阶段 11.1 重点**，仅为后续预测/分类模块提供关联参考。11.1 聚焦数值计算基础，不涉及机器学习。

### 推荐长期保留

✅ **关联参考。** 后续阶段（如预测建模、分类问题）将详细调研。

---

## 六、采用仓库列表（最终汇总）

| # | 仓库 | Stars | 角色 | Skill 中收录方式 |
|---|------|-------|------|------------------|
| 1 | numpy/numpy | ~32.4k | 数值计算基础 | API 映射 + 知识提炼 |
| 2 | scipy/scipy | ~14.9k | 科学计算核心 | API 映射 + 知识提炼 |
| 3 | TheAlgorithms/Python | ~222.9k | 算法思想参考 | 索引记录（不收录源码） |
| 4 | jupyter/notebook | ~13.3k | 实验环境工具 | 工具链推荐 |
| 5 | scikit-learn/scikit-learn | ~66.8k | 后续模块关联 | 关联索引 |

---

## 七、Stars 和活跃度总结

```
仓库                   Stars    活跃度    关键性
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NumPy                 32.4k    每日提交   ⭐⭐⭐⭐⭐
SciPy                 14.9k    每日提交   ⭐⭐⭐⭐⭐
TheAlgorithms/Python  222.9k   周级提交   ⭐⭐⭐
Jupyter Notebook      13.3k    每日提交   ⭐⭐⭐
scikit-learn           66.8k    每日提交   ⭐⭐ (本期)
```

所有仓库在 2026 年 7 月均有活跃提交，社区健康，适合作为长期知识来源。
