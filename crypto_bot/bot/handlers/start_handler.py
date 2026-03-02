"""
Handler para /start e "iniciar".
Saludo personalizado con lista de comandos.
"""

import logging
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from config.config import ESTADO_MENU_PRINCIPAL
from bot.utils.formatters import format_welcome_message
from bot.utils.timeout_manager import start_inactivity_timer
from bot.conversation.state_manager import state_manager
from database.metrics_manager import metrics_manager

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el comando /start y la palabra "iniciar".

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        Siguiente estado de la conversación.
    """
    start_time = time.time()
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "Usuario"
    username = user.username

    logger.info(f"Usuario {user_id} ({first_name}) inició el bot")

    # Registrar sesión de usuario
    metrics_manager.record_user_start(user_id, username, first_name)

    # Establecer estado
    state_manager.set_state(user_id, ESTADO_MENU_PRINCIPAL)

    # Mostrar indicador de "escribiendo..."
    await update.effective_chat.send_action(ChatAction.TYPING)

    # Enviar mensaje de bienvenida
    message = format_welcome_message(first_name)
    await update.message.reply_text(message)

    # Iniciar timer de inactividad
    await start_inactivity_timer(user_id, update.effective_chat.id, context)

    # Registrar métrica
    response_time = (time.time() - start_time) * 1000
    metrics_manager.record_command("start", user_id, True, response_time)

    return ESTADO_MENU_PRINCIPAL
