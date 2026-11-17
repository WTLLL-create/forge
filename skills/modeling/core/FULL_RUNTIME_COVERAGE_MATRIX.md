# Forge v6.4 — Full Runtime Coverage Matrix

> 审计范围: L0-L9 全部执行层  
> 审计问题: 每个层的输出是"编译器生成"还是"AI代理手动填写"？  
> 发现: L6 PaperCompiler 是唯一真正被编译器驱动的层。L1-L5 全部为 AI 手动填写。

---

## 执行层追溯

| 层 | 输出 | RUN_001 实际生成方式 | 应该的方式 | 状态 |
|:---:|------|------|------|:---:|
| **L1** | ProblemState | ❌ AI 手动写 JSON | ProblemIntelligenceCompiler 读题目+用 contradiction_finder | 🔴 |
| **L2** | StrategyPlan | ❌ AI 手动写 JSON | StrategyCompiler 读 ProblemState.sub_type + 路由 pipeline | 🔴 |
| **L3** | DecisionContract | ❌ AI 手动写 JSON (参考了 rules) | DecisionCompiler 读 models_expert/ + model_competition_engine | 🟡 |
| **L4** | ModelResult | ✅ analysis.py 实际执行计算 | ModelExecutionRouter 读 DecisionContract.model_family → 路由求解器 | 🟢 |
| **L5** | ValidationContract | ❌ AI 手动写 JSON | EvidenceCompiler 读 ModelResult + evidence_framework | 🔴 |
| **L6** | PaperSection | ✅ PaperCompiler 管线 (v6.4.3) | 同上 | 🟢 |
| **L7** | ScoreCard | ❌ AI 手动评分 | ReviewerCompiler 读 canonical_scoring_framework + paper | 🔴 |
| **L8** | FailureRecord | ❌ AI 手动写 JSON | FailureAggregator 自动聚合 ScoreCard.weaknesses | 🟡 |
| **L9** | ExperienceProposal | ❌ AI 手动写 JSON | EvolutionController 自动生成 IP | 🟡 |

## 真实消费率（区分"AI读了规则" vs "编译器执行了规则"）

| 层 | 技能 | AI读了? | 编译器执行了? | 实际消费 |
|:---:|------|:---:|:---:|:---:|
| L1 | problem_intelligence/, contradiction_finder | ✅ 读了 | ❌ 没执行 | **0%** |
| L2 | strategy_planner/ pipeline_patterns | ✅ 读了 | ❌ 没执行 | **0%** |
| L3 | expert_decision/ decision_rules, model_competition | ✅ 参考了 | ❌ 没执行 | **~30%** |
| L4 | data_processing/, numerical_computing/ | N/A | ✅ 代码执行 | **100%** |
| L5 | evidence_layer/ evidence_framework | ✅ 读了 | ❌ 没执行 | **0%** |
| L6 | PaperCompiler (v6.4.3) | N/A | ✅ 编译器管线 | **64%** |
| L7 | canonical_scoring_framework | ✅ 读了 | ❌ 没执行 | **~50%** |
| L8 | failure_aggregator | ❌ 没读 | ❌ 没执行 | **0%** |
| L9 | evolution_controller | ❌ 没读 | ❌ 没执行 | **0%** |

## 按"编译器级消费"的真实覆盖率

```
L1:  0%   ← 最关键: 问题理解仍靠AI经验
L2:  0%   ← 策略规划未程序化
L3: 30%   ← 模型选择部分依赖规则但核心决策靠AI
L4: 100%  ← 唯一完全程序化的层 (scipy/numpy)
L5:  0%   ← 验证检查靠AI阅读
L6: 64%   ← v6.4.3 完成 (7/11 skills)
L7: 50%   ← 评分框架有规则但执行靠AI
L8:  0%   ← FailureRecord未自动聚合
L9:  0%   ← Evolution未自动触发
─────────────────
加权平均: ~27%
```

## 结论

**v6.4.3 修复了 L6，但 L1-L5 和 L7-L9 仍然是"AI读规则+手动写JSON"模式。**

L6 的 PaperCompiler 证明了编译器模式可行。但这不是 Forge 的全部能力链 — 只是论文生成链。

L4 是唯一真正程序化执行的层（scipy/numpy 代码），但它不消费任何 Forge skill。

真正的 Forge Runtime 化需要把 L6 的编译器模式复制到 L1, L2, L3, L5, L7。

---

## v6.4.4 路线: 每层一个 Compiler

```
题目文本
  ↓ L1 ProblemIntelligenceCompiler    [消费: contradiction_finder]
ProblemState
  ↓ L2 StrategyCompiler                [消费: pipeline_patterns]
StrategyPlan
  ↓ L3 DecisionCompiler                [消费: models_expert, model_competition]
DecisionContract
  ↓ L4 ExecutionRouter                 [消费: models_expert(求解器)]
ModelResult
  ↓ L5 EvidenceCompiler                [消费: evidence_framework, ValidationPlanCompiler]
ValidationContract
  ↓ L6 PaperCompiler                   [已完成 v6.4.3 ✅]
PaperSection → docx
  ↓ L7 ReviewerCompiler                [消费: canonical_scoring_framework]
ScoreCard
  ↓ L8 FailureAggregator               [消费: failure_aggregator.py]
FailureRecord
  ↓ L9 EvolutionController             [消费: evolution_controller.py]
ExperienceProposal
```

**v6.4.3 完成了 L6 的样板工程。下一步: 把编译器模式复制到 L1, L2, L3, L5。**
