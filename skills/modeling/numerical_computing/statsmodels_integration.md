# statsmodels 完整参考 — 数模统计建模与时序诊断

> 来源：statsmodels/statsmodels（GitHub ~11.5k stars, BSD-3）
> 蒸馏自官方 API 文档
> 服务于 S4/S5 统计检验 + 时序分析

---

## 一、定位

```
SciPy.stats  → 快速单变量检验
statsmodels  → 完整统计建模框架：回归表/时序诊断/假设检验全套
```

核心价值：提供 **R 语言级别的回归摘要表** 和 **完整时序诊断工具链**。

```
安装：pip install statsmodels
```

---

## 二、回归分析 — 论文回归表

### OLS 普通最小二乘

```python
import statsmodels.api as sm
import numpy as np

# 准备数据（必须手动加截距列）
X = sm.add_constant(X_data)  # 添加截距
model = sm.OLS(y, X)
results = model.fit()

# R 风格的完整回归摘要表（论文直接截图）
print(results.summary())
# 输出：
#   R-squared, Adj.R-squared, F-statistic, Prob(F)
#   每个变量的 coef, std err, t, P>|t|, [0.025, 0.975]
```

### 公式接口（更直观）

```python
import statsmodels.formula.api as smf
import pandas as pd

# 直接写公式，DataFrame 列名作变量
model = smf.ols('y ~ x1 + x2 + x3', data=df)
results = model.fit()
print(results.summary())

# 提取关键数字
print(f"R² = {results.rsquared:.4f}")
print(f"F = {results.fvalue:.2f}, p = {results.f_pvalue:.4f}")
```

### 多元回归论文输出模板

```python
results = smf.ols('排放 ~ 温度 + 压力 + 流量', data=df).fit()
print(results.summary())

# 论文叙述：
# "OLS 回归结果显示，模型整体显著（F={:.2f}, p<0.001, R²={:.4f}）。
# 温度的回归系数为 {:.4f}（p={:.4f}），压力为 {:.4f}（p={:.4f}），
# 流量为 {:.4f}（p={:.4f}）。"
```

---

## 三、时序分析 — 数模预测题必备

### 平稳性检验

```python
from statsmodels.tsa.stattools import adfuller

# ADF 检验：H0 = 非平稳
result = adfuller(series)
print(f'ADF 统计量: {result[0]:.4f}')
print(f'p 值: {result[1]:.4f}')
# p < 0.05 → 拒绝 H0 → 序列平稳

if result[1] > 0.05:
    # 做差分
    series_diff = series.diff().dropna()
```

### ACF / PACF（定阶）

```python
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# 自相关图（定 MA 阶数 q）
plot_acf(series, lags=30)
# PACF 截尾在第 q 个 → MA(q)

# 偏自相关图（定 AR 阶数 p）
plot_pacf(series, lags=30)
# ACF 截尾在第 p 个 → AR(p)
```

### 季节性分解

```python
from statsmodels.tsa.seasonal import seasonal_decompose

result = seasonal_decompose(series, model='additive', period=12)
result.trend      # 趋势
result.seasonal   # 季节性
result.resid      # 残差
result.plot()     # 四合一图（论文可直接用）
```

### ARIMA/SARIMA 建模

```python
from statsmodels.tsa.arima.model import ARIMA

# ARIMA(p,d,q)
model = ARIMA(series, order=(2, 1, 2))
results = model.fit()
print(results.summary())

# 预测
forecast = results.forecast(steps=30)  # 未来30步

# SARIMA(p,d,q)(P,D,Q,s)
model = ARIMA(series, order=(2,1,2), seasonal_order=(1,1,1,12))
```

---

## 四、统计检验

```python
# 线性假设检验（如检验 β1 = β2）
results.t_test('x1 = x2')
results.f_test('x1 = 0, x2 = 0')

# Q-Q 图（残差正态性）
import statsmodels.api as sm
sm.qqplot(results.resid, line='45')
```

---

## 五、数模论文时序诊断完整流程

```python
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima.model import ARIMA

# 1. 平稳性检验
adf = adfuller(series)
print(f"ADF p-value: {adf[1]:.4f} → {'平稳' if adf[1] < 0.05 else '不平稳，做差分'}")

# 2. 季节性分解
decomp = seasonal_decompose(series, model='additive', period=7)
decomp.plot()

# 3. 定阶
plot_acf(series_diff, lags=20)
plot_pacf(series_diff, lags=20)

# 4. 建模
model = ARIMA(series, order=(p, d, q))
results = model.fit()
print(results.summary())

# 5. 预测
forecast = results.forecast(steps=30)
```

---

## 六、常见坑位

| 坑 | 现象 | 解决 |
|----|------|------|
| OLS 忘记加截距 | R² 异常 | `sm.add_constant(X)` |
| 时序不平稳就建模 | ARIMA 不收敛 | 先 ADF 检验，不平稳先差分 |
| period 设错 | 季节性分解失败 | 日数据 period=7，月数据 period=12 |
| ACF/PACF 不会读 | 定阶错误 | PACF 截尾→AR(p)，ACF 截尾→MA(q) |
| 残差未做白噪声 | 模型不可用 | 残差 Ljung-Box 检验 p>0.05 |
