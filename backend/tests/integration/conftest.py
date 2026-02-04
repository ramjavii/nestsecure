# =============================================================================
# NESTSECURE - Configuración de Tests de Integración
# =============================================================================
"""
Fixtures para tests de integración.

Importa fixtures de app/tests/conftest.py y agrega fixtures específicos
para tests de integración.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app


# =============================================================================
# Configuración de pytest-asyncio
# =============================================================================
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Crea un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Base de Datos para Tests de Integración
# =============================================================================
@pytest_asyncio.fixture
async def db_session():
    """
    Crea una sesión de base de datos para tests.
    Usa SQLite en memoria para tests rápidos.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    
    from app.db.base import Base
    # Importar todos los modelos
    from app.models import Organization, User, Asset, Service  # noqa: F401
    from app.models.scan import Scan  # noqa: F401
    from app.models.cve_cache import CVECache  # noqa: F401
    from app.models.vulnerability import Vulnerability  # noqa: F401
    
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def client_with_db(db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente de test con base de datos configurada.
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
    
    app.dependency_overrides.clear()


# =============================================================================
# Fixtures de Datos de Prueba
# =============================================================================
@pytest_asyncio.fixture
async def test_organization(db_session):
    """Crear organización de prueba."""
    from app.models import Organization
    
    org = Organization(
        name="Integration Test Org",
        slug="integration-test-org",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db_session, test_organization):
    """Crear usuario de prueba."""
    from app.models import User
    from app.core.security import get_password_hash
    
    user = User(
        email="integration@test.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Integration Test User",
        organization_id=test_organization.id,
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers_factory():
    """Factory para crear headers de autenticación."""
    from app.core.security import create_access_token
    
    def _create_headers(user_id: str, **extra_claims) -> dict:
        token = create_access_token(subject=user_id, **extra_claims)
        return {"Authorization": f"Bearer {token}"}
    
    return _create_headers


@pytest_asyncio.fixture
async def auth_headers(test_user, auth_headers_factory):
    """Headers de autenticación con token válido."""
    return auth_headers_factory(str(test_user.id))


# =============================================================================
# Fixtures de Datos de Escaneo
# =============================================================================
@pytest.fixture
def completed_nuclei_result():
    """Resultado mock de escaneo Nuclei completado."""
    return {
        "task_id": "test-nuclei-task-123",
        "status": "completed",
        "target": "https://test-target.local",
        "profile": "standard",
        "started_at": "2024-01-15T10:00:00Z",
        "completed_at": "2024-01-15T10:15:00Z",
        "duration_seconds": 900,
        "total_findings": 4,
        "findings": [
            {
                "template_id": "CVE-2021-44228",
                "name": "Log4j RCE",
                "severity": "critical",
                "type": "vulnerability",
                "host": "https://test-target.local",
                "matched_at": "https://test-target.local/api/login",
                "description": "Log4j Remote Code Execution vulnerability",
                "cve_id": "CVE-2021-44228",
                "cvss_score": 10.0,
                "reference": ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
                "tags": ["cve", "rce", "critical"],
                "curl_command": "curl -X POST 'https://test-target.local/api/login'",
                "timestamp": "2024-01-15T10:05:00Z",
            },
            {
                "template_id": "http-missing-security-headers",
                "name": "Missing Security Headers",
                "severity": "info",
                "type": "misconfiguration",
                "host": "https://test-target.local",
                "matched_at": "https://test-target.local",
                "description": "Security headers not found",
                "cve_id": None,
                "cvss_score": None,
                "reference": [],
                "tags": ["headers", "security"],
                "curl_command": None,
                "timestamp": "2024-01-15T10:06:00Z",
            },
            {
                "template_id": "exposed-git",
                "name": "Git Directory Exposure",
                "severity": "high",
                "type": "exposure",
                "host": "https://test-target.local",
                "matched_at": "https://test-target.local/.git/config",
                "description": "Git repository exposed",
                "cve_id": None,
                "cvss_score": None,
                "reference": [],
                "tags": ["exposure", "git"],
                "curl_command": None,
                "timestamp": "2024-01-15T10:07:00Z",
            },
            {
                "template_id": "ssl-weak-cipher",
                "name": "Weak SSL Cipher",
                "severity": "medium",
                "type": "vulnerability",
                "host": "https://test-target.local",
                "matched_at": "https://test-target.local:443",
                "description": "Weak cipher suite detected",
                "cve_id": None,
                "cvss_score": None,
                "reference": [],
                "tags": ["ssl", "tls"],
                "curl_command": None,
                "timestamp": "2024-01-15T10:08:00Z",
            },
        ],
        "severity_summary": {
            "critical": 1,
            "high": 1,
            "medium": 1,
            "low": 0,
            "info": 1,
        },
        "unique_cves": ["CVE-2021-44228"],
    }


@pytest.fixture
def completed_nmap_result():
    """Resultado mock de escaneo Nmap completado."""
    return {
        "task_id": "test-nmap-task-123",
        "status": "completed",
        "target": "192.168.1.100",
        "profile": "quick",
        "started_at": "2024-01-15T10:00:00Z",
        "completed_at": "2024-01-15T10:02:00Z",
        "duration_seconds": 120,
        "hosts_up": 1,
        "hosts_down": 0,
        "total_ports": 3,
        "open_ports": [
            {
                "port": 22,
                "protocol": "tcp",
                "state": "open",
                "service": "ssh",
                "version": "OpenSSH 8.2p1",
            },
            {
                "port": 80,
                "protocol": "tcp",
                "state": "open",
                "service": "http",
                "version": "nginx 1.18.0",
            },
            {
                "port": 443,
                "protocol": "tcp",
                "state": "open",
                "service": "https",
                "version": "nginx 1.18.0",
            },
        ],
        "os_detection": {
            "name": "Linux",
            "accuracy": 95,
            "type": "general purpose",
        },
    }
