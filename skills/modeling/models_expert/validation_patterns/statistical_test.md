# 统计检验决策链（参数 vs 非参数自动选择）

> 目的：防止小样本下盲用 ANOVA，根据数据特征自动选择参数/非参数方法。
> 修复来源：v7.8 Application Calibration — 6~7时间点/品种下 Shapiro-Wilk 功效不足。

---

## 决策流程

```
数据 → 检验正态性
│
├─ n ≥ 30
│   ├─ Shapiro-Wilk p ≥ 0.05 → 正态 → ANOVA
│   └─ Shapiro-Wilk p < 0.05 → 非正态 → Kruskal-Wallis
│
└─ n < 30（小样本）
    ├─ 同组内 n < 8 → Shapiro-Wilk 功效不足
    │   → 默认使用 Kruskal-Wallis（非参数）
    │   → 同时跑 ANOVA 作为参考（论文中注明"小样本下仅供参考"）
    │
    └─ 同组内 n ≥ 8
        ├─ Shapiro-Wilk p ≥ 0.05 → ANOVA
        └─ Shapiro-Wilk p < 0.05 → Kruskal-Wallis
```

---

## 事后多重比较

| 前提方法 | 多重比较 | 适用条件 |
|----------|----------|----------|
| ANOVA 通过 | Tukey HSD | 方差齐性（Levene p≥0.05） |
| ANOVA 通过，方差不齐 | Games-Howell | 方差不齐 |
| Kruskal-Wallis | Dunn's test (Bonferroni校正) | 非参数通用 |

---

## 论文表述模板

### 正态性通过时

> "经 Shapiro-Wilk 检验，各组数据满足正态性假设（p>0.05），
> 采用单因素方差分析（ANOVA）检验组间差异，
> 事后多重比较采用 Tukey HSD 法。"

### 小样本/正态性不通过时

> "鉴于样本量较小（n=X），正态性检验功效有限，
> 采用非参数 Kruskal-Wallis 检验作为主要组间差异分析方法，
> 同时报告 ANOVA 结果作为参考。"

---

## 关联：ANOVA与字母标记法

题目数据中的字母标记法（a,b,c,d...）本质是 Tukey HSD 的结果表达。
论文中应说明：

> "附件数据中的字母标记法采用 Tukey HSD 多重比较（p<0.05），
> 同一行中不同字母表示该化合物在该时间点间存在显著差异。"

这可以作为验证模型结论的外部参照——如果模型识别的氧化标志物
在原始数据中也存在显著的组间差异标记，则结论更加可信。

---

## 训练案例

### Case: 2026 D题 香玲核桃油 某VOC的6时间点差异

```
n = 6（每组6个时间点）
n < 8 → Shapiro-Wilk 功效不足
→ 默认使用 Kruskal-Wallis
→ 同时跑 ANOVA 作为参考
→ 论文："小样本下以 Kruskal-Wallis 为主，ANOVA 结果作为参考"
```
