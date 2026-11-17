"""
案例3：指数增长预测 — 人口数据拟合

问题背景：
   某地区 2010-2025 年人口数据（单位：万人）：
   [102, 106, 110, 115, 121, 127, 133, 139, 145, 152,
    158, 165, 171, 178, 184, 191]
   预测 2030 年人口。

数学模型：
   假设人口遵循 Malthus 指数增长模型：
   P(t) = P₀ * exp(r * t)
   其中 P₀ 为初始人口，r 为增长率，t = year - 2010

   需要将数据拟合到此模型上，求得 P₀ 和 r。

方法选择：
   scipy.optimize.curve_fit — 非线性最小二乘拟合
   适用于能用参数化函数表达的任何拟合问题。
   内部使用 Levenberg-Marquardt 算法（默认）。

来源：SciPy (https://github.com/scipy/scipy)
"""
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats

print("=" * 60)
print("案例3：指数增长预测 — 人口数据拟合")
print("=" * 60)

# ---- 1. 数据准备 ----
years = np.arange(2010, 2026)  # 2010-2025
population = np.array([102, 106, 110, 115, 121, 127, 133, 139,
                       145, 152, 158, 165, 171, 178, 184, 191])
t_data = years - 2010  # 时间变量（年数）

print(f"\n【历史数据】")
for i in range(0, len(years), 4):
    batch = list(zip(years[i:i+4], population[i:i+4]))
    print(f"  " + " | ".join([f"{y}: {p}万" for y, p in batch]))

# ---- 2. 模型定义 ----
def exp_growth(t, P0, r):
    """指数增长模型: P(t) = P0 * exp(r*t)"""
    return P0 * np.exp(r * t)

def logistic_growth(t, K, P0, r):
    """逻辑增长模型（备选）: P(t) = K / (1 + (K/P0-1)*exp(-r*t))"""
    return K / (1 + (K/P0 - 1) * np.exp(-r * t))

# ---- 3. 拟合 ----
# 指数模型拟合
popt_exp, pcov_exp = curve_fit(exp_growth, t_data, population,
                                p0=[100, 0.04])
perr_exp = np.sqrt(np.diag(pcov_exp))

print(f"\n【拟合结果 — 指数模型: P(t) = P₀ * exp(r*t)】")
print(f"  P₀ = {popt_exp[0]:.2f} 万人")
print(f"  r  = {popt_exp[1]:.5f} (±{perr_exp[1]:.5f})")
print(f"  年均增长率: {popt_exp[1]*100:.2f}%")

# ---- 4. 预测 ----
t_pred = 2030 - 2010  # 预测2030年
pop_2030 = exp_growth(t_pred, *popt_exp)

# 置信区间（1σ）
pop_2030_lo = exp_growth(t_pred, popt_exp[0] - perr_exp[0],
                                  popt_exp[1] - perr_exp[1])
pop_2030_hi = exp_growth(t_pred, popt_exp[0] + perr_exp[0],
                                  popt_exp[1] + perr_exp[1])

print(f"\n【2030年预测】")
print(f"  预测人口: {pop_2030:.1f} 万人")
print(f"  1σ 置信区间: [{pop_2030_lo:.1f}, {pop_2030_hi:.1f}] 万人")

# ---- 5. 模型验证 ----
predicted = exp_growth(t_data, *popt_exp)
residuals = population - predicted
ss_res = np.sum(residuals ** 2)
ss_tot = np.sum((population - np.mean(population)) ** 2)
r_squared = 1 - (ss_res / ss_tot)

print(f"\n【模型验证】")
print(f"  R² = {r_squared:.4f}")

# 残差正态性检验（好的拟合残差应近似正态）
stat, p_norm = stats.normaltest(residuals)
print(f"  残差正态性检验: p = {p_norm:.4f} {'✓' if p_norm > 0.05 else '⚠ 残差非正态'}")

# 实际 vs 预测对比
print(f"\n  实际值 vs 预测值:")
for i in range(0, len(years), 4):
    batch_data = [(years[j], population[j], predicted[j], residuals[j])
                  for j in range(i, min(i+4, len(years)))]
    for y, p, pred, res in batch_data:
        print(f"    {y}: {p:3d}万 → {pred:5.1f}万 (残差 {res:+3.1f})")

print("\n✅ 案例3完成：指数增长预测")
print(f"   方法：scipy.optimize.curve_fit (Levenberg-Marquardt)")
print(f"   建模价值：趋势预测、增长率估计、参数标定")
