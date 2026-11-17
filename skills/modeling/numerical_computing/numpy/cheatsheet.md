# NumPy 速查表

| 操作 | 代码 | 备注 |
|------|------|------|
| 创建数组 | `np.array([[1,2],[3,4]])` | 从列表创建矩阵 |
| 零矩阵 | `np.zeros((m,n))` | 初始化 |
| 单位阵 | `np.eye(n)` | I |
| 全 1 阵 | `np.ones((m,n))` | 权重/掩码 |
| 等间距 | `np.linspace(0,10,100)` | 采样点生成 |
| 时间序列 | `np.arange(0,T,dt)` | 离散时间 |
| 矩阵乘法 | `A @ B` | 推荐写法 |
| 转置 | `A.T` | |
| 求逆 | `np.linalg.inv(A)` | 慎用，尽量用 solve |
| 解方程 | `np.linalg.solve(A,b)` | Ax=b |
| 最小二乘 | `np.linalg.lstsq(A,b)` | 超定方程 |
| 特征值 | `np.linalg.eig(A)` | 一般矩阵 |
| 特征值(对称) | `np.linalg.eigh(A)` | 更稳定 |
| SVD | `np.linalg.svd(A)` | 降维/伪逆 |
| 行列式 | `np.linalg.det(A)` | |
| 范数 | `np.linalg.norm(A)` | |
| 秩 | `np.linalg.matrix_rank(A)` | |
| 指数 | `np.exp(x)` | e^x |
| 对数 | `np.log(x)` | ln(x) |
| 求和 | `np.sum(x)` | |
| 均值 | `np.mean(x)` | |
| 标准差 | `np.std(x)` | |
| 最大值索引 | `np.argmax(x)` | |
| 累积和 | `np.cumsum(x)` | |
| 随机种子 | `rng = np.random.default_rng(42)` | 可复现 |
| 正态采样 | `rng.normal(mu,sig,N)` | |
| 均匀采样 | `rng.uniform(a,b,N)` | |
| 多项式拟合 | `np.polyfit(x,y,deg)` | 传统API |
