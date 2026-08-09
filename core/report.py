import io
from datetime import datetime
from typing import Any
import pandas as pd
from log import logger

try:
    import quantstats as qs
    _HAS_QS = True
except Exception:
    _HAS_QS = False


class ReportBuilder:
    def __init__(self):
        self.enabled = _HAS_QS

    def generate(self, df: pd.DataFrame, symbol: str, benchmark: str | None = None) -> dict:
        if not self.enabled or df.empty or len(df) < 30:
            return {"symbol": symbol, "engine": "fallback", "metrics": {}, "html": ""}
        try:
            closes = df.set_index(pd.to_datetime(df["timestamp"]))["close"].astype(float)
            closes = closes[~closes.index.duplicated(keep="last")].sort_index()
            rets = closes.pct_change().dropna()
            metrics = {
                "total_return": round(qs.stats.comp(rets) if hasattr(qs.stats, "comp") else (1 + rets).prod() - 1, 4),
                "cagr": round(qs.stats.cagr(rets), 4),
                "sharpe": round(qs.stats.sharpe(rets), 4),
                "sortino": round(qs.stats.sortino(rets), 4),
                "max_drawdown": round(qs.stats.max_drawdown(rets), 4),
                "volatility": round(qs.stats.volatility(rets), 4),
                "calmar": round(qs.stats.calmar(rets), 4),
                "win_rate": round(qs.stats.win_rate(rets), 4),
            }
            try:
                html = qs.reports.html(rets, symbol, output=None, title=f"{symbol} Strategy")
                if isinstance(html, tuple):
                    html = html[0]
                html = html if isinstance(html, str) else html.decode("utf-8") if isinstance(html, bytes) else ""
            except Exception as e:
                logger.warning(f"quantstats html failed: {e}")
                html = ""
            buf = io.StringIO()
            buf.write(f"{symbol} 回测报告\n")
            buf.write(f"生成时间: {datetime.utcnow().isoformat()}\n\n")
            for k, v in metrics.items():
                buf.write(f"{k}: {v}\n")
            return {
                "symbol": symbol,
                "engine": "quantstats",
                "metrics": metrics,
                "summary": buf.getvalue(),
                "html_length": len(html),
                "html": html[:5000] + ("...(截断)" if len(html) > 5000 else ""),
            }
        except Exception as e:
            logger.error(f"quantstats report failed: {e}")
            return {"symbol": symbol, "engine": "error", "error": str(e)}