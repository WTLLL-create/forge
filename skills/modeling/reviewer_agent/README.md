# Reviewer Agent — 双层审查系统

**定位**：模拟竞赛评委的论文审查。不是规则检查器，是发现问题、提出建议、推动修改的专家评审。

**两层体系**：
- **Layer 1** (`skills/review/math-modeling/`) → 队员提交前 10-15 分钟快速自查
- **Layer 2** (`reviewer_agent/`) → AI 深度审查，6 维 100 分，三步闭环（≥85 通过 / 70-84 修改重审 / <70 退回 S2）

**上游**：Stage 28（论文排版后的完整论文）、Stage 29（证据充分性检查结果）

**下游**：`improvement_strategy.md`（问题→修改动作映射）→ Paper Agent 修改 → 再审查

**对接**：Stage 29.5 评分模拟器将从 Reviewer Agent 的评分逻辑中抽象出预测模型。
