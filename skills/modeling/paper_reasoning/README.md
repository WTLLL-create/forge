# Stage 26 — Research Logic Layer（研究逻辑层）

**定位**：让论文不是"做了A做了B做了C"，而是"有一个让人信服的故事线"。

**输入**：题目文本 + 数据特征 + 来自 Problem Intelligence 的问题分析

**输出**：研究问题 + 核心矛盾 + 论证框架 + 贡献陈述

**内部组件**：
- `contradiction_analysis/` → 矛盾发现→量化→化解（总入口：`contradiction_finder.md`）
- `motivation_generation/` → 为什么选这个模型/方案/改进（总入口：`why_this_model.md`）
- `contribution_statement/` → 做了什么→贡献是什么（总入口：`contribution_formulation.md`）
- `model_improvement/` → 为什么需要改进标准模型（`why_this_improvement.md`）
- `paragraph_reasoning/` → 段落级论证逻辑（`paragraph_reasoning.md`）
- `../paper_pattern_library/` → 高分论文模式+反例+评分映射

**上游**：Problem Intelligence (Stage 20.2)

**下游**：Stage 27 expert_decision（模型决策需要研究逻辑的论证支撑）
