# A-Share Board Radar

A股“主升浪 / 二波启动”量化选股系统，第一版目标：从全市场日线数据中筛选趋势、突破、量价、资金与风险结构同时较优的股票，并输出 0-100 综合评分。

## V1.0 核心评分

- 趋势结构：20分
- 平台/突破：20分
- 量价配合：20分
- 资金强度：20分
- 风险过滤：20分

系统不是预测涨停，而是寻找“上涨概率与盈亏比同时较优”的候选池。

## 当前状态

V1.0 先完成数据结构、指标计算、评分和扫描引擎；行情接口独立封装，后续可接 AKShare / Tushare 等数据源。

## 运行

```bash
pip install -r requirements.txt
python main.py --input data/sample.csv
```

输入至少包含：date, code, name, open, high, low, close, volume, amount, turnover。
