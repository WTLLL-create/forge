# Strategy Planner Test Cases — 管线验证

> 选取 20.1.5 中的 Router 失败案例 + 一个综合案例，
> 验证 Strategy Planner 能否为它们生成合理的建模管线。

---

## Test 01: 2021C 帕金森DBS — 机理+优化混合

### 输入 (来自 Problem Intelligence)

```
math_essence: "mechanism_then_optimize"
sub_problems: [Q1=mechanism, Q2=optimization]
dependencies: Q1→Q2
candidate_models: Q1=ODE(Runge-Kutta), Q2=参数优化
data_condition: data_size=50, has_noise
```

### 预期管线

```
Pipeline: 模板3(机理+数据) + 模板2(优化) 嵌套

S1: 建立HH神经元ODE → solve_ivp(RK45)
    ↓ 输出: 神经元放电模拟
S2: 校准ODE参数 → curve_fit (用实测数据)
    ↓ 输出: 校准后的ODE模型
S3: DBS参数优化 → minimize (在ODE上优化)
    ↓ 输出: 最优DBS参数
S4: 验证 → 敏感性分析 + 与文献对比
```

### 关键决策点

- ⚠️ Rule C: "优化参数"≠"运筹优化" → 需要先建立ODE
- 管线模板选择: 先模板3(机理)→再模板2(优化的参数调优变体)

---

## Test 02: 2019A 无线传播 — 经验公式+AI校正

### 输入

```
math_essence: "physics_formula_with_ai_correction"
sub_problems: [Q1=经验公式建模, Q2=AI残差校正]
candidate_models: Q1=Okumura-Hata公式, Q2=RF/XGBoost残差
data_condition: data_size=200, has_real_data
```

### 预期管线

```
Pipeline: 模板3(机理+数据) = physics_plus_data 模式

S1: 建立经验公式 → Okumura-Hata (路径损耗预测)
    ↓ 输出: 物理模型预测值
S2: 计算残差 → 实测-物理预测
    ↓ 分析: 残差是否有系统模式
S3: AI校正残差 → RF/XGBoost (特征: 建筑物密度, 街道宽度等)
    ↓ 输出: 残差预测
S4: 组合验证 → 物理 vs 混合 vs 纯AI 三方对比
```

---

## Test 03: 2019E 全球气候 — 多模型对比

### 输入

```
math_essence: "multi_model_comparison_with_causal_background"
sub_problems: [Q1=历史趋势分析, Q2=多模型预测, Q3=极端天气关联, Q4=矛盾解释]
candidate_models: Q2=[线性回归, 随机森林, ARIMA]
data_condition: data_size=200, has_9_factors
```

### 预期管线

```
Pipeline: 模板5(分而治之) + 并行对比

S1: 历史趋势分析 → 气候倾向率+周期性检验
S2: 并行三模型预测
    ├── 线性回归 (解释性, 系数有物理含义)
    ├── 随机森林 (精度, 非线性捕捉)
    └── ARIMA (纯时序, 长期趋势合理)
    ↓ 输出: 三模型对比表
S3: 极端天气关联 → 离群频次→三种模式(A/B/C)
S4: 矛盾解释 → 局地极寒多因子关联模型
```

### 关键决策点

- 不是选最优模型，而是展示模型对比本身的价值
- 论文叙事: "三种模型各有优劣" > "选了一个最好的"

---

## Test 04: 综合案例 — 物流配送路径优化

### 输入

```
math_essence: "network_optimization"
sub_problems: [Q1=需求分析, Q2=路径优化]
candidate_models: Q2=[Dijkstra, 遗传算法, 蚁群算法]
data_condition: data_size=50_nodes, has_discrete, is_path
```

### 预期管线

```
Pipeline: 模板2(优化) 图论变体

S1: 问题建模为图 → 节点=配送点, 边=路径, 权重=距离/时间
    ↓ 输出: 邻接矩阵
S2: 复杂度分析 → NP-hard(VRP变体)
    ↓ 决策: 不能用精确Dijkstra(多车+时间窗→组合爆炸)
S3: 启发式求解 → 遗传算法/蚁群
    ↓ 输出: 最优路径
S4: 对比验证 → 与贪心算法对比 + 不同初始化策略对比
```
