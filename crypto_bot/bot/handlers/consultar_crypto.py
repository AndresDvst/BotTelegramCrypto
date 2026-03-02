"""
Handler para /ConsultarCryptoEspecifica.
Análisis completo de una cripto específica.
Reutiliza la función de resolución de nombre/símbolo de ordenes_mercado.
"""

import logging
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from config.config import (
    ESTADO_ESPERANDO_MONEDA_NOMBRE_CONSULTA,
    ESTADO_PREGUNTA_OTRA_CONSULTA
)
from bot.utils.formatters import (
    format_coin_detail_message,
    format_ask_coin_input,
    format_loading_message,
    format_continue_message
)
from bot.utils.timeout_manager import reset_inactivity_timer
from bot.handlers.ordenes_mercado import _resolve_symbol
from services.exchange_aggregator import exchange_aggregator
from services.sentiment_service import sentiment_service
from database.metrics_manager import metrics_manager
from bot.conversation.state_manager import state_manager

logger = logging.getLogger(__name__)


async def consultar_crypto_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo de /ConsultarCryptoEspecifica preguntando por la moneda.

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        Estado esperando nombre/símbolo de moneda.
    """
    user_id = update.effective_user.id

    logger.info(f"Usuario {user_id} solicitó /ConsultarCryptoEspecifica")

    # Reset timer de inactividad
    await reset_inactivity_timer(user_id, update.effective_chat.id, context)

    # Mostrar indicador de "escribiendo..."
    await update.effective_chat.send_action(ChatAction.TYPING)

    # Preguntar nombre o símbolo
    await update.message.reply_text(format_ask_coin_input())

    state_manager.set_state(user_id, ESTADO_ESPERANDO_MONEDA_NOMBRE_CONSULTA)
    return ESTADO_ESPERANDO_MONEDA_NOMBRE_CONSULTA


async def consultar_crypto_receive_coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre o símbolo y muestra el análisis completo.

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        Siguiente estado de la conversación.
    """
    start_time = time.time()
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    logger.info(f"Usuario {user_id} envió: {user_input} para ConsultarCrypto")

    # Reset timer de inactividad
    await reset_inactivity_timer(user_id, update.effective_chat.id, context)

    # Mostrar indicador de "escribiendo..." y mensaje de carga
    await update.effective_chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(format_loading_message())

    try:
        # Resolver el símbolo (reutilizar función de ordenes_mercado)
        symbol = await _resolve_symbol(user_input)

        if not symbol:
            await update.message.reply_text(
                f"❌ No se encontró la moneda '{user_input}'. "
                "Verifica el nombre o símbolo e intenta de nuevo."
            )
            response_time = (time.time() - start_time) * 1000
            metrics_manager.record_command("ConsultarCryptoEspecifica", user_id, False, response_time)
            state_manager.set_state(user_id, ESTADO_PREGUNTA_OTRA_CONSULTA)
            await update.message.reply_text(format_continue_message())
            return ESTADO_PREGUNTA_OTRA_CONSULTA

        # Asegurar formato USDT
        if not symbol.endswith("USDT"):
            symbol = f"{symbol}USDT"

        # Obtener datos completos de la moneda
        coin_data = await exchange_aggregator.get_coin_data(symbol)

        if not coin_data:
            await update.message.reply_text(
                f"⚠️ No se encontraron datos para {symbol}. "
                "Es posible que el par no esté disponible."
            )
            response_time = (time.time() - start_time) * 1000
            metrics_manager.record_command("ConsultarCryptoEspecifica", user_id, False, response_time)
            state_manager.set_state(user_id, ESTADO_PREGUNTA_OTRA_CONSULTA)
            await update.message.reply_text(format_continue_message())
            return ESTADO_PREGUNTA_OTRA_CONSULTA

        # Obtener sentimiento (función compartida con caché)
        sentiment = await sentiment_service.get_sentiment()

        # Formatear y enviar
        message = format_coin_detail_message(coin_data, sentiment)
        await update.message.reply_text(message)

        # Pregunta de continuación
        await update.message.reply_text(format_continue_message())

        # Registrar métrica
        response_time = (time.time() - start_time) * 1000
        metrics_manager.record_command("ConsultarCryptoEspecifica", user_id, True, response_time)

    except Exception as e:
        logger.error(f"Error en /ConsultarCryptoEspecifica: {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error al consultar la criptomoneda. Intenta de nuevo."
        )
        response_time = (time.time() - start_time) * 1000
        metrics_manager.record_command("ConsultarCryptoEspecifica", user_id, False, response_time)
        await update.message.reply_text(format_continue_message())

    state_manager.set_state(user_id, ESTADO_PREGUNTA_OTRA_CONSULTA)
    return ESTADO_PREGUNTA_OTRA_CONSULTA
