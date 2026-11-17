# Skill Inventory — Forge v6.4.3 全技能盘点

> 审计日期: 2026-08-08 | 审计范围: skill_runtime_registry.yaml 全部 15 技能
> 产物用途: v6.5 Skill Governance Phase 0 前置诊断

---

## 审计维度

| 维度 | 说明 |
|------|------|
| 存在性 | Skill 源文件是否存在 |
| 结构完整性 | 是否有入口/Schema/README |
| 执行能力 | 是否有实际可运行代码 |
| 输入定义 | 参数是否明确、可消费 |
| 输出定义 | 结果是否标准化 |
| 依赖状态 | 外部资源/上游是否可用 |
| 测试状态 | 是否有 benchmark 或单元测试 |
| 调用价值 | 是否值得暴露给 Agent/Governance |

---

## 全量清单

### ACTIVE (3/15)

| # | Skill | 完成度 | 关键资产 | 备注 |
|---|-------|:---:|------|------|
| 1 | argument_compiler | 8/10 | evo_p0_001_decision_argument_compiler.py | L3.5, 编译 why_this_model + why_not_alternatives |
| 2 | model_specification | 7/10 | evo_p0_002_model_specification.py | L3.5, 模板覆盖率 33% |
| 3 | quality_gate | 8/10 | paper_quality_gate.md | L6.5, P0/P1/P2 三级门禁 |

### PARTIAL — 代码存在但不完整 (6/15)

| # | Skill | 完成度 | 卡点 | 治理建议 |
|---|-------|:---:|------|------|
| 4 | validation_plan | 8/10 | RUN_001 通过, 等 RUN_002 验证 | **Ready** |
| 5 | formula_compiler | 5/10 | 2/6 模板覆盖, 静态 LaTeX, 无 fallback | NeedsCode |
| 6 | table_compiler | 4/10 | 硬编码项目相关数据键, 无独立类 | NeedsCode |
| 7 | style_compiler | 5/10 | Schema 优秀但零运行时消费, 全部硬编码 | NeedsContract |
| 8 | reviewer_rules | 5/10 | 评分+检测+映射完备, 缺 review_executor.py | NeedsCode |
| 9 | model_competition_engine | 3/10 | 纯 Markdown 409行, 无一行代码 | NeedsCode |

### NOT CONNECTED — 从 skill_runtime_registry.yaml (6/15)

| # | Skill | 完成度 | 卡点 | 治理建议 |
|---|-------|:---:|------|------|
| 10 | paper_structure | 4/10 | 模板在 archive/v5, 编译器硬编码 8 章 | NeedsCode |
| 11 | section_generator | 3/10 | 110行规则, 零代码, 最大瓶颈 | NeedsCode |
| 12 | chart_compiler | 4/10 | 决策树完整, matplotlib→PNG→docx 全断 | NeedsCode |
| 13 | abstract_compiler | 6/10 | _generate_abstract() 存在但硬编码, 不消费模板 | NeedsCode |
| 14 | contradiction_finder | 2/10 | S-tier 知识, 零代码, 262行纯规则 | NeedsCode |
| 15 | reference_compiler | 2/10 | 零代码, 论文参考文献章节缺失 | NeedsCode |

---

## 统计

| 统计项 | 数值 |
|--------|:---:|
| 总注册技能 | 15 |
| 完全可用 (完成度 >= 7) | 4 (argument_compiler, model_specification, quality_gate, validation_plan) |
| 部分可用 (5-6) | 5 (formula, table, style, reviewer, abstract) |
| 接近不可用 (<= 4) | 6 (paper_structure, section_generator, chart, contradiction, reference, competition) |
| 有效消费率 | ~30% (实际可被程序化调用的比例) |

---

## 依赖关系

```
validation_plan
      ↓ 依赖
DecisionContract (ACTIVE)
      ↓ 依赖
problem_intelligence/ (ACTIVE) → strategy_planner/ (ACTIVE) → expert_decision/ (ACTIVE)

paper_structure → section_generator → [formula, table, chart, style, reference, abstract]_compiler
                                                           ↓
                                                    paper_compiler.py (monolith)
```

所有 L6 编译技能 (formula/table/chart/style/reference/abstract/section) 在 paper_compiler.py 中以单体形式存在或缺失，不是独立模块。
