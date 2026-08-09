import json
from typing import Any

import backtrader as bt
import pandas as pd
from log import logger


class AISignalData(bt.feeds.PandasData):
    lines = ("ai_score", "ai_confidence")
    params = (("ai_score", -1), ("ai_confidence", -1))


class AISignalStrategy(bt.Strategy):
    params = dict(
        buy_threshold=0.7,
        sell_threshold=-0.3,
        min_confidence=0.6,
        max_position=0.06,
        max_total=0.5,
        stop_loss=-0.08,
        trailing_stop=0.05,
    )

    def __init__(self):
        self.ai_signal = self.datas[0].ai_score
        self.confidence = self.datas[0].ai_confidence
        self.order = None
        self.trade_log: list[dict[str, Any]] = []

    def notify_order(self, order):
        if order.status in [order.Completed]:
            action = "BUY" if order.isbuy() else "SELL"
            logger.info(f"{action} {order.data._name} @ {order.executed.price:.2f}")
        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnlcomm
            self.trade_log.append(
                {
                    "symbol": trade.data._name,
                    "pnl": pnl,
                    "size": trade.size,
                    "entry": trade.price,
                    "exit": trade.exitprice,
                }
            )
            logger.info(f"Trade closed PnL: {pnl:.2f}")

    def next(self):
        if self.order:
            return
        if self.confidence[0] < self.p.min_confidence:
            return

        cash = self.broker.getcash()
        value = self.broker.getvalue()
        current_pos = self.position.size

        if self.ai_signal[0] > self.p.buy_threshold and current_pos == 0:
            max_cash = value * self.p.max_position
            size = int(max_cash / self.data.close[0])
            if size > 0:
                self.order = self.buy(size=size)

        elif self.ai_signal[0] < self.p.sell_threshold and current_pos > 0:
            self.order = self.sell(size=current_pos)

    def stop(self):
        total = sum(t["pnl"] for t in self.trade_log)
        wins = sum(1 for t in self.trade_log if t["pnl"] > 0)
        n = len(self.trade_log)
        logger.info(
            f"Backtest done: trades={n}, total_pnl={total:.2f}, "
            f"win_rate={wins / n if n else 0:.2%}"
        )


class BacktestEngine:
    def __init__(self, cash: float = 100000.0, commission: float = 0.0003):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(cash)
        self.cerebro.broker.setcommission(commission=commission)
        self.cerebro.broker.set_slippage_perc(0.001)

    def add_data(self, df: pd.DataFrame, symbol: str) -> None:
        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            try:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            except (ValueError, TypeError):
                df["timestamp"] = pd.to_datetime(df["timestamp"])
        feed = AISignalData(
            dataname=df,
            datetime="timestamp",
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            ai_score="ai_score",
            ai_confidence="ai_confidence",
        )
        feed._name = symbol
        self.cerebro.adddata(feed)

    def run(
        self,
        strategy_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = strategy_params or {}
        self.cerebro.addstrategy(AISignalStrategy, **params)
        results = self.cerebro.run()
        strat = results[0]

        final_value = self.cerebro.broker.getvalue()
        initial = self.cerebro.broker.startingcash
        total_return = (final_value - initial) / initial

        trades = strat.trade_log
        wins = sum(1 for t in trades if t["pnl"] > 0)
        n = len(trades)

        return {
            "total_return": total_return,
            "final_value": final_value,
            "trades": n,
            "win_rate": wins / n if n else 0.0,
            "trade_log": trades,
        }
