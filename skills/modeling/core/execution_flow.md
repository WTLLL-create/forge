# Core Path Trace — 2020 A 题 炉温曲线

> 人工模拟完整调用链，逐层记录输入/输出/断点。
> 目标: 确认 L0→L7 链路是否存在，每层输出是否可被下一层消费。

---

## 题目摘要

2020 国赛 A 题：回焊炉炉温曲线优化
- 给定: 炉温曲线数据 + 物理参数
- 要求: Q1 传热模型 → Q2 最优过炉速度 → Q3 炉温曲线优化 → Q4 对称性分析

---

## S1: Problem Intelligence

**加载**: `problem_intelligence/optimization_problem.md` + `mechanism_problem.md`

**输出 — ProblemState**:
```yaml
problem_type: mechanism + optimization
sub_type: physics_modeling + parameter_optimization
core_contradiction: "焊接质量(温度曲线需在工艺窗口内) vs 生产效率(速度最大化)"
constraints:
  - 峰值温度 240-250°C
  - 170°C以上时间 60-120s
  - 温升速率 < 3°C/s
data_available: true
data_description: "炉温曲线实验数据 + 炉子物理参数"
```

**断点检查**: 
- ✅ `optimization_problem.md` 能识别出优化子类型
- ✅ `mechanism_problem.md` 能识别出物理建模需求
- ⚠️ 输出格式不是结构化 YAML，AI 需要手动翻译 → **中等断点**

---

## S2: Strategy Planner

**加载**: `strategy_planner/pipeline_patterns/optimization_pipeline.md` + `hybrid_pipeline.md`

**输出 — StrategyPlan**:
```yaml
steps:
  - step_1: { task: "传热微分方程建模", pipeline: "mechanism_first" }
  - step_2: { task: "参数辨识(对流换热系数)", pipeline: "data_processing + numerical_computing" }
  - step_3: { task: "过炉速度优化", pipeline: "optimization_pipeline" }
  - step_4: { task: "灵敏度分析", pipeline: "evidence_layer" }
problem_decomposition: [Q1建模, Q2辨识, Q3优化, Q4对称性]
estimated_models: [热传导PDE, 最小二乘拟合, 单目标优化(速度), 多目标优化(速度+质量)]
```

**断点检查**:
- ⚠️ `optimization_pipeline.md` 是通用描述，没有针对"机理+优化混合型"的具体策略
- ⚠️ StrategyPlan 与 DecisionContract 之间缺少"先机理还是先数据"的决策规则 → **中等断点**

---

## S3: Expert Decision

**加载**: `expert_decision/decision_rules/optimization_decision_rules.md` + `model_competition_engine.md`

**输出 — DecisionContract**:
```yaml
# Q1 — 传热模型
primary_model: 一维非稳态热传导方程 (有限差分法)
reasoning: "PCB在炉内匀速运动，x=vt可转化为时间域一维传热"
alternatives_considered: [集总参数法: Bi数不满足, 二维模型: 对称性可用一维简化]

# Q2 — 参数辨识
primary_model: 非线性最小二乘 (scipy.optimize.least_squares)
reasoning: "对流系数h未知，以实验数据拟合，残差最小化"

# Q3 — 过炉速度优化
primary_model: 单目标优化 (scipy.optimize.minimize_scalar)
reasoning: "仅一个决策变量(速度v)，约束可转化为罚函数"
alternatives_considered: [网格搜索: v连续, 精度不足; GA: 单变量杀鸡用牛刀]

# Q4 — 对称性
primary_model: 敏感性分析
reasoning: "分析峰值温度对炉区设定的敏感性，验证对称性假设"

risk_flags: ["Q1显式格式需CFL条件检查"]
```

**断点检查**:
- ✅ optimization_decision_rules.md 的 O-1 (LP检查) 正确引导到单变量优化
- ✅ model_competition_engine.md 提供了"单变量不用GA"的排除逻辑
- ⚠️ DecisionContract 仍是自然语言，无结构化格式 → AI 自行翻译可靠吗？ → **中等断点**

---

## S4: Models Expert + Data + Compute

**加载**: `models_expert/` (无传热模型卡!) + `numerical_computing/api_mapping.md`

**输出 — ModelProposal**:
```yaml
model_used:
  Q1: 自建有限差分求解器 (numpy实现)
  Q2: scipy.optimize.least_squares
  Q3: scipy.optimize.minimize_scalar (method='bounded')

results_summary:
  Q1: "温度场分布已求解, 峰值=243°C at x=..."
  Q2: "h_conv=45.3 W/(m²·K), R²=0.97"
  Q3: "opt_v=78.5 cm/min, 工艺窗口满足"
  Q4: "对称性假设成立, 偏差<2%"

execution_log: "Q1 显式格式 Δt=0.01s, CFL=0.43"
issues: ["无传热模型专家卡, 需从scipy文档直接查API"]
```

**断点检查**:
- 🔴 **严重断点**: `models_expert/` 中没有传热/物理建模的模型卡！全部是统计/ML/优化模型
- ✅ numerical_computing/api_mapping.md 覆盖了 scipy 求解器
- ⚠️ 自建有限差分求解器依赖 AI 的物理知识，Forge 未提供模板 → **严重断点**

---

## S5: Evidence Layer

**加载**: `evidence_layer/evidence_framework_and_claim_validator.md`

**输出 — ValidationReport**:
```yaml
evidence_levels:
  L1_baseline: { status: "pass", detail: "与实验数据对比, R²=0.97" }
  L2_ablation: { status: "missing", detail: "未验证时间步长Δt的影响" }
  L3_robustness: { status: "pass", detail: "CFL=0.43稳定" }
  L4_sensitivity: { status: "pass", detail: "v±10%时峰值温度变化<5°C — 结论鲁棒" }
  L5_uncertainty: { status: "missing", detail: "未报告h的置信区间" }

claim_readiness: "D5预估 7/15 — 缺消融实验和不确定性量化"
```

**断点检查**:
- ✅ evidence_framework 能正确识别缺失证据
- ⚠️ ValidationReport 中的 "missing" 标记需要人工阅读后才能传递到论文 → **低度断点**

---

## S6: Paper Reasoning

**加载**: `paper_reasoning/` + `paper_pattern_library/`

**输出 — ArgumentChain**:
```yaml
sections:
  section_1:
    pattern: "contradiction_driven"
    core: "焊接质量的严格工艺窗口 vs 生产效率最大化的矛盾"

  section_5:
    pattern: "why_this_model"
    core: "Q3为什么用单变量优化：只有一个决策变量v, 约束连续可导, 
           解析梯度可用 → 不需要GA的多变量搜索机制"

  section_8:
    pattern: "contribution_formulation"
    core: "(1)建立了炉温曲线的传热-运动耦合模型 (2)给出了不同工艺窗口下的最优速度谱系"

anti_pattern_checks:
  - "✅ 无模型堆砌：Q3模型选择有"不用GA"的排除论证"
  - "⚠️ accuracy≠1：Q2用R²而非误差率"
  - "⚠️ 有模型评价章但较浅"
```

**断点检查**:
- ✅ contradiction_driven.md + why_this_model.md 覆盖了论文关键段落
- ✅ model_dump.md 可用于自检
- ⚠️ ValidationReport 中的缺失证据 (消融实验) 在论文中无自动警告 → 依赖人工 → **低度断点**

---

## S7: Evaluation

**加载**: `evaluation/canonical_scoring_framework.md`

**输出 — ScoreCard**:
```yaml
total_score: 68
dimensions:
  D1: 13  # 矛盾识别有，但未贯穿全文
  D2: 19  # Q3优化选择论证清晰，"不用GA"有力
  D3: 9   # L2创新: 传热-运动耦合模型
  D4: 15  # 求解可复现
  D5: 7   # R²+敏感性, 缺消融+不确定性
  D6: 5   # 结构规范, 图表OK

grade: S2_mid (省一~国二边界)
top_weakness: D5 verification
fix_priority:
  - 加Δt消融实验: D5 +3, 1h
  - 加h的置信区间: D5 +2, 30min  
  - 矛盾贯穿全文: D1 +2, 1h
```

**断点检查**:
- ✅ canonical_scoring_framework 产生了具体的分数和建议
- ⚠️ 但修复动作到实际论文修改仍是人工闭环 → **中等断点**

---

## 断点汇总

| # | 位置 | 严重度 | 问题 |
|:---:|------|:---:|------|
| 1 | L1→L2 | 🔴 | ProblemState 无结构化 Schema |
| 2 | L3→L4 | 🔴 | DecisionContract 无程序化接口 |
| 3 | S4 执行 | 🔴 | 缺物理建模模型卡 (传热/力学/电路) |
| 4 | L0 入口 | 🔴 | 无统一入口函数 |
| 5 | L2→L3 | 🟡 | 混合型(机理+优化)缺少策略模板 |
| 6 | L7→L4 | 🟡 | ScoreCard→FixAction 闭环未程序化 |
| 7 | L5→L6 | 🟡 | ValidationReport 缺失标记不自动触发论文警告 |
| 8 | L3 输出 | 🟡 | DecisionContract 是自然语言非结构化 |

---

## 结论

8 个断点中:
- 4 个严重 (🔴): 集中在 **接口结构化** 和 **模型覆盖** 上
- 4 个中等 (🟡): 集中在 **闭环程序化** 和 **策略模板** 上

**链路本身存在**。从 L0 到 L7，每一步都有相应的模块和规则。但问题是每一步之间的**接口是非结构化的**——都是 Markdown 文本，AI 需要"阅读理解"后才能传给下一层，而不是"解析 Schema 后自动路由"。

这解释了为什么 94 个排版文件从未被使用：因为整个链路都依赖 AI 手动操作，排版引擎缺乏自动触发的入口。
