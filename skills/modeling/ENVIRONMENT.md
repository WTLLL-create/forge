# 运行环境与依赖声明

核对日期：2026-09-09（与 verification_rerun 同日）。

## 已核实环境

| 环境 | Python | 用途 | 状态 |
|---|---|---|---|
| codex-primary-runtime | 3.12.14 | v9/v8 全量测试（188 项）与生产运行 | ✅ 全绿（1 个基线失败已于 2026-09-09 修复） |
| Doubao sandbox | 3.14.7 | 沙箱回归 | ✅ 补装 reportlab 5.0.1 / openpyxl 3.1.5 / pypdf 6.18.0 后与 3.12.14 结果一致 |

## 依赖清单

见 `requirements.txt`。核心测试依赖：python-docx、openpyxl、pypdf、numpy、pandas。
可选：scipy、matplotlib、PyMuPDF（仅示例/模板与 ai_usage_doc 的《AI工具使用详情.pdf》）。

## 已知缺口与处置

- **PyMuPDF（pymupdf）**：主环境 `codex-primary-runtime` 未安装。`submission/compilers/ai_usage_doc.py`
  生成《AI工具使用详情.pdf》依赖它（惰性导入，缺失时该编译器失败）。需要在提交前安装：
  `python -m pip install PyMuPDF`（安装软件按工作区规则需用户确认）。
- **scipy / matplotlib**：仅 data_processing / numerical_computing 的示例与模板使用，不进入核心测试链。

## 复现方式

```
cd skills/modeling
python -m pip install -r requirements.txt          # 核心 + 可选
python -m unittest discover -s tests/v9 -p "test_*.py"
python -m unittest discover -s tests/v8 -p "test_*.py"
```

## 说明

- 测试套件必须以 `unittest discover` 运行（tests/v9 与 tests/v8 非包，模块间存在同目录导入）。
- 默认 MinGW 自带的 Python 缺 python-docx 等依赖，不要作为运行解释器；使用
  codex-primary-runtime 依赖目录下的 python.exe（见 verification_rerun 记录）。
- 并行运行 v8 与 v9 套件安全：reference 项目测试已通过 `--runtime-root` 使用隔离目录。
