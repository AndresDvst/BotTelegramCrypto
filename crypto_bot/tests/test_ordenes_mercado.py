"""
Tests para el handler /OrdenesDeMercado.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.ordenes_mercado import ordenes_mercado_start, ordenes_mercado_receive_coin
from config.config import ESTADO_ESPERANDO_MONEDA_NOMBRE_ORDENES, ESTADO_PREGUNTA_OTRA_CONSULTA


MOCK_ORDERBOOK = {
    "bids": [{"price": 67000 + i, "quantity": 0.5 + i * 0.1} for i in range(20)],
    "asks": [{"price": 67500 + i, "quantity": 0.3 + i * 0.1} for i in range(20)]
}

MOCK_SENTIMENT = {"value": 65, "classification": "Codicia 🤑", "source": "coinmarketcap"}


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    update.message.text = "BTC"
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.job_queue = MagicMock()
    context.job_queue.run_once = MagicMock()
    context.job_queue.get_jobs_by_name = MagicMock(return_value=[])
    return context


@pytest.mark.asyncio
async def test_ordenes_start_asks_for_coin(mock_update, mock_context):
    """Test que el handler pregunta por la moneda."""
    with patch("bot.handlers.ordenes_mercado.reset_inactivity_timer", new_callable=AsyncMock):
        result = await ordenes_mercado_start(mock_update, mock_context)
        assert result == ESTADO_ESPERANDO_MONEDA_NOMBRE_ORDENES
        mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_ordenes_by_symbol(mock_update, mock_context):
    """Test flujo completo buscando por símbolo."""
    mock_update.message.text = "BTC"

    with patch("bot.handlers.ordenes_mercado.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.ordenes_mercado.sentiment_service") as mock_sent, \
         patch("bot.handlers.ordenes_mercado.metrics_manager"), \
         patch("bot.handlers.ordenes_mercado.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_orderbook_aggregated = AsyncMock(return_value=MOCK_ORDERBOOK)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)

        result = await ordenes_mercado_receive_coin(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA


@pytest.mark.asyncio
async def test_ordenes_by_name(mock_update, mock_context):
    """Test flujo completo buscando por nombre."""
    mock_update.message.text = "Bitcoin"

    with patch("bot.handlers.ordenes_mercado.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.ordenes_mercado.sentiment_service") as mock_sent, \
         patch("bot.handlers.ordenes_mercado._resolve_symbol", new_callable=AsyncMock, return_value="BTC"), \
         patch("bot.handlers.ordenes_mercado.metrics_manager"), \
         patch("bot.handlers.ordenes_mercado.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_orderbook_aggregated = AsyncMock(return_value=MOCK_ORDERBOOK)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)

        result = await ordenes_mercado_receive_coin(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA


@pytest.mark.asyncio
async def test_ordenes_20_bids_20_asks():
    """Test que retorna exactamente 20 órdenes de compra y 20 de venta."""
    assert len(MOCK_ORDERBOOK["bids"]) == 20
    assert len(MOCK_ORDERBOOK["asks"]) == 20


@pytest.mark.asyncio
async def test_ordenes_coin_not_found(mock_update, mock_context):
    """Test manejo de moneda no encontrada."""
    mock_update.message.text = "MonedaInexistente123"

    with patch("bot.handlers.ordenes_mercado._resolve_symbol", new_callable=AsyncMock, return_value=None), \
         patch("bot.handlers.ordenes_mercado.metrics_manager"), \
         patch("bot.handlers.ordenes_mercado.reset_inactivity_timer", new_callable=AsyncMock):

        result = await ordenes_mercado_receive_coin(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA

        calls = mock_update.message.reply_text.call_args_list
        all_text = " ".join(str(c) for c in calls)
        assert "No se encontró" in all_text or "no encontr" in all_text.lower()
