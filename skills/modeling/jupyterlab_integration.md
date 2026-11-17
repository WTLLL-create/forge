# JupyterLab 参考 — 数模实验环境

> 来源：jupyterlab/jupyterlab（GitHub 15k+ stars, BSD-3-Clause）
> 蒸馏自官方 README + 社区最佳实践
> 服务于全状态机的交互式开发环境

---

## 一、定位

JupyterLab 是数模项目的**实验环境**和**论文模板调试台**。它不直接参与 S0→S8 流程中的决策，但提供了：
- Python 代码的即时交互执行
- 数据可视化的所见即所得
- Markdown + LaTeX 混合写作
- 多窗口布局（左边代码、右边图表/文档）

---

## 二、核心概念

### 2.1 Cell 类型

| 类型 | 用途 | 快捷键切换 |
|------|------|:---:|
| **Code** | 执行 Python 代码，显示输出 | `Y` |
| **Markdown** | 写笔记、公式、文档 | `M` |
| **Raw** | 原始文本（不被处理） | `R` |

### 2.2 两种模式

| 模式 | 进入方式 | 单元格边框 | 能做什么 |
|------|----------|:---:|----------|
| **命令模式** | `Esc` | 灰色/蓝色 | 操作单元格（增删移动改类型） |
| **编辑模式** | `Enter` / 双击 | 绿色 | 编辑内容（写代码/文档） |

---

## 三、必知快捷键

### 运行

| 操作 | 快捷键 |
|------|--------|
| 运行当前Cell，跳到下一个 | `Shift + Enter` |
| 运行当前Cell，不移动 | `Ctrl + Enter` |
| 运行当前Cell，下方插入新Cell | `Alt + Enter` |
| 中断运行 | 按两次 `I` |

### 单元格操作（命令模式）

| 操作 | 快捷键 |
|------|--------|
| 上方插入Cell | `A` |
| 下方插入Cell | `B` |
| 删除Cell | 按两次 `D` |
| 撤销删除 | `Z` |
| 合并选中Cell | `Shift + M` |
| 剪切/复制/粘贴 | `X` / `C` / `V` |

### 类型切换（命令模式）

| 操作 | 快捷键 |
|------|--------|
| 转 Code | `Y` |
| 转 Markdown | `M` |
| 转 Raw | `R` |
| 设标题 1-6 | `1` ~ `6` |

### 导航与编辑

| 操作 | 快捷键 |
|------|--------|
| 打开命令面板 | `Ctrl + Shift + C` |
| 切换左侧栏 | `Ctrl + B` |
| 代码补全 | `Tab` |
| 查看函数文档 | `Shift + Tab`（在函数名上） |
| 注释/取消注释 | `Ctrl + /` |
| 多光标编辑 | `Alt + 点击` |
| 保存 | `Ctrl + S` |

---

## 四、Magic Commands（魔术命令）— 数模高效利器

### 行魔术 (%)

```python
%timeit sum(range(10000))          # 测量执行时间
%matplotlib inline                  # 图表内嵌显示
%load_ext autoreload                # 自动重载外部模块
%autoreload 2
%who                               # 列出当前变量
%whos                              # 带详情
%reset -f                          # 清空所有变量
%pwd                               # 当前工作目录
%ls                                # 列出文件
```

### 单元魔术 (%%)

```python
%%time
# 测量整个 cell 的执行时间
result = expensive_function()

%%writefile my_script.py
# 将 cell 内容写入文件
import numpy as np

%%bash
# 执行 bash 命令
pip list | grep numpy
```

### Shell 交互（`!` 前缀）

```python
!pip install pandas scipy scikit-learn  # 安装包
!python my_script.py                    # 运行外部脚本
files = !ls *.csv                       # 捕获 shell 输出到变量
```

---

## 五、界面布局 — 数模最佳实践

```
┌──────────────┬────────────────────────────────────┐
│ 左侧边栏      │  主工作区                            │
│              │                                    │
│ 📁 文件浏览器  │  ┌─────────────┐  ┌──────────────┐ │
│              │  │ Notebook    │  │ 数据表格      │ │
│ 🔴 运行内核   │  │ (代码+文档)  │  │ (df.head())  │ │
│              │  │             │  │              │ │
│ 📑 目录      │  └─────────────┘  └──────────────┘ │
│              │                                    │
│ 🔌 扩展      │  ┌────────────────────────────────┐ │
│              │  │ Matplotlib 图表输出             │ │
│              │  └────────────────────────────────┘ │
└──────────────┴────────────────────────────────────┘
```

**拖拽标签页**可实现分屏布局（代码 + 图表并排）

---

## 六、数模实验工作流（在 JupyterLab 中）

### 阶段 1：数据探索（S3）

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_csv('data.csv')

# 快速概览
df.head()
df.info()
df.describe()

# 可视化
df.hist(figsize=(12, 8))
plt.tight_layout()

# 相关性热力图
import seaborn as sns
sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
```

### 阶段 2：建模实验（S4）

```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error

# 准备数据
X = df[feature_cols].to_numpy()
y = df[target_col].values
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# 标准化 + 建模
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train_s, y_train)

# 评估
y_pred = model.predict(X_test_s)
print(f"R²: {r2_score(y_test, y_pred):.4f}")
print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}")

# 真实 vs 预测散点图
plt.scatter(y_test, y_pred, alpha=0.5)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
plt.xlabel('真实值')
plt.ylabel('预测值')
```

### 阶段 3：生成论文素材（S6）

```python
# Markdown Cell 中写论文草稿
# 支持 LaTeX 公式: $E = mc^2$
# 支持图片: ![图表](figure.png)
```

---

## 七、扩展推荐（数模相关）

| 扩展 | 用途 |
|------|------|
| `jupyterlab-git` | Git 版本控制 |
| `jupyterlab-toc` | 自动生成目录 |
| `jupyterlab-spreadsheet` | CSV/Excel 可视化编辑 |
| `jupyterlab-variableInspector` | 变量查看器（类似 Spyder/RStudio） |
| `jupyter-matplotlib` | 增强图表交互 |
| `ipywidgets` | 交互式控件 |

---

## 八、性能与调试

```python
# 自动重载外部 .py 文件（改了代码不用重启 kernel）
%load_ext autoreload
%autoreload 2

# 调试
%debug              # 进入上一条错误的调试器
%pdb on             # 自动进入调试器

# 查看源码
??model.fit          # 两个问号显示源码

# 内存使用
%memit result = expensive_function()
```

---

## 九、从 JupyterLab 到最终脚本

数模开发模式：

```
JupyterLab (实验)  →  .py 脚本 (自动化)  →  论文生成
     ↑                                            ↓
  数据探索、可视化、试错               skills/modeling/ S0→S8 流程
```

最佳实践：
1. 在 JupyterLab 中**探索数据、尝试模型、调参**
2. 确认方案后**将代码抽取为 .py 脚本**
3. 将脚本集成到 skills/modeling/ 的状态机流程中
4. 最终论文生成走 S6 (PAPER) 自动化流程

```python
# JupyterLab 中保存当前导出的方式
%%writefile model_solution.py
# 将下面所有代码保存为独立脚本
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
# ... 完整代码
```

---

## 十、安装与启动

```bash
# 安装
pip install jupyterlab
# 或
conda install -c conda-forge jupyterlab

# 启动（在项目根目录）
jupyter lab

# 指定端口
jupyter lab --port=8889

# 无浏览器模式（远程服务器）
jupyter lab --no-browser --port=8889
```

---

## 十一、与其他组件的集成

```
JupyterLab
  ├── Pandas (data_processing/pandas_integration.md)
  │    数据读取、清洗、groupby、时序处理
  ├── SciPy (numerical_computing/scipy_integration.md)
  │    优化、积分、ODE、统计检验
  ├── scikit-learn (models/sklearn_integration.md)
  │    预处理 Pipeline、模型训练、CV、调参
  └── 输出 → .py 脚本 → skills/modeling/ 状态机 → 论文 .docx
```
