import os
from datetime import datetime, timedelta
from typing import Optional

import psycopg2
import psycopg2.extras
from loguru import logger


class PostgresStore:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv(
            "DATABASE_URL", "postgresql://finagent:finagent123@localhost:5433/finagent"
        )
        self._init_tables()

    def _get_conn(self):
        return psycopg2.connect(self.dsn)

    def _init_tables(self) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
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
                    CREATE INDEX IF NOT EXISTS idx_ohlcv_sym_ts
                        ON ohlcv(symbol, exchange, timestamp);

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
                    """
                )
            conn.commit()

    def save_ohlcv(self, records: list[dict]) -> None:
        if not records:
            return
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO ohlcv (symbol, exchange, timestamp, open, high, low, close, volume)
                    VALUES %s
                    ON CONFLICT (symbol, exchange, timestamp) DO NOTHING
                    """,
                    [
                        (r["symbol"], r["exchange"], r["timestamp"], r["open"], r["high"], r["low"], r["close"], r["volume"])
                        for r in records
                    ],
                    template="(%s, %s, %s, %s, %s, %s, %s, %s)",
                )
            conn.commit()

    def log_trade(self, **kwargs) -> int:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trade_journal
                    (symbol, side, entry_price, quantity, ai_sentiment, ai_confidence, ai_reasoning, entry_time, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        kwargs["symbol"],
                        kwargs["side"],
                        kwargs["entry_price"],
                        kwargs.get("quantity"),
                        kwargs.get("ai_sentiment"),
                        kwargs.get("ai_confidence"),
                        kwargs.get("ai_reasoning"),
                        datetime.utcnow(),
                        "open",
                    ),
                )
                trade_id = cur.fetchone()[0]
            conn.commit()
        return trade_id

    def close_trade(self, trade_id: int, exit_price: float, pnl: float) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE trade_journal
                    SET exit_price=%s, pnl=%s, exit_time=%s, status='closed'
                    WHERE id=%s
                    """,
                    (exit_price, pnl, datetime.utcnow(), trade_id),
                )
            conn.commit()

    def log_strategy_run(self, **kwargs) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO strategy_runs
                    (strategy_name, params, start_date, end_date, sharpe, max_drawdown, total_return, win_rate, report_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        kwargs.get("strategy_name"),
                        kwargs.get("params"),
                        kwargs.get("start_date"),
                        kwargs.get("end_date"),
                        kwargs.get("sharpe"),
                        kwargs.get("max_drawdown"),
                        kwargs.get("total_return"),
                        kwargs.get("win_rate"),
                        kwargs.get("report_path"),
                    ),
                )
            conn.commit()
