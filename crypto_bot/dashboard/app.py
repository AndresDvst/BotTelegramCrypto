"""
Flask app del dashboard de monitoreo.
Endpoints REST para estadísticas y UI HTML con Chart.js.
"""

import logging
from flask import Flask, jsonify, render_template

from config.config import Config
from database.metrics_manager import metrics_manager

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Crea y configura la aplicación Flask del dashboard.

    Returns:
        Instancia de Flask configurada.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )
    app.secret_key = Config.DASHBOARD_SECRET_KEY

    @app.route("/")
    def dashboard():
        """Renderiza la página principal del dashboard."""
        return render_template("dashboard.html")

    @app.route("/api/stats/general")
    def stats_general():
        """Retorna estadísticas generales del bot.

        Returns:
            JSON con total_users, active_users_today, total_commands_today, total_api_calls_today.
        """
        try:
            stats = metrics_manager.get_dashboard_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error en /api/stats/general: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/stats/commands")
    def stats_commands():
        """Retorna estadísticas por comando.

        Returns:
            JSON con nombre de comando y cantidad.
        """
        try:
            stats = metrics_manager.get_command_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error en /api/stats/commands: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/stats/apis")
    def stats_apis():
        """Retorna estadísticas por API externa.

        Returns:
            JSON con nombre de API y cantidad.
        """
        try:
            stats = metrics_manager.get_api_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error en /api/stats/apis: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/stats/users")
    def stats_users():
        """Retorna estadísticas de usuarios.

        Returns:
            JSON con total y activos hoy.
        """
        try:
            stats = metrics_manager.get_user_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error en /api/stats/users: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/stats/timeline")
    def stats_timeline():
        """Retorna actividad por hora (últimas 24h).

        Returns:
            JSON con lista de {hour, count}.
        """
        try:
            stats = metrics_manager.get_timeline_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error en /api/stats/timeline: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/stats/recent")
    def stats_recent():
        """Retorna las últimas 20 peticiones.

        Returns:
            JSON con lista de peticiones recientes.
        """
        try:
            recent = metrics_manager.get_recent_requests(limit=20)
            return jsonify(recent)
        except Exception as e:
            logger.error(f"Error en /api/stats/recent: {e}")
            return jsonify({"error": str(e)}), 500

    return app


def run_dashboard() -> None:
    """Ejecuta el dashboard Flask."""
    app = create_app()
    logger.info(f"Dashboard iniciando en puerto {Config.DASHBOARD_PORT}")
    app.run(
        host="0.0.0.0",
        port=Config.DASHBOARD_PORT,
        debug=False,
        use_reloader=False
    )
