# =============================================================================
# NESTSECURE - Tests de API de Vulnerabilidades
# =============================================================================
"""
Tests para los endpoints de vulnerabilidades.

Cubre:
- CRUD operations
- Filtros y búsqueda
- Estadísticas
- Bulk updates
- Multi-tenancy
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.scan import Scan, ScanStatus
from app.models.vulnerability import Vulnerability, VulnerabilityStatus


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
async def test_scan(db: AsyncSession, test_organization, test_user) -> Scan:
    """Crea un scan de prueba."""
    scan = Scan(
        organization_id=test_organization.id,
        created_by_id=test_user.id,
        name="Test Scan",
        scan_type="vulnerability",
        targets=["192.168.1.0/24"],
        status=ScanStatus.COMPLETED.value,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


@pytest.fixture
async def test_asset(db: AsyncSession, test_organization) -> Asset:
    """Crea un asset de prueba."""
    asset = Asset(
        organization_id=test_organization.id,
        ip_address="192.168.1.100",
        hostname="test-server",
        asset_type="server",
        criticality="high",
        status="active",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@pytest.fixture
async def test_vulnerability(
    db: AsyncSession, 
    test_organization, 
    test_asset, 
    test_scan
) -> Vulnerability:
    """Crea una vulnerabilidad de prueba."""
    vuln = Vulnerability(
        organization_id=test_organization.id,
        asset_id=test_asset.id,
        scan_id=test_scan.id,
        name="SQL Injection in Login Form",
        description="Critical SQL injection vulnerability allows authentication bypass",
        severity="critical",
        cvss_score=9.8,
        status=VulnerabilityStatus.OPEN.value,
        exploit_available=True,
    )
    db.add(vuln)
    await db.commit()
    await db.refresh(vuln)
    return vuln


# =============================================================================
# Test: List Vulnerabilities
# =============================================================================
class TestVulnerabilityList:
    """Tests para listado de vulnerabilidades."""
    
    async def test_list_vulnerabilities_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """Lista vacía cuando no hay vulnerabilidades."""
        response = await api_client.get(
            "/api/v1/vulnerabilities",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
    
    async def test_list_vulnerabilities_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_vulnerability: Vulnerability,
    ):
        """Lista vulnerabilidades existentes."""
        response = await api_client.get(
            "/api/v1/vulnerabilities",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        
        # Verificar estructura
        vuln = data["items"][0]
        assert "id" in vuln
        assert "name" in vuln
        assert "severity" in vuln
        assert "status" in vuln
    
    async def test_list_vulnerabilities_filter_severity(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_vulnerability: Vulnerability,
    ):
        """Filtra por severidad."""
        response = await api_client.get(
            "/api/v1/vulnerabilities?severity=critical",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for vuln in data["items"]:
            assert vuln["severity"] == "critical"
    
    async def test_list_vulnerabilities_filter_status(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_vulnerability: Vulnerability,
    ):
        """Filtra por estado."""
        response = await api_client.get(
            "/api/v1/vulnerabilities?status=open",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for vuln in data["items"]:
            assert vuln["status"] == "open"
    
    async def test_list_vulnerabilities_search(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_vulnerability: Vulnerability,
    ):
        """Búsqueda por texto."""
        response = await api_client.get(
            "/api/v1/vulnerabilities?search=SQL",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    async def test_list_vulnerabilities_unauthorized(
        self,
        api_client: AsyncClient,
    ):
        """Requiere autenticación."""
        response = await api_client.get("/api/v1/vulnerabilities")
        assert response.status_code == 401


# =============================================================================
# Test: Get Vulnerability
# =============================================================================
class TestVulnerabilityGet:
    """Tests para obtener vulnerabilidad específica."""
    
    async def test_get_vulnerability_success(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_vulnerability: Vulnerability,
    ):
        """Obtiene vulnerabilidad por ID."""
        response = await api_client.get(
            f"/api/v1/vulnerabilities/{test_vulnerability.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_vulnerability.id
        assert data["name"] == test_vulnerability.name
        assert data["severity"] == "critical"
    
    async def test_get_vulnerability_not_found(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """404 para ID inexistente."""
        response = await api_client.get(
            "/api/v1/vulnerabilities/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404


# =============================================================================
# Test: Create Vulnerability
# =============================================================================
class TestVulnerabilityCreate:
    """Tests para crear vulnerabilidades."""
    
    async def test_create_vulnerability_success(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
        test_asset: Asset,
        test_scan: Scan,
    ):
        """Crea vulnerabilidad correctamente."""
        vuln_data = {
            "name": "XSS in Comment Field",
            "description": "Stored XSS allows script injection in comments",
            "severity": "high",
            "asset_id": test_asset.id,
            "scan_id": test_scan.id,
            "cvss_score": 7.5,
        }
        
        response = await api_client.post(
            "/api/v1/vulnerabilities",
            headers=auth_headers_operator,
            json=vuln_data,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == vuln_data["name"]
        assert data["severity"] == "high"
        assert data["status"] == "open"
    
    async def test_create_vulnerability_viewer_forbidden(
        self,
        api_client: AsyncClient,
        auth_headers: dict,  # viewer role
        test_asset: Asset,
        test_scan: Scan,
    ):
        """Viewer no puede crear vulnerabilidades."""
        vuln_data = {
            "name": "Test Vuln",
            "description": "Test",
            "severity": "low",
            "asset_id": test_asset.id,
            "scan_id": test_scan.id,
        }
        
        response = await api_client.post(
            "/api/v1/vulnerabilities",
            headers=auth_headers,
            json=vuln_data,
        )
        
        assert response.status_code == 403


# =============================================================================
# Test: Update Vulnerability
# =============================================================================
class TestVulnerabilityUpdate:
    """Tests para actualizar vulnerabilidades."""
    
    async def test_update_vulnerability_status(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
        test_vulnerability: Vulnerability,
    ):
        """Actualiza estado de vulnerabilidad."""
        response = await api_client.patch(
            f"/api/v1/vulnerabilities/{test_vulnerability.id}",
            headers=auth_headers_operator,
            json={"status": "in_progress"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
    
    async def test_update_vulnerability_mark_fixed(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
        test_vulnerability: Vulnerability,
    ):
        """Marca vulnerabilidad como corregida."""
        response = await api_client.patch(
            f"/api/v1/vulnerabilities/{test_vulnerability.id}",
            headers=auth_headers_operator,
            json={"status": "fixed"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fixed"
        assert data["resolved_at"] is not None


# =============================================================================
# Test: Delete Vulnerability
# =============================================================================
class TestVulnerabilityDelete:
    """Tests para eliminar vulnerabilidades."""
    
    async def test_delete_vulnerability_admin(
        self,
        api_client: AsyncClient,
        auth_headers_admin: dict,
        test_vulnerability: Vulnerability,
    ):
        """Admin puede eliminar vulnerabilidad."""
        response = await api_client.delete(
            f"/api/v1/vulnerabilities/{test_vulnerability.id}",
            headers=auth_headers_admin,
        )
        
        assert response.status_code == 200
    
    async def test_delete_vulnerability_operator_forbidden(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
        test_vulnerability: Vulnerability,
    ):
        """Operator no puede eliminar."""
        response = await api_client.delete(
            f"/api/v1/vulnerabilities/{test_vulnerability.id}",
            headers=auth_headers_operator,
        )
        
        assert response.status_code == 403


# =============================================================================
# Test: Vulnerability Statistics
# =============================================================================
class TestVulnerabilityStats:
    """Tests para estadísticas de vulnerabilidades."""
    
    async def test_get_stats_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """Estadísticas vacías."""
        response = await api_client.get(
            "/api/v1/vulnerabilities/stats/summary",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_severity" in data
        assert "by_status" in data
    
    async def test_get_stats_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_vulnerability: Vulnerability,
    ):
        """Estadísticas con datos."""
        response = await api_client.get(
            "/api/v1/vulnerabilities/stats/summary",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["by_severity"]["critical"] >= 1


# =============================================================================
# Test: Multi-tenancy
# =============================================================================
class TestVulnerabilityMultiTenancy:
    """Tests de aislamiento entre organizaciones."""
    
    async def test_list_only_own_organization(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db: AsyncSession,
        test_vulnerability: Vulnerability,
    ):
        """Solo ve vulnerabilidades de su organización."""
        # La vulnerabilidad de test pertenece a la organización del usuario
        response = await api_client.get(
            "/api/v1/vulnerabilities",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Todas las vulnerabilidades deben ser de la misma organización
        org_id = test_vulnerability.organization_id
        for vuln in data["items"]:
            assert vuln["organization_id"] == org_id
