"""
Configuración centralizada del bot.
Todas las variables de entorno se cargan desde un archivo .env
"""

import os
import logging
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Configuración centralizada desde variables de entorno."""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Groq IA
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # CoinMarketCap
    COINMARKETCAP_API_KEY: str = os.getenv("COINMARKETCAP_API_KEY", "")

    # Dashboard
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "5000"))
    DASHBOARD_SECRET_KEY: str = os.getenv("DASHBOARD_SECRET_KEY", "cambia_esto_por_algo_seguro")

    # Base de datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///crypto_bot.db")

    # Configuración del bot
    MIN_CHANGE_PERCENT: float = float(os.getenv("MIN_CHANGE_PERCENT", "5"))
    TOP_N_RESULTS: int = int(os.getenv("TOP_N_RESULTS", "10"))
    TOP_RECOMMENDATIONS: int = int(os.getenv("TOP_RECOMMENDATIONS", "3"))
    INACTIVITY_TIMEOUT_SECONDS: int = int(os.getenv("INACTIVITY_TIMEOUT_SECONDS", "300"))

    # Constantes de la aplicación
    HTTP_TIMEOUT: int = 10  # Timeout en segundos para llamadas HTTP
    MAX_RETRIES: int = 3  # Máximo de reintentos con backoff exponencial
    SENTIMENT_CACHE_TTL: int = 600  # Caché de sentimiento: 10 minutos (600 segundos)

    # Modelos de Groq
    GROQ_MODEL_PRIMARY: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_FALLBACK: str = "mixtral-8x7b-32768"
    GROQ_MAX_TOKENS: int = 500
    GROQ_TEMPERATURE: float = 0.3

    @classmethod
    def validate(cls) -> list[str]:
        """Valida que las variables de entorno críticas estén configuradas.

        Returns:
            Lista de errores de validación. Lista vacía si todo está correcto.
        """
        errors: list[str] = []

        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN no está configurado")
        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY no está configurado")
        if not cls.COINMARKETCAP_API_KEY:
            errors.append("COINMARKETCAP_API_KEY no está configurado")

        for error in errors:
            logger.error(f"Error de configuración: {error}")

        return errors


# Estados de conversación
ESTADO_INICIO = 0
ESTADO_MENU_PRINCIPAL = 1
ESTADO_ESPERANDO_MONEDA_NOMBRE_ORDENES = 2
ESTADO_ESPERANDO_MONEDA_SIMBOLO_ORDENES = 3
ESTADO_ESPERANDO_MONEDA_NOMBRE_CONSULTA = 4
ESTADO_ESPERANDO_MONEDA_SIMBOLO_CONSULTA = 5
ESTADO_PREGUNTA_OTRA_CONSULTA = 6
ESTADO_INACTIVO = 7
