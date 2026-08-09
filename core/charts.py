import json
import pandas as pd
from log import logger

try:
    import plotly.graph_objects as go
    from plotly.utils import PlotlyJSONEncoder
    _HAS_PLOTLY = True
except Exception:
    _HAS_PLOTLY = False


class ChartBuilder:
    def __init__(self):
        self.enabled = _HAS_PLOTLY

    def candlestick(self, df: pd.DataFrame, symbol: str, limit: int = 200) -> dict:
        if not self.enabled or df.empty:
            return {"symbol": symbol, "engine": "fallback", "error": "plotly unavailable or empty df"}
        try:
            data = df.tail(limit).copy()
            if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
                try:
                    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
                except Exception:
                    data["timestamp"] = pd.to_datetime(data["timestamp"])
            fig = go.Figure(data=[go.Candlestick(
                x=data["timestamp"],
                open=data["open"],
                high=data["high"],
                low=data["low"],
                close=data["close"],
                name=symbol,
            )])
            fig.update_layout(
                title=f"{symbol} K线",
                xaxis_title="时间",
                yaxis_title="价格",
                template="plotly_dark",
                height=420,
            )
            return {
                "symbol": symbol,
                "engine": "plotly/candlestick",
                "chart_json": json.loads(json.dumps(fig.to_plotly_json(), cls=PlotlyJSONEncoder)),
                "rows": len(data),
            }
        except Exception as e:
            logger.error(f"candlestick failed: {e}")
            return {"symbol": symbol, "engine": "error", "error": str(e)}

    def equity_curve(self, returns: list[float], symbol: str = "strategy") -> dict:
        if not self.enabled or not returns:
            return {"symbol": symbol, "engine": "fallback"}
        try:
            equity = (1 + pd.Series(returns).fillna(0)).cumprod()
            fig = go.Figure(data=[go.Scatter(
                x=list(range(len(equity))),
                y=equity.tolist(),
                mode="lines",
                name="equity",
                line=dict(color="#00d4aa", width=2),
            )])
            fig.update_layout(
                title=f"{symbol} 资金曲线",
                xaxis_title="期数",
                yaxis_title="净值",
                template="plotly_dark",
                height=320,
            )
            return {
                "symbol": symbol,
                "engine": "plotly/equity",
                "chart_json": json.loads(json.dumps(fig.to_plotly_json(), cls=PlotlyJSONEncoder)),
            }
        except Exception as e:
            logger.error(f"equity_curve failed: {e}")
            return {"symbol": symbol, "engine": "error", "error": str(e)}