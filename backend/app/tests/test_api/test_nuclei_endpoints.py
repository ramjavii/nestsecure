# =============================================================================
# NESTSECURE - Tests para API de Nuclei
# =============================================================================
"""
Tests de integración para los endpoints de Nuclei.

Cubre:
- Inicio de escaneos
- Obtención de estado
- Listado de perfiles
- Escaneos rápidos (quick, cve, web)
- Listado de historial
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_nuclei_task():
    """Mock para tareas de Celery de Nuclei."""
    mock_task = MagicMock()
    mock_task.id = "nuclei-task-123"
    mock_task.delay = MagicMock(return_value=mock_task)
    return mock_task


@pytest.fixture
def mock_nuclei_result():
    """Mock para resultado de tarea Celery."""
    return {
        "task_id": "nuclei-task-123",
        "scan_id": "scan-123",
        "profile": "standard",
        "status": "completed",
        "targets": ["https://example.com"],
        "start_time": "2024-01-15T10:00:00Z",
        "end_time": "2024-01-15T10:30:00Z",
        "findings": [
            {
                "template_id": "cve-2021-44228",
                "template_name": "Log4Shell RCE",
                "severity": "critical",
                "host": "https://example.com",
                "matched_at": "https://example.com/vulnerable",
                "cve": "CVE-2021-44228",
                "cvss": 10.0,
            },
            {
                "template_id": "missing-headers",
                "template_name": "Missing Security Headers",
                "severity": "info",
                "host": "https://example.com",
                "matched_at": "https://example.com/",
            }
        ],
        "unique_cves": ["CVE-2021-44228"],
    }


# =============================================================================
# Tests - Start Nuclei Scan
# =============================================================================

class TestStartNucleiScan:
    """Tests para POST /nuclei/scan."""
    
    @pytest.mark.asyncio
    async def test_start_scan_success(self, client_with_db, auth_headers, mock_nuclei_task):
        """Test iniciar escaneo exitosamente."""
        with patch("app.api.v1.nuclei.nuclei_scan", mock_nuclei_task):
            response = await client_with_db.post(
                "/api/v1/nuclei/scan",
                headers=auth_headers,
                json={
                    "target": "https://example.com",
                    "profile": "standard",
                    "timeout": 3600,
                }
            )
        
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert "scan_id" in data
        assert data["status"] == "queued"
        assert data["target"] == "https://example.com"
        assert data["profile"] == "standard"
    
    @pytest.mark.asyncio
    async def test_start_scan_with_tags(self, client_with_db, auth_headers, mock_nuclei_task):
        """Test iniciar escaneo con tags específicos."""
        with patch("app.api.v1.nuclei.nuclei_scan", mock_nuclei_task):
            response = await client_with_db.post(
                "/api/v1/nuclei/scan",
                headers=auth_headers,
                json={
                    "target": "https://example.com",
                    "profile": "cves",
                    "tags": ["cve", "rce"],
                    "severities": ["critical", "high"],
                }
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["profile"] == "cves"
    
    @pytest.mark.asyncio
    async def test_start_scan_invalid_profile(self, client_with_db, auth_headers):
        """Test iniciar escaneo con perfil inválido."""
        response = await client_with_db.post(
            "/api/v1/nuclei/scan",
            headers=auth_headers,
            json={
                "target": "https://example.com",
                "profile": "invalid_profile",
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_start_scan_empty_target(self, client_with_db, auth_headers):
        """Test iniciar escaneo sin target."""
        response = await client_with_db.post(
            "/api/v1/nuclei/scan",
            headers=auth_headers,
            json={
                "target": "",
                "profile": "standard",
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_start_scan_unauthenticated(self, client_with_db):
        """Test iniciar escaneo sin autenticación."""
        response = await client_with_db.post(
            "/api/v1/nuclei/scan",
            json={
                "target": "https://example.com",
            }
        )
        
        assert response.status_code == 401


# =============================================================================
# Tests - Get Scan Status
# =============================================================================

class TestGetNucleiScanStatus:
    """Tests para GET /nuclei/scan/{task_id}."""
    
    @pytest.mark.asyncio
    async def test_get_status_pending(self, client_with_db, auth_headers):
        """Test obtener estado de scan pendiente."""
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_result.ready.return_value = False
        mock_result.failed.return_value = False
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_result):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/task-123",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-123"
        assert data["status"] in ["pending", "queued"]
    
    @pytest.mark.asyncio
    async def test_get_status_completed(self, client_with_db, auth_headers, mock_nuclei_result):
        """Test obtener estado de scan completado."""
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.failed.return_value = False
        mock_result.result = mock_nuclei_result
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_result):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/task-123",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["total_findings"] == 2
        assert "CVE-2021-44228" in data["unique_cves"]


# =============================================================================
# Tests - Get Scan Results
# =============================================================================

class TestGetNucleiScanResults:
    """Tests para GET /nuclei/scan/{task_id}/results."""
    
    @pytest.mark.asyncio
    async def test_get_results_success(self, client_with_db, auth_headers, mock_nuclei_result):
        """Test obtener resultados de scan completado."""
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.failed.return_value = False
        mock_result.result = mock_nuclei_result
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_result):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/task-123/results",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert len(data["findings"]) == 2
        assert data["total_findings"] == 2
        assert "summary" in data
    
    @pytest.mark.asyncio
    async def test_get_results_with_pagination(self, client_with_db, auth_headers, mock_nuclei_result):
        """Test obtener resultados con paginación."""
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.failed.return_value = False
        mock_result.result = mock_nuclei_result
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_result):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/task-123/results?page=1&page_size=1",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["findings"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1
    
    @pytest.mark.asyncio
    async def test_get_results_filter_severity(self, client_with_db, auth_headers, mock_nuclei_result):
        """Test obtener resultados filtrados por severidad."""
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.failed.return_value = False
        mock_result.result = mock_nuclei_result
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_result):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/task-123/results?severity=critical",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        # Solo debería devolver el finding crítico
        assert all(f["severity"] == "critical" for f in data["findings"])
    
    @pytest.mark.asyncio
    async def test_get_results_not_ready(self, client_with_db, auth_headers):
        """Test obtener resultados de scan no completado."""
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_result):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/task-123/results",
                headers=auth_headers,
            )
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()


# =============================================================================
# Tests - List Profiles
# =============================================================================

class TestListNucleiProfiles:
    """Tests para GET /nuclei/profiles."""
    
    @pytest.mark.asyncio
    async def test_list_profiles(self, client_with_db, auth_headers):
        """Test listar perfiles disponibles."""
        response = await client_with_db.get(
            "/api/v1/nuclei/profiles",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert "total" in data
        assert data["total"] > 0
        
        # Verificar que los perfiles básicos existen
        profile_names = [p["name"] for p in data["profiles"]]
        assert any("quick" in name.lower() or "standard" in name.lower() for name in profile_names)
    
    @pytest.mark.asyncio
    async def test_list_profiles_unauthenticated(self, client_with_db):
        """Test listar perfiles sin autenticación."""
        response = await client_with_db.get(
            "/api/v1/nuclei/profiles",
        )
        
        assert response.status_code == 401


# =============================================================================
# Tests - Quick Scan Endpoints
# =============================================================================

class TestNucleiQuickScans:
    """Tests para endpoints de escaneos rápidos."""
    
    @pytest.mark.asyncio
    async def test_quick_scan(self, client_with_db, auth_headers, mock_nuclei_task):
        """Test escaneo rápido."""
        with patch("app.api.v1.nuclei.nuclei_quick_scan", mock_nuclei_task):
            response = await client_with_db.post(
                "/api/v1/nuclei/quick",
                headers=auth_headers,
                json={"target": "https://example.com"}
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["profile"] == "quick"
    
    @pytest.mark.asyncio
    async def test_cve_scan(self, client_with_db, auth_headers, mock_nuclei_task):
        """Test escaneo de CVEs."""
        with patch("app.api.v1.nuclei.nuclei_cve_scan", mock_nuclei_task):
            response = await client_with_db.post(
                "/api/v1/nuclei/cve",
                headers=auth_headers,
                json={"target": "https://example.com"}
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["profile"] == "cves"
    
    @pytest.mark.asyncio
    async def test_web_scan(self, client_with_db, auth_headers, mock_nuclei_task):
        """Test escaneo web."""
        with patch("app.api.v1.nuclei.nuclei_web_scan", mock_nuclei_task):
            response = await client_with_db.post(
                "/api/v1/nuclei/web",
                headers=auth_headers,
                json={"target": "https://example.com"}
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["profile"] == "web"


# =============================================================================
# Tests - Scan History
# =============================================================================

class TestNucleiScanHistory:
    """Tests para GET /nuclei/scans."""
    
    @pytest.mark.asyncio
    async def test_list_scans_empty(self, client_with_db, auth_headers):
        """Test listar historial vacío."""
        response = await client_with_db.get(
            "/api/v1/nuclei/scans",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    @pytest.mark.asyncio
    async def test_list_scans_pagination(self, client_with_db, auth_headers):
        """Test paginación del historial."""
        response = await client_with_db.get(
            "/api/v1/nuclei/scans?page=1&page_size=10",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


# =============================================================================
# Tests - Input Validation
# =============================================================================

class TestNucleiInputValidation:
    """Tests de validación de entrada."""
    
    @pytest.mark.asyncio
    async def test_timeout_too_short(self, client_with_db, auth_headers):
        """Test timeout demasiado corto."""
        response = await client_with_db.post(
            "/api/v1/nuclei/scan",
            headers=auth_headers,
            json={
                "target": "https://example.com",
                "timeout": 10,  # Mínimo es 60
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_timeout_too_long(self, client_with_db, auth_headers):
        """Test timeout demasiado largo."""
        response = await client_with_db.post(
            "/api/v1/nuclei/scan",
            headers=auth_headers,
            json={
                "target": "https://example.com",
                "timeout": 100000,  # Máximo es 14400
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_target_too_long(self, client_with_db, auth_headers):
        """Test target demasiado largo."""
        response = await client_with_db.post(
            "/api/v1/nuclei/scan",
            headers=auth_headers,
            json={
                "target": "https://example.com/" + "a" * 3000,
            }
        )
        
        assert response.status_code == 422


# =============================================================================
# Tests - Nmap Profiles (bonus, ya que están en scans.py)
# =============================================================================

class TestNmapProfiles:
    """Tests para endpoints de Nmap en /scans."""
    
    @pytest.mark.asyncio
    async def test_list_nmap_profiles(self, client_with_db, auth_headers):
        """Test listar perfiles Nmap."""
        response = await client_with_db.get(
            "/api/v1/scans/nmap/profiles",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verificar estructura de perfil
        profile = data[0]
        assert "name" in profile
        assert "description" in profile
    
    @pytest.mark.asyncio
    async def test_nmap_quick_scan(self, client_with_db, auth_headers):
        """Test escaneo rápido Nmap."""
        mock_task = MagicMock()
        mock_task.id = "nmap-task-123"
        mock_task.delay = MagicMock(return_value=mock_task)
        
        with patch("app.api.v1.scans.nmap_quick_scan_task", mock_task):
            response = await client_with_db.post(
                "/api/v1/scans/nmap/quick",
                headers=auth_headers,
                json={"target": "192.168.1.1"}
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["profile"] == "quick"
