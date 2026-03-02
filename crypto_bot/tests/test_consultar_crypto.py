"""
Tests para el handler /ConsultarCryptoEspecifica.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.consultar_crypto import consultar_crypto_start, consultar_crypto_receive_coin
from config.config import ESTADO_ESPERANDO_MONEDA_NOMBRE_CONSULTA, ESTADO_PREGUNTA_OTRA_CONSULTA


MOCK_COIN_DATA = {
    "symbol": "BTCUSDT",
    "price": 67432.50,
    "price_change_percent_24h": 3.5,
    "change_pct_4h": 1.2,
    "market_cap": "$1.32T",
    "buy_sell_ratio": "65% / 35%",
    "volume": 25000000000
}

MOCK_SENTIMENT = {"value": 72, "classification": "Codicia 🤑", "source": "coinmarketcap"}


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
async def test_consultar_start_asks_for_coin(mock_update, mock_context):
    """Test que el handler pregunta por la moneda."""
    with patch("bot.handlers.consultar_crypto.reset_inactivity_timer", new_callable=AsyncMock):
        result = await consultar_crypto_start(mock_update, mock_context)
        assert result == ESTADO_ESPERANDO_MONEDA_NOMBRE_CONSULTA


@pytest.mark.asyncio
async def test_consultar_by_name(mock_update, mock_context):
    """Test flujo completo buscando por nombre."""
    mock_update.message.text = "Bitcoin"

    with patch("bot.handlers.consultar_crypto.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.consultar_crypto.sentiment_service") as mock_sent, \
         patch("bot.handlers.consultar_crypto._resolve_symbol", new_callable=AsyncMock, return_value="BTC"), \
         patch("bot.handlers.consultar_crypto.metrics_manager"), \
         patch("bot.handlers.consultar_crypto.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_coin_data = AsyncMock(return_value=MOCK_COIN_DATA)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)

        result = await consultar_crypto_receive_coin(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA


@pytest.mark.asyncio
async def test_consultar_by_symbol(mock_update, mock_context):
    """Test flujo completo buscando por símbolo."""
    mock_update.message.text = "ETH"

    with patch("bot.handlers.consultar_crypto.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.consultar_crypto.sentiment_service") as mock_sent, \
         patch("bot.handlers.consultar_crypto.metrics_manager"), \
         patch("bot.handlers.consultar_crypto.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_coin_data = AsyncMock(return_value=MOCK_COIN_DATA)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)

        result = await consultar_crypto_receive_coin(mock_update, mock_context)
        assert result == ESTADO_PREGUNTA_OTRA_CONSULTA


@pytest.mark.asyncio
async def test_consultar_message_includes_all_fields(mock_update, mock_context):
    """Test que el mensaje incluye: precio, cambio 4h, cambio 24h, cap. mercado, ratio, sentimiento."""
    mock_update.message.text = "BTC"

    with patch("bot.handlers.consultar_crypto.exchange_aggregator") as mock_agg, \
         patch("bot.handlers.consultar_crypto.sentiment_service") as mock_sent, \
         patch("bot.handlers.consultar_crypto.metrics_manager"), \
         patch("bot.handlers.consultar_crypto.reset_inactivity_timer", new_callable=AsyncMock):

        mock_agg.get_coin_data = AsyncMock(return_value=MOCK_COIN_DATA)
        mock_sent.get_sentiment = AsyncMock(return_value=MOCK_SENTIMENT)

        await consultar_crypto_receive_coin(mock_update, mock_context)

        calls = mock_update.message.reply_text.call_args_list
        all_text = " ".join(str(c) for c in calls)

        # Verificar que aparecen los campos clave
        assert "67" in all_text  # precio
        assert "4h" in all_text or "Cambio" in all_text  # cambio 4h
        assert "24h" in all_text  # cambio 24h
        assert "Mercado" in all_text  # cap de mercado
        assert "Compra" in all_text or "Venta" in all_text  # ratio compra/venta
        assert "Sentimiento" in all_text or "sentimiento" in all_text.lower()  # sentimiento
