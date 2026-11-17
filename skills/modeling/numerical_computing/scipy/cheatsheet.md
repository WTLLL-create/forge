# SciPy 速查表

## optimize

| 操作 | 代码 | 备注 |
|------|------|------|
| 通用最小化 | `minimize(f, x0, method='...')` | 14种算法可选 |
| 线性规划 | `linprog(c, A_ub, b_ub)` | method='highs' |
| 曲线拟合 | `curve_fit(f, x, y, p0)` | 返回参数+协方差 |
| 最小二乘 | `least_squares(res, x0)` | 比curve_fit灵活 |
| 全局最优 | `differential_evolution(f, bounds)` | 不需求导 |
| 标量优化 | `minimize_scalar(f)` | 一维搜索 |
| 标量求根 | `root_scalar(f, bracket=[a,b])` | brentq方法 |
| 方程组求根 | `root(F, x0)` | 多维 |

## integrate

| 操作 | 代码 | 备注 |
|------|------|------|
| 定积分 | `quad(f, a, b)` | 返回 (值, 误差) |
| 二重积分 | `dblquad(f, x1, x2, y1, y2)` | |
| 离散积分(梯形) | `trapezoid(y, x=x)` | 已有采样点 |
| 离散积分(辛普森) | `simpson(y, x=x)` | 更精确 |
| ODE初值 | `solve_ivp(f, [t0,te], y0, t_eval=t)` | 推荐API |
| ODE边值 | `solve_bvp(f, bc, x, y_g)` | 边界条件 |

## linalg

| 操作 | 代码 | 备注 |
|------|------|------|
| 解方程 | `solve(A, b)` | 替代 np.linalg |
| LU分解 | `lu(A)` | |
| QR分解 | `qr(A)` | |
| Cholesky | `cholesky(A)` | 对称正定 |
| SVD | `svd(A)` | |
| 矩阵指数 | `expm(A)` | 微分方程解析解 |
| 伪逆 | `pinv(A)` | |
| 零空间 | `null_space(A)` | |
| 正交基 | `orth(A)` | |

## stats

| 操作 | 代码 | 备注 |
|------|------|------|
| PDF | `norm.pdf(x, loc, scale)` | 适用所有分布 |
| CDF | `norm.cdf(x)` | P(X<=x) |
| 分位数 | `norm.ppf(q)` | 逆CDF |
| 描述统计 | `describe(data)` | 一次性输出 |
| 标准化 | `zscore(data)` | Z分数 |
| t检验 | `ttest_ind(g1, g2)` | 独立双样本 |
| 单样本t | `ttest_1samp(d, mu)` | |
| 方差分析 | `f_oneway(g1,g2,g3)` | |
| U检验 | `mannwhitneyu(g1,g2)` | 非参数 |
| Kruskal | `kruskal(g1,g2,g3)` | 非参数ANOVA |
| Pearson r | `pearsonr(x, y)` | 线性相关 |
| Spearman | `spearmanr(x, y)` | 秩相关 |
| 正态性 | `normaltest(data)` | 基于偏度+峰度 |
| Shapiro | `shapiro(data)` | 小样本首选 |
| KS检验 | `kstest(data, 'norm')` | |
| 线性回归 | `linregress(x, y)` | 简单OLS |
