# Canonical State Machine — 唯一权威状态机

> **定位**：本文件是整个数学建模系统的唯一状态机定义源。
> 所有模块必须引用本文件的 S0-S8 状态编号和转移规则。
>
> **废弃文件**：`建模任务状态管理.md`（S0-S7 旧编号）已废弃，以本文件为准。
>
> 版本：v3.0 | 最后更新：2026-07-31

---

## 一、状态流转总图

```
INIT (S0)
  │  输入赛题文件
  ▼
ANALYSIS (S1)
  │  题型识别 + 问题分析
  ▼
MODEL_SELECTION (S2) ⚑ ← 人工 Checkpoint
  │  沿决策树选模型
  ▼
DATA_PROCESSING (S3) ← 可跳过（纯优化无外部数据时）
  │  6 步数据管道
  ▼
SOLVING (S4)
  │  数值求解
  ▼
VALIDATION (S5) ⚑ ← 人工 Checkpoint
  │  验证指标是否达标
  ├── pass → PAPER (S6)
  │           论文生成
  │             ▼
  │          REVIEW (S7)
  │           评分审查
  │             ├── ≥85 → DONE (S8)      直接通过
  │             ├── 70-84 → PAPER (S6)   修改论文（最多3轮）
  │             └── <70:
  │                  ├── 65-69 → PAPER (S6)  表达层问题
  │                  └── <65 → MODEL_SELECTION (S2)  模型层问题
  │
  └── fail → MODEL_SELECTION (S2)  重选模型
       SOLVING fail → 尝试备选方法 → 仍失败 → MODEL_SELECTION (S2)
       DATA 严重不足 → ANALYSIS (S1) 重新评估
```

---

## 二、状态定义

### S0: INIT — 初始化

| 维度 | 内容 |
|------|------|
| **任务** | 接收赛题文件，提取基本信息 |
| **输入** | 赛题文件(.docx/.pdf) + 附件(.xlsx/.csv) |
| **输出** | `{task_id, problem_file, attachment_files}` |
| **下一状态** | S1 ANALYSIS |

### S1: ANALYSIS — 题目分析

| 维度 | 内容 |
|------|------|
| **任务** | Problem Intelligence 三层分析 + 题型识别 |
| **输入** | S0 输出 |
| **输出** | `{problem_type, sub_type, math_essence, data_characteristics, candidate_model_space}` |
| **调用** | `数学建模题型识别.md` `problem_intelligence/problem_analysis_protocol.md` |
| **失败** | 题型不确定 → 请求人工澄清 |
| **下一状态** | S2 MODEL_SELECTION |

### S2: MODEL_SELECTION — 模型选择 ⚑

| 维度 | 内容 |
|------|------|
| **任务** | 沿决策树确定模型 + 记录选择理由 + 确定备选方案 |
| **输入** | S1 输出 |
| **输出** | `{model_name, selection_reasons, rejected_models, failover_model}` |
| **调用** | `模型选择决策树.md` `models/` |
| **Checkpoint** | **⚑ 人工确��点** — 确认/修改/退回 S1 |
| **下一状态** | S3 DATA_PROCESSING（需要数据）或 S4 SOLVING（纯优化） |

### S3: DATA_PROCESSING — 数据处理

| 维度 | 内容 |
|------|------|
| **任务** | 6 步数据管道：读取→检查→清洗→探索→特征→输出 |
| **输入** | S0 原始数据 + S2 特征需求 |
| **输出** | `{X(numpy), y(numpy), feature_names, data_quality_report}` |
| **调用** | `data_processing/workflow.md` |
| **可跳过** | 纯优化问题（无外部数据时直接进入 S4） |
| **失败** | 数据严重不足 → 退回 S1 重新评估 |
| **下一状态** | S4 SOLVING |

### S4: SOLVING — 模型求解

| 维度 | 内容 |
|------|------|
| **任务** | 运行求解器，获取数值结果 |
| **输入** | S2 模型选择 + S3 清洁数据 |
| **输出** | `{solution_values, solver_status, experiment_log}` |
| **调用** | `模型求解流程.md` `numerical_computing/` |
| **失败** | 求解不收敛 → 尝试备选方法 → 所有方法失败 → 退回 S2 |
| **下一状态** | S5 VALIDATION |

### S5: VALIDATION — 结果验证 ⚑

| 维度 | 内容 |
|------|------|
| **任务** | 准确性验证 + 对比实验 + 敏感性分析 |
| **输入** | S4 求解结果 + S3 原始数据 |
| **输出** | `{validation_metrics, pass/fail, sensitivity_results}` |
| **调用** | `模型验证方法.md` |
| **Checkpoint** | **⚑ 人工确认点** — 确认/退回 S2/接受但有保留 |
| **下一状态** | 通过 → S6 PAPER；不通过 → S2 MODEL_SELECTION |

### S6: PAPER — 论文生成

| 维度 | 内容 |
|------|------|
| **任务** | 将前序所有输出转为论文 |
| **输入** | S1-S5 全部输出 |
| **输出** | `论文.docx` 或 `论文.tex` |
| **调用** | `论文生成流程.md` `paper_integration/` |
| **下一状态** | S7 REVIEW |

### S7: REVIEW — 模拟评委审查

| 维度 | 内容 |
|------|------|
| **任务** | 6 维 100 分评分 + 生成修改建议 |
| **输入** | S6 论文 |
| **输出** | `{score, suggestions, pass/fail}` |
| **调用** | `reviewer_agent/scoring_rules.md` `evaluation_protocol.md` |
| **下一状态** | 见下方「三档审查策略」 |

### S8: DONE — 完成

论文通过审查，输出最终版本，进入项目收尾流程（`standards/project_closure.md`）。

---

## 三、审查策略（三档统一标准）

### 评分源

`evaluation_protocol.md` — 6 维 100 分制，全系统唯一权威评分标准。

### 三档处理

| 得分 | 等级 | 处理 | 最多轮次 |
|------|------|------|:---:|
| **≥ 85** | 国二及以上 | **直接通过 → S8 DONE** | 1 |
| **70-84** | 省一~国二 | **修改论文 → 退回 S6 PAPER** | 3 轮 |
| **< 70** | 省二及以下 | **分情况处理** | — |
| ├─ 65-69 | 表达层问题 | 退回 S6 PAPER 重写/优化 | 2 轮 |
| └─ < 65 | 模型层问题 | 退回 S2 MODEL_SELECTION 重新建模 | 不限 |

### 3 轮重审后仍 < 85 的处理

- 仍在 70-84 → 标注「已达省一水平，建议人工润色后提交」
- 降至 < 65 → 退回 S2 MODEL_SELECTION

---

## 四、完整状态转移表

| 当前 | 条件 | 下一状态 | 动作 |
|------|------|:---:|------|
| S0 | 赛题加载成功 | S1 | 提取问题文本 |
| S1 | 题型明确 | S2 | 输出分析结果 |
| S1 | 题型不明确 | S1 | 请求人工澄清 |
| S2 | 模型确定 | S3 | 需要数据 → 加载数据管道 |
| S2 | 模型确定，无数据需求 | S4 | 跳过 S3 |
| S3 | 数据清洗完成 | S4 | 输出 numpy 数组 |
| S3 | 数据严重不足 | S1 | 重新评估题型和数据需求 |
| S4 | 求解成功 | S5 | 记录实验日志 |
| S4 | 求解失败（首次） | S4 | 换备选方法/参数 |
| S4 | 所有方法失败 | S2 | 降级模型 |
| S5 | 验证通过 | S6 | 标记通过 |
| S5 | 验证不通过 | S2 | 重选模型 |
| S6 | 论文生成完成 | S7 | — |
| S7 | 评分 ≥ 85 | S8 | 输出最终论文 |
| S7 | 评分 70-84 | S6 | 修改论文（≤3轮） |
| S7 | 评分 65-69 | S6 | 表达层修改（≤2轮） |
| S7 | 评分 < 65 | S2 | 模型层重建 |
| S7 | 3 轮重审后 70-84 | S8 | 标注「建议人工润色」通过 |

---

## 五、Checkpoint 数据格式

每个状态结束时写入：

```json
{
  "state": "MODEL_SELECTION",
  "timestamp": "2026-07-31T14:00:00",
  "agent": "Model Selector",
  "input": {"problem_type": "optimization", "sub_type": "资源分配"},
  "output": {"model_name": "LinearProgramming", "failover_model": "MILP"},
  "decision": "选择线性规划因为目标函数和约束均为线性",
  "rejected": [
    {"model": "NLP", "reason": "问题本身是线性的"},
    {"model": "GA", "reason": "精确方法可解，不需要启发式"}
  ],
  "next": "DATA_PROCESSING (跳过，无外部数据) → SOLVING",
  "human_checkpoint": true
}
```

---

## 六、旧文件废弃声明

以下文件的状态机定义已被本文件取代，其中内容仅供历史参考：

| 文件 | 旧编号 | 处理 |
|------|:---:|------|
| `建模任务状态管理.md` | S0-S7（REVIEW 状态缺失） | 标记废弃，添加指向本文件的链接 |
| `agent_system/state_machine.md` | S0-S8（70 分旧阈值） | 降级为「设计参考」，添加「以 canonical 为准」声明 |
| `agent_system/evaluation_rules.md` | 6 维旧权重 | 删除评分标准，添加指向 `evaluation_protocol.md` 的引用 |
| `agent_system/error_handling.md` | <70 统一退回 S6 | 更新为分情况退回 S2/S6 |

---

## 七、使用方式

所有 Agent 在执行时，必须：

1. 以本文件的状态定义为唯一调度依据
2. 在每个状态转换前检查条件是否满足
3. 在每个状态结束时写入 Checkpoint 数据
4. 在 ⚑ 标记处暂停等待人工确认
5. 在 S7 使用 `evaluation_protocol.md` 的评分标准
