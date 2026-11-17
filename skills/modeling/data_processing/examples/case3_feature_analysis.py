"""
案例3：多指标探索性分析 — 城市综合评估

问题背景：
   20个城市的多维度指标（经济、环境、交通、教育、医疗），
   需要进行探索性数据分析：分布特征、变量关系、综合评分。

处理步骤：
   1. 数据加载与类型检查
   2. 单变量分布分析
   3. 相关性矩阵
   4. Z-score 标准化
   5. 综合评分（加权求和）
   6. 排名与输出
"""
import pandas as pd
import numpy as np
from scipy import stats

print("=" * 60)
print("案例3：多指标探索性分析 — 城市综合评估")
print("=" * 60)

# ---- 1. 模拟20个城市的多维数据 ----
rng = np.random.default_rng(42)
cities = [f'城市{i:02d}' for i in range(1, 21)]

df = pd.DataFrame({
    'city': cities,
    'gdp_per_capita': rng.normal(80000, 25000, 20),        # 人均GDP(元)
    'air_quality': rng.normal(70, 20, 20),                  # 空气质量指数(越低越好)
    'green_coverage': rng.normal(40, 8, 20),                # 绿化覆盖率(%)
    'public_transport': rng.normal(60, 15, 20),             # 公共交通分担率(%)
    'education_index': rng.normal(75, 10, 20),              # 教育指数
    'healthcare_beds': rng.normal(6, 2, 20),                # 每千人医疗床位数
})

# 注入一些缺失值和异常值（模拟真实数据）
df.loc[3, 'gdp_per_capita'] = np.nan
df.loc[7, 'air_quality'] = np.nan
df.loc[12, 'education_index'] = np.nan
df.loc[15, 'gdp_per_capita'] = 300000  # 异常高值
df.loc[18, 'air_quality'] = 5          # 异常低值

print(f"\n【Step 1: 数据概览】")
print(f"  城市数: {len(df)}")
print(f"  指标数: {len(df.columns) - 1}")
print(f"  缺失值: {df.isnull().sum().sum()} 个")

# ---- 2. 数据质量检查 ----
print(f"\n{'='*60}")
print(f"【Step 2: 数据质量检查】")

for col in df.columns[1:]:
    na_count = df[col].isnull().sum()
    if na_count > 0:
        print(f"  {col}: {na_count} 个缺失")

# 异常值检查（IQR方法）
for col in ['gdp_per_capita', 'air_quality', 'education_index']:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    out = df[(df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)]
    if len(out) > 0:
        print(f"  {col}: {len(out)} 个异常值 "
              f"(范围 [{Q1-1.5*IQR:.0f}, {Q3+1.5*IQR:.0f}])")

# ---- 3. 数据清洗 ----
print(f"\n{'='*60}")
print(f"【Step 3: 数据清洗】")

# 缺失值填充
for col in ['gdp_per_capita', 'air_quality', 'education_index']:
    df[col] = df[col].fillna(df[col].median())

# 异常值截断（保留数据）
df['gdp_per_capita'] = df['gdp_per_capita'].clip(
    lower=30000, upper=180000)
df['air_quality'] = df['air_quality'].clip(
    lower=10, upper=130)
print(f"  缺失值+异常值已处理")

# ---- 4. 描述性统计 ----
print(f"\n{'='*60}")
print(f"【Step 4: 描述性统计】")

desc = df.describe().round(1)
print(desc.to_string())

# ---- 5. 相关性分析 ----
print(f"\n{'='*60}")
print(f"【Step 5: 指标间相关性】")

indicator_cols = [c for c in df.columns if c != 'city']
corr_matrix = df[indicator_cols].corr().round(3)
print(corr_matrix)

# 找出强相关对
print(f"\n  强相关对 (|r| > 0.3):")
for i in range(len(indicator_cols)):
    for j in range(i+1, len(indicator_cols)):
        r = corr_matrix.iloc[i, j]
        if abs(r) > 0.3:
            print(f"    {indicator_cols[i]} ↔ {indicator_cols[j]}: r={r:.3f}")

# ---- 6. 标准化 + 综合评分 ----
print(f"\n{'='*60}")
print(f"【Step 6: 标准化与综合评分】")

# Z-score 标准化
df_z = df.copy()
for col in indicator_cols:
    df_z[col] = stats.zscore(df[col])

# 方向处理：air_quality 越低越好→取负
df_z['air_quality'] = -df_z['air_quality']

# 加权综合评分
weights = {
    'gdp_per_capita': 0.20,
    'air_quality': 0.15,
    'green_coverage': 0.15,
    'public_transport': 0.15,
    'education_index': 0.20,
    'healthcare_beds': 0.15,
}
df['综合得分'] = sum(df_z[col] * w for col, w in weights.items())

# 排名
df['排名'] = df['综合得分'].rank(ascending=False).astype('Int64')
df_sorted = df.sort_values('综合得分', ascending=False)

print(f"\n  TOP 5 城市:")
top5 = df_sorted[['city', '综合得分', '排名']].head(5).round(2)
print(top5.to_string(index=False))

print(f"\n  BOTTOM 5 城市:")
bottom5 = df_sorted[['city', '综合得分', '排名']].tail(5).round(2)
print(bottom5.to_string(index=False))

# ---- 7. 输出 ----
print(f"\n{'='*60}")
print(f"【Step 7: 输出建模就绪数据】")

X = df_z[indicator_cols].to_numpy(dtype=np.float64)
print(f"  标准化特征矩阵 X: {X.shape}")
print(f"  可喂给: PCA (numpy.linalg.eig) / 聚类 (scipy.cluster) / 优化")

print(f"\n✅ 案例3完成：多指标探索性分析")
print(f"   处理: 缺失→异常→标准化→相关性→综合评分")
print(f"   输出: numpy.ndarray ({X.shape[0]}城市, {X.shape[1]}指标)")
