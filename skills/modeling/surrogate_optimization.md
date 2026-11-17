# Surrogate + NSGA-II 优化 Skill

**日期**：2026-07-15 | **来源**：memory/patterns/surrogate_nsga2_workflow.md 升级
**适用范围**：有历史数据但无解析模型的工业过程控制参数优化

## 快速开始
1. 从 memory/patterns/math_modeling_pipeline.md 复制模板目录
2. 填充 config.py (DATA_PATH, N_CLUSTER, RF_TREE, POP_SIZE, N_GEN)
3. 实现 Problem 类 (单目标+约束 n_constr=1 或双目标 n_constr=0)
4. _evaluate 中必须向量化: `np.tile(condition, (n,1))` + 批量 predict
5. 结果从 res.pop.get("F"/"X"/"G") 提取 (pymoo 0.6.2 坑)

## 单目标 vs 双目标
- 单目标+约束: 适合有明确排放上限的场景 (如 Q2)
- 双目标无约束: 适合研究标准收紧影响 (如 Q4)
- 注意: 若数据存在删失, 双目标的排放维度无分辨性 → 改单目标或物理模型

## 前置检查清单
- [ ] 目标分布检查: 有无删失/截断? (→ memory/mistakes/data_censorship_surrogate.md)
- [ ] pymoo 版本: 0.6.2 的 Result.F 为 None (→ memory/mistakes/pymoo_result_f_is_null.md)
- [ ] sys.path: 子目录先于父目录, 避免同名覆盖 (→ memory/mistakes/python_module_shadowing.md)
- [ ] config.py: UTF-8 无 BOM (→ memory/mistakes/config_encoding.md)

## 参数建议
| 参数 | 单目标 | 双目标 |
|------|--------|--------|
| POP_SIZE | 40-60 | 80-120 |
| N_GEN | 60-80 | 100-150 |
| RF_TREE | 100 | 100 |
| N_CLUSTER | 3-5 (肘部法) | 复用 Q2 |
