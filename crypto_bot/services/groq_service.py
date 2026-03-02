"""
Servicio de análisis IA con Groq.
Modelo preferido: llama-3.3-70b-versatile
Fallback: mixtral-8x7b-32768
"""

import json
import logging
import asyncio

from groq import AsyncGroq

from config.config import Config
from database.metrics_manager import metrics_manager

logger = logging.getLogger(__name__)


class GroqService:
    """Servicio de análisis de criptomonedas con Groq IA."""

    def __init__(self) -> None:
        """Inicializa el servicio de Groq."""
        self.client = AsyncGroq(api_key=Config.GROQ_API_KEY)

    async def get_recommendations(
        self,
        top_coins: list[dict],
        sentiment: dict,
        timeframe: str,
        direction: str
    ) -> str:
        """Obtiene recomendaciones de IA basadas en los datos del top 10.

        Args:
            top_coins: Lista de dicts con datos de las top monedas.
            sentiment: Dict con datos de sentimiento del mercado.
            timeframe: '4h' o '24h'.
            direction: 'up' (subida) o 'down' (bajada).

        Returns:
            String formateado con las 3 recomendaciones de IA.
        """
        direction_text = "subida" if direction == "up" else "bajada"
        timeframe_text = "4 horas" if timeframe == "4h" else "24 horas"

        prompt = (
            f"Analiza estos datos de las {len(top_coins)} criptomonedas con mayor "
            f"{direction_text} en las últimas {timeframe_text}.\n"
            f"Datos: {json.dumps(top_coins, ensure_ascii=False)}\n"
            f"Sentimiento del mercado actual: {json.dumps(sentiment, ensure_ascii=False)}\n"
            f"Basándote en los datos, recomienda las {Config.TOP_RECOMMENDATIONS} mejores "
            f"oportunidades justificando brevemente cada una.\n"
            f"Responde en español, de forma concisa, con máximo 3 líneas por recomendación."
        )

        # Intentar con modelo principal, luego fallback
        models = [Config.GROQ_MODEL_PRIMARY, Config.GROQ_MODEL_FALLBACK]

        for model in models:
            result = await self._call_groq(prompt, model)
            if result is not None:
                return result

        # Si todo falla, retornar mensaje de error
        logger.error("Groq: todos los modelos fallaron")
        return "⚠️ Análisis IA no disponible temporalmente"

    async def _call_groq(self, prompt: str, model: str) -> str | None:
        """Realiza una llamada a Groq con retry exponencial.

        Args:
            prompt: Texto del prompt.
            model: Nombre del modelo a usar.

        Returns:
            Respuesta de Groq como string o None si falla.
        """
        import time

        for attempt in range(Config.MAX_RETRIES):
            start_time = time.time()
            try:
                chat_completion = await self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un analista experto en criptomonedas. "
                                "Responde siempre en español, de forma concisa y profesional."
                            )
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=model,
                    max_tokens=Config.GROQ_MAX_TOKENS,
                    temperature=Config.GROQ_TEMPERATURE
                )

                response_time = (time.time() - start_time) * 1000
                response_text = chat_completion.choices[0].message.content

                metrics_manager.record_api_call(
                    api_name="groq",
                    endpoint=f"/chat/completions/{model}",
                    success=True,
                    response_time=response_time,
                    status_code=200
                )

                logger.info(f"Groq ({model}): respuesta obtenida en {response_time:.0f}ms")
                return response_text

            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                logger.error(
                    f"Groq ({model}) - Intento {attempt + 1}/{Config.MAX_RETRIES}: {e}"
                )

                metrics_manager.record_api_call(
                    api_name="groq",
                    endpoint=f"/chat/completions/{model}",
                    success=False,
                    response_time=response_time,
                    status_code=None
                )

                if attempt < Config.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Groq: esperando {wait_time}s antes de reintentar...")
                    await asyncio.sleep(wait_time)

        return None


# Instancia global del servicio de Groq
groq_service = GroqService()
