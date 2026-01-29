# =============================================================================
# NESTSECURE - Tests de Autenticación
# =============================================================================
"""
Tests para los endpoints de autenticación.

Cobertura:
- POST /api/v1/auth/login - Login con OAuth2 form
- POST /api/v1/auth/login/json - Login con JSON
- POST /api/v1/auth/refresh - Refresh token
- GET /api/v1/auth/me - Obtener usuario actual
- POST /api/v1/auth/test-token - Verificar token
"""

import pytest
from httpx import AsyncClient


API_PREFIX = "/api/v1/auth"


# =============================================================================
# Tests de Login (OAuth2 Form)
# =============================================================================
class TestLoginOAuth2:
    """Tests para el endpoint POST /auth/login (OAuth2 form)."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, api_client: AsyncClient, test_user):
        """
        DADO: Un usuario válido existe
        CUANDO: Se hace login con credenciales correctas
        ENTONCES: Retorna 200 con access_token y refresh_token
        """
        response = await api_client.post(
            f"{API_PREFIX}/login",
            data={
                "username": "testuser@example.com",
                "password": "TestPassword123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_email(self, api_client: AsyncClient, test_user):
        """
        DADO: Se intenta login con email inexistente
        CUANDO: Se hace POST a /login
        ENTONCES: Retorna 401 Unauthorized
        """
        response = await api_client.post(
            f"{API_PREFIX}/login",
            data={
                "username": "noexiste@example.com",
                "password": "TestPassword123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, api_client: AsyncClient, test_user):
        """
        DADO: Se intenta login con contraseña incorrecta
        CUANDO: Se hace POST a /login
        ENTONCES: Retorna 401 Unauthorized
        """
        response = await api_client.post(
            f"{API_PREFIX}/login",
            data={
                "username": "testuser@example.com",
                "password": "WrongPassword!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, api_client: AsyncClient, db_session, test_organization):
        """
        DADO: Un usuario inactivo existe
        CUANDO: Se intenta hacer login
        ENTONCES: Retorna 403 Forbidden (usuario deshabilitado)
        """
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        
        # Crear usuario inactivo
        inactive_user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Inactive User",
            organization_id=test_organization.id,
            role=UserRole.VIEWER,
            is_active=False,
        )
        db_session.add(inactive_user)
        await db_session.commit()
        
        response = await api_client.post(
            f"{API_PREFIX}/login",
            data={
                "username": "inactive@example.com",
                "password": "Password123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        # 403 porque el usuario está deshabilitado (diferente de credenciales inválidas)
        assert response.status_code == 403


# =============================================================================
# Tests de Login JSON
# =============================================================================
class TestLoginJSON:
    """Tests para el endpoint POST /auth/login/json."""
    
    @pytest.mark.asyncio
    async def test_login_json_success(self, api_client: AsyncClient, test_user):
        """
        DADO: Un usuario válido existe
        CUANDO: Se hace login con JSON
        ENTONCES: Retorna 200 con tokens y datos del usuario
        """
        response = await api_client.post(
            f"{API_PREFIX}/login/json",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == "testuser@example.com"
    
    @pytest.mark.asyncio
    async def test_login_json_invalid_credentials(self, api_client: AsyncClient, test_user):
        """
        DADO: Se intenta login con credenciales inválidas
        CUANDO: Se hace POST a /login/json
        ENTONCES: Retorna 401 Unauthorized
        """
        response = await api_client.post(
            f"{API_PREFIX}/login/json",
            json={
                "email": "testuser@example.com",
                "password": "WrongPassword!",
            },
        )
        
        assert response.status_code == 401


# =============================================================================
# Tests de Refresh Token
# =============================================================================
class TestRefreshToken:
    """Tests para el endpoint POST /auth/refresh."""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, api_client: AsyncClient, test_user):
        """
        DADO: Un usuario tiene un refresh token válido
        CUANDO: Se solicita renovar el token
        ENTONCES: Retorna nuevos tokens
        """
        # Primero hacer login para obtener refresh_token
        login_response = await api_client.post(
            f"{API_PREFIX}/login/json",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]
        
        # Usar el refresh token
        response = await api_client.post(
            f"{API_PREFIX}/refresh",
            json={"refresh_token": refresh_token},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, api_client: AsyncClient):
        """
        DADO: Se proporciona un refresh token inválido
        CUANDO: Se intenta refrescar
        ENTONCES: Retorna 401 Unauthorized
        """
        response = await api_client.post(
            f"{API_PREFIX}/refresh",
            json={"refresh_token": "invalid-token"},
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, api_client: AsyncClient, test_user):
        """
        DADO: Se intenta usar un access_token como refresh_token
        CUANDO: Se hace POST a /refresh
        ENTONCES: Retorna 401 porque no es un refresh token
        """
        # Obtener tokens
        login_response = await api_client.post(
            f"{API_PREFIX}/login/json",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        login_data = login_response.json()
        access_token = login_data["access_token"]
        
        # Intentar usar access_token como refresh
        response = await api_client.post(
            f"{API_PREFIX}/refresh",
            json={"refresh_token": access_token},
        )
        
        assert response.status_code == 401


# =============================================================================
# Tests de Get Me
# =============================================================================
class TestGetMe:
    """Tests para el endpoint GET /auth/me."""
    
    @pytest.mark.asyncio
    async def test_get_me_success(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario autenticado
        CUANDO: Se solicita GET /me
        ENTONCES: Retorna los datos del usuario
        """
        response = await api_client.get(
            f"{API_PREFIX}/me",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["full_name"] == "Test User"
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_get_me_without_token(self, api_client: AsyncClient):
        """
        DADO: No se proporciona token
        CUANDO: Se hace GET a /me
        ENTONCES: Retorna 401 Unauthorized
        """
        response = await api_client.get(f"{API_PREFIX}/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, api_client: AsyncClient):
        """
        DADO: Se proporciona un token inválido
        CUANDO: Se hace GET a /me
        ENTONCES: Retorna 401 Unauthorized
        """
        response = await api_client.get(
            f"{API_PREFIX}/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        
        assert response.status_code == 401


# =============================================================================
# Tests de Test Token
# =============================================================================
class TestTestToken:
    """Tests para el endpoint POST /auth/test-token."""
    
    @pytest.mark.asyncio
    async def test_test_token_valid(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un token válido
        CUANDO: Se hace POST a /test-token
        ENTONCES: Retorna los datos del usuario
        """
        response = await api_client.post(
            f"{API_PREFIX}/test-token",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
    
    @pytest.mark.asyncio
    async def test_test_token_expired(self, api_client: AsyncClient, test_user):
        """
        DADO: Un token expirado
        CUANDO: Se hace POST a /test-token
        ENTONCES: Retorna 401 Unauthorized
        """
        from app.core.security import create_access_token
        from datetime import timedelta
        
        # Crear token expirado
        expired_token = create_access_token(
            subject=str(test_user.id),
            expires_delta=timedelta(minutes=-10),  # Expirado hace 10 minutos
        )
        
        response = await api_client.post(
            f"{API_PREFIX}/test-token",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        
        assert response.status_code == 401


# =============================================================================
# Tests de Seguridad
# =============================================================================
class TestAuthSecurity:
    """Tests de seguridad para autenticación."""
    
    @pytest.mark.asyncio
    async def test_password_not_in_response(
        self, api_client: AsyncClient, test_user, auth_headers
    ):
        """
        DADO: Un usuario autenticado
        CUANDO: Se obtienen sus datos
        ENTONCES: La contraseña hash no se incluye
        """
        response = await api_client.get(
            f"{API_PREFIX}/me",
            headers=auth_headers,
        )
        
        data = response.json()
        assert "hashed_password" not in data
        assert "password" not in data
    
    @pytest.mark.asyncio
    async def test_token_includes_user_claims(self, api_client: AsyncClient, test_user):
        """
        DADO: Un login exitoso
        CUANDO: Se decodifica el token
        ENTONCES: Contiene los claims esperados
        """
        from app.core.security import decode_token
        
        response = await api_client.post(
            f"{API_PREFIX}/login/json",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        
        data = response.json()
        payload = decode_token(data["access_token"])
        
        assert payload is not None
        assert payload.get("sub") == str(test_user.id)
        assert payload.get("type") == "access"
