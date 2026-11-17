# API 映射表：建模问题 → 数学方法 → Python 工具

> 数学建模中常见问题的端到端 API 映射
>
> 格式：问题描述 → 数学形式 → Python API → 来源仓库 → 典型应用

---

## 一、线性方程组 & 矩阵运算

### 1.1 线性方程组求解

```
问题：求解线性方程组
数学：Ax = b
工具：numpy.linalg.solve / scipy.linalg.solve
来源：NumPy / SciPy
应用：参数估计、平衡模型、电路分析、结构力学
```

### 1.2 超定方程组（最小二乘）

```
问题：方程数多于未知数，求最优近似解
数学：min ||Ax - b||_2
工具：numpy.linalg.lstsq / scipy.linalg.lstsq
来源：NumPy / SciPy
应用：数据拟合、回归分析、传感器校准
```

### 1.3 矩阵分解

```
问题：矩阵降维、特征提取、数值稳定化
数学：A = U Σ V^T (SVD) / A = Q R / A = L U / A = L L^T
工具：numpy.linalg.svd / qr / lu / cholesky
来源：NumPy
应用：主成分分析、推荐系统、图像压缩、求解加速
```

### 1.4 特征值问题

```
问题：分析系统固有特性
数学：A v = λ v
工具：numpy.linalg.eig / eigh / eigvals
来源：NumPy
应用：稳定性分析、振动模态、PageRank、PCA
```

---

## 二、最优化问题

### 2.1 线性规划

```
问题：在线性约束下最大化/最小化线性目标
数学：min c^T x  s.t. A_ub x <= b_ub, A_eq x = b_eq, bounds
工具：scipy.optimize.linprog
来源：SciPy
应用：资源分配、生产规划、运输调度、投资组合
```

### 2.2 混合整数线性规划

```
问题：部分变量必须为整数
数学：同 linprog，增加 x_i ∈ Z 约束
工具：scipy.optimize.milp
来源：SciPy
应用：选址问题、排班调度、网络设计
```

### 2.3 无约束非线性优化

```
问题：寻找函数最小值（无约束）
数学：min f(x)
工具：scipy.optimize.minimize (method='BFGS'/'L-BFGS-B'/'Nelder-Mead'...共14种)
来源：SciPy
应用：参数标定、极大似然估计、最优设计
```

### 2.4 有约束非线性优化

```
问题：在等式/不等式约束下寻优
数学：min f(x) s.t. g(x) <= 0, h(x) = 0
工具：scipy.optimize.minimize + NonlinearConstraint / LinearConstraint / Bounds
来源：SciPy
应用：工程优化、资源受限调度
```

### 2.5 全局优化

```
问题：非凸函数、多局部极值的全局最优
数学：global min f(x)
工具：scipy.optimize.differential_evolution / basinhopping / shgo
来源：SciPy
应用：复杂系统参数调优、黑箱优化
```

### 2.6 分配问题

```
问题：将 n 个任务分配给 n 个代理，最小化总成本
数学：min Σ c_ij x_ij
工具：scipy.optimize.linear_sum_assignment
来源：SciPy
应用：任务调度、匹配问题
```

---

## 三、拟合与回归

### 3.1 非线性曲线拟合

```
问题：给定数据 (x_i, y_i)，寻找 f(x; params) 最优参数
数学：min_θ Σ (y_i - f(x_i; θ))^2
工具：scipy.optimize.curve_fit
来源：SciPy
应用：趋势预测、增长率估计、经验公式标定
```

### 3.2 多项式拟合

```
问题：用多项式逼近数据
数学：y ≈ a_0 + a_1 x + ... + a_n x^n
工具：numpy.polyfit (传统) / numpy.polynomial.polynomial.polyfit
来源：NumPy
应用：趋势分析、数据平滑
```

### 3.3 线性回归

```
问题：线性关系 y = ax + b
数学：OLS (Ordinary Least Squares)
工具：scipy.stats.linregress
来源：SciPy
应用：相关性分析、简单预测
```

---

## 四、积分与微分方程

### 4.1 定积分

```
问题：计算曲线下面积
数学：∫_a^b f(x) dx
工具：scipy.integrate.quad
来源：SciPy
应用：概率计算、期望值、面积/体积
```

### 4.2 多重积分

```
问题：二维/三维区域积分
数学：∬ f(x,y) dxdy
工具：scipy.integrate.dblquad / tplquad / nquad
来源：SciPy
应用：质量中心、转动惯量
```

### 4.3 离散数据积分

```
问题：对采样数据积分
数学：梯形法则 / 辛普森法则
工具：scipy.integrate.trapezoid / simpson
来源：SciPy
应用：累计流量、不规则采样数据
```

### 4.4 常微分方程（初值问题）

```
问题：模拟动态系统随时间演化
数学：dy/dt = f(t, y), y(t_0) = y_0
工具：scipy.integrate.solve_ivp
来源：SciPy
应用：SIR 传染病模型、Lotka-Volterra 捕食者-猎物模型、种群动力学
```

### 4.5 常微分方程（边值问题）

```
问题：已知两端条件，求解中间状态
数学：dy/dt = f(t, y), g(y(a), y(b)) = 0
工具：scipy.integrate.solve_bvp
来源：SciPy
应用：稳态温度分布、梁的挠度
```

---

## 五、概率与统计

### 5.1 随机模拟

```
问题：生成随机样本进行 Monte Carlo 模拟
数学：X ~ Distribution(θ)
工具：numpy.random (Generator API): default_rng().normal() / uniform() / ...
来源：NumPy
应用：蒙特卡洛模拟、Bootstrap、随机优化
```

### 5.2 概率分布计算

```
问题：计算 PDF/CDF/PPF
数学：P(X <= x), f(x), F^{-1}(p)
工具：scipy.stats.norm.pdf / cdf / ppf (及其他 100+ 分布)
来源：SciPy
应用：置信区间、分位数、概率建模
```

### 5.3 描述性统计

```
问题：数据基本特征
数学：均值、标准差、峰度、偏度、分位数
工具：scipy.stats.describe / zscore / skew / kurtosis / iqr
来源：SciPy
应用：数据探索、异常检测
```

### 5.4 假设检验（参数检验）

```
问题：判断两组数据是否有显著差异
数学：t-test, F-test
工具：scipy.stats.ttest_ind / ttest_1samp / f_oneway
来源：SciPy
应用：实验效果评估、模型对比
```

### 5.5 假设检验（非参数检验）

```
问题：不假设数据分布的比较
数学：Mann-Whitney U, Kruskal-Wallis
工具：scipy.stats.mannwhitneyu / kruskal / wilcoxon
来源：SciPy
应用：非正态数据比较、排序数据
```

### 5.6 相关性检验

```
问题：变量间的关系强度和显著性
数学：Pearson r, Spearman ρ
工具：scipy.stats.pearsonr / spearmanr
来源：SciPy
应用：变量筛选、关系探索
```

### 5.7 分布检验

```
问题：判断数据是否符合某分布
数学：K-S test, Shapiro-Wilk
工具：scipy.stats.kstest / shapiro / normaltest
来源：SciPy
应用：模型假设验证（如正态性检验）
```

---

## 六、数值计算辅助

### 6.1 插值

```
问题：通过已知点估计未知点的值
数学：分段/样条插值
工具：scipy.interpolate.interp1d / CubicSpline / griddata
来源：SciPy
应用：数据补全、平滑、重采样
```

### 6.2 方程求根

```
问题：求解 f(x) = 0
数学：f(x) = 0
工具：scipy.optimize.root_scalar (brentq / newton / bisect) / root
来源：SciPy
应用：平衡点、临界值、盈亏平衡分析
```

### 6.3 数值微分

```
问题：计算函数在某点的导数
数学：f'(x)
工具：scipy.differentiate.derivative / numpy.gradient
来源：SciPy / NumPy
应用：灵敏度分析、边际分析
```

### 6.4 稀疏矩阵

```
问题：大规模稀疏系统的高效计算
数学：Ax=b where A is sparse
工具：scipy.sparse + scipy.sparse.linalg.spsolve
来源：SciPy
应用：大规模网络、有限元方法
```

---

## 快速索引（按问题类型）

| 问题关键词 | 跳转到 |
|-----------|--------|
| 方程组、线性系统、Ax=b | §1.1 |
| 矩阵分解、SVD、PCA | §1.3 |
| 优化、最大、最小、约束 | §2.x |
| 分配、匹配、调度 | §2.6 |
| 拟合、回归、预测 | §3.x |
| 积分、面积 | §4.x |
| 微分方程、动态系统 | §4.4 |
| 概率、分布 | §5.1 |
| 统计检验、显著性 | §5.4 |
| 插值、补全 | §6.1 |
| 求根、零点 | §6.2 |
