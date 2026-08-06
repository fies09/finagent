# FinAgent

A quantitative trading analysis system powered by AI.

## Features

- **AI Analysis**: News sentiment analysis and market factor generation using DashScope
- **Data Management**: OHLCV data ingestion and storage
- **Backtesting**: Strategy backtest with lookback support
- **Risk Control**: Position limits, stop-loss, and trailing stops
- **Scheduled Tasks**: Automated price fetching and analysis
- **Feedback Loop**: Trade performance tracking

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  DataIngest │────→│  DataStore  │────→│AIAnalyzer   │
│  (ccxt)     │     │  (SQLite)   │     │(DashScope)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┘
                       ↓
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Backtest   │←────│  RiskMgr    │←────│  Feedback   │
│  Engine     │     │             │     │  Loop       │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Quick Start

### 1. Environment Setup

```bash
conda create -n finagent python=3.12 -y
conda activate finagent
pip install -r requirements.txt
```

### 2. Configuration

Edit `config/settings.py` or set environment variables:

```bash
export DASHSCOPE_API_KEY="your-api-key"
export SYMBOLS="BTC/USDT,ETH/USDT,SOL/USDT"
```

### 3. Run Server

```bash
python app.py
# or
uvicorn app:app --reload --port 8000
```

### 4. Verify

```bash
curl http://localhost:8000/
# {"status": "ok", "version": "0.1.0"}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/analyze/news` | POST | Analyze news sentiment |
| `/analyze/factor` | POST | Generate factor from OHLCV |
| `/backtest` | POST | Run strategy backtest |
| `/feedback/trades` | GET | Get trade feedback report |
| `/scheduler/start` | POST | Start scheduled tasks |
| `/scheduler/stop` | POST | Stop scheduled tasks |

### Usage Examples

```bash
# News analysis
curl -X POST http://localhost:8000/analyze/news \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "text": "Bitcoin ETF approved by SEC"}'

# Factor analysis
curl -X POST "http://localhost:8000/analyze/factor?symbol=BTC/USDT"

# Run backtest
curl -X POST http://localhost:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "days": 90}'

# Start scheduler
curl -X POST "http://localhost:8000/scheduler/start?symbols=BTC/USDT,ETH/USDT"
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | - | DashScope API key (required) |
| `EXCHANGE` | binance | Crypto exchange |
| `SYMBOLS` | BTC/USDT,ETH/USDT,SOL/USDT | Trading pairs |
| `FETCH_INTERVAL_MIN` | 15 | Price fetch interval (minutes) |
| `ANALYZE_INTERVAL_MIN` | 60 | Analysis interval (minutes) |
| `RISK_MAX_POSITION` | 0.06 | Max single position size |
| `RISK_STOP_LOSS` | -0.08 | Stop loss threshold |
| `AI_MIN_CONFIDENCE` | 0.6 | Minimum AI confidence |
| `AI_BUY_THRESHOLD` | 0.7 | Buy signal threshold |

## Tech Stack

- **Framework**: FastAPI + Uvicorn
- **Data**: CCXT + Pandas + PyArrow
- **AI**: DashScope (Qwen)
- **Scheduler**: APScheduler
- **Backtest**: Backtrader

## Project Structure

```
finagent/
├── app.py              # FastAPI entry
├── config/
│   └── settings.py     # Configuration
├── core/
│   ├── ai_analyzer.py  # AI analysis logic
│   ├── backtest.py     # Backtest engine
│   ├── feedback.py     # Performance feedback
│   ├── risk.py         # Risk management
│   ├── scheduler.py    # Task scheduler
│   └── store.py        # Data storage
├── data/               # OHLCV database
├── reports/            # Output reports
├── tests/              # Test cases
└── requirements.txt    # Dependencies
```

## License

MIT
