# Strategy Planner — 建模策略规划器

> Stage 20.2.5 模块。
>
> 定位：从"理���问题"到"执行建模"之间的战术决策层。

## 为什么需要

```
Problem Intelligence → 问题是什么(what)
Knowledge Router     → 去哪找知识(where)
Strategy Planner     → 怎么组合执行(how) ← 本文档
```

没有 Strategy Planner，Agent 知道该用什么模型，但不知道按什么顺序、怎么衔接。

## 架构

```
Problem Intelligence 输出
    │
    ▼
pipeline_protocol.md         ← 5种标准管线模板 + 管线选择决策树
    │
    ├── 选择管线模板
    ├── 分解为阶段
    ├── 为每阶段匹配模型(从  Knowledge Router 候选空间)
    ├── 设计阶段间接口
    └── 识别管线风险
    │
    ▼
ModelingPipeline JSON        ← 供 agent_system/state_machine.md 消费
```

## 文件清单

| 文件 | 职责 |
|------|------|
| `pipeline_protocol.md` | 核心：管线规划协议 + 5种标准模板 |
| `pipeline_patterns/` | 从3道已完成真题提取的可复用管线模式 |
| `test_cases/` | 基于已知题目的管线验证 |
| `README.md` | 本文件 |

## 五种标准��线模板

| 模板 | 适合 | 来源 |
|------|------|------|
| 模板1: 纯预测 | 时间序列/回归预测 | 通用 |
| 模板2: 纯优化 | 运筹优化 | 通用 |
| 模板3: 机理+数据 | 物理模型+实测校准 | 2019A模式 |
| 模板4: 评价 | 多指标排序 | 通用 |
| 模板5: 分而治之 | 多独立子问题 | 2021B模式 |

## 五种实战管线模式

| 模式 | 来源 | 关键特征 |
|------|------|------|
| surrogate_optimization | A题 | 先代理后优化, 聚类降维 |
| fusion_optimization | B题 | 先融合后优化, 双重方法对比 |
| mip_system_dynamics | C题 | 先短后长, Sigmoid风险量化 |
| predict_then_decide | 通用 | 预测→决策两阶段 |
| physics_plus_data | 通用 | 物理骨架+AI残差校正 |
