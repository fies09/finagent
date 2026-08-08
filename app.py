from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from core.ai_analyzer import AIAnalyzer
from core.backtest import BacktestEngine
from core.feedback import FeedbackLoop
from core.factor import FactorEngine
from core.log_store import LogStore
from core.portfolio import PortfolioOptimizer
from core.risk import RiskConfig, RiskManager
from core.scheduler import Scheduler
from core.store import DataIngest, DataStore
from core.tracker import ExperimentTracker
from core.vbt_engine import VectorBacktest
from config.settings import HOST, PORT
from log import logger
import pandas as pd

app = FastAPI(title="FinAgent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

store = DataStore()
ingest = DataIngest()
analyzer = AIAnalyzer()
risk = RiskManager()
feedback = FeedbackLoop(store)
log_store = LogStore(store)
log_store.install_listener()
from core.news_ingest import NewsIngest
from core.cache import CacheClient
news_ingest = NewsIngest()
cache = CacheClient()
factor_engine = FactorEngine()
vector_engine = VectorBacktest()
optimizer = PortfolioOptimizer()
tracker = ExperimentTracker()
scheduler: Scheduler | None = None

class NewsRequest(BaseModel):
    symbol: str
    text: str
    model: str | None = None

class BacktestRequest(BaseModel):
    symbol: str
    days: int = 90
    params: dict | None = None

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/ui")
def ui():
    return FileResponse("static/index.html")

@app.post("/analyze/news")
def analyze_news(req: NewsRequest):
    logger.info(f"analyze_news: {req.symbol}")
    result = analyzer.analyze_news(req.symbol, req.text, req.model)
    return {"symbol": req.symbol, **result}

@app.post("/analyze/factor")
def analyze_factor(symbol: str = Query(..., description="交易对，如 BTC/USDT")):
    logger.info(f"analyze_factor: {symbol}")
    df = store.load_ohlcv(symbol, ingest.exchange.name)
    if df.empty:
        logger.warning(f"analyze_factor no data: {symbol}")
        raise HTTPException(status_code=404, detail="no data")
    metrics = {
        "latest_price": float(df["close"].iloc[-1]),
        "change_24h": float(df["close"].iloc[-1] / df["close"].iloc[-25] - 1)
        if len(df) >= 25
        else 0.0,
        "volume_trend": float(df["volume"].tail(10).mean() / df["volume"].tail(50).mean())
        if len(df) >= 50
        else 1.0,
    }
    return analyzer.generate_factor(symbol, metrics)

@app.post("/backtest")
def run_backtest(req: BacktestRequest):
    logger.info(f"backtest: {req.symbol}, days={req.days}")
    df = store.load_ohlcv(req.symbol, ingest.exchange.name)
    if df.empty or len(df) < 50:
        raise HTTPException(status_code=404, detail="insufficient data")
    df["ai_score"] = 0.0
    df["ai_confidence"] = 0.0
    engine = BacktestEngine()
    engine.add_data(df, req.symbol)
    result = engine.run(req.params or {})
    return {"symbol": req.symbol, **result}

@app.get("/feedback/trades")
def trade_feedback(days: int = 30):
    logger.info(f"feedback: last {days} days")
    return feedback.generate_report(days)

@app.post("/scheduler/start")
def start_scheduler(symbols: str = "BTC/USDT,ETH/USDT"):
    global scheduler
    if scheduler and scheduler.scheduler.running:
        return {"status": "already running"}
    scheduler = Scheduler(symbols.split(","))
    scheduler.start()
    logger.info(f"scheduler started: {symbols}")
    return {"status": "started", "symbols": symbols.split(",")}

@app.post("/scheduler/stop")
def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
    logger.info("scheduler stopped")
    return {"status": "stopped"}

@app.get("/market/price")
def market_price(symbol: str = "BTC/USDT"):
    cache_key = f"price:{symbol}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    import time
    base_prices = {"BTC/USDT": 68000.0, "ETH/USDT": 3500.0, "SOL/USDT": 165.0}
    base = base_prices.get(symbol, 100.0)
    try:
        df = store.load_ohlcv(symbol, ingest.exchange.name)
        if not df.empty and len(df) >= 25:
            price = float(df["close"].iloc[-1])
            prev = float(df["close"].iloc[-25])
            change_pct = (price / prev - 1) * 100 if prev else 0
        else:
            import time
            base = base_prices.get(symbol, 100.0)
            t = time.time()
            wave1 = 0.015 * ((t / 60) % 13 - 6.5) / 13
            wave2 = 0.008 * ((t / 120) % 17 - 8.5) / 17
            price = base * (1 + wave1 + wave2)
            change_pct = 5 * (((t / 300) % 7) - 3.5) / 3.5
        result = {"symbol": symbol, "price": round(price, 2), "change_24h_pct": round(change_pct, 2), "source": "live" if not df.empty else "fallback"}
        cache.set(cache_key, result, ttl=15)
        return result
    except Exception as e:
        logger.error(f"market_price failed: {e}")
        return {"symbol": symbol, "price": base, "change_24h_pct": 0, "source": "fallback"}


@app.get("/risk/status")
def risk_status():
    pos = store.list_open_positions()
    exposure = risk.total_exposure(pos)
    return {
        "position_count": len(pos),
        "total_exposure": round(exposure, 2),
        "max_drawdown": round(risk.max_drawdown(), 2),
        "status": "normal" if risk.check() else "alert",
    }


@app.get("/signal/latest")
def latest_signal(symbol: str = "BTC/USDT"):
    items = recent_news(symbol=symbol, limit=1)["news"]
    if not items:
        return {"signal": "--", "confidence": 0, "strength": 0, "symbols": []}
    r = analyzer.analyze_news(symbol, items[0].get("text", ""))
    score = r.get("sentiment_score", 0)
    return {
        "signal": "buy" if score > 0.3 else "sell" if score < -0.3 else "hold",
        "confidence": r.get("confidence", 0),
        "strength": abs(score),
        "symbols": items[0].get("symbols", []),
    }


@app.get("/factor/summary")
def factor_summary(symbol: str = "BTC/USDT"):
    df = store.load_ohlcv(symbol, ingest.exchange.name)
    if df.empty:
        raise HTTPException(status_code=404, detail="no data")
    return factor_engine.summary(df)


@app.post("/backtest/vbt")
def backtest_vbt(req: BacktestRequest):
    df = store.load_ohlcv(req.symbol, ingest.exchange.name)
    if df.empty or len(df) < 60:
        raise HTTPException(status_code=404, detail="insufficient data (need >=60 rows)")
    df = factor_engine.generate_signals(df)
    result = vector_engine.run(df)
    tracker.log_backtest(
        req.symbol,
        params={"engine": "vectorbt", "days": req.days, **(req.params or {})},
        metrics=result,
        tags={"symbol": req.symbol, "engine": "vbt"},
    )
    return {"symbol": req.symbol, **result}


@app.get("/portfolio/optimize")
def portfolio_optimize(method: str = "max_sharpe"):
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    prices = pd.DataFrame()
    for s in symbols:
        df = store.load_ohlcv(s, ingest.exchange.name)
        if not df.empty:
            prices[s] = df.set_index("timestamp")["close"] if "timestamp" in df.columns else df["close"]
    if prices.empty:
        raise HTTPException(status_code=404, detail="no price data")
    return optimizer.optimize(prices, method=method)


@app.get("/experiments/runs")
def list_experiments(limit: int = 20):
    return {"runs": tracker.list_runs(limit)}


@app.get("/logs")
def list_logs(level: str | None = None, limit: int = 100):
    return {"logs": log_store.list_logs(level=level, limit=limit)}


@app.post("/logs/clear")
def clear_logs():
    log_store.clear()
    return {"status": "cleared"}


@app.get("/news/recent")
def recent_news(symbol: str = "BTC/USDT", hours: int = 24, limit: int = 20):
    cache_key = f"news:{symbol}:{hours}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    items = news_ingest.fetch_all()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    out = []
    for it in items:
        if symbol.upper() not in [s.upper() for s in it.get("symbols", [])]:
            continue
        try:
            ts = datetime.fromisoformat(it.get("published_at", "").replace("Z", "+00:00"))
            if ts >= cutoff:
                out.append(it)
        except Exception:
            out.append(it)
        if len(out) >= limit:
            break
    result = {"symbol": symbol, "count": len(out), "news": out}
    cache.set(cache_key, result, ttl=600)
    return result


@app.post("/news/analyze")
def news_analyze_batch(symbol: str = "BTC/USDT", limit: int = 5, model: str | None = None):
    items = recent_news(symbol=symbol, limit=limit)["news"]
    results = []
    for it in items:
        r = analyzer.analyze_news(symbol, it.get("text", ""), model)
        results.append({"title": it.get("title", ""), "url": it.get("url", ""), **r})
    return {"symbol": symbol, "results": results}


if __name__ == "__main__":
    logger.info(f"Starting FinAgent on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
