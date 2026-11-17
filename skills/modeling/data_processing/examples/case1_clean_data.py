"""
案例1：企业销售数据清洗

问题背景：
   某企业销售系统导出的CSV包含缺失值、重复订单、异常金额、格式不一致等问题。
   需要清洗后用于月度销售分析。

数据特征（模拟）：
   - 订单ID: 部分重复
   - 日期: 字符串格式，需要转换
   - 销售额: 负数异常值
   - 客户类型: 部分缺失
   - 城市: 混有空格/大小写不一致

处理步骤：
   1. CSV 读取 + 基本信息
   2. 缺失值检测与处理
   3. 重复值检测与去重
   4. 异常值检测与处理
   5. 数据规范化（类型转换、格式统一）
   6. 输出清洗报告
"""
import pandas as pd
import numpy as np
from io import StringIO

print("=" * 60)
print("案例1：企业销售数据清洗")
print("=" * 60)

# ---- 1. 模拟原始数据（含各种问题）----
raw_data = """order_id,date,amount,customer_type,city
ORD001,2024-01-15,1500.00,企业,北京
ORD002,2024-01-15,2300.00,,Shanghai
ORD003,2024-01-16,-500.00,个人,广州
ORD001,2024-01-16,1500.00,企业,北京
ORD004,2024-01-17,8500.00,, 深圳 
ORD005,2024/01/18,1200.00,个人,Guangzhou
ORD006,2024-01-19,,企业,成都
ORD007,2024-01-20,99999.00,个人,杭州
ORD008,2024-01-20,1800.00,企业, 北京
ORD009,2024-01-21,2200.00,个人,
ORD010,2024-01-22,1900.00,企业,上海
"""

df = pd.read_csv(StringIO(raw_data))
print(f"\n【Step 1: 原始数据】")
print(f"  形状: {df.shape}")
print(f"  列名: {df.columns.tolist()}")
print(f"\n{df.to_string()}")

# ---- 2. 数据检查 ----
print(f"\n{'='*60}")
print(f"【Step 2: 数据质量检查】")

print(f"\n  列类型:")
print(f"  {df.dtypes.to_dict()}")

missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(1)
print(f"\n  缺失值统计:")
for col in df.columns:
    if missing[col] > 0:
        print(f"    {col}: {missing[col]} 个 ({missing_pct[col]}%)")

dupes = df.duplicated().sum()
print(f"\n  重复行: {dupes} 个")

dupe_ids = df.duplicated(subset=['order_id']).sum()
print(f"  重复订单ID: {dupe_ids} 个")

# ---- 3. 数据清洗 ----
print(f"\n{'='*60}")
print(f"【Step 3: 数据清洗】")

# 3.1 去重（保留第一次出现的订单）
before = len(df)
df.drop_duplicates(subset=['order_id'], keep='first', inplace=True)
print(f"  去重: {before} → {len(df)} 行 (删除 {before - len(df)} 行)")

# 3.2 日期格式统一
df['date'] = pd.to_datetime(df['date'], format='mixed', dayfirst=False)
print(f"  日期格式统一: 转换为 datetime64")

# 3.3 异常金额处理
print(f"\n  金额分布: mean={df['amount'].mean():.0f}, "
      f"median={df['amount'].median():.0f}, "
      f"max={df['amount'].max():.0f}, "
      f"min={df['amount'].min():.0f}")

# 负数处理
neg_count = (df['amount'] < 0).sum()
df['amount'] = df['amount'].abs()  # 销售额不可能为负
print(f"  负数金额修正: {neg_count} 个取绝对值")

# 极大值处理（IQR方法）
Q1 = df['amount'].quantile(0.25)
Q3 = df['amount'].quantile(0.75)
IQR = Q3 - Q1
upper = Q3 + 3.0 * IQR  # 使用更宽松的3倍IQR
outlier_mask = df['amount'] > upper
print(f"  异常高金额(>{upper:.0f}): {outlier_mask.sum()} 个 → 截断到上限")
df.loc[outlier_mask, 'amount'] = upper

# 3.4 缺失值填充
df['customer_type'] = df['customer_type'].fillna('未标记')
df['city'] = df['city'].fillna('未知')
print(f"  缺失值填充: customer_type→'未标记', city→'未知'")

# 3.5 城市名规范化
city_map = {
    'Shanghai': '上海', 'shanghai': '上海',
    'Guangzhou': '广州', 'guangzhou': '广州',
}
df['city'] = df['city'].str.strip().replace(city_map)
print(f"  城市名规范化: 去除空格, 英文→中文")

# ---- 4. 清洗后结果 ----
print(f"\n{'='*60}")
print(f"【Step 4: 清洗后数据】")
print(f"  最终形状: {df.shape}")
print(f"  缺失值: {df.isnull().sum().sum()} 个")
print(f"  重复行: {df.duplicated().sum()} 个")
print(f"\n{df.to_string()}")

# ---- 5. 汇总分析 ----
print(f"\n{'='*60}")
print(f"【Step 5: 汇总分析】")
print(f"\n  按客户类型:")
summary = df.groupby('customer_type').agg(
    订单数=('order_id', 'count'),
    总金额=('amount', 'sum'),
    平均金额=('amount', 'mean')
).round(0)
print(summary)

print(f"\n  按城市:")
city_summary = df.groupby('city').agg(
    订单数=('order_id', 'count'),
    总金额=('amount', 'sum')
).sort_values('总金额', ascending=False).round(0)
print(city_summary)

total_sales = df['amount'].sum()
print(f"\n  总销售额: {total_sales:.0f} 元")
print(f"  有效订单: {len(df)} 单")

print(f"\n✅ 案例1完成：企业销售数据清洗")
print(f"   处理: 去重→日期转换→异常值处理→缺失填充→规范化")
print(f"   输出: 干净的 DataFrame，可直接用于分析和建模")
