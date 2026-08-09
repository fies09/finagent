import pandas as pd
from log import logger

try:
    import polars as pl
    _HAS_PL = True
except Exception:
    _HAS_PL = False


class FastDataEngine:
    def __init__(self):
        self.enabled = _HAS_PL

    def compute_returns(self, df: pd.DataFrame, symbol: str = "unknown") -> dict:
        if not self.enabled or df.empty:
            return {"symbol": symbol, "engine": "fallback", "error": "polars unavailable"}
        try:
            pl_df = pl.from_pandas(df[["timestamp", "open", "high", "low", "close", "volume"]])
            pl_df = pl_df.with_columns([
                pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False),
                pl.col("close").cast(pl.Float64),
            ]).sort("timestamp")
            res = pl_df.with_columns([
                ((pl.col("close") / pl.col("close").shift(1)) - 1).alias("return_1h"),
                ((pl.col("close") / pl.col("close").shift(24)) - 1).alias("return_24h"),
                ((pl.col("close") / pl.col("close").shift(168)) - 1).alias("return_168h"),
                pl.col("close").rolling_mean(window_size=20).alias("ma20"),
                pl.col("close").rolling_std(window_size=20).alias("std20"),
                pl.col("volume").rolling_mean(window_size=20).alias("vol_ma20"),
            ])
            out = res.to_pandas()
            stats = {
                "mean_return_1h": float(out["return_1h"].mean()) if "return_1h" in out else 0,
                "std_return_1h": float(out["return_1h"].std()) if "return_1h" in out else 0,
                "mean_return_24h": float(out["return_24h"].mean()) if "return_24h" in out else 0,
                "mean_return_168h": float(out["return_168h"].mean()) if "return_168h" in out else 0,
                "last_ma20": float(out["ma20"].iloc[-1]) if "ma20" in out and not out["ma20"].isna().all() else None,
                "last_vol_ma20": float(out["vol_ma20"].iloc[-1]) if "vol_ma20" in out and not out["vol_ma20"].isna().all() else None,
            }
            return {
                "symbol": symbol,
                "engine": "polars",
                "rows": len(out),
                "stats": stats,
                "last_rows": out.tail(10).to_dict(orient="records"),
            }
        except Exception as e:
            logger.error(f"polars compute failed: {e}")
            return {"symbol": symbol, "engine": "error", "error": str(e)}

    def correlation_matrix(self, symbols_data: dict) -> dict:
        if not self.enabled or not symbols_data:
            return {"engine": "fallback", "error": "no data"}
        try:
            frames = []
            for sym, df in symbols_data.items():
                if df.empty:
                    continue
                pl_df = pl.from_pandas(df[["timestamp", "close"]].rename(columns={"close": sym}))
                frames.append(pl_df)
            if not frames:
                return {"engine": "fallback", "error": "no valid data"}
            merged = frames[0]
            for f in frames[1:]:
                merged = merged.join(f, on="timestamp", how="inner")
            corr = merged.select([pl.col(c) for c in merged.columns if c != "timestamp"]).corr()
            return {
                "engine": "polars",
                "symbols": [c for c in merged.columns if c != "timestamp"],
                "matrix": corr.to_dicts(),
            }
        except Exception as e:
            logger.error(f"polars corr failed: {e}")
            return {"engine": "error", "error": str(e)}