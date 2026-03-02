"""
Manejo de timeout de inactividad por usuario.
Timer de 5 minutos que envía mensaje de despedida automático.
"""

import logging

from telegram.ext import CallbackContext

from config.config import Config, ESTADO_INICIO
from bot.utils.formatters import format_timeout_message

logger = logging.getLogger(__name__)

# Almacén de jobs activos por usuario
_active_timers: dict[int, str] = {}


async def _timeout_callback(context: CallbackContext) -> None:
    """Callback que se ejecuta cuando expira el timer de inactividad.

    Args:
        context: Contexto del bot con datos del job.
    """
    job_data = context.job.data
    if not isinstance(job_data, dict):
        return

    chat_id = job_data.get("chat_id")
    user_id = job_data.get("user_id")

    if chat_id is None:
        return

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=format_timeout_message()
        )
        logger.info(f"Timeout enviado al usuario {user_id}")
    except Exception as e:
        logger.error(f"Error enviando mensaje de timeout a {user_id}: {e}")

    # Limpiar el timer del registro
    if user_id in _active_timers:
        del _active_timers[user_id]


async def start_inactivity_timer(user_id: int, chat_id: int, context: CallbackContext) -> None:
    """Inicia un job de 5 minutos de inactividad.

    Si el usuario no hace nada en 5 minutos, envía mensaje de despedida
    y limpia el estado.

    Args:
        user_id: ID del usuario de Telegram.
        chat_id: ID del chat.
        context: Contexto del bot.
    """
    # Cancelar timer anterior si existe
    await cancel_inactivity_timer(user_id, context)

    job_name = f"timeout_{user_id}"
    context.job_queue.run_once(
        callback=_timeout_callback,
        when=Config.INACTIVITY_TIMEOUT_SECONDS,
        data={"chat_id": chat_id, "user_id": user_id},
        name=job_name
    )

    _active_timers[user_id] = job_name
    logger.info(f"Timer de inactividad iniciado para usuario {user_id}")


async def reset_inactivity_timer(user_id: int, chat_id: int, context: CallbackContext) -> None:
    """Cancela el timer anterior y crea uno nuevo.

    Debe llamarse al inicio de cada handler.

    Args:
        user_id: ID del usuario de Telegram.
        chat_id: ID del chat.
        context: Contexto del bot.
    """
    await start_inactivity_timer(user_id, chat_id, context)


async def cancel_inactivity_timer(user_id: int, context: CallbackContext) -> None:
    """Cancela el timer de inactividad de un usuario.

    Args:
        user_id: ID del usuario.
        context: Contexto del bot.
    """
    job_name = _active_timers.get(user_id)
    if job_name:
        jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in jobs:
            job.schedule_removal()
        del _active_timers[user_id]
        logger.info(f"Timer de inactividad cancelado para usuario {user_id}")
