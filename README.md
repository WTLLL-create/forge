# Forge — 数学建模论文工作流与质量审校平台

Forge 把数学建模从题目理解、建模求解、论文集成到质量门禁与审校，组织成一条可追踪的流水线。仓库包含两个部分：

- `skills/modeling/`：规则驱动的工作流引擎、工具层、论文集成、审校 Agent 与测试。
- `projects/forge_console_2026/`：FastAPI + 原生 JavaScript 的 Web 控制台，用于启动运行、查看阶段/门禁/产物与审校结果。

> 本仓库是脱敏后的展示版本：不包含真实 API Key、运行日志、竞赛原始题目、生成结果或本机绝对路径。

## 目录

```text
forge/
├── skills/modeling/
│   ├── core/runtime/              # 模型 Provider 适配器、工作流运行时
│   ├── agent_layer/               # 工具调用审稿 Agent（RulePlanner）
│   └── submission/                # 论文契约、渲染与质量门禁
├── projects/forge_console_2026/   # Web 控制台
├── knowledge/contest_rules/       # 带日期的竞赛规则快照
└── README.md
```

## 快速启动控制台

要求：Python 3.11+、PowerShell 7。

```powershell
cd projects/forge_console_2026
python -m pip install -r requirements.txt
$env:FORGE_PYTHON = (Get-Command python).Source
.\run.ps1
```

打开 `http://127.0.0.1:8765`，API 文档在 `http://127.0.0.1:8765/api/docs`。

控制台扫描 `projects/*/workflow.json`。运行自己的项目时，在 `projects/` 下放入项目目录与 `workflow.json`；本仓库为减小体积和避免泄露，不附带竞赛原始数据。`projects/forge_v7_3_d2026/runtime/runs/demo-run/` 只是控制台 API 测试用的最小 fixture，不是真实运行结果。

## 测试

```powershell
# 控制台 API 契约测试
cd projects/forge_console_2026
python -m unittest discover -s tests -v

# 引擎测试（可选，按需安装 skills/modeling/requirements.txt）
cd ../../skills/modeling
python -m pytest tests -q
```

## 设计要点

- **串行执行**：引擎对每个 runtime root 持文件锁，控制台任务队列单 worker，避免并发写同一运行目录。
- **契约只读**：门禁状态来自落盘的 `gates/*.json`，控制台不重新计算，避免 UI 与引擎口径不一致。
- **路径安全**：产物下载路径 `resolve()` 后必须位于 run 目录内，拒绝 `../` 逃逸。
- **证据链**：manifest、阶段日志、门禁 checks、产物树均落盘，便于复盘与审校。
- **模型接入（显式选择，不自动回退）**：`core/runtime/llm_provider.py` 提供 OpenAI Responses 适配器，强制 JSON Schema 输出、输入/输出预算与超时，并在缺少凭据时失败关闭；`core/runtime/codex_provider.py` 通过已登录的 Codex CLI 调用，子进程只继承白名单环境变量，不处理 API Key，带输出上限和进程树清理；`core/runtime/agent_provider.py` 用文件桥接外部 Agent 的结构化回答。三者由 `create_provider` 按配置显式选择，未知 provider 不会回退到 API。
- **规则 Planner**：`agent_layer` 默认使用离线 `RulePlanner`，模型 Planner 是可替换接口；当前审稿 Agent 的确定性工具链不依赖模型调用。

更完整的引擎说明见 `skills/modeling/README.md`，控制台说明见 `projects/forge_console_2026/README.md`。
