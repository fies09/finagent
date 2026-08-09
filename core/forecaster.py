import pandas as pd
from log import logger

try:
    from neuralforecast import NeuralForecast
    from neuralforecast.models import NHITS
    _HAS_NF = True
except Exception:
    _HAS_NF = False


class TimeSeriesForecaster:
    def __init__(self, horizon: int = 12, input_size: int = 168, max_steps: int = 300):
        self.horizon = horizon
        self.input_size = input_size
        self.max_steps = max_steps
        self.enabled = _HAS_NF

    def predict(self, df: pd.DataFrame, symbol: str = "unknown") -> dict:
        if not self.enabled or df.empty or len(df) < self.input_size + self.horizon:
            return self._fallback(df, symbol)
        try:
            data = df.tail(self.input_size + self.horizon).copy()
            data["ds"] = pd.to_datetime(data["timestamp"])
            data["y"] = data["close"].astype(float)
            data["unique_id"] = symbol
            train = data[["unique_id", "ds", "y"]].reset_index(drop=True)
            models = [NHITS(
                h=self.horizon,
                input_size=self.input_size,
                max_steps=self.max_steps,
                scaler_type="standard",
                random_seed=42,
                val_check_steps=50,
            )]
            nf = NeuralForecast(models=models, freq="h")
            nf.fit(df=train)
            forecast = nf.predict()
            preds = forecast["NHITS"].tolist()
            last_close = float(data["y"].iloc[-1])
            return {
                "symbol": symbol,
                "engine": "neuralforecast/NHITS",
                "horizon": self.horizon,
                "last_close": round(last_close, 4),
                "predictions": [round(float(p), 4) for p in preds],
                "trend": "bullish" if preds[-1] > last_close else "bearish",
                "expected_change_pct": round((preds[-1] / last_close - 1) * 100, 2),
            }
        except Exception as e:
            logger.error(f"neuralforecast predict failed: {e}")
            return self._fallback(df, symbol)

    def _fallback(self, df: pd.DataFrame, symbol: str) -> dict:
        if df.empty:
            return {"symbol": symbol, "engine": "fallback", "predictions": [], "trend": "unknown"}
        closes = df["close"].astype(float).tail(24)
        mean = float(closes.mean())
        std = float(closes.std())
        last = float(closes.iloc[-1])
        preds = [last + (mean - last) * 0.05 * i for i in range(1, self.horizon + 1)]
        return {
            "symbol": symbol,
            "engine": "fallback/ma",
            "horizon": self.horizon,
            "last_close": round(last, 4),
            "predictions": [round(p, 4) for p in preds],
            "trend": "bullish" if preds[-1] > last else "bearish",
            "expected_change_pct": round((preds[-1] / last - 1) * 100, 2),
            "note": f"std={round(std, 4)}",
        }