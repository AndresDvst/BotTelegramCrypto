"""
Servicio de Bybit.
Endpoints públicos sin API key.
"""

import logging

from services.exchanges.base_exchange import BaseExchange

logger = logging.getLogger(__name__)


class BybitService(BaseExchange):
    """Implementación del servicio de Bybit."""

    exchange_name: str = "bybit"
    base_url: str = "https://api.bybit.com"

    async def get_tickers(self) -> list[dict]:
        """Obtiene todos los tickers de Bybit.

        Returns:
            Lista de dicts normalizados.
        """
        data = await self._make_request("/v5/market/tickers", params={"category": "spot"})
        tickers = []

        result_list = data.get("result", {}).get("list", [])
        for item in result_list:
            symbol = item.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue

            try:
                last_price = float(item.get("lastPrice", 0))
                prev_price = float(item.get("prevPrice24h", 0))
                change_pct = ((last_price - prev_price) / prev_price * 100) if prev_price > 0 else 0

                tickers.append({
                    "symbol": symbol,
                    "price": last_price,
                    "price_change_percent_24h": change_pct,
                    "volume": float(item.get("turnover24h", 0)),
                    "exchange": self.exchange_name
                })
            except (ValueError, TypeError) as e:
                logger.error(f"Error parseando ticker {symbol} de Bybit: {e}")
                continue

        logger.info(f"Bybit: {len(tickers)} pares USDT obtenidos")
        return tickers

    async def get_klines(self, symbol: str, interval: str, limit: int) -> list:
        """Obtiene velas de Bybit.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            interval: Intervalo (ej: 60 para 1h en Bybit).
            limit: Número de velas.

        Returns:
            Lista de velas normalizadas.
        """
        # Bybit usa minutos para el intervalo: 1h = "60", 4h = "240"
        bybit_interval = interval
        if interval == "1h":
            bybit_interval = "60"
        elif interval == "4h":
            bybit_interval = "240"
        elif interval == "1d":
            bybit_interval = "D"

        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": bybit_interval,
            "limit": limit
        }
        data = await self._make_request("/v5/market/kline", params=params)

        klines = []
        result_list = data.get("result", {}).get("list", [])
        for candle in result_list:
            try:
                klines.append({
                    "open_time": int(candle[0]),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })
            except (IndexError, ValueError, TypeError) as e:
                logger.error(f"Error parseando kline de Bybit: {e}")
                continue

        return klines

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Obtiene el libro de órdenes de Bybit.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            limit: Número de órdenes por lado.

        Returns:
            Dict con bids y asks.
        """
        params = {
            "category": "spot",
            "symbol": symbol,
            "limit": limit
        }
        data = await self._make_request("/v5/market/orderbook", params=params)

        result = data.get("result", {})
        bids = []
        for bid in result.get("b", [])[:limit]:
            try:
                bids.append({
                    "price": float(bid[0]),
                    "quantity": float(bid[1])
                })
            except (IndexError, ValueError, TypeError):
                continue

        asks = []
        for ask in result.get("a", [])[:limit]:
            try:
                asks.append({
                    "price": float(ask[0]),
                    "quantity": float(ask[1])
                })
            except (IndexError, ValueError, TypeError):
                continue

        return {"bids": bids, "asks": asks}
