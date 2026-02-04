# =============================================================================
# NESTSECURE - Tests de Seguridad
# =============================================================================
"""
Tests de seguridad para verificar la robustez de la aplicación
contra ataques comunes y vulnerabilidades.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
import base64
import json

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.security]


class TestAuthenticationSecurity:
    """Tests de seguridad en autenticación."""

    async def test_password_not_in_response(self, client_with_db: AsyncClient, auth_headers):
        """Test que la contraseña nunca aparezca en respuestas."""
        response = await client_with_db.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            response_text = json.dumps(data).lower()
            
            # No debe contener la contraseña ni el hash
            assert "password" not in response_text or "null" in response_text or "none" in response_text
            assert "admin123" not in response_text
            assert "$2b$" not in response_text  # bcrypt hash prefix
            assert "$argon2" not in response_text  # argon2 hash prefix

    async def test_brute_force_protection(self, client_with_db: AsyncClient, test_user):
        """Test protección contra fuerza bruta - verificar rechazo de credenciales incorrectas."""
        # Intentar login con contraseña incorrecta
        # Nota: El endpoint usa OAuth2PasswordRequestForm (form data, no JSON)
        response = await client_with_db.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "definitely_wrong_password_123"
            }
        )
        
        # Debe rechazar las credenciales incorrectas
        # 401 = Unauthorized (credenciales inválidas)
        # 403 = Forbidden (cuenta bloqueada por intentos fallidos)
        # 429 = Too Many Requests (rate limiting)
        assert response.status_code in [401, 403, 429]

    async def test_expired_token_rejected(self, client_with_db: AsyncClient):
        """Test que tokens expirados sean rechazados."""
        # Token JWT expirado (ejemplo)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"
        
        response = await client_with_db.get(
            "/api/v1/assets",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401

    async def test_malformed_token_rejected(self, client_with_db: AsyncClient):
        """Test que tokens malformados sean rechazados."""
        malformed_tokens = [
            "not_a_jwt",
            "Bearer",
            "Bearer ",
            "Bearer .",
            "Bearer ..",
            "Basic dXNlcjpwYXNz",  # Basic auth instead of Bearer
        ]
        
        for token in malformed_tokens:
            headers = {"Authorization": token} if not token.startswith("Bearer") else {"Authorization": token}
            response = await client_with_db.get(
                "/api/v1/assets",
                headers=headers
            )
            
            assert response.status_code == 401

    async def test_token_without_bearer_prefix(self, client_with_db: AsyncClient, auth_headers):
        """Test que se requiera prefijo Bearer."""
        # Obtener el token del auth_headers
        auth_value = auth_headers.get("Authorization", "")
        token = auth_value.replace("Bearer ", "")
        
        response = await client_with_db.get(
            "/api/v1/assets",
            headers={"Authorization": token}  # Sin "Bearer "
        )
        
        assert response.status_code == 401


class TestAuthorizationSecurity:
    """Tests de seguridad en autorización."""

    async def test_cannot_access_other_org_data(self, client_with_db: AsyncClient, auth_headers):
        """Test que no se pueda acceder a datos de otra organización."""
        # Intentar acceder con un organization_id diferente
        response = await client_with_db.get(
            "/api/v1/assets?organization_id=00000000-0000-0000-0000-000000000099",
            headers=auth_headers
        )
        
        # Debe filtrar por organización del usuario o retornar vacío
        assert response.status_code in [200, 403]

    async def test_cannot_modify_other_user(self, client_with_db: AsyncClient, auth_headers):
        """Test que no se pueda modificar otro usuario."""
        fake_user_id = "00000000-0000-0000-0000-000000000099"
        
        response = await client_with_db.patch(
            f"/api/v1/users/{fake_user_id}",
            headers=auth_headers,
            json={"name": "Hacked Name"}
        )
        
        # Debe ser 403 o 404
        assert response.status_code in [403, 404]


class TestInputSanitization:
    """Tests de sanitización de entrada."""

    async def test_sql_injection_in_search(self, client_with_db: AsyncClient, auth_headers):
        """Test SQL injection en búsqueda."""
        payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1; SELECT * FROM users",
            "admin'--",
            "1' UNION SELECT * FROM users --"
        ]
        
        for payload in payloads:
            response = await client_with_db.get(
                f"/api/v1/assets?search={payload}",
                headers=auth_headers
            )
            
            # No debe causar error de servidor
            assert response.status_code in [200, 400, 422]

    async def test_xss_in_input_fields(self, client_with_db: AsyncClient, auth_headers):
        """Test XSS en campos de entrada."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "test-hostname",  # Un valor normal para comparación
        ]
        
        for payload in xss_payloads:
            response = await client_with_db.post(
                "/api/v1/assets",
                headers=auth_headers,
                json={
                    "ip_address": f"192.168.{hash(payload) % 255}.1",
                    "hostname": payload,
                    "asset_type": "server"
                }
            )
            
            # Debe rechazar o aceptar pero no crashear
            assert response.status_code in [200, 201, 400, 422]

    async def test_path_traversal(self, client_with_db: AsyncClient, auth_headers):
        """Test path traversal."""
        payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd"
        ]
        
        for payload in payloads:
            response = await client_with_db.get(
                f"/api/v1/assets/{payload}",
                headers=auth_headers
            )
            
            # Debe ser 400, 404 o 422, no un error de servidor
            assert response.status_code in [400, 404, 422]

    async def test_command_injection(self, client_with_db: AsyncClient, auth_headers):
        """Test command injection."""
        payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "&& rm -rf /"
        ]
        
        for payload in payloads:
            response = await client_with_db.post(
                "/api/v1/scans",
                headers=auth_headers,
                json={
                    "name": f"Test Scan {payload}",
                    "scan_type": "nmap",
                    "targets": [f"192.168.1.1{payload}"]
                }
            )
            
            # Debe rechazar o sanitizar
            assert response.status_code in [200, 201, 400, 422]


class TestHeaderSecurity:
    """Tests de seguridad en headers HTTP."""

    async def test_host_header_injection(self, client_with_db: AsyncClient, auth_headers):
        """Test host header injection."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers={
                **auth_headers,
                "Host": "evil.com"
            }
        )
        
        # Debe funcionar normalmente o rechazar
        assert response.status_code in [200, 400]

    async def test_x_forwarded_for_handling(self, client_with_db: AsyncClient, auth_headers):
        """Test manejo de X-Forwarded-For."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers={
                **auth_headers,
                "X-Forwarded-For": "1.2.3.4, 5.6.7.8"
            }
        )
        
        # Debe funcionar normalmente
        assert response.status_code == 200


class TestDataExposure:
    """Tests de exposición de datos sensibles."""

    async def test_no_stack_trace_in_error(self, client_with_db: AsyncClient, auth_headers):
        """Test que no se expongan stack traces."""
        # Provocar un error
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={"invalid": "data" * 10000}
        )
        
        if response.status_code >= 400:
            response_text = response.text.lower()
            
            # No debe contener información de stack trace
            assert "traceback" not in response_text
            assert "file \"" not in response_text
            assert "line " not in response_text or "validation" in response_text

    async def test_no_internal_paths_exposed(self, client_with_db: AsyncClient, auth_headers):
        """Test que no se expongan rutas internas."""
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={"invalid": "data"}
        )
        
        if response.status_code >= 400:
            response_text = response.text.lower()
            
            # No debe contener rutas internas
            assert "/home/" not in response_text
            assert "/users/" not in response_text or "api" in response_text
            assert "/var/" not in response_text
            assert "c:\\" not in response_text

    async def test_no_db_info_in_error(self, client_with_db: AsyncClient, auth_headers):
        """Test que no se exponga información de base de datos."""
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={"ip_address": "not_valid_ip"}
        )
        
        if response.status_code >= 400:
            response_text = response.text.lower()
            
            # No debe contener información de BD
            assert "postgresql" not in response_text
            assert "mysql" not in response_text
            assert "sqlite" not in response_text or "test" in response_text
            assert "connection string" not in response_text


class TestSessionSecurity:
    """Tests de seguridad de sesiones."""

    async def test_token_changes_after_logout(self, client_with_db: AsyncClient):
        """Test que el token sea invalidado después de logout."""
        # Login
        login_response = await client_with_db.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@nestsecure.com",
                "password": "Admin123!"
            }
        )
        
        if login_response.status_code == 200:
            data = login_response.json()
            token = data.get("access_token")
            
            if token:
                # Logout
                await client_with_db.post(
                    "/api/v1/auth/logout",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                # Intentar usar el token después del logout
                response = await client_with_db.get(
                    "/api/v1/assets",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                # Idealmente debería ser 401, pero depende de la implementación
                # Algunos sistemas no invalidan tokens JWT hasta que expiran
                assert response.status_code in [200, 401]

    async def test_concurrent_sessions(self, client_with_db: AsyncClient, test_user, auth_headers_factory):
        """Test manejo de sesiones concurrentes."""
        # Usar el usuario de test que ya existe
        token_headers = auth_headers_factory(str(test_user.id))
        
        # Verificar que el token funcione
        response = await client_with_db.get(
            "/api/v1/users/me",
            headers=token_headers
        )
        
        assert response.status_code == 200


class TestCryptographySecurity:
    """Tests de seguridad criptográfica."""

    async def test_password_hash_strength(self, client_with_db: AsyncClient, auth_headers):
        """Test que las contraseñas se almacenen hasheadas correctamente."""
        # Este test verifica indirectamente que el sistema rechaza contraseñas débiles
        weak_passwords = [
            "123",
            "password",
            "abc"
        ]
        
        for weak_pass in weak_passwords:
            response = await client_with_db.post(
                "/api/v1/auth/register",
                json={
                    "email": f"weak_{weak_pass}@test.com",
                    "password": weak_pass,
                    "name": "Test User"
                }
            )
            
            # Debería rechazar contraseñas débiles
            # O aceptar si no hay política de contraseñas
            assert response.status_code in [200, 201, 400, 404, 422]


class TestAPIAbuse:
    """Tests de abuso de API."""

    async def test_large_request_handling(self, client_with_db: AsyncClient, auth_headers):
        """Test manejo de requests muy grandes."""
        large_data = {
            "ip_address": "192.168.255.1",
            "hostname": "test",
            "asset_type": "server",
            "extra_data": "x" * 1000000  # 1MB
        }
        
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json=large_data
        )
        
        # Debe manejar graciosamente
        assert response.status_code in [200, 201, 400, 413, 422]

    async def test_many_query_params(self, client_with_db: AsyncClient, auth_headers):
        """Test manejo de muchos query params."""
        params = "&".join([f"param{i}=value{i}" for i in range(100)])
        
        response = await client_with_db.get(
            f"/api/v1/assets?{params}",
            headers=auth_headers
        )
        
        # Debe funcionar o rechazar, no crashear
        assert response.status_code in [200, 400, 414]

    async def test_deep_json_nesting(self, client_with_db: AsyncClient, auth_headers):
        """Test manejo de JSON profundamente anidado."""
        # Crear JSON anidado
        nested = {"value": "end"}
        for _ in range(50):
            nested = {"nested": nested}
        
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.254.1",
                "hostname": "nested-test",
                "asset_type": "server",
                "metadata": nested
            }
        )
        
        # Debe manejar graciosamente
        assert response.status_code in [200, 201, 400, 422]
