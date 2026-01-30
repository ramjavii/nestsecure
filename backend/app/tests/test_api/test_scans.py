# =============================================================================
# NESTSECURE - Tests de API de Scans
# =============================================================================
"""
Tests para los endpoints de scans.

Cubre:
- CRUD operations
- Cancel scan
- Progress tracking
- Statistics
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import Scan, ScanStatus, ScanType


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
async def test_scan(db: AsyncSession, test_organization, test_user) -> Scan:
    """Crea un scan de prueba completado."""
    scan = Scan(
        organization_id=test_organization.id,
        created_by_id=test_user.id,
        name="Test Vulnerability Scan",
        description="Test scan for unit tests",
        scan_type=ScanType.VULNERABILITY.value,
        targets=["192.168.1.0/24"],
        status=ScanStatus.COMPLETED.value,
        progress=100,
        total_hosts_scanned=10,
        total_hosts_up=5,
        vuln_critical=2,
        vuln_high=5,
        vuln_medium=10,
        vuln_low=15,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


@pytest.fixture
async def running_scan(db: AsyncSession, test_organization, test_user) -> Scan:
    """Crea un scan en ejecución."""
    scan = Scan(
        organization_id=test_organization.id,
        created_by_id=test_user.id,
        name="Running Scan",
        scan_type=ScanType.PORT_SCAN.value,
        targets=["10.0.0.0/24"],
        status=ScanStatus.RUNNING.value,
        progress=45,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


# =============================================================================
# Test: List Scans
# =============================================================================
class TestScanList:
    """Tests para listado de scans."""
    
    async def test_list_scans_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """Lista vacía cuando no hay scans."""
        response = await api_client.get(
            "/api/v1/scans",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
    
    async def test_list_scans_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_scan: Scan,
    ):
        """Lista scans existentes."""
        response = await api_client.get(
            "/api/v1/scans",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        
        scan = data["items"][0]
        assert "id" in scan
        assert "name" in scan
        assert "status" in scan
        assert "progress" in scan
    
    async def test_list_scans_filter_status(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_scan: Scan,
    ):
        """Filtra por estado."""
        response = await api_client.get(
            "/api/v1/scans?status=completed",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for scan in data["items"]:
            assert scan["status"] == "completed"
    
    async def test_list_scans_filter_type(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_scan: Scan,
    ):
        """Filtra por tipo."""
        response = await api_client.get(
            "/api/v1/scans?scan_type=vulnerability",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for scan in data["items"]:
            assert scan["scan_type"] == "vulnerability"
    
    async def test_list_scans_unauthorized(
        self,
        api_client: AsyncClient,
    ):
        """Requiere autenticación."""
        response = await api_client.get("/api/v1/scans")
        assert response.status_code == 401


# =============================================================================
# Test: Get Scan
# =============================================================================
class TestScanGet:
    """Tests para obtener scan específico."""
    
    async def test_get_scan_success(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_scan: Scan,
    ):
        """Obtiene scan por ID."""
        response = await api_client.get(
            f"/api/v1/scans/{test_scan.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_scan.id
        assert data["name"] == test_scan.name
        assert data["status"] == "completed"
        assert "logs" in data  # ScanReadWithLogs includes logs
    
    async def test_get_scan_not_found(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """404 para ID inexistente."""
        response = await api_client.get(
            "/api/v1/scans/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404


# =============================================================================
# Test: Create Scan
# =============================================================================
class TestScanCreate:
    """Tests para crear scans."""
    
    async def test_create_scan_success(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
    ):
        """Crea scan correctamente."""
        scan_data = {
            "name": "New Security Scan",
            "scan_type": "port_scan",
            "targets": ["192.168.1.1", "192.168.1.2"],
            "port_range": "1-1000",
        }
        
        response = await api_client.post(
            "/api/v1/scans",
            headers=auth_headers_operator,
            json=scan_data,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == scan_data["name"]
        assert data["status"] == "pending"
        assert data["progress"] == 0
    
    async def test_create_scan_with_cidr(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
    ):
        """Crea scan con rango CIDR."""
        scan_data = {
            "name": "Network Range Scan",
            "scan_type": "discovery",
            "targets": ["10.0.0.0/24"],
        }
        
        response = await api_client.post(
            "/api/v1/scans",
            headers=auth_headers_operator,
            json=scan_data,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "10.0.0.0/24" in data["targets"]
    
    async def test_create_scan_conflict_when_running(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
        running_scan: Scan,
    ):
        """No permite crear si hay scan en curso."""
        scan_data = {
            "name": "Another Scan",
            "scan_type": "full",
            "targets": ["192.168.2.0/24"],
        }
        
        response = await api_client.post(
            "/api/v1/scans",
            headers=auth_headers_operator,
            json=scan_data,
        )
        
        assert response.status_code == 409
    
    async def test_create_scan_viewer_forbidden(
        self,
        api_client: AsyncClient,
        auth_headers: dict,  # viewer role
    ):
        """Viewer no puede crear scans."""
        scan_data = {
            "name": "Test Scan",
            "scan_type": "port_scan",
            "targets": ["192.168.1.1"],
        }
        
        response = await api_client.post(
            "/api/v1/scans",
            headers=auth_headers,
            json=scan_data,
        )
        
        assert response.status_code == 403


# =============================================================================
# Test: Cancel Scan
# =============================================================================
class TestScanCancel:
    """Tests para cancelar scans."""
    
    async def test_cancel_running_scan(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
        running_scan: Scan,
    ):
        """Cancela scan en ejecución."""
        response = await api_client.patch(
            f"/api/v1/scans/{running_scan.id}/cancel",
            headers=auth_headers_operator,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    async def test_cancel_completed_scan_fails(
        self,
        api_client: AsyncClient,
        auth_headers_operator: dict,
        test_scan: Scan,  # completed scan
    ):
        """No puede cancelar scan completado."""
        response = await api_client.patch(
            f"/api/v1/scans/{test_scan.id}/cancel",
            headers=auth_headers_operator,
        )
        
        assert response.status_code == 400


# =============================================================================
# Test: Scan Progress
# =============================================================================
class TestScanProgress:
    """Tests para progreso de scans."""
    
    async def test_get_progress(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        running_scan: Scan,
    ):
        """Obtiene progreso de scan."""
        response = await api_client.get(
            f"/api/v1/scans/{running_scan.id}/progress",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "scan_id" in data
        assert "status" in data
        assert "progress" in data
        assert data["progress"] == running_scan.progress


# =============================================================================
# Test: Scan Statistics
# =============================================================================
class TestScanStats:
    """Tests para estadísticas de scans."""
    
    async def test_get_stats_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
    ):
        """Estadísticas vacías."""
        response = await api_client.get(
            "/api/v1/scans/stats/summary",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_type" in data
        assert "by_status" in data
    
    async def test_get_stats_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_scan: Scan,
    ):
        """Estadísticas con datos."""
        response = await api_client.get(
            "/api/v1/scans/stats/summary",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["completed"] >= 1


# =============================================================================
# Test: Delete Scan
# =============================================================================
class TestScanDelete:
    """Tests para eliminar scans."""
    
    async def test_delete_scan_admin(
        self,
        api_client: AsyncClient,
        auth_headers_admin: dict,
        test_scan: Scan,
    ):
        """Admin puede eliminar scan."""
        response = await api_client.delete(
            f"/api/v1/scans/{test_scan.id}",
            headers=auth_headers_admin,
        )
        
        assert response.status_code == 200
    
    async def test_delete_running_scan_fails(
        self,
        api_client: AsyncClient,
        auth_headers_admin: dict,
        running_scan: Scan,
    ):
        """No puede eliminar scan en ejecución."""
        response = await api_client.delete(
            f"/api/v1/scans/{running_scan.id}",
            headers=auth_headers_admin,
        )
        
        assert response.status_code == 400


# =============================================================================
# Test: Multi-tenancy
# =============================================================================
class TestScanMultiTenancy:
    """Tests de aislamiento entre organizaciones."""
    
    async def test_list_only_own_organization(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        test_scan: Scan,
    ):
        """Solo ve scans de su organización."""
        response = await api_client.get(
            "/api/v1/scans",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        org_id = test_scan.organization_id
        for scan in data["items"]:
            assert scan["organization_id"] == org_id
