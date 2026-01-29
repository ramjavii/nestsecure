# =============================================================================
# NESTSECURE - Tests de Modelos SQLAlchemy
# =============================================================================
"""
Tests de integración para los modelos de base de datos.

Estos tests verifican:
- Creación de modelos
- Relaciones entre modelos
- Validaciones y constraints
- Propiedades y métodos de los modelos
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Tests de Organization
# =============================================================================
class TestOrganizationModel:
    """Tests para el modelo Organization."""
    
    @pytest.mark.asyncio
    async def test_create_organization(self, db_session: AsyncSession):
        """Test crear una organización."""
        from app.models.organization import Organization
        
        org = Organization(
            id=str(uuid4()),
            name="Test Company",
            slug="test-company",
            description="A test organization",
            max_assets=50,
            is_active=True,
        )
        
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
        
        assert org.id is not None
        assert org.name == "Test Company"
        assert org.slug == "test-company"
        assert org.max_assets == 50
        assert org.is_active is True
        assert org.created_at is not None
    
    @pytest.mark.asyncio
    async def test_organization_settings(self, db_session: AsyncSession):
        """Test configuración JSONB de organización."""
        from app.models.organization import Organization
        
        settings = {
            "theme": "dark",
            "notifications": {"email": True, "slack": False},
        }
        
        org = Organization(
            id=str(uuid4()),
            name="Settings Test",
            slug="settings-test",
            settings=settings,
        )
        
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
        
        assert org.settings == settings
        assert org.get_setting("theme") == "dark"
        assert org.get_setting("nonexistent", "default") == "default"
    
    @pytest.mark.asyncio
    async def test_organization_license_validity(self, db_session: AsyncSession):
        """Test validación de licencia."""
        from app.models.organization import Organization
        from datetime import timedelta
        
        # Org con licencia válida
        org_valid = Organization(
            id=str(uuid4()),
            name="Valid License",
            slug="valid-license",
            license_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        
        # Org con licencia expirada
        org_expired = Organization(
            id=str(uuid4()),
            name="Expired License",
            slug="expired-license",
            license_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        
        # Org sin fecha de expiración
        org_no_limit = Organization(
            id=str(uuid4()),
            name="No Limit",
            slug="no-limit",
        )
        
        db_session.add_all([org_valid, org_expired, org_no_limit])
        await db_session.commit()
        
        assert org_valid.is_license_valid is True
        assert org_expired.is_license_valid is False
        assert org_no_limit.is_license_valid is True


# =============================================================================
# Tests de User
# =============================================================================
class TestUserModel:
    """Tests para el modelo User."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test crear un usuario."""
        from app.models.organization import Organization
        from app.models.user import User
        
        # Crear organización primero
        org = Organization(
            id=str(uuid4()),
            name="User Test Org",
            slug="user-test-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        # Crear usuario
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            hashed_password="hashed_password_here",
            full_name="Test User",
            role="viewer",
            organization_id=org.id,
            is_active=True,
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.role == "viewer"
        assert user.organization_id == org.id
    
    @pytest.mark.asyncio
    async def test_user_roles(self, db_session: AsyncSession):
        """Test propiedades de roles de usuario."""
        from app.models.organization import Organization
        from app.models.user import User
        
        org = Organization(
            id=str(uuid4()),
            name="Role Test Org",
            slug="role-test-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        admin = User(
            id=str(uuid4()),
            email="admin@test.com",
            hashed_password="hash",
            full_name="Admin User",
            role="admin",
            organization_id=org.id,
        )
        
        operator = User(
            id=str(uuid4()),
            email="operator@test.com",
            hashed_password="hash",
            full_name="Operator User",
            role="operator",
            organization_id=org.id,
        )
        
        viewer = User(
            id=str(uuid4()),
            email="viewer@test.com",
            hashed_password="hash",
            full_name="Viewer User",
            role="viewer",
            organization_id=org.id,
        )
        
        db_session.add_all([admin, operator, viewer])
        await db_session.commit()
        
        assert admin.is_admin is True
        assert admin.is_operator is True
        assert admin.is_analyst is True
        
        assert operator.is_admin is False
        assert operator.is_operator is True
        
        assert viewer.is_admin is False
        assert viewer.is_operator is False
    
    @pytest.mark.asyncio
    async def test_user_organization_relationship(self, db_session: AsyncSession):
        """Test relación usuario-organización."""
        from app.models.organization import Organization
        from app.models.user import User
        
        org = Organization(
            id=str(uuid4()),
            name="Relationship Org",
            slug="relationship-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        user1 = User(
            id=str(uuid4()),
            email="user1@test.com",
            hashed_password="hash",
            full_name="User One",
            role="viewer",
            organization_id=org.id,
        )
        
        user2 = User(
            id=str(uuid4()),
            email="user2@test.com",
            hashed_password="hash",
            full_name="User Two",
            role="analyst",
            organization_id=org.id,
        )
        
        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(org)
        
        assert org.user_count == 2


# =============================================================================
# Tests de Asset
# =============================================================================
class TestAssetModel:
    """Tests para el modelo Asset."""
    
    @pytest.mark.asyncio
    async def test_create_asset(self, db_session: AsyncSession):
        """Test crear un asset."""
        from app.models.organization import Organization
        from app.models.asset import Asset
        
        org = Organization(
            id=str(uuid4()),
            name="Asset Test Org",
            slug="asset-test-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        asset = Asset(
            id=str(uuid4()),
            organization_id=org.id,
            ip_address="192.168.1.100",
            hostname="test-server",
            asset_type="server",
            criticality="high",
            status="active",
        )
        
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        assert asset.id is not None
        assert asset.ip_address == "192.168.1.100"
        assert asset.hostname == "test-server"
        assert asset.asset_type == "server"
        assert asset.criticality == "high"
    
    @pytest.mark.asyncio
    async def test_asset_vulnerability_counts(self, db_session: AsyncSession):
        """Test conteo de vulnerabilidades."""
        from app.models.organization import Organization
        from app.models.asset import Asset
        
        org = Organization(
            id=str(uuid4()),
            name="Vuln Count Org",
            slug="vuln-count-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        asset = Asset(
            id=str(uuid4()),
            organization_id=org.id,
            ip_address="10.0.0.1",
            vuln_critical_count=2,
            vuln_high_count=5,
            vuln_medium_count=10,
            vuln_low_count=20,
        )
        
        db_session.add(asset)
        await db_session.commit()
        
        assert asset.total_vulnerabilities == 37
        assert asset.has_critical_vulnerabilities is True
    
    @pytest.mark.asyncio
    async def test_asset_risk_score_calculation(self, db_session: AsyncSession):
        """Test cálculo de risk score."""
        from app.models.organization import Organization
        from app.models.asset import Asset
        
        org = Organization(
            id=str(uuid4()),
            name="Risk Score Org",
            slug="risk-score-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        asset = Asset(
            id=str(uuid4()),
            organization_id=org.id,
            ip_address="10.0.0.2",
            vuln_critical_count=1,  # 40 points
            vuln_high_count=2,       # 40 points
            vuln_medium_count=0,
            vuln_low_count=0,
        )
        
        db_session.add(asset)
        await db_session.commit()
        
        asset.update_risk_score()
        
        # 1*40 + 2*20 = 80
        assert asset.risk_score == 80.0
    
    @pytest.mark.asyncio
    async def test_asset_tags(self, db_session: AsyncSession):
        """Test manejo de etiquetas."""
        from app.models.organization import Organization
        from app.models.asset import Asset
        
        org = Organization(
            id=str(uuid4()),
            name="Tags Org",
            slug="tags-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        asset = Asset(
            id=str(uuid4()),
            organization_id=org.id,
            ip_address="10.0.0.3",
            tags=["production", "web"],
        )
        
        db_session.add(asset)
        await db_session.commit()
        
        asset.add_tag("critical")
        assert "critical" in asset.tags
        
        asset.remove_tag("web")
        assert "web" not in asset.tags
        assert "production" in asset.tags


# =============================================================================
# Tests de Service
# =============================================================================
class TestServiceModel:
    """Tests para el modelo Service."""
    
    @pytest.mark.asyncio
    async def test_create_service(self, db_session: AsyncSession):
        """Test crear un servicio."""
        from app.models.organization import Organization
        from app.models.asset import Asset
        from app.models.service import Service
        
        org = Organization(
            id=str(uuid4()),
            name="Service Test Org",
            slug="service-test-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        asset = Asset(
            id=str(uuid4()),
            organization_id=org.id,
            ip_address="192.168.1.50",
        )
        db_session.add(asset)
        await db_session.flush()
        
        service = Service(
            id=str(uuid4()),
            asset_id=asset.id,
            port=443,
            protocol="tcp",
            service_name="https",
            product="nginx",
            version="1.24.0",
            state="open",
            ssl_enabled=True,
        )
        
        db_session.add(service)
        await db_session.commit()
        await db_session.refresh(service)
        
        assert service.id is not None
        assert service.port == 443
        assert service.service_name == "https"
        assert service.ssl_enabled is True
    
    @pytest.mark.asyncio
    async def test_service_properties(self, db_session: AsyncSession):
        """Test propiedades del servicio."""
        from app.models.organization import Organization
        from app.models.asset import Asset
        from app.models.service import Service
        
        org = Organization(
            id=str(uuid4()),
            name="Service Props Org",
            slug="service-props-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        asset = Asset(
            id=str(uuid4()),
            organization_id=org.id,
            ip_address="192.168.1.51",
        )
        db_session.add(asset)
        await db_session.flush()
        
        http_service = Service(
            id=str(uuid4()),
            asset_id=asset.id,
            port=80,
            protocol="tcp",
            service_name="http",
            state="open",
        )
        
        db_service = Service(
            id=str(uuid4()),
            asset_id=asset.id,
            port=5432,
            protocol="tcp",
            service_name="postgresql",
            state="open",
        )
        
        db_session.add_all([http_service, db_service])
        await db_session.commit()
        
        assert http_service.is_web_service is True
        assert http_service.is_database_service is False
        
        assert db_service.is_web_service is False
        assert db_service.is_database_service is True
        
        assert http_service.port_protocol == "80/tcp"
    
    @pytest.mark.asyncio
    async def test_asset_services_relationship(self, db_session: AsyncSession):
        """Test relación asset-services."""
        from app.models.organization import Organization
        from app.models.asset import Asset
        from app.models.service import Service
        
        org = Organization(
            id=str(uuid4()),
            name="Relationship Org",
            slug="rel-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        asset = Asset(
            id=str(uuid4()),
            organization_id=org.id,
            ip_address="192.168.1.52",
        )
        db_session.add(asset)
        await db_session.flush()
        
        services = [
            Service(
                id=str(uuid4()),
                asset_id=asset.id,
                port=port,
                protocol="tcp",
                state="open",
            )
            for port in [22, 80, 443]
        ]
        
        db_session.add_all(services)
        await db_session.commit()
        await db_session.refresh(asset)
        
        assert asset.service_count == 3


# =============================================================================
# Tests de Relaciones Completas
# =============================================================================
class TestModelRelationships:
    """Tests para relaciones entre modelos."""
    
    @pytest.mark.asyncio
    async def test_cascade_delete_organization(self, db_session: AsyncSession):
        """Test que eliminar organización elimina usuarios y assets."""
        from app.models.organization import Organization
        from app.models.user import User
        from app.models.asset import Asset
        
        org = Organization(
            id=str(uuid4()),
            name="Cascade Test Org",
            slug="cascade-test-org",
        )
        db_session.add(org)
        await db_session.flush()
        
        user = User(
            id=str(uuid4()),
            email="cascade@test.com",
            hashed_password="hash",
            full_name="Cascade User",
            role="viewer",
            organization_id=org.id,
        )
        
        asset = Asset(
            id=str(uuid4()),
            organization_id=org.id,
            ip_address="10.0.0.99",
        )
        
        db_session.add_all([user, asset])
        await db_session.commit()
        
        # Verificar que existen
        user_id = user.id
        asset_id = asset.id
        
        # Eliminar organización
        await db_session.delete(org)
        await db_session.commit()
        
        # Verificar cascade delete
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        assert result.scalar_one_or_none() is None
        
        result = await db_session.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        assert result.scalar_one_or_none() is None
