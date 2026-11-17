# Projects

控制台会扫描本目录下包含 `workflow.json` 的项目：

```text
projects/
└── <project-name>/
    ├── workflow.json
    ├── task_assets/      # 题目/附件（按需）
    └── runtime/          # 运行产物（默认 gitignore）
```

本仓库不附带真实竞赛题目、运行结果或任务数据，避免泄露与仓库膨胀。使用自己的项目时，按 `skills/modeling/` 的 workflow 协议放入配置与输入文件。
