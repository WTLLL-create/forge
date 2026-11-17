# L6.5 Paper Engineering Layer — v6.4.1

> **【2026-09-08 表格条款废止】** 本文“必做表格 required_tables 全部至少出现1次”
> “表格数量区间”等固定配额检查已被 `standards/academic_table_standard.md` 取代，
> 不再作为成稿要求；表格以锁定的 `table_spec.json` 为准。

> 定位: L6 PaperReasoning 和 L7 Generation 之间的论文工程层  
> 职责: 将 PaperSection (内容骨架) + ModelFormalization (数学表达) + PaperStyleContract (格式约束) 转化为符合竞赛规范的 docx  
> 状态: active (v6.4.1 新增)

---

## 输入

| 来源 | 内容 | 文件 |
|------|------|------|
| L6 PaperReasoning | 论文章节骨架 (sections, content_blocks, argument_trace) | `paper_section.schema.json` |
| L5.5 Formalization | 模型数学表达 (assumptions, symbols, core_formulas, algorithm) | `model_formalization.schema.json` |
| PaperStyleContract | 格式约束 (字体/页面/表格/公式/题型要求) | `paper_style_contract.schema.json` |

## 输出

| 产物 | 说明 |
|------|------|
| 格式合规的 PaperSection (扩充版) | 在原文骨架基础上注入公式、符号、格式标记 |
| PaperComplianceReport | 格式/内容/公式 三段合规检查报告 |

---

## 规则 1: 模型章节强制六段式

每个模型的论文章节必须包含以下六个元素。缺少任一 = 不能进入 L7 Generation。

```
§X.X 模型建立
  ├── 1. 模型假设      (来自 ModelFormalization.assumptions)
  ├── 2. 符号定义      (来自 ModelFormalization.symbols)
  ├── 3. 数学表达      (来自 ModelFormalization.core_formulas)
  ├── 4. 求解方法      (来自 ModelFormalization.algorithm)
  ├── 5. 参数解释      (来自 ModelFormalization.algorithm.parameters)
  └── 6. 结果解释      (来自 ModelFormalization.result_interpretation)
```

**Gate**: 如果 ModelFormalization 为空或 core_formulas 为空 → **中止**，返回错误报告。

---

## 规则 2: 公式注入规范

### 2.1 每个公式必须

- 编号: `(1), (2), ...` 连续递增
- 前导句: 公式前至少有一句引导文字（如 "目标函数定义如下:"）
- 变量解释: 公式后必须逐符号解释（或引用符号定义表）

### 2.2 对 TOPSIS 模型，必须出现全部四公式

```
(1) 归一化:  r_{ij} = x_{ij} / sqrt(Σ x_{ij}^2)
(2) 加权:    v_{ij} = w_j · r_{ij}
(3) 距离:    D_i^+ = sqrt(Σ (v_{ij} - v_j^+)^2), D_i^- = sqrt(Σ (v_{ij} - v_j^-)^2)
(4) 贴近度:  C_i = D_i^- / (D_i^+ + D_i^-)
```

少任一个 → 不合规。

### 2.3 对 CRITIC 赋权，必须出现

```
(5) 对比强度:  σ_j = std(X_j)
(6) 冲突性:    R_j = Σ (1 - |r_{jk}|)
(7) 信息量:    C_j = σ_j · R_j
(8) 权重:      w_j = C_j / Σ C_k
```

---

## 规则 3: 表格规范

### 3.1 三线表格式

所有数据表必须使用三线表:
```
顶线: 粗线 (1.5pt)
表头分隔线: 细线 (0.5pt)  
底线: 粗线 (1.5pt)
禁止: 竖线、双线、彩色背景
```

### 3.2 每个表格必须

- 表标题在上方（黑体 10.5pt, 加粗）
- 标题格式: `表X {表格内容描述}`

---

## 规则 4: 图表数量检查

根据 PaperStyleContract.problem_type_templates 中当前题型的 required_figures/required_tables，检查:

| 检查项 | 通过条件 |
|------|------|
| 必做图表 | 全部 required_figures 在论文中至少出现1次 |
| 必做表格 | 全部 required_tables 在论文中至少出现1次 |
| 公式总数 | 在 formula_count_range 范围内 |
| 图表总数 | 在 figure_count_range 范围内 |
| 表格总数 | 在 table_count_range 范围内 |

---

## 规则 5: 摘要规范

从 PaperStyleContract.abstract_rules:
- 字数: 700-1000 字 (CUMCM)
- 禁止公式
- 禁止引用
- 关键词: 3-7 个

---

## 规则 6: 参考文献规范

从 PaperStyleContract.document_spec.reference:
- 格式: GB/T 7714-2015
- 最少: 5 篇
- 引用: 上标方括号 [1], [2-4]

---

## PaperComplianceReport 结构

```json
{
  "paper_id": "CUMCM_2026_D",
  "timestamp": "2026-08-04T21:50:00",
  "model_section_check": {
    "models_checked": 3,
    "all_six_sections_present": true,
    "failures": []
  },
  "formula_check": {
    "total_formulas": 12,
    "all_numbered": true,
    "required_formulas_present": false,
    "missing": [
      "TOPSIS归一化公式缺失",
      "TOPSIS距离公式缺失"
    ]
  },
  "table_check": {
    "required_tables_present": true,
    "all_three_line_style": false,
    "issues": ["表1-4未使用三线表, 包含竖线"]
  },
  "figure_count_check": {
    "required_figures": ["指标体系层次图", "权重分布图", "评价结果排名图"],
    "present": 0,
    "missing": 3,
    "status": "FAIL"
  },
  "abstract_check": {
    "present": false,
    "status": "FAIL"
  },
  "reference_check": {
    "count": 8,
    "min_required": 5,
    "status": "PASS"
  },
  "overall": {
    "pass": false,
    "blocking_issues": 3,
    "can_proceed_to_generation": false
  }
}
```
