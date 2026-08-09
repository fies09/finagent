import pandas as pd
from log import logger

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _HAS_OPTUNA = True
except Exception:
    _HAS_OPTUNA = False


class OptunaOptimizer:
    def __init__(self, n_trials: int = 30):
        self.n_trials = n_trials
        self.enabled = _HAS_OPTUNA

    def optimize_strategy(
        self,
        df: pd.DataFrame,
        symbol: str,
        initial_cash: float = 100000.0,
    ) -> dict:
        if not self.enabled or df.empty or len(df) < 100:
            return self._fallback(symbol)
        try:
            closes = df["close"].astype(float).reset_index(drop=True)
            ma_fast = closes.rolling(5).mean()
            ma_slow = closes.rolling(20).mean()
            position = (ma_fast > ma_slow).astype(int).fillna(0)
            returns = closes.pct_change().fillna(0)
            strategy_returns = position.shift(1).fillna(0) * returns

            def objective(trial: "optuna.Trial") -> float:
                fast = trial.suggest_int("fast", 3, 15)
                slow = trial.suggest_int("slow", 10, 60)
                threshold = trial.suggest_float("threshold", 0.0, 0.02)
                if slow <= fast:
                    raise optuna.TrialPruned()
                ma_f = closes.rolling(fast).mean()
                ma_s = closes.rolling(slow).mean()
                pos = (ma_f > ma_s * (1 + threshold)).astype(int).fillna(0)
                strat = pos.shift(1).fillna(0) * returns
                if strat.std() == 0:
                    return -10.0
                sharpe = (strat.mean() / strat.std()) * (252 ** 0.5)
                return float(sharpe)

            study = optuna.create_study(direction="maximize")
            study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)
            best = study.best_params
            best_value = study.best_value
            return {
                "symbol": symbol,
                "engine": "optuna/dual-ma",
                "trials": self.n_trials,
                "best_params": best,
                "best_sharpe": round(best_value, 4),
                "note": "fast/slow/threshold 双均线参数搜索",
            }
        except Exception as e:
            logger.error(f"optuna optimize failed: {e}")
            return self._fallback(symbol)

    def _fallback(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "engine": "fallback",
            "trials": 0,
            "best_params": {"fast": 5, "slow": 20, "threshold": 0.0},
            "best_sharpe": 0.0,
            "note": "optuna 不可用或数据不足",
        }