# GitHub 参考源 — 论文生成系统

> 阶段 14 — 论文自动生成系统的 GitHub 调研

---

## 一、ElegantLaTeX/ElegantPaper

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/ElegantLaTeX/ElegantPaper |
| **Stars** | ~1,500 |
| **维护** | 2026年重新恢复维护（56 commits） |
| **定位** | 中文工作论文 LaTeX 模板 |
| **核心** | 基于 article 类，专为经济学工作论文设计 |
| **贡献** | 章节结构规范、公式/图表环境、参考文献格式 → `section_generation_rules.md` |

---

## 二、ustcthesis/ustcthesis

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/ustcthesis/ustcthesis |
| **Stars** | ~1,500 |
| **维护** | 活跃 |
| **定位** | 中科大学位论文 LaTeX 模板 |
| **核心** | 学术论文规范：自动编号、目录生成、引用管理 |
| **贡献** | 论文结构规范化、自动编号体系 → `latex_output_rules.md` |

---

## 三、jupyter/nbconvert

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/jupyter/nbconvert |
| **Stars** | ~1,700 |
| **维护** | 活跃（v7.17.1, 2026-04） |
| **定位** | Jupyter Notebook → HTML/LaTeX/PDF 转换 |
| **核心** | Notebook 实验记录 → 多种输出格式的自动转换管道 |
| **贡献** | 实验结果→报告生成的自动化思想 → `result_to_content_rules.md` |

---

## 四、matplotlib/matplotlib

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/matplotlib/matplotlib |
| **Stars** | ~23,000 |
| **维护** | 极高活跃 |
| **定位** | Python 论文级绘图标准库 |
| **核心** | 高 DPI 输出、完整图表元素控制（标题/轴标签/图例/色图） |
| **贡献** | 图表输出规范（DPI/尺寸/字体）→ `figure_table_rules.md` |

---

## 五、plotly/plotly.py

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/plotly/plotly.py |
| **Stars** | ~16,700 |
| **维护** | 极高活跃 |
| **定位** | 交互式数据可视化 |
| **核心** | 探索性分析阶段的交互图表（不用于正式论文输出） |
| **贡献** | EDA 阶段的可视化工具推荐 → `figure_table_rules.md` EDA 部分 |

---

## 六、quarto-dev/quarto-cli

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/quarto-dev/quarto-cli |
| **Stars** | ~4,200 |
| **维护** | 极高活跃（v1.11, 20,582 commits） |
| **定位** | 基于 Pandoc 的科学/技术出版系统 |
| **核心** | Markdown→PDF/HTML/Word，集成 Jupyter/Knitr，交叉引用自动化 |
| **贡献** | 可重复研究 pipeline、代码+数据+文本一体化 → `latex_output_rules.md` |

---

## 七、citation-style-language/styles

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/citation-style-language/styles |
| **Stars** | ~3,500 |
| **维护** | 活跃 |
| **定位** | 参考文献格式标准库（GB/T 7714, APA, MLA 等） |
| **核心** | 标准化的引用格式定义 |
| **贡献** | 参考文献格式规范 → `latex_output_rules.md` 引用部分 |

---

## 八、microsoft/markitdown

| 属性 | 内容 |
|------|------|
| **地址** | https://github.com/microsoft/markitdown |
| **Stars** | ~35,000 |
| **维护** | 极高活跃 |
| **定位** | 多格式文档到 Markdown 的转换工具 |
| **核心** | PDF/Word/PPT→Markdown 的通用转换 |
| **贡献** | 反向转换通道（题目文件→结构化内容提取） |

---

## 汇总

| 仓库 | Stars | 贡献的系统文件 |
|------|-------|--------------|
| ElegantPaper | ~1.5k | section_generation_rules.md |
| ustcthesis | ~1.5k | latex_output_rules.md |
| nbconvert | ~1.7k | result_to_content_rules.md |
| matplotlib | ~23k | figure_table_rules.md |
| plotly | ~16.7k | figure_table_rules.md (EDA) |
| quarto-cli | ~4.2k | latex_output_rules.md |
| csl-styles | ~3.5k | latex_output_rules.md (引用) |
| markitdown | ~35k | 题目文件内容提取 |
