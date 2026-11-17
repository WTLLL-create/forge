"""
Invocation Gate v1.0 — Runtime Governance Layer
=================================================
Forge v6.5 Skill Governance 核心组件。
在 forge_runner.py L0 之前拦截用户查询，判断是否允许 LLM 绕过 Skill 直接回答。

三层匹配流水线:
  1. Intent Semantic Filter  — 基于 must_call.intent 语义标签缩小候选范围
  2. Boundary Pattern Matcher — 基于 must_call.patterns 做正则/关键词匹配
  3. Confidence Scorer        — 加权评分 (semantic*0.6 + pattern*0.3 + lifecycle*0.1)

规则:
  - confidence >= skill.confidence_threshold → mandatory_call (禁止直接回答)
  - confidence in (0.50, threshold)           → suggest (建议调用但不强制)
  - confidence < 0.50                          → allow_answer (自由回答)
  - dependency.upstream 非 active              → 降级为 suggest
  - lifecycle.state = sandbox/deprecated       → 禁止生产调用

用法:
  gate = InvocationGate()
  decision = gate.evaluate("为什么选择随机森林而不是BP？")
  if decision["decision"] == "mandatory_call":
      # 路由到 forge_runner, 禁止 LLM 自由回答
"""

import os
import re
import json
import yaml
from datetime import datetime, timezone
from typing import Optional


# ===== 意图语义映射 =====
# v1.0 使用关键词映射模拟语义匹配。
# 未来可替换为 embedding-based 语义相似度。

INTENT_KEYWORDS = {
    "model_selection_justification": [
        "为什么选择", "为什么不选", "模型选择", "方案对比",
        "论证", "理由", "依据", "优劣比较", "排除",
        "不用", "不采用", "替代方案", "比较", "对比",
        "选哪个", "哪个更好", "哪个更合适", "适用性",
        "不选", "淘汰", "排除"
    ],
    "paper_argument_generation": [
        "生成论据", "论证段落", "论文论证", "模型论证",
        "方法论证", "写论证", "论据编写", "有深度"
    ],
    "alternative_elimination": [
        "为什么不用", "为什么不选", "排除原因",
        "淘汰", "候选方案", "不适用", "排除", "替代"
    ],
    "model_formalization": [
        "数学模型", "数学框架", "形式化", "规格化",
        "符号说明", "符号表", "公式化", "数学表达",
        "假设条件", "模型假设", "变量定义", "形式化描述",
        "数学形式", "数学描述", "数学语言", "数学建模框架",
        "微分方程", "评价指标", "模型建立", "模型框架",
        "数学形式化", "形式化方法", "规格化描述"
    ],
    "model_documentation": [
        "生成符号表", "公式段", "符号说明章节",
        "模型章节", "公式编号"
    ],
    "paper_quality_check": [
        "检查论文", "审查质量", "格式规范",
        "质量门禁", "论文规范", "合规检查"
    ],
    "paper_compliance_verification": [
        "CUMCM格式", "国赛规范", "MCM格式",
        "美赛要求", "竞赛格式", "比赛规范"
    ],
    "pre_submission_review": [
        "提交前检查", "最终检查", "上交前",
        "交之前确认", "最后确认"
    ],
    "validation_planning": [
        "验证方案", "验证计划", "检验方案",
        "模型验证", "验证实验", "检验方法",
        "证据支持", "验证清单", "验证策略",
        "怎么验证", "如何检验", "检验步骤",
        "显著性", "验证指标", "验证方法",
        "怎么证明", "证明它", "验证有效性",
        "设计验证", "制定验证", "规划验证"
    ],
    "evidence_requirement": [
        "需要什么证据", "哪些指标", "检验要求",
        "证据清单"
    ],
    "mandatory_validation_check": [
        "__system_trigger__"  # 系统级触发, 不通过关键词匹配
    ],
}

# 意图 → 域映射（加速 Intent Filter）
INTENT_TO_DOMAIN = {
    "model_selection_justification": ["paper", "reasoning"],
    "paper_argument_generation": ["paper", "reasoning"],
    "alternative_elimination": ["paper", "reasoning"],
    "model_formalization": ["paper", "reasoning", "prediction", "optimization", "evaluation", "statistics"],
    "model_documentation": ["paper", "reasoning"],
    "paper_quality_check": ["paper", "governance"],
    "paper_compliance_verification": ["paper", "governance"],
    "pre_submission_review": ["paper", "governance"],
    "validation_planning": ["governance", "evaluation", "prediction", "optimization", "statistics"],
    "evidence_requirement": ["governance", "evaluation"],
    "mandatory_validation_check": ["governance"],
}

# 生命周期状态 → 评分的映射
LIFECYCLE_SCORE = {
    "active": 1.0,
    "partial": 0.5,
    "sandbox": 0.3,
    "not_connected": 0.1,
    "deprecated": 0.0,
}


class InvocationGate:
    """v6.5 Invocation Gate — 运行时治理层入口"""

    def __init__(self, registry_path: str = None):
        """
        Args:
            registry_path: skill_runtime_registry.yaml 的路径。
                           默认读取 ../skill_runtime_registry.yaml
        """
        if registry_path is None:
            registry_path = os.path.join(
                os.path.dirname(__file__), "..", "skill_runtime_registry.yaml"
            )
        self.registry_path = registry_path
        self.skills: dict = {}
        self._load_registry()

    def _load_registry(self):
        """从 skill_runtime_registry.yaml v2.0 加载所有受治理的技能定义"""
        if not os.path.isfile(self.registry_path):
            print(f"[InvocationGate] WARNING: registry not found: {self.registry_path}")
            return

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                registry = yaml.safe_load(f)
        except Exception as e:
            print(f"[InvocationGate] ERROR loading registry: {e}")
            return

        raw_skills = registry.get("skills", {})
        governed_count = 0

        for skill_id, data in raw_skills.items():
            boundary = data.get("boundary", {})
            must_call = boundary.get("must_call", [])
            # 只加载有 boundary 且至少有一条 must_call pattern 的技能
            if must_call and any(mc.get("patterns", []) for mc in must_call):
                governed_count += 1
                self.skills[skill_id] = data
            else:
                # boundary 存在但 patterns 为空 → stub，暂不加载到 Gate
                pass

        print(f"[InvocationGate] Loaded {governed_count}/{len(raw_skills)} governed skills: {list(self.skills.keys())}")

    # ===== 匹配流水线 =====

    def evaluate(self, query: str, domain_hint: Optional[str] = None) -> dict:
        """
        对用户查询执行完整的 Gate 评估流水线。

        Args:
            query: 用户原始查询文本
            domain_hint: Problem Intelligence 提供的领域提示（可选）

        Returns:
            GateDecision dict (符合 invocation_decision.schema.json)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        decision_id = f"ID-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

        # Step 1: Intent Filter — 缩小候选
        candidates = self._intent_filter(query, domain_hint)

        # Step 2: Boundary Match — 对每个候选评分
        scored = []
        for skill_id in candidates:
            skill = self.skills[skill_id]
            result = self._score_skill(query, skill, skill_id)
            if result:
                scored.append(result)

        # 按综合置信度降序排列
        scored.sort(key=lambda x: x["confidence"], reverse=True)

        # 如果没有候选，允许自由回答
        if not scored:
            return self._build_decision(
                decision_id=decision_id, query=query, decision="allow_answer",
                matched=None, candidates=[], timestamp=timestamp,
                reason="No skill boundary matched the query"
            )

        top = scored[0]
        top_skill_id = top["skill_id"]
        top_skill = self.skills[top_skill_id]

        # Step 3: Dependency + Lifecycle 检查
        dep_result = self._check_dependency(top_skill_id)
        lc_result = self._check_lifecycle(top_skill)

        threshold = top_skill.get("decision", {}).get("confidence_threshold", 0.80)

        # 综合判断
        if lc_result["state"] in ("deprecated", "not_connected"):
            return self._build_decision(
                decision_id=decision_id, query=query, decision="allow_answer",
                matched=top, candidates=scored, timestamp=timestamp,
                reason=f"Skill {top_skill_id} lifecycle state is {lc_result['state']}: {lc_result['reason']}",
                dep_check=dep_result, lc_check=lc_result, conf_check=None
            )

        if lc_result["state"] == "sandbox":
            # sandbox 技能不能强制调用
            final_decision = "suggest"
            reason = f"Skill {top_skill_id} is in sandbox — cannot mandatory_call"
        elif not dep_result["passed"]:
            # 上游依赖不可用
            final_decision = "suggest"
            blocking = dep_result.get("blocking_upstream", [])
            reason = f"Upstream dependencies not active: {blocking}"
        elif top["confidence"] >= threshold:
            final_decision = "mandatory_call"
            reason = f"Matched must_call intent '{top['matched_intent']}' with confidence {top['confidence']:.2f} >= threshold {threshold}"
        elif top["confidence"] >= 0.50:
            final_decision = "suggest"
            reason = f"Confidence {top['confidence']:.2f} in (0.50, {threshold}) — suggest but not mandatory"
        else:
            final_decision = "allow_answer"
            reason = f"Confidence {top['confidence']:.2f} < 0.50 — allow free answer"

        conf_check = {
            "threshold": threshold,
            "actual": top["confidence"],
            "above_threshold": top["confidence"] >= threshold,
        }

        return self._build_decision(
            decision_id=decision_id, query=query, decision=final_decision,
            matched=top, candidates=scored, timestamp=timestamp,
            reason=reason,
            dep_check=dep_result, lc_check=lc_result, conf_check=conf_check
        )

    # ===== Step 1: Intent Filter =====

    def _intent_filter(self, query: str, domain_hint: Optional[str] = None) -> list:
        """
        基于意图语义标签缩小候选技能范围。
        对每个注册技能的 must_call.intent 做关键词匹配，
        如果技能的 domain 与 domain_hint 有交集则加分。
        """
        candidates = set()
        query_lower = query.lower()

        for skill_id, skill in self.skills.items():
            must_calls = skill.get("boundary", {}).get("must_call", [])
            for mc in must_calls:
                intent = mc.get("intent", "")
                keywords = INTENT_KEYWORDS.get(intent, [])
                # 检查 query 是否包含该 intent 的任一关键词
                matched_kw = [kw for kw in keywords if kw.lower() in query_lower]
                if matched_kw:
                    candidates.add(skill_id)
                    break

                # 也检查 patterns 的直接匹配（快速路径）
                patterns = mc.get("patterns", [])
                for pat in patterns:
                    # 跳过系统级触发模式
                    if pat.startswith("__system__"):
                        continue
                    try:
                        if re.search(pat, query, re.IGNORECASE):
                            candidates.add(skill_id)
                            break
                    except re.error:
                        continue

            # domain_hint 加速：如果技能 domain 匹配 domain_hint，提升为候选
            if domain_hint and skill_id not in candidates:
                skill_domains = skill.get("identity", {}).get("domain", [])
                if domain_hint in skill_domains:
                    candidates.add(skill_id)

        return list(candidates)

    # ===== Step 2: Boundary Match + Scoring =====

    def _score_skill(self, query: str, skill: dict, skill_id: str) -> Optional[dict]:
        """
        对单个技能做完整的意图匹配 + 模式匹配 + 加权评分。
        返回 None 表示 avoid_call 被触发，此技能不应被考虑。
        """
        # avoid_call 检查 — 如果匹配则直接排除
        avoid_calls = skill.get("boundary", {}).get("avoid_call", [])
        for ac in avoid_calls:
            patterns = ac.get("patterns", [])
            for pat in patterns:
                try:
                    if re.search(pat, query, re.IGNORECASE):
                        # avoid_call 触发，排除此技能
                        return None
                except re.error:
                    continue

        # must_call 匹配
        must_calls = skill.get("boundary", {}).get("must_call", [])
        best_semantic = 0.0
        best_pattern = 0.0
        best_intent = None
        matched_patterns = []

        for mc in must_calls:
            intent = mc.get("intent", "")
            intent_conf = mc.get("confidence", 0.70)

            # 语义评分: 关键词命中率（封顶机制避免 long-tail 稀释）
            keywords = INTENT_KEYWORDS.get(intent, [])
            if keywords:
                hits = sum(1 for kw in keywords if kw.lower() in query.lower())
                # 命中 >= 3 个关键词视为满分，避免长关键词表稀释分数
                capped_hits = min(hits, 3)
                capped_len = min(len(keywords), 5)
                semantic = capped_hits / max(capped_len, 1)
            else:
                semantic = 0.0

            # 模式评分: 基于正则匹配率
            patterns = mc.get("patterns", [])
            pattern_hits = 0
            for pat in patterns:
                if pat.startswith("__system__"):
                    continue
                try:
                    if re.search(pat, query, re.IGNORECASE):
                        pattern_hits += 1
                        matched_patterns.append(pat)
                except re.error:
                    continue

            # 模式命中 >= 1 即视为该维度通过
            pattern_score = 1.0 if pattern_hits >= 1 else 0.0

            # 综合语义+模式: 取 max(semantic, pattern_score) 而非加权平均
            # 理由: 关键词和正则模式是两条独立路径，任一命中即证明 query 与 intent 匹配
            match_score = max(semantic, pattern_score)

            # 如果至少一条路径命中，intent_conf 直接生效
            if match_score > 0:
                combined = intent_conf * (0.7 + 0.3 * match_score)
            else:
                combined = 0.0

            if combined > best_semantic:
                best_semantic = combined
                best_pattern = pattern_score
                best_intent = intent

        if best_intent is None:
            return None

        # 生命周期评分
        lc_state = (
            skill.get("status")
            or skill.get("lifecycle", {}).get("state", "not_connected")
        )
        lifecycle_score = LIFECYCLE_SCORE.get(lc_state, 0.0)

        # 综合置信度 = semantic*0.6 + pattern*0.3 + lifecycle*0.1
        confidence = round(
            best_semantic * 0.6 + best_pattern * 0.3 + lifecycle_score * 0.1, 4
        )

        return {
            "skill_id": skill_id,
            "confidence": confidence,
            "semantic_score": round(best_semantic, 4),
            "pattern_score": round(best_pattern, 4),
            "lifecycle_score": lifecycle_score,
            "matched_intent": best_intent,
            "matched_patterns": matched_patterns,
        }

    # ===== Step 3: Dependency & Lifecycle 检查 =====

    def _check_dependency(self, skill_id: str) -> dict:
        """检查上游依赖是否可用"""
        skill = self.skills.get(skill_id)
        if not skill:
            return {"passed": True, "blocking_upstream": [], "reason": "skill not in registry"}

        upstream = skill.get("dependency", {}).get("upstream", [])
        blocking = []

        for dep_id in upstream:
            if dep_id in self.skills:
                dep_skill = self.skills[dep_id]
                dep_state = (
                    dep_skill.get("status")
                    or dep_skill.get("lifecycle", {}).get("state", "not_connected")
                )
                if dep_state not in ("active",):
                    blocking.append(dep_id)
            else:
                # 依赖的技能不在 boundary registry 中（可能尚未定义 boundary）
                # 不是 blocker，但记录警告
                pass

        if blocking:
            return {
                "passed": False,
                "blocking_upstream": blocking,
                "reason": f"Upstream skills not active: {', '.join(blocking)}"
            }
        return {"passed": True, "blocking_upstream": [], "reason": "All upstream dependencies active"}

    def _check_lifecycle(self, skill: dict) -> dict:
        """检查技能生命周期状态是否允许调用"""
        state = skill.get("status") or skill.get("lifecycle", {}).get("state", "not_connected")
        if state == "active":
            return {"state": state, "callable": True, "reason": "Active — full production use"}
        elif state == "partial":
            return {"state": state, "callable": True, "reason": "Partial — callable but features may be incomplete"}
        elif state == "sandbox":
            return {"state": state, "callable": False, "reason": "Sandbox — experimental, not for production"}
        elif state == "deprecated":
            return {"state": state, "callable": False, "reason": "Deprecated — scheduled for archival"}
        else:
            return {"state": state, "callable": False, "reason": f"Not connected — no runtime path"}

    # ===== 输出构建 =====

    def _build_decision(self, decision_id, query, decision,
                        matched, candidates, timestamp, reason,
                        dep_check=None, lc_check=None, conf_check=None):
        """构建符合 invocation_decision.schema.json 的 GateDecision"""
        result = {
            "decision_id": decision_id,
            "decision": decision,
            "query": {"text": query},
            "timestamp": timestamp,
            "gate_version": "v1.0",
            "reason": reason,
            "all_candidates": [
                {
                    "skill_id": c["skill_id"],
                    "confidence": c["confidence"],
                    "decision": self._confidence_to_decision(
                        c["confidence"],
                        self.skills.get(c["skill_id"], {}).get("decision", {}).get("confidence_threshold", 0.80),
                    )
                }
                for c in (candidates or [])
            ],
        }

        if matched:
            result["matched_skill"] = {
                "skill_id": matched["skill_id"],
                "confidence": matched["confidence"],
                "semantic_score": matched["semantic_score"],
                "pattern_score": matched["pattern_score"],
                "lifecycle_score": matched["lifecycle_score"],
                "matched_intent": matched["matched_intent"],
                "matched_patterns": matched["matched_patterns"],
            }

        if dep_check or lc_check or conf_check:
            gating = {}
            if dep_check:
                gating["dependency_check"] = dep_check
            if lc_check:
                gating["lifecycle_check"] = lc_check
            if conf_check:
                gating["confidence_check"] = conf_check
            result["gating_details"] = gating

        result["fallback_used"] = False
        if decision == "suggest" and dep_check and not dep_check["passed"]:
            result["fallback_used"] = True

        return result

    @staticmethod
    def _confidence_to_decision(confidence: float, threshold: float) -> str:
        if confidence >= threshold:
            return "mandatory_call"
        elif confidence >= 0.50:
            return "suggest"
        return "allow_answer"


# ===== Benchmark Runner =====

def run_boundary_test(gate: InvocationGate, test_cases: list) -> dict:
    """
    运行 Boundary Benchmark 测试。

    Args:
        gate: InvocationGate 实例
        test_cases: [{"query": str, "expected": "mandatory_call"|"allow_answer", "skill_id": str}]

    Returns:
        {"total": int, "correct": int, "accuracy": float, "failures": [...], "by_skill": {...}}
    """
    results = {"total": 0, "correct": 0, "failures": [], "by_skill": {}}

    for tc in test_cases:
        decision = gate.evaluate(tc["query"])
        actual = decision["decision"]
        expected = tc["expected"]
        skill_id = tc.get("skill_id", "unknown")

        if skill_id not in results["by_skill"]:
            results["by_skill"][skill_id] = {"total": 0, "correct": 0, "failures": []}

        results["total"] += 1
        results["by_skill"][skill_id]["total"] += 1

        if actual == expected:
            results["correct"] += 1
            results["by_skill"][skill_id]["correct"] += 1
        else:
            failure = {
                "query": tc["query"],
                "expected": expected,
                "actual": actual,
                "skill_id": skill_id,
                "matched_skill": decision.get("matched_skill", {}).get("skill_id"),
                "confidence": decision.get("matched_skill", {}).get("confidence"),
            }
            results["failures"].append(failure)
            results["by_skill"][skill_id]["failures"].append(failure)

    results["accuracy"] = round(results["correct"] / max(results["total"], 1), 4)
    return results


# ===== CLI =====

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Invocation Gate v1.0 — Self Test")
    print("=" * 60)

    gate = InvocationGate()
    print()

    # 快速烟雾测试
    test_queries = [
        # mandatory_call 期望
        ("为什么选择随机森林而不是BP神经网络？", "mandatory_call"),
        ("检查这篇论文是否符合CUMCM规范", "mandatory_call"),
        ("给这个优化问题设计数学模型框架", "mandatory_call"),
        ("需要为模型设计哪些验证实验？", "mandatory_call"),
        # allow_answer 期望
        ("什么是K-means聚类算法？", "allow_answer"),
        ("解释一下熵权法的公式", "allow_answer"),
        ("今天天气怎么样？", "allow_answer"),
    ]

    passed = 0
    for query, expected in test_queries:
        decision = gate.evaluate(query)
        actual = decision["decision"]
        matched = decision.get("matched_skill", {}).get("skill_id", "none")
        conf = decision.get("matched_skill", {}).get("confidence", 0)

        status = "PASS" if actual == expected else "FAIL"
        if status == "PASS":
            passed += 1

        print(f"[{status}] expected={expected} actual={actual} skill={matched} conf={conf:.3f}")
        print(f"        query: {query[:60]}...")
        print(f"        reason: {decision.get('reason', 'N/A')[:80]}")
        print()

    print(f"Smoke test: {passed}/{len(test_queries)} passed")
