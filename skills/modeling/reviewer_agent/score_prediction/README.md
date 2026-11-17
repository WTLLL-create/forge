# Score Prediction Layer — 评分模拟器

**定位**：模拟"如果现在提交，评委大概给多少分"。不是审查扣分，是提交前预测+改进优先级建议。

**输入**：`paper_state_schema.json`（论文特征）或直接从 Stage 26-29 模块提取

**输出**：六维得分 + 总分 + 预估等级 + 按优先级排序的改进行动（每条标注预期分数提升）

**内部组件**：
- `scoring_framework_and_rubrics.md` → 六维评分模型 + 每维 A/B/C/D 四级细则 + Forge 自动检查项
- `score_mapping_and_schema.md` → 论文特征→分数加减映射 + paper_state JSON schema
- `weakness_to_action.md` → 弱点→改进行动→预期提升 + 改进优先级算法

**上游**：Stage 26-29 全部模块（评分细则中的所有 Forge 检查项直接引用各 Stage 的规则）

**下游**：Reviewer Agent（评分预测→对比实际审查结果→校准）、Stage 30（真实论文校准评分模型）
