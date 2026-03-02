"""
Servicio de sentimiento del mercado.
CoinMarketCap Fear & Greed Index con fallback a CoinGecko.
Caché de 10 minutos para evitar peticiones redundantes.
"""

import logging
import time

import aiohttp
from cachetools import TTLCache

from config.config import Config
from database.metrics_manager import metrics_manager

logger = logging.getLogger(__name__)

# Caché de sentimiento con TTL de 10 minutos
_sentiment_cache: TTLCache = TTLCache(maxsize=1, ttl=Config.SENTIMENT_CACHE_TTL)


class SentimentService:
    """Servicio para obtener el índice Fear & Greed del mercado."""

    def __init__(self) -> None:
        """Inicializa el servicio de sentimiento."""
        pass

    @staticmethod
    def _classify_sentiment(value: int) -> str:
        """Clasifica el valor numérico del sentimiento.

        Args:
            value: Valor del índice (0-100).

        Returns:
            Clasificación en español.
        """
        if value <= 20:
            return "Miedo Extremo 😱"
        elif value <= 40:
            return "Miedo 😨"
        elif value <= 60:
            return "Neutral 😐"
        elif value <= 80:
            return "Codicia 🤑"
        else:
            return "Codicia Extrema 🤑🔥"

    async def get_sentiment(self) -> dict:
        """Obtiene el sentimiento del mercado con caché.

        Returns:
            Dict con: value (0-100), classification, previous_day, previous_week.
        """
        # Verificar caché
        cached = _sentiment_cache.get("sentiment")
        if cached is not None:
            logger.info("Sentimiento obtenido desde caché")
            return cached

        # Intentar CoinMarketCap primero
        result = await self._get_from_coinmarketcap()

        # Fallback a CoinGecko si CoinMarketCap falla
        if result is None:
            logger.warning("CoinMarketCap falló, intentando CoinGecko como fallback")
            result = await self._get_from_coingecko()

        # Si todo falla, retornar datos por defecto
        if result is None:
            logger.error("Todos los servicios de sentimiento fallaron")
            result = {
                "value": 50,
                "classification": "Neutral 😐",
                "previous_day": None,
                "previous_week": None,
                "source": "default"
            }

        # Guardar en caché
        _sentiment_cache["sentiment"] = result
        return result

    async def _get_from_coinmarketcap(self) -> dict | None:
        """Obtiene Fear & Greed de CoinMarketCap.

        Returns:
            Dict con datos de sentimiento o None si falla.
        """
        url = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest"
        headers = {
            "X-CMC_PRO_API_KEY": Config.COINMARKETCAP_API_KEY,
            "Accept": "application/json"
        }

        start_time = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=Config.HTTP_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    response_time = (time.time() - start_time) * 1000
                    status_code = response.status

                    if response.status == 200:
                        data = await response.json()
                        fg_data = data.get("data", {})
                        value = int(fg_data.get("value", 50))

                        metrics_manager.record_api_call(
                            "coinmarketcap", "/v3/fear-and-greed/latest",
                            True, response_time, status_code
                        )

                        return {
                            "value": value,
                            "classification": self._classify_sentiment(value),
                            "previous_day": fg_data.get("update_time"),
                            "previous_week": None,
                            "source": "coinmarketcap"
                        }
                    else:
                        metrics_manager.record_api_call(
                            "coinmarketcap", "/v3/fear-and-greed/latest",
                            False, response_time, status_code
                        )
                        logger.error(f"CoinMarketCap error: status {status_code}")
                        return None

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            metrics_manager.record_api_call(
                "coinmarketcap", "/v3/fear-and-greed/latest",
                False, response_time, None
            )
            logger.error(f"Error en CoinMarketCap: {e}")
            return None

    async def _get_from_coingecko(self) -> dict | None:
        """Obtiene datos de sentimiento de CoinGecko (fallback).

        Returns:
            Dict con datos de sentimiento o None si falla.
        """
        url = "https://api.coingecko.com/api/v3/global"

        start_time = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=Config.HTTP_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response_time = (time.time() - start_time) * 1000
                    status_code = response.status

                    if response.status == 200:
                        data = await response.json()
                        global_data = data.get("data", {})

                        # CoinGecko no tiene Fear & Greed directamente
                        # Usamos market_cap_change_percentage_24h como proxy
                        market_change = float(
                            global_data.get("market_cap_change_percentage_24h_usd", 0)
                        )

                        # Convertir el cambio de mercado a un valor 0-100
                        # Rango aproximado: -10% a +10% -> 0 a 100
                        value = max(0, min(100, int(50 + market_change * 5)))

                        metrics_manager.record_api_call(
                            "coingecko", "/api/v3/global",
                            True, response_time, status_code
                        )

                        return {
                            "value": value,
                            "classification": self._classify_sentiment(value),
                            "previous_day": None,
                            "previous_week": None,
                            "source": "coingecko"
                        }
                    else:
                        metrics_manager.record_api_call(
                            "coingecko", "/api/v3/global",
                            False, response_time, status_code
                        )
                        logger.error(f"CoinGecko error: status {status_code}")
                        return None

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            metrics_manager.record_api_call(
                "coingecko", "/api/v3/global",
                False, response_time, None
            )
            logger.error(f"Error en CoinGecko: {e}")
            return None

    async def resolve_coin_name(self, name: str) -> str | None:
        """Resuelve el nombre de una moneda a su símbolo usando CoinGecko.

        Args:
            name: Nombre de la moneda (ej: Bitcoin).

        Returns:
            Símbolo de la moneda (ej: BTC) o None si no se encuentra.
        """
        url = "https://api.coingecko.com/api/v3/search"
        params = {"query": name}

        start_time = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=Config.HTTP_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        data = await response.json()
                        coins = data.get("coins", [])

                        metrics_manager.record_api_call(
                            "coingecko", "/api/v3/search",
                            True, response_time, 200
                        )

                        if coins:
                            return coins[0].get("symbol", "").upper()
                        return None
                    else:
                        metrics_manager.record_api_call(
                            "coingecko", "/api/v3/search",
                            False, response_time, response.status
                        )
                        return None

        except Exception as e:
            logger.error(f"Error buscando moneda '{name}' en CoinGecko: {e}")
            return None


# Instancia global del servicio de sentimiento
sentiment_service = SentimentService()
