"""
Boundary Benchmark Runner — Skill Invocation Test Suite
=========================================================
Wave 1 Step 1.5: 对 4 个 A 类技能运行 120 条 Boundary Test。
指标: Mandatory Recall / False Invocation Rate / Ambiguous Accuracy
"""
import json
import os
import sys

# 确保可以导入 invocation_gate
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from invocation_gate import InvocationGate, run_boundary_test


def load_cases(filename):
    path = os.path.join(os.path.dirname(__file__), "skill_boundary", filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("=" * 68)
    print("  Forge v6.5 Skill Boundary Benchmark — Invocation Gate")
    print("=" * 68)
    print()

    gate = InvocationGate()

    results = {}

    # ===== Mandatory Recall Test =====
    print("--- Mandatory Recall (must-call, target: >= 90%) ---")
    mandatory_cases = load_cases("mandatory/cases.json")
    mr_result = run_boundary_test(gate, mandatory_cases)
    results["mandatory"] = mr_result
    print(f"  Total: {mr_result['total']}, Correct: {mr_result['correct']}, Accuracy: {mr_result['accuracy']:.1%}")

    for sid, stats in sorted(mr_result["by_skill"].items()):
        acc = stats["correct"] / max(stats["total"], 1)
        flag = " PASS" if acc >= 0.90 else " FAIL"
        print(f"    {sid}: {stats['correct']}/{stats['total']} ({acc:.0%}){flag}")

    if mr_result["failures"]:
        print(f"  Failures ({len(mr_result['failures'])}):")
        for f in mr_result["failures"]:
            print(f"    [{f['skill_id']}] query='{f['query'][:60]}' expected={f['expected']} actual={f['actual']} conf={f.get('confidence', 'N/A')}")
    print()

    # ===== False Invocation Rate Test =====
    print("--- False Invocation Rate (must-not-call, target: <= 5%) ---")
    forbidden_cases = load_cases("forbidden/cases.json")
    fir_result = run_boundary_test(gate, forbidden_cases)
    results["forbidden"] = fir_result
    false_positives = fir_result["total"] - fir_result["correct"]
    fir = false_positives / max(fir_result["total"], 1)

    print(f"  Total: {fir_result['total']}, Correct: {fir_result['correct']}, False Invocations: {false_positives}")
    print(f"  False Invocation Rate: {fir:.1%}")

    flag = " PASS" if fir <= 0.05 else " FAIL"
    print(f"  Target <= 5%: {flag}")

    if fir_result["failures"]:
        print(f"  False Positives ({len(fir_result['failures'])}):")
        for f in fir_result["failures"]:
            print(f"    query='{f['query'][:60]}' expected={f['expected']} actual={f['actual']} conf={f.get('confidence', 'N/A')}")
    print()

    # ===== Ambiguous Test =====
    print("--- Ambiguous Accuracy ---")
    ambiguous_cases = load_cases("ambiguous/cases.json")
    amb_result = run_boundary_test(gate, ambiguous_cases)
    results["ambiguous"] = amb_result
    print(f"  Total: {amb_result['total']}, Correct: {amb_result['correct']}, Accuracy: {amb_result['accuracy']:.1%}")

    if amb_result["failures"]:
        print(f"  Failures ({len(amb_result['failures'])}):")
        for f in amb_result["failures"]:
            print(f"    query='{f['query'][:60]}' expected={f['expected']} actual={f['actual']} conf={f.get('confidence', 'N/A')}")
    print()

    # ===== Summary =====
    print("=" * 68)
    print("  SUMMARY")
    print("=" * 68)
    total_cases = sum(r["total"] for r in results.values())
    total_correct = sum(r["correct"] for r in results.values())
    overall_accuracy = total_correct / max(total_cases, 1)

    print(f"  Total Cases: {total_cases}")
    print(f"  Total Correct: {total_correct}")
    print(f"  Overall Accuracy: {overall_accuracy:.1%}")
    print(f"  Mandatory Recall: {results['mandatory']['accuracy']:.1%}")
    print(f"  False Invocation Rate: {fir:.1%}")
    print(f"  Ambiguous Accuracy: {results['ambiguous']['accuracy']:.1%}")

    # Gate Ready?
    gate_ready = (
        results["mandatory"]["accuracy"] >= 0.90
        and fir <= 0.05
    )
    print(f"\n  Gate Ready: {'YES' if gate_ready else 'NO'} (need Mandatory Recall >= 90% + FIR <= 5%)")

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), "skill_boundary", "benchmark_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "gate_version": "v1.0",
            "skills_tested": list(gate.skills.keys()),
            "total_cases": total_cases,
            "total_correct": total_correct,
            "overall_accuracy": overall_accuracy,
            "mandatory_recall": results["mandatory"]["accuracy"],
            "false_invocation_rate": fir,
            "ambiguous_accuracy": results["ambiguous"]["accuracy"],
            "gate_ready": gate_ready,
            "failures": {
                "mandatory": results["mandatory"]["failures"],
                "forbidden": results["forbidden"]["failures"],
                "ambiguous": results["ambiguous"]["failures"],
            }
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to: {out_path}")

    return 0 if gate_ready else 1


if __name__ == "__main__":
    sys.exit(main())
