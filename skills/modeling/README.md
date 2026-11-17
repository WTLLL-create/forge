# skills/modeling/ — 数学建模专家知识层

## Agent 架构总图

```
                          用户题目（.docx + .xlsx）
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │   agent_system/          │ ← 顶层调度
                     │   state_machine.md       │   (S0→S8 状态机)
                     │   workflow_execution.md  │
                     └───────────┬─────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │   数学建模题型识别.md     │ ← 决策层
                     │   (6大类 + 解法层级)      │
                     └───────────┬─────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │   模型选择决策树.md       │
                     │   (6棵决策树 + Failover)  │
                     └───────────┬─────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
          ┌──────────────┐ ┌──────────┐ ┌──────────────┐
          │  models/     │ │ 模型求解  │ │  模型调用     │
          │ (10个模型)   │ │  流程.md │ │  接口.md     │
          └──────┬───────┘ └────┬─────┘ └──────┬───────┘
                 │              │              │
    ┌────────────┼──────────────┼──────────────┼────────────┐
    │            │              │              │            │
    ▼            ▼              ▼              ▼            ▼
┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ data_  │ │numerical │ │ case_    │ │ paper_   │ │ paper_   │
│process │ │_computing│ │ library/ │ │ case_    │ │ templates│
│  ing/  │ │    /     │ │          │ │ library/ │ │    /     │
└────┬───┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │          │            │            │            │
     └──────────┼────────────┼────────────┼────────────┘
                │            │            │
                ▼            ▼            ▼
          ┌──────────────────────────────────┐
          │       paper_integration/         │ ← 集成层
          └──────────────┬───────────────────┘
                         │
                         ▼
          ┌──────────────────────────────────┐
          │   document_engineering/          │ ← 输出层
          │   + paiban_skill/               │
          └──────────────┬───────────────────┘
                         │
                         ▼
                    .docx / .pdf
                         │
                         ▼
          ┌──────────────────────────────────┐
          │   reviewer_agent/ (Layer 2)      │ ← 审查层 (S7)
          │   skills/review/   (Layer 1)     │
          └──────────────┬───────────────────┘
                         │
                    pass / fail
```

参考状态机：`agent_system/state_machine.md` (S0→S8)

---

## 文件清单（按架构层次）

### 决策层（知识规则）

| 文件 | 定位 | 输入 → 输出 |
|------|------|-------------|
| `数学建模题型识别.md` | 6大类题型判定 + 解法层级 | 题目文本 → 类型标签 |
| `模型选择决策树.md` | 6棵决策树 + Failover + 优化子类型 | 问题特征 → 模型名称 |
| `github_sources.md` | 7个参考仓库的调研记录 | —（知识溯源） |

### 调度层（流程控制）

| 文件 | 定位 | 状态机对应 |
|------|------|:---:|
| `agent_system/state_machine.md` | **Canonical 状态机**（S0→S8，含Failover） | — |
| `agent_system/workflow_execution.md` | 9步执行序列 + Agent角色分配 | S0→S8 |
| `模型调用接口.md` | 模块间 JSON 数据交换格式 | S2→S3→S4 |
| `模型求解流程.md` | 5步标准求解（形式化→参数→求解→运行→输出） | S4 |
| `建模任务状态管理.md` | 7状态流转 + 4种 Failover（参考用） | 参考 |
| `数学建模完整流程.md` | 10阶段端到端操作手册（教学视角） | 对应 S0→S8 |

### 能力层（可执行模块）

| 目录 | 定位 | 状态机对应 |
|------|------|:---:|
| `models/` | 10个模型知识文档（12段统一模板） | S2 |
| `data_processing/` | 6步数据管道 + pandas速查 + 4案例 | S3 |
| `numerical_computing/` | numpy/scipy速查 + API映射 + 4案例 | S4 |
| `case_library/` | 3类案例（预测/优化/评价各3个） | S2 |
| `paper_case_library/` | 国赛案例 + 创新分析 + 写作模式 | S2/S6 |

### 输出层（论文生成）

| 目录 | 定位 | 状态机对应 |
|------|------|:---:|
| `paper_integration/` | 模型→论文映射 + 章节生成规则 | S6 |
| `paper_templates/` | 10个模板 + 模板选择决策 | S6 |
| `document_engineering/` | Pandoc/Typst/Word 转换管道 | S6 |
| `paiban_skill/` | LaTeX/Word 排版规则 | S6 |

### 审查层（质量保证）

| 目录 | 定位 | 状态机对应 |
|------|------|:---:|
| `reviewer_agent/` | **Layer 2**: Canonical AI深度审查（6维100分） | S7 |
| `../skills/review/math-modeling/` | **Layer 1**: 队员快速自查清单 | S7 |

详见 `reviewer_agent/review_architecture.md`

### 辅助层（专项能力）

| 文件 | 定位 |
|------|------|
| `数据分析流程.md` | 7 部分 EDA 工作流 |
| `模型验证方法.md` | 4 类题型验证体系 |
| `论文生成流程.md` | 8 步论文生成引擎 |
| `文档输出流程.md` | .docx/.pdf 规范 |
| `surrogate_optimization.md` | 代理优化指南 |
| `time_alignment_fusion.md` | 时间对齐+多源融合 |

### 外部库集成层（GitHub 仓库知识蒸馏）

> 2026-07-30 新增：从 4 个核心开源仓库深度学习后蒸馏的实战参考文档。
> 每个文件专注于"数模场景中最常用的 API 和最佳实践"。

| 文件 | 来源仓库 | 服务于 |
|------|----------|:---:|
| `data_processing/pandas_integration.md` | pandas-dev/pandas (49k+ stars) | S3 数据处理 6 步管道 |
| `numerical_computing/scipy_integration.md` | scipy/scipy (14.8k+ stars) | S4 求解 5 步流程 |
| `models/sklearn_integration.md` | scikit-learn/scikit-learn (~67k stars) | S2 模型选择 + S4 ML 求解 |
| `jupyterlab_integration.md` | jupyterlab/jupyterlab (15k+ stars) | 全流程实验环境 |

### 可视化库集成层（2026-07-30 第二批）

> 从 4 个可视化开源仓库深度学习后蒸馏的论文图表实战参考。

| 文件 | 来源仓库 | 服务于 |
|------|----------|:---:|
| `paper_integration/matplotlib_integration.md` | matplotlib/matplotlib (~23k stars) | 论文主力绘图 |
| `paper_integration/seaborn_integration.md` | mwaskom/seaborn (~13.7k stars) | 统计图自动生成 |
| `paper_integration/plotly_integration.md` | plotly/plotly.py (~18.2k stars) | 交互式答辩展示 |
| `paper_integration/mermaid_integration.md` | mermaid-js/mermaid (~89k stars) | 流程图/模型框架图 |

### 优化工具集成层（2026-07-30 第三批）

> 从 4 个优化求解开源仓库深度学习后蒸馏的实战参考。

| 文件 | 来源仓库 | 服务于 |
|------|----------|:---:|
| `numerical_computing/ortools_integration.md` | google/or-tools (~13.5k stars) | 组合优化/CP-SAT/路径规划 |
| `numerical_computing/cvxpy_integration.md` | cvxpy/cvxpy (~6.2k stars) | 凸优化/二次规划/DCP自动验证 |
| `numerical_computing/pulp_integration.md` | coin-or/pulp (~2.4k stars) | 线性/整数规划快速建模 |
| `numerical_computing/deap_integration.md` | DEAP/deap (~6.3k stars) | 遗传算法/NSGA-II多目标 |

### 专项能力集成层（2026-07-31 第四批）

> 从 5 个专项开源仓库深度学习后蒸馏的实战参考。

| 文件 | 来源仓库 | 服务于 |
|------|----------|:---:|
| `models/prophet_integration.md` | facebook/prophet (~20.2k stars) | 时序自动预测（趋势+季节分解） |
| `numerical_computing/statsmodels_integration.md` | statsmodels/statsmodels (~11.5k stars) | 统计建模/时序诊断/假设检验 |
| `paper_integration/mayavi_integration.md` | enthought/mayavi (~1.4k stars) | 专业3D科学可视化 |
| `paper_integration/bokeh_integration.md` | bokeh/bokeh (~20.4k stars) | 独立HTML交互式可视化 |
| `numerical_computing/gekko_integration.md` | BYU-PRISM/GEKKO (~702 stars) | 动态优化/微分方程/非线性MPC |

---

## 状态流转（Canonical: S0→S8）

```
S0 INIT → S1 ANALYSIS → S2 MODEL_SELECTION → S3 DATA_PROCESSING
    → S4 SOLVING → S5 VALIDATION → S6 PAPER → S7 REVIEW → S8 DONE
       │            │              │            │           │
       └────────────┴──────────────┴────────────┴── FAILOVER ──┘
                        (异常时自动回退)
```

详见 `agent_system/state_machine.md`

---

## 使用方式（Agent 视角）

```
1. 读取 agent_system/state_machine.md → 确认当前状态
2. S1: 读取 数学建模题型识别.md → 判定题目类型
3. S2: 读取 模型选择决策树.md → 选择模型（含 Failover 备选）
4. S3: 执行 data_processing/ → 清洗数据
5. S4: 读取 模型求解流程.md → 执行 numerical_computing/
6. S5: 读取 模型验证方法.md → 验证结果
7. S6: 执行 paper_integration/ + document_engineering/ → 生成论文
8. S7: 执行 reviewer_agent/ → 审查评分
9. S8: 通过则输出；不通过则回退修改
```

---

## 与入口 Skill 的关系

```
~/.workbuddy/skills/math-modeling-paper/SKILL.md  ← 薄路由入口
        │
        │ 加载场景判断
        ▼
skills/modeling/   ← 本层：全部建模知识
```
