"""Tool registry for the review agent.

Every tool is declared with a JSON Schema, validated before execution, and
returns a uniform envelope. That is the same contract a model-facing
Function Calling loop needs, but it works without a model provider.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?%?")
YEAR_RE = re.compile(r"^(19|20)\d{2}$")


class ToolError(RuntimeError):
    """Raised when a tool is unknown, arguments are invalid, or execution fails."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]


def _validate(spec: dict[str, Any], args: dict[str, Any]) -> None:
    if not isinstance(args, dict):
        raise ToolError("arguments must be an object")
    properties = spec.get("properties", {})
    for key in spec.get("required", []):
        if key not in args:
            raise ToolError(f"missing required argument: {key}")
    if spec.get("additionalProperties") is False:
        for key in args:
            if key not in properties:
                raise ToolError(f"unknown argument: {key}")
    for key, value in args.items():
        rule = properties.get(key, {})
        expected = rule.get("type")
        if expected == "string" and not isinstance(value, str):
            raise ToolError(f"{key} must be a string")
        if expected == "integer" and not isinstance(value, int):
            raise ToolError(f"{key} must be an integer")
        if expected == "number" and not isinstance(value, (int, float)):
            raise ToolError(f"{key} must be a number")
        if "enum" in rule and value not in rule["enum"]:
            raise ToolError(f"{key} must be one of {rule['enum']}")
        if "minimum" in rule and value < rule["minimum"]:
            raise ToolError(f"{key} must be >= {rule['minimum']}")
        if "maximum" in rule and value > rule["maximum"]:
            raise ToolError(f"{key} must be <= {rule['maximum']}")


def _hash_args(args: dict[str, Any]) -> str:
    payload = json.dumps(args, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


class RunTools:
    """Read-only tools over one completed run directory."""

    def __init__(self, run_dir: Path, index=None) -> None:
        self.run_dir = Path(run_dir).resolve()
        manifest_path = self.run_dir / "manifest.json"
        if manifest_path.is_file():
            self._manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        elif (self.run_dir / "artifacts" / "paper_spec.json").is_file():
            # Mid-run stage: the final manifest is written only at finish.
            self._manifest_data = {
                "run_id": os.environ.get("FORGE_RUN_ID", ""),
                "status": "RUNNING",
                "stages": [],
            }
        else:
            raise ToolError(f"not a run directory: {self.run_dir}")
        self.index = index
        self.specs: dict[str, ToolSpec] = {}
        self._register_all()

    # ---- registry -------------------------------------------------------
    def _register_all(self) -> None:
        self._add(
            "get_run_manifest",
            "Return run status, stage list, and gate summary.",
            {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            self._get_manifest,
        )
        self._add(
            "list_sections",
            "List paper sections with block counts.",
            {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            self._list_sections,
        )
        self._add(
            "get_section",
            "Read one paper section: claims, block types, and bindings.",
            {
                "type": "object",
                "properties": {"section_id": {"type": "string", "minLength": 1}},
                "required": ["section_id"],
                "additionalProperties": False,
            },
            self._get_section,
        )
        self._add(
            "get_frozen_numbers",
            "Read frozen numbers, optionally filtered by key prefix.",
            {
                "type": "object",
                "properties": {"prefix": {"type": "string"}},
                "required": [],
                "additionalProperties": False,
            },
            self._get_frozen_numbers,
        )
        self._add(
            "verify_numbers",
            "Extract numbers from text and check each against frozen_numbers.",
            {
                "type": "object",
                "properties": {"text": {"type": "string", "minLength": 1}},
                "required": ["text"],
                "additionalProperties": False,
            },
            self._verify_numbers,
        )
        self._add(
            "list_gate_checks",
            "Read gate reports; returns every check with its status.",
            {
                "type": "object",
                "properties": {"gate": {"type": "string"}},
                "required": [],
                "additionalProperties": False,
            },
            self._list_gate_checks,
        )
        self._add(
            "search_knowledge",
            "BM25 retrieval over paper-pattern and reviewer rule documents.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 8},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            self._search_knowledge,
        )

    def _add(self, name: str, description: str, schema: dict[str, Any], handler) -> None:
        self.specs[name] = ToolSpec(name, description, schema, handler)

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {"name": spec.name, "description": spec.description, "parameters": spec.schema}
            for spec in self.specs.values()
        ]

    def call(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        spec = self.specs.get(name)
        if spec is None:
            raise ToolError(f"unknown tool: {name}")
        arguments = args or {}
        _validate(spec.schema, arguments)
        try:
            result = spec.handler(arguments)
        except ToolError:
            raise
        except Exception as exc:  # noqa: BLE001 - wrapped into a tool error
            raise ToolError(f"{name} failed: {type(exc).__name__}: {exc}") from exc
        return {
            "tool": name,
            "ok": True,
            "args_hash": _hash_args(arguments),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            "result": result,
        }

    # ---- implementations -------------------------------------------------
    def _manifest(self) -> dict[str, Any]:
        return self._manifest_data

    def _paper_spec(self) -> dict[str, Any]:
        return json.loads((self.run_dir / "artifacts" / "paper_spec.json").read_text(encoding="utf-8"))

    def _get_manifest(self, _args: dict[str, Any]) -> dict[str, Any]:
        manifest = self._manifest()
        stages = manifest.get("stages") or []
        gate_files = sorted((self.run_dir / "gates").glob("*.json"))
        gates = []
        for path in gate_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            gates.append(
                {
                    "gate": payload.get("gate") or path.stem,
                    "status": payload.get("status"),
                    "checks": len(payload.get("checks") or []),
                    "kind": "freshness" if path.stem.startswith("freshness_") else "gate",
                }
            )
        return {
            "run_id": manifest.get("run_id"),
            "status": manifest.get("status"),
            "stages_total": len(stages),
            "stages_pass": sum(1 for s in stages if s.get("status") == "PASS"),
            "gates": gates,
        }

    def _list_sections(self, _args: dict[str, Any]) -> list[dict[str, Any]]:
        spec = self._paper_spec()
        return [
            {
                "section_id": section.get("id"),
                "title": section.get("title"),
                "blocks": len(section.get("blocks") or []),
            }
            for section in spec.get("sections") or []
        ]

    def _get_section(self, args: dict[str, Any]) -> dict[str, Any]:
        spec = self._paper_spec()
        for section in spec.get("sections") or []:
            if section.get("id") == args["section_id"]:
                blocks = []
                for block in section.get("blocks") or []:
                    blocks.append(
                        {
                            "block_id": block.get("id"),
                            "type": block.get("type"),
                            "info_class": block.get("info_class"),
                            "claim": block.get("claim") or "",
                            "has_binding": bool(block.get("template") or block.get("source")),
                        }
                    )
                claims = "\n".join(b["claim"] for b in blocks if b["claim"])
                return {
                    "section_id": section.get("id"),
                    "title": section.get("title"),
                    "blocks": blocks,
                    "text": claims,
                }
        raise ToolError(f"unknown section: {args['section_id']}")

    def _frozen(self) -> dict[str, Any]:
        return json.loads((self.run_dir / "artifacts" / "frozen_numbers.json").read_text(encoding="utf-8"))

    def _get_frozen_numbers(self, args: dict[str, Any]) -> dict[str, Any]:
        numbers = self._frozen().get("numbers") or {}
        prefix = args.get("prefix") or ""
        filtered = {key: value for key, value in numbers.items() if key.startswith(prefix)}
        return {"prefix": prefix, "count": len(filtered), "numbers": filtered}

    def _verify_numbers(self, args: dict[str, Any]) -> dict[str, Any]:
        numbers = self._frozen().get("numbers") or {}
        known = [float(v) for v in numbers.values() if isinstance(v, (int, float))]
        known_keys = {round(v, 4): key for key, v in numbers.items() if isinstance(v, (int, float))}
        text = args["text"]
        extracted = NUMBER_RE.findall(text)
        matched, unmatched = [], []
        for raw in extracted:
            token = raw.rstrip("%")
            try:
                value = float(token)
            except ValueError:
                continue
            if YEAR_RE.match(token) or abs(value) >= 1e6:
                continue  # years and ids are not claims
            hit = None
            for candidate in known:
                if abs(value - candidate) <= 1e-4 or abs(value - round(candidate, 2)) <= 0.011:
                    hit = candidate
                    break
            if hit is None:
                unmatched.append({"raw": raw, "value": value})
            else:
                matched.append({"raw": raw, "value": value, "frozen_key": known_keys.get(round(hit, 4), "")})
        return {
            "extracted": len(extracted),
            "matched": matched,
            "unmatched": unmatched,
            "note": "year-like and large id-like integers are skipped; percentages are compared to raw frozen values.",
        }

    def _list_gate_checks(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        gate_filter = args.get("gate") or ""
        rows = []
        for path in sorted((self.run_dir / "gates").glob("*.json")):
            if gate_filter and path.stem != gate_filter:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for check in payload.get("checks") or []:
                rows.append(
                    {
                        "gate": payload.get("gate") or path.stem,
                        "check": check.get("name"),
                        "status": check.get("status"),
                        "message": check.get("message") or "",
                    }
                )
        if not rows:
            raise ToolError(f"no checks found for gate={gate_filter or '*'}")
        return rows

    def _search_knowledge(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        if self.index is None:
            raise ToolError("knowledge index is not configured")
        hits = self.index.search(args["query"], top_k=args.get("top_k") or 4)
        return [
            {"doc_id": hit.doc_id, "title": hit.title, "score": hit.score, "snippet": hit.snippet}
            for hit in hits
        ]
