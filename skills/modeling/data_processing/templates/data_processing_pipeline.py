"""
数据预处理通用管道模板

使用说明：
  1. 复制此文件到你的项目目录
  2. 按 TODO 标记填写具体内容
  3. 运行后得到干净的 numpy.ndarray → 直接喂给数值计算 Skill

管道结构：
  Step 1: 数据读取 (read_csv / read_excel)
  Step 2: 数据检查 (shape / info / describe / isnull)
  Step 3: 缺失值处理 (fillna / dropna)
  Step 4: 异常值处理 (IQR / clip)
  Step 5: 特征工程 (���准化 / 编码 / 构造特征)
  Step 6: 输出 (to_numpy → numerical_computing Skill)
"""

import pandas as pd
import numpy as np
from scipy import stats

# ============================================================
# Step 1: 数据读取
# ============================================================
# TODO: 修改为你的实际文件路径
# df = pd.read_csv('your_data.csv', encoding='utf-8')
# df = pd.read_excel('your_data.xlsx', sheet_name='Sheet1')

# ---- 模拟数据（替换为实际读取）----
rng = np.random.default_rng(42)
df = pd.DataFrame({
    'id': range(1, 101),
    'feature_1': rng.normal(100, 15, 100),
    'feature_2': rng.normal(50, 10, 100),
    'category': rng.choice(['A', 'B', 'C'], 100),
    'target': rng.normal(200, 30, 100),
})
# 注入一些缺失值模拟真实数据
df.loc[5, 'feature_1'] = np.nan
df.loc[10, 'feature_2'] = np.nan
# ============================================================

print("=" * 60)
print("数据预处理管道开始")
print(f"  Step 1: 读取 → {df.shape[0]} 行, {df.shape[1]} 列")

# ============================================================
# Step 2: 数据检查
# ============================================================
print(f"\n{'='*60}")
print("Step 2: 数据检查")

print(f"  列名: {df.columns.tolist()}")
print(f"  类型:\n{df.dtypes.to_string()}")

# 缺失值报告
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(1)
missing_report = pd.DataFrame({'缺失数': missing, '缺失比例%': missing_pct})
missing_report = missing_report[missing_report['缺失数'] > 0]
if len(missing_report) > 0:
    print(f"  缺失值:\n{missing_report}")
else:
    print(f"  缺失值: 无")

# 重复值
dupes = df.duplicated().sum()
print(f"  重复行: {dupes}")

# 统计描述
print(f"  数值列描述:\n{df.describe().round(2).to_string()}")

# ============================================================
# Step 3: 缺失值处理
# ============================================================
print(f"\n{'='*60}")
print("Step 3: 缺失值处理")

for col in df.columns:
    if df[col].isnull().sum() > 0:
        if df[col].dtype in ['float64', 'int64']:
            df[col] = df[col].fillna(df[col].median())
            print(f"  {col} (数值): → 中位数填充")
        else:
            df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown',
                           inplace=True)
            print(f"  {col} (分类): → 众数填充")

assert df.isnull().sum().sum() == 0, "仍有缺失值未处理"

# ============================================================
# Step 4: 异常值处理
# ============================================================
print(f"\n{'='*60}")
print("Step 4: 异常值处理")

numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
numeric_cols = [c for c in numeric_cols
                if c not in ['id', 'target']]  # TODO: 排除 ID 和目标变量

for col in numeric_cols:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 3 * IQR
    upper = Q3 + 3 * IQR
    outliers = ((df[col] < lower) | (df[col] > upper)).sum()
    if outliers > 0:
        df[col] = df[col].clip(lower, upper)
        print(f"  {col}: {outliers} 个异常值 → clip 截断")

# ============================================================
# Step 5: 特征工程
# ============================================================
print(f"\n{'='*60}")
print("Step 5: 特征工程")

# 分类变量编码
cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
if cat_cols:
    df = pd.get_dummies(df, columns=cat_cols, drop_first=True, dtype=float)
    print(f"  One-Hot 编码: {cat_cols}")

# 标准化（如果后续需要）
# TODO: 根据建模需求选择是否需要标准化
# for col in numeric_cols:
#     df[f'{col}_z'] = stats.zscore(df[col])

# ============================================================
# Step 6: 输出 → Numerical Computing Skill
# ============================================================
print(f"\n{'='*60}")
print("Step 6: 输出模型就绪数据")

# 分离特征和目标
feature_cols = [c for c in df.columns
                if c not in ['id', 'target']]  # TODO: 修改排除列
target_col = 'target'  # TODO: 修改为目标列名

X = df[feature_cols].to_numpy(dtype=np.float64)
y = df[target_col].to_numpy(dtype=np.float64)

# 质量检查
assert not np.any(np.isnan(X)), "X 包含 NaN"
assert not np.any(np.isinf(X)), "X 包含 Inf"
assert not np.any(np.isnan(y)), "y 包含 NaN"

print(f"  X: {X.shape} (n_samples={X.shape[0]}, n_features={X.shape[1]})")
print(f"  y: {y.shape} (n_samples={y.shape[0]},)")
print(f"  特征名: {feature_cols}")

# ============================================================
# 管道摘要
# ============================================================
print(f"\n{'='*60}")
print("管道完成摘要")
print(f"  原始: {len(df)} 样本, {len(df.columns)} 列")
print(f"  缺失值: 已填充")
print(f"  异常值: 已处理")
print(f"  特征: {len(feature_cols)} 个")
print(f"  输出: X{y.shape} numpy.ndarray")
print(f"\n  → 可喂给 numerical_computing Skill:")
print(f"     scipy.optimize.minimize / linprog / curve_fit")
print(f"     scipy.integrate.solve_ivp")
print(f"     numpy.linalg.solve / eig / svd")
print(f"     scipy.stats (统计检验)")
print("=" * 60)
