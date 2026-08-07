import os
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from log import logger

from .ai_analyzer import AIAnalyzer
from .store import DataIngest, DataStore


class Scheduler:
    def __init__(self, symbols: list[str], fetch_interval: int = 15, analyze_interval: int = 60):
        self.symbols = symbols
        self.ingest = DataIngest(exchange_name=os.getenv("EXCHANGE", "binance"))
        self.analyzer = AIAnalyzer()
        self.store = DataStore()
        self.scheduler = BackgroundScheduler()
        self.fetch_interval = fetch_interval
        self.analyze_interval = analyze_interval

    def _fetch_job(self) -> None:
        for symbol in self.symbols:
            df = self.ingest.fetch_ohlcv(symbol, timeframe="1h", limit=100)
            if not df.empty:
                logger.info(f"fetched {symbol}: {len(df)} rows")

    def _analyze_job(self) -> None:
        for symbol in self.symbols:
            df = self.store.load_ohlcv(symbol, self.ingest.exchange.name, limit=50)
            if df.empty:
                continue
            metrics = {
                "latest_price": float(df["close"].iloc[-1]),
                "change_24h": float(df["close"].iloc[-1] / df["close"].iloc[-25] - 1)
                if len(df) >= 25
                else 0.0,
                "volume_trend": float(df["volume"].tail(10).mean() / df["volume"].tail(50).mean())
                if len(df) >= 50
                else 1.0,
            }
            result = self.analyzer.generate_factor(symbol, metrics)
            logger.info(f"AI factor {symbol}: {result}")

    def start(self) -> None:
        self.scheduler.add_job(
            self._fetch_job,
            IntervalTrigger(minutes=self.fetch_interval),
            id="fetch",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._analyze_job,
            IntervalTrigger(minutes=self.analyze_interval),
            id="analyze",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("scheduler started")

    def shutdown(self) -> None:
        self.scheduler.shutdown()
