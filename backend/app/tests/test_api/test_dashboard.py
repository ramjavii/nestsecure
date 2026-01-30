"""
Tests para el API de Dashboard.

Pruebas de estadísticas y visualizaciones del dashboard.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

from app.models.asset import Asset, AssetStatus, AssetCriticality
from app.models.service import Service


# =============================================================================
# Tests de estadísticas generales
# =============================================================================
class TestDashboardStats:
    """Tests para GET /api/v1/dashboard/stats"""
    
    @pytest.mark.asyncio
    async def test_get_stats_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Estadísticas con base de datos vacía."""
        response = await api_client.get(
            "/api/v1/dashboard/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["assets"]["total"] == 0
        assert data["services"]["total"] == 0
        assert data["vulnerabilities"]["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_stats_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Estadísticas con datos existentes."""
        # Crear assets
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
        await db_session.flush()
        
        # Crear servicios
        service = Service(
            asset_id=asset1.id,
            port=80,
            protocol="tcp",
            state="open"
        )
        db_session.add(service)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/dashboard/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["assets"]["total"] == 2
        assert data["services"]["total"] == 1
        assert data["assets"]["active"] == 1
    
    @pytest.mark.asyncio
    async def test_get_stats_unauthorized(
        self,
        api_client: AsyncClient
    ):
        """Estadísticas sin autenticación."""
        response = await api_client.get("/api/v1/dashboard/stats")
        assert response.status_code == 401


# =============================================================================
# Tests de assets recientes
# =============================================================================
class TestRecentAssets:
    """Tests para GET /api/v1/dashboard/recent-assets"""
    
    @pytest.mark.asyncio
    async def test_recent_assets_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Assets recientes sin datos."""
        response = await api_client.get(
            "/api/v1/dashboard/recent-assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    @pytest.mark.asyncio
    async def test_recent_assets_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Assets recientes con datos."""
        # Crear assets
        for i in range(5):
            asset = Asset(
                ip_address=f"192.168.1.{10 + i}",
                hostname=f"server-{i}",
                organization_id=test_organization.id
            )
            db_session.add(asset)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/dashboard/recent-assets?limit=3",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
    
    @pytest.mark.asyncio
    async def test_recent_assets_default_limit(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Límite por defecto de assets recientes."""
        # Crear 15 assets
        for i in range(15):
            asset = Asset(
                ip_address=f"192.168.1.{10 + i}",
                organization_id=test_organization.id
            )
            db_session.add(asset)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/dashboard/recent-assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10  # Límite por defecto


# =============================================================================
# Tests de assets con mayor riesgo
# =============================================================================
class TestTopRiskyAssets:
    """Tests para GET /api/v1/dashboard/top-risky-assets"""
    
    @pytest.mark.asyncio
    async def test_top_risky_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Assets de riesgo sin datos."""
        response = await api_client.get(
            "/api/v1/dashboard/top-risky-assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    @pytest.mark.asyncio
    async def test_top_risky_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Assets ordenados por riesgo."""
        assets = [
            Asset(
                ip_address="192.168.1.10",
                organization_id=test_organization.id,
                risk_score=95.0,
                criticality=AssetCriticality.CRITICAL
            ),
            Asset(
                ip_address="192.168.1.11",
                organization_id=test_organization.id,
                risk_score=50.0,
                criticality=AssetCriticality.MEDIUM
            ),
            Asset(
                ip_address="192.168.1.12",
                organization_id=test_organization.id,
                risk_score=10.0,
                criticality=AssetCriticality.LOW
            ),
        ]
        for asset in assets:
            db_session.add(asset)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/dashboard/top-risky-assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Verificar orden descendente por risk_score
        assert data[0]["risk_score"] >= data[1]["risk_score"]


# =============================================================================
# Tests de distribución de puertos
# =============================================================================
class TestPortsDistribution:
    """Tests para GET /api/v1/dashboard/ports-distribution"""
    
    @pytest.mark.asyncio
    async def test_ports_distribution_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Distribución de puertos sin datos."""
        response = await api_client.get(
            "/api/v1/dashboard/ports-distribution",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    @pytest.mark.asyncio
    async def test_ports_distribution_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Distribución de puertos con servicios."""
        # Crear varios assets con servicios en diferentes puertos
        for i in range(3):
            asset = Asset(
                ip_address=f"192.168.1.{10 + i}",
                organization_id=test_organization.id
            )
            db_session.add(asset)
            await db_session.flush()
            
            # Cada asset tiene servicios en puerto 80
            svc = Service(
                asset_id=asset.id,
                port=80,
                protocol="tcp",
                state="open"
            )
            db_session.add(svc)
        
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/dashboard/ports-distribution",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0


# =============================================================================
# Tests de timeline de assets
# =============================================================================
class TestAssetTimeline:
    """Tests para GET /api/v1/dashboard/asset-timeline"""
    
    @pytest.mark.asyncio
    async def test_asset_timeline_empty(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Timeline sin assets."""
        response = await api_client.get(
            "/api/v1/dashboard/asset-timeline",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_asset_timeline_with_data(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Timeline con assets creados."""
        # Crear assets
        for i in range(3):
            asset = Asset(
                ip_address=f"192.168.1.{10 + i}",
                organization_id=test_organization.id
            )
            db_session.add(asset)
        await db_session.commit()
        
        response = await api_client.get(
            "/api/v1/dashboard/asset-timeline?days=7",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# =============================================================================
# Tests de multi-tenancy en dashboard
# =============================================================================
class TestDashboardMultiTenancy:
    """Tests de aislamiento por organización."""
    
    @pytest.mark.asyncio
    async def test_stats_only_own_organization(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_organization
    ):
        """Stats solo incluye datos de la organización del usuario."""
        from app.models.organization import Organization
        
        # Crear otra organización con assets
        other_org = Organization(
            name="Other Org",
            slug="other-org-dashboard"
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
            "/api/v1/dashboard/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Solo debe contar el asset de mi organización
        assert data["assets"]["total"] == 1
