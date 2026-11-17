# Stage 28 — Visual & Paper Engineering（视觉表达与论文工程层）

**定位**：把复杂推理压缩成评委几秒可理解的信息结构。不是"美化论文"，是"视觉推理"。

**输入**：Stage 26 的研究逻辑 + Stage 27 的模型决策结论 + 实验结果

**输出**：论文的图表方案 + 排版规范 + 信息组织策略

**内部组件**：
- `visual_reasoning/` → 什么图回答什么问题 + 图表选择规则（总入口：`visual_reasoning_framework.md`）
- `figure_patterns/` → 高分论文图表模板（路线图/预测/Pareto/对比 + 反例）
- `paper_layout/` → 论文九章结构 + 段落/图表/公式规范（总入口：`paper_structure_and_chapter_rules.md`）

**上游**：Stage 26（研究逻辑→决定论文要论证什么）、Stage 27（模型决策→决定论文中的关键数字）

**下游**：Stage 29 evidence_layer（图表和表格是证据的主要载体）
