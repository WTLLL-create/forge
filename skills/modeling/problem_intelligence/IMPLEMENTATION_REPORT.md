# Stage 20.2 实施报告 — Problem Intelligence

> 完成日期: 2026-07-30
> 状态: ✅ 完成

---

## 一、创建的文件

| 文件 | 类型 | 行数 | 职责 |
|------|:---:|:---:|------|
| `README.md` | 文档 | ~60 | 模块总览 |
| `problem_analysis_protocol.md` | **核心协议** | ~200 | 4步分析框架 + 关键区分规则 |
| `abstraction_engine.md` | 映射引擎 | ~130 | 描述特征→数学范畴映射 + Router v1 失败规则 |
| `problem_patterns/optimization_pattern.md` | 模式 | ~30 | 优化类识别模式 |
| `problem_patterns/prediction_pattern.md` | 模式 | ~30 | 预测类识别模式（含与机理的区分线） |
| `problem_patterns/evaluation_pattern.md` | 模式 | ~20 | 评价类识别模式 |
| `problem_patterns/mechanism_pattern.md` | **重点** | ~120 | 机理类识别模式（含 Router v1 失败分析） |
| `problem_patterns/network_pattern.md` | 模式 | ~25 | 网络类识别模式 |
| `problem_patterns/uncertainty_pattern.md` | 模式 | ~25 | 不确定性类识别模式 |
| `reframing_library/problem_transfer.md` | 重构 | ~50 | 8种问题迁移模式 |
| `reframing_library/assumption_breaking.md` | 重构 | ~25 | 假设突破模式 |
| `reframing_library/hybrid_model.md` | 重构 | ~40 | 4种混合模型架构 |
| `reframing_library/innovation_patterns.md` | 重构 | ~25 | 创新来源地图 |
| `test_cases/mechanism_10_cases.md` | 测试 | ~180 | 10道机理题+Protocol逐题分析 |

**总计**: 14 个文件，~980 行，0 个已有文件被修改。

## 二、核心设计

### 知识层不是代码层

Stage 20.2 是纯粹的**知识文档**。Agent 使用 Protocol 的方式是：
1. 读取 `problem_analysis_protocol.md`
2. 按 4 步框架逐题执行手动分析
3. 用 `abstraction_engine.md` 的映射表辅助 Step 3
4. 用 `mechanism_pattern.md` 避免 Router v1 的已知误判陷阱

### 三层理解深度

```
Level 1: 表面关键词     → "预测""优化"           → Router v1 已做
Level 2: 数学结构       → "动力系统""网络流"       → 本文档建立
Level 3: 创新空间       → "可重构为图论"           → reframing_library/
```

### 三个关键区分规则

来自 Router v1 失败案例的教训：
1. **Rule A**: "建立XX模型" ≠ 机理建模 → 检查是否引用了物理定律
2. **Rule B**: "预测"可能是"用机理推演" → 检查是基于定律还是基于数据
3. **Rule C**: "优化参数"可能不是"运筹优化" → 检查优化对象是否需要先建模

## 三、与 Router v1 的集成

```
S1 ANALYSIS (agent_system/workflow_execution.md)
    │
    ├── 1. 执行 problem_analysis_protocol.md 的 4 步分析
    │      ├── Step 1: 识别研究对象
    │      ├── Step 2: 分析变量关系
    │      ├── Step 3: 判定数学本质（用 abstraction_engine.md）
    │      └── Step 4: 候选模型空间
    │
    ├── 2. 将分析结果传入 Knowledge Router
    │      router.route(problem_text, extra_features={
    │          "object_type": ...,    ← Step 1
    │          "relation_type": ...,  ← Step 2
    │          "math_essence": ...,   ← Step 3
    │          "candidate_space": ...,← Step 4
    │      })
    │
    └── 3. Router 基于精炼后的信息进行模型推荐
```

## 四、预期对 20.1.5 失败案例的改善

| 题目 | Router v1 | Protocol 分析 | 改善 |
|------|------|------|:---:|
| 2019A 无线传播 | 预测 ❌ | 机理(经验公式+物理定律) | ✅ |
| 2021C 帕金森DBS | 优化 ❌ | 机理+优化(HH ODE) | ✅ |
| 2019E 全球气候 | 预测 ❌ | 混合(因果系统→多模型对比) | ✅ |

机理题识别预期从 0/3 提升到 3/3。

## 五、后续建议

### Stage 20.2b（可立即做）
- 用 10 道机理题实际跑 Protocol 分析，验证识别准确率
- 如有仍然误判的题，补充 mechanism_pattern.md 的边界案例

### Stage 20.3
- Competition Simulator — 基于 Protocol + Router 的完整竞赛模拟
