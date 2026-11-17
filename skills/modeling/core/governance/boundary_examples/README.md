# boundary_examples/ — SkillBoundary 验证样本

> 这 4 个 YAML 文件是 skill_boundary.schema.json v1.0 的首批验证样本。
> 选择 A 类 4 技能是因为它们完成度 >= 7 且调用价值 high，
> 可以真正被 Invocation Gate 拦截调用——不是为了演示而写的假数据。

## 验证样本清单

| 文件 | 技能 | 状态 | 关键验证点 |
|------|------|:---:|------|
| `argument_compiler.yaml` | 论据编译器 | active | 3 must-call 意图 + 2 avoid-call 排除；upstream=expert_decision |
| `model_specification.yaml` | 模型规格化器 | active | 33% 模板覆盖率的 known_gaps；cross-domain capability |
| `quality_gate.yaml` | 论文质量门禁 | active | P0/P1/P2 三级检查；confidence_threshold=0.85 最高 |
| `validation_plan.yaml` | 验证规划编译器 | partial | HELD 状态；system-level trigger pattern；known_gaps 记录了 RUN_002 等待 |

## 如何使用

1. **验证 Schema**：`jsonschema.validate(boundary_yaml, skill_boundary.schema.json)` 确保格式正确
2. **测试 Gate 逻辑**：用这 4 个 boundary 的数据跑 must-call/avoid-call 测试（见 Wave 1 Step 1.5）
3. **扩展**：B/C 类技能补齐后，参照这 4 个样本的格式增加新的 boundary YAML

## 与 skill_runtime_registry.yaml 的关系

- `skill_runtime_registry.yaml` 是现有的运行时状态注册（含 trigger 的自然语言描述）
- `boundary_examples/*.yaml` 是新的结构化边界定义（符合 skill_boundary.schema.json）
- Wave 1 完成后，两个注册表将合并：runtime_registry 中的 trigger 字段升级为 boundary 块
