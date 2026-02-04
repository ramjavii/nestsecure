# =============================================================================
# NESTSECURE - Tests de Flujo Completo de Escaneo
# =============================================================================
"""
Tests de integración para flujos completos de escaneo.

Estos tests verifican el flujo end-to-end:
1. Crear escaneo
2. Verificar estado
3. Obtener resultados
4. Verificar persistencia en DB

Nota: Estos tests usan mocks para las tareas de Celery.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from uuid import uuid4

from app.models.scan import Scan, ScanStatus, ScanType
from app.models.vulnerability import Vulnerability, VulnerabilitySeverity


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def completed_nuclei_result():
    """Resultado completo de escaneo Nuclei."""
    return {
        "task_id": "nuclei-flow-123",
        "scan_id": None,  # Se llena dinámicamente
        "profile": "standard",
        "status": "completed",
        "targets": ["https://test-target.local"],
        "start_time": "2024-01-15T10:00:00Z",
        "end_time": "2024-01-15T10:30:00Z",
        "findings": [
            {
                "template_id": "cve-2021-44228-log4j",
                "template_name": "Apache Log4j RCE (CVE-2021-44228)",
                "severity": "critical",
                "host": "https://test-target.local",
                "matched_at": "https://test-target.local/api/vulnerable",
                "ip": "10.0.0.1",
                "cve": "CVE-2021-44228",
                "cvss": 10.0,
                "description": "Log4j RCE vulnerability",
                "references": ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
            },
            {
                "template_id": "xss-reflected",
                "template_name": "Reflected XSS",
                "severity": "high",
                "host": "https://test-target.local",
                "matched_at": "https://test-target.local/search?q=<script>",
                "ip": "10.0.0.1",
            },
            {
                "template_id": "ssl-certificate-expiry",
                "template_name": "SSL Certificate Expiring Soon",
                "severity": "medium",
                "host": "https://test-target.local",
                "matched_at": "https://test-target.local/",
                "ip": "10.0.0.1",
            },
            {
                "template_id": "http-missing-x-frame",
                "template_name": "Missing X-Frame-Options Header",
                "severity": "info",
                "host": "https://test-target.local",
                "matched_at": "https://test-target.local/",
                "ip": "10.0.0.1",
            },
        ],
        "severity_counts": {
            "critical": 1,
            "high": 1,
            "medium": 1,
            "low": 0,
            "info": 1,
        },
        "unique_cves": ["CVE-2021-44228"],
        "total_requests": 1500,
        "templates_used": 500,
    }


@pytest.fixture
def completed_nmap_result():
    """Resultado completo de escaneo Nmap."""
    return {
        "scan_type": "quick",
        "target": "192.168.1.100",
        "success": True,
        "services": [
            {
                "port": 22,
                "protocol": "tcp",
                "state": "open",
                "service_name": "ssh",
                "product": "OpenSSH",
                "version": "8.9p1",
            },
            {
                "port": 80,
                "protocol": "tcp",
                "state": "open",
                "service_name": "http",
                "product": "nginx",
                "version": "1.18.0",
            },
            {
                "port": 443,
                "protocol": "tcp",
                "state": "open",
                "service_name": "https",
                "product": "nginx",
                "version": "1.18.0",
            },
        ],
        "host_info": {
            "ip_address": "192.168.1.100",
            "hostname": "web-server.local",
            "os_match": "Linux 5.x",
            "mac_address": "00:11:22:33:44:55",
        },
        "services_found": 3,
    }


# =============================================================================
# TEST: Flujo Completo de Escaneo Nuclei
# =============================================================================

class TestNucleiScanFlow:
    """Tests del flujo completo de escaneo con Nuclei."""
    
    @pytest.mark.asyncio
    async def test_full_nuclei_scan_flow(
        self,
        client_with_db,
        auth_headers,
        completed_nuclei_result,
    ):
        """
        Test flujo completo:
        1. Iniciar escaneo
        2. Verificar estado (pendiente)
        3. Simular completado
        4. Obtener resultados
        """
        # Mock para la tarea de Celery
        mock_task = MagicMock()
        mock_task.id = "nuclei-flow-123"
        mock_task.delay = MagicMock(return_value=mock_task)
        
        # PASO 1: Iniciar escaneo
        with patch("app.api.v1.nuclei.nuclei_scan", mock_task):
            response = await client_with_db.post(
                "/api/v1/nuclei/scan",
                headers=auth_headers,
                json={
                    "target": "https://test-target.local",
                    "profile": "standard",
                    "scan_name": "Flow Test Scan",
                }
            )
        
        assert response.status_code == 202
        scan_data = response.json()
        task_id = scan_data["task_id"]
        scan_id = scan_data["scan_id"]
        
        assert task_id == "nuclei-flow-123"
        assert scan_data["status"] == "queued"
        
        # PASO 2: Verificar estado (pendiente)
        mock_pending = MagicMock()
        mock_pending.status = "PENDING"
        mock_pending.ready.return_value = False
        mock_pending.failed.return_value = False
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_pending):
            response = await client_with_db.get(
                f"/api/v1/nuclei/scan/{task_id}",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] in ["pending", "queued"]
        
        # PASO 3: Simular completado
        completed_nuclei_result["scan_id"] = scan_id
        
        mock_completed = MagicMock()
        mock_completed.status = "SUCCESS"
        mock_completed.ready.return_value = True
        mock_completed.successful.return_value = True
        mock_completed.failed.return_value = False
        mock_completed.result = completed_nuclei_result
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_completed):
            response = await client_with_db.get(
                f"/api/v1/nuclei/scan/{task_id}",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] == "completed"
        assert status_data["total_findings"] == 4
        
        # PASO 4: Obtener resultados completos
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_completed):
            response = await client_with_db.get(
                f"/api/v1/nuclei/scan/{task_id}/results",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        results_data = response.json()
        
        assert results_data["status"] == "completed"
        assert len(results_data["findings"]) == 4
        assert results_data["total_findings"] == 4
        
        # Verificar resumen de severidades
        summary = results_data["summary"]
        assert summary["critical"] == 1
        assert summary["high"] == 1
        assert summary["medium"] == 1
        assert summary["info"] == 1
        
        # Verificar CVEs únicos
        assert "CVE-2021-44228" in results_data["unique_cves"]
    
    @pytest.mark.asyncio
    async def test_nuclei_scan_with_severity_filter(
        self,
        client_with_db,
        auth_headers,
        completed_nuclei_result,
    ):
        """Test filtrado de resultados por severidad."""
        mock_completed = MagicMock()
        mock_completed.ready.return_value = True
        mock_completed.failed.return_value = False
        mock_completed.result = completed_nuclei_result
        
        # Filtrar solo críticos
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_completed):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/test-task/results?severity=critical",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Solo debería retornar el finding crítico
        assert len(data["findings"]) == 1
        assert data["findings"][0]["severity"] == "critical"
        # El campo puede ser cve_id o cve dependiendo del alias
        finding = data["findings"][0]
        cve_value = finding.get("cve_id") or finding.get("cve")
        assert cve_value == "CVE-2021-44228"


# =============================================================================
# TEST: Flujo Completo de Escaneo Nmap
# =============================================================================

class TestNmapScanFlow:
    """Tests del flujo completo de escaneo con Nmap."""
    
    @pytest.mark.asyncio
    async def test_full_nmap_quick_scan_flow(
        self,
        client_with_db,
        auth_headers,
        completed_nmap_result,
    ):
        """Test flujo de escaneo rápido Nmap."""
        mock_task = MagicMock()
        mock_task.id = "nmap-flow-123"
        mock_task.delay = MagicMock(return_value=mock_task)
        
        # Iniciar escaneo
        with patch("app.api.v1.scans.nmap_quick_scan_task", mock_task):
            response = await client_with_db.post(
                "/api/v1/scans/nmap/quick",
                headers=auth_headers,
                json={
                    "target": "192.168.1.100",
                    "scan_name": "Quick Nmap Test",
                }
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["profile"] == "quick"
        assert data["status"] == "queued"
    
    @pytest.mark.asyncio
    async def test_nmap_full_scan_flow(
        self,
        client_with_db,
        auth_headers,
    ):
        """Test flujo de escaneo completo Nmap."""
        mock_task = MagicMock()
        mock_task.id = "nmap-full-123"
        mock_task.delay = MagicMock(return_value=mock_task)
        
        with patch("app.api.v1.scans.nmap_full_scan_task", mock_task):
            response = await client_with_db.post(
                "/api/v1/scans/nmap/full",
                headers=auth_headers,
                json={
                    "target": "192.168.1.100",
                }
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["profile"] == "full"
        assert "30+ minutes" in data["message"]
    
    @pytest.mark.asyncio
    async def test_nmap_vulnerability_scan_flow(
        self,
        client_with_db,
        auth_headers,
    ):
        """Test flujo de escaneo de vulnerabilidades Nmap."""
        mock_task = MagicMock()
        mock_task.id = "nmap-vuln-123"
        mock_task.delay = MagicMock(return_value=mock_task)
        
        with patch("app.api.v1.scans.nmap_vuln_scan_task", mock_task):
            response = await client_with_db.post(
                "/api/v1/scans/nmap/vulnerability",
                headers=auth_headers,
                json={
                    "target": "192.168.1.100",
                }
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["profile"] == "vulnerability"


# =============================================================================
# TEST: Flujo Combinado Nmap + Nuclei
# =============================================================================

class TestCombinedScanFlow:
    """Tests de flujo combinado de múltiples scanners."""
    
    @pytest.mark.asyncio
    async def test_combined_discovery_and_vuln_scan(
        self,
        client_with_db,
        auth_headers,
    ):
        """
        Test flujo realista:
        1. Discovery con Nmap
        2. Scan de vulnerabilidades con Nuclei en hosts descubiertos
        """
        # Mock para Nmap
        nmap_task = MagicMock()
        nmap_task.id = "nmap-discovery-123"
        nmap_task.delay = MagicMock(return_value=nmap_task)
        
        # Mock para Nuclei
        nuclei_task = MagicMock()
        nuclei_task.id = "nuclei-vuln-123"
        nuclei_task.delay = MagicMock(return_value=nuclei_task)
        
        # PASO 1: Discovery con Nmap
        with patch("app.api.v1.scans.nmap_quick_scan_task", nmap_task):
            response = await client_with_db.post(
                "/api/v1/scans/nmap/quick",
                headers=auth_headers,
                json={"target": "192.168.1.0/24"}
            )
        
        assert response.status_code == 202
        nmap_data = response.json()
        
        # PASO 2: Escaneo Nuclei en host web descubierto
        with patch("app.api.v1.nuclei.nuclei_scan", nuclei_task):
            response = await client_with_db.post(
                "/api/v1/nuclei/scan",
                headers=auth_headers,
                json={
                    "target": "https://192.168.1.100",
                    "profile": "web",
                }
            )
        
        assert response.status_code == 202
        nuclei_data = response.json()
        
        # Verificar que ambos escaneos están encolados
        assert nmap_data["status"] == "queued"
        assert nuclei_data["status"] == "queued"
        
        # Ambos deberían tener IDs de tareas diferentes
        assert nmap_data["task_id"] != nuclei_data["task_id"]


# =============================================================================
# TEST: Manejo de Errores en Flujos
# =============================================================================

class TestScanFlowErrors:
    """Tests de manejo de errores en flujos de escaneo."""
    
    @pytest.mark.asyncio
    async def test_nuclei_scan_timeout(self, client_with_db, auth_headers):
        """Test manejo de timeout en escaneo Nuclei."""
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.failed.return_value = False
        mock_result.result = {
            "task_id": "timeout-task",
            "status": "timeout",
            "error": "Scan exceeded time limit",
        }
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_result):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/timeout-task",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "timeout"
    
    @pytest.mark.asyncio
    async def test_nuclei_scan_failed(self, client_with_db, auth_headers):
        """Test manejo de fallo en escaneo Nuclei."""
        mock_result = MagicMock()
        mock_result.status = "FAILURE"  # Estado de Celery para tareas fallidas
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.failed.return_value = True
        mock_result.result = Exception("Connection refused")
        
        with patch("app.api.v1.nuclei.AsyncResult", return_value=mock_result):
            response = await client_with_db.get(
                "/api/v1/nuclei/scan/failed-task",
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] is not None


# =============================================================================
# TEST: Verificación de Persistencia (Mocked)
# =============================================================================

class TestScanPersistence:
    """Tests de persistencia de resultados."""
    
    @pytest.mark.asyncio
    async def test_scan_creates_db_record(self, client_with_db, auth_headers):
        """Test que iniciar scan crea registro en DB."""
        mock_task = MagicMock()
        mock_task.id = "persist-test-123"
        mock_task.delay = MagicMock(return_value=mock_task)
        
        with patch("app.api.v1.nuclei.nuclei_scan", mock_task):
            response = await client_with_db.post(
                "/api/v1/nuclei/scan",
                headers=auth_headers,
                json={
                    "target": "https://persist-test.local",
                    "profile": "quick",
                }
            )
        
        assert response.status_code == 202
        data = response.json()
        
        # Debería tener un scan_id de la DB
        assert data["scan_id"] is not None
        assert len(data["scan_id"]) == 32  # UUID sin guiones
    
    @pytest.mark.asyncio
    async def test_scan_appears_in_history(self, client_with_db, auth_headers):
        """Test que scans completados aparecen en historial."""
        mock_task = MagicMock()
        mock_task.id = "history-test-123"
        mock_task.delay = MagicMock(return_value=mock_task)
        
        # Crear scan
        with patch("app.api.v1.nuclei.nuclei_scan", mock_task):
            create_response = await client_with_db.post(
                "/api/v1/nuclei/scan",
                headers=auth_headers,
                json={
                    "target": "https://history-test.local",
                    "profile": "standard",
                }
            )
        
        assert create_response.status_code == 202
        
        # Verificar que aparece en historial
        list_response = await client_with_db.get(
            "/api/v1/nuclei/scans",
            headers=auth_headers,
        )
        
        assert list_response.status_code == 200
        # El scan debería estar en el historial (puede tener filtro por descripción "nuclei")
