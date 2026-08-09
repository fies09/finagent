# 量化交易知识体系与技术栈指南

> 一份系统化的学习与实践路线
> 目标：从 0 到生产级量化交易系统的完整能力图谱

---

## 一、金融知识基础（必学）

### 1.1 金融市场结构
- **资产类别**：股票 / 期货 / 期权 / 外汇 / 加密货币 / 债券 / 大宗商品
- **市场参与者**：散户 / 机构 / 做市商 / 套利者 / 对冲基金
- **交易机制**：T+0 / T+1 / 撮合方式（连续竞价 / 集合竞价）/ 涨跌停
- **订单类型**：市价单 / 限价单 / 止损单 / 止损限价 / 追踪止损 / OCO / Iceberg
- **交易所**：NYSE / NASDAQ / CME / Binance / OKX / Coinbase / Interactive Brokers

### 1.2 价格行为理论
- **K线理论**：单根（锤子、十字星、吞没）/ 组合（双底、双顶、三角）
- **趋势**：上升 / 下降 / 横盘 / 反转
- **支撑阻力**：前高前低 / 整数关口 / 成交密集区 / 趋势线 / 通道
- **市场周期**：积累 → 拉升 → 派发 → 下跌

### 1.3 技术指标体系
| 类别 | 指标 | 用途 |
|------|------|------|
| 趋势 | MA / EMA / MACD / DMI / ADX | 判断方向 |
| 动量 | RSI / Stochastic / CCI / Williams %R | 超买超卖 |
| 波动 | Bollinger Bands / ATR / Keltner | 通道与止损 |
| 成交量 | OBV / VWAP / Volume Profile / A/D Line | 资金流 |
| 强度 | ADX / Aroon / TSI | 趋势强度 |

### 1.4 量化策略大类
1. **趋势跟踪（Trend Following）**：海龟、Donchian breakout、双均线
2. **均值回归（Mean Reversion）**：布林带、RSI、Pair trading
3. **套利（Arbitrage）**：跨期 / 跨市 / 跨品种 / 三角套利
4. **统计套利**：协整、PCA 因子、协方差矩阵
5. **动量（Momentum）**：截面动量 / 时序动量
6. **做市（Market Making）**：库存模型、Avellaneda-Stoikov
7. **事件驱动**：财报、公告、宏观数据
8. **机器学习策略**：XGBoost / LSTM / Transformer / RL

### 1.5 风险管理与组合理论
- **风险指标**：Sharpe / Sortino / Calmar / Max Drawdown / VaR / CVaR
- **仓位管理**：Kelly Criterion / 固定比例 / 波动率倒数
- **组合理论**：
  - Markowitz 均值-方差
  - Black-Litterman
  - 风险平价（Risk Parity）
  - 最大分散化
- **回撤控制**：移动止损 / 时间止损 / 相关性矩阵

### 1.6 回测与评估
- **回测陷阱**：未来函数 / 偷价 / 幸存者偏差 / 过拟合
- **评估指标**：年化收益 / 波动率 / Sharpe / 最大回撤 / 胜率 / 盈亏比
- **验证方法**：Walk-forward / 交叉验证 / 蒙特卡洛 / 多周期多品种
- **成本模型**：手续费 / 滑点 / 冲击成本 / 资金费率（加密）

---

## 二、技术栈全景（按重要度排序）

### 🥇 T1 核心 6 件套（强烈推荐立刻上手）

| 库 | 作用 | 替代方案 |
|------|------|----------|
| **pandas / numpy** | 数据处理基石 | polars（更快） |
| **vectorbt** | 100x 加速回测 | backtrader（事件）/ nautilus_trader（生产） |
| **pandas-ta** | 150+ 技术指标 | ta-lib / finta |
| **pyportfolioopt** | 组合优化 | riskfolio-lib |
| **mlflow** | 实验追踪 | wandb / neptune |
| **ccxt / ccxt.pro** | 行情/下单 100+ 交易所 | 私有SDK |

✅ 已集成到 FinAgent

### 🥈 T2 进阶（按需追加）

| 库 | 作用 | 场景 |
|------|------|------|
| **neuralforecast** | NHITS / TFT / PatchTST 时序预测 | 中期方向预测 |
| **stable-baselines3** | PPO / SAC 强化学习 | 复杂环境策略 |
| **optuna** | 超参搜索 | 因子权重、阈值调优 |
| **quantstats** | 一键生成 tear sheet | 回测报告 |
| **riskfolio-lib** | CVaR / 风险归因 | 高级风控 |
| **plotly / bokeh** | 交互图表 | 前端可视化 |
| **yfinance / akshare / tushare** | 多市场数据 | A 股/美股 |
| **finbert-tone** | 金融情感模型 | 新闻打分 |

### 🥉 T3 生产级（大规模部署）

| 库 | 作用 | 场景 |
|------|------|------|
| **nautilus_trader** | Rust 内核 + Python API，回测+实盘+撮合一体 | 生产平台 |
| **polars** | 5-10x pandas 性能 | 大数据 OHLCV |
| **rq / celery** | 分布式任务队列 | 多 worker |
| **timescaleDB / questdb** | 时序数据库 | tick 级数据 |
| **stream-zip / asyncio-ccxt** | 实时行情流 | 高频策略 |
| **postgres + redis** | 持久化 + 缓存 | 多实例共享 |

### 🔧 工程能力（必备）

- **数据工程**：ETL pipeline / 数据清洗 / 异常处理 / 时序对齐
- **异步编程**：asyncio / aiohttp / 异步队列
- **API 设计**：FastAPI / REST / WebSocket
- **容器化**：Docker / docker-compose
- **监控告警**：Grafana / Prometheus / Sentry
- **CI/CD**：GitHub Actions / pytest
- **数据库**：SQL / 时序 / 向量（Milvus）

---

## 三、实践路线（4 周快速成型）

### 第 1 周：基础 + 数据
- [x] 集成 vectorbt / pandas-ta / pyportfolioopt
- [ ] 接入真实 OHLCV（ccxt + 多交易所）
- [ ] 因子库初版：MA / RSI / MACD / BB
- [ ] 简单均线策略 + vectorbt 回测

### 第 2 周：策略开发
- [ ] 趋势策略：双均线 + ATR 止损
- [ ] 均值回归：布林带 + RSI
- [ ] Pair trading：协整检验
- [ ] 多策略 ensemble + 权重优化
- [ ] quantstats 生成报告

### 第 3 周：AI + 风控
- [ ] AI 情绪打分（已有）+ 技术信号融合
- [ ] 时序预测（neuralforecast）
- [ ] pyportfolioopt 组合权重
- [ ] MLflow 追踪每个实验
- [ ] 风控规则（VaR / 持仓上限）

### 第 4 周：生产化
- [ ] ccxt.pro 实盘接口
- [ ] Redis 缓存层（已有）
- [ ] PostgreSQL 持久化
- [ ] Grafana 监控
- [ ] 文档 + 回测报告模板

---

## 四、推荐学习资源

### 书籍
- 《Advances in Financial Machine Learning》— Marcos López de Prado
- 《Quantitative Trading》— Ernie Chan
- 《Algorithmic Trading》— Ernest Chan
- 《Python for Finance》— Yves Hilpisch
- 《海龟交易法则》— Curtis Faith
- 《打开量化投资的黑箱》— Rishi Narang

### 课程
- QuantConnect Lean 文档与示例
- Quantra（QuantInsti）在线课程
- Coursera 金融工程专项

### 开源参考
- **nautilus_trader** 源码（生产级典范）
- **vectorbt** 文档（向量化回测范式）
- **zipline-reloaded**（Quantopian 续作）
- **backtrader** 文档（事件驱动经典）

### 数据源
- **ccxt** 100+ 交易所
- **yfinance** 美股
- **akshare** A 股
- **tushare pro** A 股专业
- **CryptoCompare** 加密
- **FRED** 宏观

---

## 五、避坑清单（实战经验）

1. **回测 ≠ 实盘**：滑点、资金费率、网络延迟、合规风险
2. **过拟合**：参数越多越容易过拟合，walk-forward 验证
3. **未来函数**：回测时绝不能用未来数据
4. **幸存者偏差**：用退市股票数据补全
5. **策略拥挤**：同一逻辑太多人用，alpha 衰减
6. **黑天鹅**：2008 / 2020-03 / 2022-05 都需要压力测试
7. **数据质量**：复权、分红、停牌、换合约
8. **资金容量**：年化 50% 但只容 10 万 vs 100 万策略不同
10. **执行成本**：手续费 + 滑点吃掉一半 alpha

---

## 六、FinAgent 当前已具备能力 ✅

- [x] 多源 RSS 实时新闻
- [x] AI 新闻情绪分析（Claude Sonnet 5）
- [x] 150+ 技术指标（pandas-ta）
- [x] 向量化回测（vectorbt）
- [x] 事件驱动回测（backtrader）
- [x] 组合优化（pyportfolioopt）
- [x] 实验追踪（mlflow）
- [x] 系统日志持久化（system_logs）
- [x] 风险监控（RiskManager）
- [x] 交易日志 + 反馈报告
- [x] 调度器（apscheduler）

## 七、FinAgent 待落地 ⏳

- [x] 真实 ccxt OHLCV（网络可达性）
- [x] neuralforecast 时序预测
- [x] ccxt.pro 实盘下单
- [x] optuna 超参搜索（core/optuna_tuner.py）
- [x] plotly 交互图表前端（core/charts.py + /chart/candlestick）
- [x] yfinance 美股扩展（core/stock_ingest.py + /stock/fetch）
- [x] quantstats 回测报告（core/report.py + /report/generate）
- [x] akshare A股接入（core/ashare_ingest.py + /ashare/fetch）
- [x] Alphalens 因子评估（core/factor_eval.py + /factor/evaluate）
- [x] polars 加速大数据处理（core/polars_engine.py + /polars/stats /polars/corr）
- [x] nautilus_trader 生产级回测引擎（core/nautilus_engine.py + /nautilus/backtest）

---

## 八、术语速查

| 术语 | 含义 |
|------|------|
| Alpha | 超额收益 |
| Beta | 对市场敏感度 |
| Sharpe | 风险调整后收益 |
| Max DD | 最大回撤 |
| CAGR | 年化复合增长率 |
| IR | 信息比率 |
| Turnover | 换手率 |
| Slippage | 滑点 |
| Spread | 买卖价差 |
| VWAP | 成交量加权均价 |
| TWAP | 时间加权均价 |
| OHLCV | 开高低收量 |
| Backtest | 回测 |
| Walk-forward | 前推验证 |
| Monte Carlo | 蒙特卡洛模拟 |
| Cointegration | 协整性 |
| Stationary | 平稳性 |
| Kelly % | 最优下注比例 |
| Greeks | 期权敏感度（Delta/Gamma/Vega/Theta/Rho）|

---

## 九、参考方案技术栈补充（来自《AI辅助研究与严格回测实施方案》）

### 9.1 数据层
| 工具 | 覆盖 | 特点 |
|---|---|---|
| yfinance | 美股/部分加密 | 零门槛 |
| AKShare | A股/期货/宏观 | 国内首选 |
| Tushare Pro | A股财务/龙虎榜 | 高级数据需积分 |
| ccxt | 100+ 加密交易所 | ✅ FinAgent 已集成（默认 okx） |
| baostock | A股历史 | 完全免费免注册 |
| JQData/RiceQuant | A股一站式 | 有使用门槛 |

### 9.2 存储层
- 行情时序：**InfluxDB / ClickHouse**
- 财务结构化：**PostgreSQL / MySQL**
- 新闻原文：**MongoDB / Parquet**
- 向量检索：**Chroma / Milvus / FAISS**
- MVP 起步：**SQLite + Parquet**（FinAgent 当前用 SQLite）

### 9.3 回测框架
| 框架 | 定位 |
|---|---|
| **Backtrader** | 事件驱动，资料最多（FinAgent 已用） |
| **vectorbt** | 向量化，参数扫描快（FinAgent 已集成） |
| **vn.py** | A股实盘 |
| **QLib** | AI 量化一体化 |
| **Zipline-reloaded** | Quantopian 遗产 |

### 9.4 因子分析工具
- **Alphalens**：IC、分层收益、换手率
- **empyrical**：Sharpe/MaxDD/Calmar

### 9.5 基础设施
- 调度：**APScheduler**（✅ 已集成）/ **Airflow**
- 实验管理：**MLflow**（✅ 已集成）
- 日志：**loguru + 企业微信/Telegram**（✅ 已集成 system_logs）
- 容器化：**Docker**

### 9.6 严格回测必做 9 项
1. 样本外测试
2. Walk-forward 滚动
3. Purged K-Fold（避免信息泄露）
4. 手续费 + 滑点
5. 最大回撤
6. 多市场环境（牛/熊/震）
7. 胜率 vs 盈亏比
8. 参数敏感性
9. 蒙特卡洛压力测试

### 9.7 组合风控
- 相关性矩阵
- 波动率目标仓位（Vol Targeting）
- 组合 VaR / 最大回撤熔断
- 凯利公式仓位

### 9.8 实施路径
| 阶段 | 内容 | 周期 |
|---|---|---|
| 1 | 数据 + 基础回测 | 1-2 周 |
| 2 | AI 情绪打分 + Alphalens | 2-3 周 |
| 3 | 样本外 + Walk-forward | 1-2 月 |
| 4 | 日志/告警/模拟盘 | 3-6 月 |
| 5 | 极小额实盘 + 复盘 | 长期 |

---

## 十、FinAgent 模块全景（功能 ↔ 技术栈 ↔ 金融领域）

### 10.1 已落地 17 模块

| # | 功能模块 | 后端文件 | 端点 | 前端 tab | 金融领域 | 核心技术栈 |
|---|---|---|---|---|---|---|
| 1 | AI 新闻情绪分析 | core/ai_analyzer.py | /analyze/news /news/analyze | AI分析 | 事件驱动/NLP | Claude Sonnet 5 + Redis 缓存 |
| 2 | AI 因子生成 | core/ai_analyzer.py | /analyze/factor | AI分析 | 多因子模型 | Claude Sonnet 5 |
| 3 | 技术指标因子库 | core/factor.py | /factor/summary | 高级分析 | 技术分析 | pandas-ta (150+) |
| 4 | 事件驱动回测 | core/backtest.py | /backtest | 回测引擎 | 经典 CTA | backtrader |
| 5 | 向量化回测 | core/vbt_engine.py | /backtest/vbt | 高级分析 | 大规模扫描 | vectorbt + pandas-ta |
| 6 | 组合优化 | core/portfolio.py | /portfolio/optimize | 高级分析 | 现代资产组合 | pyportfolioopt |
| 7 | 实验追踪 | core/tracker.py | /experiments/runs | 高级分析 | ML Ops | mlflow (sqlite) |
| 8 | 风险管理 | core/risk.py | /risk/status | 仪表盘 | 仓位/回撤 | 自研规则引擎 |
| 9 | 交易反馈 | core/feedback.py | /feedback/trades | 调度器 | 策略复盘 | pandas |
| 10 | 任务调度 | core/scheduler.py | /scheduler/start /scheduler/stop | 调度器 | 自动化 | APScheduler |
| 11 | 时序预测 | core/forecaster.py | /forecast | 时序预测 | 时序预测 | neuralforecast/NHITS |
| 12 | 超参搜索 | core/optuna_tuner.py | /tune | 超参搜索 | 策略调优 | optuna |
| 13 | 交互图表 | core/charts.py | /chart/candlestick | 图表 | 可视化 | plotly |
| 14 | 美股行情 | core/stock_ingest.py | /stock/fetch /stock/quote | 美股 | 跨市场 | yfinance |
| 15 | 实盘交易 | core/live_trader.py | /live/* | 实盘交易 | 执行 | ccxt.pro (okx) |
| 16 | 系统日志 | core/log_store.py | /logs /logs/clear | 系统日志 | 监控 | loguru + sqlite |
| 17 | 行情获取 | core/store.py | /market/price | 仪表盘 | 数据层 | ccxt (okx) |

### 10.2 待落地（pip 镜像 503 暂未安装）

| 模块 | 用途 | 阻塞项 |
|---|---|---|
| polars 加速 | 替代 pandas，5-10x OHLCV 处理 | pip 镜像源 503 |
| nautilus_trader | Rust 内核生产级回测/撮合引擎 | pip 镜像源 503 |

### 10.3 后续可继续追加的金融技术栈

| 金融领域 | 推荐库 | 用途 | 优先级 |
|---|---|---|---|
| 期权定价 | py_vollib / QuantLib | Black-Scholes / Greeks / 波动率曲面 | 中 |
| 固定收益 | QuantLib | 收益率曲线 / 久期 / 凸性 | 中 |
| 统计套利 | statsmodels / arch | 协整检验 / GARCH / VAR | 中 |
| 金融情感 | finbert-tone | 预训练 BERT 替代 LLM 判情绪 | 高 |
| 因子分析 | alphalens-reloaded | IC / 分层收益 / 换手率评估 | 高 |
| 回测报告 | quantstats | 一键生成 tear sheet | 高 |
| 技术指标 | ta-lib | C 实现，速度更快 | 中 |
| 风控 | riskfolio-lib | CVaR / 风险归因 / 最大回撤优化 | 中 |
| Tick 数据 | arctic / questdb | 高频 tick 存储 | 低 |
| 分布式任务 | rq / celery | 多 worker 并行 | 低 |
| 实时行情 | stream-zip / asyncio-ccxt | WebSocket 推送 | 中 |
| 时序数据库 | timescaleDB / questdb | tick 级数据 | 低 |
| 因子存储 | arctic / dolphindb | 高频因子持久化 | 低 |
| 多市场数据 | akshare / tushare / finnhub | A 股 / 美股 / 外汇 | 高 |
| 报告渲染 | jinja2 + weasyprint | PDF 月报/周报 | 低 |

### 10.4 金融知识体系深化

#### 10.4.1 资产类别
- 股票：A 股 / 港股 / 美股（多市场已覆盖：加密 + 美股）
- 期货：商品期货 / 金融期货 / 国债期货（待对接 CTPMini）
- 期权：ETF 期权 / 商品期权 / 股指期权（待 QuantLib）
- 数字货币：现货 / 合约 / 杠杆代币（已覆盖现货 + 实盘）
- 外汇：主要货币对（ccxt 已支持部分）

#### 10.4.2 量化策略大类
1. **趋势跟踪**：双均线 / Donchian / 海龟 / Aberration
2. **均值回归**：布林带 / RSI / Pair trading / Statistical arb
3. **套利**：跨期 / 跨市 / 跨品种 / 三角套利
4. **统计套利**：协整 / PCA / 协方差矩阵
5. **动量**：截面动量 / 时序动量 / 资金流
6. **做市**：Avellaneda-Stoikov / 库存模型
7. **事件驱动**：财报 / 公告 / 宏观数据
8. **机器学习**：XGBoost / LSTM / Transformer / RL

#### 10.4.3 风控层级
- **事前**：信号过滤 / 仓位限额 / 黑名单
- **事中**：止损 / 移动止盈 / 波动率倒数仓位
- **事后**：回撤熔断 / 复盘 / 策略下线

#### 10.4.4 回测陷阱
- 未来函数 / 偷价 / 幸存者偏差 / 过拟合
- 滑点 / 资金费率 / 手续费 / 冲击成本
- 多周期多品种 / Walk-forward / Purged K-Fold

---

**持续更新**：每完成一个模块后回到此文档打勾 + 补充实战经验。