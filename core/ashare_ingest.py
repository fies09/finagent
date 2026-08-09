import pandas as pd
from datetime import datetime, timedelta
from log import logger

try:
    import akshare as ak
    _HAS_AK = True
except Exception:
    _HAS_AK = False


class AShareIngest:
    def __init__(self):
        self.enabled = _HAS_AK

    def fetch_daily(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        if not self.enabled:
            return pd.DataFrame()
        try:
            if not start:
                start = (datetime.utcnow() - timedelta(days=180)).strftime("%Y%m%d")
            if not end:
                end = datetime.utcnow().strftime("%Y%m%d")
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust=adjust,
            )
            if df.empty:
                return df
            rename = {"日期": "timestamp", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume"}
            df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["symbol"] = symbol
            return df[["timestamp", "open", "high", "low", "close", "volume", "symbol"]]
        except Exception as e:
            logger.error(f"akshare fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_spot(self) -> pd.DataFrame:
        if not self.enabled:
            return pd.DataFrame()
        try:
            df = ak.stock_zh_a_spot_em()
            keep = ["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额"]
            return df[[c for c in keep if c in df.columns]].head(100)
        except Exception as e:
            logger.error(f"akshare spot failed: {e}")
            return pd.DataFrame()