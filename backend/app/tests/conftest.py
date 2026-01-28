# =============================================================================
# NESTSECURE - Configuración de Pytest
# =============================================================================
"""
Fixtures y configuración global para tests.

Este módulo contiene:
- Fixtures compartidos entre todos los tests
- Configuración del cliente de pruebas
- Mocks comunes
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import app, app_state


# =============================================================================
# Configuración de pytest-asyncio
# =============================================================================
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Crea un event loop para toda la sesión de tests.
    
    Esto permite reutilizar el event loop entre tests async,
    mejorando el rendimiento.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Settings para tests
# =============================================================================
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    Configuración específica para tests.
    
    Sobreescribe valores que podrían causar problemas en tests
    (conexiones a servicios externos, etc.)
    """
    return Settings(
        ENVIRONMENT="testing",
        DEBUG=True,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test_db",
        REDIS_URL="redis://localhost:6379/15",  # DB separada para tests
        SECRET_KEY="test-secret-key-for-testing-only",
    )


# =============================================================================
# HTTP Client para tests
# =============================================================================
@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP asíncrono para probar endpoints.
    
    Uso:
        async def test_endpoint(async_client):
            response = await async_client.get("/health")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client


@pytest.fixture
def client() -> Generator[AsyncClient, None, None]:
    """
    Fixture síncrono que crea el cliente asíncrono.
    Para tests que no necesitan ser async.
    """
    transport = ASGITransport(app=app)
    with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


# =============================================================================
# Mock de Redis
# =============================================================================
@pytest.fixture
def mock_redis_connected(monkeypatch):
    """
    Simula que Redis está conectado.
    """
    monkeypatch.setattr(app_state, "redis_connected", True)


@pytest.fixture
def mock_redis_disconnected(monkeypatch):
    """
    Simula que Redis NO está conectado.
    """
    monkeypatch.setattr(app_state, "redis_connected", False)
    monkeypatch.setattr(app_state, "redis_client", None)


# =============================================================================
# Fixtures de datos de prueba
# =============================================================================
@pytest.fixture
def sample_user_data() -> dict:
    """Datos de usuario de prueba."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }


@pytest.fixture
def sample_asset_data() -> dict:
    """Datos de asset de prueba."""
    return {
        "name": "Test Server",
        "ip_address": "192.168.1.100",
        "asset_type": "server",
        "hostname": "test-server.local",
    }


@pytest.fixture
def sample_scan_config() -> dict:
    """Configuración de escaneo de prueba."""
    return {
        "name": "Test Scan",
        "scan_type": "nmap",
        "targets": ["192.168.1.0/24"],
        "options": {
            "ports": "1-1000",
            "timing": "T3",
        }
    }


# =============================================================================
# Utilidades de testing
# =============================================================================
class ResponseValidator:
    """
    Helper para validar respuestas HTTP.
    
    Uso:
        validator = ResponseValidator(response)
        validator.assert_success()
        validator.assert_has_key("data")
    """
    
    def __init__(self, response):
        self.response = response
        self.data = response.json() if response.content else {}
    
    def assert_success(self):
        """Verifica que la respuesta sea exitosa (2xx)."""
        assert 200 <= self.response.status_code < 300, (
            f"Expected success, got {self.response.status_code}: {self.data}"
        )
        return self
    
    def assert_status(self, expected_status: int):
        """Verifica el código de estado específico."""
        assert self.response.status_code == expected_status, (
            f"Expected {expected_status}, got {self.response.status_code}"
        )
        return self
    
    def assert_has_key(self, key: str):
        """Verifica que la respuesta contenga una clave."""
        assert key in self.data, f"Key '{key}' not found in response"
        return self
    
    def assert_equals(self, key: str, value):
        """Verifica el valor de una clave."""
        assert self.data.get(key) == value, (
            f"Expected {key}={value}, got {self.data.get(key)}"
        )
        return self


@pytest.fixture
def response_validator():
    """Factory fixture para crear validadores."""
    return ResponseValidator
