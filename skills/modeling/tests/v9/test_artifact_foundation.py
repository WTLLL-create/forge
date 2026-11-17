from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))


class ArtifactFoundationTests(unittest.TestCase):
    def _store(self, run_dir: Path, run_id: str = "run-a"):
        from core.runtime.artifact_store import ArtifactStore

        return ArtifactStore(run_dir, run_id)

    def test_registers_first_artifact_and_makes_it_active(self) -> None:
        """Break caught: a stored artifact has no immutable identity or active pointer."""
        try:
            from core.runtime.artifact_store import ArtifactStore
        except ImportError as exc:
            self.fail(f"Artifact Foundation is missing: {exc}")

        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            store = ArtifactStore(run_dir, "run-a")
            record = store.register_json(
                artifact_type="sample",
                version=1,
                content={"value": 7},
                producer="test",
            )

            self.assertEqual("sample@1", record["meta"]["artifact_id"])
            stored_path = run_dir / record["store_path"]
            self.assertTrue(stored_path.is_file())
            registry = json.loads((run_dir / "active_artifacts.json").read_text(encoding="utf-8"))
            self.assertEqual("run-a", registry["run_id"])
            self.assertEqual("sample@1", registry["artifacts"]["sample"]["artifact_id"])

    def test_same_id_and_content_is_idempotent(self) -> None:
        """Break caught: retrying a successful registration creates or corrupts a version."""
        with tempfile.TemporaryDirectory() as raw:
            store = self._store(Path(raw))
            first = store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="test")
            second = store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="retry")
            self.assertEqual(first, second)
            self.assertEqual(1, len(list((Path(raw) / "artifacts" / ".store" / "sample").glob("*.json"))))

    def test_same_id_with_different_content_is_rejected(self) -> None:
        """Break caught: an immutable artifact id is overwritten with different content."""
        from core.schema.artifact_meta import ArtifactConflictError

        with tempfile.TemporaryDirectory() as raw:
            store = self._store(Path(raw))
            store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="test")
            with self.assertRaises(ArtifactConflictError):
                store.register_json(artifact_type="sample", version=1, content={"value": 8}, producer="test")

    def test_superseding_version_becomes_active_and_preserves_old_file(self) -> None:
        """Break caught: activating a repair deletes history or leaves the old version active."""
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            store = self._store(run_dir)
            first = store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="test")
            second = store.register_json(
                artifact_type="sample",
                version=2,
                content={"value": 8},
                producer="repair",
                supersedes=["sample@1"],
            )
            registry = json.loads((run_dir / "active_artifacts.json").read_text(encoding="utf-8"))
            self.assertEqual("sample@2", registry["artifacts"]["sample"]["artifact_id"])
            self.assertEqual(["sample@1"], second["meta"]["supersedes"])
            self.assertTrue((run_dir / first["store_path"]).is_file())
            self.assertTrue((run_dir / second["store_path"]).is_file())

    def test_old_version_cannot_be_reactivated(self) -> None:
        """Break caught: a superseded artifact silently returns to the active chain."""
        from core.schema.artifact_meta import ArtifactVersionError

        with tempfile.TemporaryDirectory() as raw:
            store = self._store(Path(raw))
            store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="test")
            store.register_json(
                artifact_type="sample", version=2, content={"value": 8}, producer="repair", supersedes=["sample@1"]
            )
            with self.assertRaises(ArtifactVersionError):
                store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="retry")

    def test_new_version_must_explicitly_supersede_active_version(self) -> None:
        """Break caught: lineage advances without identifying the version it replaces."""
        from core.schema.artifact_meta import ArtifactVersionError

        with tempfile.TemporaryDirectory() as raw:
            store = self._store(Path(raw))
            store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="test")
            with self.assertRaises(ArtifactVersionError):
                store.register_json(artifact_type="sample", version=2, content={"value": 8}, producer="repair")

    def test_cross_run_artifact_cannot_be_activated(self) -> None:
        """Break caught: Run A metadata is accepted by Run B's active registry."""
        from core.runtime.active_registry import ActiveArtifactRegistry
        from core.schema.artifact_meta import ArtifactRunMismatchError

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            record = self._store(root / "run-a", "run-a").register_json(
                artifact_type="sample", version=1, content={"value": 7}, producer="test"
            )
            registry_b = ActiveArtifactRegistry(root / "run-b", "run-b")
            with self.assertRaises(ArtifactRunMismatchError):
                registry_b.activate(record["meta"], record["store_path"])

    def test_input_hash_mismatch_is_rejected(self) -> None:
        """Break caught: a child artifact lies about the exact upstream content it consumed."""
        from core.schema.artifact_meta import ArtifactDependencyError

        with tempfile.TemporaryDirectory() as raw:
            store = self._store(Path(raw))
            parent = store.register_json(artifact_type="parent", version=1, content={"value": 7}, producer="test")
            with self.assertRaises(ArtifactDependencyError):
                store.register_json(
                    artifact_type="child",
                    version=1,
                    content={"derived": 14},
                    producer="test",
                    input_refs=["parent@1"],
                    input_hashes={"parent@1": "0" * 64},
                )
            self.assertNotEqual("0" * 64, parent["meta"]["content_sha256"])

    def test_missing_input_reference_is_rejected(self) -> None:
        """Break caught: an artifact depends on an upstream id that was never stored."""
        from core.schema.artifact_meta import ArtifactDependencyError

        with tempfile.TemporaryDirectory() as raw:
            store = self._store(Path(raw))
            with self.assertRaises(ArtifactDependencyError):
                store.register_json(
                    artifact_type="child",
                    version=1,
                    content={"derived": 14},
                    producer="test",
                    input_refs=["parent@1"],
                    input_hashes={"parent@1": "0" * 64},
                )

    def test_unstored_artifact_cannot_be_activated(self) -> None:
        """Break caught: registry points at metadata that Artifact Store never committed."""
        from core.runtime.active_registry import ActiveArtifactRegistry
        from core.schema.artifact_meta import ArtifactIntegrityError, build_artifact_meta

        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            registry = ActiveArtifactRegistry(run_dir, "run-a")
            meta = build_artifact_meta(
                artifact_type="sample", run_id="run-a", version=1, producer="test", content={"value": 7}
            )
            with self.assertRaises(ArtifactIntegrityError):
                registry.activate(meta, "artifacts/.store/sample/000001.json")

    def test_tampered_active_artifact_fails_integrity_check(self) -> None:
        """Break caught: the registry trusts recorded hashes without reading stored content."""
        from core.schema.artifact_meta import ArtifactIntegrityError

        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            store = self._store(run_dir)
            record = store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="test")
            stored_path = run_dir / record["store_path"]
            envelope = json.loads(stored_path.read_text(encoding="utf-8"))
            envelope["content"]["value"] = 999
            stored_path.write_text(json.dumps(envelope), encoding="utf-8")
            self.assertTrue(hasattr(store.registry, "verify_integrity"), "Registry has no integrity verifier")
            with self.assertRaises(ArtifactIntegrityError):
                store.registry.verify_integrity()

    def test_tampered_artifact_metadata_fails_integrity_check(self) -> None:
        """Break caught: provenance metadata changes while content hash remains valid."""
        from core.schema.artifact_meta import ArtifactIntegrityError

        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            store = self._store(run_dir)
            record = store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="test")
            stored_path = run_dir / record["store_path"]
            envelope = json.loads(stored_path.read_text(encoding="utf-8"))
            envelope["meta"]["producer"] = "rewritten-provenance"
            stored_path.write_text(json.dumps(envelope), encoding="utf-8")
            with self.assertRaises(ArtifactIntegrityError):
                store.registry.verify_integrity()

    def test_canonical_hash_is_stable_for_same_content(self) -> None:
        """Break caught: semantically identical JSON gets different hashes from key ordering."""
        from core.schema.artifact_meta import content_sha256

        self.assertEqual(content_sha256({"b": 2, "a": 1}), content_sha256({"a": 1, "b": 2}))

    def test_idempotent_retry_cannot_launder_tampered_metadata(self) -> None:
        """Break caught: retry replaces the trusted metadata hash with a tampered one."""
        from core.schema.artifact_meta import ArtifactIntegrityError

        with tempfile.TemporaryDirectory() as raw:
            store = self._store(Path(raw))
            record = store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="test")
            path = Path(raw) / record["store_path"]
            record["meta"]["producer"] = "forged"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(ArtifactIntegrityError):
                store.register_json(artifact_type="sample", version=1, content={"value": 7}, producer="retry")
            with self.assertRaises(ArtifactIntegrityError):
                store.registry.verify_integrity()

    def test_registry_pointer_edit_and_rollback_are_detected(self) -> None:
        """Break caught: valid old pointers or removed pointers hide registered versions."""
        from core.schema.artifact_meta import ArtifactIntegrityError

        for modification in ("clear", "rollback", "delete"):
            with self.subTest(modification=modification), tempfile.TemporaryDirectory() as raw:
                store = self._store(Path(raw))
                store.register_json(artifact_type="sample", version=1, content=1, producer="test")
                old = store.registry.path.read_text(encoding="utf-8")
                store.register_json(artifact_type="sample", version=2, content=2, producer="test", supersedes=["sample@1"])
                if modification == "delete":
                    store.registry.path.unlink()
                elif modification == "rollback":
                    store.registry.path.write_text(old, encoding="utf-8")
                else:
                    registry = json.loads(old)
                    registry["artifacts"] = {}
                    store.registry.path.write_text(json.dumps(registry), encoding="utf-8")
                with self.assertRaises(ArtifactIntegrityError):
                    self._store(Path(raw)).registry.verify_integrity()

    def test_concurrent_registry_writer_is_rejected_without_changes(self) -> None:
        """Break caught: two independent writers can race read/validate/replace."""
        from core.schema.artifact_meta import ArtifactConflictError

        with tempfile.TemporaryDirectory() as raw:
            first = self._store(Path(raw))
            second = self._store(Path(raw))
            first.register_json(artifact_type="sample", version=1, content=1, producer="test")
            self.assertTrue(hasattr(first.registry, "locked"), "No registry transaction lock")
            before = first.registry.path.read_bytes()
            with first.registry.locked():
                with self.assertRaises(ArtifactConflictError):
                    second.register_json(artifact_type="sample", version=2, content=2, producer="test", supersedes=["sample@1"])
            self.assertEqual(before, first.registry.path.read_bytes())
            self.assertFalse((Path(raw) / "artifacts/.store/sample/000002.json").exists())

    def test_interrupted_registry_commit_fails_closed(self) -> None:
        """Break caught: a partially committed pointer is silently accepted or repaired."""
        from unittest.mock import patch
        from core.runtime.active_registry import _atomic_write_json
        from core.schema.artifact_meta import ArtifactIntegrityError

        with tempfile.TemporaryDirectory() as raw:
            store = self._store(Path(raw))
            store.register_json(artifact_type="sample", version=1, content=1, producer="test")

            def interrupted_write(path, value):
                if path == store.registry.path:
                    raise OSError("injected pointer write failure")
                return _atomic_write_json(path, value)

            with patch("core.runtime.active_registry._atomic_write_json", side_effect=interrupted_write):
                with self.assertRaises(OSError):
                    store.register_json(artifact_type="sample", version=2, content=2, producer="test", supersedes=["sample@1"])
            with self.assertRaises(ArtifactIntegrityError):
                store.registry.verify_integrity()

    def test_canonical_hash_changes_with_content(self) -> None:
        """Break caught: a content change leaves the artifact hash unchanged."""
        from core.schema.artifact_meta import content_sha256

        self.assertNotEqual(content_sha256({"value": 7}), content_sha256({"value": 8}))

    def test_reference_workflow_registers_model_result_as_first_active_artifact(self) -> None:
        """Break caught: the existing ModelResult flow bypasses the new artifact foundation."""
        from core.runtime.production_workflow import ProductionWorkflow
        from core.schema.artifact_meta import content_sha256

        project = MODELING_ROOT.parents[1] / "projects" / "forge_v7_3_d2026"
        # Isolated runtime root keeps parallel v8/v9 suites from racing on the
        # reference project's own runtime/runs directory.
        with tempfile.TemporaryDirectory() as raw:
            outcome = ProductionWorkflow(project / "workflow.json", python_executable=sys.executable,
                                         runtime_root=Path(raw)).run()
            self.assertEqual("PASS", outcome["status"])
            run_dir = Path(outcome["run_dir"])
            self.assertTrue((run_dir / "active_artifacts.json").is_file())
            registry = json.loads((run_dir / "active_artifacts.json").read_text(encoding="utf-8"))
            pointer = registry["artifacts"]["model_result"]
            self.assertEqual("model_result@1", pointer["artifact_id"])
            stored = json.loads((run_dir / pointer["path"]).read_text(encoding="utf-8"))
            legacy_model_result = json.loads((run_dir / "artifacts" / "model_result.json").read_text(encoding="utf-8"))
            self.assertEqual(legacy_model_result, stored["content"])
            self.assertEqual(content_sha256(legacy_model_result), pointer["sha256"])
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("active_artifacts.json", manifest["artifact_registry"])
            self.assertEqual("model_result@1", manifest["artifacts"][0]["artifact_id"])


if __name__ == "__main__":
    unittest.main()
