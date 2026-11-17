# models_expert/ — 专家模型知识卡

> 不是 API 文档，而是决策指南：何时用、何时不用、为何失败、如何创新、论文怎么写。

## 模型家族

| 家族 | 目录 | 卡片数 | 覆盖 |
|------|------|:---:|------|
| optimization | `optimization/` | 3 | LP, MILP, NSGA-II |
| prediction | `prediction/` | 3 | ARIMA, RF, XGBoost |
| evaluation | `evaluation/` | 1 | TOPSIS |
| classification | `classification/` | 1 | SVM |
| clustering | `clustering/` | 1 | KMeans |
| statistics | `statistics/` | 1 | Bayesian |
| **physics** | `physics/` | **3** | mechanism_model, heat_transfer, parameter_identification |

## 卡片标准格式

每张卡片必须回答：
1. **决策入口** — 三问判定，条件→模型
2. **不适用** — 什么场景绝对不能用
3. **失败模式** — 用错了会怎样，怎么修
4. **创新空间** — L1-L5 创新等级对应
5. **论文表达** — 可直接使用的论证段落模板
