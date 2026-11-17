# scikit-learn 速查表

> Stage 20.5: 补充 numerical_computing/ 缺失的 sklearn 参考

## Regression 回归

```python
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor

# 线性
model = LinearRegression()
model = Ridge(alpha=1.0)       # L2正则
model = Lasso(alpha=0.1)       # L1正则(特征选择)
model = ElasticNet(alpha=0.1)  # L1+L2

# 集成
model = RandomForestRegressor(n_estimators=200, max_depth=10)
model = GradientBoostingRegressor(n_estimators=200, learning_rate=0.1)

# 其他
model = SVR(kernel='rbf', C=1.0)
```

## Classification 分类

```python
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
```

## Clustering 聚类

```python
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture

kmeans = KMeans(n_clusters=4, n_init=10)
dbscan = DBSCAN(eps=0.5, min_samples=5)
gmm = GaussianMixture(n_components=4)
```

## Decomposition 降维

```python
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

pca = PCA(n_components=0.85)  # 保留85%方差
X_pca = pca.fit_transform(X)

tsne = TSNE(n_components=2)  # 可视化
X_tsne = tsne.fit_transform(X)
```

## Model Selection

```python
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score

# 时序数据: 必须用 TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, test_idx in tscv.split(X):
    ...
```

## Feature Importance

```python
# RF/XGBoost
importances = model.feature_importances_

# 线性模型系数
coef = model.coef_
```
