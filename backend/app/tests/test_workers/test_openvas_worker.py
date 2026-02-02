# =============================================================================
# NESTSECURE - Tests para OpenVAS Worker
# =============================================================================
"""
Tests unitarios para el worker de OpenVAS.

Usa mocking para simular Celery y GVM.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.workers.openvas_worker import (
    openvas_full_scan,
    openvas_create_target,
    openvas_check_status,
    openvas_get_results,
    openvas_stop_scan,
    openvas_cleanup,
    openvas_health_check,
    run_async,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_gvm_client():
    """Mock del cliente GVM."""
    mock = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    
    # Mock de métodos
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    mock.create_target = AsyncMock(return_value="target-123")
    mock.create_task = AsyncMock(return_value="task-456")
    mock.start_task = AsyncMock(return_value="report-789")
    
    # Mock de task status (terminado inmediatamente para tests)
    task_status = MagicMock()
    task_status.status = "Done"
    task_status.progress = 100
    task_status.is_done = True
    task_status.is_running = False
    task_status.last_report_id = "report-789"
    mock.get_task_status = AsyncMock(return_value=task_status)
    
    # Mock de reporte
    report = MagicMock()
    report.id = "report-789"
    report.host_count = 5
    report.vuln_count = 10
    report.critical_count = 1
    report.high_count = 3
    report.medium_count = 4
    report.low_count = 2
    report.all_cves = ["CVE-2023-1234"]
    report.hosts = []
    report.get_summary = MagicMock(return_value={"total": 10})
    mock.get_report = AsyncMock(return_value=report)
    
    mock.stop_task = AsyncMock(return_value=True)
    mock.delete_task = AsyncMock(return_value=True)
    mock.delete_target = AsyncMock(return_value=True)
    
    return mock


@pytest.fixture
def mock_celery_task():
    """Mock de tarea Celery."""
    mock = MagicMock()
    mock.update_state = MagicMock()
    return mock


# =============================================================================
# Tests - run_async helper
# =============================================================================

class TestRunAsync:
    """Tests para el helper run_async."""
    
    def test_run_async_simple(self):
        """Test ejecutar coroutine simple."""
        async def simple_coro():
            return "result"
        
        result = run_async(simple_coro())
        assert result == "result"
    
    def test_run_async_with_exception(self):
        """Test que propaga excepciones correctamente."""
        async def failing_coro():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            run_async(failing_coro())


# =============================================================================
# Tests - Health Check
# =============================================================================

class TestHealthCheck:
    """Tests para health check task."""
    
    def test_health_check_healthy(self, mock_gvm_client):
        """Test health check cuando GVM está healthy."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_health_check()
            
            assert result["status"] == "healthy"
    
    def test_health_check_error(self):
        """Test health check cuando GVM falla."""
        mock = MagicMock()
        mock.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))
        mock.__aexit__ = AsyncMock()
        
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock):
            result = openvas_health_check()
            
            assert result["status"] == "unhealthy"
            assert "error" in result


# =============================================================================
# Tests - Create Target
# =============================================================================

class TestCreateTarget:
    """Tests para create target task."""
    
    def test_create_target_success(self, mock_gvm_client):
        """Test crear target exitosamente."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_create_target(
                hosts="192.168.1.0/24",
                name="Test Target",
            )
            
            assert result["status"] == "success"
            assert "target_id" in result
    
    def test_create_target_auto_name(self, mock_gvm_client):
        """Test crear target con nombre automático."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_create_target(hosts="192.168.1.1")
            
            assert result["status"] == "success"
            assert result["name"].startswith("NestSecure-")
    
    def test_create_target_error(self, mock_gvm_client):
        """Test error al crear target."""
        from app.integrations.gvm.exceptions import GVMError
        mock_gvm_client.create_target = AsyncMock(side_effect=GVMError("Failed"))
        
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_create_target(hosts="192.168.1.1")
            
            assert result["status"] == "error"
            assert "error" in result


# =============================================================================
# Tests - Check Status
# =============================================================================

class TestCheckStatus:
    """Tests para check status task."""
    
    def test_check_status_success(self, mock_gvm_client):
        """Test verificar estado exitosamente."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_check_status("task-456")
            
            assert result["task_id"] == "task-456"
            assert "status" in result
            assert "progress" in result
    
    def test_check_status_error(self, mock_gvm_client):
        """Test error al verificar estado."""
        from app.integrations.gvm.exceptions import GVMError
        mock_gvm_client.get_task_status = AsyncMock(side_effect=GVMError("Not found"))
        
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_check_status("invalid-task")
            
            assert result["status"] == "error"


# =============================================================================
# Tests - Get Results
# =============================================================================

class TestGetResults:
    """Tests para get results task."""
    
    def test_get_results_success(self, mock_gvm_client):
        """Test obtener resultados exitosamente."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_get_results("report-789")
            
            assert result["status"] == "success"
            assert result["report_id"] == "report-789"
            assert "summary" in result
            assert "vulnerabilities" in result
    
    def test_get_results_error(self, mock_gvm_client):
        """Test error al obtener resultados."""
        from app.integrations.gvm.exceptions import GVMError
        mock_gvm_client.get_report = AsyncMock(side_effect=GVMError("Report not found"))
        
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_get_results("invalid-report")
            
            assert result["status"] == "error"


# =============================================================================
# Tests - Stop Scan
# =============================================================================

class TestStopScan:
    """Tests para stop scan task."""
    
    def test_stop_scan_success(self, mock_gvm_client):
        """Test detener scan exitosamente."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_stop_scan("task-456")
            
            assert result["task_id"] == "task-456"
            assert result["status"] == "stopped"
    
    def test_stop_scan_error(self, mock_gvm_client):
        """Test error al detener scan."""
        from app.integrations.gvm.exceptions import GVMError
        mock_gvm_client.stop_task = AsyncMock(side_effect=GVMError("Failed"))
        
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_stop_scan("task-456")
            
            assert result["status"] == "error"


# =============================================================================
# Tests - Cleanup
# =============================================================================

class TestCleanup:
    """Tests para cleanup task."""
    
    def test_cleanup_task_only(self, mock_gvm_client):
        """Test limpiar solo task."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_cleanup(task_id="task-456")
            
            assert result["status"] == "success"
            assert "task:task-456" in result["deleted"]
    
    def test_cleanup_target_only(self, mock_gvm_client):
        """Test limpiar solo target."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_cleanup(target_id="target-123")
            
            assert result["status"] == "success"
            assert "target:target-123" in result["deleted"]
    
    def test_cleanup_both(self, mock_gvm_client):
        """Test limpiar task y target."""
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_cleanup(target_id="target-123", task_id="task-456")
            
            assert result["status"] == "success"
            assert len(result["deleted"]) == 2
    
    def test_cleanup_partial_error(self, mock_gvm_client):
        """Test cleanup con error parcial."""
        mock_gvm_client.delete_task = AsyncMock(return_value=True)
        mock_gvm_client.delete_target = AsyncMock(return_value=False)
        
        with patch("app.workers.openvas_worker.GVMClient", return_value=mock_gvm_client):
            result = openvas_cleanup(target_id="target-123", task_id="task-456")
            
            assert result["status"] == "partial"
            assert len(result["errors"]) > 0


# =============================================================================
# Tests - Task Decorators (Celery Registration)
# =============================================================================

class TestTaskRegistration:
    """Tests para verificar que las tasks están registradas correctamente."""
    
    def test_full_scan_task_attributes(self):
        """Test atributos del task full_scan."""
        assert openvas_full_scan.name == "openvas.full_scan"
    
    def test_create_target_task_attributes(self):
        """Test atributos del task create_target."""
        assert openvas_create_target.name == "openvas.create_target"
    
    def test_check_status_task_attributes(self):
        """Test atributos del task check_status."""
        assert openvas_check_status.name == "openvas.check_status"
    
    def test_get_results_task_attributes(self):
        """Test atributos del task get_results."""
        assert openvas_get_results.name == "openvas.get_results"
    
    def test_stop_scan_task_attributes(self):
        """Test atributos del task stop_scan."""
        assert openvas_stop_scan.name == "openvas.stop_scan"
    
    def test_cleanup_task_attributes(self):
        """Test atributos del task cleanup."""
        assert openvas_cleanup.name == "openvas.cleanup"
    
    def test_health_check_task_attributes(self):
        """Test atributos del task health_check."""
        assert openvas_health_check.name == "openvas.health_check"
