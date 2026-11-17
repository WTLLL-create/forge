# PuLP 完整参考 — 数模线性规划快速建模

> 来源：coin-or/pulp（GitHub ~2.4k stars, MIT）
> 蒸馏自官方 README + PyPI 文档
> 服务于 S4 (SOLVING) 线性规划/整数规划快速原型

---

## 一、PuLP 定位

```
SciPy.linprog → 矩阵形式，简单直接
CVXPY        → 数学表达，自动验证凸性
PuLP         → 最接近教学写法："x + 2y <= 10" 直接写
```

- COIN-OR 项目，支持 CBC/GLPK/SCIP/Gurobi/CPLEX 等求解器
- Python 建模语法直观，适合数模比赛快速原型

```
安装：pip install pulp[cbc]  # 含默认求解器CBC
```

---

## 二、核心 API

### 五个核心类

| 类 | 用途 |
|----|------|
| `LpProblem` | 容器：问题定义 |
| `LpVariable` | 决策变量 |
| `LpConstraint` | 约束条件 |
| `lpSum` | 求和表达式 |
| `lpDot` | 点积表达式 |

### 基本模式

```python
from pulp import *

# 1. 创建问题
prob = LpProblem("My_Problem", LpMinimize)  # 或 LpMaximize

# 2. 定义变量
x = LpVariable('x', lowBound=0, cat='Continuous')      # 连续
y = LpVariable('y', lowBound=0, upBound=100, cat='Integer')  # 整数
z = LpVariable('z', cat='Binary')                      # 0-1

# 3. 目标函数
prob += 3 * x + 2 * y

# 4. 添加约束（用 += 追加）
prob += x + y <= 50
prob += 2 * x + 4 * y >= 60
prob += x - y == 0

# 5. 求解
prob.solve()

# 6. 输出
print(f"状态: {LpStatus[prob.status]}")
print(f"目标值: {value(prob.objective)}")
print(f"x = {value(x)}, y = {value(y)}")
```

---

## 三、变量类型

```python
x = LpVariable(name, lowBound, upBound, cat)

# cat 选项：
# 'Continuous' — 连续（默认）
# 'Integer'    — 整数
# 'Binary'     — 0-1 变量
```

---

## 四、批量创建变量

```python
# 列表推导
x = [LpVariable(f'x_{i}', lowBound=0) for i in range(10)]

# 字典 + 列表推导
ingredients = ['chicken', 'beef', 'mutton', 'rice']
costs = {'chicken': 0.013, 'beef': 0.008, 'mutton': 0.010, 'rice': 0.002}
x = LpVariable.dicts('x', ingredients, lowBound=0)

# 多索引
routes = [(i, j) for i in range(3) for j in range(3)]
x = LpVariable.dicts('route', routes, cat='Binary')
```

---

## 五、约束批量写法

```python
# lpSum 求和
prob += lpSum(x[i] for i in range(n)) == 1

# lpDot 点积
prob += lpDot(costs, [x[i] for i in ingredients]) <= budget

# 多重约束
for j in range(m):
    prob += lpSum(x[i] for i in range(n) if condition) <= supply[j]
```

---

## 六、完整数模模板

### 运输问题

```python
from pulp import *

# 数据
supply = [20, 30, 25]       # 3个产地
demand = [10, 15, 20, 30]   # 4个销地
cost = [[8, 6, 10, 9], [9, 12, 13, 7], [14, 9, 16, 5]]

m, n = len(supply), len(demand)

# 变量
routes = [(i, j) for i in range(m) for j in range(n)]
x = LpVariable.dicts('x', routes, lowBound=0, cat='Integer')

# 问题
prob = LpProblem("Transportation", LpMinimize)
prob += lpSum(cost[i][j] * x[i,j] for i,j in routes)

# 供应约束
for i in range(m):
    prob += lpSum(x[i,j] for j in range(n)) <= supply[i]

# 需求约束
for j in range(n):
    prob += lpSum(x[i,j] for i in range(m)) >= demand[j]

prob.solve()
print(f"最低成本: {value(prob.objective)}")
```

### 指派问题

```python
n = 4
workers = range(n)
tasks = range(n)
cost = [[...], [...], [...], [...]]  # 成本矩阵

x = LpVariable.dicts('assign', [(i,j) for i in workers for j in tasks], cat='Binary')

prob = LpProblem("Assignment", LpMinimize)
prob += lpSum(cost[i][j] * x[i,j] for i in workers for j in tasks)

for i in workers:
    prob += lpSum(x[i,j] for j in tasks) == 1   # 每人一个任务
for j in tasks:
    prob += lpSum(x[i,j] for i in workers) == 1  # 每个任务一个人

prob.solve()
```

---

## 七、求解状态

```python
LpStatus[prob.status]
# 'Optimal'     — 找到最优解
# 'Not Solved'  — 未求解
# 'Infeasible'  — 不可行
# 'Unbounded'   — 无界
# 'Undefined'   — 未定义
```

---

## 八、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| 没有求解器 | `PulpError: No solver available` | `pip install pulp[cbc]` |
| 变量类型不匹配 | 整数解不是整数 | 设 `cat='Integer'` 而非 `Continuous` |
| 大规模问题慢 | 求解超时 | 换 Gurobi/CPLEX 或降规模 |
| 约束冲突 | Infeasible | 逐一松弛约束找矛盾 |
| += 忘了 | 目标/约束没加上 | 每次都用 `prob += ...` |
