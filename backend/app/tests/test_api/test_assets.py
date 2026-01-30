"""
Tests para el API de Assets.

Pruebas completas de CRUD y funcionalidades avanzadas
para la gestión de activos de red.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.models.asset import Asset, AssetStatus, AssetCriticality, AssetType


# =============================================================================
# Tests de listado de assets
# =============================================================================
class TestAssetList:
    """Tests para GET /api/v1/assets"""
    
    @pytest.mark.asyncio
    async def test_list_assets_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Listar assets cuando no hay ninguno."""
        response = await api_client.get(
            "/api/v1/assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
    
    @pytest.mark.asyncio
    async def test_list_assets_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Listar assets con datos existentes."""
        # Crear assets de prueba
        for i in range(3):
            asset = Asset(
                ip_address=f"192.168.1.{10 + i}",
                hostname=f"server-{i}",
                organization_id=test_organization.id,
                status=AssetStatus.ACTIVE,
                criticality=AssetCriticality.MEDIUM
            )
            db_session.add(asset)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
    
    @pytest.mark.asyncio
    async def test_list_assets_with_status_filter(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Filtrar assets por estado."""
        # Crear assets con diferentes estados
        asset1 = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id,
            status=AssetStatus.ACTIVE
        )
        asset2 = Asset(
            ip_address="192.168.1.11",
            organization_id=test_organization.id,
            status=AssetStatus.INACTIVE
        )
        db_session.add_all([asset1, asset2])
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/assets?status=active",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_list_assets_with_criticality_filter(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Filtrar assets por criticidad."""
        asset1 = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id,
            criticality=AssetCriticality.CRITICAL
        )
        asset2 = Asset(
            ip_address="192.168.1.11",
            organization_id=test_organization.id,
            criticality=AssetCriticality.LOW
        )
        db_session.add_all([asset1, asset2])
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/assets?criticality=critical",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["criticality"] == "critical"
    
    @pytest.mark.asyncio
    async def test_list_assets_with_search(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Buscar assets por hostname o IP."""
        asset1 = Asset(
            ip_address="192.168.1.10",
            hostname="webserver-01",
            organization_id=test_organization.id
        )
        asset2 = Asset(
            ip_address="192.168.1.11",
            hostname="database-01",
            organization_id=test_organization.id
        )
        db_session.add_all([asset1, asset2])
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/assets?search=webserver",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "webserver" in data["items"][0]["hostname"]
    
    @pytest.mark.asyncio
    async def test_list_assets_pagination(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Verificar paginación de assets."""
        # Crear 15 assets
        for i in range(15):
            asset = Asset(
                ip_address=f"192.168.1.{10 + i}",
                organization_id=test_organization.id
            )
            db_session.add(asset)
        await db_session.commit()
        
        # Primera página
        response = await api_client.get(
            "/api/v1/assets?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["pages"] == 2
        
        # Segunda página
        response = await api_client.get(
            "/api/v1/assets?page=2&page_size=10",
            headers=auth_headers
        )
        
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2
    
    @pytest.mark.asyncio
    async def test_list_assets_unauthorized(self, api_client: AsyncClient):
        """Listar assets sin autenticación."""
        response = await api_client.get("/api/v1/assets")
        assert response.status_code == 401


# =============================================================================
# Tests de creación de assets
# =============================================================================
class TestAssetCreate:
    """Tests para POST /api/v1/assets"""
    
    @pytest.mark.asyncio
    async def test_create_asset_success(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Crear asset exitosamente."""
        asset_data = {
            "ip_address": "192.168.1.100",
            "hostname": "test-server",
            "mac_address": "00:11:22:33:44:55",
            "asset_type": "server",
            "criticality": "high",
            "status": "active"
        }
        
        response = await api_client.post(
            "/api/v1/assets",
            json=asset_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["ip_address"] == "192.168.1.100"
        assert data["hostname"] == "test-server"
        assert data["criticality"] == "high"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_asset_minimal(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Crear asset con datos mínimos."""
        asset_data = {
            "ip_address": "10.0.0.1"
        }
        
        response = await api_client.post(
            "/api/v1/assets",
            json=asset_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["ip_address"] == "10.0.0.1"
    
    @pytest.mark.asyncio
    async def test_create_asset_duplicate_ip(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict,
        db_session,
        test_organization
    ):
        """No permitir IPs duplicadas en la misma organización."""
        # Crear asset existente
        existing = Asset(
            ip_address="192.168.1.100",
            organization_id=test_organization.id
        )
        db_session.add(existing)
        await db_session.commit()
        
        # Intentar crear otro con la misma IP
        asset_data = {"ip_address": "192.168.1.100"}
        
        response = await api_client.post(
            "/api/v1/assets",
            json=asset_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 409
        detail = response.json()["detail"].lower()
        assert "already exists" in detail or "existe" in detail or "ya existe" in detail
    
    @pytest.mark.asyncio
    async def test_create_asset_viewer_forbidden(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Usuario viewer no puede crear assets."""
        asset_data = {"ip_address": "192.168.1.100"}
        
        response = await api_client.post(
            "/api/v1/assets",
            json=asset_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403


# =============================================================================
# Tests de obtención de asset individual
# =============================================================================
class TestAssetGet:
    """Tests para GET /api/v1/assets/{asset_id}"""
    
    @pytest.mark.asyncio
    async def test_get_asset_success(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Obtener asset por ID."""
        asset = Asset(
            ip_address="192.168.1.50",
            hostname="test-host",
            organization_id=test_organization.id,
            status=AssetStatus.ACTIVE
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        response = await api_client.get(
            f"/api/v1/assets/{asset.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(asset.id)
        assert data["ip_address"] == "192.168.1.50"
    
    @pytest.mark.asyncio
    async def test_get_asset_not_found(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Asset no encontrado."""
        fake_id = str(uuid4()).replace("-", "")
        
        response = await api_client.get(
            f"/api/v1/assets/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_asset_other_organization(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session
    ):
        """No acceder a assets de otra organización."""
        from app.models.organization import Organization
        
        # Crear otra organización con un asset
        other_org = Organization(
            name="Other Org",
            slug="other-org"
        )
        db_session.add(other_org)
        await db_session.flush()
        
        asset = Asset(
            ip_address="10.0.0.1",
            organization_id=other_org.id
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        response = await api_client.get(
            f"/api/v1/assets/{asset.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


# =============================================================================
# Tests de actualización de assets
# =============================================================================
class TestAssetUpdate:
    """Tests para PATCH /api/v1/assets/{asset_id}"""
    
    @pytest.mark.asyncio
    async def test_update_asset_success(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict,
        db_session,
        test_organization
    ):
        """Actualizar asset exitosamente."""
        asset = Asset(
            ip_address="192.168.1.50",
            hostname="old-hostname",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        update_data = {
            "hostname": "new-hostname",
            "criticality": "critical",
            "description": "Updated notes"
        }
        
        response = await api_client.patch(
            f"/api/v1/assets/{asset.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["hostname"] == "new-hostname"
        assert data["criticality"] == "critical"
    
    @pytest.mark.asyncio
    async def test_update_asset_partial(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict,
        db_session,
        test_organization
    ):
        """Actualización parcial de asset."""
        asset = Asset(
            ip_address="192.168.1.50",
            hostname="original",
            criticality=AssetCriticality.LOW,
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        # Solo actualizar criticality
        update_data = {"criticality": "high"}
        
        response = await api_client.patch(
            f"/api/v1/assets/{asset.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["hostname"] == "original"  # Sin cambios
        assert data["criticality"] == "high"  # Actualizado
    
    @pytest.mark.asyncio
    async def test_update_asset_viewer_forbidden(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Viewer no puede actualizar assets."""
        asset = Asset(
            ip_address="192.168.1.50",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        response = await api_client.patch(
            f"/api/v1/assets/{asset.id}",
            json={"hostname": "new"},
            headers=auth_headers
        )
        
        assert response.status_code == 403


# =============================================================================
# Tests de eliminación de assets
# =============================================================================
class TestAssetDelete:
    """Tests para DELETE /api/v1/assets/{asset_id}"""
    
    @pytest.mark.asyncio
    async def test_delete_asset_success(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict,
        db_session,
        test_organization
    ):
        """Eliminar asset exitosamente."""
        asset = Asset(
            ip_address="192.168.1.50",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        response = await api_client.delete(
            f"/api/v1/assets/{asset.id}",
            headers=admin_auth_headers
        )
        
        # Puede retornar 200 o 204 dependiendo de la implementación
        assert response.status_code in [200, 204]
        
        # Verificar que ya no existe
        response = await api_client.get(
            f"/api/v1/assets/{asset.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_asset_not_found(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Eliminar asset inexistente."""
        fake_id = str(uuid4()).replace("-", "")
        
        response = await api_client.delete(
            f"/api/v1/assets/{fake_id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_asset_viewer_forbidden(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Viewer no puede eliminar assets."""
        asset = Asset(
            ip_address="192.168.1.50",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        response = await api_client.delete(
            f"/api/v1/assets/{asset.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 403


# =============================================================================
# Tests de servicios de un asset
# =============================================================================
class TestAssetServices:
    """Tests para GET /api/v1/assets/{asset_id}/services"""
    
    @pytest.mark.asyncio
    async def test_get_asset_services_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Servicios de un asset sin servicios."""
        asset = Asset(
            ip_address="192.168.1.50",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        response = await api_client.get(
            f"/api/v1/assets/{asset.id}/services",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificar que es una lista o paginación
        if isinstance(data, list):
            assert data == []
        else:
            assert data["items"] == []
            assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_asset_services_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Servicios de un asset con servicios detectados."""
        from app.models.service import Service
        
        asset = Asset(
            ip_address="192.168.1.50",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        # Agregar servicios - usando service_name en lugar de name
        services = [
            Service(
                asset_id=asset.id,
                port=22,
                protocol="tcp",
                service_name="ssh",
                state="open"
            ),
            Service(
                asset_id=asset.id,
                port=80,
                protocol="tcp",
                service_name="http",
                state="open"
            ),
        ]
        for svc in services:
            db_session.add(svc)
        await db_session.commit()
        await db_session.refresh(asset)
        
        response = await api_client.get(
            f"/api/v1/assets/{asset.id}/services",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificar que es una lista o paginación
        if isinstance(data, list):
            assert len(data) == 2
            ports = [s["port"] for s in data]
        else:
            assert data["total"] == 2
            ports = [s["port"] for s in data["items"]]
        assert 22 in ports
        assert 80 in ports


# =============================================================================
# Tests de multi-tenancy
# =============================================================================
class TestAssetMultiTenancy:
    """Tests de aislamiento por organización."""
    
    @pytest.mark.asyncio
    async def test_list_only_own_organization(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Solo listar assets de mi organización."""
        from app.models.organization import Organization
        
        # Crear otra organización con assets
        other_org = Organization(
            name="Other Org",
            slug="other-org-mt"
        )
        db_session.add(other_org)
        await db_session.flush()
        
        # Asset de otra organización
        other_asset = Asset(
            ip_address="10.0.0.1",
            organization_id=other_org.id
        )
        db_session.add(other_asset)
        
        # Asset de mi organización
        my_asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(my_asset)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Solo debe mostrar el asset de mi organización
        assert data["total"] == 1
        assert data["items"][0]["ip_address"] == "192.168.1.10"
