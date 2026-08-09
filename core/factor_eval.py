import pandas as pd
import numpy as np
from log import logger

try:
    from alphalens.utils import get_clean_factor_and_forward_returns
    from alphalens.tears import create_returns_tear_sheet, create_information_tear_sheet, create_summary_tear_sheet
    from alphalens.performance import factor_information_coefficient, mean_information_coefficient
    _HAS_AL = True
except Exception:
    _HAS_AL = False


class FactorEvaluator:
    def __init__(self):
        self.enabled = _HAS_AL

    def evaluate(
        self,
        prices: pd.DataFrame,
        factor: pd.Series,
        symbol: str = "factor",
        quantiles: int = 5,
    ) -> dict:
        if not self.enabled or prices.empty or factor.empty:
            return self._fallback(prices, factor, symbol)
        try:
            price_df = prices.copy()
            if not isinstance(price_df.index, pd.DatetimeIndex):
                if "timestamp" in price_df.columns:
                    price_df.index = pd.to_datetime(price_df["timestamp"])
                else:
                    price_df.index = pd.to_datetime(price_df.index)
            price_df = price_df[~price_df.index.duplicated(keep="last")].sort_index()

            if isinstance(factor, pd.Series):
                factor_data = factor.copy()
            else:
                factor_data = pd.Series(factor)
            if not isinstance(factor_data.index, pd.DatetimeIndex):
                if "timestamp" in factor_data.index if hasattr(factor_data.index, "name") else False:
                    factor_data.index = pd.to_datetime(factor_data.index)
            factor_data = factor_data.dropna()

            common_idx = price_df.index.intersection(factor_data.index)
            if len(common_idx) < 30:
                return self._fallback(prices, factor, symbol, "时间对齐后样本不足")

            factor_aligned = factor_data.reindex(common_idx).dropna()
            price_aligned = price_df["close"].reindex(common_idx).astype(float)

            factor_df = pd.DataFrame({"factor": factor_aligned})
            factor_df["asset"] = symbol
            factor_df = factor_df.reset_index().rename(columns={"index": "date", factor_df.index.name or "level_0": "date"})
            factor_df = factor_df[["date", "asset", "factor"]].set_index(["date", "asset"])["factor"]

            prices_panel = price_aligned.to_frame(name=symbol).reset_index().rename(columns={"index": "date"})
            prices_panel = prices_panel.rename(columns={"level_0": "date"})
            prices_panel = prices_panel.set_index(["date"]) if "date" in prices_panel.columns else prices_panel.set_index(prices_panel.columns[0])
            prices_panel = prices_panel[[symbol]].astype(float)

            clean_factor = get_clean_factor_and_forward_returns(
                factor=factor_aligned,
                prices=prices_panel,
                quantiles=quantiles,
                periods=(1, 5),
            )
            ic = factor_information_coefficient(clean_factor)
            mean_ic = mean_information_coefficient(ic).mean()
            return {
                "symbol": symbol,
                "engine": "alphalens",
                "rows": len(clean_factor),
                "ic_mean": round(float(mean_ic), 4),
                "ic_std": round(float(ic.std().mean()), 4) if hasattr(ic, "std") else 0,
                "quantiles": quantiles,
                "note": "IC > 0.05 视为有效因子，> 0.1 为强因子",
            }
        except Exception as e:
            logger.error(f"alphalens evaluate failed: {e}")
            return self._fallback(prices, factor, symbol, str(e))

    def _fallback(self, prices: pd.DataFrame, factor: pd.Series, symbol: str, note: str = "") -> dict:
        try:
            if prices.empty or factor.empty:
                return {"symbol": symbol, "engine": "fallback", "note": note or "数据不足"}
            closes = prices["close"].astype(float) if "close" in prices.columns else prices.iloc[:, 0].astype(float)
            returns = closes.pct_change().shift(-1)
            f = factor.reindex(closes.index).dropna() if isinstance(factor, pd.Series) else pd.Series(factor, index=closes.index).dropna()
            aligned = pd.concat([f, returns], axis=1, keys=["f", "ret"]).dropna()
            if len(aligned) < 10:
                return {"symbol": symbol, "engine": "fallback", "note": "样本不足"}
            corr = aligned["f"].corr(aligned["ret"])
            return {
                "symbol": symbol,
                "engine": "fallback/pearson",
                "ic": round(float(corr), 4),
                "rows": len(aligned),
                "note": "alphalens 不可用，使用皮尔森相关系数近似 IC",
            }
        except Exception as e:
            return {"symbol": symbol, "engine": "error", "error": str(e)}