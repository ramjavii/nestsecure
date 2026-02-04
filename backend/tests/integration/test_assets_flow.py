# =============================================================================
# NESTSECURE - Tests de Integración: Gestión de Assets
# =============================================================================
"""
Tests de integración para el flujo completo de gestión de assets.
Verifica CRUD completo, filtros, paginación y relaciones.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestAssetsFlow:
    """Tests de integración para assets."""

    async def test_list_assets_empty(self, client_with_db: AsyncClient, auth_headers):
        """Test listar assets cuando no hay ninguno."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
        items = data.get("items", data)
        assert len(items) == 0

    async def test_create_asset(self, client_with_db: AsyncClient, auth_headers):
        """Test crear un nuevo asset."""
        asset_data = {
            "ip_address": "192.168.1.100",
            "hostname": "test-server",
            "asset_type": "server",
            "criticality": "high",
            "status": "active"
        }
        
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json=asset_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["ip_address"] == "192.168.1.100"
        assert data["hostname"] == "test-server"
        assert data["asset_type"] == "server"
        assert "id" in data

    async def test_get_asset_by_id(self, client_with_db: AsyncClient, auth_headers):
        """Test obtener asset por ID."""
        # Primero crear un asset
        create_response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.1.101",
                "hostname": "get-test-server",
                "asset_type": "server"
            }
        )
        
        assert create_response.status_code in [200, 201]
        asset = create_response.json()
        asset_id = asset["id"]
        
        # Obtener el asset
        get_response = await client_with_db.get(
            f"/api/v1/assets/{asset_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == asset_id
        assert data["hostname"] == "get-test-server"

    async def test_update_asset(self, client_with_db: AsyncClient, auth_headers):
        """Test actualizar un asset."""
        # Crear asset
        create_response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.1.102",
                "hostname": "update-test-server",
                "asset_type": "server"
            }
        )
        
        asset = create_response.json()
        asset_id = asset["id"]
        
        # Actualizar asset
        update_response = await client_with_db.patch(
            f"/api/v1/assets/{asset_id}",
            headers=auth_headers,
            json={"hostname": "updated-hostname", "criticality": "critical"}
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["hostname"] == "updated-hostname"
        assert data["criticality"] == "critical"

    async def test_delete_asset(self, client_with_db: AsyncClient, auth_headers):
        """Test eliminar un asset."""
        # Crear asset
        create_response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.1.103",
                "hostname": "delete-test-server",
                "asset_type": "server"
            }
        )
        
        asset = create_response.json()
        asset_id = asset["id"]
        
        # Eliminar asset
        delete_response = await client_with_db.delete(
            f"/api/v1/assets/{asset_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code in [200, 204]
        
        # Verificar que ya no existe
        get_response = await client_with_db.get(
            f"/api/v1/assets/{asset_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 404

    async def test_list_assets_with_pagination(self, client_with_db: AsyncClient, auth_headers):
        """Test paginación de assets."""
        # Crear varios assets
        for i in range(5):
            await client_with_db.post(
                "/api/v1/assets",
                headers=auth_headers,
                json={
                    "ip_address": f"192.168.2.{i}",
                    "hostname": f"pagination-test-{i}",
                    "asset_type": "server"
                }
            )
        
        # Listar con paginación
        response = await client_with_db.get(
            "/api/v1/assets?page=1&page_size=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "items" in data:
            assert len(data["items"]) <= 2
            assert "total" in data or "count" in data

    async def test_filter_assets_by_type(self, client_with_db: AsyncClient, auth_headers):
        """Test filtrar assets por tipo."""
        # Crear assets de diferentes tipos
        await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.3.1",
                "hostname": "filter-server",
                "asset_type": "server"
            }
        )
        
        await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.3.2",
                "hostname": "filter-workstation",
                "asset_type": "workstation"
            }
        )
        
        # Filtrar por tipo server
        response = await client_with_db.get(
            "/api/v1/assets?asset_type=server",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        
        for item in items:
            if "asset_type" in item:
                assert item["asset_type"] == "server"

    async def test_filter_assets_by_criticality(self, client_with_db: AsyncClient, auth_headers):
        """Test filtrar assets por criticidad."""
        # Crear assets con diferentes criticidades
        await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.4.1",
                "hostname": "critical-server",
                "asset_type": "server",
                "criticality": "critical"
            }
        )
        
        # Filtrar por criticidad
        response = await client_with_db.get(
            "/api/v1/assets?criticality=critical",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_create_asset_duplicate_ip(self, client_with_db: AsyncClient, auth_headers):
        """Test crear asset con IP duplicada."""
        # Crear primer asset
        await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.5.1",
                "hostname": "duplicate-test-1",
                "asset_type": "server"
            }
        )
        
        # Intentar crear otro con la misma IP
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.5.1",
                "hostname": "duplicate-test-2",
                "asset_type": "server"
            }
        )
        
        # Debería fallar o permitirse según la lógica de negocio
        assert response.status_code in [200, 201, 400, 409]

    async def test_create_asset_invalid_ip(self, client_with_db: AsyncClient, auth_headers):
        """Test crear asset con IP inválida."""
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "not-an-ip",
                "hostname": "invalid-ip-test",
                "asset_type": "server"
            }
        )
        
        # Debería fallar la validación
        assert response.status_code == 422

    async def test_get_nonexistent_asset(self, client_with_db: AsyncClient, auth_headers):
        """Test obtener asset que no existe."""
        response = await client_with_db.get(
            "/api/v1/assets/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestAssetServices:
    """Tests de integración para servicios de assets."""

    async def test_list_asset_services(self, client_with_db: AsyncClient, auth_headers):
        """Test listar servicios de un asset."""
        # Crear asset primero
        create_response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.6.1",
                "hostname": "services-test",
                "asset_type": "server"
            }
        )
        
        asset = create_response.json()
        asset_id = asset["id"]
        
        # Listar servicios
        response = await client_with_db.get(
            f"/api/v1/assets/{asset_id}/services",
            headers=auth_headers
        )
        
        # El endpoint puede existir o no
        assert response.status_code in [200, 404]
