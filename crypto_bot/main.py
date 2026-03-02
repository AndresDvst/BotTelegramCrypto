"""
Punto de entrada principal del bot de Telegram Crypto.
Inicia el bot de Telegram y el dashboard Flask en paralelo.
Maneja señales de cierre graceful (SIGTERM, SIGINT).
"""

import asyncio
import logging
import signal
import sys
import threading

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

from config.config import (
    Config,
    ESTADO_MENU_PRINCIPAL,
    ESTADO_ESPERANDO_MONEDA_NOMBRE_ORDENES,
    ESTADO_ESPERANDO_MONEDA_NOMBRE_CONSULTA,
    ESTADO_PREGUNTA_OTRA_CONSULTA
)
from database.models import init_db
from dashboard.app import run_dashboard

# Handlers
from bot.handlers.start_handler import start_command
from bot.handlers.top_subidas_4h import top_subidas_4h
from bot.handlers.top_bajadas_4h import top_bajadas_4h
from bot.handlers.top_subidas_24h import top_subidas_24h
from bot.handlers.top_bajadas_24h import top_bajadas_24h
from bot.handlers.sentimiento import sentimiento_del_mercado
from bot.handlers.ordenes_mercado import ordenes_mercado_start, ordenes_mercado_receive_coin
from bot.handlers.consultar_crypto import consultar_crypto_start, consultar_crypto_receive_coin
from bot.utils.formatters import format_menu_message, format_goodbye_message
from bot.utils.timeout_manager import cancel_inactivity_timer

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crypto_bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


async def handle_si(update, context) -> int:
    """Maneja la respuesta /si o 'sí' para continuar.

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        Estado del menú principal.
    """
    await update.message.reply_text(format_menu_message())
    return ESTADO_MENU_PRINCIPAL


async def handle_no(update, context) -> int:
    """Maneja la respuesta /no o 'no' para terminar.

    Args:
        update: Update de Telegram.
        context: Contexto del bot.

    Returns:
        ConversationHandler.END para finalizar la conversación.
    """
    user_id = update.effective_user.id
    await cancel_inactivity_timer(user_id, context)
    await update.message.reply_text(format_goodbye_message())
    return ConversationHandler.END


async def run_bot() -> None:
    """Función async que configura e inicia el bot de Telegram."""

    # Crear aplicación del bot
    logger.info("Configurando bot de Telegram...")
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Definir ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            MessageHandler(
                filters.Regex(r"(?i)^iniciar$"),
                start_command
            ),
        ],
        states={
            ESTADO_MENU_PRINCIPAL: [
                CommandHandler("TopSubidas4H", top_subidas_4h),
                CommandHandler("TopBajadas4H", top_bajadas_4h),
                CommandHandler("TopSubidas24H", top_subidas_24h),
                CommandHandler("TopBajadas24H", top_bajadas_24h),
                CommandHandler("SentimientoDelMercado", sentimiento_del_mercado),
                CommandHandler("OrdenesDeMercado", ordenes_mercado_start),
                CommandHandler("ConsultarCryptoEspecifica", consultar_crypto_start),
            ],
            ESTADO_ESPERANDO_MONEDA_NOMBRE_ORDENES: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    ordenes_mercado_receive_coin
                ),
            ],
            ESTADO_ESPERANDO_MONEDA_NOMBRE_CONSULTA: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    consultar_crypto_receive_coin
                ),
            ],
            ESTADO_PREGUNTA_OTRA_CONSULTA: [
                CommandHandler("si", handle_si),
                CommandHandler("no", handle_no),
                MessageHandler(
                    filters.Regex(r"(?i)^s[ií]$"),
                    handle_si
                ),
                MessageHandler(
                    filters.Regex(r"(?i)^no$"),
                    handle_no
                ),
            ],
        },
        fallbacks=[
            CommandHandler("start", start_command),
            MessageHandler(
                filters.Regex(r"(?i)^iniciar$"),
                start_command
            ),
        ],
        per_user=True,
        per_chat=True,
    )

    application.add_handler(conv_handler)

    # Iniciar bot usando initialize/start/polling manual (compatible con Python 3.14)
    logger.info("Bot de Telegram iniciando polling...")
    logger.info("Bot listo. Presiona Ctrl+C para detener.")

    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=["message"])

        # Mantener el bot corriendo hasta que se interrumpa
        stop_event = asyncio.Event()

        def signal_handler(sig, frame):
            logger.info(f"Señal {sig} recibida. Cerrando...")
            stop_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        await stop_event.wait()

        # Cierre graceful
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main() -> None:
    """Función principal que inicia el bot y el dashboard."""

    # Validar configuración
    errors = Config.validate()
    if errors:
        logger.error("Errores de configuración encontrados:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.warning("El bot iniciará pero algunas funcionalidades podrían no funcionar.")

    # Inicializar base de datos
    logger.info("Inicializando base de datos...")
    init_db()

    # Iniciar dashboard en un hilo separado
    logger.info("Iniciando dashboard web...")
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    logger.info(f"Dashboard corriendo en http://localhost:{Config.DASHBOARD_PORT}")

    # Ejecutar el bot con asyncio.run (compatible con Python 3.14)
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
