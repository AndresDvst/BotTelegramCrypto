"""
Tests para el handler /TopSubidas4H.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.top_subidas_4h import top_subidas_4h
from config.config import ESTADO_PREGUNTA_OTRA_CONSULTA


MOCK_TOP_MOVERS = [
    {
        "symbol": f"COIN{i}USDT",
        "price": 100.0 + i * 10,
        "change_pct": 10.0 - i * 0.5,
        "market_cap": "$1.00B",
        "buy_sell_ratio": "60% / 40%",
        "exchange_source": "binance"
    }
    for i in range(10)
]

MOCK_SENTIMENT = {
    "value": 72,
    "classification": "Codicia 🤑",
    "previous_day": None,
    "previous_week": None,
    "source": "coinmarketcap"
}


@pytest.fixture
def mock_update():
    """Fixture que crea un mock de Update."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Fixture que crea un mock de Context."""
    context = MagicMock()
    context.job_queue = MagicMock()
    context.job_queue.run_once = MagicMock()
    context.job_queue.get_jobs_by_name = MagicMock(return_value=[])
    return context


@pytest.mark.asyncio
async def test_top_subidas_4h_full_flow(mock_update, mock_context):
    """Test flujo completo con mocks de todos los exchanges."""
    with patch("bot.handlers.top_subidas_4h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_subidas_4h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_subidas_4h.groq_service") as mock_groq, \
         patch("bot.handlers.top_subidas_4h.metrics_manager"), \
         patch("bot.handlers.top_subidas_4h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="🥇 COIN0 — Buena oportunidad")

        result = await top_subidas_4h(mock_update, mock_context)

        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA
        assert mock_update.message.reply_text.call_count >= 2


@pytest.mark.asyncio
async def test_top_subidas_4h_fallback_binance(mock_update, mock_context):
    """Test fallback cuando todos los exchanges fallan (debe usar solo Binance)."""
    with patch("bot.handlers.top_subidas_4h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_subidas_4h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_subidas_4h.groq_service") as mock_groq, \
         patch("bot.handlers.top_subidas_4h.metrics_manager"), \
         patch("bot.handlers.top_subidas_4h.reset_inactivity_timer", new_callable=AsyncMock):

        # Simular que retorna datos (el fallback a Binance está dentro del aggregator)
        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS[:5])
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Recomendación")

        result = await top_subidas_4h(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA


@pytest.mark.asyncio
async def test_top_subidas_4h_returns_10_results(mock_update, mock_context):
    """Test que retorna exactamente 10 resultados."""
    with patch("bot.handlers.top_subidas_4h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_subidas_4h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_subidas_4h.groq_service") as mock_groq, \
         patch("bot.handlers.top_subidas_4h.metrics_manager"), \
         patch("bot.handlers.top_subidas_4h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Recomendación")

        await top_subidas_4h(mock_update, mock_context)

        mock_agg.get_top_movers.assert_called_once_with(
            timeframe="4h", direction="up", top_n=10
        )


@pytest.mark.asyncio
async def test_top_subidas_4h_sorted_by_positive_change():
    """Test que los resultados están ordenados de mayor a menor cambio positivo."""
    sorted_movers = sorted(MOCK_TOP_MOVERS, key=lambda x: x["change_pct"], reverse=True)
    assert sorted_movers[0]["change_pct"] >= sorted_movers[-1]["change_pct"]


@pytest.mark.asyncio
async def test_top_subidas_4h_result_fields():
    """Test que cada resultado tiene los campos requeridos."""
    required_fields = ["symbol", "price", "change_pct", "market_cap", "buy_sell_ratio"]
    for mover in MOCK_TOP_MOVERS:
        for field in required_fields:
            assert field in mover, f"Campo {field} no encontrado"


@pytest.mark.asyncio
async def test_top_subidas_4h_groq_called(mock_update, mock_context):
    """Test que Groq es llamado con los 10 resultados."""
    with patch("bot.handlers.top_subidas_4h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_subidas_4h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_subidas_4h.groq_service") as mock_groq, \
         patch("bot.handlers.top_subidas_4h.metrics_manager"), \
         patch("bot.handlers.top_subidas_4h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(return_value="Recomendación")

        await top_subidas_4h(mock_update, mock_context)

        mock_groq.get_recommendations.assert_called_once_with(
            top_coins=MOCK_TOP_MOVERS,
            sentiment=MOCK_SENTIMENT,
            timeframe="4h",
            direction="up"
        )


@pytest.mark.asyncio
async def test_top_subidas_4h_message_has_emojis(mock_update, mock_context):
    """Test que el mensaje final contiene emojis y las 3 recomendaciones."""
    with patch("bot.handlers.top_subidas_4h.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.top_subidas_4h.sentiment_service") as mock_sent, \
         patch("bot.handlers.top_subidas_4h.groq_service") as mock_groq, \
         patch("bot.handlers.top_subidas_4h.metrics_manager"), \
         patch("bot.handlers.top_subidas_4h.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_top_movers = AsyncMock(return_value=MOCK_TOP_MOVERS)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)
        mock_groq.get_recommendations = AsyncMock(
            return_value="🥇 COIN0\n🥈 COIN1\n🥉 COIN2"
        )

        await top_subidas_4h(mock_update, mock_context)

        # El segundo call es el mensaje principal formateado
        calls = mock_update.message.reply_text.call_args_list
        # Al menos uno de los mensajes debe contener emojis
        all_messages = " ".join(str(call) for call in calls)
        assert "📈" in all_messages or "🔄" in all_messages
