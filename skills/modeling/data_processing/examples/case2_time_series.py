"""
案例2：城市指标时间序列分析

问题背景：
   5个城市2018-2025年的季度经济指标数据（GDP增速、CPI、失业率、PMI），
   需要处理时间序列格式、计算统计特征、发现趋势和城市间差异。

处理步骤：
   1. 长格式→宽格式转换
   2. 时间索引设置
   3. 重采样与滚动计算
   4. 城市间横向对比
   5. 输出建模就绪数据
"""
import pandas as pd
import numpy as np

print("=" * 60)
print("案例2：城市指标时间序列分析")
print("=" * 60)

# ---- 1. 模拟数据 ----
rng = np.random.default_rng(42)
cities = ['北京', '上海', '广州', '深圳', '成都']
dates = pd.date_range('2018-01-01', '2025-12-31', freq='QE')

# 生成长格式数据（含趋势+噪声+城市特性）
records = []
for city in cities:
    base_gdp = {'北京': 6.5, '上海': 6.3, '广州': 6.0, '深圳': 7.0, '成都': 7.5}[city]
    base_cpi = {'北京': 2.3, '上海': 2.5, '广州': 2.0, '深圳': 2.2, '成都': 2.8}[city]

    for d in dates:
        trend_factor = 1 - (d.year - 2018) * 0.02  # 微弱下行趋势
        records.append({
            'date': d,
            'city': city,
            'gdp_growth': base_gdp * trend_factor + rng.normal(0, 0.3),
            'cpi': base_cpi + rng.normal(0, 0.15),
            'unemployment': 4.0 + rng.normal(0, 0.2),
            'pmi': 50 + rng.normal(0, 1.5)
        })

df = pd.DataFrame(records)
print(f"\n【原始数据（长格式）】")
print(f"  形状: {df.shape}")
print(f"  城市: {df['city'].unique().tolist()}")
print(f"  时间范围: {df['date'].min()} ~ {df['date'].max()}")
print(f"\n{df.head(10).to_string()}")

# ---- 2. 时间序列处理 ----
print(f"\n{'='*60}")
print(f"【Step 2: 时间序列格式化】")

df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)
df.sort_index(inplace=True)

print(f"  索引频率: {df.index.inferred_freq}")

# ---- 3. 多城市重采样与滚动计算 ----
print(f"\n{'='*60}")
print(f"【Step 3: 重采样与滚动计算】")

# 每个城市的年度均值
annual = df.groupby('city').resample('YE').mean(numeric_only=True)
print(f"\n  年度均值 (北京):")
beijing_annual = annual.loc['北京'].round(2)
print(beijing_annual)

# 4季度移动平均（平滑）
df['gdp_ma4'] = df.groupby('city')['gdp_growth'].transform(
    lambda x: x.rolling(window=4, min_periods=2).mean()
)
print(f"\n  移动平均 (前几行):")
print(df[['city', 'gdp_growth', 'gdp_ma4']].head(10).round(2).to_string())

# 同比变化
df['gdp_yoy'] = df.groupby('city')['gdp_growth'].transform(
    lambda x: x.pct_change(periods=4) * 100
)

# ---- 4. 城市横向对比 ----
print(f"\n{'='*60}")
print(f"【Step 4: 城市间横向对比】")

city_stats = df.groupby('city').agg(
    GDP增速均值=('gdp_growth', 'mean'),
    GDP增速标准差=('gdp_growth', 'std'),
    CPI均值=('cpi', 'mean'),
    失业率均值=('unemployment', 'mean'),
    PMI均值=('pmi', 'mean')
).round(2)

print(city_stats)

# 排序：GDP增速最高的城市
top_city = city_stats['GDP增速均值'].idxmax()
print(f"\n  GDP增速最高: {top_city} ({city_stats.loc[top_city, 'GDP增速均值']:.2f}%)")

# ---- 5. 相关性分析 ----
print(f"\n{'='*60}")
print(f"【Step 5: 指标相关性】")

corr = df[['gdp_growth', 'cpi', 'unemployment', 'pmi']].corr().round(3)
print(corr)

# 输出关键发现
print(f"\n  关键发现:")
print(f"    GDP增速与失业率相关系数: {corr.loc['gdp_growth', 'unemployment']:.3f}")
print(f"    GDP增速与PMI相关系数: {corr.loc['gdp_growth', 'pmi']:.3f}")

# ---- 6. 输出建模就绪数据 ----
print(f"\n{'='*60}")
print(f"【Step 6: 输出建模就绪数据】")

# 选择特征列，输出为 numpy
feature_cols = ['gdp_growth', 'cpi', 'unemployment', 'pmi', 'gdp_ma4']
model_data = df[feature_cols].dropna()

X = model_data.to_numpy(dtype=np.float64)
print(f"  特征矩阵 X: {X.shape} (n_samples, n_features)")
print(f"  特征列: {feature_cols}")
print(f"  可喂给: scipy.optimize / numpy.linalg / sklearn")

print(f"\n✅ 案例2完成：城市指标时间序列分析")
print(f"   处理: 长格式→时间索引→重采样→滚动→横向对比→相关性")
print(f"   输出: numpy.ndarray ({X.shape[0]}, {X.shape[1]})")
