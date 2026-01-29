# =============================================================================
# NESTSECURE - Tests de Endpoints de Organizaciones
# =============================================================================
"""
Tests para los endpoints CRUD de organizaciones.

Cobertura:
- GET /api/v1/organizations - Listar organizaciones
- POST /api/v1/organizations - Crear organización (superuser)
- GET /api/v1/organizations/{id} - Obtener organización
- PATCH /api/v1/organizations/{id} - Actualizar organización
- DELETE /api/v1/organizations/{id} - Eliminar organización (superuser)
- GET /api/v1/organizations/{id}/stats - Estadísticas
- PATCH /api/v1/organizations/{id}/activate - Activar/desactivar
"""

import pytest
from httpx import AsyncClient


API_PREFIX = "/api/v1/organizations"


# =============================================================================
# Tests de Listar Organizaciones
# =============================================================================
class TestListOrganizations:
    """Tests para GET /organizations."""
    
    @pytest.mark.asyncio
    async def test_list_organizations_as_superuser(
        self, api_client: AsyncClient, test_superuser, superuser_auth_headers
    ):
        """
        DADO: Un superusuario autenticado
        CUANDO: Se solicita listar organizaciones
        ENTONCES: Retorna todas las organizaciones
        """
        response = await api_client.get(
            API_PREFIX,
            headers=superuser_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
    
    @pytest.mark.asyncio
    async def test_list_organizations_as_regular_user(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario normal autenticado
        CUANDO: Se solicita listar organizaciones
        ENTONCES: Solo ve su propia organización
        """
        response = await api_client.get(
            API_PREFIX,
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
    
    @pytest.mark.asyncio
    async def test_list_organizations_unauthenticated(self, api_client: AsyncClient):
        """
        DADO: No se proporciona token
        CUANDO: Se intenta listar organizaciones
        ENTONCES: Retorna 401 Unauthorized
        """
        response = await api_client.get(API_PREFIX)
        assert response.status_code == 401


# =============================================================================
# Tests de Crear Organización
# =============================================================================
class TestCreateOrganization:
    """Tests para POST /organizations."""
    
    @pytest.mark.asyncio
    async def test_create_organization_as_superuser(
        self, api_client: AsyncClient, test_superuser, superuser_auth_headers
    ):
        """
        DADO: Un superusuario autenticado
        CUANDO: Se crea una organización
        ENTONCES: Retorna 201 con los datos de la organización
        """
        response = await api_client.post(
            API_PREFIX,
            headers=superuser_auth_headers,
            json={
                "name": "New Organization",
                "slug": "new-org",
                "description": "A new test organization",
                "max_assets": 50,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Organization"
        assert data["slug"] == "new-org"
        assert data["user_count"] == 0
        assert data["asset_count"] == 0
    
    @pytest.mark.asyncio
    async def test_create_organization_as_admin_forbidden(
        self, api_client: AsyncClient, test_admin, admin_auth_headers
    ):
        """
        DADO: Un admin (no superuser)
        CUANDO: Intenta crear una organización
        ENTONCES: Retorna 403 Forbidden
        """
        response = await api_client.post(
            API_PREFIX,
            headers=admin_auth_headers,
            json={
                "name": "Another Org",
                "slug": "another-org",
            },
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug(
        self, api_client: AsyncClient, test_organization, superuser_auth_headers
    ):
        """
        DADO: Una organización con cierto slug existe
        CUANDO: Se intenta crear otra con el mismo slug
        ENTONCES: Retorna 409 Conflict
        """
        response = await api_client.post(
            API_PREFIX,
            headers=superuser_auth_headers,
            json={
                "name": "Duplicate Org",
                "slug": "test-org",  # Ya existe
            },
        )
        
        assert response.status_code == 409


# =============================================================================
# Tests de Obtener Organización
# =============================================================================
class TestGetOrganization:
    """Tests para GET /organizations/{id}."""
    
    @pytest.mark.asyncio
    async def test_get_own_organization(
        self, api_client: AsyncClient, test_user, test_organization, auth_headers
    ):
        """
        DADO: Un usuario autenticado
        CUANDO: Solicita su propia organización
        ENTONCES: Retorna los datos de la organización
        """
        response = await api_client.get(
            f"{API_PREFIX}/{test_organization.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Organization"
        assert "user_count" in data
        assert "asset_count" in data
    
    @pytest.mark.asyncio
    async def test_get_other_organization_forbidden(
        self, api_client: AsyncClient, db_session, test_user, auth_headers
    ):
        """
        DADO: Un usuario de otra organización
        CUANDO: Intenta obtener una organización diferente
        ENTONCES: Retorna 403 Forbidden
        """
        from app.models.organization import Organization
        
        # Crear otra organización
        other_org = Organization(
            name="Other Org",
            slug="other-org",
            max_assets=10,
        )
        db_session.add(other_org)
        await db_session.commit()
        await db_session.refresh(other_org)
        
        response = await api_client.get(
            f"{API_PREFIX}/{other_org.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_any_organization_as_superuser(
        self, api_client: AsyncClient, db_session, superuser_auth_headers
    ):
        """
        DADO: Un superusuario autenticado
        CUANDO: Solicita cualquier organización
        ENTONCES: Retorna los datos
        """
        from app.models.organization import Organization
        
        # Crear otra organización
        other_org = Organization(
            name="Super Accessible Org",
            slug="super-accessible-org",
            max_assets=10,
        )
        db_session.add(other_org)
        await db_session.commit()
        await db_session.refresh(other_org)
        
        response = await api_client.get(
            f"{API_PREFIX}/{other_org.id}",
            headers=superuser_auth_headers,
        )
        
        assert response.status_code == 200


# =============================================================================
# Tests de Actualizar Organización
# =============================================================================
class TestUpdateOrganization:
    """Tests para PATCH /organizations/{id}."""
    
    @pytest.mark.asyncio
    async def test_update_organization_as_admin(
        self, api_client: AsyncClient, test_organization, admin_auth_headers
    ):
        """
        DADO: Un admin de la organización
        CUANDO: Actualiza la organización
        ENTONCES: Retorna 200 con datos actualizados
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_organization.id}",
            headers=admin_auth_headers,
            json={"description": "Updated description"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_update_organization_as_regular_user_forbidden(
        self, api_client: AsyncClient, test_organization, auth_headers
    ):
        """
        DADO: Un usuario normal (no admin)
        CUANDO: Intenta actualizar la organización
        ENTONCES: Retorna 403 Forbidden
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_organization.id}",
            headers=auth_headers,
            json={"name": "Hacked Name"},
        )
        
        assert response.status_code == 403


# =============================================================================
# Tests de Eliminar Organización
# =============================================================================
class TestDeleteOrganization:
    """Tests para DELETE /organizations/{id}."""
    
    @pytest.mark.asyncio
    async def test_delete_organization_as_superuser(
        self, api_client: AsyncClient, db_session, superuser_auth_headers
    ):
        """
        DADO: Un superusuario autenticado
        CUANDO: Elimina una organización
        ENTONCES: Retorna 200 con confirmación
        """
        from app.models.organization import Organization
        
        # Crear organización a eliminar
        org_to_delete = Organization(
            name="To Delete",
            slug="to-delete-org",
            max_assets=10,
        )
        db_session.add(org_to_delete)
        await db_session.commit()
        await db_session.refresh(org_to_delete)
        
        response = await api_client.delete(
            f"{API_PREFIX}/{org_to_delete.id}",
            headers=superuser_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_id"] == str(org_to_delete.id)
    
    @pytest.mark.asyncio
    async def test_delete_organization_as_admin_forbidden(
        self, api_client: AsyncClient, db_session, admin_auth_headers
    ):
        """
        DADO: Un admin (no superuser)
        CUANDO: Intenta eliminar una organización
        ENTONCES: Retorna 403 Forbidden
        """
        from app.models.organization import Organization
        
        # Crear organización
        org = Organization(
            name="Protected Org",
            slug="protected-org",
            max_assets=10,
        )
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
        
        response = await api_client.delete(
            f"{API_PREFIX}/{org.id}",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 403


# =============================================================================
# Tests de Estadísticas de Organización
# =============================================================================
class TestOrganizationStats:
    """Tests para GET /organizations/{id}/stats."""
    
    @pytest.mark.asyncio
    async def test_get_stats_for_own_organization(
        self, api_client: AsyncClient, test_organization, auth_headers
    ):
        """
        DADO: Un usuario autenticado
        CUANDO: Solicita stats de su organización
        ENTONCES: Retorna estadísticas
        """
        response = await api_client.get(
            f"{API_PREFIX}/{test_organization.id}/stats",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "organization_id" in data
        assert "user_count" in data
        assert "asset_count" in data
        assert "scan_count" in data
        assert "vulnerability_count" in data


# =============================================================================
# Tests de Activar/Desactivar Organización
# =============================================================================
class TestActivateOrganization:
    """Tests para PATCH /organizations/{id}/activate."""
    
    @pytest.mark.asyncio
    async def test_deactivate_organization_as_superuser(
        self, api_client: AsyncClient, db_session, superuser_auth_headers
    ):
        """
        DADO: Un superusuario autenticado
        CUANDO: Desactiva una organización
        ENTONCES: Retorna 200 con organización desactivada
        """
        from app.models.organization import Organization
        
        # Crear organización
        org = Organization(
            name="To Deactivate",
            slug="to-deactivate-org",
            max_assets=10,
            is_active=True,
        )
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
        
        response = await api_client.patch(
            f"{API_PREFIX}/{org.id}/activate?is_active=false",
            headers=superuser_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_activate_organization_as_admin_forbidden(
        self, api_client: AsyncClient, test_organization, admin_auth_headers
    ):
        """
        DADO: Un admin (no superuser)
        CUANDO: Intenta activar/desactivar una organización
        ENTONCES: Retorna 403 Forbidden
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_organization.id}/activate?is_active=false",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 403
