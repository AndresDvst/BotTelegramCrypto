"""
Clase base abstracta para todos los exchanges.
Define la interfaz que cada exchange debe implementar.
"""

import logging
import time
import asyncio
from abc import ABC, abstractmethod

import aiohttp

from config.config import Config
from database.metrics_manager import metrics_manager

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503}


class ExchangeError(Exception):
    """Error de exchange con flag para retry."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class BaseExchange(ABC):
    """Clase base abstracta para servicios de exchanges de criptomonedas."""

    exchange_name: str = ""
    base_url: str = ""

    def __init__(self) -> None:
        """Inicializa el exchange base."""
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene o crea una sesión HTTP.

        Returns:
            Sesión aiohttp activa.
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=Config.HTTP_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _make_request(self, endpoint: str, params: dict | None = None) -> dict | list:
        """Realiza una petición HTTP GET con retry y backoff exponencial."""
        url = f"{self.base_url}{endpoint}"
        last_exception: Exception | None = None

        for attempt in range(Config.MAX_RETRIES):
            start_time = time.time()
            try:
                session = await self._get_session()
                async with session.get(url, params=params) as response:
                    response_time = (time.time() - start_time) * 1000
                    status_code = response.status

                    if status_code == 200:
                        data = await response.json()
                        metrics_manager.record_api_call(
                            api_name=self.exchange_name,
                            endpoint=endpoint,
                            success=True,
                            response_time=response_time,
                            status_code=status_code
                        )
                        return data

                    metrics_manager.record_api_call(
                        api_name=self.exchange_name,
                        endpoint=endpoint,
                        success=False,
                        response_time=response_time,
                        status_code=status_code
                    )

                    if status_code == 400:
                        raise ExchangeError(
                            f"{self.exchange_name} símbolo inválido o sin datos: {endpoint}",
                            retryable=False
                        )
                    if status_code in RETRYABLE_STATUS_CODES:
                        raise ExchangeError(
                            f"{self.exchange_name} API error recuperable: status {status_code}",
                            retryable=True
                        )
                    raise ExchangeError(
                        f"{self.exchange_name} API error no recuperable: status {status_code}",
                        retryable=False
                    )

            except ExchangeError as e:
                last_exception = e
                logger.error(
                    f"{self.exchange_name} - Intento {attempt + 1}/{Config.MAX_RETRIES} "
                    f"fallido para {endpoint}: {e}"
                )
                if e.retryable and attempt < Config.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"{self.exchange_name} - Esperando {wait_time}s antes de reintentar...")
                    await asyncio.sleep(wait_time)
                else:
                    break

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                logger.error(
                    f"{self.exchange_name} - Intento {attempt + 1}/{Config.MAX_RETRIES} "
                    f"fallido para {endpoint}: {e}"
                )
                if attempt < Config.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"{self.exchange_name} - Esperando {wait_time}s antes de reintentar...")
                    await asyncio.sleep(wait_time)
                else:
                    break

            except Exception as e:
                last_exception = e
                logger.error(f"{self.exchange_name} - Error no recuperable en {endpoint}: {e}")
                break

        metrics_manager.record_api_call(
            api_name=self.exchange_name,
            endpoint=endpoint,
            success=False,
            response_time=0,
            status_code=None
        )
        raise last_exception or ExchangeError(f"{self.exchange_name}: todos los reintentos fallaron")

    async def close(self) -> None:
        """Cierra la sesión HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def get_tickers(self) -> list[dict]:
        """Obtiene todos los tickers del exchange.

        Returns:
            Lista de dicts con al menos: symbol, price, price_change_percent_24h, volume.
        """
        ...

    @abstractmethod
    async def get_klines(self, symbol: str, interval: str, limit: int) -> list:
        """Obtiene velas (klines) para un símbolo.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            interval: Intervalo de la vela (ej: 1h).
            limit: Número de velas a obtener.

        Returns:
            Lista de velas con datos OHLCV.
        """
        ...

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Obtiene el libro de órdenes de un símbolo.

        Args:
            symbol: Símbolo del par (ej: BTCUSDT).
            limit: Número de órdenes a obtener.

        Returns:
            Dict con 'bids' y 'asks', cada uno una lista de [precio, cantidad].
        """
        ...

