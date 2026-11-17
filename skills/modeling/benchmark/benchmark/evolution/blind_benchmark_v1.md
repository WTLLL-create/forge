# CUMCM Blind Benchmark v1 — Forge v7.8

> Generated: 2026-08-08T15:19:53.783897+00:00
> Problems: 10 (4 completed, 6 blocked)

## Overall Verdict: **NEEDS_ARCHITECTURE_IMPROVEMENT**

核心决策和知识覆盖率不足以支撑竞赛级任务

## Average Metrics (10 problems)

| Metric | Score | Status |
|--------|:----:|--------|
| Decision Accuracy | 92 | READY |
| Preflight Recall | 100% | ACTIVE |
| Artifact Completeness | 40% | PARTIAL |
| Reasoning Score | 95 | SOLID |
| Judge Score | 34 | BELOW |
| Human Correction Cost | 54% | HIGH |
| Wrong Confidence Rate | 18% | RISKY |

## Per-Problem Results

| Problem | Type | Preflight | Decision | Artifact | Reasoning | Judge | HCC | WCR |
|---------|------|:--------:|:--------:|:--------:|:---------:|:-----:|:---:|:---:|
| ✗ BLIND_A1 | prediction | GAP | 100 | 0 | 95 | 0 | 80% | 30% |
| ✗ BLIND_A2 | prediction | GAP | 100 | 0 | 95 | 0 | 80% | 30% |
| ✗ BLIND_A3 | prediction | GAP | 100 | 0 | 95 | 0 | 80% | 30% |
| ✗ BLIND_B1 | optimization | GAP | 100 | 0 | 95 | 0 | 80% | 30% |
| ✗ BLIND_B2 | optimization | GAP | 100 | 0 | 95 | 0 | 80% | 30% |
| ✗ BLIND_B3 | optimization | GAP | 100 | 0 | 95 | 0 | 80% | 30% |
| ✓ BLIND_C1 | evaluation | OK | 100 | 100 | 95 | 86 | 15% | 0% |
| ✓ BLIND_C2 | evaluation | OK | 100 | 100 | 95 | 86 | 15% | 0% |
| ✓ BLIND_D1 | hybrid     | OK | 60 | 100 | 95 | 86 | 15% | 0% |
| ✓ BLIND_D2 | hybrid     | OK | 60 | 100 | 95 | 86 | 15% | 0% |

## Gap Analysis

- **6 problems blocked** by Knowledge Preflight — 优化/预测模型族缺失
- **Recommendation**: 补充 NSGA-II, MILP, ARIMA, XGBoost 知识资产后重新测试

## Architecture Validation Summary

| Claim | Evidence |
|-------|----------|
| Preflight prevents uninformed generation | 6 problems correctly blocked |
| Decision accuracy is robust across types | Avg 92 across 10 problems |
| Human correction cost is manageable | HCC avg 54% |
| Wrong confidence is controlled | WCR avg 18% |