import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import ccxt
import pandas as pd
from log import logger


class DataStore:
    def __init__(self, db_path: str = "./data/finagent.db", data_dir: str = "./data"):
        self.db_path = Path(db_path)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ohlcv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    quantity REAL,
                    pnl REAL,
                    ai_sentiment REAL,
                    ai_confidence REAL,
                    ai_reasoning TEXT,
                    entry_time TEXT,
                    exit_time TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS strategy_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    params TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    sharpe REAL,
                    max_drawdown REAL,
                    total_return REAL,
                    win_rate REAL,
                    report_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    source TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
                CREATE INDEX IF NOT EXISTS idx_logs_time ON system_logs(created_at);
                """
            )

    def save_ohlcv(self, df: pd.DataFrame, symbol: str, exchange: str) -> None:
        if df.empty:
            return
        df = df.copy()
        df["symbol"] = symbol
        df["exchange"] = exchange
        cols = ["symbol", "exchange", "timestamp", "open", "high", "low", "close", "volume"]
        with sqlite3.connect(self.db_path) as conn:
            df[cols].to_sql("ohlcv", conn, if_exists="append", index=False)

    def load_ohlcv(
        self,
        symbol: str,
        exchange: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        query = "SELECT * FROM ohlcv WHERE symbol=? AND LOWER(exchange)=LOWER(?)"
        params: list = [symbol, exchange]
        if start:
            query += " AND timestamp >= ?"
            params.append(int(start.timestamp() * 1000))
        if end:
            query += " AND timestamp <= ?"
            params.append(int(end.timestamp() * 1000))
        query += " ORDER BY timestamp"
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)

    def log_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        ai_sentiment: float,
        ai_confidence: float,
        ai_reasoning: str,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO trade_journal
                (symbol, side, entry_price, quantity, ai_sentiment, ai_confidence, ai_reasoning, entry_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    side,
                    entry_price,
                    quantity,
                    ai_sentiment,
                    ai_confidence,
                    ai_reasoning,
                    datetime.utcnow().isoformat(),
                    "open",
                ),
            )
            conn.commit()
            return cur.lastrowid or 0

    def close_trade(self, trade_id: int, exit_price: float, pnl: float) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE trade_journal
                SET exit_price=?, pnl=?, exit_time=?, status='closed'
                WHERE id=?
                """,
                (exit_price, pnl, datetime.utcnow().isoformat(), trade_id),
            )
            conn.commit()

    def list_open_positions(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trade_journal WHERE status='open' ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def log_strategy_run(self, **kwargs) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO strategy_runs
                (strategy_name, params, start_date, end_date, sharpe, max_drawdown, total_return, win_rate, report_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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


class DataIngest:
    def __init__(self, exchange_name: str = "binance"):
        self.exchange = getattr(ccxt, exchange_name)({"enableRateLimit": True})
        self.store = DataStore()

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if not raw:
                return pd.DataFrame()
            df = pd.DataFrame(
                raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            self.store.save_ohlcv(df, symbol, self.exchange.name)
            return df
        except Exception as e:
            logger.error(f"fetch_ohlcv failed: {e}")
            return pd.DataFrame()

    def backfill(self, symbol: str, timeframe: str = "1h", days: int = 365) -> None:
        since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
        all_data: list = []
        while True:
            df = self.fetch_ohlcv(symbol, timeframe, since=since, limit=500)
            if df.empty:
                break
            all_data.append(df)
            since = int(df["timestamp"].iloc[-1].timestamp() * 1000) + 1
            if len(df) < 500:
                break
        if all_data:
            full = pd.concat(all_data, ignore_index=True).drop_duplicates(
                subset=["timestamp"]
            )
            self.store.save_ohlcv(full, symbol, self.exchange.name)
            logger.info(f"backfill {symbol}: {len(full)} rows")
