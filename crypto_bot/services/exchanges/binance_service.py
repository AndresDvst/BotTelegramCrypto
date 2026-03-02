"""
Servicio de Binance.
Endpoints públicos sin API key.
"""

import logging

from services.exchanges.base_exchange import BaseExchange

logger = logging.getLogger(__name__)


class BinanceService(BaseExchange):
    """Implementación del servicio de Binance."""

    exchange_name: str = "binance"
    base_url: str = "https://api.binance.com"

    async def get_tickers(self) -> list[dict]:
        """Obtiene todos los tickers de Binance.

        Returns:
            Lista de dicts normalizados con symbol, price, price_change_percent_24h, volume.
        """
        data = await self._make_request("/api/v3/ticker/24hr")
        tickers = []

        for item in data:
            symbol = item.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue

            try:
                tickers.append({
                    "symbol": symbol,
                    "price": float(item.get("lastPrice", 0)),
                    "price_change_percent_24h": float(item.get("priceChangePercent", 0)),
                    "volume": float(item.get("quoteVolume", 0)),
                    "exchange": self.exchange_name
                })
            except (ValueError, TypeError) as e:
                logger.error(f"Error parseando ticker {symbol} de Binance: {e}")
                continue

        logger.info(f"Binance: {len(tickers)} pares USDT obtenidos")
        return tickers

    async def get_klines(self, symbol: str, interval: str, limit: int) -> list:
        """Obtiene velas de Binance.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            interval: Intervalo (ej: 1h, 4h).
            limit: Número de velas.

        Returns:
            Lista de velas [open_time, open, high, low, close, volume, ...].
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        data = await self._make_request("/api/v3/klines", params=params)

        klines = []
        for candle in data:
            try:
                klines.append({
                    "open_time": candle[0],
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })
            except (IndexError, ValueError, TypeError) as e:
                logger.error(f"Error parseando kline de Binance: {e}")
                continue

        return klines

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Obtiene el libro de órdenes de Binance.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            limit: Número de órdenes por lado.

        Returns:
            Dict con bids y asks.
        """
        params = {
            "symbol": symbol,
            "limit": limit
        }
        data = await self._make_request("/api/v3/depth", params=params)

        bids = []
        for bid in data.get("bids", [])[:limit]:
            try:
                bids.append({
                    "price": float(bid[0]),
                    "quantity": float(bid[1])
                })
            except (IndexError, ValueError, TypeError):
                continue

        asks = []
        for ask in data.get("asks", [])[:limit]:
            try:
                asks.append({
                    "price": float(ask[0]),
                    "quantity": float(ask[1])
                })
            except (IndexError, ValueError, TypeError):
                continue

        return {"bids": bids, "asks": asks}
