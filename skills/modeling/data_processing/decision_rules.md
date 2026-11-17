# AI 决策规则：根据数据特征自动选择处理方法

> Agent 读取数据后，按以下规则判断处理策略

---

## 规则 1：数据读取

```
触发：输入为文件路径（.csv/.xlsx/.json/.txt）
动作：根据扩展名选择读取方法
  .csv   → pd.read_csv(encoding='utf-8')
  .xlsx  → pd.read_excel(sheet_name=None)  # 先读取所有 sheet 名
  .json  → pd.read_json()
  .txt   → 尝试 pd.read_csv(sep='\t') 或自定义分隔符
```

---

## 规则 2：缺失值策略

```
触发：df.isnull().sum() > 0
判断：
  缺失比例 < 5%     → 数值列 fillna(median)，分类列 fillna(mode)
  缺失比例 5%-20%   → 尝试 fillna(method='ffill') 或 interpolate()
  缺失比例 20%-50%  → 警告用户，建议 drop 或建模填充
  缺失比例 > 50%    → 删除该列 drop(columns=[col])

特殊情况：
  时间序列列缺失     → 优先 ffill()（前向填充）
  分类列缺失         → 创建 'Unknown' 类别而非填充众数
  目标变量缺失       → 删除对应行（不可填充）
```

---

## 规则 3：异常值检测

```
触发：数值列 range 异常 或 describe() 显示偏度 > 2

方法选择：
  正态分布数据       → Z-score: |z| > 3 为异常
  偏态分布数据       → IQR: Q1-1.5*IQR ~ Q3+1.5*IQR
  物理约束已知       → 直接 clip(lower, upper)
  不知道分布         → 先画 boxplot/hist 再判断

处理方式选择：
  样本充足           → 删除异常行
  样本不足           → clip 截断
  需要保留所有样本   → winsorize（替换为边界值）
```

---

## 规则 4：时间序列识别

```
触发：列名含 'date'/'time'/'year'/'month'/'day'/'日期'/'时间'
   或 数据规律递增/递减

动作：
  1. pd.to_datetime() 转换
  2. 设置索引: df.set_index('date', inplace=True)
  3. 检查频率: df.index.inferred_freq

后续操作选择：
  需要月度/季度汇总  → df.resample('M').mean()
  需要平滑趋势       → df.rolling(window=7).mean()
  需要滞后特征       → df.shift(periods)
  需要同比/环比      → df.pct_change(periods)
  需要时间特征提取   → dt.year, dt.month, dt.dayofweek
```

---

## 规则 5：特征准备（ML 模型接口）

```
触发：建模目标为预测/分类，需要构建 X, y

动作：
  1. 分离特征和标签: X = df.drop('target', axis=1), y = df['target']
  2. 数值特征标准化: StandardScaler / zscore
  3. 分类特征编码: pd.get_dummies() 或 LabelEncoder
  4. 训练/测试划分: train_test_split (如果需要模型验证)
  5. 输出: X(numpy), y(numpy), feature_names(list)

注意：
  - 标准化应在划分后做（避免数据泄漏）
  - One-Hot 编码后用 float 而非 bool
  - 缺失值必须在特征准备前处理完成
```

---

## 规则 6：数据量判断

```
触发：读取完数据后自动判断

dtype 优化：
  df.shape[0] > 100,000  → df['col'] = df['col'].astype('float32') 节省内存
  df.shape[0] > 1,000,000 → 考虑分块处理 chunksize

列数优化：
  n_cols > 50 → 检查常数列和高度相关列，可考虑降维
  n_cols > 100 → 建议先做特征筛选再看数据
```

---

## 自检清单

Agent 在完成数据处理后应自检：

- [ ] 所有列类型是否正确（数值 float/int，时间 datetime，分类 category）
- [ ] 缺失值已处理（isnull().sum().sum() == 0）
- [ ] 无重复行（duplicated().sum() == 0）
- [ ] 数值范围合理（无负价格、负人口等）
- [ ] 列名无特殊字符（可用 df.columns 作为变量名）
- [ ] 输出格式正确（numpy.ndarray 或 干净 DataFrame）
