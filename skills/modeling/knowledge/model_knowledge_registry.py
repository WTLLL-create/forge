"""
Model Knowledge Registry v1.0 — 评价模型族 + 化学领域知识
=============================================================
Forge v7.4: 所有模型知识资产符合 knowledge_contract.schema.json。
可被 KnowledgeRouter 检索、ModelStrategyEngine 消费、PatternEngine 匹配。

四大模型资产:
  1. EntropyWeight — 熵权法
  2. TOPSIS — 逼近理想解排序法
  3. CRITIC — 准则间相关性权重法
  4. ReactionKinetics — 化学反应动力学领域知识
"""

KNOWLEDGE_BASE = {
    "entropy_weight": {
        "model_identity": {"name": "熵权法", "category": "evaluation", "aliases": ["EntropyWeight", "熵值法", "信息熵赋权"]},
        "problem_types": ["evaluation"],
        "input": {"data_requirement": "多指标评价矩阵, 样本≥5, 指标≥3, 正向化预处理"},
        "output": "各指标的客观权重向量 [w₁, w₂, ..., wₙ], ∑w=1",
        "mathematical_core": {
            "formula": "eⱼ = -k ∑ p_ij·ln(p_ij), dⱼ = 1 - eⱼ, wⱼ = dⱼ / ∑dⱼ",
            "steps": ["评价矩阵R → 标准化Z", "计算p_ij = z_ij / ∑z_ij", "计算熵值eⱼ", "计算差异系数dⱼ = 1-eⱼ", "归一化得权重wⱼ = dⱼ/∑dⱼ"],
        },
        "assumptions": ["数据可正向化", "指标间无结构性冗余", "样本量足够使p_ij统计意义成立"],
        "advantages": ["纯客观赋权 · 无主观偏见", "计算简单 · 结果可解释", "适合指标变异大的场景"],
        "limitations": ["不考虑指标间相关性 · 冗余指标可能过度赋权", "对极端值敏感", "不适用分类/预测题"],
        "failure_cases": ["样本<5时p_ij不稳定", "指标间高度相关(>0.8) → 冗余赋权", "与AHP混用导致权重矛盾"],
        "competition_pattern": {
            "trigger_conditions": ["客观数据充足", "需要纯定量赋权", "题目要求'客观评价'"],
            "typical_pairings": ["TOPSIS → 熵权-TOPSIS", "灰色关联 → 客观赋权+灰色评价"],
            "avoid_combinations": ["AHP (主客观权重冲突)", "线性回归 (不同范式)"],
        },
        "evidence_links": ["MODEL_SUPERIORITY", "SOLUTION_REPRODUCIBLE"],
        "related_models": ["TOPSIS", "CRITIC", "AHP"],
        "confidence": 0.92,
        "source_papers": ["2026D", "2016B", "2022C"],
    },

    "topsis": {
        "model_identity": {"name": "TOPSIS", "category": "evaluation", "aliases": ["逼近理想解排序法", "Technique for Order Preference"]},
        "problem_types": ["evaluation"],
        "input": {"data_requirement": "标准化评价矩阵 + 权重向量, 样本≥3, 指标≥2, 区分正向/负向"},
        "output": "方案排序: 从最优到最劣的相对贴近度 Cᵢ ∈ [0,1]",
        "mathematical_core": {
            "formula": "Cᵢ = D⁻ᵢ / (D⁺ᵢ + D⁻ᵢ), D⁺ = min_ideal, D⁻ = max_ideal",
            "steps": ["标准化矩阵", "加权标准化: v_ij = w_j · z_ij", "确定正理想解A⁺和负理想解A⁻", "计算欧氏距离D⁺和D⁻", "计算贴近度C = D⁻/(D⁺+D⁻)", "按C排序"],
        },
        "assumptions": ["指标单调性: 越大越好或越小越好", "指标间可加性", "权重已知"],
        "advantages": ["几何直观 · 可解释性强", "充分利用原始数据信息", "对样本数要求不高", "国赛评价题标配(占比>60%)"],
        "limitations": ["无法处理模糊指标", "权重敏感性高", "不考虑指标相关性"],
        "failure_cases": ["正负理想解定义错误", "权重不统一(主客观混用)", "与灰色关联混用但未区分场景"],
        "competition_pattern": {
            "trigger_conditions": ["评价/排序问题", "指标可量化", "需要明确方案对比"],
            "typical_pairings": ["熵权法 → 熵权-TOPSIS", "CRITIC → CRITIC-TOPSIS", "AHP → AHP-TOPSIS"],
            "avoid_combinations": ["随机森林 (不同范式)", "ARIMA (不同题型)"],
        },
        "evidence_links": ["MODEL_SUPERIORITY", "RESULT_ROBUST"],
        "related_models": ["EntropyWeight", "CRITIC", "AHP", "灰色关联分析"],
        "confidence": 0.95,
        "source_papers": ["2026D 77分", "2016B 75分", "2020D", "2021C"],
    },

    "critic": {
        "model_identity": {"name": "CRITIC", "category": "evaluation", "aliases": ["Criteria Importance Through Intercriteria Correlation", "准则间相关性赋权"]},
        "problem_types": ["evaluation"],
        "input": {"data_requirement": "标准化评价矩阵, 样本≥5, 指标≥3, 需计算标准差和相关系数"},
        "output": "各指标的客观权重, 综合考虑变异性 + 冲突性",
        "mathematical_core": {
            "formula": "Cⱼ = σⱼ · ∑(1 - rⱼₖ), wⱼ = Cⱼ / ∑Cⱼ",
            "steps": ["标准化矩阵", "计算各指标标准差σⱼ(变异性)", "计算指标间相关系数rⱼₖ", "计算信息量Cⱼ = σⱼ·∑(1 - rⱼₖ)", "归一化得权重"],
        },
        "assumptions": ["标准差反映信息量", "相关系数>0.8表示严重冗余"],
        "advantages": ["同时考虑变异性和冲突性 · 比熵权法更全面", "对冗余指标自动降权", "数学推导严谨"],
        "limitations": ["计算复杂度高于熵权(O(n²))", "对标准差为0的常量指标失效", "对样本分布有要求"],
        "failure_cases": ["常量指标(σ≈0)导致权重为0", "大维数(p>50)计算不稳定", "与主观权重简单加和"],
        "competition_pattern": {
            "trigger_conditions": ["指标间相关性显著(>0.6)", "需要区分冗余指标", "评价维度>5"],
            "typical_pairings": ["TOPSIS → CRITIC-TOPSIS", "PCA → CRITIC(PCA后)"],
            "avoid_combinations": ["熵权法(同一层面·可能冗余)"],
        },
        "evidence_links": ["MODEL_SUPERIORITY"],
        "related_models": ["EntropyWeight", "TOPSIS", "PCA"],
        "confidence": 0.88,
        "source_papers": ["2026D 核桃油", "2023A"],
    },

    "reaction_kinetics": {
        "model_identity": {"name": "化学反应动力学", "category": "domain_knowledge", "aliases": ["ReactionKinetics", "动力学模型", "Arrhenius方程"]},
        "problem_types": ["prediction", "optimization"],
        "input": {"data_requirement": "反应温度T、浓度c、时间t、反应速率r"},
        "output": "动力学参数: 速率常数k、活化能Ea、反应级数n; 预测方程: r = k·cₐⁿᵃ·c_bⁿᵇ",
        "mathematical_core": {
            "formula": "k = Ae^(-Ea/RT), r = k·c_A^α·c_B^β",
            "steps": ["实验设计: 改变温度/浓度t收集速率数据", "参数估计: 对数线性化 → 最小二乘拟合ln(k) vs 1/T", "活化能: Ea = -R·slope", "常数: A = e^intercept", "验证: 预测速率 vs 实验速率 R²"],
        },
        "assumptions": ["基元反应机制", "恒容/恒温条件可近似", "指前因子A与温度弱相关"],
        "advantages": ["物理含义明确 · Arrhenius方程广泛接受", "可用于外推其他温度下的速率", "与化工优化题直接对接"],
        "limitations": ["非基元反应需额外机理分析", "高压/极温下Arrhenius偏差", "需要足够实验数据拟合"],
        "failure_cases": ["扩散控制反应(非动力学限制)", "催化机理未考虑(表面反应)", "实验噪声大 → 参数估计不稳定"],
        "competition_pattern": {
            "trigger_conditions": ["化工反应题", "温度-速率数据", "催化剂筛选", "反应器设计"],
            "typical_pairings": ["非线性回归(参数估计)", "RSM响应面(实验设计)", "Tobit(有删失数据)"],
            "avoid_combinations": ["随机森林(数据少·物理含义弱)", "纯黑箱(评审不认可)"],
        },
        "evidence_links": ["MODEL_SUPERIORITY", "PROBLEM_ESSENCE"],
        "related_models": ["Arrhenius方程", "Langmuir-Hinshelwood", "Michaelis-Menten"],
        "confidence": 0.90,
        "source_papers": ["2026A 水泥窑排放", "2021B 乙醇偶合", "2020A 炉温曲线"],
    },
}
