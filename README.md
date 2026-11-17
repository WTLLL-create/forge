# Forge — 数学建模论文工作流与质量审校平台

Forge 把数学建模从题目理解、建模求解、论文集成到质量门禁与审校，组织成一条可追踪的流水线。仓库包含两个部分：

- `skills/modeling/`：规则驱动的工作流引擎、工具层、论文集成、审校 Agent 与测试。
- `projects/forge_console_2026/`：FastAPI + 原生 JavaScript 的 Web 控制台，用于启动运行、查看阶段/门禁/产物与审校结果。

> 本仓库是脱敏后的展示版本：不包含真实 API Key、运行日志、竞赛原始题目、生成结果或本机绝对路径。

## 目录

```text
forge/
├── skills/modeling/                 # 多阶段建模/论文引擎
├── projects/forge_console_2026/     # Web 控制台
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
- **规则驱动 Planner**：当前版本由规则规划器调度带 Schema 校验的工具；模型 Planner 是后续扩展点。

更完整的引擎说明见 `skills/modeling/README.md`，控制台说明见 `projects/forge_console_2026/README.md`。
