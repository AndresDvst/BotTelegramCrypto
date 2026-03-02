"""
Handler para /OrdenesDeMercado.
Órdenes de compra/venta de una cripto específica.
Flujo: pregunta nombre/símbolo → resuelve → obtiene orderbook → muestra.
"""

import logging
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from config.config import (
    ESTADO_ESPERANDO_MONEDA_NOMBRE_ORDENES,
    ESTADO_PREGUNTA_OTRA_CONSULTA
)
from bot.utils.formatters import (
    format_orderbook_message,
    format_ask_coin_input,
    format_loading_message,
    format_continue_message
)
from bot.utils.timeout_manager import reset_inactivity_timer
from services.exchange_aggregator import exchange_aggregator
from services.sentiment_service import sentiment_service
from database.metrics_manager import metrics_manager
from bot.conversation.state_manager import state_manager

logger = logging.getLogger(__name__)


async def ordenes_mercado_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo de /OrdenesDeMercado preguntando por la moneda.

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        Estado esperando nombre/símbolo de moneda.
    """
    user_id = update.effective_user.id

    logger.info(f"Usuario {user_id} solicitó /OrdenesDeMercado")

    # Reset timer de inactividad
    await reset_inactivity_timer(user_id, update.effective_chat.id, context)

    # Mostrar indicador de "escribiendo..."
    await update.effective_chat.send_action(ChatAction.TYPING)

    # Preguntar nombre o símbolo
    await update.message.reply_text(format_ask_coin_input())

    state_manager.set_state(user_id, ESTADO_ESPERANDO_MONEDA_NOMBRE_ORDENES)
    return ESTADO_ESPERANDO_MONEDA_NOMBRE_ORDENES


async def ordenes_mercado_receive_coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre o símbolo de la moneda y muestra las órdenes.

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        Siguiente estado de la conversación.
    """
    start_time = time.time()
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    logger.info(f"Usuario {user_id} envió: {user_input} para OrdenesDeMercado")

    # Reset timer de inactividad
    await reset_inactivity_timer(user_id, update.effective_chat.id, context)

    # Mostrar indicador de "escribiendo..." y mensaje de carga
    await update.effective_chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(format_loading_message())

    try:
        # Resolver el símbolo
        symbol = await _resolve_symbol(user_input)

        if not symbol:
            await update.message.reply_text(
                f"❌ No se encontró la moneda '{user_input}'. "
                "Verifica el nombre o símbolo e intenta de nuevo."
            )
            response_time = (time.time() - start_time) * 1000
            metrics_manager.record_command("OrdenesDeMercado", user_id, False, response_time)
            state_manager.set_state(user_id, ESTADO_PREGUNTA_OTRA_CONSULTA)
            await update.message.reply_text(format_continue_message())
            return ESTADO_PREGUNTA_OTRA_CONSULTA

        # Asegurar formato USDT
        if not symbol.endswith("USDT"):
            symbol = f"{symbol}USDT"

        # Obtener orderbook de todos los exchanges
        orderbook = await exchange_aggregator.get_orderbook_aggregated(symbol, 20)

        if not orderbook.get("bids") and not orderbook.get("asks"):
            await update.message.reply_text(
                f"⚠️ No se encontraron órdenes para {symbol}. "
                "Es posible que el par no esté disponible en los exchanges."
            )
            response_time = (time.time() - start_time) * 1000
            metrics_manager.record_command("OrdenesDeMercado", user_id, False, response_time)
            state_manager.set_state(user_id, ESTADO_PREGUNTA_OTRA_CONSULTA)
            await update.message.reply_text(format_continue_message())
            return ESTADO_PREGUNTA_OTRA_CONSULTA

        # Obtener sentimiento (función compartida con caché)
        sentiment = await sentiment_service.get_sentiment()

        # Formatear y enviar
        message = format_orderbook_message(
            symbol=symbol,
            bids=orderbook.get("bids", []),
            asks=orderbook.get("asks", []),
            sentiment=sentiment
        )
        await update.message.reply_text(message)

        # Pregunta de continuación
        await update.message.reply_text(format_continue_message())

        # Registrar métrica
        response_time = (time.time() - start_time) * 1000
        metrics_manager.record_command("OrdenesDeMercado", user_id, True, response_time)

    except Exception as e:
        logger.error(f"Error en /OrdenesDeMercado: {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error al obtener las órdenes. Intenta de nuevo."
        )
        response_time = (time.time() - start_time) * 1000
        metrics_manager.record_command("OrdenesDeMercado", user_id, False, response_time)
        await update.message.reply_text(format_continue_message())

    state_manager.set_state(user_id, ESTADO_PREGUNTA_OTRA_CONSULTA)
    return ESTADO_PREGUNTA_OTRA_CONSULTA


async def _resolve_symbol(user_input: str) -> str | None:
    """Resuelve el input del usuario a un símbolo de cripto.

    Si es un símbolo corto (1-5 chars uppercase), lo usa directamente.
    Si parece un nombre, busca en CoinGecko.

    Args:
        user_input: Texto ingresado por el usuario.

    Returns:
        Símbolo de la moneda o None si no se encuentra.
    """
    cleaned = user_input.strip().upper()

    # Si parece un símbolo (corto, solo letras)
    if len(cleaned) <= 5 and cleaned.isalpha():
        return cleaned

    # Si parece un nombre, buscar en CoinGecko
    from services.sentiment_service import sentiment_service
    symbol = await sentiment_service.resolve_coin_name(user_input)
    return symbol
