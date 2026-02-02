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


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture asíncrono que crea el cliente asíncrono.
    Para tests async.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def client_with_db(db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente de test con base de datos de prueba configurada.
    Hace override de la dependencia get_db para usar SQLite en memoria.
    """
    from app.db.session import get_db
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client
    
    # Limpiar override
    app.dependency_overrides.clear()


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
# Fixtures de Base de Datos para Tests
# =============================================================================
@pytest_asyncio.fixture
async def db_session():
    """
    Crea una sesión de base de datos para tests.
    
    Usa SQLite en archivo temporal para tests rápidos.
    """
    import tempfile
    import os
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    
    from app.db.base import Base
    # Importar todos los modelos para que SQLAlchemy registre las tablas
    from app.models import Organization, User, Asset, Service  # noqa: F401
    from app.models.scan import Scan  # noqa: F401
    from app.models.cve_cache import CVECache  # noqa: F401
    from app.models.vulnerability import Vulnerability  # noqa: F401
    
    # Usar SQLite en memoria con StaticPool para compartir conexión
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,  # Mantiene una sola conexión compartida
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    # Crear todas las tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Crear session maker
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()
    
    # Limpiar
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


# Alias para compatibilidad
@pytest_asyncio.fixture
async def db(db_session):
    """Alias de db_session para compatibilidad."""
    yield db_session


# Alias test_db para compatibilidad con tests existentes
@pytest_asyncio.fixture
async def test_db(db_session):
    """Alias de db_session para tests que usan test_db."""
    yield db_session


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
        "ip_address": "192.168.1.100",
        "asset_type": "server",
        "hostname": "test-server.local",
        "criticality": "medium",
    }


@pytest.fixture
def sample_organization_data() -> dict:
    """Datos de organización de prueba."""
    return {
        "name": "Test Organization",
        "slug": "test-org",
        "description": "Organization for testing",
        "max_assets": 100,
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
# Fixtures de Autenticación
# =============================================================================
@pytest_asyncio.fixture
async def test_organization(db_session):
    """
    Crea una organización de prueba en la base de datos.
    """
    from app.models.organization import Organization
    
    org = Organization(
        name="Test Organization",
        slug="test-org",
        description="Organization for testing",
        max_assets=100,
        is_active=True,
        settings={},
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db_session, test_organization):
    """
    Crea un usuario de prueba en la base de datos.
    """
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash
    
    user = User(
        email="testuser@example.com",
        hashed_password=get_password_hash("TestPassword123!"),
        full_name="Test User",
        organization_id=test_organization.id,
        role=UserRole.VIEWER,  # Usuario normal con rol viewer
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session, test_organization):
    """
    Crea un usuario admin de prueba.
    """
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash
    
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPassword123!"),
        full_name="Admin User",
        organization_id=test_organization.id,
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_superuser(db_session, test_organization):
    """
    Crea un superusuario de prueba.
    """
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash
    
    superuser = User(
        email="superuser@example.com",
        hashed_password=get_password_hash("SuperPassword123!"),
        full_name="Super User",
        organization_id=test_organization.id,
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
    )
    db_session.add(superuser)
    await db_session.commit()
    await db_session.refresh(superuser)
    return superuser


@pytest_asyncio.fixture
async def test_operator(db_session, test_organization):
    """
    Crea un usuario operator de prueba.
    """
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash
    
    operator = User(
        email="operator@example.com",
        hashed_password=get_password_hash("OperatorPassword123!"),
        full_name="Operator User",
        organization_id=test_organization.id,
        role=UserRole.OPERATOR,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(operator)
    await db_session.commit()
    await db_session.refresh(operator)
    return operator


@pytest.fixture
def auth_headers_factory():
    """
    Factory para crear headers de autenticación.
    """
    from app.core.security import create_access_token
    
    def _create_headers(user_id: str, **extra_claims) -> dict:
        token = create_access_token(subject=user_id, **extra_claims)
        return {"Authorization": f"Bearer {token}"}
    
    return _create_headers


@pytest_asyncio.fixture
async def auth_headers(test_user, auth_headers_factory):
    """
    Headers de autenticación para un usuario normal.
    """
    return auth_headers_factory(str(test_user.id))


@pytest_asyncio.fixture
async def admin_auth_headers(test_admin, auth_headers_factory):
    """
    Headers de autenticación para un admin.
    """
    return auth_headers_factory(str(test_admin.id))


@pytest_asyncio.fixture
async def auth_headers_admin(test_admin, auth_headers_factory):
    """
    Alias para admin_auth_headers (compatibilidad).
    """
    return auth_headers_factory(str(test_admin.id))


@pytest_asyncio.fixture
async def auth_headers_operator(test_operator, auth_headers_factory):
    """
    Headers de autenticación para un operator.
    """
    return auth_headers_factory(str(test_operator.id))


@pytest_asyncio.fixture
async def superuser_auth_headers(test_superuser, auth_headers_factory):
    """
    Headers de autenticación para un superusuario.
    """
    return auth_headers_factory(str(test_superuser.id))


@pytest_asyncio.fixture
async def api_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP con base de datos de prueba inyectada.
    
    Este cliente sobreescribe la dependencia get_db para usar
    la sesión de prueba en lugar de la real.
    """
    from app.main import app
    from app.db.session import get_db
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client
    
    # Limpiar override
    app.dependency_overrides.clear()


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
