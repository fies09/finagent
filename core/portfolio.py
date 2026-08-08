from typing import Any

import numpy as np
import pandas as pd
from log import logger

try:
    from pypfopt import EfficientFrontier, expected_returns, risk_models
    HAS_PFOPT = True
except ImportError:
    HAS_PFOPT = False


class PortfolioOptimizer:
    def optimize(
        self,
        prices: pd.DataFrame,
        method: str = "markowitz",
        risk_free_rate: float = 0.02,
    ) -> dict[str, Any]:
        if not HAS_PFOPT:
            return {"error": "pyportfolioopt not installed"}
        if prices.empty or prices.shape[1] < 2:
            return {"error": "need at least 2 symbols with price history"}

        mu = expected_returns.mean_historical_return(prices, frequency=252)
        S = risk_models.sample_cov(prices, frequency=252)
        ef = EfficientFrontier(mu, S, weight_bounds=(0, 0.5))

        if method == "min_volatility":
            ef.min_volatility()
        elif method == "max_sharpe":
            ef.max_sharpe(risk_free_rate=risk_free_rate)
        elif method == "risk_parity":
            from pypfopt import objective
            w = ef.min_volatility()
            ef = EfficientFrontier(mu, S, weight_bounds=(0, 0.5))
            ef.add_objective(objective.L2_reg, gamma=0.1)
            ef.max_sharpe(risk_free_rate=risk_free_rate)
        else:
            ef.max_sharpe(risk_free_rate=risk_free_rate)

        weights = ef.clean_weights()
        perf = ef.portfolio_performance(verbose=False, risk_free_rate=risk_free_rate)
        return {
            "method": method,
            "weights": weights,
            "expected_return": round(float(perf[0]), 4),
            "volatility": round(float(perf[1]), 4),
            "sharpe": round(float(perf[2]), 4),
        }

    def equal_weight(self, symbols: list[str]) -> dict[str, float]:
        if not symbols:
            return {}
        w = 1.0 / len(symbols)
        return {s: round(w, 4) for s in symbols}