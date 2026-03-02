"""
CRUD de métricas para el dashboard y monitoreo del bot.
Gestiona el registro y consulta de métricas de uso.
"""

import logging
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from database.models import (
    SessionLocal, UserSession, CommandMetric, ApiCallMetric, DailyStats
)

logger = logging.getLogger(__name__)


class MetricsManager:
    """Gestor de métricas del bot para el dashboard."""

    def __init__(self) -> None:
        """Inicializa el gestor de métricas."""
        pass

    def _get_session(self) -> Session:
        """Crea y retorna una nueva sesión de base de datos."""
        return SessionLocal()

    def record_command(self, command: str, user_id: int, success: bool, response_time: float) -> None:
        """Registra la ejecución de un comando.

        Args:
            command: Nombre del comando ejecutado.
            user_id: ID del usuario de Telegram.
            success: Si el comando se ejecutó correctamente.
            response_time: Tiempo de respuesta en milisegundos.
        """
        session = self._get_session()
        try:
            metric = CommandMetric(
                command_name=command,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                success=success,
                response_time_ms=response_time
            )
            session.add(metric)

            # Actualizar la sesión del usuario
            user_session = session.query(UserSession).filter_by(
                user_id=user_id, is_active=True
            ).first()
            if user_session:
                user_session.total_commands += 1
                user_session.last_activity = datetime.utcnow()

            session.commit()
            logger.info(f"Comando registrado: {command} por usuario {user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error al registrar comando: {e}")
        finally:
            session.close()

    def record_api_call(self, api_name: str, endpoint: str, success: bool,
                        response_time: float, status_code: int | None = None) -> None:
        """Registra una llamada a una API externa.

        Args:
            api_name: Nombre de la API (binance, bybit, kucoin, kraken, coinbase, coinmarketcap, coingecko, groq).
            endpoint: Endpoint consultado.
            success: Si la llamada fue exitosa.
            response_time: Tiempo de respuesta en milisegundos.
            status_code: Código de estado HTTP.
        """
        session = self._get_session()
        try:
            metric = ApiCallMetric(
                api_name=api_name,
                endpoint=endpoint,
                timestamp=datetime.utcnow(),
                success=success,
                response_time_ms=response_time,
                status_code=status_code
            )
            session.add(metric)
            session.commit()
            logger.info(f"API call registrada: {api_name} - {endpoint}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error al registrar API call: {e}")
        finally:
            session.close()

    def record_user_start(self, user_id: int, username: str | None, first_name: str | None) -> None:
        """Registra un nuevo inicio de sesión de usuario.

        Args:
            user_id: ID del usuario de Telegram.
            username: Nombre de usuario de Telegram.
            first_name: Nombre del usuario.
        """
        session = self._get_session()
        try:
            # Desactivar sesiones previas del usuario
            session.query(UserSession).filter_by(
                user_id=user_id, is_active=True
            ).update({"is_active": False})

            # Crear nueva sesión
            user_session = UserSession(
                user_id=user_id,
                username=username,
                first_name=first_name,
                started_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                total_commands=0,
                is_active=True
            )
            session.add(user_session)
            session.commit()
            logger.info(f"Sesión de usuario registrada: {user_id} ({first_name})")
        except Exception as e:
            session.rollback()
            logger.error(f"Error al registrar sesión de usuario: {e}")
        finally:
            session.close()

    def get_dashboard_stats(self) -> dict:
        """Retorna estadísticas generales para el dashboard.

        Returns:
            Dict con total_users, active_users_today, total_commands_today, total_api_calls_today.
        """
        session = self._get_session()
        try:
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())

            total_users = session.query(
                func.count(func.distinct(UserSession.user_id))
            ).scalar() or 0

            active_users_today = session.query(
                func.count(func.distinct(CommandMetric.user_id))
            ).filter(CommandMetric.timestamp >= today_start).scalar() or 0

            total_commands_today = session.query(
                func.count(CommandMetric.id)
            ).filter(CommandMetric.timestamp >= today_start).scalar() or 0

            total_api_calls_today = session.query(
                func.count(ApiCallMetric.id)
            ).filter(ApiCallMetric.timestamp >= today_start).scalar() or 0

            return {
                "total_users": total_users,
                "active_users_today": active_users_today,
                "total_commands_today": total_commands_today,
                "total_api_calls_today": total_api_calls_today
            }
        except Exception as e:
            logger.error(f"Error al obtener stats del dashboard: {e}")
            return {
                "total_users": 0,
                "active_users_today": 0,
                "total_commands_today": 0,
                "total_api_calls_today": 0
            }
        finally:
            session.close()

    def get_command_stats(self) -> dict:
        """Retorna estadísticas por comando.

        Returns:
            Dict con nombre de comando como clave y cantidad como valor.
        """
        session = self._get_session()
        try:
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())

            results = session.query(
                CommandMetric.command_name,
                func.count(CommandMetric.id).label("count")
            ).filter(
                CommandMetric.timestamp >= today_start
            ).group_by(
                CommandMetric.command_name
            ).all()

            return {row.command_name: row.count for row in results}
        except Exception as e:
            logger.error(f"Error al obtener command stats: {e}")
            return {}
        finally:
            session.close()

    def get_api_stats(self) -> dict:
        """Retorna estadísticas por API externa.

        Returns:
            Dict con nombre de API como clave y cantidad como valor.
        """
        session = self._get_session()
        try:
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())

            results = session.query(
                ApiCallMetric.api_name,
                func.count(ApiCallMetric.id).label("count")
            ).filter(
                ApiCallMetric.timestamp >= today_start
            ).group_by(
                ApiCallMetric.api_name
            ).all()

            return {row.api_name: row.count for row in results}
        except Exception as e:
            logger.error(f"Error al obtener API stats: {e}")
            return {}
        finally:
            session.close()

    def get_user_stats(self) -> dict:
        """Retorna estadísticas de usuarios.

        Returns:
            Dict con total y activos hoy.
        """
        session = self._get_session()
        try:
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())

            total = session.query(
                func.count(func.distinct(UserSession.user_id))
            ).scalar() or 0

            active_today = session.query(
                func.count(func.distinct(UserSession.user_id))
            ).filter(
                UserSession.last_activity >= today_start
            ).scalar() or 0

            return {"total": total, "active_today": active_today}
        except Exception as e:
            logger.error(f"Error al obtener user stats: {e}")
            return {"total": 0, "active_today": 0}
        finally:
            session.close()

    def get_timeline_stats(self) -> list[dict]:
        """Retorna actividad por hora de las últimas 24 horas.

        Returns:
            Lista de dicts con hour y count.
        """
        session = self._get_session()
        try:
            since = datetime.utcnow() - timedelta(hours=24)

            results = session.query(
                func.strftime('%H', CommandMetric.timestamp).label("hour"),
                func.count(CommandMetric.id).label("count")
            ).filter(
                CommandMetric.timestamp >= since
            ).group_by(
                func.strftime('%H', CommandMetric.timestamp)
            ).order_by("hour").all()

            return [{"hour": row.hour, "count": row.count} for row in results]
        except Exception as e:
            logger.error(f"Error al obtener timeline stats: {e}")
            return []
        finally:
            session.close()

    def get_recent_requests(self, limit: int = 20) -> list[dict]:
        """Retorna las últimas N peticiones.

        Args:
            limit: Número máximo de peticiones a retornar.

        Returns:
            Lista de dicts con timestamp, user_id, command, response_time, success.
        """
        session = self._get_session()
        try:
            results = session.query(CommandMetric).order_by(
                desc(CommandMetric.timestamp)
            ).limit(limit).all()

            return [
                {
                    "timestamp": metric.timestamp.isoformat(),
                    "user_id": metric.user_id,
                    "command": metric.command_name,
                    "response_time_ms": metric.response_time_ms,
                    "success": metric.success
                }
                for metric in results
            ]
        except Exception as e:
            logger.error(f"Error al obtener peticiones recientes: {e}")
            return []
        finally:
            session.close()


# Instancia global del gestor de métricas
metrics_manager = MetricsManager()
