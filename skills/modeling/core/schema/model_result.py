"""Forge v8 ModelResult schema and deterministic JSON helpers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "run_id",
    "problem_id",
    "model_version",
    "parameters",
    "metrics",
    "diagnostics",
    "tables",
    "figures",
    "rankings",
    "claims",
)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_path_get(document: Any, path: str) -> Any:
    if not path.startswith("$."):
        raise ValueError(f"Only absolute JSON paths are allowed: {path}")
    current = document
    for token in path[2:].split("."):
        match = re.fullmatch(r"([^\[]+)(?:\[(\d+)\])?", token)
        if not match:
            raise ValueError(f"Unsupported JSON path token: {token}")
        key, index = match.groups()
        if not isinstance(current, dict) or key not in current:
            raise KeyError(path)
        current = current[key]
        if index is not None:
            current = current[int(index)]
    return current


def validate_model_result(result: dict[str, Any], expected_run_id: str | None = None,
                          *, expected_schema: str | None = None) -> None:
    if not isinstance(result, dict):
        raise ValueError("ModelResult must be an object")
    missing = [field for field in REQUIRED_FIELDS if field not in result]
    if missing:
        raise ValueError(f"ModelResult missing fields: {missing}")
    schema = result.get("schema")
    if schema not in ("forge-model-result/v1", "forge-model-result/v2"):
        raise ValueError("Unsupported ModelResult.schema")
    if expected_schema is not None and schema != expected_schema:
        raise ValueError("MODEL_RESULT_CONSUMER_VERSION_MISMATCH")
    legacy = schema == "forge-model-result/v1"
    if not isinstance(result["run_id"], str) or not result["run_id"].strip():
        raise ValueError("ModelResult.run_id must be non-empty")
    if expected_run_id and result["run_id"] != expected_run_id:
        raise ValueError(f"ModelResult belongs to run {result['run_id']}, expected {expected_run_id}")
    for field in ("problem_id", "model_version"):
        if not isinstance(result[field], str) or not result[field].strip():
            raise ValueError(f"ModelResult.{field} must be non-empty")
    for field in ("parameters", "metrics", "diagnostics"):
        if not isinstance(result[field], dict):
            raise ValueError(f"ModelResult.{field} must be an object")
    for field in ("tables", "figures", "rankings", "claims"):
        if not isinstance(result[field], list):
            raise ValueError(f"ModelResult.{field} must be an array")
    def reject_nonfinite(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                reject_nonfinite(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                reject_nonfinite(child, f"{path}[{index}]")
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"ModelResult contains non-finite number at {path}")
    reject_nonfinite(result["parameters"], "parameters")
    reject_nonfinite(result["metrics"], "metrics")
    reject_nonfinite(result["diagnostics"], "diagnostics")

    if not legacy:
        _validate_general_json(result)
        if not any(result[field] for field in ("metrics", "tables", "rankings")):
            raise ValueError("GENERAL_RESULT_OUTPUT_REQUIRED")
        for collection, fields in (
            ('tables', ('id', 'source_path')), ('figures', ('id', 'caption', 'path')),
            ('claims', ('id', 'source_path')), ('rankings', ('sample',)),
        ):
            for item in result[collection]:
                if not isinstance(item, dict) or any(not isinstance(item.get(f), str) or not item[f].strip() for f in fields):
                    raise ValueError('GENERAL_RESULT_ITEM_INVALID')

    if legacy:
        weights = result["parameters"].get("entropy_weights")
        if not isinstance(weights, dict) or not weights:
            raise ValueError("ModelResult.parameters.entropy_weights must be non-empty")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value < 0 for value in weights.values()):
            raise ValueError("Entropy weights must be finite non-negative numbers")
        if not math.isclose(sum(float(value) for value in weights.values()), 1.0, abs_tol=1e-6):
            raise ValueError("Entropy weights must sum to 1")

    if legacy and not result["rankings"]:
        raise ValueError("ModelResult.rankings must be non-empty")
    samples = []
    ranks = []
    for item in result["rankings"]:
        if not isinstance(item, dict) or not item.get("sample") or (legacy and not item.get("grade")):
            raise ValueError("Each ranking needs sample, score, rank, and grade")
        score = item.get("score")
        rank = item.get("rank")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(float(score)):
            raise ValueError("Ranking scores must be finite numbers")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
            raise ValueError("Ranking ranks must be positive integers")
        samples.append(item["sample"])
        ranks.append(rank)
    if len(samples) != len(set(samples)) or len(ranks) != len(set(ranks)):
        raise ValueError("Ranking samples and ranks must be unique")
    if sorted(ranks) != list(range(1, len(ranks) + 1)):
        raise ValueError("Ranking ranks must be contiguous from 1")

    table_ids = []
    for table in result["tables"]:
        if not isinstance(table, dict) or not table.get("id") or not table.get("source_path") or "rows" not in table:
            raise ValueError("Each ModelResult table needs id, source_path, and rows")
        if legacy:
            json_path_get(result, table["source_path"])
        else:
            source = _general_fact_source(result, table["source_path"])
            if not isinstance(table['rows'], list) or canonical_json_bytes(source) != canonical_json_bytes(table['rows']):
                raise ValueError("GENERAL_TABLE_SOURCE_MISMATCH")
        table_ids.append(table["id"])
    if len(table_ids) != len(set(table_ids)):
        raise ValueError("ModelResult table ids must be unique")

    figure_ids = []
    for figure in result["figures"]:
        if not isinstance(figure, dict) or not figure.get("id") or not figure.get("caption") or not figure.get("path"):
            raise ValueError("Each ModelResult figure needs id, caption, and path")
        path = Path(figure["path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("ModelResult figure paths must be artifact-relative")
        figure_ids.append(figure["id"])
    if len(figure_ids) != len(set(figure_ids)):
        raise ValueError("ModelResult figure ids must be unique")

    claim_ids = []
    for claim in result["claims"]:
        if not isinstance(claim, dict) or not claim.get("id") or not claim.get("source_path"):
            raise ValueError("Every ModelResult claim must declare id and source_path")
        if legacy:
            json_path_get(result, claim["source_path"])
        else:
            _general_fact_source(result, claim['source_path'])
        claim_ids.append(claim["id"])
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("ModelResult claim ids must be unique")


def _validate_general_json(value: Any) -> None:
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("GENERAL_RESULT_JSON_KEY_INVALID")
        for child in value.values():
            _validate_general_json(child)
    elif isinstance(value, list):
        for child in value:
            _validate_general_json(child)
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError("GENERAL_RESULT_NONFINITE")
    elif value is not None and type(value) not in (str, int, bool):
        raise ValueError("GENERAL_RESULT_JSON_VALUE_INVALID")


def _general_fact_source(result: dict, path: str) -> Any:
    if not isinstance(path, str) or not (path == '$.rankings' or path.startswith(("$.parameters.", "$.metrics.", "$.diagnostics.", "$.rankings["))):
        raise ValueError("GENERAL_RESULT_FACT_SOURCE_INVALID")
    try:
        return json_path_get(result, path)
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError("GENERAL_RESULT_FACT_SOURCE_UNRESOLVED") from None


def load_model_result(path: str | Path, expected_run_id: str | None = None,
                      *, expected_schema: str = "forge-model-result/v1") -> dict[str, Any]:
    # Existing production/paper consumers remain pinned to v1 unless explicitly migrated.
    result = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_model_result(result, expected_run_id, expected_schema=expected_schema)
    return result


def write_model_result(path: str | Path, result: dict[str, Any]) -> None:
    validate_model_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
