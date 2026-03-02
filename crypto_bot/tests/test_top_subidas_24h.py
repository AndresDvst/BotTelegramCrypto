"""
Tests para el handler /TopSubidas24H.
Mismos tests pero verificando que se usa ventana de 24h.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.top_subidas_24h import top_subidas_24h
from config.config import ESTADO_PREGUNTA_OTRA_CONSULTA


MOCK_TOP_MOVERS_24H = [
    {
        "symbol": f"COIN{i}USDT",
        "price": 200.0 + i * 20,
        "change_pct": 15.0 - i,
        "market_cap": "$2.00B",
        "buy_sell_ratio": "55% / 45%",
        "exchange_source": "binance"
    }
    for i in range(10)
]

MOCK_SENTIMENT = {
    "value": 65,
    "classification": "Codicia 🤑",
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
async def test_top_subidas_24h_uses_24h_timeframe(mock_update, mock_context):
    """Test que se usa ventana de 24h."""
    with patch("bot.handlers.top_subidas_24h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_subidas_24h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_subidas_24h.groq_service") as mock_groq, \
         patch("bot.handlers.top_subidas_24h.metrics_manager"), \
         patch("bot.handlers.top_subidas_24h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS_24H)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Recomendación 24h")

        await top_subidas_24h(mock_update, mock_context)

        mock_agg.get_top_movers.assert_called_once_with(
            timeframe="24h", direction="up", top_n=10
        )


@pytest.mark.asyncio
async def test_top_subidas_24h_full_flow(mock_update, mock_context):
    """Test flujo completo 24h."""
    with patch("bot.handlers.top_subidas_24h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_subidas_24h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_subidas_24h.groq_service") as mock_groq, \
         patch("bot.handlers.top_subidas_24h.metrics_manager"), \
         patch("bot.handlers.top_subidas_24h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS_24H)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Recomendación")

        result = await top_subidas_24h(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA
        assert mock_update.message.reply_text.call_count >= 2
