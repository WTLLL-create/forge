# Reviewer Agent — GitHub 参考源

> 阶段 16 — 评测框架调研

---

## 一、openai/evals

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/openai/evals |
| **Stars** | ~20,000 |
| **定位** | AI 模型评测框架 |
| **核心** | Evaluation Dataset + Scoring Rule + 自动化测试 |
| **借鉴** | 评分体系的自动化验证 — 给定标准答案，自动计算模型得分 |

---

## 二、promptfoo/promptfoo

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/promptfoo/promptfoo |
| **Stars** | ~8,000 |
| **定位** | LLM 输出质量测试 |
| **核心** | 多版本 Prompt 对比 + 自动评分 + 回归测试 |
| **借鉴** | 论文多轮修改后的版本对比（修改前 vs 修改后的评分提升） |

---

## 三、Arize-ai/phoenix

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/Arize-ai/phoenix |
| **Stars** | ~8,000 |
| **定位** | AI 系统可观测性平台 |
| **核心** | Trace 追踪 + 过程分析 + 错误定位 |
| **借鉴** | Agent 推理过程的可追溯记录（每步决策都有 Audit Trail） |

---

## 四、explodinggradients/ragas

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/explodinggradients/ragas |
| **Stars** | ~10,000 |
| **定位** | RAG 质量评价 |
| **核心** | Faithfulness(忠实度) + Answer Relevance + Context Relevance |
| **借鉴** | 知识调用正确性评价 — Agent 是否真的调用了正确的 models/ 文档？ |

---

## 五、confident-ai/deepeval

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/confident-ai/deepeval |
| **Stars** | ~10,000 |
| **定位** | LLM 应用评测框架 |
| **核心** | 多维评分 + 自动评估 + 批量测试 |
| **借鉴** | 多维评分体系设计和批量论文评估 |

---

## 六、truera/trulens

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/truera/trulens |
| **Stars** | ~4,000 |
| **定位** | LLM 应用质量评估 |
| **核心** | Groundedness(有据性) + Completeness(完整性) + Correctness(正确性) |
| **借鉴** | 论文结论的三个质量维度：有据/完整/正确 |

---

## 七、SWE-agent/SWE-agent

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/SWE-agent/SWE-agent |
| **Stars** | ~15,000 |
| **定位** | 自动代码修复 Agent |
| **核心** | 发现问题 → 定位根因 → 修改 → 重新验证的闭环 |
| **借鉴** | `improvement_strategy.md` — 论文问题的自动修复循环 |

---

## 汇总

| 框架 | Stars | 核心借鉴 |
|------|-------|----------|
| openai/evals | 20k | 自动化评分验证 |
| promptfoo | 8k | 多版本对比评分 |
| Arize Phoenix | 8k | 推理过程追踪 |
| ragas | 10k | 知识调用正确性评价 |
| DeepEval | 10k | 多维评分体系 |
| TruLens | 4k | 有据性/完整性/正确性 |
| SWE-agent | 15k | 发现问题→修改→重验闭环 |
