# 分数映射 + Paper State Schema

> 论文特征 → 分数加减。每条映射连接 Forge 的 Stage 26-29 规则，说明"这个特征影响哪个评分维度、加减多少分"。

---

## 一、问题分析特征 → D1 映射

| 论文特征 | 影响 | Forge 来源 |
|----------|:---:|------|
| 识别了核心矛盾并定量描述 | +4 | Stage 26 contradiction_finder §二 |
| 分析了≥1个传统方法的局限（有证据） | +3 | Stage 26 why_this_model §三 |
| 提出了明确的研究问题 | +3 | Stage 26 research_question |
| 问题分析=题目复述（无新信息） | −5 | — |
| 直接开始建模，无问题分析章节 | −10 | — |

## 二、模型选择特征 → D2 映射

| 论文特征 | 影响 | Forge 来源 |
|----------|:---:|------|
| 三层论证完整（特征→排除→选择） | +5 | Stage 26 why_this_model |
| 比较了≥2个候选方案并说明为什么不用 | +3 | Stage 27.4 竞争引擎 |
| 能LP的地方用了LP（而非GA） | +3 | Stage 27.3 LP知识卡 |
| 模型选择只说了"本文使用XX"无理由 | −5 | anti_pattern: model_dump |
| 明显误用（外推用RF/小样本用LSTM） | −15 | Stage 27.3 不适用场景 |
| 多Q模型假设冲突 | −5 | Stage 27.1 hybrid_rules |

## 三、创新特征 → D3 映射

| 论文特征 | 影响 | Forge 来源 |
|----------|:---:|------|
| 创新等级 L3+（问题重构/机制发现） | +12~15 | Stage 26 contribution_taxonomy |
| 创新等级 L2 + 消融验证 | +8~12 | |
| 创新等级 L1（首次应用于新场景） | +5~8 | |
| 声称有创新但无消融验证 | −5 | Stage 29 证据要求 C3 |
| 纯套用标准模型 | −10 | L0=零创新 |
| 过度声称"优于所有方法" | −3 | Stage 29 claim_validator |

## 四、实验验证特征 → D4+D5 映射

| 论文特征 | 影响 | 影响维度 | Forge 来源 |
|----------|:---:|:---:|------|
| L1+L2+L3 三级基线对比 | +5 | D5 | Stage 29 baseline |
| 消融实验（改进=完整−消融） | +8 | D5 | Stage 29 ablation |
| 敏感性分析（单因素+多因素） | +5 | D5 | Stage 29 sensitivity |
| 鲁棒性验证（≥3维） | +5 | D5 | Stage 29 robustness |
| 不确定性量化（置信区间） | +3 | D5 | Stage 29 uncertainty |
| 收敛曲线（优化类） | +3 | D4 | Stage 27.3 NSGA-II |
| 统计显著性检验 | +3 | D4 | Stage 29 |
| 无任何基线对比 | −8 | D5 | — |
| 只有单次实验结果 | −5 | D4 | — |
| GA 无编码/交叉/适应度定义 | −10 | D4 | Stage 27.3 知识卡 |

## 五、论文表达特征 → D6 映射

| 论文特征 | 影响 | Forge 来源 |
|----------|:---:|------|
| 图标题达到 Level 3（标题=结论） | +2 | Stage 28.1 visual_reasoning |
| 每张图有引导+解读 | +2 | Stage 28.3 paragraph_figure_formula |
| 公式有前导和意义解释 | +1 | Stage 28.3 |
| 章节间有论证链接 | +1 | Stage 28.3 paper_structure |
| 图表与正文脱节（仅"如图X所示"） | −2 | — |

---

## 六、综合加分项

| 论文特征 | 影响 | 条件 |
|----------|:---:|------|
| 诊断了失败并诚实报告 | +3 | 将失败转化为发现（Stage 27.2） |
| 发现了反直觉的规律 | +5 | L4 创新（Stage 26 contradiction） |
| 给出了实际可操作的决策建议 | +2 | 超越"模型跑完" |

---

## 七、Paper State Schema

```json
{
  "paper_id": "任务唯一ID",
  
  "problem_analysis": {
    "contradiction_found": true,
    "contradiction_quantified": true,
    "research_question_explicit": true,
    "traditional_limits_analyzed": true
  },
  
  "model": {
    "type": ["ARIMA", "RandomForest"],
    "selection_reasoning": "full_3layer",
    "alternatives_compared": true,
    "alternatives_count": 3,
    "misuse_detected": false,
    "cross_q_consistency": true
  },
  
  "innovation": {
    "level": "L2",
    "ablation_validated": false,
    "overclaim_detected": false
  },
  
  "experiment": {
    "baseline_levels": ["L1", "L2"],
    "ablation": false,
    "sensitivity": true,
    "robustness_dims": 2,
    "uncertainty_ci": false,
    "statistical_test": false,
    "convergence_curve": true
  },
  
  "paper_expression": {
    "figure_caption_level": "L2",
    "figure_guided": true,
    "formula_explained": true,
    "chapter_linked": false
  },
  
  "bonus": {
    "failure_diagnosed": false,
    "counterintuitive_found": false,
    "actionable_advice": false
  }
}
```

**使用方式**：填充此 JSON → 查 `scoring_framework_and_rubrics.md` 的 Forge 检查项 → 计算每维分数 → 输出 `weakness_to_action.md` 的改进建议。
