---
name: modeling
description: Automate mathematical-modeling projects from supplied problem data through reproducible computation, figures, validation, and template-bound Word submission. Use for mathematical modeling contests, modeling-paper generation, or audits and repairs of this repository's Forge workflow; do not use for isolated everyday calculations that do not need a modeling deliverable.
---

# Mathematical Modeling Workflow

Treat this skill as an executable workflow, not as a collection of reading
material. Preserve the user's requested scope: an audit is read-only, while a
request to build, repair, run, or finish authorizes the corresponding local
project changes and executions.

## Route the request

1. Identify the target project and its source problem, attachments, draft, and
   required deliverables. Do not invent missing competition rules or data.
2. Production has exactly one entry:
   `core/runtime/workflow_executor.py --config <workflow.json>`. The config must
   use `forge-project-workflow/v2`. Without a valid `--config`, stop; never invoke
   anything under `core/runtime/legacy/`, a fallback DAG, or a default problem.
3. If no manifest exists, inspect the project and create one before execution.
   Declare every source input, stage `requires`, stage `produces`, script, and
   gate. Use `projects/forge_v7_3_d2026/workflow.json` only as a schema example.
4. A production config may ingest source problem files and declared reference
   templates. It must not ingest project-root `data/`, `results/`, figures,
   generated papers, `paper_draft.md`, or any previous `runtime/runs/*` output.
   Source files must live under the project's `task_assets/` or `source_inputs/`;
   templates must live under the project's `templates/` or this skill's declared
   `submission/templates/`. Stage arguments use explicit `--flag value` pairs;
   every path must be rooted in a current-run token and every gate `--run-id`
   must be `${RUN_ID}`.
   Every stage reads `runtime/runs/current_run/inputs` or current-run artifacts
   and writes only current-run artifacts or gates.
5. Stop on a missing input, pre-existing declared output, missing output,
   unavailable dependency, non-zero stage, failed freshness check, or failed
   content gate. A printed `PASSED` is never evidence by itself. Success means
   the v2 executor archived one run whose manifest and every declared stage are
   `PASS`, every output has a SHA-256 record, every required GateResult is
   `PASS`, and `artifacts/published/submission.docx` exists in that same run.

## Submission invariant

Production paper data must follow this chain without bypasses:

`ModelResult -> PaperSpec -> generated Markdown -> template-bound DOCX -> gates -> published DOCX`

Compute scripts may emit raw results but may not author paper facts. PaperSpec
numeric text, rankings, and parameter tables must reference the current run's
`model_result.json`; a human draft is not a production paper source. When Word
output is requested, load the current run's declared reference DOCX in
`submission/compilers/template_docx_compiler.py`. Never start from a blank
`Document()` or silently substitute hard-coded styles.

The final workflow must genuinely run all of:

- `submission/gates/scientific_gate.py` for numerical, ranking, parameter,
  sample-size, significance, metric-range, and leakage consistency;
- `submission/validators/template_compliance_gate.py` for template identity,
  page geometry, styles, header/footer, three-line tables, and authoring-meta
  removal;
- `submission/validators/artifact_integrity_gate.py` for exact figure identity
  plus table, figure, and equation completeness.
- `submission/gates/publish_gate.py`, which must verify all prior gate reports
  and their DOCX hashes before creating the only deliverable copy.

Extension gates for the 2026 CUMCM rules (in force since 2026-09-01; declared
per workflow via `publish_gate --required-gate`, never silently assumed):

- `submission/gates/ai_compliance_gate.py` — the paper must carry an
  "AI工具使用声明" immediately BEFORE the references; when AI was used, the
  supporting materials must contain `AI工具使用详情.pdf` covering tool
  name/version, purpose & stage, prompting process, and human review.
- `submission/compilers/ai_usage_doc.py` — generates the declaration text and
  the detail PDF from a `forge-ai-usage/v1` JSON record.
- `submission/gates/number_freeze_gate.py` — every numeric leaf of
  `model_result.json` must exist in `frozen_numbers.json`; unlogged drift
  blocks the run (re-freezes must be recorded in `freeze_log.jsonl`).
- `submission/gates/human_judgment_gate.py` — `method_selection` and
  `result_acceptance` decisions must be recorded as made by the team
  (`judgment_records.jsonl`), per the rule that 核心建模与分析由参赛队主导.
- `submission/gates/aigc_audit_gate.py` — heuristic AIGC-trace audit of
  `paper.md`; HIGH risk requires rewriting before submission.
- `submission/gates/writing_quality_gate.py` — anti-defensive writing (no
  self-weakening phrases), measurable claims (vague words need numbers),
  causal-claim safety (strong causal language needs verification sections),
  and the four-element abstract contract (problem/method/result/conclusion).
  Tunable via `--tolerance`.
- `submission/gates/review_audit_gate.py` — reviewer-style findings with
  Severity (Critical/Major/Minor) x Priority (P0/P1/P2) triage; every
  paper number must trace to `model_result.json` (unmatched ones become
  [PENDING VERIFICATION]); abstract numbers must reappear in the body;
  references need >= 3 entries and well-formed DOIs. Critical/P0 blocks.
- `submission/compilers/citation_verify.py` — verifies reference DOIs live
  against CrossRef; degrades to format-check when the network is unavailable
  (never silently trusts). Exit 1 when a DOI fails verification.
- `submission/schema/paper_spec.py` — every PaperSpec block carries an
  `info_class` (original/confirmed/inferred/suggestion). Bound numeric facts
  must be original or confirmed; static text claiming original/confirmed
  status must declare a source.
- `knowledge/writing_checklists.md` — section-level writing self-check
  (8 sections + pre-submission checklist) for the paper-writing stage.

`template_compliance_gate.py` accepts `--policy cumcm-2026` (default) to also
enforce the 2026 revision: no TOC field, no identity/school/team-number leak,
and an appendix declaring support materials or no-program statement. Pass
`--policy legacy` to keep the pre-2026 checks only.

Intermediate `artifacts/submission.docx` is not publishable. Never hand it off
as a successful paper; only the current run's `artifacts/published/` copy may be
reported as a production deliverable.

Use an official competition DOCX when supplied. The checked-in
`submission/templates/CUMCM_template.docx` is only a contract-derived bootstrap
reference; disclose that limitation and do not call it an official template.
Read `submission/templates/README.md` when replacing or regenerating it.

For a final DOCX, use the available document workflow to render and inspect all
pages. If a page renderer is unavailable, perform structural audits and clearly
state that visual page QA remains pending.

## Knowledge routing

Load only the references needed by the identified stage. Start with
`canonical_state_machine.md` for lifecycle decisions; use the specialized
directories for problem intelligence, data processing, model selection,
numerical computing, validation, paper integration, and submission only when
that part of the task is active.

For a real contest that spans multiple AI tools/sessions, uses an official
online simulator with limited formal-test attempts, or imposes hard safety
guarantees alongside an efficiency target, load `contest_ops/` (beta,
validated on the 2026 CUMCM Problem B campaign). Its manuals cover the
cross-model handoff package, evidence-boundary fact tables, adversarial
logic-collision review, phase-0 audit before optimization with lower-bound
discipline, online/offline dual-world protocol discipline, and the
reproducible paper-figure pipeline. Read `contest_ops/README.md` first and
route to the numbered manual matching the active situation; its templates
directory provides ready handoff/fact-table/acceptance/self-check/AI-usage
skeletons.

Report the concrete output paths, gate results, and any remaining external
input needed from the user, especially an official template or missing data.
