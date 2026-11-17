# LaTeX 输出规范

> 论文最终输出为 LaTeX 时的格式要求

---

## 一、文档类与排版

```latex
\documentclass[12pt,a4paper]{article}
\usepackage[UTF8]{ctex}     % 中文支持
\usepackage{geometry}
\geometry{left=3.17cm, right=3.17cm, top=2.54cm, bottom=2.54cm}
\usepackage{amsmath, amssymb} % 数学公式
\usepackage{booktabs}         % 三线表
\usepackage{graphicx}         % 图片
\usepackage[sort&compress]{gbt7714} % GB/T 7714 参考文献
```

---

## 二、章节自动编号

| 层级 | LaTeX 命令 | 编号格式 |
|------|-----------|----------|
| 一级标题 | `\section{标题}` | 一、二、三... |
| 二级标题 | `\subsection{标题}` | 1.1, 1.2... |
| 三级标题 | `\subsubsection{标题}` | 1.1.1... |

---

## 三、公式自动编号

```latex
% 行内公式
$E = mc^2$

% 独立公式（自动编号）
\begin{equation}
  \min \quad c^T x
\end{equation}

% 多行公式（共享一个编号）
\begin{align}
  x + y &= 1 \\
  2x - y &= 3
\end{align}
```

---

## 四、图片自动引用

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.8\textwidth]{figures/prediction.png}
  \caption{图X 实际值与预测值对比}
  \label{fig:prediction}
\end{figure}

% 正文引用
如图\ref{fig:prediction}所示...
```

---

## 五、三线表

```latex
\begin{table}[htbp]
  \centering
  \caption{表X 模型参数估计结果}
  \label{tab:params}
  \begin{tabular}{lccc}
    \toprule
    参数 & 估计值 & 标准误 & p值 \\
    \midrule
    a    & 2.34   & 0.12   & <0.001 \\
    b    & 5.67   & 0.23   & <0.001 \\
    \bottomrule
  \end{tabular}
\end{table}
```

---

## 六、参考文献（GB/T 7714）

```latex
% 使用 gbt7714 宏包
\usepackage[sort&compress]{gbt7714}
\bibliographystyle{gbt7714-numerical}

% 引用
文献\cite{ref_key}研究了...

% 输出参考文献列表
\bibliography{references}
```

---

## 七、编译输出

```bash
# 推荐编译命令
latexmk -xelatex -shell-escape -file-line-error main.tex

# 最终输出
# main.pdf — 论文终稿
# main.synctex.gz — 反向搜索文件
```

---

## 八、与 python-docx 的对照

当前 `math-modeling-paper` Skill 使用 python-docx 直接生成 .docx。LaTeX 方案适用于需要严谨排版和数学公式的场合。

| 特性 | python-docx | LaTeX |
|------|------------|-------|
| 数学公式 | 文字表述为主 | 原生支持 |
| 自动编号 | 手动维护 | 自动 |
| 跨平台 | 中文兼容性依赖系统字体 | 跨平台一致 |
| 学习成本 | 低 | 中 |

**建议**：竞赛论文优先用 python-docx（快速出稿），学术期刊投稿用 LaTeX（格式严谨）。
