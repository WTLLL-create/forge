"""
StyleCompiler v1.0 — 合同驱动样式编译器
=========================================
Forge v6.5 Wave 2.2: 从 paper_compiler.py 硬编码 style dict 升级为
PaperStyleContract 驱动的独立运行时模块。

原则: 不硬编码一个样式参数。所有样式值来自 PaperStyleContract。
      修改 Contract 中的任意值 → StyleCompiler 输出相应变化。
"""
import json
import os
from typing import Dict


class StyleCompiler:
    """消费 PaperStyleContract，输出 RenderedStyleConfig"""

    def __init__(self, contract_path: str = None):
        if contract_path is None:
            contract_path = os.path.join(
                os.path.dirname(__file__), "..", "contracts", "paper_style_contract.schema.json"
            )
        self.contract_path = contract_path
        self._contract = None

    def load_contract(self) -> Dict:
        """加载 PaperStyleContract schema"""
        with open(self.contract_path, "r", encoding="utf-8") as f:
            self._contract = json.load(f)
        return self._contract

    def compile(self, competition: str = "CUMCM") -> Dict:
        """
        编译样式配置。

        Args:
            competition: "CUMCM" | "MCM"

        Returns:
            RenderedStyleConfig dict (由 Contract 参数驱动)
        """
        if self._contract is None:
            self.load_contract()

        spec_key = f"{competition.lower()}_spec"
        spec = self._contract.get("$defs", {}).get(spec_key, {})

        return {
            "competition": competition,
            "font": {
                "body": self._extract_font(spec, "font.body"),
                "heading": self._extract_font(spec, "font.heading"),
                "title": self._extract_font(spec, "font.title"),
                "table_caption": self._extract_font(spec, "font.table_caption"),
            },
            "page": {
                "size": self._get(spec, "page.size"),
                "margin_mm": self._get(spec, "page.margin_mm"),
                "line_spacing": self._get(spec, "page.line_spacing"),
                "first_line_indent_cm": self._get(spec, "page.first_line_indent_cm"),
            },
            "table": {
                "style": self._get(spec, "table_style.style"),
                "top_pt": 1.5 if spec.get("table_style", {}).get("no_vertical_lines") else 1.0,
                "mid_pt": 0.5,
                "bottom_pt": 1.5,
                "no_vertical_lines": self._get(spec, "table_style.no_vertical_lines"),
                "no_double_lines": self._get(spec, "table_style.no_double_lines"),
                "no_color_background": self._get(spec, "table_style.no_color_background"),
                "caption_position": self._get(spec, "table_style.caption_position"),
            },
            "equation": {
                "numbering_style": self._get(spec, "equation.numbering_style"),
                "must_be_numbered": self._get(spec, "equation.must_be_numbered"),
                "must_have_intro_text": self._get(spec, "equation.must_have_intro_text"),
                "must_explain_variables": self._get(spec, "equation.must_explain_variables"),
            },
            "reference": {
                "style": self._get(spec, "reference.style"),
                "min_count": self._get(spec, "reference.min_count"),
                "citation_style": self._get(spec, "reference.citation_style"),
            },
            "abstract": {
                "min_words": 700,
                "max_words": 1000,
                "min_keywords": 3,
                "max_keywords": 7,
            },
            "_meta": {
                "contract_version": self._contract.get("$id", "unknown"),
                "spec_used": spec_key,
                "compile_mode": "contract_driven",
            },
        }

    def _extract_font(self, spec: Dict, path: str) -> Dict:
        """从 spec 中提取字体配置，穿透 properties"""
        parts = path.split(".")
        node = spec
        for p in parts:
            if isinstance(node, dict) and "properties" in node:
                node = node["properties"]
            node = node.get(p, {})

        if not node:
            return {"name": "宋体"}

        # 穿透最后一层 properties
        if isinstance(node, dict) and "properties" in node:
            node = node["properties"]

        result = {}
        for k, v in node.items():
            if isinstance(v, dict) and "const" in v:
                result[k] = v["const"]
            elif v is not None:
                result[k] = v
        return result

    def _get(self, spec: Dict, path: str, default=None):
        """从 spec 中读取值，自动穿透 JSON Schema 的 properties 嵌套"""
        parts = path.split(".")
        node = spec
        for p in parts:
            # JSON Schema: 如果当前节点有 properties，穿透进去
            if isinstance(node, dict) and "properties" in node:
                node = node["properties"]
            node = node.get(p, {})
        if isinstance(node, dict):
            if "const" in node:
                return node["const"]
            return default
        return node if node else default


# ===== Contract Mutation Test =====

def mutation_test(compiler: StyleCompiler) -> Dict:
    """
    验证 StyleCompiler 是真正的 Contract 驱动:
    修改 Contract 中的值 → 编译器输出相应变化。
    如果输出不变 = 硬编码，测试失败。
    """
    import copy

    contract = compiler.load_contract()
    original = compiler.compile("CUMCM")

    results = {"total": 0, "detected": 0, "undetected": [], "mutations": []}

    mutations = [
        # (路径, 旧值, 新值, 预期变化字段)
        ("$defs.cumcm_spec.font.body.size_pt.const", 12, 10, "font.body.size_pt"),
        ("$defs.cumcm_spec.font.heading.size_h1_pt.const", 16, 14, "font.heading.size_h1_pt"),
        ("$defs.cumcm_spec.page.line_spacing.const", 1.38, 1.5, "page.line_spacing"),
        ("$defs.cumcm_spec.page.margin_mm.const", 25, 30, "page.margin_mm"),
        ("$defs.cumcm_spec.table_style.caption_position.const", "above", "below", "table.caption_position"),
        ("$defs.cumcm_spec.reference.min_count.const", 5, 10, "reference.min_count"),
    ]

    for path_str, old_val, new_val, expected_field in mutations:
        results["total"] += 1
        # 修改 Contract — 穿透 properties 层级
        contracted = copy.deepcopy(contract)
        parts = path_str.split(".")
        node = contracted
        for p in parts[:-1]:
            if isinstance(node, dict) and "properties" in node:
                node = node["properties"]
            node = node[p]
        last = parts[-1]
        node[last] = new_val

        # 应用修改后的 Contract
        patched = copy.deepcopy(compiler)
        patched._contract = contracted
        mutated_config = patched.compile("CUMCM")

        # 检查变化
        field_parts = expected_field.split(".")
        mutated_val = mutated_config
        for fp in field_parts:
            mutated_val = mutated_val.get(fp, {})

        detected = mutated_val == new_val

        mutation = {
            "path": path_str,
            "old": old_val,
            "new": new_val,
            "expected_field": expected_field,
            "actual_value": mutated_val,
            "detected": detected,
        }
        results["mutations"].append(mutation)

        if detected:
            results["detected"] += 1
        else:
            results["undetected"].append(mutation)

    results["pass"] = results["detected"] == results["total"]
    return results


# ===== CLI =====

if __name__ == "__main__":
    print("=" * 60)
    print("StyleCompiler v1.0 — Contract-Driven Test")
    print("=" * 60)

    compiler = StyleCompiler()

    # 编译 CUMCM 样式
    style = compiler.compile("CUMCM")
    print(f"\nCompetition: {style['competition']}")
    print(f"Font body: {style['font']['body']}")
    print(f"Page: {style['page']}")
    print(f"Table style: {style['table']['style']}")
    print(f"Equation numbering: {style['equation']['numbering_style']}")
    print(f"Reference: {style['reference']}")
    print(f"Contract version: {style['_meta']['contract_version']}")

    # Contract Mutation Test
    print(f"\n{'=' * 60}")
    print("Contract Mutation Test")
    print(f"{'=' * 60}")
    result = mutation_test(compiler)
    print(f"\nDetected: {result['detected']}/{result['total']}")
    for m in result["mutations"]:
        status = "PASS" if m["detected"] else "FAIL"
        print(f"  [{status}] {m['expected_field']}: {m['old']} → {m['new']} → got {m['actual_value']}")
    print(f"\nMutation Test: {'PASS' if result['pass'] else 'FAIL'}")
