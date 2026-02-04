# =============================================================================
# NESTSECURE - Tests de Health Services Endpoint
# =============================================================================
"""
Tests para el endpoint /health/services que muestra
estado de circuit breakers.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.circuit_breaker import reset_all, get_circuit_breaker


# =============================================================================
# FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def async_client():
    """Cliente HTTP asíncrono para tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Resetear circuit breakers antes de cada test."""
    reset_all()
    yield
    reset_all()


# =============================================================================
# TESTS
# =============================================================================

class TestHealthServicesEndpoint:
    """Tests para /health/services."""
    
    @pytest.mark.asyncio
    async def test_health_services_returns_200(self, async_client):
        """Endpoint retorna 200."""
        response = await async_client.get("/health/services")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_services_structure(self, async_client):
        """Respuesta tiene estructura correcta."""
        response = await async_client.get("/health/services")
        data = response.json()
        
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data
        assert "service_count" in data
    
    @pytest.mark.asyncio
    async def test_health_services_includes_all_breakers(self, async_client):
        """Incluye todos los circuit breakers."""
        response = await async_client.get("/health/services")
        data = response.json()
        
        services = data["services"]
        
        # Debe incluir los servicios principales
        assert "gvm" in services
        assert "nvd" in services
        assert "nmap" in services
        assert "nuclei" in services
    
    @pytest.mark.asyncio
    async def test_health_services_healthy_by_default(self, async_client):
        """Estado es healthy por defecto."""
        response = await async_client.get("/health/services")
        data = response.json()
        
        assert data["status"] == "healthy"
        
        for service_name, service_data in data["services"].items():
            assert service_data["status"] == "healthy"
            assert service_data["circuit_state"] == "closed"
    
    @pytest.mark.asyncio
    async def test_health_services_service_details(self, async_client):
        """Cada servicio tiene detalles completos."""
        response = await async_client.get("/health/services")
        data = response.json()
        
        for service_name, service_data in data["services"].items():
            assert "status" in service_data
            assert "circuit_state" in service_data
            assert "failure_count" in service_data
            assert "total_calls" in service_data
            assert "config" in service_data
    
    @pytest.mark.asyncio
    async def test_health_services_after_failure(self, async_client):
        """Muestra fallos después de errores."""
        # Causar un fallo en GVM circuit breaker
        gvm = get_circuit_breaker("GVM")
        if gvm:
            try:
                gvm.call(lambda: 1/0)
            except:
                pass
        
        response = await async_client.get("/health/services")
        data = response.json()
        
        gvm_data = data["services"].get("gvm", {})
        assert gvm_data.get("failure_count", 0) >= 1
    
    @pytest.mark.asyncio
    async def test_health_services_degraded_when_open(self, async_client):
        """Estado es degraded cuando un circuit está abierto."""
        # Abrir circuit de NVD (threshold bajo = 3)
        nvd = get_circuit_breaker("NVD")
        if nvd:
            for _ in range(5):  # Más que el threshold
                try:
                    nvd.call(lambda: 1/0)
                except:
                    pass
        
        response = await async_client.get("/health/services")
        data = response.json()
        
        # Estado global debe ser degraded
        if nvd and nvd.state.value == "open":
            assert data["status"] == "degraded"
            assert data["services"]["nvd"]["status"] == "unavailable"
