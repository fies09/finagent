from typing import Any

import numpy as np
import pandas as pd
import pandas_ta as ta
from log import logger


class FactorEngine:
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 60:
            return df
        df = df.copy()
        df["rsi_14"] = ta.rsi(df["close"], length=14)
        df["macd"] = ta.macd(df["close"], fast=12, slow=26, signal=9).iloc[:, 0]
        df["macd_signal"] = ta.macd(df["close"], fast=12, slow=26, signal=9).iloc[:, 1]
        df["bb_upper"] = ta.bbands(df["close"], length=20, std=2).iloc[:, 0]
        df["bb_mid"] = ta.bbands(df["close"], length=20, std=2).iloc[:, 1]
        df["bb_lower"] = ta.bbands(df["close"], length=20, std=2).iloc[:, 2]
        df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        df["obv"] = ta.obv(df["close"], df["volume"])
        df["ema_20"] = ta.ema(df["close"], length=20)
        df["ema_50"] = ta.ema(df["close"], length=50)
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.compute(df)
        if df.empty:
            return df
        df["signal"] = 0
        df.loc[(df["rsi_14"] < 30) & (df["close"] < df["bb_lower"]), "signal"] = 1
        df.loc[(df["rsi_14"] > 70) & (df["close"] > df["bb_upper"]), "signal"] = -1
        df.loc[(df["macd"] > df["macd_signal"]) & (df["close"] > df["ema_20"]), "signal"] = 1
        df.loc[(df["macd"] < df["macd_signal"]) & (df["close"] < df["ema_20"]), "signal"] = -1
        return df

    def summary(self, df: pd.DataFrame) -> dict[str, Any]:
        if df.empty or len(df) < 60:
            return {"error": "insufficient data (need >=60 rows)"}
        df = self.compute(df)
        last = df.iloc[-1]
        return {
            "rsi_14": round(float(last["rsi_14"]), 2),
            "macd": round(float(last["macd"]), 4),
            "macd_signal": round(float(last["macd_signal"]), 4),
            "bb_position": round(float((last["close"] - last["bb_lower"]) / (last["bb_upper"] - last["bb_lower"])), 3),
            "atr_14": round(float(last["atr_14"]), 2),
            "obv_trend": round(float(df["obv"].iloc[-1] - df["obv"].iloc[-20]), 0),
            "trend": "bullish" if last["ema_20"] > last["ema_50"] else "bearish",
            "signal": int(self.generate_signals(df).iloc[-1]["signal"]),
        }