# FinAgent 功能说明

> AI 量化交易分析系统 - 模块功能清单与使用指南
> 启动：`/Users/fanyong/miniforge3/envs/finagent/bin/python app.py`
> 访问：`http://127.0.0.1:8000`

---

## 一、核心模块（core/）

### 1.1 `ai_analyzer.py` — AI 分析引擎
- **作用**：调用 Claude Sonnet 5（通过 yiyongai 网关）做新闻情绪分析 + 因子解读
- **关键方法**：
  - `analyze_news(symbol, text, model)` → 返回 sentiment_score/impact_level/reasoning/confidence
  - `generate_factor(symbol, metrics)` → 基于价格/成交量数据识别异常因子
- **端点**：
  - `POST /analyze/news` — 单条新闻分析
  - `POST /analyze/factor?symbol=BTC/USDT` — 因子生成
- **JSON 兜底**：AI 返回 ```json``` 代码块自动剥离；解析失败返回默认值不报错

### 1.2 `factor.py` — 因子工程（pandas-ta）
- **作用**：计算 150+ 技术指标，生成量化信号
- **关键指标**：
  - RSI(14) — 超买超卖
  - MACD / Signal — 趋势动量
  - Bollinger Bands — 波动率通道
  - ATR(14) — 真实波幅（用于止损）
  - OBV — 能量潮
  - EMA(20/50) — 均线趋势
- **信号规则**：
  - `+1`（买入）：RSI<30 + 跌破布林下轨 / MACD金叉 + 站上EMA20
  - `-1`（卖出）：RSI>70 + 突破布林上轨 / MACD死叉 + 跌破EMA20
  - `0`（持有）：其他
- **端点**：`GET /factor/summary?symbol=BTC/USDT`

### 1.3 `vbt_engine.py` — 向量化回测（vectorbt）
- **作用**：100x 快于循环回测，支持多因子矩阵并行
- **输入**：带 `signal` 列的 OHLCV DataFrame
- **输出**：total_return / sharpe / max_drawdown / win_rate / equity_curve
- **端点**：`POST /backtest/vbt` — 自动用因子引擎生成信号后回测

### 1.4 `portfolio.py` — 组合优化（pyportfolioopt）
- **作用**：Markowitz 现代投资理论，优化多币种权重
- **方法**：
  - `max_sharpe` — 最大化夏普比率（推荐）
  - `min_volatility` — 最小化波动率
  - `risk_parity` — 风险平价
- **端点**：`GET /portfolio/optimize?method=max_sharpe`

### 1.5 `tracker.py` — 实验追踪（mlflow）
- **作用**：自动记录每次回测的参数、指标、标签
- **存储**：本地 `./mlruns/` 目录
- **端点**：`GET /experiments/runs?limit=20`
- **使用**：浏览器打开 MLflow UI 需额外启动 `mlflow ui --port 5000`

### 1.6 `risk.py` — 风险管理
- **作用**：仓位控制、最大回撤监控、止损
- **配置**（`RiskConfig`）：
  - `max_position=0.06` — 单仓位不超过 6%
  - `max_total=0.5` — 总仓位不超过 50%
  - `stop_loss=-0.08` — 止损 -8%
  - `trailing_stop=0.05` — 追踪止损 5%
  - `max_drawdown=-0.15` — 最大回撤 -15%
- **端点**：`GET /risk/status`

### 1.7 `backtest.py` — 事件驱动回测（backtrader）
- **作用**：传统逐 bar 回测，含完整交易日志
- **策略**：`AISignalStrategy` — 基于 ai_score / ai_confidence 决策
- **端点**：`POST /backtest` — 事件驱动回测（适合含 AI 信号对比）

### 1.8 `store.py` — 数据存储层
- **作用**：SQLite 本地持久化 + ccxt 行情接入
- **表**：`ohlcv` / `trade_journal` / `strategy_runs`
- **关键方法**：
  - `load_ohlcv(symbol, exchange)` → 加载 K 线
  - `log_trade(...)` → 记录开仓
  - `close_trade(trade_id, exit_price, pnl)` → 平仓
  - `list_open_positions()` → 当前持仓列表

### 1.9 `news_ingest.py` — 新闻抓取
- **作用**：从 4 大免费 RSS 源抓取加密新闻
- **源**：CoinDesk / Cointelegraph / CoinGape / Decrypt
- **端点**：
  - `GET /news/recent?symbol=BTC/USDT&hours=24&limit=20`
  - `POST /news/analyze?symbol=BTC/USDT&limit=5&model=claude-sonnet-5` — 抓取+AI分析

### 1.10 `feedback.py` — 交易反馈
- **作用**：统计历史交易的胜率、置信度阈值效果
- **端点**：`GET /feedback/trades?days=30`

### 1.11 `scheduler.py` — 任务调度
- **作用**：定时抓取行情 + 跑因子 + AI 决策
- **端点**：
  - `POST /scheduler/start?symbols=BTC/USDT,ETH/USDT`
  - `POST /scheduler/stop`

### 1.12 `cache.py` — Redis 缓存
- **作用**：行情/新闻缓存 15s/600s，Redis 不可用时降级 no-op
- **连接**：`redis://:redis123@localhost:6379/0`（infra-redis 容器）

---

## 二、API 路由速查

| 方法   | 路径                          | 说明                       |
|--------|-------------------------------|----------------------------|
| GET    | `/`                           | 前端主页                   |
| GET    | `/health`                     | 健康检查                   |
| GET    | `/market/price`               | 实时价格（15s 缓存）       |
| GET    | `/news/recent`                | 最新新闻                   |
| POST   | `/news/analyze`               | 抓取新闻+AI 分析           |
| POST   | `/analyze/news`               | 单条新闻 AI 分析           |
| POST   | `/analyze/factor`             | 生成因子假设               |
| GET    | `/factor/summary`             | 技术指标摘要               |
| POST   | `/backtest`                   | 事件驱动回测（backtrader） |
| POST   | `/backtest/vbt`               | 向量化回测（vectorbt）      |
| GET    | `/portfolio/optimize`         | 组合权重优化               |
| GET    | `/signal/latest`              | 最新 AI 信号               |
| GET    | `/risk/status`                | 风险状态                   |
| GET    | `/feedback/trades`            | 交易反馈报告               |
| GET    | `/experiments/runs`           | MLflow 实验列表            |
| POST   | `/scheduler/start`            | 启动调度器                 |
| POST   | `/scheduler/stop`             | 停止调度器                 |

---

## 三、前端 Tab 速查

| Tab        | 功能                                  |
|------------|---------------------------------------|
| 仪表盘     | 价格、新闻、信号、风险自动刷新（30s） |
| AI 分析    | 单条新闻分析、实时抓取、因子生成       |
| 回测引擎   | 事件驱动回测                          |
| 调度器     | 启停监控、交易反馈报告                 |
| 系统日志   | 服务状态展示                          |

---

## 四、常见问题

### Q1: `/analyze/factor` 返回 404？
A: 必须带 query 参数 `?symbol=BTC/USDT`，路由签名 `def analyze_factor(symbol: str = Query(...))`

### Q2: AI 返回 ```json``` 代码块解析失败？
A: 已修复。`_safe_json` 自动剥离 markdown 代码块 + 兜底返回默认值

### Q3: `vectorbt` / `pandas-ta` 装不上？
A: 安装顺序很重要。先装 numpy，再装 `pip install vectorbt pandas-ta pyportfolioopt mlflow`

### Q4: 没有 MLflow UI 怎么看实验？
A: 终端跑 `mlflow ui --port 5000`，浏览器访问 http://127.0.0.1:5000

### Q5: 新闻源 403？
A: 已移除 CryptoPanic（已取消免费 tier），现使用 4 个 RSS 源

---

## 五、未来扩展路线（已落地 + 待落地）

✅ 已落地：vectorbt / pandas-ta / pyportfolioopt / mlflow / quantstats
⏳ 待落地：
- `neuralforecast` — NHITS/TFT 时序预测
- `ccxt.pro` — 实盘下单
- `stable-baselines3` — 强化学习策略
- `optuna` — 超参搜索
- `plotly` — 前端图表