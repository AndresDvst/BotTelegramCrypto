"""
Tests para el servicio de Groq.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.groq_service import GroqService


MOCK_TOP_COINS = [
    {"symbol": "BTCUSDT", "price": 67000, "change_pct": 5.3},
    {"symbol": "ETHUSDT", "price": 3500, "change_pct": 4.1},
]

MOCK_SENTIMENT = {"value": 72, "classification": "Codicia 🤑"}


@pytest.mark.asyncio
async def test_groq_successful_call():
    """Test llamada exitosa a Groq."""
    service = GroqService()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "🥇 BTC — Recomendación\n🥈 ETH — Recomendación"

    with patch.object(service.client.chat.completions, "create",
                      new_callable=AsyncMock, return_value=mock_response), \
         patch("services.groq_service.metrics_manager"):

        result = await service.get_recommendations(
            MOCK_TOP_COINS, MOCK_SENTIMENT, "4h", "up"
        )
        assert "BTC" in result
        assert "ETH" in result


@pytest.mark.asyncio
async def test_groq_retry_on_rate_limit():
    """Test retry en caso de rate limiting."""
    service = GroqService()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Recomendación después de retry"

    with patch.object(service.client.chat.completions, "create",
                      new_callable=AsyncMock,
                      side_effect=[
                          Exception("Rate limited"),
                          mock_response
                      ]), \
         patch("services.groq_service.metrics_manager"), \
         patch("asyncio.sleep", new_callable=AsyncMock):

        result = await service.get_recommendations(
            MOCK_TOP_COINS, MOCK_SENTIMENT, "4h", "up"
        )
        assert "Recomendación después de retry" in result


@pytest.mark.asyncio
async def test_groq_fallback_on_complete_failure():
    """Test fallback cuando Groq falla completamente."""
    service = GroqService()

    with patch.object(service.client.chat.completions, "create",
                      new_callable=AsyncMock,
                      side_effect=Exception("API Error")), \
         patch("services.groq_service.metrics_manager"), \
         patch("asyncio.sleep", new_callable=AsyncMock):

        result = await service.get_recommendations(
            MOCK_TOP_COINS, MOCK_SENTIMENT, "4h", "up"
        )
        assert "no disponible" in result.lower() or "⚠️" in result


@pytest.mark.asyncio
async def test_groq_prompt_includes_data():
    """Test que el prompt incluye todos los datos necesarios."""
    service = GroqService()

    captured_messages = None

    async def capture_call(**kwargs):
        nonlocal captured_messages
        captured_messages = kwargs.get("messages", [])
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Recomendación"
        return mock_resp

    with patch.object(service.client.chat.completions, "create",
                      side_effect=capture_call), \
         patch("services.groq_service.metrics_manager"):

        await service.get_recommendations(
            MOCK_TOP_COINS, MOCK_SENTIMENT, "4h", "up"
        )

        assert captured_messages is not None
        user_prompt = captured_messages[1]["content"]
        assert "BTCUSDT" in user_prompt
        assert "subida" in user_prompt
        assert "4 horas" in user_prompt
