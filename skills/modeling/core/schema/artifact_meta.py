"""Artifact identity and deterministic content hashing for one Forge run."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


ARTIFACT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class ArtifactError(RuntimeError):
    """Base error for artifact identity, storage, and registry failures."""


class ArtifactConflictError(ArtifactError):
    """An existing artifact id was presented with different content."""


class ArtifactIntegrityError(ArtifactError):
    """Stored bytes or declared dependencies do not match recorded hashes."""


class ArtifactVersionError(ArtifactError):
    """An artifact version would move an active pointer backwards."""


class ArtifactRunMismatchError(ArtifactError):
    """An artifact and registry belong to different runs."""


class ArtifactDependencyError(ArtifactError):
    """An artifact dependency is missing or invalid."""


def canonical_content_bytes(content: Any) -> bytes:
    return json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def content_sha256(content: Any) -> str:
    return hashlib.sha256(canonical_content_bytes(content)).hexdigest()


def artifact_meta_sha256(meta: dict[str, Any]) -> str:
    """Hash immutable provenance separately from artifact content."""
    return hashlib.sha256(canonical_content_bytes(meta)).hexdigest()


def build_artifact_meta(
    *,
    artifact_type: str,
    run_id: str,
    version: int,
    producer: str,
    content: Any,
    input_refs: list[str] | None = None,
    input_hashes: dict[str, str] | None = None,
    supersedes: list[str] | None = None,
    status: str = "REGISTERED",
    warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not ARTIFACT_TYPE_PATTERN.fullmatch(artifact_type):
        raise ValueError(f"Unsafe artifact_type: {artifact_type}")
    if not run_id.strip() or not producer.strip():
        raise ValueError("run_id and producer must be non-empty")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("version must be a positive integer")
    refs = list(input_refs or [])
    hashes = dict(input_hashes or {})
    if len(refs) != len(set(refs)) or set(refs) != set(hashes):
        raise ValueError("input_refs and input_hashes must contain the same unique artifact ids")
    return {
        "schema_version": "forge-artifact-meta/v1",
        "artifact_id": f"{artifact_type}@{version}",
        "artifact_type": artifact_type,
        "run_id": run_id,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "producer": producer,
        "input_refs": refs,
        "input_hashes": hashes,
        "content_sha256": content_sha256(content),
        "status": status,
        "warnings": list(warnings or []),
        "supersedes": list(supersedes or []),
    }
