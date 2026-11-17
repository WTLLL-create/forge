# Validation Pattern: evaluation（评价类模型）

> 适用模型: TOPSIS, AHP, 熵权法, CRITIC, 模糊综合评价  
> 核心验证目标: 排序的稳健性 — "换一个指标或权重，排名会不会变？"

## required（必须执行 — 不做=论文不合格）

| 类型 | 方法 | 参数 | 指标 | 原因 |
|------|------|------|------|------|
| sensitivity_analysis | leave_one_out | 逐一移除指标 | Kendall's τ / 排名一致率 | 指标集选择影响结论 → 必须验证稳健性 |
| baseline_comparison | method_comparison | vs 等权法 | τ, 区分度(score_range) | 证明赋权方法的必要性 |
| robustness_check | method_comparison | 2-3种赋权方法对比 | τ ≥ 0.7 | 验证结论不依赖特定赋权方法 |

## recommended（建议执行）

| 类型 | 方法 | 参数 | 指标 | 条件 |
|------|------|------|------|------|
| ablation_study | leave_one_out | 移除单个子指标 | 排名位移 | 指标体系≥5个指标时 |
| uncertainty_quantification | monte_carlo | 1000次 ±SD扰动 | 95%CI宽度 | 原始数据含SD时 |

## blocking_conditions

| 条件 | 替代方案 |
|------|------|
| 指标数 < 3 | sensitivity_analysis → not_executable, 论文标注"指标过少无法进行有意义的敏感性分析" |
| 仅1种赋权方法可用 | robustness_check → not_executable |

## paper_statement模板

```
sensitivity: "指标集敏感性分析表明，{n}种指标组合下品质排序的top-3一致率为{consistency}%，说明模型结论{stability_judgment}。"
robustness: "CRITIC-熵权-等权三种赋权方法的排序一致性Kendall's τ={tau}(p<0.01)，验证了评价结论的稳健性。"
```
