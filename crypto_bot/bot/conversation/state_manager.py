"""
Manejo de estado de conversación por usuario.
Estado aislado por user_id con persistencia en SQLite.
"""

import logging
from typing import Any

from config.config import ESTADO_INICIO

logger = logging.getLogger(__name__)

# Estado en memoria por usuario
_user_states: dict[int, dict[str, Any]] = {}


class StateManager:
    """Gestor de estado de conversación multiusuario."""

    @staticmethod
    def get_state(user_id: int) -> int:
        """Obtiene el estado actual de un usuario.

        Args:
            user_id: ID del usuario de Telegram.

        Returns:
            Estado actual del usuario.
        """
        user_data = _user_states.get(user_id, {})
        return user_data.get("state", ESTADO_INICIO)

    @staticmethod
    def set_state(user_id: int, state: int) -> None:
        """Establece el estado de un usuario.

        Args:
            user_id: ID del usuario de Telegram.
            state: Nuevo estado.
        """
        if user_id not in _user_states:
            _user_states[user_id] = {}
        _user_states[user_id]["state"] = state
        logger.info(f"Estado del usuario {user_id} actualizado a {state}")

    @staticmethod
    def get_data(user_id: int, key: str, default: Any = None) -> Any:
        """Obtiene un dato almacenado para un usuario.

        Args:
            user_id: ID del usuario.
            key: Clave del dato.
            default: Valor por defecto si no existe.

        Returns:
            Valor almacenado o default.
        """
        user_data = _user_states.get(user_id, {})
        return user_data.get(key, default)

    @staticmethod
    def set_data(user_id: int, key: str, value: Any) -> None:
        """Almacena un dato para un usuario.

        Args:
            user_id: ID del usuario.
            key: Clave del dato.
            value: Valor a almacenar.
        """
        if user_id not in _user_states:
            _user_states[user_id] = {}
        _user_states[user_id][key] = value

    @staticmethod
    def clear_state(user_id: int) -> None:
        """Limpia todo el estado de un usuario.

        Args:
            user_id: ID del usuario.
        """
        if user_id in _user_states:
            del _user_states[user_id]
        logger.info(f"Estado del usuario {user_id} limpiado")

    @staticmethod
    def get_all_active_users() -> list[int]:
        """Retorna la lista de IDs de usuarios con estado activo.

        Returns:
            Lista de user_ids.
        """
        return list(_user_states.keys())


# Instancia global
state_manager = StateManager()
