"""
Agregador de datos de todos los exchanges.
Consulta en paralelo, deduplica, y retorna top movers con fallback a Binance.
"""

import logging
import asyncio

import aiohttp

from config.config import Config
from services.exchanges.binance_service import BinanceService
from services.exchanges.bybit_service import BybitService
from services.exchanges.kucoin_service import KuCoinService
from services.exchanges.kraken_service import KrakenService
from services.exchanges.coinbase_service import CoinbaseService
from database.metrics_manager import metrics_manager

logger = logging.getLogger(__name__)

MIN_VOLUME_USDT = 100_000
MAX_KLINES_CONCURRENCY = 10


class ExchangeAggregator:
    """Agrega datos de todos los exchanges con fallback a Binance."""

    def __init__(self) -> None:
        """Inicializa el agregador con instancias de todos los exchanges."""
        self.binance = BinanceService()
        self.bybit = BybitService()
        self.kucoin = KuCoinService()
        self.kraken = KrakenService()
        self.coinbase = CoinbaseService()
        self.exchanges = [
            self.binance,
            self.bybit,
            self.kucoin,
            self.kraken,
            self.coinbase
        ]

    async def get_top_movers(self, timeframe: str, direction: str, top_n: int = 10) -> list[dict]:
        """Obtiene las criptomonedas con mayor movimiento.

        Args:
            timeframe: '4h' o '24h'.
            direction: 'up' o 'down'.
            top_n: Número de resultados a retornar.

        Returns:
            Lista de dicts con: symbol, price, change_pct, market_cap, buy_sell_ratio, exchange_source.
        """
        # Consultar todos los exchanges en paralelo
        all_tickers = await self._fetch_tickers_without_coinbase()

        if not all_tickers:
            logger.warning("Todos los exchanges fallaron, intentando solo Binance como fallback")
            try:
                all_tickers = await self.binance.get_tickers()
            except Exception as e:
                logger.error(f"Fallback a Binance también falló: {e}")
                return []

        # Deduplicar por símbolo (quedarse con el de mayor volumen)
        deduplicated = self._deduplicate_tickers(all_tickers)

        # Calcular cambio % según timeframe
        if timeframe == "4h":
            deduplicated = await self._calculate_4h_change(deduplicated)
        # Para 24h usamos el cambio que ya viene de los tickers

        # Ordenar según dirección
        if direction == "up":
            key_field = "change_pct" if timeframe == "4h" else "price_change_percent_24h"
            sorted_tickers = sorted(
                deduplicated,
                key=lambda x: x.get(key_field, 0),
                reverse=True
            )
        else:
            key_field = "change_pct" if timeframe == "4h" else "price_change_percent_24h"
            sorted_tickers = sorted(
                deduplicated,
                key=lambda x: x.get(key_field, 0)
            )

        # Tomar top N
        top_movers = sorted_tickers[:top_n]

        # Enriquecer con datos adicionales
        enriched = await self._enrich_data(top_movers, timeframe)

        return enriched

    async def get_orderbook_aggregated(self, symbol: str, limit: int = 20) -> dict:
        """Obtiene el libro de órdenes agregado de todos los exchanges.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            limit: Número de órdenes por lado.

        Returns:
            Dict con bids y asks agregados.
        """
        tasks = []
        for exchange in self.exchanges:
            tasks.append(self._safe_orderbook(exchange, symbol, limit))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_bids = []
        all_asks = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Error obteniendo orderbook de {self.exchanges[i].exchange_name}: {result}"
                )
                continue
            if isinstance(result, dict):
                all_bids.extend(result.get("bids", []))
                all_asks.extend(result.get("asks", []))

        # Ordenar: bids de mayor a menor precio, asks de menor a mayor
        all_bids.sort(key=lambda x: x.get("price", 0), reverse=True)
        all_asks.sort(key=lambda x: x.get("price", 0))

        return {
            "bids": all_bids[:limit],
            "asks": all_asks[:limit]
        }

    async def get_coin_data(self, symbol: str) -> dict:
        """Obtiene datos completos de una criptomoneda desde todos los exchanges.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).

        Returns:
            Dict con precio, cambios, volumen, etc.
        """
        # Buscar en todos los exchanges
        all_tickers = await self._fetch_tickers_without_coinbase()
        if not all_tickers:
            try:
                all_tickers = await self.binance.get_tickers()
            except Exception:
                return {}

        # Buscar el símbolo
        coin_data = None
        for ticker in all_tickers:
            if ticker.get("symbol") == symbol:
                if coin_data is None or ticker.get("volume", 0) > coin_data.get("volume", 0):
                    coin_data = ticker

        if not coin_data:
            return {}

        # Obtener cambio 4h
        try:
            klines = await self.binance.get_klines(symbol, "1h", 4)
            if klines and len(klines) >= 2:
                open_price = klines[0].get("open", 0)
                close_price = klines[-1].get("close", 0)
                change_4h = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0
                coin_data["change_pct_4h"] = round(change_4h, 2)
        except Exception as e:
            logger.error(f"Error calculando cambio 4h para {symbol}: {e}")
            coin_data["change_pct_4h"] = 0

        # Obtener orderbook para ratio compra/venta
        try:
            orderbook = await self._get_orderbook_without_coinbase(symbol, 20)
            bid_volume = sum(b.get("quantity", 0) * b.get("price", 0) for b in orderbook.get("bids", []))
            ask_volume = sum(a.get("quantity", 0) * a.get("price", 0) for a in orderbook.get("asks", []))
            total_volume = bid_volume + ask_volume
            if total_volume > 0:
                buy_ratio = round((bid_volume / total_volume) * 100, 1)
                sell_ratio = round((ask_volume / total_volume) * 100, 1)
            else:
                buy_ratio = 50.0
                sell_ratio = 50.0
            coin_data["buy_sell_ratio"] = f"{buy_ratio}% / {sell_ratio}%"
        except Exception as e:
            logger.error(f"Error obteniendo orderbook para {symbol}: {e}")
            coin_data["buy_sell_ratio"] = "50% / 50%"

        # Obtener capitalización de mercado de CoinGecko
        coin_data["market_cap"] = await self._get_market_cap(symbol)

        return coin_data

    async def _fetch_all_tickers(self) -> list[dict]:
        """Consulta tickers de todos los exchanges en paralelo.

        Returns:
            Lista combinada de tickers de todos los exchanges.
        """
        tasks = [self._safe_tickers(exchange) for exchange in self.exchanges]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_tickers = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Exchange {self.exchanges[i].exchange_name} falló: {result}"
                )
                continue
            if isinstance(result, list):
                all_tickers.extend(result)
                logger.info(
                    f"{self.exchanges[i].exchange_name}: {len(result)} tickers obtenidos"
                )

        return all_tickers

    async def _safe_tickers(self, exchange) -> list[dict]:
        """Wrapper seguro para obtener tickers de un exchange.

        Args:
            exchange: Instancia del exchange.

        Returns:
            Lista de tickers o lista vacía si hay error.
        """
        try:
            return await exchange.get_tickers()
        except Exception as e:
            logger.error(f"Error en {exchange.exchange_name}.get_tickers(): {e}")
            raise

    async def _safe_orderbook(self, exchange, symbol: str, limit: int) -> dict:
        """Wrapper seguro para obtener orderbook de un exchange.

        Args:
            exchange: Instancia del exchange.
            symbol: Símbolo del par.
            limit: Número de órdenes.

        Returns:
            Dict con orderbook o dict vacío si hay error.
        """
        try:
            return await exchange.get_orderbook(symbol, limit)
        except Exception as e:
            logger.error(f"Error en {exchange.exchange_name}.get_orderbook(): {e}")
            raise

    def _deduplicate_tickers(self, tickers: list[dict]) -> list[dict]:
        """Deduplica tickers por símbolo, manteniendo el de mayor volumen.

        Args:
            tickers: Lista de tickers con posibles duplicados.

        Returns:
            Lista de tickers deduplicados.
        """
        symbol_map: dict[str, dict] = {}

        for ticker in tickers:
            symbol = ticker.get("symbol", "")
            if symbol in symbol_map:
                if ticker.get("volume", 0) > symbol_map[symbol].get("volume", 0):
                    symbol_map[symbol] = ticker
            else:
                symbol_map[symbol] = ticker

        return list(symbol_map.values())

    async def _calculate_4h_change(self, tickers: list[dict]) -> list[dict]:
        """Calcula el cambio porcentual de las últimas 4 horas usando klines.

        Args:
            tickers: Lista de tickers.

        Returns:
            Lista de tickers con campo change_pct actualizado.
        """
        # Usar Binance para obtener klines de las top monedas por volumen
        sorted_by_volume = sorted(tickers, key=lambda x: x.get("volume", 0), reverse=True)
        top_by_volume = sorted_by_volume[:100]  # Limitar para no sobrecargar

        tickers_filtrados = [
            ticker for ticker in top_by_volume
            if float(ticker.get("quoteVolume", ticker.get("volume", 0)) or 0) >= MIN_VOLUME_USDT
        ]
        logger.info(
            "Pares filtrados por volumen: %s descartados de %s totales",
            len(top_by_volume) - len(tickers_filtrados),
            len(top_by_volume)
        )

        semaforo = asyncio.Semaphore(MAX_KLINES_CONCURRENCY)

        async def get_klines_con_limite(symbol: str) -> float:
            async with semaforo:
                return await self._get_4h_change(symbol)

        results = await asyncio.gather(
            *[get_klines_con_limite(ticker.get("symbol", "")) for ticker in tickers_filtrados],
            return_exceptions=True
        )

        for i, result in enumerate(results):
            if isinstance(result, (int, float)):
                tickers_filtrados[i]["change_pct"] = result
            else:
                tickers_filtrados[i]["change_pct"] = 0

        return tickers_filtrados

    async def _get_4h_change(self, symbol: str) -> float:
        """Calcula el cambio % de 4h para un símbolo.

        Args:
            symbol: Símbolo del par.

        Returns:
            Cambio porcentual de las últimas 4 horas.
        """
        try:
            klines = await self.binance.get_klines(symbol, "1h", 4)
            if klines and len(klines) >= 2:
                open_price = klines[0].get("open", 0)
                close_price = klines[-1].get("close", 0)
                if open_price > 0:
                    return round(((close_price - open_price) / open_price) * 100, 2)
        except Exception as e:
            logger.error(f"Error calculando cambio 4h para {symbol}: {e}")
        return 0.0

    async def _enrich_data(self, movers: list[dict], timeframe: str) -> list[dict]:
        """Enriquece los datos del top movers con market cap y ratio compra/venta.

        Args:
            movers: Lista de top movers.
            timeframe: '4h' o '24h'.

        Returns:
            Lista enriquecida con market_cap y buy_sell_ratio.
        """
        enriched = []

        for mover in movers:
            symbol = mover.get("symbol", "")
            change_field = "change_pct" if timeframe == "4h" else "price_change_percent_24h"

            enriched_item = {
                "symbol": symbol,
                "price": mover.get("price", 0),
                "change_pct": mover.get(change_field, 0),
                "exchange_source": mover.get("exchange", "unknown")
            }

            # Market cap de CoinGecko
            enriched_item["market_cap"] = await self._get_market_cap(symbol)

            # Ratio compra/venta del orderbook
            try:
                orderbook = await self.binance.get_orderbook(symbol, 20)
                bid_vol = sum(b.get("quantity", 0) * b.get("price", 0) for b in orderbook.get("bids", []))
                ask_vol = sum(a.get("quantity", 0) * a.get("price", 0) for a in orderbook.get("asks", []))
                total = bid_vol + ask_vol
                if total > 0:
                    buy_pct = round((bid_vol / total) * 100, 1)
                    sell_pct = round((ask_vol / total) * 100, 1)
                else:
                    buy_pct = 50.0
                    sell_pct = 50.0
                enriched_item["buy_sell_ratio"] = f"{buy_pct}% / {sell_pct}%"
            except Exception:
                enriched_item["buy_sell_ratio"] = "N/A"

            enriched.append(enriched_item)

        return enriched

    async def _get_market_cap(self, symbol: str) -> str:
        """Obtiene la capitalización de mercado de CoinGecko.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).

        Returns:
            Market cap formateado como string.
        """
        # Extraer el símbolo base (sin USDT)
        base_symbol = symbol.replace("USDT", "").lower()

        # Mapeo de símbolos comunes a IDs de CoinGecko
        symbol_to_coingecko = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "bnb": "binancecoin",
            "sol": "solana",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "dot": "polkadot",
            "avax": "avalanche-2",
            "link": "chainlink",
            "matic": "matic-network",
            "ltc": "litecoin",
            "uni": "uniswap",
            "atom": "cosmos",
            "xlm": "stellar",
            "near": "near",
            "apt": "aptos",
            "arb": "arbitrum",
            "op": "optimism",
            "sui": "sui",
        }

        coingecko_id = symbol_to_coingecko.get(base_symbol)
        if not coingecko_id:
            return "N/A"

        try:
            import aiohttp
            import time

            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=Config.HTTP_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"https://api.coingecko.com/api/v3/simple/price"
                params = {
                    "ids": coingecko_id,
                    "vs_currencies": "usd",
                    "include_market_cap": "true"
                }
                async with session.get(url, params=params) as response:
                    response_time = (time.time() - start_time) * 1000
                    if response.status == 200:
                        data = await response.json()
                        market_cap = data.get(coingecko_id, {}).get("usd_market_cap", 0)
                        metrics_manager.record_api_call(
                            "coingecko", "/api/v3/simple/price",
                            True, response_time, 200
                        )
                        return self._format_market_cap(market_cap)
                    else:
                        metrics_manager.record_api_call(
                            "coingecko", "/api/v3/simple/price",
                            False, response_time, response.status
                        )
        except Exception as e:
            logger.error(f"Error obteniendo market cap de CoinGecko para {base_symbol}: {e}")

        return "N/A"

    @staticmethod
    def _format_market_cap(value: float) -> str:
        """Formatea la capitalización de mercado de forma legible.

        Args:
            value: Valor numérico de la capitalización.

        Returns:
            String formateado (ej: $1.32T, $500B, $100M).
        """
        if value >= 1_000_000_000_000:
            return f"${value / 1_000_000_000_000:.2f}T"
        elif value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        elif value > 0:
            return f"${value:,.0f}"
        return "N/A"

    async def _fetch_tickers_without_coinbase(self) -> list[dict]:
        """Consulta tickers de todos los exchanges excepto Coinbase."""
        exchanges_sin_coinbase = [e for e in self.exchanges if e.exchange_name != "coinbase"]
        tasks = [self._safe_tickers(exchange) for exchange in exchanges_sin_coinbase]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_tickers = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exchange {exchanges_sin_coinbase[i].exchange_name} falló: {result}")
                continue
            if isinstance(result, list):
                all_tickers.extend(result)
                logger.info(f"{exchanges_sin_coinbase[i].exchange_name}: {len(result)} tickers obtenidos")

        return all_tickers

    async def _get_orderbook_without_coinbase(self, symbol: str, limit: int = 20) -> dict:
        """Obtiene orderbook agregado de todos los exchanges excepto Coinbase."""
        exchanges_sin_coinbase = [e for e in self.exchanges if e.exchange_name != "coinbase"]
        tasks = [self._safe_orderbook(exchange, symbol, limit) for exchange in exchanges_sin_coinbase]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_bids = []
        all_asks = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error orderbook de {exchanges_sin_coinbase[i].exchange_name}: {result}")
                continue
            if isinstance(result, dict):
                all_bids.extend(result.get("bids", []))
                all_asks.extend(result.get("asks", []))

        all_bids.sort(key=lambda x: x.get("price", 0), reverse=True)
        all_asks.sort(key=lambda x: x.get("price", 0))

        return {"bids": all_bids[:limit], "asks": all_asks[:limit]}

    async def close_all(self) -> None:
        """Cierra todas las sesiones HTTP de los exchanges."""
        for exchange in self.exchanges:
            await exchange.close()


# Instancia global del agregador
exchange_aggregator = ExchangeAggregator()
