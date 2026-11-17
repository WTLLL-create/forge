"""
案例4：机器学习建模前数据准备

问题背景：
   某电商平台需要预测用户年度消费金额。
   原始数据包含用户画像、行为指标，需要完整的数据准备管道：
   清洗 → 特征工程 → 编码 → 划分 → 输出模型就绪数据。

处理步骤：
   1. 加载原始数据（含缺失值/异常值/分类变量）
   2. 探索性分析
   3. 缺失值处理
   4. 特征工程（标准化/编码/特征构造）
   5. 特征选择（相关性分析）
   6. 训练/测试划分
   7. 输出 X_train, X_test, y_train, y_test (numpy array)
   8. 打印管道摘要（供论文使用）
"""
import pandas as pd
import numpy as np
from scipy import stats

print("=" * 60)
print("案例4：机器学习建模前数据准备")
print("=" * 60)

# ---- 1. 模拟用户数据 ----
rng = np.random.default_rng(42)
n = 500

df = pd.DataFrame({
    'user_id': range(1, n+1),
    'age': rng.normal(35, 12, n).astype(int),
    'income': rng.lognormal(mean=10.5, sigma=0.5, size=n).astype(int),
    'tenure_months': rng.integers(1, 60, n),        # 注册月数
    'logins_per_week': rng.poisson(3, n),             # 周登录次数
    'items_viewed': rng.poisson(20, n),               # 浏览商品数
    'cart_adds': rng.poisson(5, n),                   # 加购次数
    'orders': rng.poisson(2, n),                      # 下单次数
    'city_tier': rng.choice(['一线', '二线', '三线', '四线'], n,
                            p=[0.2, 0.3, 0.3, 0.2]),
    'gender': rng.choice(['M', 'F', np.nan], n, p=[0.45, 0.45, 0.1]),
    'annual_spend': rng.lognormal(mean=8.5, sigma=0.8, size=n),  # 目标变量
})

# 注入缺失值
mask = rng.random(n) < 0.08
df.loc[mask, 'income'] = np.nan
mask2 = rng.random(n) < 0.05
df.loc[mask2, 'age'] = np.nan

# 注入异常值
df.loc[10, 'logins_per_week'] = 999
df.loc[20, 'income'] = 99999999

print(f"\n【Step 1: 原始数据】")
print(f"  样本数: {n}")
print(f"  特征数: {len(df.columns) - 2}")  # 减去 user_id 和 target
print(f"  缺失值: {df.isnull().sum().sum()} 个")
print(f"\n{df.head(8).to_string()}")

# ---- 2. 探索性分析 ----
print(f"\n{'='*60}")
print(f"【Step 2: 探索性分析】")

print(f"\n  描述性统计:")
print(df.describe().round(1).to_string())

print(f"\n  分类变量分布:")
print(f"  city_tier:\n{df['city_tier'].value_counts()}")
print(f"  gender:\n{df['gender'].value_counts(dropna=False)}")

# ---- 3. 数据清洗 ----
print(f"\n{'='*60}")
print(f"【Step 3: 数据清洗】")

# 缺失值
for col in ['age', 'income']:
    before = df[col].isnull().sum()
    df[col] = df[col].fillna(df[col].median())
    print(f"  {col}: {before} 个缺失 → 中位数填充")

df['gender'] = df['gender'].fillna('Unknown')
print(f"  gender: 缺失 → 'Unknown' 类")

# 异常值
df['logins_per_week'] = df['logins_per_week'].clip(upper=30)
df['income'] = df['income'].clip(lower=10000, upper=500000)
df['age'] = df['age'].clip(lower=18, upper=80)
print(f"  异常值已截断处理")

# ---- 4. 特征工程 ----
print(f"\n{'='*60}")
print(f"【Step 4: 特征工程】")

# 构造复合特征
df['conversion_rate'] = df['orders'] / (df['items_viewed'] + 1)  # 转化率
df['cart_to_order'] = df['orders'] / (df['cart_adds'] + 1)       # 购物车转化
df['avg_order_value'] = df['annual_spend'] / (df['orders'] + 1)   # 客单价
df['engagement_score'] = (df['logins_per_week'] * 0.4 +
                          df['items_viewed'] * 0.3 +
                          df['cart_adds'] * 0.3)                  # 参与度评分

# log 变换（偏态特征）
df['income_log'] = np.log1p(df['income'])
df['annual_spend_log'] = np.log1p(df['annual_spend'])

# 编码分类变量
df_encoded = pd.get_dummies(df, columns=['city_tier', 'gender'],
                            drop_first=True, dtype=float)

print(f"  新构造特征: conversion_rate, cart_to_order, avg_order_value, engagement_score")
print(f"  log变换: income_log, annual_spend_log")
print(f"  One-Hot编码: city_tier, gender")
print(f"  特征总数: {len(df_encoded.columns)}")

# ---- 5. 特征选择 ----
print(f"\n{'='*60}")
print(f"【Step 5: 特征选择】")

# 排除ID列和目标变量（原始值），选择特征列
feature_cols = [c for c in df_encoded.columns
                if c not in ['user_id', 'annual_spend']]

X = df_encoded[feature_cols]
y = df_encoded['annual_spend_log']  # 使用 log 变换后的目标

# 相关性分析（与目标变量）
correlations = X.corrwith(y).abs().sort_values(ascending=False)
print(f"\n  特征与目标相关性 TOP 10:")
for feat, corr in correlations.head(10).items():
    print(f"    {feat}: r={corr:.3f}")

# 去除常数特征和低方差特征
variance = X.var()
constant_cols = variance[variance < 0.001].index.tolist()
if constant_cols:
    X.drop(columns=constant_cols, inplace=True)
    print(f"\n  已删除常数特征: {constant_cols}")

# 去除高相关特征对（|r| > 0.9）
corr_matrix = X.corr().abs()
upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
high_corr_cols = [col for col in upper_tri.columns
                  if any(upper_tri[col] > 0.9)]
if high_corr_cols:
    X.drop(columns=high_corr_cols, inplace=True)
    print(f"  已删除高相关特征: {high_corr_cols}")

print(f"  最终特征数: {X.shape[1]}")

# ---- 6. 训练/测试划分 ----
print(f"\n{'='*60}")
print(f"【Step 6: 训练/测试划分】")

# 简单随机划分（80/20）
n_train = int(len(X) * 0.8)
indices = rng.permutation(len(X))
train_idx = indices[:n_train]
test_idx = indices[n_train:]

X_train = X.iloc[train_idx].to_numpy(dtype=np.float64)
X_test = X.iloc[test_idx].to_numpy(dtype=np.float64)
y_train = y.iloc[train_idx].to_numpy(dtype=np.float64)
y_test = y.iloc[test_idx].to_numpy(dtype=np.float64)

print(f"  训练集: X_train {X_train.shape}, y_train {y_train.shape}")
print(f"  测试集: X_test {X_test.shape}, y_test {y_test.shape}")
print(f"  划分比例: {len(train_idx)}/{len(test_idx)} ({len(train_idx)/len(X)*100:.0f}/{len(test_idx)/len(X)*100:.0f})")

# ---- 7. 质量检查 ----
print(f"\n{'='*60}")
print(f"【Step 7: 质量检查】")

checks = {
    'X_train 无 NaN': not np.any(np.isnan(X_train)),
    'X_test 无 NaN': not np.any(np.isnan(X_test)),
    'y_train 无 NaN': not np.any(np.isnan(y_train)),
    'y_test 无 NaN': not np.any(np.isnan(y_test)),
    'X_train 无 Inf': not np.any(np.isinf(X_train)),
    'X_test 无 Inf': not np.any(np.isinf(X_test)),
}
all_pass = all(checks.values())
for check, result in checks.items():
    print(f"  {check}: {'✓' if result else '✗'}")

# ---- 8. 管道摘要（供论文使用） ----
print(f"\n{'='*60}")
print(f"【管道摘要 — 可直接用于论文数据预处理章节】")

print(f"""
数据预处理管道：
  1. 原始数据: {n} 样本, {len(df.columns)-1} 变量
  2. 缺失值: 中位数填充数值变量, 'Unknown'类填充分类变量
  3. 异常值: clip 截断处理
  4. 特征工程: 构造4个复合特征, log变换偏态特征, One-Hot编码
  5. 特征选择: 去除常数特征和高相关特征(|r|>0.9)
  6. 最终: {X.shape[1]} 个特征, 80/20 训练测试划分
""")

# 输出格式说明（连接 Numerical Computing Skill）
print(f"\n✅ 案例4完成：机器学习建模前数据准备")
print(f"   输出格式:")
print(f"     X_train: numpy.ndarray ({X_train.shape[0]}, {X_train.shape[1]})")
print(f"     y_train: numpy.ndarray ({y_train.shape[0]},)")
print(f"     → 可直接输入 scipy.optimize.curve_fit / sklearn 模型")
