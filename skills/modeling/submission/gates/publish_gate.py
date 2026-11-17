"""Publish only when every required Forge gate has genuinely passed."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

MODELING_ROOT = Path(__file__).resolve().parents[2]
if str(MODELING_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELING_ROOT))

from core.schema.gate_result import gate_check, gate_result, validate_gate_result, write_gate_result


REQUIRED_GATES = {"scientific_gate", "template_compliance_gate", "artifact_integrity_gate"}
# Gates added after the original three (AI compliance, number freeze, human
# judgment, AIGC audit). They are enforced only when a workflow declares them
# via --required-gate, keeping existing workflow.json configs backward compatible.
EXTENDED_GATES = {
    "ai_compliance_gate",
    "number_freeze_gate",
    "human_judgment_gate",
    "aigc_audit_gate",
    "writing_quality_gate",
    "review_audit_gate",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_publish_gate(
    run_id: str,
    gate_paths: list[Path],
    source: Path,
    output: Path,
    required: set[str] | None = None,
) -> dict:
    required_gates = REQUIRED_GATES | set(required or ())
    loaded = []
    load_errors = []
    for path in gate_paths:
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            validate_gate_result(item)
            loaded.append(item)
        except Exception as exc:
            load_errors.append(f"{path}: {exc}")
    names = {item.get("gate") for item in loaded}
    source_hash = sha256_file(source) if source.is_file() else None
    attestations = {
        item.get("gate"): item.get("artifacts", {}).get("docx_sha256")
        for item in loaded
        if item.get("gate") in required_gates
    }
    # Only gates that actually attest the document (scientific/template/
    # artifact-integrity/ai-compliance) must match the source hash. Gates that
    # attest other products (numbers, judgments, markdown) are enforced by
    # "all required gates present" + "all gates pass" + "belong to current run".
    docx_attesting = {name: digest for name, digest in attestations.items() if digest}
    checks = [
        gate_check("gate names are unique", len(names) == len(loaded)),
        gate_check("mandatory document attestations present", all(
            isinstance(attestations.get(name), str) and len(attestations[name]) == 64
            for name in required_gates & (REQUIRED_GATES | {"ai_compliance_gate"}))),
        gate_check("gate reports readable", not load_errors, actual=load_errors, expected=[]),
        gate_check("all required gates present", required_gates <= names, actual=sorted(names), expected=sorted(required_gates)),
        gate_check("all gates pass", all(item.get("status") == "PASS" for item in loaded), actual={item.get("gate"): item.get("status") for item in loaded}, expected="all PASS"),
        gate_check("all gates belong to current run", all(item.get("run_id") == run_id for item in loaded), actual={item.get("gate"): item.get("run_id") for item in loaded}, expected=run_id),
        gate_check("source document exists", source.is_file(), actual=str(source), expected="existing DOCX"),
        gate_check(
            "source document matches every gate attestation",
            source_hash is not None
            and bool(docx_attesting)
            and all(digest == source_hash for digest in docx_attesting.values()),
            actual=attestations,
            expected={name: source_hash for name in sorted(docx_attesting)},
            message="The document changed after validation or a document-attesting gate omitted its hash.",
        ),
    ]
    result = gate_result("publish_gate", checks, run_id=run_id)
    result["scope"] = "Validated internal candidate copy; not human approval or official submission."
    result["official_submission"] = "NOT_PERFORMED"
    if result["status"] == "PASS":
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
        result["published"] = {"path": str(output), "sha256": sha256_file(output), "source_sha256": source_hash}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--gate", action="append", required=True)
    parser.add_argument("--required-gate", action="append", default=None,
                        help="Additional required gate name (repeatable); defaults to the original three")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    required = REQUIRED_GATES | set(args.required_gate) if args.required_gate else None
    result = run_publish_gate(args.run_id, [Path(path) for path in args.gate], Path(args.source), Path(args.output), required=required)
    write_gate_result(args.report, result)
    print(json.dumps({"gate": result["gate"], "status": result["status"], "report": str(Path(args.report).resolve())}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
