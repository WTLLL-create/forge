# Stage 27 — Expert Decision Layer（专家决策层）

**定位**：把数学建模专家的隐性判断转化为可检索、可执行的规则系统。

**输入**：题目特征 + 数据特征 + Stage 26 的矛盾分析结果

**输出**：推荐模型 + 候选池 + 论证理由 + 失败后的替代方案

**内部组件**：
- `decision_rules/` → 按场景组织的模型选择规则（总入口：`prediction_decision_rules.md`）
- `model_diagnosis/` → 模型失败→诊断→修复（总入口：`diagnosis_workflow.md`）
- `model_competition/` → 多模型竞争→评分→推荐（总入口：`model_competition_engine.md`）
- `../models_expert/` → 每个模型的专家知识卡（决策入口/边界/失败/创新/论文表达）

**上游**：Stage 26 paper_reasoning（为什么这样研究）

**下游**：Stage 23 实验引擎（运行推荐模型）→ Stage 28 visual_engineering（将决策理由转化为论文图表）

**完整闭环**：27.1 选 → 27.3 知边界 → 27.4 竞争 → 27.2 诊断失败 → 27.3 替代 → 27.4 重竞争
