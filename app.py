from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.ai_analyzer import AIAnalyzer
from core.backtest import BacktestEngine
from core.feedback import FeedbackLoop
from core.risk import RiskConfig, RiskManager
from core.scheduler import Scheduler
from core.store import DataIngest, DataStore
from config.settings import HOST, PORT
from log import logger

app = FastAPI(title="FinAgent", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

store = DataStore()
ingest = DataIngest()
analyzer = AIAnalyzer()
risk = RiskManager()
feedback = FeedbackLoop(store)
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
def analyze_factor(symbol: str):
    logger.info(f"analyze_factor: {symbol}")
    df = store.load_ohlcv(symbol, ingest.exchange.name)
    if df.empty:
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

if __name__ == "__main__":
    logger.info(f"Starting FinAgent on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
