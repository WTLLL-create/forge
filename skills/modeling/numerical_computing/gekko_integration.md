# GEKKO 参考 — 数模复杂动态优化

> 来源：BYU-PRISM/GEKKO（GitHub ~702 stars, MIT）
> 蒸馏自官方 README + API 文档
> 服务于 S4 动态优化/微分方程/非线性 MPC

---

## 一、定位

```
SciPy optimize → 静态优化（参数优化）
CVXPY          → 凸优化（自动验证凸性）
GEKKO          → 动态优化 + 微分代数方程 + 混合整数
```

专门解决含**微分方程约束**的优化问题。数模中适用于：
- 化学反应动力学优化
- 控制参数动态优化
- 参数估计与数据调和

```
安装：pip install gekko
```

---

## 二、9 种运行模式 (imode)

| 模式 | 说明 | 场景 |
|------|------|------|
| SS (1) | 稳态仿真 | 定常系统 |
| MPU (2) | 参数估计/数据调和 | 从数据标定模型参数 |
| RTO (3) | 实时优化 | 在线最优控制 |
| SIM (4) | 动态仿真 | 看系统如何随时间变化 |
| EST (5) | 移动水平估计 | 状态估计 |
| CTL (6) | 非线性控制/动态优化 | **数模最常用** |
| SQS (7) | 序贯动态仿真 | 逐时间步求解 |
| SQE (8) | 序贯动态估计 | 序贯参数更新 |
| SQO (9) | 序贯动态优化 | 分步全局优化 |

---

## 三、基本模式

```python
from gekko import GEKKO
import numpy as np

m = GEKKO(remote=False)  # local=False 用远程高性能服务器

# 变量
x = m.Var(value=0, lb=0)       # 状态变量
u = m.MV(value=1, lb=0, ub=100) # 操作变量（控制量）
u.STATUS = 1                    # 允许优化器调整
p = m.Param(value=5)            # 固定参数

# 方程（微分方程）
m.Equation(x.dt() == -x + u)   # dx/dt = -x + u

# 目标函数
m.Obj(x**2)                     # 最小化 x²

# 时间离散
m.time = np.linspace(0, 10, 101)

# 求解
m.options.IMODE = 6  # 动态优化模式
m.solve()

# 结果
print(x.value)
```

---

## 四、关键变量类型

```python
# 状态变量
x = m.Var(value=0, lb=-10, ub=10)

# 操作变量/控制变量
u = m.MV(value=1, lb=0, ub=100)
u.STATUS = 1    # 可以被优化器改变
u.DCOST = 0.1   # 控制变化惩罚（平滑控制）

# 固定参数
p = m.Param(value=5)

# 固定变量（常数）
c = m.Const(3.14)

# 中间变量
y = m.Intermediate(x**2 + u)

# 整数变量
z = m.Var(value=0, lb=0, ub=10, integer=True)
```

---

## 五、关键方程类型

```python
# 代数方程
m.Equation(x + y == 10)

# 微分方程
m.Equation(x.dt() == -k * x)

# 不等式
m.Equation(x * y >= 5)

# 目标函数
m.Minimize(x**2 + u**2)       # 最小化
m.Maximize(profit)             # 最大化

# 终端约束
m.Equation(x * m.time == m.time[-1])  # 只在最终时刻生效
```

---

## 六、求解器选择

```python
m.options.SOLVER = 1  # APOPT (默认，MINLP)
# 1=APOPT, 2=BPOPT, 3=IPOPT
```

---

## 七、数模模板：反应器控制优化

```python
from gekko import GEKKO
import numpy as np

m = GEKKO(remote=False)
m.time = np.linspace(0, 100, 101)

# 状态
T = m.Var(value=300)      # 温度
C = m.Var(value=1.0)      # 浓度

# 控制
Q = m.MV(value=0, lb=-50, ub=50)  # 加热/冷却功率
Q.STATUS = 1
Q.DCOST = 0.01

# 动力学
k = 0.1  # 反应速率常数
m.Equation(C.dt() == -k * C * m.exp(-1000/T))
m.Equation(T.dt() == 0.1 * Q - 0.05 * (T - 300))

# 优化目标：最大转化率
m.Obj(-C)

m.options.IMODE = 6
m.solve()
```

---

## 八、论文输出模板

```python
m.solve()

# 关键结果
print(f"最终转化率: {C.value[-1]:.4f}")
print(f"控制总能耗: {np.sum(np.abs(Q.value)):.2f}")

# 论文叙述：
# "使用 GEKKO 动态优化框架，在 IMODE=6 模式下求解非线性 MPC 问题。
# 优化后转化率提升 X%，控制能耗降低 Y%。"
```

---

## 九、常见坑

| 坑 | 解决 |
|----|------|
| 求解不收敛 | 调整初始值 + 收紧边界，或换 SOLVER=3 (IPOPT) |
| 微分方程写法错误 | `x.dt()` 不是 `dx/dt` |
| remote=True 需网络 | 设 `remote=False` 本地求解 |
| MV 变量忘记设 STATUS=1 | 优化器不会调整该变量 |
| DCOST 设太小 | 控制变量抖动剧烈，适当增大 |
