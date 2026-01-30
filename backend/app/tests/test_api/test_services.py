"""
Tests para el API de Services.

Pruebas completas de CRUD para servicios detectados en assets.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.models.asset import Asset, AssetStatus
from app.models.service import Service


# =============================================================================
# Tests de listado de services
# =============================================================================
class TestServiceList:
    """Tests para GET /api/v1/services"""
    
    @pytest.mark.asyncio
    async def test_list_services_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Listar servicios cuando no hay ninguno."""
        response = await api_client.get(
            "/api/v1/services",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_services_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Listar servicios con datos existentes."""
        # Crear asset y servicios
        asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        services = [
            Service(asset_id=asset.id, port=22, protocol="tcp", service_name="ssh"),
            Service(asset_id=asset.id, port=80, protocol="tcp", service_name="http"),
            Service(asset_id=asset.id, port=443, protocol="tcp", service_name="https"),
        ]
        for svc in services:
            db_session.add(svc)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/services",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
    
    @pytest.mark.asyncio
    async def test_list_services_filter_by_port(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Filtrar servicios por puerto."""
        asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        services = [
            Service(asset_id=asset.id, port=22, protocol="tcp", service_name="ssh"),
            Service(asset_id=asset.id, port=80, protocol="tcp", service_name="http"),
        ]
        for svc in services:
            db_session.add(svc)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/services?port=22",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["port"] == 22
    
    @pytest.mark.asyncio
    async def test_list_services_filter_by_protocol(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Filtrar servicios por protocolo."""
        asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        services = [
            Service(asset_id=asset.id, port=53, protocol="tcp", service_name="dns"),
            Service(asset_id=asset.id, port=161, protocol="udp", service_name="snmp"),
        ]
        for svc in services:
            db_session.add(svc)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/services?protocol=udp",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["protocol"] == "udp"
    
    @pytest.mark.asyncio
    async def test_list_services_filter_by_state(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Filtrar servicios por estado."""
        asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        services = [
            Service(asset_id=asset.id, port=22, protocol="tcp", state="open"),
            Service(asset_id=asset.id, port=23, protocol="tcp", state="closed"),
        ]
        for svc in services:
            db_session.add(svc)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/services?state=open",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["state"] == "open"
    
    @pytest.mark.asyncio
    async def test_list_services_unauthorized(
        self,
        api_client: AsyncClient
    ):
        """Listar servicios sin autenticación."""
        response = await api_client.get("/api/v1/services")
        assert response.status_code == 401


# =============================================================================
# Tests de obtención de service individual
# =============================================================================
class TestServiceGet:
    """Tests para GET /api/v1/services/{service_id}"""
    
    @pytest.mark.asyncio
    async def test_get_service_success(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Obtener servicio por ID."""
        asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        service = Service(
            asset_id=asset.id,
            port=443,
            protocol="tcp",
            service_name="https"
        )
        db_session.add(service)
        await db_session.commit()
        await db_session.refresh(service)
        
        response = await api_client.get(
            f"/api/v1/services/{service.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(service.id)
        assert data["port"] == 443
    
    @pytest.mark.asyncio
    async def test_get_service_not_found(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Servicio no encontrado."""
        fake_id = str(uuid4()).replace("-", "")
        
        response = await api_client.get(
            f"/api/v1/services/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


# =============================================================================
# Tests de actualización de services
# =============================================================================
class TestServiceUpdate:
    """Tests para PATCH /api/v1/services/{service_id}"""
    
    @pytest.mark.asyncio
    async def test_update_service_success(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict,
        db_session,
        test_organization
    ):
        """Actualizar servicio exitosamente."""
        asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        service = Service(
            asset_id=asset.id,
            port=80,
            protocol="tcp",
            service_name="http",
            state="open"
        )
        db_session.add(service)
        await db_session.commit()
        await db_session.refresh(service)
        
        update_data = {
            "service_name": "nginx",
            "version": "1.20.0",
            "banner": "nginx/1.20.0"
        }
        
        response = await api_client.patch(
            f"/api/v1/services/{service.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "nginx"
        assert data["version"] == "1.20.0"
    
    @pytest.mark.asyncio
    async def test_update_service_state(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict,
        db_session,
        test_organization
    ):
        """Actualizar estado del servicio."""
        asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        service = Service(
            asset_id=asset.id,
            port=22,
            protocol="tcp",
            state="open"
        )
        db_session.add(service)
        await db_session.commit()
        await db_session.refresh(service)
        
        update_data = {"state": "closed"}
        
        response = await api_client.patch(
            f"/api/v1/services/{service.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["state"] == "closed"


# =============================================================================
# Tests de eliminación de services
# =============================================================================
class TestServiceDelete:
    """Tests para DELETE /api/v1/services/{service_id}"""
    
    @pytest.mark.asyncio
    async def test_delete_service_success(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict,
        db_session,
        test_organization
    ):
        """Eliminar servicio exitosamente."""
        asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(asset)
        await db_session.flush()
        
        service = Service(
            asset_id=asset.id,
            port=80,
            protocol="tcp"
        )
        db_session.add(service)
        await db_session.commit()
        await db_session.refresh(service)
        
        response = await api_client.delete(
            f"/api/v1/services/{service.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code in [200, 204]
    
    @pytest.mark.asyncio
    async def test_delete_service_not_found(
        self,
        api_client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Eliminar servicio inexistente."""
        fake_id = str(uuid4()).replace("-", "")
        
        response = await api_client.delete(
            f"/api/v1/services/{fake_id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 404


# =============================================================================
# Tests de multi-tenancy
# =============================================================================
class TestServiceMultiTenancy:
    """Tests de aislamiento por organización."""
    
    @pytest.mark.asyncio
    async def test_list_only_own_organization_services(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Solo listar servicios de assets de mi organización."""
        from app.models.organization import Organization
        
        # Crear otra organización con asset y servicio
        other_org = Organization(
            name="Other Org",
            slug="other-org-svc"
        )
        db_session.add(other_org)
        await db_session.flush()
        
        # Asset de otra organización
        other_asset = Asset(
            ip_address="10.0.0.1",
            organization_id=other_org.id
        )
        db_session.add(other_asset)
        await db_session.flush()
        
        # Servicio de otra organización
        other_svc = Service(
            asset_id=other_asset.id,
            port=22,
            protocol="tcp"
        )
        db_session.add(other_svc)
        
        # Asset de mi organización
        my_asset = Asset(
            ip_address="192.168.1.10",
            organization_id=test_organization.id
        )
        db_session.add(my_asset)
        await db_session.flush()
        
        # Servicio de mi organización
        my_svc = Service(
            asset_id=my_asset.id,
            port=80,
            protocol="tcp"
        )
        db_session.add(my_svc)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/services",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Solo debe mostrar el servicio de mi organización
        assert data["total"] == 1
        assert data["items"][0]["port"] == 80
