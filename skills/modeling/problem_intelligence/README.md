# Problem Intelligence — 问题理解层

> Stage 20.2 核心模块。
>
> 定位：让 Agent 从"匹配关键词"升级为"理解问题本质"。
> 不负责求解，只负责理解。

---

## 架构

```
Raw Problem Text
    │
    ▼
problem_analysis_protocol.md     ← 4步分析框架
    │
    ├── Step 1: 识别研究对象
    ├── Step 2: 分析变量关系
    ├── Step 3: 判定数学本质  ← 由 abstraction_engine.md 支持
    └── Step 4: 候选模型空间
    │
    ▼
Structured Problem Understanding
    │
    ▼
Knowledge Router (Stage 20.1)     ← 消费 Problem Intelligence 输出
```

---

## 文件清单

| 文件 | 职责 |
|------|------|
| `problem_analysis_protocol.md` | **核心**：Agent 固定执行的 4 步分析框架 + 关键区分规则 |
| `abstraction_engine.md` | 从描述性分析→数学范畴的映射引擎 + Router v1 失败案例规则 |
| `problem_patterns/` | 6 类问题的识别模式 |
| `reframing_library/` | 问题重构知识库（创新视角） |
| `test_cases/` | 机理类题目测试用例 |

---

## 与 Router v1 的关系

```
Router v1 (20.1):
  题目关键词 → 题型匹配 → 模型推荐
  问题: 70% 准确率, 机理类 0%

Problem Intelligence (20.2):
  题目文本 → 4步分析 → 数学本质 → 结构化理解 → 传给 Router
  目标: 80%+ 准确率, 机理类 ≥80%
```

**Problem Intelligence 不替代 Router**。它前置在 Router 之前，把原始问题转化为 Router 能更好消费的结构化信息。

---

## 验收标准

基于 20.1.5 benchmark 发现的机理类盲区：

- 输入：10 道含机理特征的题目（来自 benchmark 失败案例 + 新增）
- 目标：机理识别从 0/3 提升到 ≥80%
- 不要求 Router 输出变化（Router 不受影响），只要求 Problem Intelligence 的数学本质判定正确

---

## 设计原则

1. **不写代码**：20.2 第一版是知识文档，Protocol 是 Agent 手动执行的思维框架
2. **最小侵入**：新增独立目录，不修改任何已有文件
3. **前置不替代**：Problem Intelligence 在 Router 之前工作，Router 逻辑完全不变
4. **聚焦盲区**：优先解决 20.1.5 暴露的机理类问题
