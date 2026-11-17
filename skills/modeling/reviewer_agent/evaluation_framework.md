# 评审框架总则

> Reviewer Agent 的执行协议：何时触发、怎么审查、审查深度

---

## 一、触发条件

Reviewer Agent 在以下情况触发：

| 触发条件 | 动作 |
|----------|------|
| Paper Agent (§6) 完成论文生成 | 自动启动审查 |
| 用户明确要求审查 | 重新审查当前论文 |
| 论文修改后（improvement_strategy.md） | 第 N+1 轮审查 |

---

## 二、审查流程

```
Step 1: 结构完整性检查
  → paper_quality_rules.md — 快速扫描11个章节是否齐全

Step 2: 模型专项审查
  → model_review_rules.md — 按模型类型逐项检查

Step 3: 数学严谨性检查
  → mathematical_check_rules.md — 公式/推导/假设/结果

Step 4: 创新性评估
  → innovation_check_rules.md — L0~L3 等级评定

Step 5: 综合评分
  → scoring_rules.md — 6维度加权打分

Step 6: 生成审查报告
  → review_report_template.md — 输出标准格式报告

Step 7: 确定下一步
  → improvement_strategy.md — 问题→修改动作映射
```

---

## 三、审查深度控制

| 审查轮次 | 深度 | 重点 |
|----------|------|------|
| 第 1 轮 | 全面 | 所有 6 维度完整审查 |
| 第 2 轮 | 聚焦 | 重点审查第 1 轮标记的问题是否修复 + 是否引入新问题 |
| 第 3 轮 | 终审 | 只检查致命问题和高影响问题 |

---

## 四、与 agent_system 的集成

```
agent_system/workflow_execution.md
        │
        S7: REVIEW
        │
        ▼
reviewer_agent/evaluation_framework.md (本文件)
        │
        ├── 评分 ≥ 85 → S8 DONE
        ├── 评分 70-84 → improvement_strategy.md → S6 PAPER (修改)
        └── 评分 < 70 → state_machine.md → S2 MODEL_SELECTION (退回)
```

---

## 五、审查质量自检

Reviewer 完成审查后自问：

1. 我是否发现了至少 3 个具体问题（而非泛泛评价）？
2. 我的扣分是否有明确依据（哪条规则、哪个文件）？
3. 我的修改建议是否可执行（Agent 能直接按建议修改）？
4. 致命错误是否被优先标记？
