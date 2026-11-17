# 数学建模知识层 — GitHub 参考源

> 本文档记录用于构建 Forge 数学建模知识层的 GitHub 仓库调研结果。
> 提取的是**组织结构、分类逻辑和设计思想**，非源码。
>
> 创建日期：2026-07-29

---

## 一、模型分类体系参考

### 1.1 zhanwen/MathModel

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/zhanwen/MathModel |
| **Stars** | ~7,000 |
| **维护状态** | 低活跃（最后更新 2025-09，430 commits） |
| **定位** | 国赛/美赛资���汇集库（试题、论文、模板、算法） |

**核心组织方式**：

```
按年份分层（2004-2025 试题+论文）
      +
按算法性质分类：
  ├── 经典算法（基础数学方法）
  └── 现代算法（8类：仿真/粒子群/马尔可夫/蒙特卡洛/模拟退火/神经网络/小波/遗传）
      +
按学习阶段分类：基础篇 / 技巧篇
```

**对本系统的贡献**：

| 借鉴点 | 对应知识层文件 | 如何调整 |
|--------|--------------|----------|
| 算法时代二分法（经典/现代） | `数学建模题型识别.md` | 在题型分类中增加"解法类型"维度，标注经典/现代 |
| 十类核心算法清单 | `模型选择决策树.md` | 验证现有决策树覆盖度，补充遗漏的仿真/小波分析 |
| 按年份归档赛题论文 | `projects/math-modeling/` | 参考其项目结构优化模板 |

---

### 1.2 luochang212/Mathematical-Modeling

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/luochang212/Mathematical-Modeling |
| **Stars** | — (仓库 404，可能已删除或私有化) |
| **状态** | ❌ 不可访问，已从调研列表中移除 |

---

### 1.3 TheAlgorithms/Python

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/TheAlgorithms/Python |
| **Stars** | ~222,900 |
| **维护状态** | 极高活跃（周级提交） |
| **定位** | 全球最大算法百科，800+ 算法实现，40+ 分类 |

**核心分类体系**（与建模相关的子目录）：

```
TheAlgorithms/Python/
├── maths/                  ← 数论、数值方法、序列
├── linear_algebra/         ← 矩阵运算（纯 Python 教学实现）
├── dynamic_programming/    ← DP 模式大全
├── greedy_methods/         ← 贪心策略
├── divide_and_conquer/     ← 分治
├── genetic_algorithm/      ← 进化计算
├── graphs/                 ← 图论（最短路径、网络流）
├── knapsack/               ← 背包问题变体
├── scheduling/             ← 调度算法
├── machine_learning/       ← ML 参考实现
├── neural_network/         ← NN 参考实现
├── physics/                ← 物理仿真
├── fuzzy_logic/            ← 模糊逻辑
├── computer_vision/        ← CV
└── financial/              ← 金融建模
```

**对本系统的贡献**：

| 借鉴点 | 对应文件 | 调整方向 |
|--------|----------|----------|
| 40+ 分类的命名与划分逻辑 | `模型选择决策树.md` | 参考其数学类子目录命名（如 `maths/` 细分数值方法/数列） |
| "Implementations are for learning purposes only" | 全局原则 | 知识层文档中明确标注：代码为教学参考，生产用 NumPy/SciPy |
| CI/CD + pre-commit + type hints 工程化 | `standards/` | 可参考其代码质量控制方式 |

---

## 二、机器学习模型选择参考

### 2.1 scikit-learn/scikit-learn

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/scikit-learn/scikit-learn |
| **Stars** | ~66,800 |
| **维护状态** | 极高活跃 |
| **定位** | Python ML 标准库 |

**核心模型选择逻辑**（sklearn 的 classifier/regressor/cluster 三分法）：

```
任务类型
├── 分类 (Classifier)
│   ├── 线性: LogisticRegression, LinearSVC
│   ├── 树模型: RandomForest, GradientBoosting
│   └── 核方法: SVC
├── 回归 (Regressor)
│   ├── 线性: LinearRegression, Ridge, Lasso
│   ├── 树模型: RandomForestRegressor
│   └── 核方法: SVR
├── 聚类 (Clustering)
│   ├── KMeans, DBSCAN, Agglomerative
│   └── GaussianMixture
└── 降维 (Decomposition)
    └── PCA, t-SNE, NMF
```

**对本系统的贡献**：

| 借鉴点 | 对应文件 | 调整方向 |
|--------|----------|----------|
| 任务类型→模型→适用条件 三级映射 | `模型选择决策树.md` | 在现有决策树中增加"数据规模/变量类型/任务类型"判断维度 |
| `sklearn.choose_best` 的模型选择流程图 | `模型选择决策树.md` | 参考其 famous 的算法选择 cheat-sheet |

---

## 三、优化问题分类参考

### 3.1 google/or-tools

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/google/or-tools |
| **Stars** | ~11,000 |
| **维护状态** | 高活跃（15,819 commits，2026-06 仍在提交） |
| **许可证** | Apache 2.0 |
| **定位** | 组合优化求解器套件（Google 出品） |

**优化问题分类体系**：

```
按求解方法:
├── 线性规划 (LP)    → Glop, PDLP 求解器
├── 混合整数规划 (MIP) → 商业/开源求解器包装
├── 约束规划 (CP)    → CP-SAT, CP* 求解器
└── 布尔优化 (BOP)   → BOP 求解器

按问题类型:
├── 路径规划    → TSP / VRP
├── 装箱/背包   → Bin packing / Knapsack
├── 调度        → Scheduling
└── 图问题      → 最短路径 / 最小成本流 / 最大流 / 分配
```

**对本系统的贡献**：

| 借鉴点 | 对应文件 | 调整方向 |
|--------|----------|----------|
| 优化问题的二维分类（方法 × 问题类型） | `模型选择决策树.md` + `numerical_computing/decision_rules.md` | 在决策树中增加"先判问题类型，再选求解方法"的分层逻辑 |
| CP-SAT vs LP 的适用场景区分 | `numerical_computing/api_mapping.md` | 补充整数规划（milp）和约束规划的应用场景说明 |
| 路径/装箱/调度 三大经典问题模式 | `数学建模题型识别.md` | 在优化类题目下，补充子类型识别词（如"路线"→VRP，"物品分配"→Bin packing） |

---

## 四、建模工作流参考

### 4.1 jupyter/notebook

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/jupyter/notebook |
| **Stars** | ~13,300 |
| **维护状态** | 极高活跃 |
| **定位** | 交互式计算工作流环境 |

**对建模流程的参考价值**：

- **探索 → 实验 → 记录** 三段式循环是 Jupyter 的核心使用模式
- 我们的 `workflow.md`（data_processing）和 `数学建模完整流程.md` 已经吸收了这种三段式
- 建议在建模流程中明确标注"实验记录节点"——每次模型参数变化都做 snapshot

---

## 五、工作流架构参考

### 5.1 langchain-ai/langgraph

| 属性 | 内�� |
|------|------|
| **地址** | https://github.com/langchain-ai/langgraph |
| **Stars** | ~37,800 |
| **维护状态** | 极高活跃（7,011+ commits，日级发布） |
| **定位** | 弹性 Agent 的图状态机编排框架 |

**核心架构概念**（仅提取思想，不接入多 Agent）：

```
状态图模型:
  State Graph (有向图)
    ├── Nodes  — 处理节点（每个节点 = 一个建模步骤）
    ├── Edges  — 流转路径（普通边 = 固定顺序，条件边 = 根据状态分支）
    ├── State  — 共享状态（当前所有已知信息）
    └── Checkpoint — 检查点（可暂停、审查、恢复）
```

**对本系统的贡献**：

| 借鉴点 | 对应设计 | 调整方向 |
|--------|----------|----------|
| **状态驱动**：每个步骤输出决定下一步 | `数学建模完整流程.md` | 将流程中"确认点"显式化为条件判断节点 |
| **条件路由**：根据模型评估结果自动选择下一步（通过/重试/换方法） | `模型选择决策树.md` | 在决策树中增加"Failover"分支——如果首选方法失败，自动降级到备选 |
| **检查点机制**：在关键节点（模型选择后、参数设定后、结果验证后）设置人工确认 | 全部流程文档 | 在流程图中标注 Checkpoint 位置 |
| **不应引入的**：LangGraph 的 Multi-Agent、持久化存储、LangSmith 部署 | — | 明确排除 |

---

## 六、仓库全景汇总

| # | 仓库 | Stars | 角色 | 借鉴重点 | 状态 |
|---|------|-------|------|----------|------|
| 1 | zhanwen/MathModel | ~7k | 模型分类参考 | 经典/现代二分，十类算法清单 | ✅ 纳入 |
| 2 | luochang212/Mathematical-Modeling | — | — | — | ❌ 404 |
| 3 | TheAlgorithms/Python | ~222.9k | 算法分类参考 | 40+ 分类命名，代码规范 | ✅ 纳入 |
| 4 | scikit-learn/scikit-learn | ~66.8k | ML 模型选择 | 任务类型→模型→条件 三级映射 | ✅ 纳入 |
| 5 | google/or-tools | ~11k | 优化问题分类 | 二维分类（方法×问题类型） | ✅ 纳入 |
| 6 | jupyter/notebook | ~13.3k | 工作流环境 | 探索→实验→记录 循环 | ✅ 纳入 |
| 7 | langchain-ai/langgraph | ~37.8k | 工作流架构 | 状态图、条件路由、检查点 | ✅ 纳入（思想层） |

---

## 七、调研总结

### 对 Forge 数学建模知识层的 5 条关键贡献

1. **从 MathModel 学到**：算法应按"经典/现代"两层组织，题型识别中增加"解法类型"维度
2. **从 sklearn 学到**：模型选择应走三级映射（任务→模型→条件），不只列 API
3. **从 OR-Tools 学到**：优化问题需二维分类（先判问题类型，再选求解方法）
4. **从 Jupyter 学到**：建模流程需明确标注"探索→实验→记录"的循环节点
5. **从 LangGraph 学到**：流程设计应加入条件路由（首选方法失败→自动降级）和检查点（关键决策暂停人工确认）

### 不采纳的方向

- 不引入 Multi-Agent 架构（LangGraph 的核心卖点，但对单体建模流程过度设计）
- 不引入持久化存储/部署平台（LangSmith，商业依赖）
- 不直接复制算法代码（TheAlgorithms，仅供分类参考）
