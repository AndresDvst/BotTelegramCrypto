"""
Tests para el handler /TopBajadas24H.
Mismos tests verificando ventana de 24h con dirección bajada.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.top_bajadas_24h import top_bajadas_24h
from config.config import ESTADO_PREGUNTA_OTRA_CONSULTA


MOCK_SENTIMENT = {
    "value": 25,
    "classification": "Miedo 😨",
    "source": "coingecko"
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
async def test_top_bajadas_24h_uses_24h_timeframe(mock_update, mock_context):
    """Test que se usa ventana de 24h con dirección down."""
    movers = [{"symbol": "BTCUSDT", "price": 60000, "change_pct": -8.5,
               "market_cap": "$1T", "buy_sell_ratio": "45%/55%", "exchange_source": "binance"}]

    with patch("bot.handlers.top_bajadas_24h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_bajadas_24h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_bajadas_24h.groq_service") as mock_groq, \
         patch("bot.handlers.top_bajadas_24h.metrics_manager"), \
         patch("bot.handlers.top_bajadas_24h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=movers)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Análisis bajada 24h")

        await top_bajadas_24h(mock_update, mock_context)

        mock_agg.get_top_movers.assert_called_once_with(
            timeframe="24h", direction="down", top_n=10
        )


@pytest.mark.asyncio
async def test_top_bajadas_24h_full_flow(mock_update, mock_context):
    """Test flujo completo bajadas 24h."""
    movers = [{"symbol": f"T{i}USDT", "price": 50+i, "change_pct": -5-i,
               "market_cap": "$100M", "buy_sell_ratio": "40%/60%",
               "exchange_source": "binance"} for i in range(10)]

    with patch("bot.handlers.top_bajadas_24h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_bajadas_24h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_bajadas_24h.groq_service") as mock_groq, \
         patch("bot.handlers.top_bajadas_24h.metrics_manager"), \
         patch("bot.handlers.top_bajadas_24h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=movers)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Recomendación")

        result = await top_bajadas_24h(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA
