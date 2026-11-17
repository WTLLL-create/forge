# Numerical Computing Skill — 数值计算模块

> 阶段 11.1：基于 GitHub 高质量开源仓库构建的数学建模数值计算知识库
>
> 创建日期：2026-07-29 | 版本：v1.0

---

## 定位

本 Skill 是 Forge 数学建模体系的**数值计算基础设施层**。它不是教程文档，而是经过 GitHub 仓库深度调研、知识提炼、AI 决策规则构建后的**可被 Agent 调用的结构化知识库**。

## 设计原则

1. **不复制源码** — 只提取 API 语义、使用模式、建模映射关系
2. **面向建模场景** — 所有内容以数学建模问题为锚点，不做泛化
3. **Agent 可执行** — decision_rules.md 可被 AI 直接解析为 if-this-then-that 规则
4. **与现有体系协同** — 不替代 skills/modeling/ 中的方法论，只补充数值计算层

## 与其他 Skill 的关系

```
skills/modeling/
├── 数学建模完整流程.md         ← 流程控制（调用本 Skill）
├── 模型选择决策树.md           ← 模型层决策（上层）
├── 数据分析流程.md             ← 数据预处理（本 Skill 上游）
├── numerical_computing/        ← ★ 数值计算层（本 Skill）
│   ├── decision_rules.md       ← 根据问题关键词→选择 NumPy/SciPy 工具
│   ├── api_mapping.md          ← 问题→数学方法→Python API→来源映射
│   └── examples/               ← 可运行的建模案例
├── surrogate_optimization.md   ← 代理优化（本 Skill 下游）
└── 模型验证方法.md              ← 模型验证���本 Skill 下游）
```

## 目录结构

```
numerical_computing/
├── README.md              ← 本文件
├── github_sources.md      ← GitHub 仓库调研结果
├── decision_rules.md      ← AI 自动决策规则
├── api_mapping.md         ← 建模问题→API 映射表
├── evaluation.md          ← Skill 验收标准与测试
├── numpy/
│   ├── index.md           ← NumPy 知识提炼（ndarray/广播/线性代数/随机）
│   └── cheatsheet.md      ← NumPy 速查表
├── scipy/
│   ├── index.md           ← SciPy 知识提炼（optimize/integrate/linalg/stats）
│   └── cheatsheet.md      ← SciPy 速查表
├── examples/
│   ├── case1_linear_system.py    ← 案例1：线性方程组求解
│   ├── case2_linear_program.py   ← 案例2：线性规划优化
│   ├── case3_exponential_fit.py  ← 案例3：指数增长预测
│   └── case4_sir_model.py        ← 案例4：SIR 微分方程模拟
└── templates/
    └── modeling_script.py        ← 数学建模通用脚本模板
```

## 快速导航

| 我想... | 去这里 |
|---------|--------|
| 了解来源仓库 | `github_sources.md` |
| 根据问题自动选工具 | `decision_rules.md` |
| 看建模问题和 API 对应关系 | `api_mapping.md` |
| 学 NumPy 在建模中的用法 | `numpy/index.md` |
| 学 SciPy 在建模中的用法 | `scipy/index.md` |
| 看完整案例 | `examples/` |
| 验收 Skill 可用性 | `evaluation.md` |

## Agent 调用方式

当数学建模流程进入「数值计算」阶段时，Agent 应：

1. 读取 `decision_rules.md` 识别问题类型
2. 参考 `api_mapping.md` 找到对应的 Python API
3. 查阅 `numpy/index.md` 或 `scipy/index.md` 了解 API 用法
4. 参考 `examples/` 中的类似案例编写代码

```python
# 示例：Agent 自动识别后的调用链路
# 问题关键词: "最大化利润" + "资源约束" 
#   → decision_rules.md: 优化问题 → scipy.optimize
#   → api_mapping.md: 线性规划 → scipy.optimize.linprog
#   → scipy/index.md: linprog 签名和使用方式
#   → examples/case2_linear_program.py: 参考实现
```

## 维护策略

- **研究来源更新**：NumPy/SciPy 大版本发布时，更新 `github_sources.md` 和 `api_mapping.md`
- **案例扩充**：每完成一个实际建模项目，将可复用的数值计算片段加入 `examples/`
- **决策规则迭代**：每遇到新的问题类型，补充 `decision_rules.md`
