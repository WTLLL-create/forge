"""Atomic active-artifact pointers for a single isolated Forge run."""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from core.schema.artifact_meta import (
    ArtifactConflictError,
    ArtifactIntegrityError,
    ArtifactRunMismatchError,
    ArtifactVersionError,
    artifact_meta_sha256,
    content_sha256,
)


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


class ActiveArtifactRegistry:
    def __init__(self, run_dir: str | Path, run_id: str):
        self.run_dir = Path(run_dir).resolve()
        self.run_id = run_id
        self.path = self.run_dir / "active_artifacts.json"
        self.checkpoint = self.run_dir / "artifacts" / ".store" / "registry_integrity.json"
        self._mutex = RLock()
        self._lock_depth = 0
        with self.locked():
            if self.path.exists() or self.checkpoint.exists():
                self._load()
            else:
                self._commit({"schema": "forge-active-artifacts/v1", "run_id": run_id, "artifacts": {}})

    @contextmanager
    def locked(self):
        """Fail closed on concurrent writers; never remove another writer's lock."""
        with self._mutex:
            if self._lock_depth:
                self._lock_depth += 1
                try:
                    yield
                finally:
                    self._lock_depth -= 1
                return
            self.run_dir.mkdir(parents=True, exist_ok=True)
            lock_path = self.run_dir / ".artifact_registry.lock"
            try:
                handle = lock_path.open("x", encoding="utf-8")
            except FileExistsError as exc:
                raise ArtifactConflictError("Artifact registry is locked; no automatic stale-lock recovery") from exc
            self._lock_depth = 1
            try:
                with handle:
                    yield
            finally:
                self._lock_depth = 0
                lock_path.unlink()

    def _commit(self, registry: dict[str, Any]) -> None:
        # Two atomic files, not a crash-atomic transaction. An interrupted update
        # deliberately fails integrity rather than guessing which copy is valid.
        _atomic_write_json(self.checkpoint, {"run_id": self.run_id, "sha256": content_sha256(registry)})
        _atomic_write_json(self.path, registry)

    def _load(self) -> dict[str, Any]:
        try:
            registry = json.loads(self.path.read_text(encoding="utf-8"))
            checkpoint = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError("Registry or integrity checkpoint is missing/unreadable") from exc
        if registry.get("schema") != "forge-active-artifacts/v1" or registry.get("run_id") != self.run_id:
            raise ArtifactRunMismatchError("Registry identity does not match the current run")
        if not isinstance(registry.get("artifacts"), dict):
            raise ArtifactIntegrityError("Registry artifacts must be an object")
        if checkpoint.get("run_id") != self.run_id or checkpoint.get("sha256") != content_sha256(registry):
            raise ArtifactIntegrityError("Registry differs from its integrity checkpoint")
        return registry

    def _stored_envelope(self, store_path: str) -> dict[str, Any]:
        relative = Path(store_path)
        if relative.is_absolute() or ".." in relative.parts or tuple(relative.parts[:2]) != ("artifacts", ".store"):
            raise ArtifactIntegrityError(f"Unsafe artifact store path: {store_path}")
        target = (self.run_dir / relative).resolve()
        try:
            target.relative_to(self.run_dir)
        except ValueError as exc:
            raise ArtifactIntegrityError(f"Artifact path escapes current run: {store_path}") from exc
        if not target.is_file():
            raise ArtifactIntegrityError(f"Registered artifact file is missing: {store_path}")
        try:
            envelope = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError(f"Registered artifact cannot be read: {store_path}") from exc
        if envelope.get("schema") != "forge-artifact-envelope/v1" or not isinstance(envelope.get("meta"), dict):
            raise ArtifactIntegrityError(f"Invalid artifact envelope: {store_path}")
        meta = envelope["meta"]
        if meta.get("run_id") != self.run_id:
            raise ArtifactRunMismatchError("Stored artifact belongs to a different run")
        actual_hash = content_sha256(envelope.get("content"))
        if actual_hash != meta.get("content_sha256"):
            raise ArtifactIntegrityError(f"Stored artifact content hash changed: {store_path}")
        return envelope

    def validate_transition(self, meta: dict[str, Any]) -> None:
        if meta.get("run_id") != self.run_id:
            raise ArtifactRunMismatchError("Artifact belongs to a different run")
        current = self._load()["artifacts"].get(meta["artifact_type"])
        if not current:
            return
        if meta["version"] < current["version"]:
            raise ArtifactVersionError("Active artifact version cannot move backwards")
        if meta["version"] == current["version"]:
            if meta["artifact_id"] != current["artifact_id"] or meta["content_sha256"] != current["sha256"]:
                raise ArtifactVersionError("Active artifact version conflicts with the registered pointer")
            if artifact_meta_sha256(meta) != current.get("meta_sha256"):
                raise ArtifactIntegrityError("Existing artifact provenance cannot be replaced by a retry")
            return
        if current["artifact_id"] not in meta.get("supersedes", []):
            raise ArtifactVersionError(
                f"New artifact must supersede the active version: {current['artifact_id']}"
            )

    def activate(self, meta: dict[str, Any], store_path: str) -> None:
        with self.locked():
            self._activate_locked(meta, store_path)

    def _activate_locked(self, meta: dict[str, Any], store_path: str) -> None:
        self.verify_integrity()
        self.validate_transition(meta)
        envelope = self._stored_envelope(store_path)
        stored_meta = envelope["meta"]
        if (
            stored_meta.get("artifact_id") != meta.get("artifact_id")
            or stored_meta.get("content_sha256") != meta.get("content_sha256")
            or artifact_meta_sha256(stored_meta) != artifact_meta_sha256(meta)
        ):
            raise ArtifactIntegrityError("Registry metadata does not match the stored artifact")
        registry = self._load()
        artifact_type = meta["artifact_type"]
        registry["artifacts"][artifact_type] = {
            "artifact_id": meta["artifact_id"],
            "version": meta["version"],
            "sha256": meta["content_sha256"],
            "meta_sha256": artifact_meta_sha256(meta),
            "path": store_path,
        }
        self._commit(registry)

    def verify_integrity(self) -> bool:
        with self.locked():
            return self._verify_integrity_locked()

    def _verify_integrity_locked(self) -> bool:
        registry = self._load()
        for artifact_type, pointer in registry["artifacts"].items():
            envelope = self._stored_envelope(pointer.get("path", ""))
            meta = envelope["meta"]
            if (
                meta.get("artifact_type") != artifact_type
                or meta.get("artifact_id") != pointer.get("artifact_id")
                or meta.get("version") != pointer.get("version")
                or meta.get("content_sha256") != pointer.get("sha256")
                or artifact_meta_sha256(meta) != pointer.get("meta_sha256")
            ):
                raise ArtifactIntegrityError(f"Active pointer does not match stored artifact: {artifact_type}")
        return True
