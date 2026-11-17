# OR-Tools 完整参考 — 数模组合优化求解

> 来源：google/or-tools（GitHub ~13.5k stars, Apache-2.0）
> 蒸馏自官方 README + Python API 文档
> 服务于 S4 (SOLVING) 路径规划/调度/约束满足

---

## 一、OR-Tools 定位

Google 的运筹优化工具套件。数模中最强大的**组合优化**求解器。

```
安装：pip install ortools
包含：CP-SAT约束编程 + 线性求解(GLoP/PDLP) + 路径规划(VRP/TSP) + 图算法
```

---

## 二、三套 API 选择

| API | 导入 | 适用问题 |
|-----|------|----------|
| **CP-SAT** | `ortools.sat.python.cp_model` | 整数变量、约束满足、调度（最推荐） |
| **Linear Solver** | `ortools.linear_solver.pywraplp` | 线性/混合整数规划 |
| **Routing** | `ortools.constraint_solver` | TSP/VRP 路径规划 |

---

## 三、CP-SAT — 数模最常用

### 基本模式

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()

# 1. 创建变量
x = model.NewIntVar(0, 100, 'x')
y = model.NewIntVar(0, 100, 'y')
z = model.NewBoolVar('z')       # 0-1 变量

# 2. 添加约束
model.Add(x + y <= 50)           # 线性
model.Add(x != y)                # 不等
model.AddAllDifferent([x, y])    # 互异
model.Add(x + y * z >= 10)       # 含布尔变量

# 3. 设置目标
model.Maximize(3 * x + 2 * y)
# model.Minimize(x + y)

# 4. 求解
solver = cp_model.CpSolver()
status = solver.Solve(model)

# 5. 输出
if status == cp_model.OPTIMAL:
    print(f"x={solver.Value(x)}, y={solver.Value(y)}")
    print(f"目标值={solver.ObjectiveValue()}")
```

### 状态码

| 状态 | 含义 |
|------|------|
| `cp_model.OPTIMAL` | 最优解 |
| `cp_model.FEASIBLE` | 可行解（不定最优） |
| `cp_model.INFEASIBLE` | 不可行 |
| `cp_model.UNKNOWN` | 超时/未找到 |

### 常用约束

```python
model.Add(x + y <= 10)                   # 线性不等式
model.Add(x != y)                         # 不等于
model.AddAllDifferent([x, y, z])          # 互不相同
model.AddLinearConstraint(2*x + 3*y, 5, 10)  # 5 <= 2x+3y <= 10

# 逻辑约束（若 z 则 x >= y）
model.Add(x >= y).OnlyEnforceIf(z)
model.Add(x < y).OnlyEnforceIf(z.Not())

# 区间变量（调度）
job = model.NewIntervalVar(start, duration, end, 'job')
```

### 枚举所有解

```python
class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def on_solution_callback(self):
        print(f"x={self.Value(x)}, y={self.Value(y)}")

solver.parameters.enumerate_all_solutions = True
solver.Solve(model, SolutionPrinter())
```

---

## 四、Linear Solver — 线性/混合整数规划

```python
from ortools.linear_solver import pywraplp

solver = pywraplp.Solver.CreateSolver('GLOP')  # 或 'SCIP' 整数

# 变量
x = solver.NumVar(0, 1, 'x')     # 连续 [0,1]
y = solver.IntVar(0, 10, 'y')    # 整数 [0,10]

# 约束
ct = solver.Constraint(0, 10, 'ct')  # 0 <= ... <= 10
ct.SetCoefficient(x, 2)
ct.SetCoefficient(y, 3)

# 目标
obj = solver.Objective()
obj.SetCoefficient(x, 3)
obj.SetCoefficient(y, 1)
obj.SetMaximization()  # 或 obj.SetMinimization()

# 求解
status = solver.Solve()
print(f"x={x.solution_value()}, y={y.solution_value()}")
print(f"目标={solver.Objective().Value()}")
```

**求解器后端**：`GLOP`(线性)/`SCIP`(MIP)/`CP-SAT`(整数)/`CLP`/`GLPK`

---

## 五、Routing — 路径规划

```python
from ortools.constraint_solver import routing_enums_pb2, pywrapcp

# 距离矩阵
data = {'distance_matrix': [[...], [...], ...], 'num_vehicles': 2, 'depot': 0}
manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                        data['num_vehicles'], data['depot'])
routing = pywrapcp.RoutingModel(manager)

def distance_callback(from_idx, to_idx):
    return data['distance_matrix'][manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]

routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(distance_callback))
solution = routing.Solve()
```

---

## 六、数模场景速查

| 我需要... | OR-Tools API |
|-----------|-------------|
| 0-1 决策变量（是/否） | `cp_model.NewBoolVar()` |
| 资源分配/调度 | CP-SAT `NewIntervalVar` + Constraints |
| 线性规划 | `pywraplp.Solver.CreateSolver('GLOP')` |
| 混合整数规划 | `pywraplp.Solver.CreateSolver('SCIP')` |
| TSP/VRP 路径规划 | RoutingModel |
| 互斥约束 | `AddAllDifferent()` 或 `OnlyEnforceIf()` |
| 最小/最大目标 | `model.Minimize()` / `model.Maximize()` |

---

## 七、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| CP-SAT 只支持整数 | 小数报错 | 乘以倍数转整数（×100, ×1000） |
| 变量范围过大 | 求解极慢 | 用领域知识缩小范围 |
| 忘记设置目标 | 解随机/只求可行 | 必须调用 Minimize/Maximize |
| SCIP 需额外安装 | ImportError | 用 GLOP 或 CP-SAT 代替 |
| 模型不可行 | 返回 INFEASIBLE | 逐一放宽约束定位矛盾 |
