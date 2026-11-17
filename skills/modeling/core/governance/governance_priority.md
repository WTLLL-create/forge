# Governance Priority — v6.5 Skill Governance 实施优先级

> 审计日期: 2026-08-08 | 基于 readiness_matrix.md + missing_contracts.md

---

## 前置: 已完成

- [x] Phase 0: Skill Capability Audit — 15 技能逐项审查
- [x] 四象限矩阵: A类(4) / B类(7) / C类(4) / D类(0)
- [x] 缺失合同清单: 4 新建 + 4 修复

---

## Wave 1: Invocation Gate + Skill Registry (P0)

**为什么**: Gate 决定 Registry 长什么样, Registry 是后续所有 router/benchmark 的基础。不做这一步, 后续全架在沙上。

### Step 1.1: SkillBoundary Contract (1 天)

产物: `skills/modeling/core/contracts/skill_boundary.schema.json`

为 15 个技能定义结构化边界:
- must_call patterns (正则/关键词匹配)
- avoid_call patterns (排除规则)
- input schema refs
- output schema refs
- confidence_threshold

不再使用"自然语言描述触发条件"。改为结构化 YAML, 可被程序化匹配。

### Step 1.2: Invocation Gate (2 天)

产物: `skills/modeling/core/governance/invocation_gate.py`

逻辑:
```
query → SkillRegistry.match(query)
  → if top_match.confidence > 0.80:
      forbid_direct_answer()
      route_to_forge_runner(skill_id)
  → elif top_match.confidence > 0.50:
      suggest_skill(skill_id)
  → else:
      allow_free_answer()
```

Gate 在 `forge_runner.py` L0 之前工作。不是 prompt engineering 层——是执行层拦截。

### Step 1.3: SkillRegistry 升级 (1 天)

产物: 在现有 `skill_runtime_registry.yaml` 中为 A 类的 4 个技能增加 `boundary` 块

升级后 registry 的每个条目:
```yaml
skill_id:
  state: active
  boundary:
    must_call: [...]
    avoid_call: [...]
  input: {required: [...], schema_ref: "..."}
  output: {produces: "...", schema_ref: "..."}
  confidence_threshold: 0.80
```

### Step 1.4: validation_plan RUN_002 验证 (1 天)

将 validation_plan 从 HELD → ACTIVE:
- 在第二种题型上运行 `ValidationPlanCompiler.compile()`
- 确认生成的计划合理
- 更新 registry 状态

---

## Wave 2: B 类技能补齐 (P1)

### Step 2.1: abstract_compiler 重构 (2 天, 最高 ROI)

从 6/10 → 8/10:
- 消费 abstract_patterns.md 的 5 要素模板
- 解硬编码 oil domain
- 按 problem_type 路由到对应模板
- 字数保障逻辑

### Step 2.2: PaperStyleContract 运行时消费 (1 天)

修复 3 个技能的共同上游:
- PaperCompiler 从硬编码 style dict → json.load(PaperStyleContract)
- jsonschema.validate() 集成
- 为 table_compiler 和 reference_compiler 铺路

### Step 2.3: paper_structure 模板路由 (2 天)

从 archive/v5 提取模板:
- StructureSelector: problem_type → 结构骨架
- 支持 CUMCM 标准 / MCM / 单模型 / 架构型 四种模式
- 动态章节列表替代硬编码 8 章

### Step 2.4: review_executor.py (3 天)

reviewer_rules 从 5/10 → 7/10:
- 消费 ScoreCard → 映射到 improvement_strategy 动作
- 轮次追踪 + 修改前后分数记录
- 最多 3 轮, 自动停止

---

## Wave 3: C 类技能建设 (P2)

### Step 3.1: chart_compiler 三段管线 (5 天, 最大缺口)

完全重建 matplotlib→PNG→docx 路径:
- ChartDecisionEngine (消费 chart_decision_tree)
- ChartRenderer (matplotlib OO 风格 + 600dpi)
- ChartInserter (PNG→python-docx add_picture)

### Step 3.2: contradiction_finder (3 天, S-tier 知识资产)

将 262 行规范转化为 Python:
- 关键词扫描器 + 4 类型匹配器
- 4 维评分矩阵
- 结构化 ContradictionDeclaration JSON 输出

### Step 3.3: reference_compiler (2 天)

从零构建:
- 消费 PaperStyleContract.reference (GB/T 7714)
- 从 DecisionContract 模型来源提取元数据
- 生成 docx 参考文献章节

### Step 3.4: model_competition_engine (5 天, 大工程)

最小可用版:
- CandidateGenerator + Scorer (核心评分)
- TradeoffApplier 作为 v2

### Step 3.5: formula_compiler 模板补齐 (3 天)

optimization/prediction/statistics 族:
- 补齐 SPEC_TEMPLATES (2/6 → 6/6)
- AI fallback: 无模板时动态推导公式

---

## Wave 4 (远期): Skill Router + Benchmark + FailureMemory

当有效消费率 > 70% 后启动:

- **Skill Router**: 从 1:1 路由 → 概率性多候选排序 + DAG 规划
- **Skill Benchmark**: must-call/must-not-call/chain-call 三层测试
- **Skill FailureMemory**: bypass 追踪 → 自动 trigger 修正 → Controlled Evolution

---

## 总工期估计

| Wave | 内容 | 工期 | 目标 |
|:---:|------|:---:|------|
| Wave 1 | Invocation Gate + Registry + Boundary | 5 天 | 基础治理启动 |
| Wave 2 | B 类 4 技能补齐 | 8 天 | 消费率 30%→55% |
| Wave 3 | C 类 5 技能建设 | 18 天 | 消费率 55%→80% |
| Wave 4 | Router + Benchmark + FailureMemory | 远期 | 消费率 80%→90%+ |

---
> **当前决策点**: 是否启动 Wave 1 Step 1.1 — SkillBoundary Contract 设计？
