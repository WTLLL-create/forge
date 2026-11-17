# Readiness Matrix — 技能治理四象限

> 审计日期: 2026-08-08 | 基于 skill_inventory.md 的完成度 × 调用价值交叉

---

## 象限定义

```
                        调用价值高
                           ↑
              B类              A类
         缺少触发/Contract   已完成可治理
      ────────────────────────────────→ 完成度高
              D类              C类
          淘汰/归档          功能不足需修复
                           ↓
                        调用价值低
```

---

## A 类: 已完成可治理 (Wave 1)

**标准**: 完成度 >= 7 AND 调用价值 high

| Skill | 完成度 | 行动 |
|-------|:---:|------|
| validation_plan | 8/10 | 执行 RUN_002 验证 → 改为 ACTIVE → 接入 Gate |
| argument_compiler | 8/10 | 已在 ACTIVE, 直接接入 Gate + Registry |
| quality_gate | 8/10 | 已在 ACTIVE, 直接接入 Gate + Registry |
| model_specification | 7/10 | 已在 ACTIVE, 补齐模板覆盖率(33%→80%)后接入 |

**Wave 1 产物**: 4 个技能的 boundary 定义 (must_call/avoid_call/input/output/confidence_threshold)

---

## B 类: 价值高但缺少触发/Contract (Wave 2)

**标准**: 完成度 4-6 AND 调用价值 high

| Skill | 完成度 | 缺失 | 预计工作量 |
|-------|:---:|------|:---:|
| abstract_compiler | 6/10 | 模板驱动重构 (已有 _generate_abstract, 需解硬编码) | small (200-300行) |
| style_compiler | 5/10 | Contract 运行时消费 (已有 Schema, 无消费代码) | small (100-150行) |
| formula_compiler | 5/10 | 补齐剩余 4 族模板 (optimization/prediction/statistics) | medium (300-500行) |
| reviewer_rules | 5/10 | review_executor.py (规则完备, 缺调度代码) | medium (200-300行) |
| paper_structure | 4/10 | 从 archive 提取模板 + StructureSelector | small (150-200行) |
| chart_compiler | 4/10 | matplotlib→PNG→docx 三段管线 | medium (500-700行) |
| table_compiler | 4/10 | 独立 TableCompiler 类 + Contract 消费 | medium (300-400行) |

**Wave 2 产物**: 补齐 Contract/Code 后接入 Gate + Registry

**优先级排序 (ROI)**:
1. abstract_compiler (6/10, 最快见效) — 1-2 天
2. style_compiler (5/10, Contract 消费路径) — 1 天
3. paper_structure (4/10, 模板路由) — 2 天
4. reviewer_rules (5/10, 闭环调度) — 3 天
5. chart_compiler (4/10, 管线重建) — 5 天

---

## C 类: 功能不足需修复 (Wave 3)

**标准**: 完成度 2-3 AND 调用价值 high

| Skill | 完成度 | 缺失 | 预计工作量 |
|-------|:---:|------|:---:|
| section_generator | 3/10 | 11章生成器类系统, 最大单体工程 | large (800-1200行) |
| model_competition_engine | 3/10 | 从 409行 MD→Python, 5维评分+4权衡规则 | large (500-800行) |
| contradiction_finder | 2/10 | S-tier 知识→Python 规则引擎 | medium (300-400行) |
| reference_compiler | 2/10 | 从零构建 GB/T 7714 生成器 | medium (250-350行) |

**注意**: section_generator 和 model_competition_engine 的预计工程量很大 (500-1200 行)，且它们都依赖多个上游 Contract 稳定。建议在 Wave 1-2 完成、上游 Contract 消费路径被验证后，再启动这两个。

---

## D 类: 淘汰/归档

**当前无 D 类技能。** 所有 12 个 partial/not_connected 技能的调用价值都是 high。

但需警惕: 如果 Wave 2 完成后某技能仍未达到 Ready 状态，应降级为 D 类并归档。

---

## 治理路线图

```
Wave 1 (当前 → 1周)
├── A类 4技能: boundary 定义 + Gate 接入
├── validation_plan: RUN_002 验证
└── 产物: Invocation Gate v1.0 + Skill Registry v1.0

Wave 2 (1-3周)
├── B类 7技能: 优先 abstract → style → structure → reviewer
├── 产物: 有效消费率 30%→70%
└── chart_compiler: matplotlib 管线重建

Wave 3 (4-8周)
├── C类 4技能: 优先 contradiction → reference → competition → section
└── 产物: 有效消费率 70%→85%
```

---

## 风险提示

1. **section_generator** 是 1200 行大工程。如果在 Wave 2 完成前启动，会因为上游 Contract 消费路径未稳定而反复返工。
2. **model_competition_engine** 的规范已经是国家级质量——但正因为太详尽，容易陷入"过度工程"。建议先做最小可用版（CandidateGenerator + Scorer），TradeoffApplier 作为 v2。
3. **D 类空缺** 不是好消息——说明 12 个技能一个都没被认为可以淘汰。需要定期复核，防止"永远不会淘汰"的文化固化。
