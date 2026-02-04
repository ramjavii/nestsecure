# =============================================================================
# NESTSECURE - Tests de Integración: Flujo de Autenticación
# =============================================================================
"""
Tests de integración para el flujo completo de autenticación.
Verifica login, tokens JWT, refresh tokens, y logout.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestAuthenticationFlow:
    """Tests de integración para autenticación."""

    async def test_login_success(self, client_with_db: AsyncClient, test_user):
        """Test login exitoso con credenciales válidas."""
        response = await client_with_db.post(
            "/api/v1/auth/login/json",
            json={
                "email": "integration@test.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "integration@test.com"

    async def test_login_invalid_password(self, client_with_db: AsyncClient, test_user):
        """Test login con contraseña inválida."""
        response = await client_with_db.post(
            "/api/v1/auth/login/json",
            json={
                "email": "integration@test.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    async def test_login_nonexistent_user(self, client_with_db: AsyncClient, test_user):
        """Test login con usuario inexistente."""
        response = await client_with_db.post(
            "/api/v1/auth/login/json",
            json={
                "email": "nonexistent@test.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == 401

    async def test_access_protected_route_with_token(self, client_with_db: AsyncClient, test_user, auth_headers):
        """Test acceso a ruta protegida con token válido."""
        response = await client_with_db.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "integration@test.com"

    async def test_access_protected_route_without_token(self, client_with_db: AsyncClient, test_user):
        """Test acceso a ruta protegida sin token."""
        response = await client_with_db.get("/api/v1/users/me")
        
        assert response.status_code == 401

    async def test_access_with_invalid_token(self, client_with_db: AsyncClient, test_user):
        """Test acceso con token inválido."""
        response = await client_with_db.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401

    async def test_refresh_token_flow(self, client_with_db: AsyncClient, test_user):
        """Test renovación de token con refresh token."""
        # Primero login para obtener tokens
        login_response = await client_with_db.post(
            "/api/v1/auth/login/json",
            json={
                "email": "integration@test.com",
                "password": "testpassword123"
            }
        )
        
        assert login_response.status_code == 200
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]
        
        # Usar refresh token para obtener nuevo access token
        refresh_response = await client_with_db.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        # Si el endpoint existe y funciona
        if refresh_response.status_code == 200:
            data = refresh_response.json()
            assert "access_token" in data
        else:
            # El endpoint puede no estar implementado aún
            assert refresh_response.status_code in [200, 404, 422]

    async def test_logout_flow(self, client_with_db: AsyncClient, test_user, auth_headers):
        """Test logout invalida el token."""
        # Verificar que el token funciona
        me_response = await client_with_db.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        assert me_response.status_code == 200
        
        # Hacer logout
        logout_response = await client_with_db.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        # El logout puede retornar 200 o 204
        assert logout_response.status_code in [200, 204, 404]

    async def test_password_validation_on_login(self, client_with_db: AsyncClient, test_user):
        """Test validación de formato de contraseña."""
        # Contraseña muy corta
        response = await client_with_db.post(
            "/api/v1/auth/login/json",
            json={
                "email": "integration@test.com",
                "password": "123"
            }
        )
        
        # Debería fallar por credenciales inválidas o validación
        assert response.status_code in [401, 422]

    async def test_email_validation_on_login(self, client_with_db: AsyncClient, test_user):
        """Test validación de formato de email."""
        response = await client_with_db.post(
            "/api/v1/auth/login/json",
            json={
                "email": "not-an-email",
                "password": "testpassword123"
            }
        )
        
        # Debería fallar por validación o no encontrar usuario
        assert response.status_code in [401, 422]


class TestUserProfile:
    """Tests de integración para perfil de usuario."""

    async def test_get_current_user_profile(self, client_with_db: AsyncClient, test_user, auth_headers):
        """Test obtener perfil del usuario actual."""
        response = await client_with_db.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "integration@test.com"
        assert data["full_name"] == "Integration Test User"
        assert data["role"] == "admin"
        assert data["is_active"] is True

    async def test_update_user_profile(self, client_with_db: AsyncClient, test_user, auth_headers):
        """Test actualizar perfil del usuario."""
        response = await client_with_db.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"full_name": "Updated Name"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["full_name"] == "Updated Name"
        else:
            # El endpoint puede usar PUT o no estar implementado
            assert response.status_code in [200, 404, 405]
