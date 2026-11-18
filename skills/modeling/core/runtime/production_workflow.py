"""Forge v8 production workflow library.

This module deliberately has no direct production CLI. The sole production
entry point is ``workflow_executor.py --config workflow.json``.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import shutil
import subprocess
import sys
import uuid
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, validate_gate_result, write_gate_result
from core.schema.model_result import load_model_result
from core.runtime.artifact_store import ArtifactStore
from submission.schema.paper_spec import load_paper_spec, validate_paper_spec
from submission.schema.render_paper_spec import render_markdown


SCHEMA = "forge-project-workflow/v2"
ALLOWED_REQUIRE_ROOTS = {"inputs", "artifacts", "gates"}
ALLOWED_OUTPUT_ROOTS = {"artifacts", "gates"}
FILE_SUFFIXES = {".json", ".csv", ".tsv", ".xlsx", ".xls", ".docx", ".md", ".png", ".jpg", ".jpeg", ".pdf", ".log"}
IMPORTABLE_CODE_SUFFIXES = {".py", ".pyc", ".pyd", ".so", ".dll"}
FORBIDDEN_INPUT_PARTS = {"data", "results", "figures", "runtime", "runs", "artifacts", "gates", "logs", "published"}
FORBIDDEN_INPUT_NAMES = {"paper_draft.md", "paper_final.docx", "submission.docx", "model_result.json", "paper_spec.json"}
# 2026 CUMCM revision: the appendix must declare support materials / programs.
# Fixed trusted value so a project cannot inject arbitrary appendix text through the trust chain.
APPENDIX_DECLARATION = (
    "支撑材料包括：数据文件、计算结果、可运行源码与结果图示。"
    "全部文件及运行方法见随论文提交的支撑材料清单。"
)
TRUST_CHAIN_OUTPUTS = {
    "model_compute": {"artifacts/model_result.json"},
    "build_paper_spec": {"artifacts/paper_spec.json"},
    "render_markdown": {"artifacts/paper.md"},
    "compile_docx": {"artifacts/submission.docx"},
    "scientific_gate": {"gates/scientific_gate.json"},
    "template_compliance_gate": {"gates/template_compliance_gate.json"},
    "artifact_integrity_gate": {"gates/artifact_integrity_gate.json"},
    "publish_gate": {"artifacts/published/submission.docx", "gates/publish_gate.json"},
}
CANONICAL_TRUST_SCRIPTS = {
    "build_paper_spec": MODELING_ROOT / "submission" / "schema" / "build_paper_spec.py",
    "render_markdown": MODELING_ROOT / "submission" / "schema" / "render_paper_spec.py",
    "compile_docx": MODELING_ROOT / "submission" / "compilers" / "template_docx_compiler.py",
    "scientific_gate": MODELING_ROOT / "submission" / "gates" / "scientific_gate.py",
    "template_compliance_gate": MODELING_ROOT / "submission" / "validators" / "template_compliance_gate.py",
    "artifact_integrity_gate": MODELING_ROOT / "submission" / "validators" / "artifact_integrity_gate.py",
    "publish_gate": MODELING_ROOT / "submission" / "gates" / "publish_gate.py",
}
PATH_ARGUMENTS = {
    "--input", "--output", "--output-dir", "--results-dir", "--summary", "--rankings",
    "--kinetics", "--figures-dir", "--model-result", "--paper-spec", "--markdown", "--docx",
    "--report", "--template", "--style-contract", "--gate", "--source", "--problem-source",
    # 2026 compliance gates (ai_usage_doc / ai_compliance / number_freeze /
    # human_judgment / aigc_audit / writing_quality) read current-run paths only.
    "--usage", "--support-dir", "--frozen", "--freeze-log", "--judgments",
}
SCALAR_ARGUMENTS = {"--problem-id", "--model-version", "--appendix-material", "--tolerance", "--required-gate"}
SAFE_STAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
CANONICAL_TRUST_ARGUMENTS = {
    "build_paper_spec": [
        "--model-result", "${RUN_ARTIFACTS}/model_result.json",
        "--output", "${RUN_ARTIFACTS}/paper_spec.json",
        "--appendix-material", APPENDIX_DECLARATION,
    ],
    "render_markdown": [
        "--paper-spec", "${RUN_ARTIFACTS}/paper_spec.json",
        "--model-result", "${RUN_ARTIFACTS}/model_result.json",
        "--output", "${RUN_ARTIFACTS}/paper.md",
    ],
    "compile_docx": [
        "--input", "${RUN_ARTIFACTS}/paper.md",
        "--output", "${RUN_ARTIFACTS}/submission.docx",
        "--template", "${RUN_INPUTS}/template/CUMCM_template.docx",
        "--style-contract", "${RUN_INPUTS}/template/cumcm_template.json",
        "--figures-dir", "${RUN_ARTIFACTS}/figures",
    ],
    "scientific_gate": [
        "--run-id", "${RUN_ID}",
        "--model-result", "${RUN_ARTIFACTS}/model_result.json",
        "--paper-spec", "${RUN_ARTIFACTS}/paper_spec.json",
        "--markdown", "${RUN_ARTIFACTS}/paper.md",
        "--docx", "${RUN_ARTIFACTS}/submission.docx",
        "--report", "${RUN_GATES}/scientific_gate.json",
    ],
    "template_compliance_gate": [
        "--run-id", "${RUN_ID}",
        "--docx", "${RUN_ARTIFACTS}/submission.docx",
        "--template", "${RUN_INPUTS}/template/CUMCM_template.docx",
        "--style-contract", "${RUN_INPUTS}/template/cumcm_template.json",
        "--report", "${RUN_GATES}/template_compliance_gate.json",
    ],
    "artifact_integrity_gate": [
        "--run-id", "${RUN_ID}",
        "--paper-spec", "${RUN_ARTIFACTS}/paper_spec.json",
        "--docx", "${RUN_ARTIFACTS}/submission.docx",
        "--report", "${RUN_GATES}/artifact_integrity_gate.json",
    ],
    "publish_gate": [
        "--run-id", "${RUN_ID}",
        "--gate", "${RUN_GATES}/scientific_gate.json",
        "--gate", "${RUN_GATES}/template_compliance_gate.json",
        "--gate", "${RUN_GATES}/artifact_integrity_gate.json",
        "--gate", "${RUN_GATES}/ai_compliance_gate.json",
        "--gate", "${RUN_GATES}/number_freeze_gate.json",
        "--gate", "${RUN_GATES}/human_judgment_gate.json",
        "--gate", "${RUN_GATES}/aigc_audit_gate.json",
        "--gate", "${RUN_GATES}/writing_quality_gate.json",
        "--required-gate", "ai_compliance_gate",
        "--required-gate", "number_freeze_gate",
        "--required-gate", "human_judgment_gate",
        "--required-gate", "aigc_audit_gate",
        "--required-gate", "writing_quality_gate",
        "--source", "${RUN_ARTIFACTS}/submission.docx",
        "--output", "${RUN_ARTIFACTS}/published/submission.docx",
        "--report", "${RUN_GATES}/publish_gate.json",
    ],
}
TRUST_STAGE_REQUIRES = {
    "build_paper_spec": {"artifacts/model_result.json"},
    "render_markdown": {"artifacts/model_result.json", "artifacts/paper_spec.json"},
    "compile_docx": {
        "artifacts/paper.md",
        "inputs/template/CUMCM_template.docx",
        "inputs/template/cumcm_template.json",
    },
    "scientific_gate": {
        "artifacts/model_result.json", "artifacts/paper_spec.json",
        "artifacts/paper.md", "artifacts/submission.docx",
    },
    "template_compliance_gate": {
        "artifacts/submission.docx",
        "inputs/template/CUMCM_template.docx",
        "inputs/template/cumcm_template.json",
    },
    "artifact_integrity_gate": {"artifacts/paper_spec.json", "artifacts/submission.docx"},
    "publish_gate": {
        "gates/scientific_gate.json", "gates/template_compliance_gate.json",
        "gates/artifact_integrity_gate.json", "gates/ai_compliance_gate.json",
        "gates/number_freeze_gate.json", "gates/human_judgment_gate.json",
        "gates/aigc_audit_gate.json", "gates/writing_quality_gate.json",
        "artifacts/submission.docx",
    },
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_time(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def safe_relative(value: str, allowed_roots: set[str]) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] not in allowed_roots:
        raise ValueError(f"Run path is outside its allowed roots: {value}")
    return path


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def run_relative_from_token(value: str) -> str | None:
    prefixes = {
        "${RUN_INPUTS}/": "inputs/",
        "${RUN_ARTIFACTS}/": "artifacts/",
        "${RUN_LOGS}/": "logs/",
        "${RUN_GATES}/": "gates/",
        "${RUN_ROOT}/": "",
    }
    normalized = value.replace("\\", "/")
    for token, relative in prefixes.items():
        if normalized.startswith(token):
            return relative + normalized[len(token):]
    return None


class ProductionWorkflow:
    """Execute one validated workflow in one isolated run directory."""

    def __init__(self, config_path: str | Path, python_executable: str | Path | None = None,
                 runtime_root: str | Path | None = None):
        self.config_path = Path(config_path).resolve()
        if not self.config_path.is_file():
            raise FileNotFoundError(f"Workflow config not found: {self.config_path}")
        config_bytes = self.config_path.read_bytes()
        self._config_hash = hashlib.sha256(config_bytes).hexdigest()
        self.project_dir = self.config_path.parent
        self.config = json.loads(config_bytes.decode("utf-8"))
        self.python_executable = Path(python_executable or sys.executable).resolve()
        runtime_setting = runtime_root or self.config.get("runtime_root", "runtime/runs")
        runtime_candidate = Path(runtime_setting)
        self.runtime_root = (
            runtime_candidate.resolve()
            if runtime_candidate.is_absolute()
            else (self.project_dir / runtime_candidate).resolve()
        )
        self.current_run = self.runtime_root / "current_run"
        self.lock_path = self.runtime_root / ".active_run.lock"
        self.run_id = ""
        self.manifest: dict[str, Any] = {}
        self._prepared = False
        self._owns_lock = False
        self._validate_config()
        self._code_hashes = {
            str(path): sha256_file(path)
            for path in sorted(self._trusted_code_paths(), key=lambda item: str(item).lower())
        }
        self._code_hashes[str(self.config_path)] = self._config_hash

    def _validate_config(self) -> None:
        if self.config.get("schema") != SCHEMA:
            raise ValueError(f"Production requires schema {SCHEMA}")
        if not self.config.get("workflow_id"):
            raise ValueError("workflow_id is required")
        if not isinstance(self.config.get("inputs"), list):
            raise ValueError("inputs must be an array")
        stages = self.config.get("stages")
        if not isinstance(stages, list) or not stages:
            raise ValueError("stages must be a non-empty array")
        seen: set[str] = set()
        for stage in stages:
            stage_id = stage.get("id")
            if not stage_id or stage_id in seen:
                raise ValueError(f"Stage id is missing or duplicated: {stage_id}")
            if not SAFE_STAGE_ID.fullmatch(str(stage_id)):
                raise ValueError(f"Stage id must be a safe slug: {stage_id}")
            seen.add(stage_id)
            if not stage.get("script"):
                raise ValueError(f"Stage {stage_id} has no script")
            for value in stage.get("requires", []):
                safe_relative(value, ALLOWED_REQUIRE_ROOTS)
            outputs = stage.get("produces", [])
            if not outputs:
                raise ValueError(f"Stage {stage_id} must declare at least one output")
            for value in outputs:
                safe_relative(value, ALLOWED_OUTPUT_ROOTS)
        ordered_ids = [stage["id"] for stage in stages]
        positions = []
        missing_trust = []
        for required_id in TRUST_CHAIN_OUTPUTS:
            if required_id not in ordered_ids:
                missing_trust.append(required_id)
            else:
                positions.append(ordered_ids.index(required_id))
        if missing_trust or positions != sorted(positions):
            raise ValueError(
                "Production trust chain is missing or out of order: "
                f"missing={missing_trust}, required={list(TRUST_CHAIN_OUTPUTS)}"
            )
        by_id = {stage["id"]: stage for stage in stages}
        for stage_id, required_outputs in TRUST_CHAIN_OUTPUTS.items():
            actual_outputs = set(by_id[stage_id].get("produces", []))
            if required_outputs != actual_outputs:
                raise ValueError(
                    f"Production trust chain stage {stage_id} outputs must be argument-bound exactly to "
                    f"{sorted(required_outputs)}"
                )
        for stage_id, canonical_script in CANONICAL_TRUST_SCRIPTS.items():
            raw_script = Path(by_id[stage_id]["script"])
            resolved_script = raw_script.resolve() if raw_script.is_absolute() else (self.project_dir / raw_script).resolve()
            if resolved_script != canonical_script.resolve():
                raise ValueError(
                    f"Production trust chain stage {stage_id} must use canonical script {canonical_script}"
                )
        for item in self.config["inputs"]:
            if not isinstance(item, dict) or not item.get("source") or not item.get("target"):
                raise ValueError("Each input requires source and target")
            if item.get("kind") not in {"source", "template"}:
                raise ValueError("Each input requires kind=source or kind=template")
            target = Path(item["target"])
            if target.is_absolute() or ".." in target.parts or not target.parts:
                raise ValueError(f"Unsafe input target: {item['target']}")
            target_is_template = target.parts[0].lower() == "template"
            if (item["kind"] == "template") != target_is_template:
                raise ValueError(
                    f"Input kind={item['kind']} cannot cross its target namespace: {item['target']}"
                )
            source_value = Path(item["source"])
            source = source_value.resolve() if source_value.is_absolute() else (self.project_dir / source_value).resolve()
            lowered_parts = {part.lower() for part in source.parts}
            if lowered_parts & FORBIDDEN_INPUT_PARTS or source.name.lower() in FORBIDDEN_INPUT_NAMES:
                raise ValueError(f"A derived-output path cannot be declared as a production input: {source}")
            if is_within(source, self.runtime_root):
                raise ValueError(f"Inputs may not come from current or previous runs: {source}")
            approved_roots = (
                [self.project_dir / "task_assets", self.project_dir / "source_inputs"]
                if item["kind"] == "source"
                else [self.project_dir / "templates", MODELING_ROOT / "submission" / "templates"]
            )
            if not any(is_within(source, root) for root in approved_roots):
                raise ValueError(
                    f"Input is outside an approved source directory for kind={item['kind']}: {source}"
                )
        known_tokens = {"${RUN_ID}", "${RUN_ROOT}", "${RUN_INPUTS}", "${RUN_ARTIFACTS}", "${RUN_LOGS}", "${RUN_GATES}"}
        for stage in stages:
            args = [str(value) for value in stage.get("args", [])]
            if len(args) % 2 or any(
                not args[index].startswith("--")
                or "=" in args[index]
                or args[index + 1].startswith("--")
                for index in range(0, len(args), 2)
            ):
                raise ValueError(f"Stage {stage['id']} arguments must be explicit --flag/value pairs")
            flags = args[::2]
            duplicate_flags = [flag for flag, count in Counter(flags).items() if count > 1 and flag not in {"--gate", "--required-gate"}]
            if duplicate_flags:
                raise ValueError(f"Stage {stage['id']} has duplicate arguments: {duplicate_flags}")
            for index in range(0, len(args), 2):
                flag, value = args[index], args[index + 1]
                if flag not in PATH_ARGUMENTS | SCALAR_ARGUMENTS | {"--run-id"}:
                    raise ValueError(
                        f"Unsupported argument {flag} in stage {stage['id']}; its value may point outside current run"
                    )
                referenced_tokens = {"${" + part.split("}", 1)[0] + "}" for part in value.split("${")[1:] if "}" in part}
                unknown_tokens = referenced_tokens - known_tokens
                if unknown_tokens:
                    raise ValueError(f"Unknown run token in stage {stage['id']} argument: {value}")
                if flag == "--run-id":
                    if value != "${RUN_ID}":
                        raise ValueError(f"Stage {stage['id']} --run-id must use ${{RUN_ID}}")
                    continue
                if flag in SCALAR_ARGUMENTS:
                    continue
                candidate_value = Path(value)
                looks_like_path = (
                    flag in PATH_ARGUMENTS
                    or candidate_value.is_absolute()
                    or "/" in value
                    or "\\" in value
                    or candidate_value.suffix.lower() in FILE_SUFFIXES
                )
                if not looks_like_path:
                    continue
                expanded = value
                replacements = {
                    "${RUN_ROOT}": str(self.current_run),
                    "${RUN_INPUTS}": str(self.current_run / "inputs"),
                    "${RUN_ARTIFACTS}": str(self.current_run / "artifacts"),
                    "${RUN_LOGS}": str(self.current_run / "logs"),
                    "${RUN_GATES}": str(self.current_run / "gates"),
                }
                for token, replacement in replacements.items():
                    expanded = expanded.replace(token, replacement)
                if not referenced_tokens & (known_tokens - {"${RUN_ID}"}):
                    raise ValueError(
                        f"Stage {stage['id']} path argument {flag} points outside current run; use a RUN_* token: {value}"
                    )
                candidate = Path(expanded)
                resolved = candidate.resolve() if candidate.is_absolute() else (self.project_dir / candidate).resolve()
                if not is_within(resolved, self.current_run):
                    raise ValueError(f"Stage {stage['id']} argument points outside current run: {value}")

        model_args = [str(value) for value in by_id["model_compute"].get("args", [])]
        model_pairs = dict(zip(model_args[::2], model_args[1::2]))
        if model_pairs.get("--run-id") != "${RUN_ID}" or model_pairs.get("--output") != "${RUN_ARTIFACTS}/model_result.json":
            raise ValueError("Production trust chain stage model_compute violates its canonical argument binding")
        for stage_id, expected_args in CANONICAL_TRUST_ARGUMENTS.items():
            actual_args = [str(value) for value in by_id[stage_id].get("args", [])]
            if actual_args != expected_args:
                raise ValueError(
                    f"Production trust chain stage {stage_id} violates its canonical argument binding"
                )
            missing_requires = TRUST_STAGE_REQUIRES[stage_id] - set(by_id[stage_id].get("requires", []))
            if missing_requires:
                raise ValueError(
                    f"Production trust chain stage {stage_id} is missing canonical requires: {sorted(missing_requires)}"
                )
        for stage_id in TRUST_CHAIN_OUTPUTS:
            stage = by_id[stage_id]
            args = [str(value) for value in stage.get("args", [])]
            input_files: set[str] = set()
            input_directories: set[str] = set()
            output_files: set[str] = set()
            for index in range(0, len(args), 2):
                flag, value = args[index], args[index + 1]
                if flag not in PATH_ARGUMENTS:
                    continue
                if flag == "--output-dir":
                    raise ValueError(
                        f"Production trust chain stage {stage_id} output arguments cannot use --output-dir; "
                        "each output file must be declared explicitly"
                    )
                relative = run_relative_from_token(value)
                if relative is None:
                    continue
                if flag in {"--output", "--report"}:
                    output_files.add(relative)
                    continue
                if flag in {"--figures-dir", "--results-dir"}:
                    input_directories.add(relative.rstrip("/"))
                else:
                    input_files.add(relative)
            actual_requires = set(stage.get("requires", []))
            missing_inputs = sorted(input_files - actual_requires)
            unbound_requires = sorted(
                value for value in actual_requires
                if value not in input_files
                and not any(value.startswith(directory + "/") for directory in input_directories)
            )
            if missing_inputs or unbound_requires:
                raise ValueError(
                    f"Production trust chain stage {stage_id} requires must be argument-bound; "
                    f"missing={missing_inputs}, unbound={unbound_requires}"
                )
            actual_outputs = set(stage.get("produces", []))
            missing_outputs = sorted(output_files - actual_outputs)
            unbound_outputs = sorted(
                value for value in actual_outputs
                if value not in output_files
            )
            if missing_outputs or unbound_outputs:
                raise ValueError(
                    f"Production trust chain stage {stage_id} output arguments must bind every produced file; "
                    f"missing={missing_outputs}, unbound={unbound_outputs}"
                )

    def _trusted_code_paths(self) -> set[Path]:
        paths: set[Path] = {Path(__file__).resolve(), self.config_path}
        for stage in self.config["stages"]:
            value = Path(stage["script"])
            path = value.resolve() if value.is_absolute() else (self.project_dir / value).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Stage script missing during code attestation: {path}")
            paths.update(
                candidate.resolve()
                for candidate in path.parent.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in IMPORTABLE_CODE_SUFFIXES
            )
        for folder in (
            MODELING_ROOT / "core" / "schema",
            MODELING_ROOT / "submission" / "schema",
            MODELING_ROOT / "submission" / "gates",
            MODELING_ROOT / "submission" / "validators",
        ):
            paths.update(path.resolve() for path in folder.glob("*.py"))
        paths.add((MODELING_ROOT / "submission" / "compilers" / "template_docx_compiler.py").resolve())
        paths.add((MODELING_ROOT / "core" / "runtime" / "build_model_result.py").resolve())
        return paths

    def _new_run_id(self) -> str:
        stamp = utc_now().strftime("%Y%m%dT%H%M%S%fZ")
        return f"{stamp}-{uuid.uuid4().hex[:10]}"

    def _write_manifest(self) -> None:
        target = self.current_run / "manifest.json"
        target.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def _archive_abandoned_current(self) -> None:
        if not self.current_run.exists():
            return
        abandoned = self.runtime_root / f"abandoned-{self._new_run_id()}"
        self.current_run.rename(abandoned)

    def _acquire_lock(self) -> None:
        descriptor = None
        for attempt in range(2):
            try:
                descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError as exc:
                try:
                    owner = json.loads(self.lock_path.read_text(encoding="utf-8"))
                except Exception:
                    owner = None
                same_host = isinstance(owner, dict) and owner.get("host") == socket.gethostname()
                owner_pid = owner.get("pid") if isinstance(owner, dict) else None
                alive = isinstance(owner_pid, int) and self._process_is_alive(owner_pid)
                if attempt == 0 and same_host and isinstance(owner_pid, int) and not alive:
                    stale = self.runtime_root / f".stale-lock-{utc_now().strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
                    try:
                        self.lock_path.rename(stale)
                    except FileNotFoundError:
                        pass
                    continue
                owner_text = json.dumps(owner, ensure_ascii=False) if owner is not None else "unreadable lock"
                raise RuntimeError(f"An active run already owns {self.runtime_root}: {owner_text}") from exc
        if descriptor is None:
            raise RuntimeError(f"Could not acquire run lock for {self.runtime_root}")
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                {"pid": os.getpid(), "host": socket.gethostname(), "config": str(self.config_path), "acquired_at": iso_time()},
                stream,
            )
        self._owns_lock = True

    @staticmethod
    def _process_is_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        if os.name == "nt":
            # os.kill(pid, 0) is not a portable Windows liveness probe.
            # Query a handle without sending any signal; unknown access fails closed.
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.WaitForSingleObject.restype = wintypes.DWORD
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
            if not handle:
                return ctypes.get_last_error() != 87  # invalid PID; access denied is unknown
            try:
                return kernel.WaitForSingleObject(handle, 0) != 0  # signalled = exited
            finally:
                kernel.CloseHandle(handle)
        try:
            os.kill(pid, 0)
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _release_lock(self) -> None:
        if self._owns_lock and self.lock_path.exists():
            self.lock_path.unlink()
        self._owns_lock = False

    def prepare(self) -> Path:
        if self._prepared:
            raise RuntimeError("Run is already prepared")
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self._acquire_lock()
        try:
            self._archive_abandoned_current()
            self.run_id = self._new_run_id()
            for name in ("inputs", "artifacts", "logs", "gates"):
                (self.current_run / name).mkdir(parents=True, exist_ok=False)

            registered_inputs = []
            for item in self.config["inputs"]:
                source_value = Path(item["source"])
                source = source_value.resolve() if source_value.is_absolute() else (self.project_dir / source_value).resolve()
                if is_within(source, self.runtime_root):
                    raise ValueError(f"Inputs may not come from current or previous runs: {source}")
                if not source.is_file():
                    raise FileNotFoundError(f"Required input missing: {source}")
                target = self.current_run / "inputs" / Path(item["target"])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                registered_inputs.append(
                    {
                        "path": target.relative_to(self.current_run).as_posix(),
                        "sha256": sha256_file(target),
                        "source": str(source),
                        "copied_at": iso_time(),
                    }
                )

            self.manifest = {
                "schema": "forge-run-manifest/v1",
                "run_id": self.run_id,
                "workflow_id": self.config["workflow_id"],
                "config": str(self.config_path),
                "config_sha256": self._config_hash,
                "status": "RUNNING",
                "start_time": iso_time(),
                "end_time": None,
                "inputs": registered_inputs,
                "code": [
                    {"path": path, "sha256": digest}
                    for path, digest in sorted(self._code_hashes.items())
                ],
                "stages": [],
                "artifact_registry": None,
                "artifacts": [],
            }
            self._write_manifest()
            self._prepared = True
            return self.current_run
        except Exception:
            self._release_lock()
            raise

    def _expand_arg(self, value: str) -> str:
        replacements = {
            "${RUN_ID}": self.run_id,
            "${RUN_ROOT}": str(self.current_run),
            "${RUN_INPUTS}": str(self.current_run / "inputs"),
            "${RUN_ARTIFACTS}": str(self.current_run / "artifacts"),
            "${RUN_LOGS}": str(self.current_run / "logs"),
            "${RUN_GATES}": str(self.current_run / "gates"),
        }
        expanded = str(value)
        for token, replacement in replacements.items():
            expanded = expanded.replace(token, replacement)
        return expanded

    def _stage_inputs(self, stage: dict[str, Any]) -> tuple[list[Path], str]:
        paths = [self.current_run / safe_relative(value, ALLOWED_REQUIRE_ROOTS) for value in stage.get("requires", [])]
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Stage {stage['id']} missing current-run inputs: {missing}")
        hashes = {path.relative_to(self.current_run).as_posix(): sha256_file(path) for path in paths}
        return paths, sha256_json(hashes)

    def _stage_outputs(self, stage: dict[str, Any]) -> list[Path]:
        return [self.current_run / safe_relative(value, ALLOWED_OUTPUT_ROOTS) for value in stage["produces"]]

    def _script_path(self, stage: dict[str, Any]) -> Path:
        value = Path(stage["script"])
        script = value.resolve() if value.is_absolute() else (self.project_dir / value).resolve()
        if not script.is_file():
            raise FileNotFoundError(f"Stage script missing: {script}")
        expected_hash = self._code_hashes.get(str(script))
        if expected_hash is None or sha256_file(script) != expected_hash:
            raise RuntimeError(f"Stage script changed after workflow validation: {script}")
        return script

    def _stage_environment(self, stage_id: str) -> dict[str, str]:
        environment = os.environ.copy()
        if stage_id in TRUST_CHAIN_OUTPUTS:
            python_paths = [str(MODELING_ROOT)]
        else:
            configured_python_paths = []
            for raw in self.config.get("python_paths", []):
                candidate = Path(raw)
                configured_python_paths.append(
                    str(candidate.resolve() if candidate.is_absolute() else (self.project_dir / candidate).resolve())
                )
            inherited = [environment["PYTHONPATH"]] if environment.get("PYTHONPATH") else []
            python_paths = [str(MODELING_ROOT), *configured_python_paths, *inherited]
        environment["PYTHONPATH"] = os.pathsep.join(python_paths)
        environment.update(
            {
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "FORGE_RUN_ID": self.run_id,
                "FORGE_RUN_ROOT": str(self.current_run),
                "FORGE_RUN_INPUTS": str(self.current_run / "inputs"),
                "FORGE_RUN_ARTIFACTS": str(self.current_run / "artifacts"),
                "FORGE_RUN_LOGS": str(self.current_run / "logs"),
                "FORGE_RUN_GATES": str(self.current_run / "gates"),
            }
        )
        return environment

    def _write_freshness_gate(self, stage_id: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
        result = gate_result(f"freshness_{stage_id}", checks, run_id=self.run_id)
        write_gate_result(self.current_run / "gates" / f"freshness_{stage_id}.json", result)
        return result

    def _validate_trust_output(self, stage_id: str) -> tuple[bool, str]:
        """Validate semantic identity at each mandatory trust-chain boundary."""
        artifacts = self.current_run / "artifacts"
        gates = self.current_run / "gates"
        try:
            if stage_id == "model_compute":
                load_model_result(artifacts / "model_result.json", self.run_id)
            elif stage_id == "build_paper_spec":
                model_path = artifacts / "model_result.json"
                model = load_model_result(model_path, self.run_id)
                spec = load_paper_spec(artifacts / "paper_spec.json")
                validate_paper_spec(spec, model, model_path)
            elif stage_id == "render_markdown":
                spec = load_paper_spec(artifacts / "paper_spec.json")
                actual = (artifacts / "paper.md").read_text(encoding="utf-8")
                if actual != render_markdown(spec):
                    raise ValueError("paper.md is not the deterministic rendering of PaperSpec")
            elif stage_id in {
                "scientific_gate", "template_compliance_gate", "artifact_integrity_gate", "publish_gate"
            }:
                expected_gate = stage_id
                report = json.loads((gates / f"{stage_id}.json").read_text(encoding="utf-8"))
                validate_gate_result(report)
                if report["gate"] != expected_gate or report["run_id"] != self.run_id:
                    raise ValueError(
                        f"Gate identity mismatch: gate={report.get('gate')} run_id={report.get('run_id')}"
                    )
                if report["status"] != "PASS":
                    raise ValueError(f"Gate {expected_gate} did not pass")
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _check_run_integrity(self) -> bool:
        registered = list(self.manifest.get("inputs", []))
        for stage in self.manifest.get("stages", []):
            registered.extend(stage.get("outputs", []))
        mismatches = []
        for item in registered:
            relative = safe_relative(item["path"], ALLOWED_REQUIRE_ROOTS)
            path = self.current_run / relative
            if not path.is_file():
                mismatches.append({"path": item["path"], "reason": "missing"})
                continue
            actual_hash = sha256_file(path)
            if actual_hash != item["sha256"]:
                mismatches.append(
                    {"path": item["path"], "reason": "sha256 changed", "expected": item["sha256"], "actual": actual_hash}
                )
        result = gate_result(
            "run_integrity",
            [
                gate_check(
                    "registered inputs and prior outputs remain unchanged",
                    not mismatches,
                    actual=mismatches,
                    expected=[],
                    message="A registered current-run file changed after its producing boundary.",
                )
            ],
            run_id=self.run_id,
        )
        write_gate_result(self.current_run / "gates" / "run_integrity.json", result)
        return result["status"] == "PASS"

    def _check_code_integrity(self) -> bool:
        mismatches = []
        expected_paths = set(self._code_hashes)
        current_paths = {str(path) for path in self._trusted_code_paths()}
        for raw_path in sorted(current_paths - expected_paths):
            mismatches.append({"path": raw_path, "reason": "unexpected code file"})
        for raw_path in sorted(expected_paths - current_paths):
            mismatches.append({"path": raw_path, "reason": "missing from code inventory"})
        for raw_path, expected_hash in self._code_hashes.items():
            path = Path(raw_path)
            if not path.is_file():
                mismatches.append({"path": raw_path, "reason": "missing"})
                continue
            actual_hash = sha256_file(path)
            if actual_hash != expected_hash:
                mismatches.append(
                    {"path": raw_path, "reason": "sha256 changed", "expected": expected_hash, "actual": actual_hash}
                )
        result = gate_result(
            "code_integrity",
            [
                gate_check(
                    "configured scripts and trust modules remain unchanged",
                    not mismatches,
                    actual=mismatches,
                    expected=[],
                    message="Production code changed after workflow validation.",
                )
            ],
            run_id=self.run_id,
        )
        write_gate_result(self.current_run / "gates" / "code_integrity.json", result)
        return result["status"] == "PASS"

    def _run_stage(self, stage: dict[str, Any]) -> bool:
        stage_id = stage["id"]
        started = utc_now()
        outputs = self._stage_outputs(stage)
        preexisting = [path.relative_to(self.current_run).as_posix() for path in outputs if path.exists()]
        if preexisting:
            freshness = self._write_freshness_gate(
                stage_id,
                [gate_check("declared outputs absent before stage", False, actual=preexisting, expected=[])],
            )
            self.manifest["stages"].append(
                {
                    "stage": stage_id,
                    "start_time": iso_time(started),
                    "end_time": iso_time(),
                    "inputs_hash": None,
                    "outputs": [],
                    "status": "FAIL",
                    "errors": ["A declared output existed before this stage; stale artifact reuse is forbidden."],
                    "freshness_gate": freshness["status"],
                }
            )
            self._write_manifest()
            return False

        try:
            input_paths, inputs_hash = self._stage_inputs(stage)
            script = self._script_path(stage)
        except Exception as exc:
            freshness = self._write_freshness_gate(
                stage_id,
                [gate_check("current-run inputs and script are available", False, message=str(exc))],
            )
            self.manifest["stages"].append(
                {
                    "stage": stage_id,
                    "start_time": iso_time(started),
                    "end_time": iso_time(),
                    "inputs_hash": None,
                    "outputs": [],
                    "status": "FAIL",
                    "errors": [str(exc)],
                    "freshness_gate": freshness["status"],
                }
            )
            self._write_manifest()
            return False

        for output in outputs:
            output.parent.mkdir(parents=True, exist_ok=True)
        stdout_path = self.current_run / "logs" / f"{stage_id}.stdout.log"
        stderr_path = self.current_run / "logs" / f"{stage_id}.stderr.log"
        command = [str(self.python_executable), str(script), *[self._expand_arg(arg) for arg in stage.get("args", [])]]
        environment = self._stage_environment(stage_id)
        timeout = int(stage.get("timeout_seconds", self.config.get("timeout_seconds", 900)))
        try:
            completed = subprocess.run(
                command,
                cwd=self.project_dir,
                env=environment,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=timeout,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            # TimeoutExpired may expose bytes even with text=True.
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stderr += f"\nStage timed out after {timeout} seconds."
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")

        ended = utc_now()
        missing = [path.relative_to(self.current_run).as_posix() for path in outputs if not path.is_file()]
        stale_times = []
        output_records = []
        for path in outputs:
            if not path.is_file():
                continue
            stat = path.stat()
            if stat.st_mtime + 1e-6 < started.timestamp():
                stale_times.append(path.relative_to(self.current_run).as_posix())
            output_records.append(
                {
                    "path": path.relative_to(self.current_run).as_posix(),
                    "sha256": sha256_file(path),
                    "created_at": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat().replace("+00:00", "Z"),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
                    "produced_by": stage_id,
                }
            )
        trust_ok, trust_error = (True, "")
        if returncode == 0 and not missing and stage_id in TRUST_CHAIN_OUTPUTS:
            trust_ok, trust_error = self._validate_trust_output(stage_id)
        artifact_registration_ok = True
        artifact_registration_error = ""
        if stage_id == "model_compute":
            artifact_registration_ok = False
            if returncode == 0 and not missing and not stale_times and trust_ok:
                try:
                    model_path = self.current_run / "artifacts" / "model_result.json"
                    model_result = load_model_result(model_path, self.run_id)
                    artifact = ArtifactStore(self.current_run, self.run_id).register_json(
                        artifact_type="model_result",
                        version=1,
                        content=model_result,
                        producer=stage_id,
                    )
                    artifact_registration_ok = True
                    self.manifest["artifact_registry"] = "active_artifacts.json"
                    self.manifest["artifacts"].append(
                        {
                            "artifact_id": artifact["meta"]["artifact_id"],
                            "artifact_type": artifact["meta"]["artifact_type"],
                            "version": artifact["meta"]["version"],
                            "path": artifact["store_path"],
                            "sha256": artifact["meta"]["content_sha256"],
                            "producer": artifact["meta"]["producer"],
                        }
                    )
                except Exception as exc:
                    artifact_registration_error = str(exc)
        checks = [
            gate_check("declared outputs absent before stage", True, actual=[], expected=[]),
            gate_check("stage exit code", returncode == 0, actual=returncode, expected=0),
            gate_check("all declared outputs exist", not missing, actual=missing, expected=[]),
            gate_check("outputs modified during current stage", not stale_times, actual=stale_times, expected=[]),
            gate_check(
                "outputs registered with SHA-256",
                len(output_records) == len(outputs) and all(record["sha256"] for record in output_records),
                actual=len(output_records),
                expected=len(outputs),
            ),
            gate_check(
                "trust-chain output has current-run identity and valid schema",
                trust_ok,
                actual=trust_error or "valid",
                expected="valid",
                message=trust_error,
            ),
        ]
        if stage_id == "model_compute":
            checks.append(
                gate_check(
                    "ModelResult registered as the active immutable artifact",
                    artifact_registration_ok,
                    actual=artifact_registration_error or "model_result@1",
                    expected="model_result@1",
                    message=artifact_registration_error,
                )
            )
        freshness = self._write_freshness_gate(stage_id, checks)
        passed = freshness["status"] == "PASS"
        self.manifest["stages"].append(
            {
                "stage": stage_id,
                "start_time": iso_time(started),
                "end_time": iso_time(ended),
                "inputs_hash": inputs_hash,
                "inputs": [path.relative_to(self.current_run).as_posix() for path in input_paths],
                "outputs": output_records,
                "command": command,
                "returncode": returncode,
                "logs": {
                    "stdout": stdout_path.relative_to(self.current_run).as_posix(),
                    "stderr": stderr_path.relative_to(self.current_run).as_posix(),
                },
                "status": "PASS" if passed else "FAIL",
                "errors": [check["message"] for check in checks if check["status"] == "FAIL"],
                "freshness_gate": freshness["status"],
            }
        )
        self._write_manifest()
        return passed

    def _finish(self, status: str) -> dict[str, Any]:
        published = self.current_run / "artifacts" / "published"
        if status == "FAIL" and published.exists():
            quarantine = self.current_run / "artifacts" / "quarantined-published"
            published.rename(quarantine)
            self.manifest["quarantined_publish"] = quarantine.relative_to(self.current_run).as_posix()
        self.manifest["status"] = status
        self.manifest["end_time"] = iso_time()
        self.manifest["gate_reports"] = [
            {
                "path": path.relative_to(self.current_run).as_posix(),
                "sha256": sha256_file(path),
                "created_at": datetime.fromtimestamp(path.stat().st_ctime, timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            for path in sorted((self.current_run / "gates").glob("*.json"))
        ]
        self._write_manifest()
        final_dir = self.runtime_root / self.run_id
        if final_dir.exists():
            raise FileExistsError(f"Run archive already exists: {final_dir}")
        try:
            self.current_run.rename(final_dir)
            latest = {
                "run_id": self.run_id,
                "status": status,
                "run_dir": str(final_dir),
                "manifest": str(final_dir / "manifest.json"),
            }
            (self.runtime_root / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
            result = {"run_id": self.run_id, "status": status, "run_dir": final_dir, "manifest": final_dir / "manifest.json"}
            if status == "PASS":
                from core.runtime.release_controller import stage_candidate
                result["release"] = stage_candidate(final_dir)
            return result
        finally:
            self._release_lock()

    def run_prepared(self) -> dict[str, Any]:
        if not self._prepared or not self.current_run.is_dir():
            raise RuntimeError("prepare() must succeed before run_prepared()")
        if not self._check_code_integrity() or not self._check_run_integrity():
            return self._finish("FAIL")
        for stage in self.config["stages"]:
            if not self._check_code_integrity() or not self._check_run_integrity():
                return self._finish("FAIL")
            stage_passed = self._run_stage(stage)
            integrity_passed = self._check_run_integrity()
            code_integrity_passed = self._check_code_integrity()
            if not stage_passed or not integrity_passed or not code_integrity_passed:
                return self._finish("FAIL")
        return self._finish("PASS")

    def run(self) -> dict[str, Any]:
        try:
            self.prepare()
            return self.run_prepared()
        finally:
            self._release_lock()


def main() -> int:
    print(
        "ERROR: production_workflow.py is a library, not a production entry point. "
        "Use workflow_executor.py --config workflow.json.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
