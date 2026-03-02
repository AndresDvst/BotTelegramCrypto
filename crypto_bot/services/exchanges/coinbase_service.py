"""
Servicio de Coinbase.
Endpoints públicos sin API key.
"""

import logging

from services.exchanges.base_exchange import BaseExchange

logger = logging.getLogger(__name__)


class CoinbaseService(BaseExchange):
    """Implementación del servicio de Coinbase."""

    exchange_name: str = "coinbase"
    base_url: str = "https://api.exchange.coinbase.com"

    async def get_tickers(self) -> list[dict]:
        """Obtiene todos los tickers de Coinbase.

        Returns:
            Lista de dicts normalizados.
        """
        # Primero obtener la lista de productos
        try:
            products = await self._make_request("/products")
        except Exception as e:
            logger.error(f"Error obteniendo productos de Coinbase: {e}")
            return []

        tickers = []

        # Filtrar solo pares USD
        usd_products = [
            p for p in products
            if isinstance(p, dict) and p.get("quote_currency") == "USD"
            and p.get("status") == "online"
        ]

        for product in usd_products[:50]:  # Limitar para no sobrecargar la API
            product_id = product.get("id", "")
            try:
                ticker_data = await self._make_request(f"/products/{product_id}/ticker")

                price = float(ticker_data.get("price", 0))
                # Coinbase no da cambio % directamente, lo obtenemos del open_24h
                open_24h = float(ticker_data.get("open_24h", 0) or 0)
                change_pct = ((price - open_24h) / open_24h * 100) if open_24h > 0 else 0
                volume = float(ticker_data.get("volume", 0))

                # Convertir formato BTC-USD a BTCUSDT
                base = product.get("base_currency", "")
                normalized_symbol = f"{base}USDT"

                tickers.append({
                    "symbol": normalized_symbol,
                    "price": price,
                    "price_change_percent_24h": change_pct,
                    "volume": volume,
                    "exchange": self.exchange_name
                })
            except Exception as e:
                logger.error(f"Error obteniendo ticker {product_id} de Coinbase: {e}")
                continue

        logger.info(f"Coinbase: {len(tickers)} pares USD obtenidos")
        return tickers

    async def get_klines(self, symbol: str, interval: str, limit: int) -> list:
        """Obtiene velas de Coinbase.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            interval: Intervalo (ej: 1h).
            limit: Número de velas.

        Returns:
            Lista de velas normalizadas.
        """
        # Convertir formato estándar a Coinbase: BTCUSDT -> BTC-USD
        if symbol.endswith("USDT"):
            coinbase_product = f"{symbol[:-4]}-USD"
        else:
            coinbase_product = symbol

        # Convertir intervalo a granularidad en segundos
        granularity_map = {"1h": 3600, "4h": 14400, "1d": 86400}
        granularity = granularity_map.get(interval, 3600)

        params = {
            "granularity": granularity
        }
        data = await self._make_request(
            f"/products/{coinbase_product}/candles",
            params=params
        )

        klines = []
        # Coinbase retorna [time, low, high, open, close, volume]
        candles = data if isinstance(data, list) else []
        for candle in candles[:limit]:
            try:
                klines.append({
                    "open_time": int(candle[0]),
                    "open": float(candle[3]),
                    "high": float(candle[2]),
                    "low": float(candle[1]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })
            except (IndexError, ValueError, TypeError) as e:
                logger.error(f"Error parseando kline de Coinbase: {e}")
                continue

        return klines

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Obtiene el libro de órdenes de Coinbase.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            limit: Número de órdenes por lado.

        Returns:
            Dict con bids y asks.
        """
        # Convertir formato estándar a Coinbase
        if symbol.endswith("USDT"):
            coinbase_product = f"{symbol[:-4]}-USD"
        else:
            coinbase_product = symbol

        params = {"level": 2}
        data = await self._make_request(
            f"/products/{coinbase_product}/book",
            params=params
        )

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
