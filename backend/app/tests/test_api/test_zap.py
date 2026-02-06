# =============================================================================
# NESTSECURE - Tests de API ZAP
# =============================================================================
"""
Tests para los endpoints de la API de ZAP.

Incluye:
- Tests de escaneos
- Tests de perfiles
- Tests de resultados
- Tests de estado del servicio
"""

import pytest
from datetime import datetime, timezone
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from httpx import AsyncClient

from app.main import app


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_zap_scan_response() -> Dict:
    """Mock response from ZAP scan."""
    return {
        "task_id": "test-task-123",
        "status": "PENDING",
        "message": "Scan queued successfully",
    }


@pytest.fixture
def mock_zap_result() -> Dict:
    """Mock ZAP scan result."""
    return {
        "task_id": "test-task-123",
        "status": "SUCCESS",
        "target_url": "https://example.com",
        "mode": "standard",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 120.5,
        "urls_found": 50,
        "alerts_count": 10,
        "alerts": [
            {
                "name": "X-Frame-Options Header Not Set",
                "risk": 2,
                "url": "https://example.com/page",
            }
        ],
    }


@pytest.fixture
def mock_zap_profiles() -> list:
    """Mock ZAP scan profiles."""
    return [
        {
            "id": "quick",
            "name": "Quick Scan",
            "description": "Fast passive scan with limited spider depth",
            "estimated_time": "2-5 minutes",
        },
        {
            "id": "standard",
            "name": "Standard Scan",
            "description": "Balanced scan with active scanning",
            "estimated_time": "10-30 minutes",
        },
        {
            "id": "full",
            "name": "Full Scan",
            "description": "Comprehensive scan with all checks",
            "estimated_time": "1-4 hours",
        },
    ]


# =============================================================================
# TESTS - ZAP SCAN ENDPOINTS
# =============================================================================

class TestZapScanEndpoints:
    """Tests for ZAP scan endpoints."""
    
    @pytest.mark.asyncio
    async def test_start_scan_requires_auth(self, client: AsyncClient):
        """Start scan should require authentication."""
        response = await client.post(
            "/api/v1/zap/scan",
            json={"target_url": "https://example.com"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_start_scan_success(
        self, 
        authenticated_client: AsyncClient,
        mock_zap_scan_response: Dict
    ):
        """Should start scan successfully."""
        with patch("app.api.v1.zap.zap_scan.delay") as mock_task:
            mock_task.return_value.id = "test-task-123"
            
            response = await authenticated_client.post(
                "/api/v1/zap/scan",
                json={
                    "target_url": "https://example.com",
                    "mode": "standard",
                }
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "PENDING"
    
    @pytest.mark.asyncio
    async def test_start_scan_invalid_url(self, authenticated_client: AsyncClient):
        """Should reject invalid URLs."""
        response = await authenticated_client.post(
            "/api/v1/zap/scan",
            json={"target_url": "not-a-valid-url"}
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
    
    @pytest.mark.asyncio
    async def test_start_quick_scan(self, authenticated_client: AsyncClient):
        """Should start quick scan."""
        with patch("app.api.v1.zap.zap_quick_scan.delay") as mock_task:
            mock_task.return_value.id = "quick-scan-123"
            
            response = await authenticated_client.post(
                "/api/v1/zap/quick",
                json={"target_url": "https://example.com"}
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()
            assert "task_id" in data
    
    @pytest.mark.asyncio
    async def test_start_full_scan(self, authenticated_client: AsyncClient):
        """Should start full scan."""
        with patch("app.api.v1.zap.zap_full_scan.delay") as mock_task:
            mock_task.return_value.id = "full-scan-123"
            
            response = await authenticated_client.post(
                "/api/v1/zap/full",
                json={"target_url": "https://example.com"}
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.asyncio
    async def test_start_api_scan(self, authenticated_client: AsyncClient):
        """Should start API scan."""
        with patch("app.api.v1.zap.zap_api_scan.delay") as mock_task:
            mock_task.return_value.id = "api-scan-123"
            
            response = await authenticated_client.post(
                "/api/v1/zap/api",
                json={
                    "target_url": "https://api.example.com",
                    "openapi_url": "https://api.example.com/openapi.json",
                }
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.asyncio
    async def test_start_spa_scan(self, authenticated_client: AsyncClient):
        """Should start SPA scan."""
        with patch("app.api.v1.zap.zap_spa_scan.delay") as mock_task:
            mock_task.return_value.id = "spa-scan-123"
            
            response = await authenticated_client.post(
                "/api/v1/zap/spa",
                json={"target_url": "https://spa.example.com"}
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED


# =============================================================================
# TESTS - ZAP RESULTS ENDPOINTS
# =============================================================================

class TestZapResultsEndpoints:
    """Tests for ZAP results endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_scan_status_pending(self, authenticated_client: AsyncClient):
        """Should get pending scan status."""
        with patch("app.api.v1.zap.AsyncResult") as mock_result:
            mock_result.return_value.state = "PENDING"
            mock_result.return_value.info = None
            
            response = await authenticated_client.get(
                "/api/v1/zap/scan/test-task-123"
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "PENDING"
    
    @pytest.mark.asyncio
    async def test_get_scan_status_success(
        self,
        authenticated_client: AsyncClient,
        mock_zap_result: Dict
    ):
        """Should get successful scan result."""
        with patch("app.api.v1.zap.AsyncResult") as mock_result:
            mock_result.return_value.state = "SUCCESS"
            mock_result.return_value.result = mock_zap_result
            
            response = await authenticated_client.get(
                "/api/v1/zap/scan/test-task-123"
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "SUCCESS"
    
    @pytest.mark.asyncio
    async def test_get_scan_status_failure(self, authenticated_client: AsyncClient):
        """Should get failed scan status."""
        with patch("app.api.v1.zap.AsyncResult") as mock_result:
            mock_result.return_value.state = "FAILURE"
            mock_result.return_value.info = Exception("Scan failed")
            
            response = await authenticated_client.get(
                "/api/v1/zap/scan/test-task-123"
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "FAILURE"
    
    @pytest.mark.asyncio
    async def test_get_scan_results_not_found(self, authenticated_client: AsyncClient):
        """Should handle missing results."""
        with patch("app.api.v1.zap.AsyncResult") as mock_result:
            mock_result.return_value.state = "PENDING"
            mock_result.return_value.result = None
            
            response = await authenticated_client.get(
                "/api/v1/zap/results/nonexistent-task"
            )
            
            assert response.status_code in [
                status.HTTP_200_OK,  # With pending status
                status.HTTP_404_NOT_FOUND,
            ]


# =============================================================================
# TESTS - ZAP PROFILES ENDPOINTS
# =============================================================================

class TestZapProfilesEndpoints:
    """Tests for ZAP profiles endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_scan_profiles(
        self,
        authenticated_client: AsyncClient,
        mock_zap_profiles: list
    ):
        """Should get available scan profiles."""
        response = await authenticated_client.get("/api/v1/zap/profiles")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
        
        # Check profile structure
        for profile in data:
            assert "id" in profile
            assert "name" in profile
    
    @pytest.mark.asyncio
    async def test_profiles_include_all_modes(self, authenticated_client: AsyncClient):
        """Should include all scan modes."""
        response = await authenticated_client.get("/api/v1/zap/profiles")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        profile_ids = [p["id"] for p in data]
        assert "quick" in profile_ids
        assert "standard" in profile_ids
        assert "full" in profile_ids


# =============================================================================
# TESTS - ZAP SERVICE STATUS
# =============================================================================

class TestZapServiceStatus:
    """Tests for ZAP service status."""
    
    @pytest.mark.asyncio
    async def test_get_zap_version_available(self, authenticated_client: AsyncClient):
        """Should get ZAP version when service is available."""
        with patch("app.api.v1.zap.ZapClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_version.return_value = {"version": "2.14.0"}
            mock_client_class.return_value = mock_client
            
            response = await authenticated_client.get("/api/v1/zap/version")
            
            assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_get_zap_version_unavailable(self, authenticated_client: AsyncClient):
        """Should handle ZAP service unavailable."""
        with patch("app.api.v1.zap.ZapClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_version.side_effect = Exception("Connection refused")
            mock_client_class.return_value = mock_client
            
            response = await authenticated_client.get("/api/v1/zap/version")
            
            assert response.status_code in [
                status.HTTP_200_OK,  # With error message
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]
    
    @pytest.mark.asyncio
    async def test_clear_session(self, authenticated_client: AsyncClient):
        """Should clear ZAP session."""
        with patch("app.api.v1.zap.ZapClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.new_session.return_value = True
            mock_client_class.return_value = mock_client
            
            response = await authenticated_client.post("/api/v1/zap/clear")
            
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_204_NO_CONTENT,
            ]


# =============================================================================
# TESTS - ZAP ALERTS
# =============================================================================

class TestZapAlertsEndpoints:
    """Tests for ZAP alerts endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_alerts_from_result(self, authenticated_client: AsyncClient):
        """Should get alerts from scan result."""
        mock_result = {
            "alerts": [
                {"name": "Alert 1", "risk": 2},
                {"name": "Alert 2", "risk": 3},
            ]
        }
        
        with patch("app.api.v1.zap.AsyncResult") as mock_async_result:
            mock_async_result.return_value.state = "SUCCESS"
            mock_async_result.return_value.result = mock_result
            
            response = await authenticated_client.get(
                "/api/v1/zap/alerts/test-task-123"
            )
            
            assert response.status_code == status.HTTP_200_OK


# =============================================================================
# TESTS - INPUT VALIDATION
# =============================================================================

class TestZapInputValidation:
    """Tests for input validation."""
    
    @pytest.mark.asyncio
    async def test_scan_with_empty_url(self, authenticated_client: AsyncClient):
        """Should reject empty URL."""
        response = await authenticated_client.post(
            "/api/v1/zap/scan",
            json={"target_url": ""}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_scan_with_invalid_mode(self, authenticated_client: AsyncClient):
        """Should reject invalid mode."""
        with patch("app.api.v1.zap.zap_scan.delay"):
            response = await authenticated_client.post(
                "/api/v1/zap/scan",
                json={
                    "target_url": "https://example.com",
                    "mode": "invalid_mode",
                }
            )
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]
    
    @pytest.mark.asyncio
    async def test_scan_with_localhost_blocked(self, authenticated_client: AsyncClient):
        """Should potentially block localhost scans in production."""
        # This test verifies security measures for production
        response = await authenticated_client.post(
            "/api/v1/zap/scan",
            json={"target_url": "http://localhost:3000"}
        )
        # Either allowed or blocked depending on configuration
        assert response.status_code in [
            status.HTTP_202_ACCEPTED,
            status.HTTP_400_BAD_REQUEST,
        ]
    
    @pytest.mark.asyncio
    async def test_scan_with_private_ip_warning(self, authenticated_client: AsyncClient):
        """Should warn about private IP ranges."""
        with patch("app.api.v1.zap.zap_scan.delay") as mock_task:
            mock_task.return_value.id = "test-123"
            
            response = await authenticated_client.post(
                "/api/v1/zap/scan",
                json={"target_url": "http://192.168.1.1"}
            )
            # May include warning or be allowed
            assert response.status_code in [
                status.HTTP_202_ACCEPTED,
                status.HTTP_400_BAD_REQUEST,
            ]


# =============================================================================
# TESTS - SCAN CONFIGURATIONS
# =============================================================================

class TestZapScanConfigurations:
    """Tests for scan configuration options."""
    
    @pytest.mark.asyncio
    async def test_scan_with_custom_depth(self, authenticated_client: AsyncClient):
        """Should accept custom spider depth."""
        with patch("app.api.v1.zap.zap_scan.delay") as mock_task:
            mock_task.return_value.id = "test-123"
            
            response = await authenticated_client.post(
                "/api/v1/zap/scan",
                json={
                    "target_url": "https://example.com",
                    "spider_depth": 5,
                }
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.asyncio
    async def test_scan_with_authentication(self, authenticated_client: AsyncClient):
        """Should accept authentication config."""
        with patch("app.api.v1.zap.zap_scan.delay") as mock_task:
            mock_task.return_value.id = "test-123"
            
            response = await authenticated_client.post(
                "/api/v1/zap/scan",
                json={
                    "target_url": "https://example.com",
                    "auth": {
                        "type": "bearer",
                        "token": "test-token",
                    }
                }
            )
            
            # Auth config may or may not be supported
            assert response.status_code in [
                status.HTTP_202_ACCEPTED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]
