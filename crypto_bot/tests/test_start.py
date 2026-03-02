"""
Tests para el handler /start e "iniciar".
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.start_handler import start_command
from config.config import ESTADO_MENU_PRINCIPAL


@pytest.fixture
def mock_update():
    """Fixture que crea un mock de Update de Telegram."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.first_name = "TestUser"
    update.effective_user.username = "testuser"
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
async def test_start_responds_to_start_command(mock_update, mock_context):
    """Test que el bot responde al comando /start."""
    with patch("bot.handlers.start_handler.metrics_manager"), \
         patch("bot.handlers.start_handler.start_inactivity_timer", new_callable=AsyncMock):
        result = await start_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        assert result == ESTADO_MENU_PRINCIPAL


@pytest.mark.asyncio
async def test_start_responds_to_iniciar(mock_update, mock_context):
    """Test que el bot responde a la palabra 'iniciar'."""
    mock_update.message.text = "iniciar"
    with patch("bot.handlers.start_handler.metrics_manager"), \
         patch("bot.handlers.start_handler.start_inactivity_timer", new_callable=AsyncMock):
        result = await start_command(mock_update, mock_context)
        assert result == ESTADO_MENU_PRINCIPAL


@pytest.mark.asyncio
async def test_start_responds_to_iniciar_uppercase(mock_update, mock_context):
    """Test que el bot responde a 'INICIAR' (mayúsculas)."""
    mock_update.message.text = "INICIAR"
    with patch("bot.handlers.start_handler.metrics_manager"), \
         patch("bot.handlers.start_handler.start_inactivity_timer", new_callable=AsyncMock):
        result = await start_command(mock_update, mock_context)
        assert result == ESTADO_MENU_PRINCIPAL


@pytest.mark.asyncio
async def test_welcome_message_contains_user_name(mock_update, mock_context):
    """Test que el mensaje de bienvenida contiene el nombre del usuario."""
    with patch("bot.handlers.start_handler.metrics_manager"), \
         patch("bot.handlers.start_handler.start_inactivity_timer", new_callable=AsyncMock):
        await start_command(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        assert "TestUser" in message


@pytest.mark.asyncio
async def test_welcome_message_contains_all_commands(mock_update, mock_context):
    """Test que el mensaje contiene todos los comandos."""
    with patch("bot.handlers.start_handler.metrics_manager"), \
         patch("bot.handlers.start_handler.start_inactivity_timer", new_callable=AsyncMock):
        await start_command(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]

        commands = [
            "/TopSubidas4H",
            "/TopBajadas4H",
            "/TopSubidas24H",
            "/TopBajadas24H",
            "/SentimientoDelMercado",
            "/OrdenesDeMercado",
            "/ConsultarCryptoEspecifica"
        ]
        for cmd in commands:
            assert cmd in message, f"Comando {cmd} no encontrado en el mensaje"
