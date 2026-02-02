# =============================================================================
# NESTSECURE - Tests para API de Scans
# =============================================================================
"""
Tests de integración para los endpoints de scans.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.models.scan import Scan, ScanStatus, ScanType


# =============================================================================
# Tests - Create Scan
# =============================================================================

class TestCreateScan:
    """Tests para POST /scans."""
    
    @pytest.mark.asyncio
    async def test_create_scan_success(self, client, auth_headers, test_db):
        """Test crear scan exitosamente."""
        # Mock de Celery task
        mock_task = MagicMock()
        mock_task.id = "celery-task-123"
        mock_task.delay = MagicMock(return_value=mock_task)
        
        with patch("app.api.v1.scans.openvas_full_scan", mock_task):
            response = await client.post(
                "/api/v1/scans",
                headers=auth_headers,
                json={
                    "name": "Test Scan",
                    "description": "Test description",
                    "scan_type": "vulnerability",
                    "targets": ["192.168.1.0/24"],
                }
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Scan"
        assert data["status"] == "queued"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_scan_invalid_targets(self, client, auth_headers):
        """Test crear scan sin targets."""
        response = await client.post(
            "/api/v1/scans",
            headers=auth_headers,
            json={
                "name": "Test Scan",
                "targets": [],
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_create_scan_unauthenticated(self, client):
        """Test crear scan sin autenticación."""
        response = await client.post(
            "/api/v1/scans",
            json={
                "name": "Test Scan",
                "targets": ["192.168.1.1"],
            }
        )
        
        assert response.status_code == 401


# =============================================================================
# Tests - List Scans
# =============================================================================

class TestListScans:
    """Tests para GET /scans."""
    
    @pytest.mark.asyncio
    async def test_list_scans_empty(self, client, auth_headers):
        """Test listar scans vacío."""
        response = await client.get(
            "/api/v1/scans",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    @pytest.mark.asyncio
    async def test_list_scans_pagination(self, client, auth_headers):
        """Test paginación de scans."""
        response = await client.get(
            "/api/v1/scans",
            headers=auth_headers,
            params={"page": 1, "page_size": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    @pytest.mark.asyncio
    async def test_list_scans_filter_status(self, client, auth_headers):
        """Test filtrar scans por estado."""
        response = await client.get(
            "/api/v1/scans",
            headers=auth_headers,
            params={"status": "completed"}
        )
        
        assert response.status_code == 200


# =============================================================================
# Tests - Get Scan Detail
# =============================================================================

class TestGetScan:
    """Tests para GET /scans/{id}."""
    
    @pytest.mark.asyncio
    async def test_get_scan_not_found(self, client, auth_headers):
        """Test obtener scan inexistente."""
        response = await client.get(
            "/api/v1/scans/nonexistent-id",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


# =============================================================================
# Tests - Get Scan Status
# =============================================================================

class TestGetScanStatus:
    """Tests para GET /scans/{id}/status."""
    
    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client, auth_headers):
        """Test estado de scan inexistente."""
        response = await client.get(
            "/api/v1/scans/nonexistent-id/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


# =============================================================================
# Tests - Stop Scan
# =============================================================================

class TestStopScan:
    """Tests para POST /scans/{id}/stop."""
    
    @pytest.mark.asyncio
    async def test_stop_scan_not_found(self, client, auth_headers):
        """Test detener scan inexistente."""
        response = await client.post(
            "/api/v1/scans/nonexistent-id/stop",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


# =============================================================================
# Tests - Delete Scan
# =============================================================================

class TestDeleteScan:
    """Tests para DELETE /scans/{id}."""
    
    @pytest.mark.asyncio
    async def test_delete_scan_not_found(self, client, auth_headers):
        """Test eliminar scan inexistente."""
        response = await client.delete(
            "/api/v1/scans/nonexistent-id",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
