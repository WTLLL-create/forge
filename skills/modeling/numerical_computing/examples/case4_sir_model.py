"""
案例4：SIR 微分方程模拟 — 传染病传播动力学

问题背景：
   10000 人的封闭群体中爆发传染病。
   初始感染者 10 人，康复者 0 人，易感者 9990 人。
   传染率 β = 0.3，康复率 γ = 0.1。
   模拟未来 160 天的传播过程。

数学模型 (SIR Model, Kermack-McKendrick 1927):
   dS/dt = -β·S·I / N           （易感者减少 = 被感染）
   dI/dt =  β·S·I / N - γ·I     （感染者变化 = 新增 - 康复）
   dR/dt =  γ·I                  （康复者增加 = 感染者康复）

   其中 N = S + I + R = 10000（总人口不变）

方法选择：
   scipy.integrate.solve_ivp — ODE 初值问题求解器
   默认 RK45 方法：5(4) 阶自适应步长 Runge-Kutta
   适合非刚性常微分方程系统

来源：SciPy (https://github.com/scipy/scipy)
"""
import numpy as np
from scipy.integrate import solve_ivp

print("=" * 60)
print("案例4：SIR 微分方程模拟 — 传染病传播动力学")
print("=" * 60)

# ---- 1. 参数设置 ----
N = 10000       # 总人口
I0 = 10         # 初始感染者
R0 = 0          # 初始康复者
S0 = N - I0 - R0  # 初始易感者
beta = 0.3      # 传染率（每人每天接触导致的感染数）
gamma = 0.1     # 康复率（1/平均感染期）
t_max = 160     # 模拟天数

print(f"\n【模型参数】")
print(f"  总人口 N = {N}")
print(f"  初始状态: S₀={S0}, I₀={I0}, R₀={R0}")
print(f"  传染率 β = {beta}")
print(f"  康复率 γ = {gamma}")
print(f"  基本再生数 R₀ = {beta/gamma:.1f} (R₀>1 表示疫情扩散)")
print(f"  模拟时长: {t_max} 天")

# ---- 2. 定义 SIR 模型 ----
def sir_model(t, y):
    """
    SIR 模型微分方程
    y = [S, I, R] — 易感者、感染者、康复者
    """
    S, I, R = y
    N_total = S + I + R

    dS = -beta * S * I / N_total
    dI = beta * S * I / N_total - gamma * I
    dR = gamma * I

    return [dS, dI, dR]

# ---- 3. 求解 ----
sol = solve_ivp(sir_model, [0, t_max], [S0, I0, R0],
                method='RK45',
                t_eval=np.linspace(0, t_max, 1000),
                rtol=1e-6, atol=1e-8)

S, I, R = sol.y
t = sol.t

# ---- 4. 关键指标 ----
peak_idx = np.argmax(I)
peak_day = t[peak_idx]
peak_infected = I[peak_idx]

# 最终状态
final_S = S[-1]
final_I = I[-1]
final_R = R[-1]

# 总感染人数
total_infected = N - final_S

print(f"\n【模拟结果】")
print(f"  感染峰值日: 第 {peak_day:.0f} 天")
print(f"  峰值感染人数: {peak_infected:.0f} 人 ({peak_infected/N*100:.1f}%)")
print(f"  最终易感者: {final_S:.0f} 人")
print(f"  总感染人数(累计): {total_infected:.0f} 人 ({total_infected/N*100:.1f}%)")
print(f"  最终感染者: {final_I:.1f} 人 (疫情结束)")

# ---- 5. 模型验证 ----
# 检验总人口守恒
N_error = np.max(np.abs(S + I + R - N))
print(f"\n【模型验证】")
print(f"  人口守恒检验: 最大误差 = {N_error:.2e} {'✓' if N_error < 1e-4 else '⚠'}")

# 检验 dS/dt + dI/dt + dR/dt ≈ 0 (总人口不变)
print(f"  总变化率之和 ≈ 0: ✓ (模型保证)")

# ---- 6. 参数敏感性 ----
print(f"\n【参数敏感性分析 — γ 变化对峰值的影响】")
for gamma_test in [0.05, 0.10, 0.15, 0.20]:
    def sir_test(t, y):
        S, I, R = y
        N_t = S + I + R
        return [-beta*S*I/N_t, beta*S*I/N_t - gamma_test*I, gamma_test*I]

    sol_test = solve_ivp(sir_test, [0, t_max], [S0, I0, R0],
                         t_eval=np.linspace(0, t_max, 500))
    peak = np.max(sol_test.y[1])
    peak_t = sol_test.t[np.argmax(sol_test.y[1])]
    print(f"  γ={gamma_test:.2f} (平均感染{1/gamma_test:.0f}天) "
          f"→ 峰值 {peak:.0f}人 (第{peak_t:.0f}天)")

# ---- 7. 简要文字输出（供论文使用）----
print(f"\n【论文摘要用】")
print(f"  SIR模型模拟表明，在β={beta}、γ={gamma}的条件下，")
print(f"  疫情在第{peak_day:.0f}天达到峰值{peak_infected:.0f}人，")
print(f"  最终{total_infected:.0f}人({total_infected/N*100:.1f}%)被感染。")

print("\n✅ 案例4完成：SIR 微分方程模拟")
print(f"   方法：scipy.integrate.solve_ivp (RK45)")
print(f"   建模价值：传染病建模、种群动力学、系统动力学")
