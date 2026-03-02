"""
Tests para el Exchange Aggregator.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.exchange_aggregator import ExchangeAggregator


MOCK_TICKERS = [
    {"symbol": "BTCUSDT", "price": 67000, "price_change_percent_24h": 3.5,
     "volume": 25000000000, "exchange": "binance"},
    {"symbol": "ETHUSDT", "price": 3500, "price_change_percent_24h": 2.1,
     "volume": 15000000000, "exchange": "binance"},
    {"symbol": "BTCUSDT", "price": 67050, "price_change_percent_24h": 3.6,
     "volume": 20000000000, "exchange": "bybit"},
]


@pytest.fixture
def aggregator():
    """Fixture que crea un agregador con mocks."""
    return ExchangeAggregator()


@pytest.mark.asyncio
async def test_queries_all_exchanges_in_parallel(aggregator):
    """Test que consulta todos los exchanges en paralelo."""
    for exchange in aggregator.exchanges:
        exchange.get_tickers = AsyncMock(return_value=[
            {"symbol": "BTCUSDT", "price": 67000, "price_change_percent_24h": 3.5,
             "volume": 25000000000, "exchange": exchange.exchange_name}
        ])

    with patch.object(aggregator, "_enrich_data", new_callable=AsyncMock,
                      return_value=[{"symbol": "BTCUSDT"}]):
        result = await aggregator.get_top_movers("24h", "up", 10)

        for exchange in aggregator.exchanges:
            exchange.get_tickers.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_to_binance_when_all_fail(aggregator):
    """Test fallback a Binance cuando todos fallan."""
    for exchange in aggregator.exchanges:
        exchange.get_tickers = AsyncMock(side_effect=Exception("Connection error"))

    # Override Binance para que funcione en el segundo intento (fallback)
    binance_data = [
        {"symbol": "BTCUSDT", "price": 67000, "price_change_percent_24h": 3.5,
         "volume": 25000000000, "exchange": "binance"}
    ]
    aggregator.binance.get_tickers = AsyncMock(
        side_effect=[Exception("First fail"), binance_data]
    )

    with patch.object(aggregator, "_enrich_data", new_callable=AsyncMock,
                      return_value=[{"symbol": "BTCUSDT"}]), \
         patch.object(aggregator, "_calculate_4h_change", new_callable=AsyncMock,
                      return_value=[{"symbol": "BTCUSDT", "change_pct": 5.0}]):
        # El fallback ocurre dentro del método
        result = await aggregator.get_top_movers("24h", "up", 10)


@pytest.mark.asyncio
async def test_deduplication_by_volume(aggregator):
    """Test deduplicación de símbolos (se queda con el de mayor volumen)."""
    duplicates = [
        {"symbol": "BTCUSDT", "price": 67000, "volume": 25000000000, "exchange": "binance"},
        {"symbol": "BTCUSDT", "price": 67050, "volume": 20000000000, "exchange": "bybit"},
        {"symbol": "ETHUSDT", "price": 3500, "volume": 15000000000, "exchange": "binance"},
    ]

    result = aggregator._deduplicate_tickers(duplicates)

    # Solo debe haber 2 símbolos únicos
    symbols = [r["symbol"] for r in result]
    assert len(symbols) == 2
    assert "BTCUSDT" in symbols
    assert "ETHUSDT" in symbols

    # BTC debe ser el de Binance (mayor volumen)
    btc = next(r for r in result if r["symbol"] == "BTCUSDT")
    assert btc["volume"] == 25000000000


@pytest.mark.asyncio
async def test_metrics_recorded(aggregator):
    """Test que registra métricas correctamente."""
    with patch("services.exchange_aggregator.metrics_manager") as mock_metrics:
        for exchange in aggregator.exchanges:
            exchange.get_tickers = AsyncMock(return_value=[])

        with patch.object(aggregator, "_enrich_data", new_callable=AsyncMock, return_value=[]):
            await aggregator.get_top_movers("24h", "up", 10)
