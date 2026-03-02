"""
Modelos SQLAlchemy para métricas y estado del bot.
Tablas: UserSession, CommandMetric, ApiCallMetric, DailyStats.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Date
from sqlalchemy.orm import declarative_base, sessionmaker

from config.config import Config

Base = declarative_base()


class UserSession(Base):
    """Registra sesiones de usuarios del bot."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_commands = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<UserSession(user_id={self.user_id}, username={self.username})>"


class CommandMetric(Base):
    """Registra métricas de cada comando ejecutado."""
    __tablename__ = "command_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    command_name = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    response_time_ms = Column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<CommandMetric(command={self.command_name}, user_id={self.user_id})>"


class ApiCallMetric(Base):
    """Registra métricas de cada llamada a APIs externas."""
    __tablename__ = "api_call_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_name = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    response_time_ms = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<ApiCallMetric(api={self.api_name}, success={self.success})>"


class DailyStats(Base):
    """Estadísticas diarias agregadas."""
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    total_users = Column(Integer, default=0, nullable=False)
    total_commands = Column(Integer, default=0, nullable=False)
    total_api_calls = Column(Integer, default=0, nullable=False)
    most_used_command = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<DailyStats(date={self.date}, total_commands={self.total_commands})>"


# Motor y sesión de base de datos
engine = create_engine(Config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """Inicializa la base de datos creando todas las tablas."""
    Base.metadata.create_all(bind=engine)
