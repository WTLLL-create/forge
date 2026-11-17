# Missing Contracts — 缺失合同清单

> 审计日期: 2026-08-08 | 基于 readiness_matrix.md 的 NeedsContract 分析

---

## 现有合同资产 (已存在, 无需新建)

| Contract | Schema 文件 | 消费状态 |
|----------|------------|:---:|
| ProblemState | problem_state.schema.json | ACTIVE (L1→L2) |
| DecisionContract | decision_contract.schema.json | ACTIVE (L3→L4) |
| ModelResult | model_result.schema.json | ACTIVE (L4→L5) |
| ValidationContract | validation_contract.schema.json | ACTIVE (L5→L6) |
| PaperSection | paper_section.schema.json | ACTIVE (L6→L8) |
| FailureRecord | failure_record.schema.json | ACTIVE (L7→L3/L4) |
| ModelFormalization | model_formalization.schema.json | 部分消费 |
| PaperStyleContract | paper_style_contract.schema.json | **零运行时消费** |
| ValidationPlan | validation_plan.schema.json | ACTIVE |
| ImprovementProposal | improvement_proposal.schema.json | 偶尔消费 (manual) |
| ApprovalRecord | approval_record.schema.json | ACTIVE (evolution) |

---

## 缺失合同 (需新建)

### 1. SkillBoundary Contract (P0)

**用途**: 定义 Skill 的触发边界、输入输出、置信度阈值。供 Skill Registry 和 Invocation Gate 消费。

**关联技能**: 全部 15 个

**建议 Schema 结构**:
```yaml
skill_id: string
name: string
domain: enum[prediction, optimization, evaluation, classification, clustering, visualization, paper, governance]
boundary:
  must_call:
    - pattern: string  # 触发模式
      confidence: float  # 0-1
  avoid_call:
    - pattern: string
      reason: string
input:
  required: [string]
  optional: [string]
  schema_ref: string  # 指向已有 Schema $id
output:
  produces: string  # 输出类型名
  schema_ref: string
confidence_threshold: float
lifecycle: enum[active, partial, not_connected, deprecated]
```

**预计工作量**: 创建 `skill_boundary.schema.json` + 为 15 个技能定义 boundary (每个约 20 行 YAML)

---

### 2. ContentBlock Contract (P1)

**用途**: L6 论文生成管线中 section_generator 的输出格式。定义 content_block 的通用结构（paragraphs, tables, formulas, figures, citations）。

**关联技能**: section_generator, formula_compiler, table_compiler, chart_compiler

**建议 Schema 结构**:
```json
{
  "$id": "forge-v6/content-block/v1",
  "type": "object",
  "properties": {
    "block_id": {"type": "string"},
    "block_type": {"enum": ["paragraph", "table", "formula", "figure", "citation"]},
    "chapter_id": {"type": "string"},
    "content": {"type": "object"},
    "sources": {
      "type": "array",
      "items": {"$ref": "source contract type"}
    }
  }
}
```

**预计工作量**: 创建 `content_block.schema.json`

---

### 3. ChartSpec Contract (P1)

**用途**: chart_compiler 的输入/输出定义。从 chart_decision_tree.md 的结构化规则转化为 Schema。

**关联技能**: chart_compiler

**预计工作量**: 创建 `chart_spec.schema.json`

---

### 4. AbstractSpec Contract (P2)

**用途**: abstract_compiler 的 5 要素输出结构。

**关联技能**: abstract_compiler

**预计工作量**: 创建 `abstract_spec.schema.json`, 小工作量 (已有 abstract_patterns.md 定义结构)

---

## 消费路径断裂 (需修复, 非新建)

| Contract | 断裂点 | 修复方式 |
|----------|--------|----------|
| PaperStyleContract | paper_compiler.py 全部硬编码, 零 json.load() | 在 PaperCompiler.__init__ 中添加 schema 加载 + 验证 |
| ModelFormalization | 消费方 unstable | 已在 evo_p0_002 中有代码, 整合到 paper_compiler |
| PaperStyleContract.table | table_compiler 不消费 | 集成到独立 TableCompiler 模块 |
| PaperStyleContract.reference | reference_compiler 不存在 | 新建 ReferenceCompiler + 绑定 Contract |

---

## 优先级总结

| 优先级 | 合同 | 类型 | 影响面 |
|:---:|------|------|------|
| P0 | SkillBoundary | 新建 | 全部 15 技能, Gate 依赖 |
| P1 | ContentBlock | 新建 | L6 管线 7 技能 |
| P1 | ChartSpec | 新建 | chart_compiler |
| P1 | PaperStyleContract 消费 | 修复 | style/table/reference 3 技能 |
| P2 | AbstractSpec | 新建 | abstract_compiler 1 技能 |
