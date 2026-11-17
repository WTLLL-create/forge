# Blind Benchmark v1 — Round 1 Decision Report

> 日期: 2026-08-04 | 10 道 A 题 Decision 阶段 | 禁止人工修正

---

## 总体评分

| # | 题目 | 问题识别(25) | 变量/目标(20) | 模型选择(25) | 候选比较(15) | 风险识别(15) | **总分** | 评级 |
|:---:|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| B01 | 2018A 高温服装 | 23 | 18 | 23 | 12 | 12 | **88** | S3 |
| B02 | 2020A 炉温曲线 | 24 | 20 | 24 | 14 | 14 | **96** | S4 |
| B03 | 2019A 高压油管 | 20 | 16 | 18 | 10 | 9 | **73** | S2_mid |
| B04 | 2021A FAST馈源 | 22 | 18 | 22 | 12 | 12 | **86** | S3 |
| B05 | 2017A CT标定 | 18 | 14 | 18 | 8 | 10 | **68** | S2_low |
| B06 | 2022A 波浪能 | 20 | 15 | 20 | 10 | 10 | **75** | S2_mid |
| B07 | 2016A 系泊系统 | 19 | 16 | 20 | 9 | 10 | **74** | S2_mid |
| B08 | 2023A 定日镜场 | 21 | 17 | 18 | 8 | 10 | **74** | S2_mid |
| B09 | 2024A 板凳龙 | 16 | 14 | 17 | 7 | 9 | **63** | S2_low |
| B10 | 2015A 太阳影子 | 14 | 10 | 12 | 5 | 8 | **49** | S1 |
| | **平均** | **19.7** | **15.8** | **19.2** | **9.5** | **10.4** | **74.6** | S2_mid |

---

## Failure Pattern 分析

### Pattern 1: 候选比较不足 (7/10 题)

| 题目 | 候选数 | 问题 |
|------|:---:|------|
| B03 高压油管 | 2 | PID 被排除但未给出 "什么条件下 PID 就够了" |
| B05 CT标定 | 1 | "逆问题" 没有比较 Tikhonov vs 贝叶斯反演 |
| B07 系泊系统 | 1 | Q2 未比较不同悬链线模型 (弹性/非弹性) |
| B08 定日镜场 | 1 | SA vs GA vs MILP 未展开对比 |
| B09 板凳龙 | 1 | 路径规划未比较样条插值 vs 优化 |
| B10 太阳影子 | 1 | 反演方法未比较 LS vs MCMC |

**根因**: `model_competition_engine.md` 的"≥2候选"规则存在，但 Expert Decision 执行时没有强制执行。**Contract Validator 应拒绝 alternatives_considered 不满≥2 的 DecisionContract**。

### Pattern 2: 模型家族未覆盖 (4/10 题)

| 题目 | 缺失模型家族 | 影响 |
|------|------|------|
| B03 高压油管 | fluid_dynamics | 只能用简化假设绕过 |
| B05 CT标定 | inverse_problem | 依赖通用 stat/optimize 凑合 |
| B07 系泊系统 | structural_mechanics | 悬链线模型需完全从零推导 |
| B10 太阳影子 | astronomy/geodesy | 天球几何完全无覆盖 — **决定性失败** |

**根因**: `models_expert/physics/` 只有 3 张卡（传热+机理+参数辨识）。A 题的物理领域远超这 3 个。

### Pattern 3: 约束遗漏 (5/10 题)

| 题目 | 遗漏约束 |
|------|------|
| B03 | 电磁阀响应时间（仅给了开关频率） |
| B05 | 探测器噪声模型（Poisson/Gaussian） |
| B08 | 定日镜跟踪精度误差 |
| B09 | 队员步长/臂长约束 |
| B10 | 大气折射修正 |

**根因**: ProblemIntelligence 只从题目文字提取约束，未从问题领域推导隐含约束。

### Pattern 4: 难度错判 (2/10 题)

| 题目 | Forge 判断 | 实际 |
|------|------|------|
| B09 板凳龙 | 低估: "几何+优化" | 实际是多刚体运动学+非线性规划, 近年级最难 A 题 |
| B10 太阳影子 | 严重低估: 用 mechanism+param_id 覆盖 | 实际是严重不适定反问题, 信息量根本不足以唯一确定 |

---

## 模型家族覆盖矩阵

| 家族 | 已覆盖? | 涉及题目数 | 优先级 |
|------|:---:|:---:|:---:|
| heat_transfer | ✅ | B01, B02 | — |
| mechanism_model | ✅ | B01-B09 | — |
| parameter_identification | ✅ | B05 | — |
| fluid_dynamics | ❌ | B03 | P1 |
| structural_mechanics | ❌ | B04, B07 | P1 |
| inverse_problem | ❌ | B05, B10 | P1 |
| discrete_optimization | ❌ | B08 | P2 |
| kinematic_modeling | ❌ | B09 | P2 |
| surrogate_optimization | ❌ | B06 | P2 |
| astronomical_modeling | ❌ | B10 | P3 |

---

## 改进优先级

| 优先级 | 动作 | 预期提升 |
|:---:|------|:---:|
| **P0** | Contract Validator 强制 `alternatives_considered ≥ 2` | 候选比较分 +6 (15→21 平均) |
| **P0** | 补 fluid_dynamics + structural_mechanics 模型卡 (2张) | B03/B07 模型选择 +5 |
| **P1** | ProblemIntelligence 增加领域隐含约束推导 | 约束遗漏 -3→-1 |
| **P1** | 补 inverse_problem 模型卡 (1张) | B05/B10 模型选择 +8 |
| **P2** | 补 discrete_optimization + kinematic + surrogate 卡 (3张) | B06/B08/B09 覆盖 |
| **P3** | 10 题重跑 Decision 验证改进 | 目标: 平均 85+ |

---

## 结论

**Round 1 平均 74.6 分 (S2_mid)**。Forge 在熟悉领域（传热+标准优化）表现优秀 (B01=88, B02=96)。但在三个方向系统性地弱：

1. **候选对比强制执行不足** — 7/10 题只有 0-1 个候选 → 这是 contract 层的问题，修起来最快
2. **模型家族覆盖集中在传热** — A 题实际需要 10+ 个物理子领域，目前只有 3 个
3. **问题难度识别的天花板** — B09 板凳龙和 B10 太阳影子暴露了 Forge 对非常规领域缺乏判断力

**最危险的发现**: B10 (2015A 太阳影子) 的 49 分是结构性失败，不是参数可调的问题——models_expert 完全无法覆盖天球几何。

**最积极的发现**: B02 (2020A 炉温曲线) 的 96 分验证了 contract 层的设计——当模型家族和决策规则都就位时，Forge 可以输出接近完美的决策。
