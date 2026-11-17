# DEAP 完整参考 — 数模进化算法/遗传算法

> 来源：DEAP/deap（GitHub ~6.3k stars, LGPL-3.0）
> 蒸馏自官方 Overview + API 文档
> 服务于 S4 (SOLVING) 遗传算法/NSGA-II多目标优化

---

## 一、DEAP 定位

Python 进化计算框架。**不限定算法，提供积木让你自己搭。**

```
安装：pip install deap
核心：Toolbox(工具箱) + creator(动态类型) + algorithms(标准算法)
```

---

## 二、三步搭建遗传算法

### 步骤 1：创建类型（creator）

```python
from deap import base, creator

# 适应度：最小化问题 weights=(-1.0,)，最大化 weights=(1.0,)
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)
```

### 步骤 2：注册操作（Toolbox）

```python
import random
from deap import tools

toolbox = base.Toolbox()

# 初始化
toolbox.register("attr_float", random.random)
toolbox.register("individual", tools.initRepeat, creator.Individual,
                 toolbox.attr_float, n=10)     # 10个基因
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# 适应度函数
def evaluate(individual):
    # 例如：最小化 sum(x_i²)
    return sum(x**2 for x in individual),

toolbox.register("evaluate", evaluate)

# 遗传算子
toolbox.register("mate", tools.cxTwoPoint)                     # 两点交叉
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.1)  # 高斯变异
toolbox.register("select", tools.selTournament, tournsize=3)   # 锦标赛选择
```

### 步骤 3：运行进化

```python
pop = toolbox.population(n=50)
fitnesses = list(map(toolbox.evaluate, pop))
for ind, fit in zip(pop, fitnesses):
    ind.fitness.values = fit

CXPB, MUTPB, NGEN = 0.5, 0.2, 40

for g in range(NGEN):
    # 选择
    offspring = toolbox.select(pop, len(pop))
    offspring = list(map(toolbox.clone, offspring))

    # 交叉
    for child1, child2 in zip(offspring[::2], offspring[1::2]):
        if random.random() < CXPB:
            toolbox.mate(child1, child2)
            del child1.fitness.values
            del child2.fitness.values

    # 变异
    for mutant in offspring:
        if random.random() < MUTPB:
            toolbox.mutate(mutant)
            del mutant.fitness.values

    # 重评估
    invalid = [ind for ind in offspring if not ind.fitness.valid]
    fitnesses = map(toolbox.evaluate, invalid)
    for ind, fit in zip(invalid, fitnesses):
        ind.fitness.values = fit

    pop[:] = offspring

# 最优个体
best = tools.selBest(pop, 1)[0]
print(f"最优适应度: {best.fitness.values}")
```

---

## 三、内置标准算法（快速调用）

```python
from deap import algorithms

# 简单遗传算法
algorithms.eaSimple(pop, toolbox, cxpb=0.5, mutpb=0.2, ngen=40)

# (μ+λ) 进化策略
algorithms.eaMuPlusLambda(pop, toolbox, mu=50, lambda_=100, cxpb=0.5, mutpb=0.2, ngen=40)

# (μ,λ) 进化策略
algorithms.eaMuCommaLambda(pop, toolbox, mu=50, lambda_=100, cxpb=0.5, mutpb=0.2, ngen=40)
```

---

## 四、遗传算子速查

### 选择 (selection)

```python
tools.selTournament(individuals, k, tournsize=3)     # 锦标赛（最常用）
tools.selRoulette(individuals, k)                     # 轮盘赌
tools.selBest(individuals, k)                         # 精英选择
tools.selNSGA2(population, k)                         # NSGA-II 非支配排序
```

### 交叉 (crossover)

```python
tools.cxOnePoint(ind1, ind2)       # 单点交叉
tools.cxTwoPoint(ind1, ind2)       # 两点交叉
tools.cxUniform(ind1, ind2, indpb=0.5)  # 均匀交叉
tools.cxBlend(ind1, ind2, alpha=0.5)   # 混合交叉（实数）
tools.cxSimulatedBinary(ind1, ind2, eta=20)  # SBX（实数，NSGA-II标配）
```

### 变异 (mutation)

```python
tools.mutGaussian(ind, mu=0, sigma=1, indpb=0.1)  # 高斯变异
tools.mutFlipBit(ind, indpb=0.05)                   # 位翻转变异（0-1问题）
tools.mutUniformInt(ind, low, up, indpb=0.1)        # 均匀整数变异
tools.mutPolynomialBounded(ind, eta=20, low, up, indpb=0.1)  # 多项式变异（NSGA-II标配）
```

---

## 五、多目标优化 (NSGA-II)

```python
# 适应度：多目标 weights=(-1.0, -1.0) 表示两目标都最小化
creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))
creator.create("Individual", list, fitness=creator.FitnessMulti)

def evaluate(individual):
    f1 = objective_1(individual)   # 目标1：最小化成本
    f2 = objective_2(individual)   # 目标2：最小化排放
    return f1, f2

toolbox.register("evaluate", evaluate)
toolbox.register("select", tools.selNSGA2)  # NSGA-II 非支配排序选择

# 运行
pop = toolbox.population(n=100)
algorithms.eaMuPlusLambda(pop, toolbox, mu=100, lambda_=200,
                          cxpb=0.7, mutpb=0.3, ngen=200)

# 提取 Pareto 前沿
pareto_front = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
```

---

## 六、数据结构自适应

```python
# 列表型个体（连续优化）
creator.create("Individual", list, fitness=creator.FitnessMin)
toolbox.register("attr_float", random.uniform, -5, 5)

# 集合型个体（组合优化，如 TSP）
creator.create("Individual", set, fitness=creator.FitnessMin)
toolbox.register("attr_int", random.randint, 0, 100)

# NumPy 数组型个体
import numpy as np
creator.create("Individual", np.ndarray, fitness=creator.FitnessMin)
```

---

## 七、统计与日志

```python
stats = tools.Statistics(lambda ind: ind.fitness.values)
stats.register("avg", np.mean)
stats.register("std", np.std)
stats.register("min", np.min)
stats.register("max", np.max)

pop, logbook = algorithms.eaSimple(pop, toolbox, cxpb=0.5, mutpb=0.2,
                                   ngen=40, stats=stats)
print(logbook)

# Hall of Fame（保存历史最优）
hof = tools.HallOfFame(1)
pop, logbook = algorithms.eaSimple(pop, toolbox, cxpb=0.5, mutpb=0.2,
                                   ngen=40, stats=stats, halloffame=hof)
print(f"最优解: {hof[0]}, 适应度: {hof[0].fitness.values}")
```

---

## 八、数模模板：DEAP + Scipy 混用

```python
# DEAP 搜索架构参数 → Scipy/Fitness 评估复杂模型
def evaluate(individual):
    param1, param2 = individual[0], individual[1]
    # 用 SciPy 求解器评估
    result = minimize(my_model, x0=[...], args=(param1, param2))
    return result.fun,  # 返回目标值
```

---

## 九、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| fitness 返回非元组 | TypeError | `return val,`（注意逗号） |
| 交叉后 fitness 未清除 | 适应度不准 | 交叉/变异后 `del ind.fitness.values` |
| 收敛过早 | 种群多样性丧失 | 增大变异率 `mutpb`，增大种群 |
| 实数编码用错交叉 | 后代不收敛 | 实数用 `cxSimulatedBinary` 不用 `cxTwoPoint` |
| 多目标 weights 反了 | 最小化变成最大化 | weights=(-1.0, -1.0) 表示两目标都最小化 |
