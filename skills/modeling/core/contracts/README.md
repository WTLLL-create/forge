# Core Contract Layer v1

> v6.0 接口标准化层。定义了模块间传递的结构化数据格式。
> 原则: 每个 Schema 只包含下游模块 **必须消费** 的字段，不追求完整性。

## Schema 清单

| Schema | 生产者 | 消费者 | 状态 |
|--------|--------|--------|:---:|
| `problem_state.schema.json` | L1 Problem Intelligence | L2 Strategy Planner | v1 |
| `decision_contract.schema.json` | L3 Expert Decision | L4 Models/Data/Compute | v1 |
| `model_result.schema.json` | L4 Execution | L5 Evidence Layer | v1 |
| `paper_section.schema.json` | L6 Paper Reasoning | L8 Generation | v1 |
| `failure_record.schema.json` | L7 Evaluation | L3/L4 (下次运行) | v1 |

## 使用方式

每个模块的输出 **必须** 包含对应 Schema 的 JSON 序列化版本，放在输出的 `contract` 字段中。下游模块 **优先读取 contract**，仅在 contract 缺失时回退到阅读 Markdown。

## 设计原则

1. **先路由，后完善**: 每个 Schema 的第一优先级是回答"下游该走哪个分支"
2. **可选字段标记**: 非关键信息标 `required: false`，避免阻塞链路
3. **向后兼容**: 新增字段不破坏旧模块
