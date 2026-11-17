# v6.2 Data Feedback Loop — 经验收集与回放层

> 原则: 系统记录和提议，人类审批和执行。不是 Self Evolution，是 Controlled Evolution。

## 组件

| 文件 | 作用 |
|------|------|
| `failure_aggregator.py` | 聚合分散的 FailureRecord → 13 个 Pattern |
| `experience_registry.yaml` | 存储已审批的经验 (7条: 4 resolved, 3 proposed) |
| `improvement_proposal.schema.json` | 改进建议的标准格式 (系统提议→人工审批) |

## 工作流

```
Benchmark 运行
    ↓
FailureRecord 产生
    ↓
failure_aggregator.py 聚合
    ↓
生成 ImprovementProposal
    ↓
人工审批 (pending → approved/rejected)
    ↓
写入 experience_registry.yaml
    ↓
下一次 Benchmark 加载注册经验
```

## 当前经验库

| ID | 名称 | 状态 | 修复于 |
|:---|------|:---:|:---:|
| EXP-001 | missing_alternative_comparison | resolved | v6.0 |
| EXP-002 | missing_domain_constraints | proposed | — |
| EXP-003 | difficulty_misclassification | proposed | — |
| EXP-004 | insufficient_paper_validation | resolved | v6.1 |
| EXP-005 | large_scale_discrete_optimization | proposed | — |
| EXP-006 | incomplete_complex_execution | proposed | — |
| EXP-007 | inverse_problem_non_uniqueness | resolved | v6.1 |

## v6.2 验收指标

- [ ] 重复错误减少: 下次 Benchmark 中 EXP-001 应零出现 (v6.0 已修复)
- [ ] 新规则有效: EXP-004/007 修复后, B02 D5 从 6→8 (已验证)
- [ ] 无错误传播: baseline B02 分数不低于 v6.0 的 82
