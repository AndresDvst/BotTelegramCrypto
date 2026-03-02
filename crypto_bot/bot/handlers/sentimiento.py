"""
Handler para /SentimientoDelMercado.
Índice Fear & Greed y sentimiento general del mercado.
IMPORTANTE: Este comando SOLO consulta y muestra el sentimiento.
NO consulta exchanges NI llama a Groq. Es independiente.
"""

import logging
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from config.config import ESTADO_PREGUNTA_OTRA_CONSULTA
from bot.utils.formatters import format_sentiment_message, format_continue_message
from bot.utils.timeout_manager import reset_inactivity_timer
from services.sentiment_service import sentiment_service
from database.metrics_manager import metrics_manager
from bot.conversation.state_manager import state_manager

logger = logging.getLogger(__name__)


async def sentimiento_del_mercado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el comando /SentimientoDelMercado.

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        Siguiente estado de la conversación.
    """
    start_time = time.time()
    user_id = update.effective_user.id

    logger.info(f"Usuario {user_id} solicitó /SentimientoDelMercado")

    # Reset timer de inactividad
    await reset_inactivity_timer(user_id, update.effective_chat.id, context)

    # Mostrar indicador de "escribiendo..."
    await update.effective_chat.send_action(ChatAction.TYPING)

    try:
        # Obtener sentimiento (con caché)
        sentiment = await sentiment_service.get_sentiment()

        # Formatear y enviar mensaje
        message = format_sentiment_message(sentiment)
        await update.message.reply_text(message)

        # Pregunta de continuación
        await update.message.reply_text(format_continue_message())

        # Registrar métrica
        response_time = (time.time() - start_time) * 1000
        metrics_manager.record_command("SentimientoDelMercado", user_id, True, response_time)

    except Exception as e:
        logger.error(f"Error en /SentimientoDelMercado: {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error al obtener el sentimiento del mercado. Intenta de nuevo."
        )
        response_time = (time.time() - start_time) * 1000
        metrics_manager.record_command("SentimientoDelMercado", user_id, False, response_time)

    state_manager.set_state(user_id, ESTADO_PREGUNTA_OTRA_CONSULTA)
    return ESTADO_PREGUNTA_OTRA_CONSULTA
