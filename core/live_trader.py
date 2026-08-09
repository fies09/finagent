import asyncio
from typing import Optional
import ccxt.pro as ccxtpro
from log import logger


class LiveTrader:
    def __init__(self, exchange_name: str = "okx", api_key: str = "", secret: str = "", password: str = ""):
        self.exchange_name = exchange_name.lower()
        self.api_key = api_key
        self.secret = secret
        self.password = password
        self.exchange: Optional[ccxtpro.Exchange] = None

    async def connect(self):
        try:
            cls = getattr(ccxtpro, self.exchange_name)
            config: dict = {"enableRateLimit": True, "options": {"defaultType": "spot"}}
            if self.api_key:
                config["apiKey"] = self.api_key
            if self.secret:
                config["secret"] = self.secret
            if self.password:
                config["password"] = self.password
            self.exchange = cls(config)
            await self.exchange.load_markets()
            logger.info(f"LiveTrader connected to {self.exchange_name}")
        except Exception as e:
            logger.error(f"LiveTrader connect failed: {e}")
            raise

    async def disconnect(self):
        if self.exchange:
            await self.exchange.close()
            self.exchange = None

    async def get_balance(self, currency: str = "USDT") -> dict:
        if not self.exchange:
            raise RuntimeError("not connected")
        try:
            bal = await self.exchange.fetch_balance()
            free = bal.get("free", {}).get(currency, 0.0)
            used = bal.get("used", {}).get(currency, 0.0)
            total = bal.get("total", {}).get(currency, 0.0)
            return {"currency": currency, "free": free, "used": used, "total": total}
        except Exception as e:
            logger.error(f"get_balance failed: {e}")
            return {"currency": currency, "free": 0.0, "used": 0.0, "total": 0.0, "error": str(e)}

    async def create_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = "market",
    ) -> dict:
        if not self.exchange:
            raise RuntimeError("not connected")
        try:
            params: dict = {}
            if self.exchange_name == "okx":
                params["tdMode"] = "cash"
            order = await self.exchange.create_order(symbol, order_type, side, amount, price, params)
            return {
                "order_id": order.get("id"),
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "amount": amount,
                "price": price,
                "status": order.get("status"),
                "raw": order,
            }
        except Exception as e:
            logger.error(f"create_order failed: {e}")
            return {"error": str(e), "symbol": symbol, "side": side, "amount": amount}

    async def cancel_order(self, order_id: str, symbol: str) -> dict:
        if not self.exchange:
            raise RuntimeError("not connected")
        try:
            result = await self.exchange.cancel_order(order_id, symbol)
            return {"order_id": order_id, "symbol": symbol, "status": result.get("status"), "raw": result}
        except Exception as e:
            logger.error(f"cancel_order failed: {e}")
            return {"error": str(e), "order_id": order_id, "symbol": symbol}

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> list:
        if not self.exchange:
            raise RuntimeError("not connected")
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(f"fetch_open_orders failed: {e}")
            return []

    async def fetch_ticker(self, symbol: str) -> dict:
        if not self.exchange:
            raise RuntimeError("not connected")
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "last": ticker.get("last"),
                "timestamp": ticker.get("timestamp"),
            }
        except Exception as e:
            logger.error(f"fetch_ticker failed: {e}")
            return {"symbol": symbol, "error": str(e)}