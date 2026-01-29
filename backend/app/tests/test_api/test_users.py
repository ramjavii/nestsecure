# =============================================================================
# NESTSECURE - Tests de Endpoints de Usuarios
# =============================================================================
"""
Tests para los endpoints CRUD de usuarios.

Cobertura:
- GET /api/v1/users - Listar usuarios
- POST /api/v1/users - Crear usuario
- GET /api/v1/users/me - Perfil actual
- GET /api/v1/users/{id} - Obtener usuario
- PATCH /api/v1/users/{id} - Actualizar usuario
- DELETE /api/v1/users/{id} - Eliminar usuario
- PATCH /api/v1/users/{id}/password - Cambiar contraseña
- PATCH /api/v1/users/{id}/activate - Activar/desactivar
"""

import pytest
from httpx import AsyncClient


API_PREFIX = "/api/v1/users"


# =============================================================================
# Tests de Listar Usuarios
# =============================================================================
class TestListUsers:
    """Tests para GET /users."""
    
    @pytest.mark.asyncio
    async def test_list_users_authenticated(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario autenticado
        CUANDO: Se solicita listar usuarios
        ENTONCES: Retorna lista paginada de usuarios de su organización
        """
        response = await api_client.get(
            API_PREFIX,
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] >= 1
    
    @pytest.mark.asyncio
    async def test_list_users_unauthenticated(self, api_client: AsyncClient):
        """
        DADO: No se proporciona token
        CUANDO: Se intenta listar usuarios
        ENTONCES: Retorna 401 Unauthorized
        """
        response = await api_client.get(API_PREFIX)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_users_pagination(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Usuarios existen
        CUANDO: Se solicita con paginación
        ENTONCES: Respeta los parámetros de paginación
        """
        response = await api_client.get(
            f"{API_PREFIX}?page=1&page_size=5",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
    
    @pytest.mark.asyncio
    async def test_list_users_search(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario existe con cierto email
        CUANDO: Se busca por email
        ENTONCES: Retorna solo usuarios que coinciden
        """
        response = await api_client.get(
            f"{API_PREFIX}?search=testuser",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        # Verificar que los resultados contienen el término de búsqueda
        for user in data["items"]:
            assert (
                "testuser" in user["email"].lower() or 
                "testuser" in (user.get("full_name") or "").lower()
            )


# =============================================================================
# Tests de Crear Usuario
# =============================================================================
class TestCreateUser:
    """Tests para POST /users."""
    
    @pytest.mark.asyncio
    async def test_create_user_as_admin(
        self, api_client: AsyncClient, test_admin, test_organization, admin_auth_headers
    ):
        """
        DADO: Un admin autenticado
        CUANDO: Se crea un nuevo usuario
        ENTONCES: Retorna 201 con los datos del usuario
        """
        response = await api_client.post(
            API_PREFIX,
            headers=admin_auth_headers,
            json={
                "email": "newuser@example.com",
                "password": "NewPassword123!",
                "full_name": "New User",
                "role": "viewer",
                "organization_id": str(test_organization.id),
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_create_user_as_regular_user_forbidden(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario normal (no admin)
        CUANDO: Intenta crear un usuario
        ENTONCES: Retorna 403 Forbidden
        """
        response = await api_client.post(
            API_PREFIX,
            headers=auth_headers,
            json={
                "email": "another@example.com",
                "password": "Password123!",
                "full_name": "Another User",
            },
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, api_client: AsyncClient, test_user, test_admin, test_organization, admin_auth_headers
    ):
        """
        DADO: Un email ya existe
        CUANDO: Se intenta crear usuario con ese email
        ENTONCES: Retorna 409 Conflict
        """
        response = await api_client.post(
            API_PREFIX,
            headers=admin_auth_headers,
            json={
                "email": "testuser@example.com",  # Ya existe
                "password": "Password123!",
                "full_name": "Duplicate User",
                "organization_id": str(test_organization.id),
            },
        )
        
        assert response.status_code == 409


# =============================================================================
# Tests de Obtener Usuario Actual (Me)
# =============================================================================
class TestGetCurrentUser:
    """Tests para GET /users/me."""
    
    @pytest.mark.asyncio
    async def test_get_me_success(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario autenticado
        CUANDO: Se solicita GET /me
        ENTONCES: Retorna datos del usuario actual
        """
        response = await api_client.get(
            f"{API_PREFIX}/me",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert "organization" in data


# =============================================================================
# Tests de Obtener Usuario por ID
# =============================================================================
class TestGetUser:
    """Tests para GET /users/{id}."""
    
    @pytest.mark.asyncio
    async def test_get_user_same_org(
        self, api_client: AsyncClient, test_user, test_admin, admin_auth_headers
    ):
        """
        DADO: Un admin de la misma organización
        CUANDO: Solicita un usuario
        ENTONCES: Retorna los datos del usuario
        """
        response = await api_client.get(
            f"{API_PREFIX}/{test_user.id}",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self, api_client: AsyncClient, test_admin, admin_auth_headers
    ):
        """
        DADO: Un ID de usuario inexistente
        CUANDO: Se solicita GET /users/{id}
        ENTONCES: Retorna 404 Not Found
        """
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = await api_client.get(
            f"{API_PREFIX}/{fake_id}",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 404


# =============================================================================
# Tests de Actualizar Usuario
# =============================================================================
class TestUpdateUser:
    """Tests para PATCH /users/{id}."""
    
    @pytest.mark.asyncio
    async def test_update_user_as_admin(
        self, api_client: AsyncClient, test_user, test_admin, admin_auth_headers
    ):
        """
        DADO: Un admin autenticado
        CUANDO: Actualiza un usuario
        ENTONCES: Retorna 200 con datos actualizados
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_user.id}",
            headers=admin_auth_headers,
            json={"full_name": "Updated Name"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_update_own_profile(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario normal (no admin)
        CUANDO: Intenta actualizar su propio perfil via PATCH /users/{id}
        ENTONCES: Retorna 403 Forbidden (solo admins pueden usar este endpoint)
        
        Nota: Usuarios pueden usar PATCH /users/me para actualizar su perfil limitado
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_user.id}",
            headers=auth_headers,
            json={"full_name": "My New Name"},
        )
        
        # Solo admins pueden actualizar usuarios via este endpoint
        assert response.status_code == 403


# =============================================================================
# Tests de Eliminar Usuario
# =============================================================================
class TestDeleteUser:
    """Tests para DELETE /users/{id}."""
    
    @pytest.mark.asyncio
    async def test_delete_user_as_admin(
        self, api_client: AsyncClient, db_session, test_organization, admin_auth_headers
    ):
        """
        DADO: Un admin autenticado
        CUANDO: Elimina un usuario
        ENTONCES: Retorna 200 con confirmación
        """
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        
        # Crear usuario a eliminar
        user_to_delete = User(
            email="todelete@example.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="To Delete",
            organization_id=test_organization.id,
            role=UserRole.VIEWER,
            is_active=True,
        )
        db_session.add(user_to_delete)
        await db_session.commit()
        await db_session.refresh(user_to_delete)
        
        response = await api_client.delete(
            f"{API_PREFIX}/{user_to_delete.id}",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_id"] == str(user_to_delete.id)
    
    @pytest.mark.asyncio
    async def test_delete_user_forbidden_for_regular_user(
        self, api_client: AsyncClient, test_user, test_admin, auth_headers
    ):
        """
        DADO: Un usuario normal
        CUANDO: Intenta eliminar a otro usuario
        ENTONCES: Retorna 403 Forbidden
        """
        response = await api_client.delete(
            f"{API_PREFIX}/{test_admin.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 403


# =============================================================================
# Tests de Cambiar Contraseña
# =============================================================================
class TestChangePassword:
    """Tests para PATCH /users/{id}/password."""
    
    @pytest.mark.asyncio
    async def test_change_own_password(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario autenticado
        CUANDO: Cambia su propia contraseña
        ENTONCES: Retorna 200 con confirmación
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_user.id}/password",
            headers=auth_headers,
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePassword456!",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Se proporciona contraseña actual incorrecta
        CUANDO: Se intenta cambiar la contraseña
        ENTONCES: Retorna 400 Bad Request
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_user.id}/password",
            headers=auth_headers,
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewSecurePassword456!",
            },
        )
        
        assert response.status_code == 400


# =============================================================================
# Tests de Activar/Desactivar Usuario
# =============================================================================
class TestActivateUser:
    """Tests para PATCH /users/{id}/activate."""
    
    @pytest.mark.asyncio
    async def test_deactivate_user_as_admin(
        self, api_client: AsyncClient, test_user, admin_auth_headers
    ):
        """
        DADO: Un admin autenticado
        CUANDO: Desactiva un usuario
        ENTONCES: Retorna 200 con usuario desactivado
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_user.id}/activate?is_active=false",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_activate_user_forbidden_for_regular_user(
        self, api_client: AsyncClient, test_user, test_admin, auth_headers
    ):
        """
        DADO: Un usuario normal
        CUANDO: Intenta activar/desactivar a otro
        ENTONCES: Retorna 403 Forbidden
        """
        response = await api_client.patch(
            f"{API_PREFIX}/{test_admin.id}/activate?is_active=false",
            headers=auth_headers,
        )
        
        assert response.status_code == 403
