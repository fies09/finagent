from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from log import logger


@dataclass
class RiskConfig:
    max_position: float = 0.06
    max_total: float = 0.5
    max_sector: float = 0.25
    stop_loss: float = -0.08
    trailing_stop: float = 0.05
    max_drawdown: float = -0.15


class RiskManager:
    def __init__(self, config: RiskConfig | None = None):
        self.cfg = config or RiskConfig()
        self.positions: dict[str, dict[str, Any]] = {}
        self.peak_value: float = 0.0

    def can_open(self, symbol: str, price: float, cash: float, portfolio_value: float) -> bool:
        if portfolio_value <= 0:
            return False
        total_exposure = sum(p.get("value", 0) for p in self.positions.values())
        if total_exposure / portfolio_value >= self.cfg.max_total:
            logger.warning("max_total exposure reached")
            return False
        max_cash = portfolio_value * self.cfg.max_position
        if max_cash > cash:
            logger.warning(f"insufficient cash for {symbol}")
            return False
        return True

    def add_position(self, symbol: str, price: float, size: float) -> None:
        self.positions[symbol] = {
            "entry": price,
            "size": size,
            "value": price * size,
            "peak": price,
        }

    def update_price(self, symbol: str, price: float) -> str | None:
        pos = self.positions.get(symbol)
        if not pos:
            return None
        pos["value"] = price * pos["size"]
        if price > pos["peak"]:
            pos["peak"] = price
        entry = pos["entry"]
        pnl_pct = (price - entry) / entry
        if pnl_pct <= self.cfg.stop_loss:
            return "stop_loss"
        peak = pos["peak"]
        if peak > entry and (peak - price) / peak >= self.cfg.trailing_stop:
            return "trailing_stop"
        return None

    def remove_position(self, symbol: str) -> None:
        self.positions.pop(symbol, None)

    def check_portfolio_drawdown(self, current_value: float) -> bool:
        if current_value > self.peak_value:
            self.peak_value = current_value
        if self.peak_value <= 0:
            return False
        dd = (current_value - self.peak_value) / self.peak_value
        if dd <= self.cfg.max_drawdown:
            logger.warning(f"portfolio drawdown {dd:.2%} exceeds limit")
            return True
        return False

    def get_position_summary(self) -> dict[str, Any]:
        total = sum(p["value"] for p in self.positions.values())
        return {
            "count": len(self.positions),
            "total_value": total,
            "symbols": list(self.positions.keys()),
        }
