# CORE_MANIFEST.md — v6.4.1 核心模块契约

> 不是"介绍每个模块做什么"，而是"定义模块之间的输入/输出合同"。
> 任何模块的修改必须同步更新此文件。
>
> **接口 Schema**: 见 `contracts/` 目录。每个模块的输出必须包含对应 JSON Schema 的实例。

---

## 调用链总图 (v6.4.1 — 含 Paper Quality Closure)

```
S1: problem_intelligence/  →  ProblemState      [schema: contracts/problem_state.schema.json]
        ↓
S2: strategy_planner/      →  StrategyPlan      [由 ProblemState.sub_type 自动路由]
        ↓
S3: expert_decision/       →  DecisionContract  [schema: contracts/decision_contract.schema.json]
        ↓
S4: models_expert/         →  ModelResult       [schema: contracts/model_result.schema.json]
        ↓
S5: evidence_layer/        →  ValidationContract [schema: contracts/validation_contract.schema.json]
        ↓
S5.5: formalization/       →  ModelFormalization [schema: contracts/model_formalization.schema.json]  ← v6.4.1 NEW
        ↓
S6: paper_reasoning/       →  PaperSection      [schema: contracts/paper_section.schema.json]
        ↓
S6.5: paper_engineering/   →  PaperComplianceReport  [rules: core/paper_engineering.md]  ← v6.4.1 NEW
        ↓
   ┌─ Paper Quality Gate ─────────────────────┐  ← v6.4.1 NEW
   │ P0 Fatal → REJECT   P1 Critical → CAP70  │
   └──────────────────────────────────────────┘
        ↓ (P0 passed)
S7: evaluation/            →  ScoreCard + FailureRecord [schema: contracts/failure_record.schema.json]
        ↓ (if < target)
S4: models_expert/         ←  FixAction (下次 Expert Decision 读取 FailureRecord)
```

**v6.4.1 新增**:
- `contracts/model_formalization.schema.json` — 模型数学表达合约 (L5.5)
- `contracts/paper_style_contract.schema.json` — 论文格式约束 (继承 v5 layout_profile.json)
- `core/paper_engineering.md` — 论文工程层规则 (L6.5)
- `core/paper_quality_gate.md` — 三级门禁 (P0/P1/P2)

**验证用例**: `contracts/validation_2020A.md` — 2020 A 题 炉温曲线的 Schema 化完整链路。

---

## 模块契约

### L0 — Entry

| 字段 | 值 |
|------|-----|
| 文件 | `SKILL_STATUS.md` |
| 输入 | 用户请求 ("求解2021A题") |
| 输出 | 路由到 `problem_intelligence/` |
| 决策 | 确定加载哪个 L1 模块 |

---

### L1 — Problem Intelligence

| 字段 | 值 |
|------|-----|
| 目录 | `problem_intelligence/` |
| 输入 | 赛题原文 (.docx + 附件数据) |
| 输出 | **ProblemState** |
| 决策 | 题型分类 (A/B/C) + 子类型 + 核心矛盾识别 |
| 下游 | → `strategy_planner/` |

**ProblemState 必须包含**:
```yaml
problem_type: optimization  # 或 mechanism / prediction / evaluation / classification / hybrid
sub_type: multi_objective   # 子类型
core_contradiction: "生产效率和排放达标之间的矛盾"
constraints: [约束1, 约束2, ...]
data_available: true/false
data_description: "3个CSV, 500行×20列"
```

**验证**: 2021 A 题 → 能否正确输出 `problem_type: optimization, sub_type: multi_objective`？

---

### L2 — Strategy Planner

| 字段 | 值 |
|------|-----|
| 目录 | `strategy_planner/` |
| 输入 | ProblemState |
| 输出 | **StrategyPlan** |
| 决策 | 解题步骤序列 + 各步骤使用的管线模式 |
| 下游 | → `expert_decision/` |

**StrategyPlan 必须包含**:
```yaml
steps:
  - step_1: { task: "数据清洗", pipeline: "data_processing" }
  - step_2: { task: "机理分析", pipeline: "mechanism_first" }
  - step_3: { task: "多目标优化", pipeline: "optimization_pipeline" }
  - step_4: { task: "方案评价", pipeline: "evaluation_pipeline" }
problem_decomposition: [子问题1, 子问题2, ...]
estimated_models: [候选模型列表]
```

**验证**: 给定 ProblemState(type=optimization, multi_objective) → 是否产生包含 NSGA-II/加权法的候选？

---

### L3 — Expert Decision

| 字段 | 值 |
|------|-----|
| 目录 | `expert_decision/` |
| 输入 | StrategyPlan |
| 输出 | **DecisionContract** |
| 决策 | 具体模型选择 + 为什么选 + 为什么不选备选 |
| 下游 | → `models_expert/` + `data_processing/` + `numerical_computing/` |

**DecisionContract 必须包含**:
```yaml
primary_model: NSGA-II
reasoning: "三目标冲突，权重无法先验确定 → 需Pareto前沿"
alternatives_considered: [加权法: 权重敏感, 约束法: 目标数过多]
model_parameters:
  pop_size: 100
  n_gen: 200
data_requirements: [X矩阵, y向量, 约束边界]
risk_flags: ["种收群敛性待验证"]
```

**验证**: 给定优化策略 → 是否生成 ≥2 个候选模型的对比论证？

---

### L4 — Models Expert + Data + Compute

| 字段 | 值 |
|------|-----|
| 源目录 | `models_expert/` + `data_processing/` + `numerical_computing/` |
| 输入 | DecisionContract |
| 输出 | **ModelProposal** + 计算结果 |
| 决策 | 参数调优 + 异常处理 + 失败回退 |
| 下游 | → `evidence_layer/` |

**ModelProposal 必须包含**:
```yaml
model_used: NSGA-II (pymoo implementation)
results_summary:
  pareto_front_size: 50
  objective_ranges: { 产量: [100,200], 能耗: [50,80], 排放: [10,30] }
execution_log: "3次运行, 收敛在第187代"
issues: []
```

**验证**: 给定 DecisionContract(NSGA-II, pop=100) → 能否实际求解并返回 Pareto 前沿？

---

### L5 — Evidence Layer

| 字段 | 值 |
|------|-----|
| 目录 | `evidence_layer/` |
| 输入 | ModelProposal |
| 输出 | **ValidationReport** |
| 决策 | 结论可信度判断 + 缺失证据标记 |
| 下游 | → `paper_reasoning/` |

**ValidationReport 必须包含**:
```yaml
evidence_levels:
  L1_baseline: { status: "pass", detail: "与加权法对比, Pareto解更优" }
  L2_ablation: { status: "missing", detail: "未验证种群大小影响" }
  L3_robustness: { status: "pass", detail: "3次运行, 前沿稳定" }
  L4_sensitivity: { status: "missing", detail: "未验证目标权重敏感性" }
  L5_uncertainty: { status: "missing", detail: "未报告置信区间" }
claim_readiness: "D5预估 9/15 — 验证不完整, 但不阻止获奖"
```

**验证**: 给定 NSGA-II 结果 → 是否识别出"缺少消融实验"？

---

### L6 — Paper Reasoning

| 字段 | 值 |
|------|-----|
| 目录 | `paper_reasoning/` + `paper_pattern_library/` |
| 输入 | ProblemState + DecisionContract + ModelProposal + ValidationReport |
| 输出 | **ArgumentChain** (论文骨架) |
| 决策 | 每章的信息组织策略 |
| 下游 | → `paper_utils.py` 生成 .docx + → `evaluation/` |

**ArgumentChain 必须包含**:
```yaml
sections:
  section_1: { pattern: "contradiction_driven", core: "效率 vs 排放的矛盾" }
  section_5: { pattern: "why_this_model", core: "三目标冲突→NSGA-II三层论证" }
  section_8: { pattern: "contribution_formulation", core: "发现Pareto前沿存在效率-排放的非线性拐点" }
anti_pattern_checks: ["无模型堆砌", "accuracy≠1", "有模型评价章"]
```

**验证**: 给定完整的 ProblemState + DecisionContract + ModelProposal → 论文是否包含模型选择的三层论证？

---

### L7 — Evaluation

| 字段 | 值 |
|------|-----|
| 文件 | `evaluation/canonical_scoring_framework.md` |
| 输入 | 生成的论文 (.docx 或 .md) |
| 输出 | **ScoreCard** |
| 决策 | 分数 + 弱点定位 + 修复优先级 |
| 下游 | → `reviewer_agent/improvement_strategy.md` 产生修复动作 |

**ScoreCard 必须包含**:
```yaml
total_score: 72
dimensions:
  D1: 14  # 问题理解
  D2: 20  # 模型合理性
  D3: 12  # 创新性
  D4: 16  # 求解可靠性
  D5: 5   # 验证完整性
  D6: 5   # 论文表达
grade: S2_mid (省一~国二边界)
top_weakness: D5 (验证不足 — 缺消融实验)
fix_priority: [加消融实验 +3, 加敏感性分析 +2, 改进图表 +1]
```

**验证**: 给定一篇论文 → 是否输出 ≥6 维分数 + ≥1 条具体修复建议？

---

## 🔴 当前断点（待 Week 2-3 盲测验证）

以下是在审查中发现的已知链断裂：

| 断裂点 | 症状 | 严重度 |
|--------|------|:---:|
| L1→L2 | Problem Intelligence 输出无结构化 Schema，Strategy Planner 无法自动消费 | 🔴 |
| L3→L4 | DecisionContract 没有程序化接口，需要人工阅读 .md 后手动执行 | 🔴 |
| L5→L6 | ValidationReport 中的缺失证据标记不会自动触发论文警告段落 | 🟡 |
| L7→L4 | ScoreCard→FixAction 的闭环未程序化，依赖人工判断 | 🟡 |
| L0 入口 | 没有统一入口函数/脚本，AI 进入后靠"读 README"手动路由 | 🔴 |

---

## v6.0 通过标准

以下全部为 YES 才算 v6.0 核心链验证通过：

- [ ] 输入一道陌生 A 题 → L1 正确输出 ProblemState
- [ ] ProblemState → L2 正确输出 StrategyPlan
- [ ] StrategyPlan → L3 正确输出 DecisionContract（含 ≥2 候选对比）
- [ ] DecisionContract → L4 实际求解并输出 ModelProposal
- [ ] ModelProposal → L5 输出 ValidationReport（含 ≥1 条缺失证据）
- [ ] 全部上游输出 → L6 输出 ArgumentChain（含模型选择论证）
- [ ] ArgumentChain → 生成 .docx 论文
- [ ] 论文 → L7 输出 ScoreCard（含 ≥1 条修复建议）
- [ ] ScoreCard.weakness → 论文修改后 ScoreCard 分数提高
