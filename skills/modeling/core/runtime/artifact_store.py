"""Immutable JSON artifact storage layered onto an existing Forge run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.runtime.active_registry import ActiveArtifactRegistry, _atomic_write_json
from core.schema.artifact_meta import (
    ARTIFACT_TYPE_PATTERN,
    ArtifactConflictError,
    ArtifactDependencyError,
    ArtifactIntegrityError,
    ArtifactRunMismatchError,
    build_artifact_meta,
    content_sha256,
)


class ArtifactStore:
    def __init__(self, run_dir: str | Path, run_id: str):
        self.run_dir = Path(run_dir).resolve()
        self.run_id = run_id
        self.registry = ActiveArtifactRegistry(self.run_dir, run_id)

    def _path_for_id(self, artifact_id: str) -> Path:
        try:
            artifact_type, raw_version = artifact_id.rsplit("@", 1)
            version = int(raw_version)
        except (ValueError, AttributeError) as exc:
            raise ArtifactDependencyError(f"Invalid artifact reference: {artifact_id}") from exc
        if not ARTIFACT_TYPE_PATTERN.fullmatch(artifact_type) or version < 1:
            raise ArtifactDependencyError(f"Invalid artifact reference: {artifact_id}")
        return self.run_dir / "artifacts" / ".store" / artifact_type / f"{version:06d}.json"

    def _validate_dependencies(self, input_refs: list[str], input_hashes: dict[str, str]) -> None:
        for artifact_id in input_refs:
            target = self._path_for_id(artifact_id)
            if not target.is_file():
                raise ArtifactDependencyError(f"Input artifact is missing: {artifact_id}")
            try:
                envelope = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ArtifactDependencyError(f"Input artifact cannot be read: {artifact_id}") from exc
            meta = envelope.get("meta", {})
            if meta.get("run_id") != self.run_id:
                raise ArtifactRunMismatchError(f"Input artifact belongs to another run: {artifact_id}")
            actual_hash = content_sha256(envelope.get("content"))
            if actual_hash != meta.get("content_sha256") or actual_hash != input_hashes[artifact_id]:
                raise ArtifactDependencyError(f"Input artifact hash mismatch: {artifact_id}")

    def register_json(
        self,
        *,
        artifact_type: str,
        version: int,
        content: Any,
        producer: str,
        input_refs: list[str] | None = None,
        input_hashes: dict[str, str] | None = None,
        supersedes: list[str] | None = None,
    ) -> dict[str, Any]:
        with self.registry.locked():
            self.registry.verify_integrity()
            return self._register_json_locked(
                artifact_type=artifact_type, version=version, content=content, producer=producer,
                input_refs=input_refs, input_hashes=input_hashes, supersedes=supersedes,
            )

    def _register_json_locked(
        self,
        *,
        artifact_type: str,
        version: int,
        content: Any,
        producer: str,
        input_refs: list[str] | None = None,
        input_hashes: dict[str, str] | None = None,
        supersedes: list[str] | None = None,
    ) -> dict[str, Any]:
        refs = list(input_refs or [])
        hashes = dict(input_hashes or {})
        meta = build_artifact_meta(
            artifact_type=artifact_type,
            run_id=self.run_id,
            version=version,
            producer=producer,
            content=content,
            input_refs=refs,
            input_hashes=hashes,
            supersedes=supersedes,
        )
        self._validate_dependencies(refs, hashes)
        relative = Path("artifacts") / ".store" / artifact_type / f"{version:06d}.json"
        target = self.run_dir / relative
        envelope = {
            "schema": "forge-artifact-envelope/v1",
            "meta": meta,
            "content": content,
            "store_path": relative.as_posix(),
        }
        if target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
            actual_existing_hash = content_sha256(existing.get("content"))
            if actual_existing_hash != existing.get("meta", {}).get("content_sha256"):
                raise ArtifactIntegrityError(f"Stored artifact was modified: {meta['artifact_id']}")
            if actual_existing_hash != meta["content_sha256"]:
                raise ArtifactConflictError(f"Artifact id already has different content: {meta['artifact_id']}")
            envelope = existing
        else:
            self.registry.validate_transition(meta)
            _atomic_write_json(target, envelope)
        self.registry.activate(envelope["meta"], envelope["store_path"])
        return envelope
