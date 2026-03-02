"""
Tests para el handler /SentimientoDelMercado.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


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
async def test_sentimiento_returns_fear_greed(mock_update, mock_context):
    """Test que retorna el índice Fear & Greed."""
    from bot.handlers.sentimiento import sentimiento_del_mercado

    sentiment = {"value": 72, "classification": "Codicia 🤑", "source": "coinmarketcap", "previous_day": None}

    with patch("bot.handlers.sentimiento.sentiment_service") as mock_sent, \
         patch("bot.handlers.sentimiento.metrics_manager"), \
         patch("bot.handlers.sentimiento.reset_inactivity_timer", new_callable=AsyncMock):

        mock_sent.get_sentiment = AsyncMock(return_value=sentiment)
        await sentimiento_del_mercado(mock_update, mock_context)

        calls = mock_update.message.reply_text.call_args_list
        all_text = " ".join(str(c) for c in calls)
        assert "72" in all_text


@pytest.mark.asyncio
async def test_sentimiento_fallback_coingecko(mock_update, mock_context):
    """Test fallback a CoinGecko cuando CoinMarketCap falla."""
    from services.sentiment_service import SentimentService

    service = SentimentService()

    with patch.object(service, "_get_from_coinmarketcap", new_callable=AsyncMock, return_value=None), \
         patch.object(service, "_get_from_coingecko", new_callable=AsyncMock,
                      return_value={"value": 55, "classification": "Neutral 😐", "source": "coingecko",
                                    "previous_day": None, "previous_week": None}):

        # Limpiar caché para este test
        from services.sentiment_service import _sentiment_cache
        _sentiment_cache.clear()

        result = await service.get_sentiment()
        assert result["source"] == "coingecko"
        assert result["value"] == 55


@pytest.mark.asyncio
async def test_sentimiento_cache_works():
    """Test que el caché funciona (segunda llamada no hace petición HTTP)."""
    from services.sentiment_service import SentimentService, _sentiment_cache

    service = SentimentService()

    cached_data = {"value": 60, "classification": "Neutral 😐", "source": "cache_test",
                   "previous_day": None, "previous_week": None}

    _sentiment_cache["sentiment"] = cached_data

    result = await service.get_sentiment()
    assert result["source"] == "cache_test"
    assert result["value"] == 60

    # Limpiar caché después del test
    _sentiment_cache.clear()


@pytest.mark.asyncio
async def test_sentimiento_message_format(mock_update, mock_context):
    """Test formato del mensaje de sentimiento."""
    from bot.handlers.sentimiento import sentimiento_del_mercado

    sentiment = {"value": 15, "classification": "Miedo Extremo 😱", "source": "coinmarketcap",
                 "previous_day": None, "previous_week": None}

    with patch("bot.handlers.sentimiento.sentiment_service") as mock_sent, \
         patch("bot.handlers.sentimiento.metrics_manager"), \
         patch("bot.handlers.sentimiento.reset_inactivity_timer", new_callable=AsyncMock):

        mock_sent.get_sentiment = AsyncMock(return_value=sentiment)
        await sentimiento_del_mercado(mock_update, mock_context)

        calls = mock_update.message.reply_text.call_args_list
        main_message = calls[0][0][0]
        assert "SENTIMIENTO" in main_message
        assert "15" in main_message
