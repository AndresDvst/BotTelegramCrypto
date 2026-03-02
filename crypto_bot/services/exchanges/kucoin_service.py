"""
Servicio de KuCoin.
Endpoints públicos sin API key.
"""

import logging
import time

from services.exchanges.base_exchange import BaseExchange

logger = logging.getLogger(__name__)


class KuCoinService(BaseExchange):
    """Implementación del servicio de KuCoin."""

    exchange_name: str = "kucoin"
    base_url: str = "https://api.kucoin.com"

    async def get_tickers(self) -> list[dict]:
        """Obtiene todos los tickers de KuCoin.

        Returns:
            Lista de dicts normalizados.
        """
        data = await self._make_request("/api/v1/market/allTickers")
        tickers = []

        ticker_list = data.get("data", {}).get("ticker", [])
        for item in ticker_list:
            symbol = item.get("symbol", "")
            # KuCoin usa formato BTC-USDT
            if not symbol.endswith("-USDT"):
                continue

            try:
                change_rate = float(item.get("changeRate", 0))
                change_pct = change_rate * 100

                # Convertir formato KuCoin (BTC-USDT) a formato estándar (BTCUSDT)
                normalized_symbol = symbol.replace("-", "")

                tickers.append({
                    "symbol": normalized_symbol,
                    "price": float(item.get("last", 0)),
                    "price_change_percent_24h": change_pct,
                    "volume": float(item.get("volValue", 0)),
                    "exchange": self.exchange_name
                })
            except (ValueError, TypeError) as e:
                logger.error(f"Error parseando ticker {symbol} de KuCoin: {e}")
                continue

        logger.info(f"KuCoin: {len(tickers)} pares USDT obtenidos")
        return tickers

    async def get_klines(self, symbol: str, interval: str, limit: int) -> list:
        """Obtiene velas de KuCoin.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT, se convierte a BTC-USDT).
            interval: Intervalo (ej: 1hour).
            limit: Número de velas.

        Returns:
            Lista de velas normalizadas.
        """
        # Convertir formato estándar a KuCoin
        kucoin_symbol = symbol
        if "USDT" in symbol and "-" not in symbol:
            kucoin_symbol = symbol.replace("USDT", "-USDT")

        # Convertir intervalo a formato KuCoin
        kucoin_interval = interval
        if interval == "1h":
            kucoin_interval = "1hour"
        elif interval == "4h":
            kucoin_interval = "4hour"
        elif interval == "1d":
            kucoin_interval = "1day"

        end_at = int(time.time())
        # Calcular inicio basado en intervalo y cantidad de velas
        interval_seconds = {"1hour": 3600, "4hour": 14400, "1day": 86400}
        seconds = interval_seconds.get(kucoin_interval, 3600)
        start_at = end_at - (seconds * limit)

        params = {
            "symbol": kucoin_symbol,
            "type": kucoin_interval,
            "startAt": start_at,
            "endAt": end_at
        }
        data = await self._make_request("/api/v1/market/candles", params=params)

        klines = []
        candle_list = data.get("data", [])
        for candle in candle_list:
            try:
                klines.append({
                    "open_time": int(candle[0]),
                    "open": float(candle[1]),
                    "high": float(candle[3]),
                    "low": float(candle[4]),
                    "close": float(candle[2]),
                    "volume": float(candle[5])
                })
            except (IndexError, ValueError, TypeError) as e:
                logger.error(f"Error parseando kline de KuCoin: {e}")
                continue

        return klines

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Obtiene el libro de órdenes de KuCoin.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT, se convierte a BTC-USDT).
            limit: Número de órdenes por lado.

        Returns:
            Dict con bids y asks.
        """
        # Convertir formato estándar a KuCoin
        kucoin_symbol = symbol
        if "USDT" in symbol and "-" not in symbol:
            kucoin_symbol = symbol.replace("USDT", "-USDT")

        data = await self._make_request(
            f"/api/v1/market/orderbook/level2_20",
            params={"symbol": kucoin_symbol}
        )

        order_data = data.get("data", {})
        bids = []
        for bid in order_data.get("bids", [])[:limit]:
            try:
                bids.append({
                    "price": float(bid[0]),
                    "quantity": float(bid[1])
                })
            except (IndexError, ValueError, TypeError):
                continue

        asks = []
        for ask in order_data.get("asks", [])[:limit]:
            try:
                asks.append({
                    "price": float(ask[0]),
                    "quantity": float(ask[1])
                })
            except (IndexError, ValueError, TypeError):
                continue

        return {"bids": bids, "asks": asks}
