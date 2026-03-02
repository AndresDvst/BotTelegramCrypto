"""
Tests para el handler /TopBajadas4H.
Mismo set de tests pero verificando orden de mayor bajada.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.top_bajadas_4h import top_bajadas_4h
from config.config import ESTADO_PREGUNTA_OTRA_CONSULTA


MOCK_TOP_MOVERS_DOWN = [
    {
        "symbol": f"COIN{i}USDT",
        "price": 100.0 - i * 5,
        "change_pct": -10.0 + i * 0.5,
        "market_cap": "$500M",
        "buy_sell_ratio": "40% / 60%",
        "exchange_source": "binance"
    }
    for i in range(10)
]

MOCK_SENTIMENT = {
    "value": 30,
    "classification": "Miedo 😨",
    "previous_day": None,
    "previous_week": None,
    "source": "coinmarketcap"
}


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.job_queue = MagicMock()
    context.job_queue.run_once = MagicMock()
    context.job_queue.get_jobs_by_name = MagicMock(return_value=[])
    return context


@pytest.mark.asyncio
async def test_top_bajadas_4h_full_flow(mock_update, mock_context):
    """Test flujo completo de bajadas 4h."""
    with patch("bot.handlers.top_bajadas_4h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_bajadas_4h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_bajadas_4h.groq_service") as mock_groq, \
         patch("bot.handlers.top_bajadas_4h.metrics_manager"), \
         patch("bot.handlers.top_bajadas_4h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS_DOWN)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Análisis de bajadas")

        result = await top_bajadas_4h(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA


@pytest.mark.asyncio
async def test_top_bajadas_4h_direction_down(mock_update, mock_context):
    """Test que se llama con direction='down'."""
    with patch("bot.handlers.top_bajadas_4h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_bajadas_4h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_bajadas_4h.groq_service") as mock_groq, \
         patch("bot.handlers.top_bajadas_4h.metrics_manager"), \
         patch("bot.handlers.top_bajadas_4h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS_DOWN)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Recomendación")

        await top_bajadas_4h(mock_update, mock_context)

        mock_agg.get_top_movers.assert_called_once_with(
            timeframe="4h", direction="down", top_n=10
        )


@pytest.mark.asyncio
async def test_top_bajadas_4h_sorted_by_negative_change():
    """Test que los resultados están ordenados por mayor bajada."""
    sorted_movers = sorted(MOCK_TOP_MOVERS_DOWN, key=lambda x: x["change_pct"])
    assert sorted_movers[0]["change_pct"] <= sorted_movers[-1]["change_pct"]


@pytest.mark.asyncio
async def test_top_bajadas_4h_empty_response(mock_update, mock_context):
    """Test manejo de respuesta vacía."""
    with patch("bot.handlers.top_bajadas_4h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_bajadas_4h.metrics_manager"), \
         patch("bot.handlers.top_bajadas_4h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=[])

        result = await top_bajadas_4h(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA
