"""
Tests para el Dashboard API.
"""

import pytest
from unittest.mock import patch, MagicMock

from dashboard.app import create_app


@pytest.fixture
def client():
    """Fixture que crea un cliente de test de Flask."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_dashboard_page_loads(client):
    """Test GET / retorna la página del dashboard."""
    response = client.get("/")
    assert response.status_code == 200


def test_general_stats_returns_200(client):
    """Test GET /api/stats/general retorna 200."""
    with patch("dashboard.app.metrics_manager") as mock_metrics:
        mock_metrics.get_dashboard_stats.return_value = {
            "total_users": 10,
            "active_users_today": 3,
            "total_commands_today": 45,
            "total_api_calls_today": 120
        }
        response = client.get("/api/stats/general")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_users" in data
        assert data["total_users"] == 10


def test_commands_stats_returns_by_command(client):
    """Test GET /api/stats/commands retorna stats por comando."""
    with patch("dashboard.app.metrics_manager") as mock_metrics:
        mock_metrics.get_command_stats.return_value = {
            "start": 15,
            "TopSubidas4H": 8,
            "TopBajadas4H": 5,
            "SentimientoDelMercado": 12
        }
        response = client.get("/api/stats/commands")
        assert response.status_code == 200
        data = response.get_json()
        assert "start" in data
        assert data["TopSubidas4H"] == 8


def test_apis_stats_returns_by_api(client):
    """Test GET /api/stats/apis retorna stats por API."""
    with patch("dashboard.app.metrics_manager") as mock_metrics:
        mock_metrics.get_api_stats.return_value = {
            "binance": 50,
            "bybit": 30,
            "groq": 15,
            "coingecko": 20
        }
        response = client.get("/api/stats/apis")
        assert response.status_code == 200
        data = response.get_json()
        assert "binance" in data
        assert data["binance"] == 50


def test_users_stats_returns_200(client):
    """Test GET /api/stats/users retorna 200."""
    with patch("dashboard.app.metrics_manager") as mock_metrics:
        mock_metrics.get_user_stats.return_value = {
            "total": 25,
            "active_today": 5
        }
        response = client.get("/api/stats/users")
        assert response.status_code == 200


def test_timeline_stats_returns_200(client):
    """Test GET /api/stats/timeline retorna 200."""
    with patch("dashboard.app.metrics_manager") as mock_metrics:
        mock_metrics.get_timeline_stats.return_value = [
            {"hour": "10", "count": 5},
            {"hour": "11", "count": 8}
        ]
        response = client.get("/api/stats/timeline")
        assert response.status_code == 200


def test_recent_stats_returns_200(client):
    """Test GET /api/stats/recent retorna 200."""
    with patch("dashboard.app.metrics_manager") as mock_metrics:
        mock_metrics.get_recent_requests.return_value = [
            {"timestamp": "2024-01-01T10:00:00", "user_id": 123,
             "command": "start", "response_time_ms": 150, "success": True}
        ]
        response = client.get("/api/stats/recent")
        assert response.status_code == 200


def test_metrics_increment_correctly(client):
    """Test que las métricas se incrementan correctamente."""
    with patch("dashboard.app.metrics_manager") as mock_metrics:
        mock_metrics.get_dashboard_stats.return_value = {
            "total_users": 1, "active_users_today": 1,
            "total_commands_today": 1, "total_api_calls_today": 1
        }
        response1 = client.get("/api/stats/general")
        data1 = response1.get_json()

        mock_metrics.get_dashboard_stats.return_value = {
            "total_users": 2, "active_users_today": 2,
            "total_commands_today": 5, "total_api_calls_today": 10
        }
        response2 = client.get("/api/stats/general")
        data2 = response2.get_json()

        assert data2["total_commands_today"] > data1["total_commands_today"]
