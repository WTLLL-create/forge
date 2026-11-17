"""Build a source-bound PaperSpec exclusively from a ModelResult."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.model_result import load_model_result, sha256_file, validate_model_result
from submission.schema.paper_spec import render_bound_text, validate_paper_spec, write_paper_spec


def binding(path: str, format_spec: str = "") -> dict:
    return {"artifact": "model_result.json", "path": path, "format": format_spec}


def bound_block(block_id: str, template: str, bindings: dict, result: dict,
                info_class: str = "confirmed") -> dict:
    if info_class not in {"original", "confirmed"}:
        raise ValueError("Bound numeric facts must be original or confirmed")
    block = {"id": block_id, "type": "bound_text", "info_class": info_class,
             "template": template, "bindings": bindings}
    block["claim"] = render_bound_text(block, result)
    return block


def build_paper_spec(result: dict, model_result_path: Path,
                     appendix_material: str | None = None) -> dict:
    validate_model_result(result, expected_schema='forge-model-result/v1')
    ranking_rows = [
        [item["sample"], f"{item['score']:.4f}", str(item["rank"]), item["grade"]]
        for item in result["rankings"]
    ]
    parameter_rows = [
        [name, f"{float(value):.4f}"]
        for name, value in sorted(result["parameters"]["entropy_weights"].items())
    ]
    figures = [
        {"id": item["id"], "type": "figure", "caption": item["caption"], "path": item["path"]}
        for item in result["figures"]
    ]
    sections = [
        {
            "id": "abstract",
            "title": "摘要",
            "blocks": [
                bound_block(
                    "abstract_metrics",
                    "本研究分析了{samples}个样本，筛选得到{core}个核心氧化标志物，其中醛类占比为{aldehyde}%。",
                    {
                        "samples": binding("$.metrics.pca.n_samples", "d"),
                        "core": binding("$.metrics.biomarkers.n_core", "d"),
                        "aldehyde": binding("$.metrics.biomarkers.aldehyde_pct", ".0f"),
                    },
                    result,
                ),
                bound_block(
                    "abstract_conclusion",
                    "综合TOPSIS贴近度评价，最优样本为{best}，最末样本为{worst}，"
                    "表明不同品种核桃油氧化进程存在显著差异，可为氧化品质监测提供依据。",
                    {
                        "best": binding("$.metrics.evaluation.best_sample"),
                        "worst": binding("$.metrics.evaluation.worst_sample"),
                    },
                    result,
                ),
            ],
        },
        {
            "id": "evaluation",
            "title": "综合评价结果",
            "blocks": [
                bound_block(
                    "best_worst",
                    "综合评价中最优样本为{best}，贴近度为{best_score}；最末样本为{worst}，贴近度为{worst_score}。",
                    {
                        "best": binding("$.metrics.evaluation.best_sample"),
                        "best_score": binding("$.metrics.evaluation.best_score", ".4f"),
                        "worst": binding("$.metrics.evaluation.worst_sample"),
                        "worst_score": binding("$.metrics.evaluation.worst_score", ".4f"),
                    },
                    result,
                ),
                {
                    "id": "ranking_table",
                    "type": "ranking_table",
                    "source": {"artifact": "model_result.json", "path": "$.rankings"},
                    "headers": ["样本", "TOPSIS贴近度", "排名", "等级"],
                    "rows": ranking_rows,
                },
            ],
        },
        {
            "id": "parameters",
            "title": "模型参数",
            "blocks": [
                {
                    "id": "entropy_weights",
                    "type": "parameter_table",
                    "source": {"artifact": "model_result.json", "path": "$.parameters.entropy_weights"},
                    "headers": ["指标", "熵权"],
                    "rows": parameter_rows,
                }
            ],
        },
        {
            "id": "robustness",
            "title": "稳健性检验",
            "blocks": [
                bound_block(
                    "rank_stability",
                    "权重扰动检验中的前三名稳定率为{stability}%。",
                    {"stability": binding("$.metrics.sensitivity.rank_stability_pct", ".0f")},
                    result,
                )
            ],
        },
        {"id": "figures", "title": "结果图示", "blocks": figures},
    ]
    if appendix_material:
        sections.append(
            {
                "id": "appendix",
                "title": "附录",
                "blocks": [
                    {
                        "id": "appendix_declaration",
                        "type": "static_text",
                        "info_class": "confirmed",
                        "source": {"artifact": "workflow_artifacts"},
                        "text": appendix_material,
                    }
                ],
            }
        )
    spec = {
        "schema": "forge-paper-spec/v1",
        "run_id": result["run_id"],
        "problem_id": result["problem_id"],
        "model_result": {"artifact": "model_result.json", "sha256": sha256_file(model_result_path)},
        "title": "核桃油加速氧化过程中VOCs变化规律与综合品质评价",
        "sections": sections,
        "expected_artifacts": {"tables": 2, "figures": len(figures), "equations": 0},
    }
    validate_paper_spec(spec, result, model_result_path)
    return spec


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-result", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--appendix-material",
        default=None,
        help="Appendix declaration text (2026 revision: support materials / programs). "
        "Newlines separated by \\n. Omit to keep the paper without an appendix section.",
    )
    args = parser.parse_args()
    model_path = Path(args.model_result)
    result = load_model_result(model_path)
    spec = build_paper_spec(result, model_path, appendix_material=args.appendix_material)
    write_paper_spec(args.output, spec)
    print(json.dumps({"run_id": spec["run_id"], "output": str(Path(args.output).resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
