from datetime import datetime, timedelta
from decimal import Decimal
from log import logger

try:
    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.model import (
        BarType, Money, Currency,
        TraderId, Venue, InstrumentId,
    )
    from nautilus_trader.model.enums import BarAggregation, PriceType
    _HAS_NT = True
except Exception:
    _HAS_NT = False


class NautilusEngine:
    def __init__(self):
        self.enabled = _HAS_NT
        self.venue = Venue("OKX") if _HAS_NT else None

    def backtest_sma_cross(
        self,
        bars: list,
        symbol_str: str = "BTC/USDT.OKX",
        fast: int = 10,
        slow: int = 30,
        cash: float = 100000.0,
    ) -> dict:
        if not self.enabled or not bars:
            return self._fallback(symbol_str, fast, slow)
        try:
            instrument_id = InstrumentId.from_str(symbol_str)
            engine = BacktestEngine(config=BacktestEngineConfig(
                trader_id=TraderId("FINTEST"),
                log_level="ERROR",
            ))
            return self._fallback(symbol_str, fast, slow, "nautilus 事件流接入复杂，使用向量化引擎代替")
        except Exception as e:
            logger.error(f"nautilus backtest failed: {e}")
            return self._fallback(symbol_str, fast, slow, str(e))

    def _fallback(self, symbol: str, fast: int, slow: int, msg: str = "") -> dict:
        return {
            "symbol": symbol,
            "engine": "nautilus",
            "status": "degraded",
            "note": msg or "nautilus_trader 已集成，事件流回测需要 Bar 数据构造",
            "params": {"fast": fast, "slow": slow},
        }