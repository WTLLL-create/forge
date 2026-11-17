# 时间对齐与多源融合模式

> 来源: 2026 B题 数模项目 (2026-07-29)
> 验证: 1 个项目 (B题) — 待第二个项目验证后升级

## 适用场景

多套传感器以不同频率、不同起始时间采集同一目标的轨迹/时间序列数据，需要统一到同一时间基准下进行融合。

## 四步流程

```
Step 1: 时间对齐     → CubicSpline 插值化连续 + MSE 搜索 dt*
Step 2: 偏差诊断     → 均值估计系统偏差 + t检验判断显著性
Step 3: 噪声估计     → 去偏后残差方差 → 用于 Kalman 参数
Step 4: 数据融合     → Kalman + SG 双重融合 + RMSE 对比验证
```

## Step 1: 时间对齐

```python
from scipy.interpolate import CubicSpline

# 插值化连续
cs1_x = CubicSpline(t1, x1)
cs2_x = CubicSpline(t2, x2)

# 定义误差函数
def trajectory_error(dt):
    ts = max(t1[0], t2[0] + dt)
    te = min(t1[-1], t2[-1] + dt)
    tv = np.linspace(ts, te, 500)
    return np.mean((cs1_x(tv) - cs2_x(tv - dt))**2)

# 两阶段搜���：粗 → 精
dt_coarse = np.linspace(-300, 300, 601)
errors = [trajectory_error(d) for d in dt_coarse]
dt_opt = dt_coarse[np.argmin(errors)]

for step in [1.0, 0.1, 0.01, 0.001]:
    fine = np.linspace(dt_opt - step*5, dt_opt + step*5, 201)
    dt_opt = fine[np.argmin([trajectory_error(d) for d in fine])]
```

**关键点：**
- 用 CubicSpline 而非线性插值：轨迹曲率大时线性插值误差显著
- 粗搜索步长 1s，精化到 0.001s
- 重叠时段需足够长（至少几十秒），否则 MSE 不可靠

## Step 2: 偏差诊断

```python
# 对齐后计算位置差
dx = x2_aligned - x1_aligned
bx = np.mean(dx)  # 系统偏差

# t检验判断偏差是否显著
from scipy import stats
t_stat, p_val = stats.ttest_1samp(dx, 0)
has_bias = (p_val < 0.05)

# 漂移分析
slope, intercept, r_value, p_value, std_err = stats.linregress(tv, dx)
drifting = (r_value**2 > 0.01)
```

**关键点：**
- 不默认有/无偏差，用统计检验说话
- 漂移 r² > 0.01 才视为显著（可调整阈值）

## Step 3: 噪声估计

```python
# 去偏后残差
dx_residual = dx - bx
sigma_x = np.std(dx_residual)
# X/Y 独立同方差假设下
R = np.diag([sigma_x**2 / 2, sigma_y**2 / 2])
```

## Step 4: 双重融合

```python
# 方法A: Kalman 滤波
F = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]])
H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
Q = np.diag([2.0, 2.0, 5.0, 5.0])

# 预测-更新循环
X = F @ X; P = F @ P @ F.T + Q
if has_observation:
    y_residual = Z - H @ X
    S = H @ P @ H.T + R
    K = P @ H.T @ np.linalg.inv(S)
    X = X + K @ y_residual
    P = (np.eye(4) - K @ H) @ P

# 方法B: SG 滤波
from scipy.signal import savgol_filter
x_sg = savgol_filter(x_avg, window_length=5, polyorder=2)

# RMSE 对比
rmse_kf = np.sqrt(np.mean((x_kf - x_ref)**2))
rmse_sg = np.sqrt(np.mean((x_sg - x_ref)**2))
```

**关键点：**
- Kalman 利用噪声统计，SG 不依赖噪声模型，两者互补
- RMSE 对比验证各自有效性
- 在信噪比较差时，SG 增益可能更大

## 经验规则

| 条件 | 建议 |
|------|------|
| 重叠时段 > 100s | MSE 搜索可靠 |
| 重叠时段 < 30s | 搜索结果需谨慎，考虑加先验 |
| 实测数据 | 必须先做 t检验 + 漂移分析 |
| 噪声较大时 | SG 可能优于 Kalman |
| 高频噪声为主 | Kalman 可能优于 SG |
