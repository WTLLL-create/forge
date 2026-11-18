"""Adapt the existing walnut-oil computation outputs to Forge v8 ModelResult."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.model_result import sha256_file, write_model_result


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def build_model_result(
    *,
    run_id: str,
    problem_id: str,
    model_version: str,
    problem_source_path: Path,
    summary_path: Path,
    rankings_path: Path,
    kinetics_path: Path,
    figures_dir: Path,
) -> dict:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    significance = summary["significance"]
    significance_pass = (
        significance.get("method") == "Kruskal-Wallis"
        and isinstance(significance.get("tests_executed"), int)
        and significance["tests_executed"] > 0
        and significance.get("test_failures") == 0
        and isinstance(significance.get("min_p_value"), (int, float))
        and isinstance(significance.get("max_p_value"), (int, float))
        and 0 <= significance["min_p_value"] <= significance["max_p_value"] <= 1
    )
    ranking_rows = read_csv(rankings_path)
    rankings = sorted(
        [
            {
                "sample": row["sample"],
                "score": round(float(row["TOPSIS_score"]), 4),
                "rank": int(round(float(row["rank"]))),
                "grade": row["grade"],
            }
            for row in ranking_rows
        ],
        key=lambda item: item["rank"],
    )
    kinetics_rows = read_csv(kinetics_path)
    model_counts: dict[str, int] = {}
    for row in kinetics_rows:
        model_counts[row["best_model"]] = model_counts.get(row["best_model"], 0) + 1
    figure_specs = [
        ("2-1", "技术路线"),
        ("2-2", "模型求解流程"),
        ("4-1", "六类VOCs动态变化"),
        ("6-1", "PCA氧化轨迹"),
        ("7-2", "不同样品综合品质排序"),
    ]
    figures = []
    for figure_id, caption in figure_specs:
        path = figures_dir / f"fig{figure_id}.png"
        if not path.is_file():
            raise FileNotFoundError(f"ModelResult figure missing: {path}")
        figures.append({"id": figure_id, "caption": caption, "path": f"figures/{path.name}"})
    result = {
        "schema": "forge-model-result/v1",
        "run_id": run_id,
        "problem_id": problem_id,
        "model_version": model_version,
        "parameters": {
            "entropy_weights": summary["entropy_weights"],
        },
        "metrics": summary,
        "diagnostics": {
            "source_problem": {
                "path": "inputs/task_data/problem.docx",
                "sha256": sha256_file(problem_source_path),
            },
            "sample_size": int(summary["pca"]["n_samples"]),
            "ranking_count": len(rankings),
            "score_range": [
                min(item["score"] for item in rankings),
                max(item["score"] for item in rankings),
            ],
            "data_leakage": {
                "status": "NOT_APPLICABLE",
                "reason": "Unsupervised PCA and multi-criteria ranking; no supervised target split is used.",
            },
            "significance": {
                "status": "PASS" if significance_pass else "FAIL",
                **significance,
            },
            "kinetics_model_counts": model_counts,
        },
        "tables": [
            {"id": "ranking", "source_path": "$.rankings", "rows": rankings},
            {"id": "entropy_weights", "source_path": "$.parameters.entropy_weights", "rows": summary["entropy_weights"]},
        ],
        "figures": figures,
        "rankings": rankings,
        "claims": [
            {"id": "sample_size", "source_path": "$.metrics.pca.n_samples"},
            {"id": "core_biomarkers", "source_path": "$.metrics.biomarkers.n_core"},
            {"id": "aldehyde_pct", "source_path": "$.metrics.biomarkers.aldehyde_pct"},
            {"id": "best_sample", "source_path": "$.metrics.evaluation.best_sample"},
            {"id": "best_score", "source_path": "$.metrics.evaluation.best_score"},
            {"id": "worst_sample", "source_path": "$.metrics.evaluation.worst_sample"},
            {"id": "worst_score", "source_path": "$.metrics.evaluation.worst_score"},
            {"id": "rank_stability", "source_path": "$.metrics.sensitivity.rank_stability_pct"},
        ],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--problem-id", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--problem-source", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--rankings", required=True)
    parser.add_argument("--kinetics", required=True)
    parser.add_argument("--figures-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build_model_result(
        run_id=args.run_id,
        problem_id=args.problem_id,
        model_version=args.model_version,
        problem_source_path=Path(args.problem_source),
        summary_path=Path(args.summary),
        rankings_path=Path(args.rankings),
        kinetics_path=Path(args.kinetics),
        figures_dir=Path(args.figures_dir),
    )
    write_model_result(args.output, result)
    print(json.dumps({"run_id": args.run_id, "output": str(Path(args.output).resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
