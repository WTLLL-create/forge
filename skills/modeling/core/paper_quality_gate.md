# Paper Quality Gate — v6.4.1

> **【2026-09-08 表格条款废止】** 本门禁中 P1-7“缺必做表格”、P2-6“表格数<题型下限”
> 以及任何按 PaperStyleContract 固定表格名单/数量配额的扣分，均已被
> `standards/academic_table_standard.md` 取代：成稿表格无固定数量配额，列结构与数量
> 由来源数据和锁定的 `table_spec.json` 决定。P2-3“三线表格式错误”仍有效，但判定以
> 统一规范及独立表格检查器为准。本文件目前是指导文档，其表格扣分项无可执行实现。

> 位置: L6.5 → L7 之间的硬门禁  
> 职责: 论文在提交给 Reviewer 之前，必须通过所有 P0 和 P1 检查  
> 原则: 不合格的论文不应该被评分，应该被退回修改

---

## Gate 执行流程

```
L6.5 PaperComplianceReport
        ↓
    ┌───────────────────┐
    │ P0 Fatal Gate     │ ← 任一失败 → 退回 L5.5/L6, 不进入评分
    └───────┬───────────┘
            ↓ (P0 全部通过)
    ┌───────────────────┐
    │ P1 Critical Gate  │ ← 任一失败 → 标记为 "论文不合格", 仍可评分但分数封顶
    └───────┬───────────┘
            ↓ (P1 全部通过)
    ┌───────────────────┐
    │ P2 Standard Gate  │ ← 失败 → 记录扣分项, 不阻止评分
    └───────┬───────────┘
            ↓
        L7 Reviewer (ScoreCard)
```

---

## P0 Fatal Gate (致命级 — 触发 = 中止评分)

| # | 检查项 | 来源 | 判定规则 |
|:---:|------|------|------|
| P0-1 | **模型无数学表达式** | layout_profile.json P0 | 论文中所有模型均无 LaTeX 公式 → FATAL |
| P0-2 | **优化题无求解过程** | layout_profile.json P0 | optimization 题无算法描述或求解步骤 → FATAL |
| P0-3 | **结果与模型矛盾** | layout_profile.json P0 | 如 η>1, 概率>1, R²且无解释 → FATAL |
| P0-4 | **参考文献 < 3篇** | layout_profile.json P0 | 参考文献 < 3 → FATAL |
| P0-5 | **缺摘要** | PaperStyleContract | 摘要节为空 → FATAL |
| P0-6 | **模型章节缺六段式** | ModelFormalization | 任一模型的 假设/符号/公式/求解/参数/解释 缺失 → FATAL |
| P0-7 | **公式编号缺失** | PaperStyleContract | 有公式但全部无编号 → FATAL |

**P0 任一失败 → 论文状态: REJECTED_NO_SCORE**
**系统行为: 输出 P0 失败报告, 不生成 ScoreCard, L8 FailureRecord 记录 P0 命中**

---

## P1 Critical Gate (严重级 — 触发 = 分数封顶)

| # | 检查项 | 来源 | 判定规则 |
|:---:|------|------|------|
| P1-1 | **缺收敛曲线 (优化题)** | layout_profile.json P1 | A题优化模型无收敛曲线 → D4 -5 |
| P1-2 | **缺误差分析 (预测题)** | layout_profile.json P1 | B题预测模型无误差分析 → D4 -5 |
| P1-3 | **缺敏感性分析** | layout_profile.json P1 | 评价/优化类缺敏感性分析 → D5 -3 |
| P1-4 | **关键变量未定义** | layout_profile.json P1 | 公式中出现未在 symbols 中定义的变量 → D4 -3 |
| P1-5 | **缺模型评价/验证章节** | CORE_MANIFEST L5 | 论文无独立的模型评价章 → D5 -5 |
| P1-6 | **缺必做图表** | PaperStyleContract | required_figures 中 mandatory=true 的图全部缺失 → D6 -3 |
| P1-7 | **缺必做表格** | PaperStyleContract | required_tables 全部缺失 → D6 -2 |
| P1-8 | **公式 < 题型下限** | PaperStyleContract | evaluation 题型公式 < 10 个 → D4 -3 |

**P1 任一失败 → 论文分数封顶 = max(70, 原始分数)**
**即: P1 命中 → 最高不超过 70 分**

---

## P2 Standard Gate (标准级 — 触发 = 记录扣分)

| # | 检查项 | 来源 | 扣分 |
|:---:|------|------|:---:|
| P2-1 | 公式编号不连续 | layout_profile.json P2 | D6 -1 |
| P2-2 | 图表编号不连续 | layout_profile.json P2 | D6 -1 |
| P2-3 | 三线表格式错误 (有竖线) | layout_profile.json P2 | D6 -1 |
| P2-4 | 引用格式不一致 | layout_profile.json P2 | D6 -1 |
| P2-5 | 图标题位置错误 (应在下方) | layout_profile.json P2 | D6 -1 |
| P2-6 | 表格数 < 题型下限 | PaperStyleContract | D6 -1 |
| P2-7 | 图表数 < 题型下限 | PaperStyleContract | D6 -1 |
| P2-8 | 公式有前导无解释 | PaperStyleContract.equation | D6 -1 |
| P2-9 | 摘要字数 < 700 (CUMCM) | PaperStyleContract | D6 -1 |

---

## Gate 输出: PaperGateReport

```json
{
  "paper_id": "CUMCM_2026_D",
  "timestamp": "2026-08-04T21:55:00",
  "gate_version": "v6.4.1",

  "p0_fatal": {
    "passed": false,
    "failures": [
      {"id": "P0-6", "item": "模型章节缺六段式", "detail": "Q3 TOPSIS 模型: 缺数学表达(核心公式), 缺算法描述, 缺参数解释"}
    ],
    "block_count": 1
  },

  "p1_critical": {
    "passed": false,
    "failures": [
      {"id": "P1-3", "item": "缺敏感性分析", "detail": "FC阈值未经敏感性验证; TOPSIS指标集未经敏感性验证"},
      {"id": "P1-6", "item": "缺必做图表", "detail": "评价类题型缺失: 权重分布图, 评价结果排名图, 敏感性分析图"}
    ],
    "score_cap": 70,
    "block_count": 2
  },

  "p2_standard": {
    "passed": false,
    "failures": [
      {"id": "P2-3", "item": "三线表格式错误", "detail": "所有表格包含竖线和双线, 未使用三线表格式"},
      {"id": "P2-4", "item": "引用格式不一致", "detail": "部分引用使用非上标格式"},
      {"id": "P2-8", "item": "公式有前导无解释", "detail": "Q2标志物筛选公式缺乏变量解释"}
    ],
    "deductions": 3
  },

  "verdict": "REJECTED_NO_SCORE",
  "reason": "P0-6 (模型缺数学表达) 触发 Fatal Gate。论文在补充完整的数学公式和算法描述之前, 不能进入评分阶段。",
  "fix_instructions": [
    "为每个模型 (Q1拟合 / Q2标志物筛选 / Q3 CRITIC-TOPSIS) 补充完整的数学表达：" ,
    "  - 核心公式 (LaTeX) 含编号",
    "  - 符号定义表",
    "  - 算法步骤或伪代码",
    "  - 参数解释" ,
    "在 L5.5 ModelFormalization 通过后, 重新运行 L6.5 → Gate → L7"
  ]
}
```
