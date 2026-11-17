# Stage 29 — Evidence & Evaluation Layer（证据评价层）

**定位**：回答"你的结论凭什么可信"。不是增加实验数量，是提高证据质量。

**输入**：论文中的每一条结论性声明 + Stage 23 的实验结果

**输出**：声明验证报告（哪条声明证据不足）+ 补实验建议 + 论文修改建议

**内部组件**：
- `evidence_framework_and_claim_validator.md` → 证据金字塔 + 四类声明 + 声明确认器
- `baseline_ablation_robustness_sensitivity_uncertainty.md` → 五大实验范式的标准设计

**上游**：Stage 26（贡献陈述=声明来源）、Stage 27（模型决策=被验证的对象）、Stage 28（图表=证据载体）

**下游**：Reviewer Agent（评分时使用证据完整性检查）、Stage 29.5 评分模拟器（待建）
