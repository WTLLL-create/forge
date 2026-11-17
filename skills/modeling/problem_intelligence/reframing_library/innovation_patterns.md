# Innovation Patterns — 创新模式库

> 参考：`paper_case_library/innovation_analysis/` 下的 model_combination / assumption_innovation / validation_innovation / visualization_innovation / problem_reframing

## 创新来源地图

```
创新不是"想出来的"，而是从以下维度中发现的：

1. 问题重构    → 换一个角度看问题（见 problem_transfer.md）
2. 假设突破    → 挑战隐含假设（见 assumption_breaking.md）
3. 模型组合    → 多模型协同（见 hybrid_model.md）
4. 特征工程    → 构造问题特有的新特征
5. 初始化策略  → 不是随机初始化，而是基于领域知识的启发式种子
6. 验证创新    → 不只做标准验证，加入场景特化的验证维度
7. 可视化创新  → 不是标准图表，而是揭示问题本质的定制图表
```

## 创新等级（来自 reviewer_agent/innovation_check_rules.md）

| 等级 | 说明 | 示例 |
|:---:|------|------|
| L3 | 对现有方法的实质性改进 | 改进GM(1,1)背景值公式 |
| L2 | 两种以上方法的创新组合 | AHP修正+TOPSIS+自定义惩罚项 |
| L1 | 标准方法+问题特化 | 为具体问题增加自定义约束 |
| L0 | 直接套用标准方法 | 课本例题原样照搬 |
