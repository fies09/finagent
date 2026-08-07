import json
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from log import logger

from .store import DataStore


class FeedbackLoop:
    def __init__(self, store: DataStore | None = None):
        self.store = store or DataStore()

    def generate_report(self, days: int = 30) -> dict[str, Any]:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with pd.read_sql_query(
            "SELECT * FROM trade_journal WHERE created_at > ?",
            self.store.db_path,
            params=(since,),
        ) as df:
            if df.empty:
                return {"message": "no trades in period"}

            total_pnl = df["pnl"].sum()
            wins = (df["pnl"] > 0).sum()
            n = len(df)

            high_conf = df[df["ai_confidence"] >= 0.7]
            low_conf = df[df["ai_confidence"] < 0.7]

            return {
                "period_days": days,
                "total_trades": n,
                "win_rate": wins / n if n else 0.0,
                "total_pnl": total_pnl,
                "avg_pnl": df["pnl"].mean(),
                "high_conf_trades": len(high_conf),
                "high_conf_win_rate": (high_conf["pnl"] > 0).sum() / len(high_conf)
                if len(high_conf)
                else 0.0,
                "low_conf_trades": len(low_conf),
                "low_conf_win_rate": (low_conf["pnl"] > 0).sum() / len(low_conf)
                if len(low_conf)
                else 0.0,
                "recommendation": self._recommend(df),
            }

    def _recommend(self, df: pd.DataFrame) -> str:
        high = df[df["ai_confidence"] >= 0.7]
        low = df[df["ai_confidence"] < 0.7]
        if high.empty or low.empty:
            return "insufficient data for confidence threshold analysis"
        hw = (high["pnl"] > 0).mean()
        lw = (low["pnl"] > 0).mean()
        if hw > lw + 0.1:
            return "raise min_confidence threshold: high-confidence signals outperform"
        if lw > hw + 0.1:
            return "lower min_confidence threshold: low-confidence signals outperform"
        return "confidence threshold has limited predictive power, review other factors"

    def compare_strategies(self, strategy_names: list[str], days: int = 90) -> pd.DataFrame:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        query = """
            SELECT * FROM strategy_runs
            WHERE strategy_name IN ({}) AND created_at > ?
            ORDER BY created_at DESC
        """.format(",".join("?" * len(strategy_names)))
        with pd.read_sql_query(
            query, self.store.db_path, params=(*strategy_names, since)
        ) as df:
            if df.empty:
                return pd.DataFrame()
            return df.groupby("strategy_name").agg(
                {
                    "sharpe": "mean",
                    "max_drawdown": "mean",
                    "total_return": "mean",
                    "win_rate": "mean",
                    "runs": "count",
                }
            ).reset_index()
