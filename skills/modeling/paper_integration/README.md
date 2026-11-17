# Paper Integration — 论文集成层

> 阶段 14：连接模型结果到论文输出的完整管道
>
> 这层回答：Agent 算出结果后，怎么自动变成论文？

---

## 管道总览

```
模型求解结果（数值/图表/分析文本）
    │
    ▼
model_to_paper_mapping.md    ← 模型→论文结构映射
    │
    ▼
section_generation_rules.md  ← 每章从哪来、怎么写
    │
    ├── result_to_content_rules.md  ← 数值→论文语言转换
    ├── figure_table_rules.md       ← 图类型与格式规范（表格条款已废止，见下）
    └── latex_output_rules.md       ← LaTeX 最终输出规范
    │
    │  表格唯一依据：standards/academic_table_standard.md + 锁定的 table_spec.json
    ▼
math-modeling-paper Skill    ← 执行层：调 python-docx 或 LaTeX
    │
    ▼
outputs/论文.docx 或 论文.pdf
```

## 与其他层的关系

```
skills/modeling/
├── 数学建模题型识别.md         ← 第1环
├── 模型选择决策树.md           ← 第2环
├── 建模任务状态管理.md         ← 状态机
├── models/                     ← 模型知识库（阶段13）
│
├── paper_integration/          ← ★ 论文集成层（阶段14）
│   ├── model_to_paper_mapping.md    → 模型知识→论文结构
│   ├── section_generation_rules.md  → 10个标准章节的生成规则
│   ├── figure_table_rules.md        → 按模型类型的图要求（表格条款已废止，统一以 standards/academic_table_standard.md 为准）
│   ├── latex_output_rules.md        → LaTeX 输出规范
│   └── result_to_content_rules.md   → 数值→中文表达转换
│
├── 论文生成流程.md             ← 论文生成 Skill 触发
└── 文档输出流程.md             ← .docx/.pdf 格式规范
```

## 目录结构

```
paper_integration/
├── README.md                    ← 本文件
├── github_sources.md            ← 论文生成系统 GitHub 调研
├── model_to_paper_mapping.md    ← 10个模型→论文章节映射
├── section_generation_rules.md  ← 10个标准章节的输入/规则/检查
├── result_to_content_rules.md   ← 数值→论文语言转换规则
├── figure_table_rules.md        ← 按模型类型的图规范（表格条款已废止，见 standards/academic_table_standard.md）
└── latex_output_rules.md        ← LaTeX 格式与编译输出
```
