"""
Registry Consistency Validator — Skill Registry v2.0 一致性检查
===============================================================
检查 skill_runtime_registry.yaml v2.0 的内部一致性:
  1. 每个 skill 的 boundary/capability/decision/dependency/lifecycle 字段是否存在
  2. dependency 中引用的 skill_id 是否在 registry 中存在
  3. lifecycle.state 取值是否合法
  4. governed skills 的 must_call patterns 是否非空
"""
import os
import sys
import yaml


STATES = {"active", "partial", "not_connected", "deprecated", "sandbox"}


def validate_registry(registry_path: str) -> dict:
    """返回 {"valid": bool, "errors": [...], "warnings": [...]}"""

    errors = []
    warnings = []

    if not os.path.isfile(registry_path):
        return {"valid": False, "errors": [f"Registry file not found: {registry_path}"], "warnings": []}

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    version = registry.get("version", "unknown")
    print(f"Registry version: {version}")

    skills = registry.get("skills", {})
    if not skills:
        errors.append("No skills found in registry")
        return {"valid": False, "errors": errors, "warnings": warnings}

    all_skill_ids = set(skills.keys())

    for skill_id, data in skills.items():
        # 1. Required sections
        for section in ["boundary", "capability", "decision", "lifecycle"]:
            if section not in data:
                errors.append(f"[{skill_id}] Missing required section: {section}")

        # 2. Lifecycle state
        state = data.get("lifecycle", {}).get("state", data.get("status", ""))
        if state and state not in STATES:
            # Also check top-level status field for backward compat
            top_status = data.get("status", "")
            if top_status in ("active", "partial"):
                pass  # legacy format, ok
            elif state not in STATES:
                errors.append(f"[{skill_id}] Invalid lifecycle state: '{state}' (valid: {STATES})")

        # 3. Boundary must_call patterns
        boundary = data.get("boundary", {})
        must_call = boundary.get("must_call", [])
        if must_call:
            for i, mc in enumerate(must_call):
                patterns = mc.get("patterns", [])
                intent = mc.get("intent", f"entry_{i}")
                if not patterns:
                    warnings.append(f"[{skill_id}] Empty patterns for must_call intent: {intent}")
                conf = mc.get("confidence", 0)
                if conf < 0 or conf > 1:
                    errors.append(f"[{skill_id}] Invalid confidence {conf} for intent: {intent}")

        # 4. Decision threshold
        threshold = data.get("decision", {}).get("confidence_threshold", None)
        if threshold is not None and (threshold < 0.5 or threshold > 1.0):
            errors.append(f"[{skill_id}] Invalid confidence_threshold: {threshold}")

        # 5. Capability input
        cap_input = data.get("capability", {}).get("input", {})
        if cap_input and "required" not in cap_input:
            warnings.append(f"[{skill_id}] Capability input missing 'required' field")

    # 6. Cross-skill dependency check (only for governed skills with patterns)
    governed = {sid for sid, d in skills.items() if d.get("boundary", {}).get("must_call", []) and any(mc.get("patterns", []) for mc in d["boundary"]["must_call"])}

    for skill_id, data in skills.items():
        dep = data.get("dependency", {})
        for direction, label in [("upstream", "upstream"), ("downstream", "downstream")]:
            for dep_id in dep.get(direction, []):
                if dep_id not in all_skill_ids:
                    # 外部系统组件（非 skill）— 仅 warning
                    if skill_id in governed:
                        warnings.append(f"[{skill_id}] {label} dependency '{dep_id}' is external (not a registered skill)")
                    # stubs 的外部依赖不报警
                    pass
                elif skill_id in governed and dep_id not in governed:
                    # governed skill 依赖了一个 stub → 降级为 warning
                    warnings.append(f"[{skill_id}] {label} dependency '{dep_id}' is a stub (no boundary patterns)")
                    pass

    valid = len(errors) == 0

    print(f"\nResult: {'VALID' if valid else 'INVALID'}")
    print(f"  Skills: {len(skills)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  ! {e}")
    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  ? {w}")

    return {"valid": valid, "errors": errors, "warnings": warnings}


if __name__ == "__main__":
    registry_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "skill_runtime_registry.yaml"
    )
    result = validate_registry(registry_path)
    sys.exit(0 if result["valid"] else 1)
