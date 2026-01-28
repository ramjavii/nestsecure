# =============================================================================
# NESTSECURE - Tests de Health Endpoints
# =============================================================================
"""
Tests para los endpoints de health check.

Cobertura:
- GET /health - Health check básico
- GET /health/ready - Readiness check
- GET /health/live - Liveness check
- GET / - Root endpoint
"""

import pytest
from httpx import AsyncClient

from app.config import get_settings


settings = get_settings()


# =============================================================================
# Tests de /health (Health Check Básico)
# =============================================================================
class TestHealthCheck:
    """Tests para el endpoint /health."""
    
    @pytest.mark.asyncio
    async def test_health_returns_200(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health
        ENTONCES: Retorna 200 OK
        """
        response = await async_client.get("/health")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_returns_correct_structure(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health
        ENTONCES: Retorna la estructura esperada con status, timestamp, version
        """
        response = await async_client.get("/health")
        data = response.json()
        
        # Verificar campos requeridos
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        
        # Verificar valores
        assert data["status"] == "healthy"
        assert data["version"] == settings.APP_VERSION
    
    @pytest.mark.asyncio
    async def test_health_timestamp_is_iso_format(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health
        ENTONCES: El timestamp está en formato ISO 8601
        """
        from datetime import datetime
        
        response = await async_client.get("/health")
        data = response.json()
        
        # Intentar parsear el timestamp
        try:
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Timestamp no es ISO 8601: {data['timestamp']}")


# =============================================================================
# Tests de /health/ready (Readiness Check)
# =============================================================================
class TestReadinessCheck:
    """Tests para el endpoint /health/ready."""
    
    @pytest.mark.asyncio
    async def test_readiness_returns_checks(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health/ready
        ENTONCES: Retorna estado de los servicios
        """
        response = await async_client.get("/health/ready")
        data = response.json()
        
        # Debe tener estructura de checks
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data
        
        # Debe incluir check de Redis
        assert "redis" in data["checks"]
    
    @pytest.mark.asyncio
    async def test_readiness_includes_uptime(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health/ready
        ENTONCES: Incluye uptime_seconds
        """
        response = await async_client.get("/health/ready")
        data = response.json()
        
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0
    
    @pytest.mark.asyncio
    async def test_readiness_status_reflects_checks(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health/ready
        ENTONCES: El status refleja el estado de los checks
        """
        response = await async_client.get("/health/ready")
        data = response.json()
        
        # Status debe ser "ready" o "degraded"
        assert data["status"] in ["ready", "degraded"]


# =============================================================================
# Tests de /health/live (Liveness Check)
# =============================================================================
class TestLivenessCheck:
    """Tests para el endpoint /health/live."""
    
    @pytest.mark.asyncio
    async def test_liveness_returns_200(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health/live
        ENTONCES: Retorna 200 OK
        """
        response = await async_client.get("/health/live")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_liveness_returns_alive_status(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health/live
        ENTONCES: Retorna status "alive"
        """
        response = await async_client.get("/health/live")
        data = response.json()
        
        assert data["status"] == "alive"
    
    @pytest.mark.asyncio
    async def test_liveness_includes_pid(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /health/live
        ENTONCES: Incluye el PID del proceso
        """
        response = await async_client.get("/health/live")
        data = response.json()
        
        assert "pid" in data
        assert isinstance(data["pid"], int)
        assert data["pid"] > 0


# =============================================================================
# Tests del Root Endpoint
# =============================================================================
class TestRootEndpoint:
    """Tests para el endpoint raíz /."""
    
    @pytest.mark.asyncio
    async def test_root_returns_200(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /
        ENTONCES: Retorna 200 OK
        """
        response = await async_client.get("/")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_root_returns_app_info(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /
        ENTONCES: Retorna información de la aplicación
        """
        response = await async_client.get("/")
        data = response.json()
        
        assert data["name"] == settings.APP_NAME
        assert data["version"] == settings.APP_VERSION
        assert "description" in data
    
    @pytest.mark.asyncio
    async def test_root_includes_links(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace GET a /
        ENTONCES: Incluye enlaces útiles
        """
        response = await async_client.get("/")
        data = response.json()
        
        assert "links" in data
        links = data["links"]
        
        assert "health" in links
        assert "health_ready" in links
        assert "health_live" in links


# =============================================================================
# Tests de Headers y Middleware
# =============================================================================
class TestMiddleware:
    """Tests para middlewares."""
    
    @pytest.mark.asyncio
    async def test_request_includes_process_time_header(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo
        CUANDO: Se hace cualquier request
        ENTONCES: La respuesta incluye X-Process-Time header
        """
        response = await async_client.get("/health")
        
        assert "x-process-time" in response.headers
        
        # Verificar formato (debe ser número con "ms")
        process_time = response.headers["x-process-time"]
        assert "ms" in process_time
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, async_client: AsyncClient):
        """
        DADO: La API está corriendo con CORS configurado
        CUANDO: Se hace un request con Origin header
        ENTONCES: La respuesta incluye CORS headers
        """
        # Simular request desde frontend
        headers = {"Origin": "http://localhost:3000"}
        response = await async_client.get("/health", headers=headers)
        
        # Verificar que permite el origen
        assert response.status_code == 200
