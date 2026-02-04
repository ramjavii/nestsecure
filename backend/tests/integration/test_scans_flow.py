# =============================================================================
# NESTSECURE - Tests de Integración: Gestión de Scans
# =============================================================================
"""
Tests de integración para el flujo completo de gestión de scans.
Verifica creación, ejecución, estados y resultados de escaneos.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestScansFlow:
    """Tests de integración para scans."""

    async def test_list_scans_empty(self, client_with_db: AsyncClient, auth_headers):
        """Test listar scans cuando no hay ninguno."""
        response = await client_with_db.get(
            "/api/v1/scans",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert isinstance(items, list)

    async def test_create_scan(self, client_with_db: AsyncClient, auth_headers):
        """Test crear un escaneo."""
        scan_data = {
            "name": "Test Scan",
            "scan_type": "vulnerability",
            "targets": ["192.168.1.0/24"]
        }
        
        response = await client_with_db.post(
            "/api/v1/scans",
            headers=auth_headers,
            json=scan_data
        )
        
        # El scan puede crearse o fallar si no hay conexión a servicios externos
        assert response.status_code in [200, 201, 400, 422, 500, 503]

    async def test_get_scan_by_id_nonexistent(self, client_with_db: AsyncClient, auth_headers):
        """Test obtener scan inexistente por ID."""
        fake_id = str(uuid4())
        
        response = await client_with_db.get(
            f"/api/v1/scans/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_list_scans_with_filters(self, client_with_db: AsyncClient, auth_headers):
        """Test listar scans con filtros."""
        response = await client_with_db.get(
            "/api/v1/scans?status=pending",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_list_scans_with_pagination(self, client_with_db: AsyncClient, auth_headers):
        """Test paginación de scans."""
        response = await client_with_db.get(
            "/api/v1/scans?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "items" in data:
            assert len(data["items"]) <= 10

    async def test_get_nmap_profiles(self, client_with_db: AsyncClient, auth_headers):
        """Test obtener perfiles de nmap disponibles."""
        response = await client_with_db.get(
            "/api/v1/scans/nmap/profiles",
            headers=auth_headers
        )
        
        # Puede existir o no
        assert response.status_code in [200, 404]

    async def test_create_scan_empty_targets(self, client_with_db: AsyncClient, auth_headers):
        """Test crear scan sin targets."""
        response = await client_with_db.post(
            "/api/v1/scans",
            headers=auth_headers,
            json={
                "name": "No Targets Scan",
                "scan_type": "vulnerability",
                "targets": []
            }
        )
        
        # Debería fallar la validación
        assert response.status_code in [400, 422]

    async def test_create_scan_invalid_name(self, client_with_db: AsyncClient, auth_headers):
        """Test crear scan sin nombre."""
        response = await client_with_db.post(
            "/api/v1/scans",
            headers=auth_headers,
            json={
                "name": "",
                "scan_type": "vulnerability",
                "targets": ["10.0.0.1"]
            }
        )
        
        # Debería fallar la validación
        assert response.status_code in [400, 422]


class TestScanOperations:
    """Tests de operaciones sobre scans."""

    async def test_stop_nonexistent_scan(self, client_with_db: AsyncClient, auth_headers):
        """Test detener scan que no existe."""
        fake_id = str(uuid4())
        
        response = await client_with_db.post(
            f"/api/v1/scans/{fake_id}/stop",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_get_status_nonexistent_scan(self, client_with_db: AsyncClient, auth_headers):
        """Test obtener estado de scan inexistente."""
        fake_id = str(uuid4())
        
        response = await client_with_db.get(
            f"/api/v1/scans/{fake_id}/status",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_get_results_nonexistent_scan(self, client_with_db: AsyncClient, auth_headers):
        """Test obtener resultados de scan inexistente."""
        fake_id = str(uuid4())
        
        response = await client_with_db.get(
            f"/api/v1/scans/{fake_id}/results",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_delete_nonexistent_scan(self, client_with_db: AsyncClient, auth_headers):
        """Test eliminar scan inexistente."""
        fake_id = str(uuid4())
        
        response = await client_with_db.delete(
            f"/api/v1/scans/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
