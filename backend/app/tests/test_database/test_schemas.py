# =============================================================================
# NESTSECURE - Tests de Schemas Pydantic
# =============================================================================
"""
Tests para los schemas de validación Pydantic.

Estos tests verifican:
- Validaciones de campos
- Valores por defecto
- Transformaciones de datos
- Errores de validación
"""

import pytest
from pydantic import ValidationError


# =============================================================================
# Tests de Organization Schemas
# =============================================================================
class TestOrganizationSchemas:
    """Tests para schemas de Organization."""
    
    def test_organization_create_valid(self, sample_organization_data):
        """Test crear schema de organización válido."""
        from app.schemas.organization import OrganizationCreate
        
        schema = OrganizationCreate(**sample_organization_data)
        
        assert schema.name == "Test Organization"
        assert schema.slug == "test-org"
        assert schema.max_assets == 100
    
    def test_organization_create_slug_lowercase(self):
        """Test que el slug se convierte a minúsculas."""
        from app.schemas.organization import OrganizationCreate
        
        schema = OrganizationCreate(
            name="Test Org",
            slug="Test-Org-UPPER",
        )
        
        assert schema.slug == "test-org-upper"
    
    def test_organization_create_invalid_slug(self):
        """Test slug inválido rechazado."""
        from app.schemas.organization import OrganizationCreate
        
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                name="Test Org",
                slug="invalid slug!",  # Espacios y caracteres inválidos
            )
        
        assert "slug" in str(exc_info.value)
    
    def test_organization_update_partial(self):
        """Test actualización parcial de organización."""
        from app.schemas.organization import OrganizationUpdate
        
        # Solo actualizar nombre
        schema = OrganizationUpdate(name="New Name")
        
        assert schema.name == "New Name"
        assert schema.description is None
        assert schema.max_assets is None


# =============================================================================
# Tests de User Schemas
# =============================================================================
class TestUserSchemas:
    """Tests para schemas de User."""
    
    def test_user_create_valid(self):
        """Test crear schema de usuario válido."""
        from app.schemas.user import UserCreate
        
        schema = UserCreate(
            email="test@example.com",
            password="SecurePass123",
            full_name="Test User",
            role="viewer",
            organization_id="123e4567-e89b-12d3-a456-426614174000",
        )
        
        assert schema.email == "test@example.com"
        assert schema.role == "viewer"
    
    def test_user_create_password_too_short(self):
        """Test contraseña muy corta rechazada."""
        from app.schemas.user import UserCreate
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="short",
                full_name="Test User",
                role="viewer",
                organization_id="123e4567-e89b-12d3-a456-426614174000",
            )
        
        # Pydantic devuelve mensaje en inglés
        assert "8 characters" in str(exc_info.value) or "password" in str(exc_info.value).lower()
    
    def test_user_create_password_no_uppercase(self):
        """Test contraseña sin mayúscula rechazada."""
        from app.schemas.user import UserCreate
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="nouppercase123",
                full_name="Test User",
                role="viewer",
                organization_id="123e4567-e89b-12d3-a456-426614174000",
            )
        
        assert "mayúscula" in str(exc_info.value)
    
    def test_user_create_password_no_number(self):
        """Test contraseña sin número rechazada."""
        from app.schemas.user import UserCreate
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="NoNumberHere",
                full_name="Test User",
                role="viewer",
                organization_id="123e4567-e89b-12d3-a456-426614174000",
            )
        
        assert "número" in str(exc_info.value)
    
    def test_user_create_invalid_role(self):
        """Test rol inválido rechazado."""
        from app.schemas.user import UserCreate
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="SecurePass123",
                full_name="Test User",
                role="superadmin",  # Rol no válido
                organization_id="123e4567-e89b-12d3-a456-426614174000",
            )
        
        assert "Rol inválido" in str(exc_info.value)
    
    def test_user_create_invalid_email(self):
        """Test email inválido rechazado."""
        from app.schemas.user import UserCreate
        
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="SecurePass123",
                full_name="Test User",
                role="viewer",
                organization_id="123e4567-e89b-12d3-a456-426614174000",
            )
    
    def test_user_update_password(self):
        """Test schema de cambio de contraseña."""
        from app.schemas.user import UserUpdatePassword
        
        schema = UserUpdatePassword(
            current_password="OldPass123",
            new_password="NewSecure456",
        )
        
        assert schema.current_password == "OldPass123"
        assert schema.new_password == "NewSecure456"


# =============================================================================
# Tests de Asset Schemas
# =============================================================================
class TestAssetSchemas:
    """Tests para schemas de Asset."""
    
    def test_asset_create_valid(self):
        """Test crear schema de asset válido."""
        from app.schemas.asset import AssetCreate
        
        schema = AssetCreate(
            ip_address="192.168.1.100",
            hostname="web-server",
            organization_id="123e4567-e89b-12d3-a456-426614174000",
            asset_type="server",
            criticality="high",
        )
        
        assert schema.ip_address == "192.168.1.100"
        assert schema.asset_type == "server"
        assert schema.criticality == "high"
    
    def test_asset_create_ipv6(self):
        """Test asset con IPv6 válida."""
        from app.schemas.asset import AssetCreate
        
        schema = AssetCreate(
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            organization_id="123e4567-e89b-12d3-a456-426614174000",
        )
        
        assert "2001:" in schema.ip_address
    
    def test_asset_create_invalid_ip(self):
        """Test IP inválida rechazada."""
        from app.schemas.asset import AssetCreate
        
        with pytest.raises(ValidationError) as exc_info:
            AssetCreate(
                ip_address="not-an-ip",
                organization_id="123e4567-e89b-12d3-a456-426614174000",
            )
        
        assert "IP válida" in str(exc_info.value)
    
    def test_asset_create_invalid_mac(self):
        """Test MAC inválida rechazada."""
        from app.schemas.asset import AssetCreate
        
        with pytest.raises(ValidationError):
            AssetCreate(
                ip_address="192.168.1.100",
                mac_address="invalid-mac",
                organization_id="123e4567-e89b-12d3-a456-426614174000",
            )
    
    def test_asset_create_valid_mac(self):
        """Test MAC válida aceptada."""
        from app.schemas.asset import AssetCreate
        
        schema = AssetCreate(
            ip_address="192.168.1.100",
            mac_address="AA:BB:CC:DD:EE:FF",
            organization_id="123e4567-e89b-12d3-a456-426614174000",
        )
        
        assert schema.mac_address == "AA:BB:CC:DD:EE:FF"
    
    def test_asset_create_tags_normalized(self):
        """Test que las etiquetas se normalizan."""
        from app.schemas.asset import AssetCreate
        
        schema = AssetCreate(
            ip_address="192.168.1.100",
            organization_id="123e4567-e89b-12d3-a456-426614174000",
            tags=["  Production  ", "WEB", "Critical"],
        )
        
        assert schema.tags == ["production", "web", "critical"]
    
    def test_asset_create_invalid_asset_type(self):
        """Test tipo de asset inválido rechazado."""
        from app.schemas.asset import AssetCreate
        
        with pytest.raises(ValidationError) as exc_info:
            AssetCreate(
                ip_address="192.168.1.100",
                organization_id="123e4567-e89b-12d3-a456-426614174000",
                asset_type="spaceship",  # Tipo inválido
            )
        
        assert "Tipo inválido" in str(exc_info.value)
    
    def test_asset_create_invalid_criticality(self):
        """Test criticidad inválida rechazada."""
        from app.schemas.asset import AssetCreate
        
        with pytest.raises(ValidationError) as exc_info:
            AssetCreate(
                ip_address="192.168.1.100",
                organization_id="123e4567-e89b-12d3-a456-426614174000",
                criticality="ultra-critical",  # Valor inválido
            )
        
        assert "Criticidad inválida" in str(exc_info.value)


# =============================================================================
# Tests de Service Schemas
# =============================================================================
class TestServiceSchemas:
    """Tests para schemas de Service."""
    
    def test_service_create_valid(self):
        """Test crear schema de servicio válido."""
        from app.schemas.service import ServiceCreate
        
        schema = ServiceCreate(
            asset_id="123e4567-e89b-12d3-a456-426614174000",
            port=443,
            protocol="tcp",
            service_name="https",
        )
        
        assert schema.port == 443
        assert schema.protocol == "tcp"
        assert schema.service_name == "https"
    
    def test_service_create_port_limits(self):
        """Test límites de puerto."""
        from app.schemas.service import ServiceCreate
        
        # Puerto mínimo válido
        schema_min = ServiceCreate(
            asset_id="123e4567-e89b-12d3-a456-426614174000",
            port=1,
            protocol="tcp",
        )
        assert schema_min.port == 1
        
        # Puerto máximo válido
        schema_max = ServiceCreate(
            asset_id="123e4567-e89b-12d3-a456-426614174000",
            port=65535,
            protocol="tcp",
        )
        assert schema_max.port == 65535
    
    def test_service_create_invalid_port(self):
        """Test puerto inválido rechazado."""
        from app.schemas.service import ServiceCreate
        
        with pytest.raises(ValidationError):
            ServiceCreate(
                asset_id="123e4567-e89b-12d3-a456-426614174000",
                port=70000,  # Fuera de rango
                protocol="tcp",
            )
    
    def test_service_create_protocol_lowercase(self):
        """Test que el protocolo se normaliza a minúsculas."""
        from app.schemas.service import ServiceCreate
        
        schema = ServiceCreate(
            asset_id="123e4567-e89b-12d3-a456-426614174000",
            port=22,
            protocol="TCP",  # Mayúsculas
        )
        
        assert schema.protocol == "tcp"
    
    def test_service_create_invalid_protocol(self):
        """Test protocolo inválido rechazado."""
        from app.schemas.service import ServiceCreate
        
        with pytest.raises(ValidationError) as exc_info:
            ServiceCreate(
                asset_id="123e4567-e89b-12d3-a456-426614174000",
                port=22,
                protocol="icmp",  # No soportado
            )
        
        assert "Protocolo inválido" in str(exc_info.value)


# =============================================================================
# Tests de Common Schemas
# =============================================================================
class TestCommonSchemas:
    """Tests para schemas comunes."""
    
    def test_pagination_params_defaults(self):
        """Test valores por defecto de paginación."""
        from app.schemas.common import PaginationParams
        
        params = PaginationParams()
        
        assert params.page == 1
        assert params.page_size == 20
        assert params.offset == 0
    
    def test_pagination_params_offset_calculation(self):
        """Test cálculo de offset."""
        from app.schemas.common import PaginationParams
        
        params = PaginationParams(page=3, page_size=25)
        
        assert params.offset == 50  # (3-1) * 25
    
    def test_pagination_params_limits(self):
        """Test límites de paginación."""
        from app.schemas.common import PaginationParams
        
        # page_size máximo
        with pytest.raises(ValidationError):
            PaginationParams(page_size=500)
        
        # page mínimo
        with pytest.raises(ValidationError):
            PaginationParams(page=0)
    
    def test_paginated_response_create(self):
        """Test crear respuesta paginada."""
        from app.schemas.common import PaginatedResponse
        
        response = PaginatedResponse.create(
            items=["a", "b", "c"],
            total=100,
            page=2,
            page_size=10,
        )
        
        assert response.items == ["a", "b", "c"]
        assert response.total == 100
        assert response.pages == 10
    
    def test_message_response(self):
        """Test respuesta con mensaje."""
        from app.schemas.common import MessageResponse
        
        response = MessageResponse(message="Operación exitosa")
        
        assert response.message == "Operación exitosa"
        assert response.success is True
    
    def test_error_response(self):
        """Test respuesta de error."""
        from app.schemas.common import ErrorResponse
        
        response = ErrorResponse(
            detail="Something went wrong",
            error_code="ERR_001",
            errors=[{"field": "email", "message": "Invalid"}],
        )
        
        assert response.detail == "Something went wrong"
        assert response.error_code == "ERR_001"
        assert len(response.errors) == 1
