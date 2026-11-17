# model_competition_engine — 能力拆分分析

> Wave 3.3 Step 3.3.1 | 审计日期: 2026-08-08
> 源文件: expert_decision/model_competition/model_competition_engine.md (409行)

---

## 拆分结论

409 行规范包含 **4 个独立职责**，与现有 3 个技能存在重叠。

### 一、归属分类

| 章节 | 行数 | 内容 | 归属 | 理由 |
|------|:--:|------|------|------|
| §1 竞争框架 | 33% | 6步流程定义 | Decision | 编排候选→评分→权衡→推荐 |
| §2 候选生成 | 25% | 4族×条件→候选池映射表 | Decision | 核心决策逻辑，直接产出候选列表 |
| §3 五维评分 | 15% | 5维加权公式+评分细则+示例 | Decision | 数量化决策算法 |
| §4 权衡规则 | 10% | T-1~T-4 | Mixed | T-1/T-2/T-4=Decision; T-3=Knowledge |
| §5 实验设计 | 7% | 统一条件+表格+检验 | Execution | 代码实现层面 |
| §6 决策报告 | 7% | 论文/内部决策模板 | **argument_compiler已覆盖** | 论据编译的职责 |
| §7 竞争示例 | 5% | 2026A/2021B 案例 | Knowledge | 参考案例，非运行时代码 |
| §8 系统对接 | 0% | 拓扑图 | 架构文档 |
| §9 自检清单 | 0% | QA清单 | 文档 |

### 二、与现有技能的职责边界

| 能力 | 现有技能 | model_competition_engine | 冲突？ |
|------|------|------|:--:|
| 模型选择论证 | argument_compiler (why_this + why_not) | §6 决策报告模板 | **重叠** |
| 模型形式化 | model_specification | — | 互补 |
| 候选生成 | — | §2 候选生成规则 | **唯一新增** |
| 多维度评分 | — | §3 五维评分体系 | **唯一新增** |
| 权衡调节 | — | §4 T-1/T-2/T-4 | **唯一新增** |

### 三、拆分方案

```
model_competition_engine (409行)

  ├── CompetitionKnowledge (→ knowledge/competition/)
  │    └── T-3 时间约束策略 + 权重调优表
  │
  ├── ModelStrategyEngine (→ 新建 governed skill, Decision Layer)
  │    ├── 候选生成规则 (§2)
  │    ├── 五维评分引擎 (§3)
  │    ├── 权衡调节器 (§4 T-1/T-2/T-4)
  │    └── 输出: StrategyArtifact (ranked candidates + rationale)
  │
  ├── → argument_compiler 已有职责
  │    └── §6 决策报告模板 (合并, 不重复)
  │
  └── ModelImplementationMapper (→ 未来 Execution Layer)
       └── §5 实验设计规范 (暂不独立)
```

### 四、推荐: 新建 ModelStrategyEngine

只提取 §2+§3+§4 的核心决策逻辑，其他内容 → 已有技能或知识库。

```
ModelStrategyEngine
  输入: ProblemState + DatasetProfile
  输出: StrategyArtifact (candidates[] + scores[] + recommendation)
  
  与 argument_compiler 的关系:
    StrategyEngine:  "应该选哪个模型？" (候选生成 + 量化评分)
    ArgumentCompiler: "为什么选这个模型？" (论文论证段落)
    
  与 model_specification 的关系:
    StrategyEngine: 选择模型
    ModelSpecification: 形式化选中的模型
```

**15/15 governed，但 §6 决策报告模板归属 argument_compiler，不重复建设。**
