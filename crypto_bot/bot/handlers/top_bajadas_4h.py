"""
Handler para /TopBajadas4H.
Top 10 criptos con mayor bajada en las últimas 4 horas.
"""

import logging
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from config.config import ESTADO_PREGUNTA_OTRA_CONSULTA
from bot.utils.formatters import (
    format_top_movers_message,
    format_loading_message,
    format_continue_message
)
from bot.utils.timeout_manager import reset_inactivity_timer
from services.exchange_aggregator import exchange_aggregator
from services.sentiment_service import sentiment_service
from services.groq_service import groq_service
from database.metrics_manager import metrics_manager
from bot.conversation.state_manager import state_manager

logger = logging.getLogger(__name__)


async def top_bajadas_4h(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el comando /TopBajadas4H.

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        Siguiente estado de la conversación.
    """
    start_time = time.time()
    user_id = update.effective_user.id

    logger.info(f"Usuario {user_id} solicitó /TopBajadas4H")

    # Reset timer de inactividad
    await reset_inactivity_timer(user_id, update.effective_chat.id, context)

    # Mostrar indicador de "escribiendo..." y mensaje de carga
    await update.effective_chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(format_loading_message())

    try:
        # Obtener top movers (bajadas)
        top_movers = await exchange_aggregator.get_top_movers(
            timeframe="4h", direction="down", top_n=10
        )

        if not top_movers:
            await update.message.reply_text(
                "⚠️ No se pudieron obtener datos de los exchanges en este momento. "
                "Intenta de nuevo en unos minutos."
            )
            response_time = (time.time() - start_time) * 1000
            metrics_manager.record_command("TopBajadas4H", user_id, False, response_time)
            return ESTADO_PREGUNTA_OTRA_CONSULTA

        # Obtener sentimiento
        sentiment = await sentiment_service.get_sentiment()

        # Obtener recomendaciones de IA
        recommendations = await groq_service.get_recommendations(
            top_coins=top_movers,
            sentiment=sentiment,
            timeframe="4h",
            direction="down"
        )

        # Formatear y enviar mensaje
        message = format_top_movers_message(
            movers=top_movers,
            timeframe="4h",
            direction="down",
            recommendations=recommendations,
            sentiment=sentiment
        )
        await update.message.reply_text(message)

        # Pregunta de continuación
        await update.message.reply_text(format_continue_message())

        # Registrar métrica
        response_time = (time.time() - start_time) * 1000
        metrics_manager.record_command("TopBajadas4H", user_id, True, response_time)

    except Exception as e:
        logger.error(f"Error en /TopBajadas4H: {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error al procesar tu solicitud. Intenta de nuevo."
        )
        response_time = (time.time() - start_time) * 1000
        metrics_manager.record_command("TopBajadas4H", user_id, False, response_time)

    state_manager.set_state(user_id, ESTADO_PREGUNTA_OTRA_CONSULTA)
    return ESTADO_PREGUNTA_OTRA_CONSULTA
