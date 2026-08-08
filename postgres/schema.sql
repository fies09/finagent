-- FinAgent 数据库 Schema
-- 包含 OHLCV、交易日志、策略运行记录

CREATE TABLE IF NOT EXISTS ohlcv (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    UNIQUE(symbol, exchange, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_sym_ts ON ohlcv(symbol, exchange, timestamp);

CREATE TABLE IF NOT EXISTS trade_journal (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    entry_price REAL,
    exit_price REAL,
    quantity REAL,
    pnl REAL,
    ai_sentiment REAL,
    ai_confidence REAL,
    ai_reasoning TEXT,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    status VARCHAR(10) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trade_symbol ON trade_journal(symbol);
CREATE INDEX IF NOT EXISTS idx_trade_created ON trade_journal(created_at);

CREATE TABLE IF NOT EXISTS strategy_runs (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    params TEXT,
    start_date DATE,
    end_date DATE,
    sharpe REAL,
    max_drawdown REAL,
    total_return REAL,
    win_rate REAL,
    report_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_strategy_name ON strategy_runs(strategy_name);