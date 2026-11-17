"""
案例2：线性规划优化 — 工厂生产计划

问题背景：
   某工厂生产 A、B 两种产品：
   - 每件 A：利润 300 元，耗 2kg 钢材 + 3 工时
   - 每件 B：利润 200 元，耗 4kg 钢材 + 1 工时
   现有资源：钢材 100kg，工时 80 小时
   目标：最大化利润

数学模型：
   决策变量: x_A, x_B (≥ 0)
   目标函数: max 300x_A + 200x_B
            等价于 min -300x_A - 200x_B
   约束条件:
       2x_A + 4x_B ≤ 100  (钢材)
       3x_A + 1x_B ≤  80  (工时)

方法选择：
   scipy.optimize.linprog — 线性规划标准求解器
   使用 HiGHS 方法（method='highs'），速度快、精度高

来源：SciPy (https://github.com/scipy/scipy)
"""
import numpy as np
from scipy.optimize import linprog

print("=" * 60)
print("案例2：线性规划优化 — 工厂生产计划")
print("=" * 60)

# ---- 1. 问题定义 ----
# 目标函数系数（linprog 默认最小化，所以取负）
c = [-300, -200]  # min -300x_A - 200x_B

# 不等式约束 A_ub @ x <= b_ub
A_ub = [[2, 4],   # 2x_A + 4x_B <= 100
        [3, 1]]   # 3x_A + 1x_B <= 80
b_ub = [100, 80]

# 变量边界 x >= 0
bounds = [(0, None), (0, None)]

print(f"\n【问题描述】")
print(f"产品A: 利润300元, 耗2kg钢+3工时")
print(f"产品B: 利润200元, 耗4kg钢+1工时")
print(f"资源: 钢材100kg, 工时80h")

# ---- 2. 求解 ----
result = linprog(c, A_ub=A_ub, b_ub=b_ub,
                 bounds=bounds, method='highs')

# ---- 3. 结果 ----
print(f"\n【最优方案】")
print(f"产���A产量: {result.x[0]:.1f} 件")
print(f"产品B产量: {result.x[1]:.1f} 件")
print(f"最大利润: {-result.fun:.0f} 元")
print(f"求解状态: {'成功' if result.success else '失败'}")

# ---- 4. 资源消耗验证 ----
steel_used = 2 * result.x[0] + 4 * result.x[1]
labor_used = 3 * result.x[0] + 1 * result.x[1]

print(f"\n【资源使用】")
print(f"钢材: {steel_used:.1f} / 100 kg ({steel_used/100*100:.1f}%)")
print(f"工时: {labor_used:.1f} / 80 h ({labor_used/80*100:.1f}%)")

# ---- 5. 灵敏度分析 ----
print(f"\n【灵敏度分析 — 目标系数变化范围】")
# 分析：如果产品A利润从300变化，最优方案何时改变？
for profit_A in [250, 280, 300, 320, 350]:
    c_test = [-profit_A, -200]
    r = linprog(c_test, A_ub=A_ub, b_ub=b_ub,
                bounds=bounds, method='highs')
    print(f"  A利润={profit_A:3d}元 → x_A={r.x[0]:.1f}, x_B={r.x[1]:.1f}, 总利润={-r.fun:.0f}")

print("\n✅ 案例2完成：线性规划优化")
print(f"   方法：scipy.optimize.linprog (HiGHS 求解器)")
print(f"   建模价值：资源分配、生产规划、投资组合")
