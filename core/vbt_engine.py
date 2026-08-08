from typing import Any

import numpy as np
import pandas as pd
from log import logger

try:
    import vectorbt as vbt
    HAS_VBT = True
except ImportError:
    HAS_VBT = False


class VectorBacktest:
    def run(
        self,
        df: pd.DataFrame,
        signal_col: str = "signal",
        init_cash: float = 100000.0,
        fees: float = 0.001,
    ) -> dict[str, Any]:
        if not HAS_VBT:
            return {"error": "vectorbt not installed"}
        if df.empty or signal_col not in df.columns:
            return {"error": "invalid dataframe or missing signal column"}

        close = df["close"]
        signals = df[signal_col].fillna(0).astype(int)
        entries = signals == 1
        exits = signals == -1

        pf = vbt.Portfolio.from_signals(
            close=close,
            entries=entries,
            exits=exits,
            init_cash=init_cash,
            fees=fees,
            freq="1h",
        )

        stats = pf.stats()
        return {
            "total_return": round(float(stats.get("Total Return", 0)), 4),
            "sharpe": round(float(stats.get("Sharpe Ratio", 0)), 3),
            "max_drawdown": round(float(stats.get("Max Drawdown", 0)), 4),
            "win_rate": round(float(stats.get("Win Rate", 0)), 4),
            "total_trades": int(stats.get("Total Trades", 0)),
            "final_value": round(float(pf.value().iloc[-1]), 2),
            "equity_curve": pf.value().tail(200).round(2).tolist(),
        }