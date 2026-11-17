# 候选稿、人工审核与本地发布

唯一执行入口仍为 `core/runtime/workflow_executor.py --config ...`。成功产出 DOCX 时自动保存 `release/candidates/<sha256>.json`；其中列出运行文件及哈希。这份记录不是批准，也不保存一份新的可编辑论文。原稿变化后须重新生成候选记录、重新审核。旧记录保留，不覆盖。

V9 的发布控制已接入；V8 固定参考工作流仅生成 `UNSUPPORTED_OR_REFERENCE_ONLY` 候选，不能凭演练 PASS 转为真实发布。现有 `artifacts/published` 是旧门禁的内部校验副本。实际本地发布以 `release/current.json` 为准，任何路径名都不代表官方提交。

## 操作流程

1. 用已有 workflow 配置生成当前运行；从返回值取得 `run_dir`。数学、数据或参考清单不支持时先修正输入并重新运行，不修改运行产物绕过 gate。
2. 使用项目已绑定的渲染器导出 `artifacts/submission.pdf`，核对它与 DOCX 一致。当前代码不替用户安装渲染软件，也不自动宣称 Word 已渲染成 PDF。
3. 在项目内建立候选刷新配置，例如 `release_candidate.json`：

```json
{"schema":"forge-release-request/v1","run_dir":"runtime/runs/实际运行ID","action":"candidate"}
```

4. 运行唯一入口取得新的 `candidate_sha256`。把审核记录放到该运行的 `release/reviews/`；以下字段须由真实审核者填写，不可复制测试夹具当证据。
5. 最后用发布配置运行同一入口。默认 `manual`；明确改为 `automatic` 只省去单独的发布按钮确认，仍要求全部人工质量审核、三题验收和规则核对。

```json
{"schema":"forge-release-request/v1","run_dir":"runtime/runs/实际运行ID","action":"publish","candidate_sha256":"候选记录的完整64位哈希","mode":"manual"}
```

成功会生成 `release/versions/<事件ID>/` 中的 DOCX、PDF 与收据，并原子更新 `release/current.json`；失败会记录 `release/events/` 中的阻塞原因，不更新当前发布。

## 必须由人补齐的记录

`human.json`、`rules.json`、`publish.json` 共用：`status: APPROVED`、`reviewer` 非空、`run_id`、`candidate_sha256`、带时区的 `reviewed_at`。这些值只表达提交者的声明；没有认证身份或电子签名。

`human.json` 还需要 `checks` 中以下每项为布尔 true：

- `paper_quality`、`visual_layout`、`table_spec`、`recomputed_results`；
- `ai_declaration`、`ai_details_pdf`、`aigc_heuristic_review`；
- `anonymity`、`supporting_materials`、`pdf_matches_docx`。

`rules.json` 还需 `profile_sha256`（当前 `knowledge/contest_rules/cumcm_2026.json` 的文件哈希）、`seven_days_is_local_policy: true`、`official_sources_checked: true`。快照和审核时间均不得超出本地复核窗口；七天不是官方期限。赛区附加要求仍由人核对。

`pdf_boundaries.json`：`status: APPROVED`、`reviewer`、`pdf_sha256`、`abstract_end: 1`、`body_end`（正文末页的 PDF 物理页号）。电子版从摘要第一页开始，正文紧随摘要，附录在正文之后；只支持这种连续分段。程序计总页数并验证正文 1–30 页。摘要原则上一页在本地按一页保守拦截；章节含义和视觉质量仍需人工确认。不能使用 DOCX 属性页数、文件名或总页数猜测正文范围。

`acceptance.json`：`status: APPROVED`，`cases` 恰好三项；每项必须有不同的 `problem_id`、`run_id`、`status: APPROVED`、`reviewer`、`official_source_url`、`manifest_path`、`provider_audit_path`、`evidence`。`evidence` 是运行内相对路径到 SHA-256 的映射，至少覆盖该项 manifest/provider audit。把验收材料副本存到 `release/reviews/acceptance_cases/`；manifest 必须来自真实模型调用并为 `READY_FOR_REVIEW`，provider audit 必须 `COMPLETED`。URL和人工评价的真实性仍需审核，文件字段不能证明远端模型确实被调用。

`READY_FOR_REVIEW` 有两种语义，验收时必须区分：模型设计阶段完成即返回 `READY_FOR_REVIEW + solver_mapping: PLANNED_NOT_EXECUTED`，只代表"问题理解与模型设计可送审"，不代表任何公式已求解；求解阶段完成才带已执行映射与数值产物。manifest 中 `solver_mapping` 为 `PLANNED_NOT_EXECUTED` 时，验收范围仅覆盖调用与设计，结论不得表述为"已求解/已产出数值"。

三题历史真题验收可以在取得真实题目及调用条件后立即进行，无须等当届发题；当届官方题则必须满足发布时间及来源核验。三题工程资格验收与官方竞赛提交是不同事件。

## 撤回与恢复

```json
{"schema":"forge-release-request/v1","run_dir":"runtime/runs/实际运行ID","action":"revoke","reason":"填写实际撤回原因"}
```

撤回仅把本地当前发布标记为 `REVOKED`，保留全部历史文件和上一收据；不撤销已上传的官方提交。恢复旧稿应重新提交该稿的候选发布请求并重走证据核验，不直接把旧指针恢复为有效。

## 安全边界

SHA-256 防止未同步更新的旧文件混入，不抵御拥有整个工作区写权限的人重写全部证据；审核 JSON 不具备身份认证。AIGC gate 是文风启发式，PASS 不证明作者身份或声明合规。控制器使用排他文件锁；崩溃遗留锁保守阻塞，确认无运行者后再人工处理。它不是官方上传器、操作系统访问控制或通用论文完整性证明。
