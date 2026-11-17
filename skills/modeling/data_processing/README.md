# Data Processing Skill — 数据处理模块

> 阶段 11.2：数学建模数据处理能力，从原始数据到模型输入的完整管道
>
> 创建日期：2026-07-29 | 版本：v1.0

---

## 定位

本 Skill 是 Forge 数学建模体系的**数据预处理层**。它定义了从原始数据文件到模型就绪输入的完整转换管道。与阶段 11.1（Numerical Computing）形成上下游关系：

```
原始数据(CSV/Excel)
  │
  ▼  ← data_processing Skill (本模块)
DataFrame → 质量检查 → 清洗 → 转换 → 探索 → 特征构造
  │
  ▼  ← numerical_computing Skill (阶段11.1)
numpy.ndarray → 矩阵运算 → 模型求解 → 结果
```

## 与其他 Skill 的关系

```
skills/modeling/
├── 数学建模完整流程.md        ← 流程控制
├── 数据分析流程.md            ← EDA 方法论（上游指导）
├── data_processing/           ← ★ 数据预处理层（本 Skill）
│   ├── workflow.md            ← 6 步标准流水线
│   ├── decision_rules.md      ← 根据数据特征自动选择处理方法
│   └── examples/              ← 可运行案例
│       ├── case1 → 清洗 → [连接]
│       ├── case2 → 探索 → [连接]
│       ├── case3 → 时序 → [连接]
│       └── case4 → 特征 → [连接]
│                    ↓
├── numerical_computing/       ← 数值计算层
│   └── examples/              ← 接收 numpy.ndarray 输入
├── surrogate_optimization.md  ← 优化层
└── 模型验证方法.md             ← 验证层
```

## 设计原则

1. **管道式思维** — 每个步骤的输入/输出类型明确定义，Agent 可以接力执行
2. **质量优先** — 数据清洗是建模的基石，不干净的数据产出的模型不可信
3. **场景驱动** — 一切围绕数学建模竞赛场景设计，不做泛化的"数据分析教程"
4. **与 11.1 无缝衔接** — 输出统一为 numpy.ndarray 或干净 DataFrame

## 目录结构

```
data_processing/
├── README.md              ← 本文件
├── github_sources.md      ← GitHub 仓库调研
├── workflow.md            ← 6 步标准数据处理流水线
├── decision_rules.md      ← AI 自动决策规则
├── pandas/
│   ├── index.md           ← Pandas 知识提炼
│   └── cheatsheet.md      ← Pandas 速查表
├── data_quality/
│   ├── missing_value.md   ← 缺失值处理策略
│   └── outlier_detection.md ← 异常值检测方法
├── feature_engineering/
│   └── index.md           ← 特征工程指南
├── examples/
│   ├── case1_clean_data.py       ← 案例1：企业销售数据清洗
│   ├── case2_time_series.py      ← 案例2：城市指标时间序列
│   ├── case3_feature_analysis.py ← 案例3：多指标探索分析
│   └── case4_ml_prepare.py       ← 案例4：机器学习数据准备
└── templates/
    └── data_processing_pipeline.py ← 通用管道模板
```

## Agent 调用方式

当数学建模流程进入「数据处理」阶段时，Agent 应：

1. 读取 `workflow.md` 了解标准 6 步流水线
2. 读取 `decision_rules.md` 根据数据特征选择处理方法
3. 查阅 `pandas/index.md` 了解核心 API 用法
4. 参考 `examples/` 中的类似场景

## 与 Numerical Computing Skill 的接口

```python
# 数据处理阶段输出 → 数值计算阶段输入
from skills.modeling.data_processing.examples.case4_ml_prepare import prepare_model_input

# 返回格式：
# X: numpy.ndarray (n_samples, n_features)  → 喂给 scipy.optimize / numpy.linalg
# y: numpy.ndarray (n_samples,)              → 目标变量
# feature_names: list[str]                   → 特征名（用于论文解释）
```
