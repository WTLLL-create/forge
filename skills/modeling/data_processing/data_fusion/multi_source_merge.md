# Multi-Source Data Fusion — 多源数据合并

> 真实国赛很少是单表输入。多源数据合并是建模的第一步。

## 标准流程

```
Source 1 (CSV): 污染物监测数据 (日期, 站点, O3, PM2.5...)
Source 2 (CSV): 气象数据 (日期, 站点, 温度, 湿度...)
Source 3 (XLSX): 人口/交通数据 (年份, 区域...)

Step 0.1: Schema 对齐
  □ 识别共同键 (日期, 站点ID, 区域代码)
  □ 检查键的粒度和格式是否一致
  □ 时间戳: '2021-01-01' vs '2021/1/1' → 统一

Step 0.2: 合并策略选择
  时间序列: 按时间戳 merge (pd.merge on='date')
  空间对齐: 按站点ID merge (pd.merge on='station_id')
  不同粒度: 先聚合到统一粒度再 merge
    (如人口是年度, 污染物是逐日 → 人口在年内复制或插值)

Step 0.3: 合并执行
  df = pd.merge(df1, df2, on=['date', 'station_id'], how='left')

Step 0.4: 合并后检查
  □ merge 后的行数是否合理? (不是笛卡尔积)
  □ 是否有站点在合并后丢失? (how='left' vs 'inner')
  □ 新列的缺失率是否过高?

Step 0.5: 进入标准数据管道
  → data_processing/workflow.md Step 1-6
```

## 常见坑

- 不同数据源的站点命名不一致 (如 '朝阳站' vs 'CY_Station')
- 时间粒度不同 (小时 vs 日均 → 需先聚合)
- merge key 有重复值导致行数爆炸
