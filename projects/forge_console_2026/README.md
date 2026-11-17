# Forge Console

Forge 工作流的 Web 控制台：把 `skills/modeling` 里的多阶段引擎暴露成 HTTP API，并提供一页式运行视图。

控制台不实现引擎。它只做两件事：

1. 调 `ProductionWorkflow` 启动一次真实运行；
2. 读运行落盘的契约（`manifest.json` + `gates/*.json` + `artifacts/`），把阶段、门禁、产物渲染出来。

## 目录结构

```
forge_console_2026/
├── backend/
│   ├── main.py            # FastAPI 路由与静态挂载
│   ├── forge_service.py   # 项目/运行发现、契约读取、路径安全检查
│   └── jobs.py            # 单 worker 串行任务队列
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/
│   └── test_api.py        # API 契约测试（含路径逃逸用例）
├── requirements.txt
└── run.ps1
```

## 启动

```powershell
cd projects/forge_console_2026
python -m pip install -r requirements.txt
.\run.ps1
```

默认监听 `http://127.0.0.1:8765`，打开就是控制台。API 文档在 `/api/docs`。

`run.ps1` 优先使用 `FORGE_PYTHON`，否则使用当前 PATH 中的 `python`。

## 界面

左侧是运行记录；右侧是选中的一次运行：阶段时间线、9 道门禁、产物下载。点击阶段看日志，点击门禁卡片看逐项 `checks`。截图请运行后自行生成。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/api/projects` | 扫描 `projects/*/workflow.json` |
| GET | `/api/runs?project=` | 运行列表（读 manifest 摘要） |
| GET | `/api/runs/{run_id}` | 阶段、门禁、产物树 |
| GET | `/api/runs/{run_id}/download?path=` | 下载产物（路径必须落在 run 目录内） |
| GET | `/api/runs/{run_id}/logs/{stage}/{stream}` | stdout / stderr |
| POST | `/api/jobs?project=` | 提交一次运行，返回 job_id |
| GET | `/api/jobs/{job_id}` | 轮询任务状态 |

## 设计约束

- **串行执行**：`ProductionWorkflow` 对每个 runtime root 持文件锁，任务队列只有一个 worker，避免并发冲突。
- **只读契约**：门禁状态不重新计算，直接读 `gates/*.json` 的 `checks`，保证界面与引擎同源。
- **路径安全**：产物路径 `resolve()` 后必须位于 run 目录内，`../../` 之类直接 404。
- **不伪造成功**：界面显示的 PASS 来自落盘报告，不是前端推断。

## 测试

```powershell
cd projects/forge_console_2026
python -m unittest discover -s tests -v
```

覆盖健康检查、项目发现、运行详情、产物下载、日志读取、路径逃逸、未知 run/project。
