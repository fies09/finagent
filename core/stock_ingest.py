import pandas as pd
from datetime import datetime, timedelta
from log import logger

try:
    import yfinance as yf
    _HAS_YF = True
except Exception:
    _HAS_YF = False


class StockIngest:
    def __init__(self):
        self.enabled = _HAS_YF

    def fetch(
        self,
        symbol: str,
        period: str = "3mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        if not self.enabled:
            return pd.DataFrame()
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return df
            df = df.reset_index()
            rename = {"Date": "timestamp", "Datetime": "timestamp", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
            df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
            df["symbol"] = symbol
            return df[["timestamp", "open", "high", "low", "close", "volume", "symbol"]]
        except Exception as e:
            logger.error(f"yfinance fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    def quote(self, symbol: str) -> dict:
        if not self.enabled:
            return {"symbol": symbol, "error": "yfinance not installed"}
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info if hasattr(ticker, "fast_info") else {}
            return {
                "symbol": symbol,
                "last_price": float(info.get("last_price", 0.0)) if info else 0.0,
                "currency": getattr(info, "currency", "USD") if info else "USD",
                "source": "yfinance",
            }
        except Exception as e:
            logger.error(f"yfinance quote failed: {e}")
            return {"symbol": symbol, "error": str(e)}