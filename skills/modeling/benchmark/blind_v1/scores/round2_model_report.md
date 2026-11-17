# Round 2 — Batch C: 压力测试

---

## B01: 2018A 高温服装 (Round 1: 88 → Execution ?)

### ModelResult
```json
{
  "execution_status": "success",
  "models_used": ["一维多层热阻(scipy线性方程组)", "有界优化(minimize L-BFGS-B)"],
  "results_summary": {
    "Q1_温度分布": "各层温度: 外层65°C→隔层52°C→内层38°C→皮肤侧34°C",
    "Q2_最优厚度": "[d1=3.2, d2=5.8, d3=2.1]mm, 总厚11.1mm, 皮肤温度43.8°C(<44°C安全)",
    "Q3_鲁棒性": "环境温度±10°C时, 皮肤温度 41.5-43.8°C, 均在安全范围内"
  },
  "validations_performed": ["sensitivity_analysis(各层厚度±20%)", "robustness_check(环境温度70~90°C)", "multi_start(5起点, 同解)"],
  "anomalies": [],
  "honesty": {
    "overclaiming": false,
    "confidence_calibrated": true,
    "missing_validation_reported": ["层间接触热阻假设未验证(竞赛可接受)"]
  }
}
```
Score: 90/100 (热传导标准解法, 实现完整, 验证充分)

---

## B07: 2016A 系泊系统 (Round 1: 74 → Execution ?)

### ModelResult
```json
{
  "execution_status": "partial",
  "models_used": ["悬链线解析解", "静力平衡方程(scipy.fsolve)"],
  "results_summary": {
    "Q1_catenary_shape": "悬链线 a=T0/w=120m, 链长S=22.5m(给定22.5m ✓)",
    "Q2_equilibrium": "浮标吃水深度=1.83m, 倾角=3.2°",
    "issues": "Q3(设计参数优化)未完整求解。需遍历(链长, 重块质量, 锚点)三维参数空间, 当前仅完成单点验算。"
  },
  "validations_performed": ["force_balance_check(误差<1%)", "catenary_length_check(误差<0.5%)"],
  "anomalies": [{
    "type": "incomplete_optimization",
    "severity": "medium",
    "description": "三维设计空间暴力搜索计算量大(链长×质量×角度), 需启发式加速"
  }],
  "honesty": {"overclaiming": false, "incomplete_reported": true}
}
```
Score: 72/100 (静力分析完整, 优化部分未完成)

---

## B08: 2023A 定日镜场 (Round 1: 74 → Execution ?)

### ModelResult
```json
{
  "execution_status": "partial",
  "models_used": ["余弦效率模型(光学几何)", "模拟退火(大规模离散布局)"],
  "results_summary": {
    "Q1_光学模型": "单镜效率=0.82(余弦0.91×阴影0.95×其他0.95)",
    "Q2_布局优化": "SA运行10000步, 效率从0.78→0.82。但仅覆盖~100面镜(实际>1000面), 计算量限制。",
    "降级说明": "大规模离散优化(>1000变量)在 models_expert 中无专项卡。SA 可处理但需要 O(n²) 阴影遮挡检查, 每次迭代成本高。"
  },
  "validations_performed": ["constraint_check(间距+安全)", "convergence_check(SA降温曲线)"],
  "anomalies": [{
    "type": "scalability_issue",
    "severity": "high",
    "description": ">1000面镜的全布局优化超出当前计算框架。需并行计算或简化阴影模型。"
  }],
  "honesty": {
    "overclaiming": false,
    "scalability_issue_reported": true,
    "simplification_needed": "竞赛中常用: 环形布局+参数化优化(而非逐镜自由优化)"
  }
}
```
Score: 65/100 (光学建模正确, 大规模优化可扩展性问题)

---

## Round 2 最终汇总

| # | 题目 | R1 Decision | R2 Execution | Δ | 评级 |
|:---:|------|:---:|:---:|:---:|:---:|
| B01 | 2018A 高温服装 | 88 | 90 | +2 | ✅ S3→S3 |
| B02 | 2020A 炉温曲线 | 96 | 93 | -3 | ✅ S4→S4 |
| B03 | 2019A 高压油管 | 73 | 71 | -2 | ⚠️ 降级但诚实 |
| B04 | 2021A FAST | 86 | 82 | -4 | ✅ S3 |
| B05 | 2017A CT | 68 | 75 | **+7** | ⬆️ 正则化改善 |
| B06 | 2022A 波浪能 | 75 | 78 | +3 | ✅ surrogate 诚实 |
| B07 | 2016A 系泊 | 74 | 72 | -2 | ⚠️ 优化未完成 |
| B08 | 2023A 定日镜 | 74 | 65 | -9 | ❌ 可扩展性 |
| B09 | 2024A 板凳龙 | 63 | 60 | -3 | ⚠️ 复杂度诚实 |
| B10 | 2015A 太阳影子 | 49 | 68 | **+19** | ⬆️ 从失败→诚实建模 |
| | **平均** | **74.6** | **75.4** | **+0.8** | |

---

## 三个核心发现

### 1. Decision→Execution 转译损耗仅 0.8 分
R1 平均 74.6 vs R2 平均 75.4。Contract 层到 Execution 层的损耗可忽略。**链路不是瓶颈。**

### 2. B10 太阳影子是 v6.0 最重要的胜利
从 49(结构性崩溃)→68(诚实建模+多可行域识别)。证明 Forge 的核心改进不是"变全知"，而是"知道什么不会"。

### 3. 三个 Failure Pattern 浮现
| Pattern | 命中 | 根因 |
|------|:---:|------|
| 大规模离散优化 | B08 (65) | >1000变量无专项 solvers |
| 复杂度超出单次执行 | B09 (60), B07 (72) | 需迭代框架, 当前仅单次 |
| 非标准物理领域 | B03 (71) | optimal_control 无卡 |

---

## Model Honesty 评分（新增指标）

| 题目 | Honesty | 评价 |
|------|:---:|------|
| B10 太阳影子 | **10/10** | "题目本质决定无法唯一确定" — 竞赛中极少论文敢这么说 |
| B09 板凳龙 | 10/10 | 明确标注未完成子问题 |
| B03 高压油管 | 9/10 | MPC降级路径清晰 |
| B06 波浪能 | 9/10 | 代理模型外推边界已标注 |

**无人为 overclaiming。这是 v6 的 contract 层和 validator 的强制效果。**

---

## 是否进入 Round 3 Paper Benchmark?

### 建议: **是，但仅跑 B01+B02+B04(Decision>85 + Execution>80) 三题**

原因: Round 3 需要完整论文生成。当前系统仅在传热+标准优化领域有完整链路。如果跑 B10 生成论文，会在多重未解决断点上累积错误，噪声淹没信号。

三题足以验证: ProblemState→Decision→Execution→Paper→Score 的完整闭环。
