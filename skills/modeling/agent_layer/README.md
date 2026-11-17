# Agent Layer —— 论文审稿 Agent

在 Forge 运行产物之上加的一层 Agent：用工具调用做证据核对，输出结构化审稿报告。

它不改动 19 阶段流水线，读取的是每次运行落盘的契约：`manifest.json`、`paper_spec.json`、`frozen_numbers.json`、`gates/*.json`。

## 为什么单独一层

| 层 | 职责 | 特点 |
|---|---|---|
| 执行层（19 阶段） | 算数据、生成图表、渲染论文、跑门禁 | 确定性脚本，可复现 |
| 知识层（15 模块） | 论文模式、审稿规则、模型策略、图表规范 | 离线 Markdown 规则库 |
| **Agent 层（本模块）** | 调工具核对证据、检索规则、输出问题清单 | 工具调用循环，可插拔 Planner |

原来的知识层没有被运行链调用。Agent 层是把"规则库"变成"可执行判断"的桥梁。

## 目录

```
agent_layer/
├── tools.py            # 7 个工具 + JSON Schema 校验 + 统一返回信封
├── retrieval.py        # BM25 检索（中文 bigram，无外部依赖）
├── reviewer.py         # Agent 循环 + RulePlanner + 报告契约
├── pipeline.py         # Reviewer -> Writer -> Verifier 闭环，只出修订计划
├── stage.py            # 工作流第 20 阶段入口（advisory，不阻断发布）
├── fault_injector.py   # 三类缺陷注入 + 召回率/误报评测
├── prompts.py          # Reviewer / Writer / Verifier 角色卡
├── cli.py              # 命令行入口
└── tests/              # 36 个用例
```

## 七个工具

| 工具 | 作用 |
|---|---|
`get_run_manifest` | 运行状态、阶段、门禁摘要
`list_sections` | 列出论文章节与块数
`get_section` | 读某章节的断言、块类型、是否有数据绑定
`get_frozen_numbers` | 读冻结数字表（可按前缀过滤）
`verify_numbers` | 从文本抽数字，逐个核对冻结表
`list_gate_checks` | 读门禁逐项检查结果
`search_knowledge` | BM25 检索论文模式与审稿规则

每个工具都有 JSON Schema，执行前校验参数；未知工具、缺参、多参一律拒绝。

## 循环

```
planner.next() -> 选工具
executor.call() -> 校验 + 执行 + 计时 + 参数哈希
result -> 回填证据，决定下一个工具
planner 返回 None 或步数到 60 -> 结束
```

`RulePlanner` 的固定路线：清单 → 章节列表 → 逐章节（读正文 → 核数字 → 检索规则）→ 关键门禁。

任意 `Planner` 实现都可以替换它（模型 Planner 只需返回同样的 `{"tool", "args"}`）。

## 运行

```powershell
cd <repo-root>\skills\modeling

# 审稿
python -m agent_layer.cli --run "projects/<your-project>\runtime\runs\<run_id>"

# 不建检索索引（更快）
python -m agent_layer.cli --run "<run_id>" --no-index
```

默认输出到 `projects/forge_v7_3_d2026/agent_reports/<run_id>/`：

- `review_report.json`：问题清单 + 证据 + 工具调用轨迹 + 轨迹哈希
- `agent_trace.jsonl`：逐步调用记录

## 多 Agent 闭环

Review 之后不直接结束，而是交给 Writer 和 Verifier：

```
ReviewAgent  -> issues（带 section / block_id / evidence）
WriterAgent  -> patches（replace_number 或 mark_unsupported，逐条可定位）
VerifierAgent-> 每个 patch 三项检查：命中已报 issue、确实改动、新文本无未冻结数字
             -> verdict PASS / FAIL / EMPTY
```

产物 `revision_plan.json`（schema `forge-revision-plan/v1`，`applied: false`）：只给修订建议，**不写回论文**。Verifier 的“越界补丁”检查用来防止 Writer 改到未被报告的段落。

### 回退环

Verifier 判 FAIL 时，把失败的 patch 退回 Writer 重写，最多 `max_rounds` 轮（默认 2，硬上限避免死循环）：

- 重写只做确定性修复：新文本里未登记的数字换成 `（数值待核实）`
- 修不动的 patch 直接丢弃，不编造数据填坑
- `attempts` 逐轮记录 verdict、patch 数、失败 patch id；`rounds` 是实际执行轮数
- 仍然不改动论文，最终产物依旧只是 `applied: false` 的计划

## 接入流水线

`stage.py` 是 `workflow.json` 的第 20 阶段 `agent_review`，排在 `publish_gate` 之后：

- 输入：`${RUN_ARTIFACTS}/paper_spec.json`
- 输出：`gates/agent_review.json`（PASS / REVIEW_NEEDED）+ `artifacts/support/revision_plan.json`
- `ADVISORY = True`：脚本始终 `exit 0`，报告写 `advisory: true`，不阻断发布
- 想改成阻断式，把 `ADVISORY` 置 False 并在 `publish_gate` 的 `--required-gate` 里加 `agent_review`

阶段运行时不依赖最终 `manifest.json`（它在全部阶段结束后才写），`RunTools` 会用 `FORGE_RUN_ID` 构造一个 RUNNING 视图。

## 实测

| 场景 | 结果 |
|---|---|
| 真实运行（2026 D 核桃油） | 22 步、6 章节、0 issue、plan verdict EMPTY |
| 注入缺陷（未登记数字 + 无源断言） | 同时报出 `unmatched_number` 与 `unsupported_claim`；Writer 生成 2 个 patch；Verifier PASS |
| 缺陷矩阵（三类 + 干净运行） | 3/3 检出（recall 1.0）；纯数字注入只报 `unmatched_number`，不误报无源断言；干净运行 0 issue |
| 回退环（伪造成含未登记数字的 patch） | 第一轮 FAIL，第二轮把数字替换为占位符后 PASS；无法修复的 patch 被丢弃 |
| 干净运行 + 越界补丁 | Verifier 判 FAIL（“patch targets an reported issue”不通过） |
| 20 阶段端到端 | PASS，`agent_review` 阶段 22 步、0 issue |

## 测试

```powershell
cd <repo-root>\skills\modeling
python -m unittest agent_layer.tests.test_agent_layer agent_layer.tests.test_fault_detection agent_layer.tests.test_pipeline agent_layer.tests.test_fault_eval -v
```

36 个用例：工具 10、检索 4、循环 9、缺陷检测 4、闭环 9（含回退环 3）、缺陷矩阵 4。

## 与面试知识点的对应

| 知识点 | 落点 |
|---|---|
| Function Calling / Tool Use | `tools.py` 的 JSON Schema 定义、参数校验、统一信封 |
| Agent 循环与终止条件 | `reviewer.py` 的 planner/executor 循环、步数预算 |
| 结构化输出 | `forge-agent-review/v1` 报告契约 |
| RAG / 检索 | `retrieval.py` BM25 + `search_knowledge` |
| System Prompt / 角色 | `prompts.py` 三角色卡 |
| 上下文管理 | 工具按需取片段，不塞全文；章节逐个处理 |
| 可观测性 | `agent_trace.jsonl` + `trace_sha256` |
| 评估与阳性对照 | `fault_injector.py` + 缺陷检测测试 |
| 多 Agent 协作 | `pipeline.py` 三角色闭环 + patch 级复核 |

## 边界

- 只读运行产物，不写回 `paper_spec.json` / `artifact`。
- 不修改门禁报告，不伪造 PASS。
- 数字核对是规则匹配，不是语义理解；未匹配项交给人判断。
- 离线 `RulePlanner` 不等于自主 Agent，报告里 `planner` 字段如实标注。
- 阶段当前是 advisory，不阻断发布；阻断是后续可选项。
