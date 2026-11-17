# Pipeline Protocol — 建模管线规划协议

> Stage 20.2.5 核心文档。
>
> 定位：从"理解问题"到"执行建模"之间的战术决策层。
> 输入：Problem Intelligence 的结构化理解 + Knowledge Router 的候选模型
> 输出：多步骤建模管线 + 每步的模型/验证/风险配置

---

## 管线设计原则

### 原则 1: 管线 = 阶段序列，不是模型列表

```
❌ 错误: "用 LSTM + MILP + 敏感性分析"
✅ 正确:
    Pipeline:
      Step 1: 能源需求预测 → LSTM (输入: 历史数据, 输出: 未来需求)
      Step 2: 发电调度优化 → MILP (输入: 预测需求+产能约束, 输出: 调度方案)
      Step 3: 鲁棒性验证 → 敏感性分析 (输入: 调度方案, 扰动: 需求±10%)
```

### 原则 2: 每步管线有明确的输入→输出契约

```
Step N: [阶段名称]
├── 输入: [需要哪些数据/前置结果]
├── 模型: [主模型 + 备选]
├── 输出: [产出什么]
├── 验证: [如何确认这一步做对了]
└── 风险: [这一步特有的坑]
```

### 原则 3: 管线可以有分支和回退

```
Step 1 (数据探索)
    │
    ├── 数据充足 → Step 2a (复杂模型)
    └── 数据不足 → Step 2b (简化模型, 降级)
```

---

## 管线生成流程

```
Problem Intelligence 输出
    │
    ├── 数学本质: "机理+优化混合"
    ├── 子问题结构: Q1=OD建模, Q2=参数优化
    └── 依存关系: Q1输出 → Q2输入
    │
    ▼
Step 1: 分解问题为建模阶段
    │   识别每个子问题需要的建模阶段
    │   判断阶段间的数据依赖
    │
    ▼
Step 2: 为每个阶段选择模型
    │   从 Knowledge Router 的候选空间中选取
    │   考虑阶段间兼容性
    │
    ▼
Step 3: 设计验证链
    │   每个阶段独立的验证
    │   跨阶段的端到端验证
    │
    ▼
Step 4: 识别管线风险
    │   阶段衔接处的断裂风险
    │   单一阶段失败的连锁效应
    │
    ▼
输出: ModelingPipeline (JSON)
```

---

## 标准管线模板

### 模板 1: 纯预测管线

```
Pipeline: Data → Clean → Feature → Model → Validate → Forecast

Step 1: 数据预处理
  模型: data_processing/workflow.md 6步管道
  输出: X_train, y_train, X_test, y_test
  验证: 缺失值清零, 分布检查

Step 2: 特征工程
  模型: 特征选择 + PCA(如高维)
  输出: 筛选后的特征集
  验证: 特征-目标相关性分析

Step 3: 模型训练与选择
  模型: 主模型 + 至少1个对比模型
  输出: 训练好的模型 + 验证集指标
  验证: MAE/RMSE, 残差分析, 过拟合检查
  风险: 时序数据必须时间切分

Step 4: 预测与解释
  模型: 测试集最终评估
  输出: 预测值 + 置信区间 + 特征重要性
  验证: 预测值合理性检验
```

### 模板 2: 纯优化管线

```
Pipeline: Problem → Formulate → Simplify → Solve → Validate

Step 1: 问题形式化
  模型: 决策变量+目标函数+��束条件的数学表达
  输出: 标准优化问题形式
  验证: 约束完整性检查

Step 2: 复杂度分析与方法选择
  模型: 判定 LP/NP-hard → 选择精���/启发式
  输出: 求解策略
  风险: Rule C — 如果优化对象需要先建模，先走机理管线

Step 3: 求解
  模型: 精确(linprog) 或 启发式(GA/NSGA-II)
  输出: 最优解 + 算法日志
  验证: 约束满足检查 + 收敛性 + 与基准对比

Step 4: 后处理
  模型: 敏感性分析, 影子价格
  输出: 结果解读 + 建议
```

### 模板 3: 机理+数据混合管线

```
Pipeline: Physics → ODE → Calibrate → Validate → (Optimize)

Step 1: 建立物理模型
  模型: ODE/PDE/经验公式
  输出: 方程系统 + 参数定义
  验证: 方程与已知定律一致性

Step 2: 数值求解物理模型
  模型: Runge-Kutta/有限差分
  输出: 模拟结果
  验证: 改变步长收敛性检查

Step 3: 数据校准(如有实测数据)
  模型: 曲线拟合/参数估计
  输出: 校准后的参数
  验证: 模拟 vs 实测对比

Step 4: (可选) 基于物理模型的优化
  模型: 在物理模型上的参数优化
  输出: 最优参数
  风险: 物理模型的数值稳定性
```

### 模板 4: 评价管线

```
Pipeline: Data → Index → Weight → Score → Rank → Sensitivity

Step 1: 指标体系构建
  模型: 层级指标树(目标→准则→指标)
  输出: 指标体系图 + 每个指标的定义
  验证: 指标可计算性检查

Step 2: 赋权
  模型: AHP(有专家) 或 熵权法(纯数据)
  输出: 权重向量
  验证: CR<0.1(AHP) 或 权重分布的合理性

Step 3: 综合评价
  模型: TOPSIS/RSR/模糊综合评价
  输出: 得分 + 排序
  验证: Kendall τ 多方案一致性

Step 4: 敏感性分析
  模型: 权重±10% 扰动
  输出: 排名稳定性报告
```

### 模板 5: 分而治之管线

```
Pipeline: Decompose → [Sub-pipeline 1] → [Sub-pipeline 2] → ... → Integrate

Step 1: 问题分解
  模型: 识别独立子问题, 判定数据依赖
  输出: 子问题列表 + 依赖图

Step 2-N: 每个子问题独立走对应管线
  子问题类型决定使用模板1-4中的哪一个

Step N+1: 结果整合
  模型: 汇总各子问题结果
  输出: 统一结果报告
  风险: 子问题间的假设一致性
```

### 模板 6: 多模型竞争对比管线 (Stage 20.5 新增)

```
Pipeline: Data → Feature Engineering → [Parallel Models] → Compare → Select/Ensemble

Step 1: 数据准备 + 特征工程
  模型: 参考 architecture_patterns/feature_engineering_pipeline.md
  输出: 特征矩阵 + 训练/验证切分(时序用时间切分)
  验证: 特征-目标相关性

Step 2: 并行模型训练
  模型: N个候选模型同时训练
        (ARIMA, XGBoost, RandomForest, LSTM, Prophet...)
  输出: N个训练好的模型
  管理: experiment_planner.md 批量实验框架

Step 3: 统一指标对比
  模型: 计算 RMSE/MAE/R² for each model
  输出: 多模型对比表(模型|RMSE|MAE|R²|排名|优势|劣势)
  模板: paper_integration/figure_table_rules.md 增补模板（仅思路参考；成稿表格以 standards/academic_table_standard.md 和锁定 table_spec.json 为准，不得自动加粗最优值或固定配额）

Step 4: 分析 + 选择/集成
  分析: 为什么A在某个指标上优于B?
  选择: Top-1 单模型 或 Top-3 ensemble
  集成: architecture_patterns/ensemble_stacking.md
```

---

## 管线选择决策

### 如何选择管线模板

```
输入 Problem Intelligence 的 Step 3 判定

├── 数学本质 = 时间序列预测 → 模板1: 纯预测管线
│   └── 平台: 多模型不确定最优 → 模板6: 多模型竞争对比
├── 数学本质 = 优化 → 模板2: 纯优化管线
├── 数学本质 = 综合评价 → 模板4: 评价管线
├── 数学本质 = 机理建模
│   ├── 有实测数据 → 模板3: 机理+数据混合管线
│   └── 无实测数据 → 模板3: 纯物理推演(跳过校准)
├── 数��本质 = 混合型
│   ├── 子问题独立 → 模板5: 分而治之管线
│   └── 嵌套依赖 → 组合使用: 先子管线A,输出→子管线B输入
└── 数学本质 = 网络模型 → 模板2变体: 图论优化管线
```

---

## 输入输出格式

### 输入 (来自 Problem Intelligence + Knowledge Router)

```json
{
  "problem_structure": {
    "math_essence": "mechanism_optimization",
    "sub_problems": [
      {"id": "Q1", "type": "mechanism", "depends_on": []},
      {"id": "Q2", "type": "optimization", "depends_on": ["Q1"]}
    ],
    "dependencies": "Q1 → Q2"
  },
  "candidate_models": {
    "Q1": ["ODE(Runge-Kutta)"],
    "Q2": ["参数优化(minimize)"]
  },
  "data_condition": {
    "has_real_data": true,
    "data_size": 50,
    "data_quality": "含噪声"
  }
}
```

### 输出: ModelingPipeline

```json
{
  "pipeline_name": "机理+参数优化混合管线",
  "template": "mechanism_then_optimize",
  "stages": [
    {
      "stage": 1,
      "name": "建立神经元ODE模型",
      "input": "题目物理参数(HH方程参数)",
      "model": "Runge-Kutta (scipy.integrate.solve_ivp)",
      "output": "神经元放电模拟结果",
      "validation": "改变步长收敛性检查, 与已知放电模式对比",
      "risk": "方程参数不完整, 需要文献补充"
    },
    {
      "stage": 2,
      "name": "DBS参数优化",
      "input": "Stage 1 的ODE模型 + 优化目标(治疗效果+副作用)",
      "model": "scipy.optimize.minimize (或 pymoo 多目标)",
      "output": "最优DBS参数(频率/脉宽/幅值)",
      "validation": "约束满足检查, 多初始点搜索避免局部最优",
      "risk": "ODE的数值稳定性影响优化收敛"
    }
  ],
  "end_to_end_validation": "模拟最优参数下的神经元响应, 与文献治疗效果对比",
  "global_risks": [
    "HH方程参数来自文献, 可能与具体患者不匹配",
    "忽略了神经元网络的突触连接效应"
  ]
}
```

---

## 与已有模块的关系

```
Problem Intelligence (20.2)
    │  输出: 问题结构 + 数学本质
    ▼
Knowledge Router (20.1)
    │  输出: 候选模型 + 知识文件 + 工具
    ▼
Strategy Planner (20.2.5)          ← 本文档
    │  输出: 分阶段建模管线
    ▼
agent_system/state_machine.md
    │  按管线阶段执行 S2→S3→S4→S5
    ▼
Competition Simulator (20.3)
    │  按管线模拟72小时竞赛
```
