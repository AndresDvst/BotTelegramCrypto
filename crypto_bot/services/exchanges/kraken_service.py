"""
Servicio de Kraken.
Endpoints públicos sin API key.
"""

import logging

from services.exchanges.base_exchange import BaseExchange

logger = logging.getLogger(__name__)

# Mapeo de pares comunes de Kraken a formato estándar
KRAKEN_PAIR_MAP = {
    "XXBTZUSD": "BTCUSDT",
    "XETHZUSD": "ETHUSDT",
    "XXRPZUSD": "XRPUSDT",
    "XLTCZUSD": "LTCUSDT",
    "XXLMZUSD": "XLMUSDT",
}


class KrakenService(BaseExchange):
    """Implementación del servicio de Kraken."""

    exchange_name: str = "kraken"
    base_url: str = "https://api.kraken.com"

    def _normalize_symbol(self, kraken_pair: str) -> str:
        """Normaliza un par de Kraken al formato estándar.

        Args:
            kraken_pair: Par en formato Kraken (ej: XXBTZUSD).

        Returns:
            Par en formato estándar (ej: BTCUSDT).
        """
        if kraken_pair in KRAKEN_PAIR_MAP:
            return KRAKEN_PAIR_MAP[kraken_pair]

        # Intentar normalización genérica
        pair = kraken_pair.upper()
        if pair.endswith("USD"):
            base = pair[:-3]
            if base.startswith("X"):
                base = base[1:]
            if base.startswith("Z"):
                base = base[1:]
            return f"{base}USDT"
        return pair

    def _to_kraken_symbol(self, symbol: str) -> str:
        """Convierte un símbolo estándar a formato Kraken.

        Args:
            symbol: Símbolo estándar (ej: BTCUSDT).

        Returns:
            Símbolo en formato Kraken.
        """
        # Buscar en el mapa inverso
        for kraken, standard in KRAKEN_PAIR_MAP.items():
            if standard == symbol:
                return kraken

        # Conversión genérica: BTCUSDT -> BTCUSD
        if symbol.endswith("USDT"):
            return symbol[:-1]  # Quitar la T final
        return symbol

    async def get_tickers(self) -> list[dict]:
        """Obtiene tickers de Kraken.

        Returns:
            Lista de dicts normalizados.
        """
        # Kraken requiere especificar pares, obtenemos la lista primero
        try:
            pairs_data = await self._make_request("/0/public/AssetPairs")
            result = pairs_data.get("result", {})

            # Filtrar pares con USD
            usd_pairs = [
                pair for pair in result.keys()
                if pair.endswith("USD") and not pair.endswith("ZUSD")
                or pair.endswith("ZUSD")
            ]

            if not usd_pairs:
                logger.warning("Kraken: no se encontraron pares USD")
                return []

            # Consultar tickers para los pares encontrados
            pairs_str = ",".join(usd_pairs[:50])  # Limitar a 50 pares
            ticker_data = await self._make_request("/0/public/Ticker", params={"pair": pairs_str})

        except Exception as e:
            logger.error(f"Error obteniendo tickers de Kraken: {e}")
            return []

        tickers = []
        ticker_result = ticker_data.get("result", {})

        for pair, info in ticker_result.items():
            try:
                last_price = float(info.get("c", [0])[0])
                open_price = float(info.get("o", 0))
                change_pct = ((last_price - open_price) / open_price * 100) if open_price > 0 else 0
                volume = float(info.get("v", [0, 0])[1])  # Volume 24h

                normalized_symbol = self._normalize_symbol(pair)

                tickers.append({
                    "symbol": normalized_symbol,
                    "price": last_price,
                    "price_change_percent_24h": change_pct,
                    "volume": volume,
                    "exchange": self.exchange_name
                })
            except (ValueError, TypeError, IndexError) as e:
                logger.error(f"Error parseando ticker {pair} de Kraken: {e}")
                continue

        logger.info(f"Kraken: {len(tickers)} pares USD obtenidos")
        return tickers

    async def get_klines(self, symbol: str, interval: str, limit: int) -> list:
        """Obtiene velas de Kraken.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            interval: Intervalo (ej: 1h).
            limit: Número de velas.

        Returns:
            Lista de velas normalizadas.
        """
        kraken_pair = self._to_kraken_symbol(symbol)

        # Convertir intervalo a minutos (formato Kraken)
        interval_map = {"1h": 60, "4h": 240, "1d": 1440}
        kraken_interval = interval_map.get(interval, 60)

        params = {
            "pair": kraken_pair,
            "interval": kraken_interval
        }
        data = await self._make_request("/0/public/OHLC", params=params)

        klines = []
        result = data.get("result", {})

        # Kraken retorna el resultado con el nombre del par como clave
        for key, candles in result.items():
            if key == "last":
                continue
            for candle in candles[-limit:]:  # Tomar solo las últimas 'limit' velas
                try:
                    klines.append({
                        "open_time": int(candle[0]),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[6])
                    })
                except (IndexError, ValueError, TypeError) as e:
                    logger.error(f"Error parseando kline de Kraken: {e}")
                    continue
            break  # Solo procesar la primera clave (que son los datos)

        return klines

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Obtiene el libro de órdenes de Kraken.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            limit: Número de órdenes por lado.

        Returns:
            Dict con bids y asks.
        """
        kraken_pair = self._to_kraken_symbol(symbol)

        params = {
            "pair": kraken_pair,
            "count": limit
        }
        data = await self._make_request("/0/public/Depth", params=params)

        result = data.get("result", {})

        bids = []
        asks = []

        for key, order_data in result.items():
            for bid in order_data.get("bids", [])[:limit]:
                try:
                    bids.append({
                        "price": float(bid[0]),
                        "quantity": float(bid[1])
                    })
                except (IndexError, ValueError, TypeError):
                    continue

            for ask in order_data.get("asks", [])[:limit]:
                try:
                    asks.append({
                        "price": float(ask[0]),
                        "quantity": float(ask[1])
                    })
                except (IndexError, ValueError, TypeError):
                    continue
            break  # Solo procesar la primera clave

        return {"bids": bids, "asks": asks}
