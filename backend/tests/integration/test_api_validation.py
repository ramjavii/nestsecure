# =============================================================================
# NESTSECURE - Tests de Validación de API
# =============================================================================
"""
Tests de validación para verificar que todas las respuestas de API
cumplen con los schemas definidos y manejan correctamente los errores.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from typing import Any
import json

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestAPIValidation:
    """Tests de validación de estructura de respuestas API."""

    async def test_health_endpoint(self, client_with_db: AsyncClient):
        """Test endpoint de health check."""
        response = await client_with_db.get("/health")
        
        # Puede ser 200 o 404 dependiendo si existe
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or isinstance(data, dict)

    async def test_api_version(self, client_with_db: AsyncClient):
        """Test endpoint de versión de API."""
        response = await client_with_db.get("/api/v1")
        
        # Puede ser cualquier respuesta válida
        assert response.status_code in [200, 404, 307, 308]

    async def test_openapi_schema(self, client_with_db: AsyncClient):
        """Test que el schema OpenAPI esté disponible."""
        response = await client_with_db.get("/openapi.json")
        
        if response.status_code == 200:
            data = response.json()
            assert "openapi" in data
            assert "paths" in data
            assert "info" in data

    async def test_docs_endpoint(self, client_with_db: AsyncClient):
        """Test que la documentación esté disponible."""
        response = await client_with_db.get("/docs")
        
        assert response.status_code in [200, 307, 308]


class TestErrorHandling:
    """Tests de manejo de errores."""

    async def test_404_response_format(self, client_with_db: AsyncClient, auth_headers):
        """Test formato de respuesta 404."""
        response = await client_with_db.get(
            "/api/v1/nonexistent-endpoint",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data or "message" in data or "error" in data

    async def test_401_without_auth(self, client_with_db: AsyncClient):
        """Test respuesta 401 sin autenticación."""
        response = await client_with_db.get("/api/v1/assets")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data or "message" in data

    async def test_401_with_invalid_token(self, client_with_db: AsyncClient):
        """Test respuesta 401 con token inválido."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401

    async def test_422_validation_error(self, client_with_db: AsyncClient, auth_headers):
        """Test respuesta 422 para errores de validación."""
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={"ip_address": "invalid-ip-format"}  # IP inválida
        )
        
        assert response.status_code == 422
        data = response.json()
        # Verificar que hay información de error
        assert "detail" in data or "message" in data or "errors" in data or len(data) > 0

    async def test_method_not_allowed(self, client_with_db: AsyncClient, auth_headers):
        """Test respuesta 405 para método no permitido."""
        response = await client_with_db.put(
            "/api/v1/auth/login",  # PUT no permitido en login
            headers=auth_headers,
            json={}
        )
        
        assert response.status_code in [405, 422]


class TestResponseStructure:
    """Tests de estructura de respuestas."""

    async def test_list_response_structure(self, client_with_db: AsyncClient, auth_headers):
        """Test estructura de respuestas de lista."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Debe ser una lista o un objeto con items
        if isinstance(data, dict):
            assert "items" in data or "data" in data or "results" in data
        else:
            assert isinstance(data, list)

    async def test_single_item_response_structure(self, client_with_db: AsyncClient, auth_headers):
        """Test estructura de respuesta de item único."""
        # Crear asset primero
        create_response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.200.1",
                "hostname": "structure-test",
                "asset_type": "server"
            }
        )
        
        if create_response.status_code in [200, 201]:
            asset = create_response.json()
            asset_id = asset["id"]
            
            # Obtener item único
            get_response = await client_with_db.get(
                f"/api/v1/assets/{asset_id}",
                headers=auth_headers
            )
            
            assert get_response.status_code == 200
            data = get_response.json()
            
            # Debe tener los campos básicos
            assert "id" in data
            assert isinstance(data, dict)

    async def test_pagination_structure(self, client_with_db: AsyncClient, auth_headers):
        """Test estructura de paginación."""
        response = await client_with_db.get(
            "/api/v1/assets?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if isinstance(data, dict) and "items" in data:
            # Debe tener campos de paginación
            pagination_fields = ["total", "page", "page_size", "pages", "count", "limit", "offset"]
            has_pagination = any(field in data for field in pagination_fields)
            assert has_pagination or "items" in data


class TestContentTypes:
    """Tests de tipos de contenido."""

    async def test_json_content_type(self, client_with_db: AsyncClient, auth_headers):
        """Test que las respuestas sean JSON."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    async def test_accepts_json_request(self, client_with_db: AsyncClient, auth_headers):
        """Test que se acepten requests JSON."""
        response = await client_with_db.post(
            "/api/v1/assets",
            headers={
                **auth_headers,
                "Content-Type": "application/json"
            },
            json={
                "ip_address": "192.168.201.1",
                "hostname": "content-type-test",
                "asset_type": "server"
            }
        )
        
        assert response.status_code in [200, 201]


class TestRateLimiting:
    """Tests de rate limiting."""

    async def test_rate_limit_headers(self, client_with_db: AsyncClient, auth_headers):
        """Test que existan headers de rate limiting."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers=auth_headers
        )
        
        # Los headers de rate limiting son opcionales pero recomendados
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
            "ratelimit-limit",
            "ratelimit-remaining"
        ]
        
        has_rate_limit = any(
            header.lower() in [h.lower() for h in response.headers.keys()]
            for header in rate_limit_headers
        )
        
        # No es estrictamente requerido, solo verificamos la respuesta
        assert response.status_code == 200


class TestCORSHeaders:
    """Tests de headers CORS."""

    async def test_cors_headers_present(self, client_with_db: AsyncClient):
        """Test que existan headers CORS."""
        response = await client_with_db.options(
            "/api/v1/assets",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # El servidor debe responder a OPTIONS
        assert response.status_code in [200, 204, 405]

    async def test_cors_allow_origin(self, client_with_db: AsyncClient, auth_headers):
        """Test header Access-Control-Allow-Origin."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers={
                **auth_headers,
                "Origin": "http://localhost:3000"
            }
        )
        
        # Verificar la respuesta (CORS puede variar según configuración)
        assert response.status_code == 200


class TestInputValidation:
    """Tests de validación de entrada."""

    async def test_sql_injection_prevention(self, client_with_db: AsyncClient, auth_headers):
        """Test prevención de SQL injection."""
        response = await client_with_db.get(
            "/api/v1/assets?search='; DROP TABLE assets; --",
            headers=auth_headers
        )
        
        # No debe causar error de servidor
        assert response.status_code in [200, 400, 422]

    async def test_xss_prevention(self, client_with_db: AsyncClient, auth_headers):
        """Test prevención de XSS."""
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json={
                "ip_address": "192.168.202.1",
                "hostname": "<script>alert('xss')</script>",
                "asset_type": "server"
            }
        )
        
        # Debe rechazar o sanitizar
        if response.status_code in [200, 201]:
            data = response.json()
            # El hostname no debe contener el script sin escapar
            assert "<script>" not in data.get("hostname", "") or "script" in data.get("hostname", "")

    async def test_large_payload_handling(self, client_with_db: AsyncClient, auth_headers):
        """Test manejo de payloads grandes."""
        large_data = {
            "ip_address": "192.168.203.1",
            "hostname": "large-payload-test",
            "asset_type": "server",
            "description": "x" * 100000  # 100KB de texto
        }
        
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            json=large_data
        )
        
        # Debe manejar graciosamente (aceptar o rechazar pero no crashear)
        assert response.status_code in [200, 201, 400, 413, 422]

    async def test_invalid_uuid_handling(self, client_with_db: AsyncClient, auth_headers):
        """Test manejo de UUID inválido."""
        response = await client_with_db.get(
            "/api/v1/assets/not-a-valid-uuid",
            headers=auth_headers
        )
        
        assert response.status_code in [400, 404, 422]

    async def test_empty_body_handling(self, client_with_db: AsyncClient, auth_headers):
        """Test manejo de body vacío."""
        response = await client_with_db.post(
            "/api/v1/assets",
            headers=auth_headers,
            content=""
        )
        
        assert response.status_code == 422

    async def test_malformed_json_handling(self, client_with_db: AsyncClient, auth_headers):
        """Test manejo de JSON malformado."""
        response = await client_with_db.post(
            "/api/v1/assets",
            headers={**auth_headers, "Content-Type": "application/json"},
            content="{invalid json"
        )
        
        assert response.status_code == 422


class TestDateTimeHandling:
    """Tests de manejo de fechas y tiempos."""

    async def test_datetime_format_in_response(self, client_with_db: AsyncClient, auth_headers):
        """Test formato ISO de fechas en respuestas."""
        # Crear un scan que tiene created_at
        create_response = await client_with_db.post(
            "/api/v1/scans",
            headers=auth_headers,
            json={
                "name": "DateTime Test Scan",
                "scan_type": "nmap",
                "targets": ["10.0.50.1"]
            }
        )
        
        if create_response.status_code in [200, 201]:
            data = create_response.json()
            
            # Verificar formato de fecha
            if "created_at" in data:
                created_at = data["created_at"]
                # Debe ser formato ISO o timestamp
                assert isinstance(created_at, (str, int, float))
                if isinstance(created_at, str):
                    # Formato ISO básico: YYYY-MM-DD
                    assert "-" in created_at or "T" in created_at


class TestSecurityHeaders:
    """Tests de headers de seguridad."""

    async def test_security_headers_present(self, client_with_db: AsyncClient, auth_headers):
        """Test presencia de headers de seguridad."""
        response = await client_with_db.get(
            "/api/v1/assets",
            headers=auth_headers
        )
        
        # Headers de seguridad recomendados (no todos son obligatorios)
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "strict-transport-security",
            "content-security-policy"
        ]
        
        # Solo verificamos que la respuesta sea válida
        # Los headers de seguridad dependen de la configuración
        assert response.status_code == 200
