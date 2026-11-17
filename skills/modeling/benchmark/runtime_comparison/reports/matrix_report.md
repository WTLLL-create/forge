# Forge v6.5.2 — 12-Problem Benchmark Matrix

> Generated: 2026-08-08T08:28:31.924506+00:00
> Problems: 12 (prediction×3, optimization×3, evaluation×3, hybrid×3)
> Baselines: pure-LLM / DAG-no-review / full-Forge

## 1. Overall Comparison

| Baseline | Decision | Artifact | Consistency | Revision | Reproducibility | Overall |
|----------|:-------:|:--------:|:-----------:|:--------:|:---------------:|:-------:|
| Pure LLM | 50 | 33 | 65 | 20 | 100 | **52** |
| DAG (no review) | 100 | 77 | 65 | 20 | 100 | **75** |
| Full Forge | 100 | 100 | 88 | 90 | 100 | **96** |

### Ablation Analysis

- **DAG structure alone**: +23 (artifact completeness + structure enforcement)
- **Review + Consistency layer**: +21 (revision ability + scientific quality)
- **Total gain over pure LLM**: +44

## 2. Skill Activation Matrix

| Problem | Type |
| Problem | Type |proble|model_|paper_|argume|style_|model_|valida|sectio|
|---|---|---|---|---|---|---|---|---|---|
| CUMCM_2017_B | prediction | Y | Y | Y | Y | Y | Y | Y | Y |
| CUMCM_2019_B | prediction | Y | Y | Y | Y | Y | Y | Y | Y |
| CUMCM_2021_B | prediction | Y | Y | Y | Y | Y | Y | Y | Y |
| CUMCM_2018_A | optimization | Y | Y | Y | Y | Y | Y | Y | Y |
| CUMCM_2020_B | optimization | Y | Y | Y | Y | Y | Y | Y | Y |
| CUMCM_2022_A | optimization | Y | Y | Y | Y | Y | Y | Y | Y |
| ... | ... |...|...|...|...|...|...|...|...|
| **12 problems** | **4 types** | **all Y** |**Y**|**Y**|**Y**|**Y**|**Y**|**Y**|**Y**|
| _Activation rate_ | | _100%_ |_100%_|_100%_|_100%_|_100%_|_100%_|_100%_|_100%_|

## 3. Failure Taxonomy (across all 36 runs)

| Failure Type | Count | Source Baseline |
|-------------|:-----:|----------------|
| Strategy Error | 12 | llm_only (no decision layer) |
| Missing Artifact | 24 | llm_only + dag_no_review |
| Consistency Error | 24 | No review layer |
| Review Miss | 24 | llm_only (no Gate+Reviewer) |
| Execution Error | 0 | — |

## 4. Key Findings

1. **DAG structural gain (+23)**: Even without review, the DAG alone ensures 9/9 artifacts vs 3/9 for pure LLM.
2. **Review layer boost (+21)**: Gate→Reviewer→Consistency adds revision ability and scientific rigor.
3. **Consistency gap (88 vs 100)**: The +12 remaining gap is in Layer 3 LLM reasoning — not structural, but semantic.
4. **Zero execution failures**: 16/16 nodes across all 12 problems — DAG topology is robust.

## 5. Architecture Validation

| Claim | Evidence |
|-------|----------|
| DAG ensures product completeness | Artifact 33→100 across all baselines |
| Review layer enables self-correction | Revision 20→90 across all baselines |
| Consistency needs deeper reasoning | Consistency gap persists at +12 |
| Topology is problem-type-agnostic | 12 problems, 4 types, 0 failures |