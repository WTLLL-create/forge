"""
案例1：线性方程组求解 — 电路网络分析

问题背景：
   一个直流电路网络中，需要求解各支路电流。已知三个回路的
   基尔霍夫电压定律方程，组成 3x3 线性系统。

数学模型：
   12I₁ -  4I₂ -  3I₃ =  12
   -4I₁ + 10I₂ -  2I₃ =  -8
   -3I₁ -  2I₂ +  8I₃ =  15

   矩阵形式：A·I = V，其中 A 为电阻矩阵，I 为电流向量

方法选择：
   numpy.linalg.solve — 方阵且可逆时最高效的求解器
   内部使用 LU 分解，精度和速度都优于先求逆再乘

来源：NumPy (https://github.com/numpy/numpy)
"""
import numpy as np

print("=" * 60)
print("案例1：线性方程组求解 — 电路网络分析")
print("=" * 60)

# ---- 1. 问题定义 ----
# 电阻矩阵 A (单位: Ω)
A = np.array([
    [12, -4, -3],
    [-4, 10, -2],
    [-3, -2,  8]
])

# 电压向量 V (单位: V)
V = np.array([12, -8, 15])

print(f"\n【已知】")
print(f"电阻矩阵 A =\n{A}")
print(f"电压向量 V = {V}")

# ---- 2. 求解 ----
I = np.linalg.solve(A, V)

print(f"\n【求解结果】")
print(f"电流 I₁ = {I[0]:.3f} A")
print(f"电流 I₂ = {I[1]:.3f} A")
print(f"电流 I₃ = {I[2]:.3f} A")

# ---- 3. 验证 ----
# 验证 A·I 是否等于 V
V_check = A @ I
error = np.max(np.abs(V_check - V))

print(f"\n【验证】")
print(f"A·I = {V_check}")
print(f"给定 V = {V}")
print(f"最大残差 = {error:.2e}")

# ---- 4. 额外分析 ----
# 条件数：衡量病态程度，< 1e3 为良态
cond = np.linalg.cond(A)
det = np.linalg.det(A)
print(f"\n【矩阵分析】")
print(f"行列式 det(A) = {det:.2f}")
print(f"条件数 cond(A) = {cond:.2f}")
if cond < 100:
    print("结论：矩阵良态，解可靠")
elif cond < 1000:
    print("结论：矩阵条件数中等，解基本可靠")
else:
    print("警告：矩阵接近奇异，解可能不稳定")

print("\n✅ 案例1完成：线性方程组求解")
print(f"   方法：numpy.linalg.solve (基于 LU 分解)")
print(f"   建模价值：参数估计、平衡模型、网络分析")
