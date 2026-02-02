# =============================================================================
# NESTSECURE - Tests para GVM Client
# =============================================================================
"""
Tests unitarios para el cliente GVM/OpenVAS.

Usa mocking para simular conexión con GVM.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.integrations.gvm.client import GVMClient, get_gvm_client, reset_gvm_client
from app.integrations.gvm.models import (
    GVMTarget, GVMTask, GVMTaskStatus, GVMReport,
    GVMHostResult, GVMVulnerability, GVMSeverity,
)
from app.integrations.gvm.exceptions import (
    GVMError, GVMConnectionError, GVMAuthenticationError,
    GVMScanError, GVMNotFoundError,
)
from app.integrations.gvm.parser import GVMParser


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_gvm_client():
    """Cliente GVM en modo mock."""
    return GVMClient(mock_mode=True)


# =============================================================================
# Tests - Mock Mode
# =============================================================================

class TestGVMClientMockMode:
    """Tests del cliente GVM en modo mock."""
    
    @pytest.mark.asyncio
    async def test_connect_mock(self, mock_gvm_client):
        """Test conexión en modo mock."""
        async with mock_gvm_client as gvm:
            # En mock mode, conecta exitosamente
            assert gvm is not None
    
    @pytest.mark.asyncio
    async def test_health_check_mock(self, mock_gvm_client):
        """Test health check en modo mock."""
        async with mock_gvm_client as gvm:
            health = await gvm.health_check()
            assert health["status"] == "healthy"
            assert "version" in health
    
    @pytest.mark.asyncio
    async def test_create_target_mock(self, mock_gvm_client):
        """Test crear target en modo mock."""
        async with mock_gvm_client as gvm:
            target_id = await gvm.create_target(
                name="Test Target",
                hosts="192.168.1.0/24",
            )
            assert target_id is not None
            assert len(target_id) == 36  # UUID format
    
    @pytest.mark.asyncio
    async def test_create_task_mock(self, mock_gvm_client):
        """Test crear task en modo mock."""
        async with mock_gvm_client as gvm:
            target_id = await gvm.create_target(
                name="Test Target",
                hosts="192.168.1.1",
            )
            
            task_id = await gvm.create_task(
                name="Test Task",
                target_id=target_id,
            )
            
            assert task_id is not None
            assert len(task_id) == 36
    
    @pytest.mark.asyncio
    async def test_start_task_mock(self, mock_gvm_client):
        """Test iniciar task en modo mock."""
        async with mock_gvm_client as gvm:
            target_id = await gvm.create_target(name="Target", hosts="192.168.1.1")
            task_id = await gvm.create_task(name="Task", target_id=target_id)
            
            report_id = await gvm.start_task(task_id)
            
            assert report_id is not None
            assert len(report_id) == 36
    
    @pytest.mark.asyncio
    async def test_quick_scan_mock(self, mock_gvm_client):
        """Test quick scan en modo mock."""
        async with mock_gvm_client as gvm:
            result = await gvm.quick_scan(
                name="Quick Test",
                hosts="192.168.1.1",
            )
            
            assert "target_id" in result
            assert "task_id" in result
            assert "report_id" in result


# =============================================================================
# Tests - Models
# =============================================================================

class TestGVMModels:
    """Tests para modelos GVM."""
    
    def test_severity_from_cvss(self):
        """Test conversión CVSS a severidad."""
        assert GVMSeverity.from_cvss(9.5) == GVMSeverity.CRITICAL
        assert GVMSeverity.from_cvss(8.0) == GVMSeverity.HIGH
        assert GVMSeverity.from_cvss(5.0) == GVMSeverity.MEDIUM
        assert GVMSeverity.from_cvss(2.0) == GVMSeverity.LOW
        assert GVMSeverity.from_cvss(0.0) == GVMSeverity.LOG
    
    def test_severity_from_threat(self):
        """Test conversión threat string a severidad."""
        assert GVMSeverity.from_threat("Critical") == GVMSeverity.CRITICAL
        assert GVMSeverity.from_threat("High") == GVMSeverity.HIGH
        assert GVMSeverity.from_threat("Medium") == GVMSeverity.MEDIUM
        assert GVMSeverity.from_threat("Low") == GVMSeverity.LOW
        assert GVMSeverity.from_threat("Log") == GVMSeverity.LOG
        assert GVMSeverity.from_threat("Unknown") == GVMSeverity.LOG
    
    def test_task_status_properties(self):
        """Test propiedades de GVMTaskStatus."""
        assert GVMTaskStatus.RUNNING.is_running is True
        assert GVMTaskStatus.DONE.is_running is False
        assert GVMTaskStatus.DONE.is_finished is True
        assert GVMTaskStatus.RUNNING.is_finished is False


# =============================================================================
# Tests - Parser
# =============================================================================

class TestGVMParser:
    """Tests para el parser GVM."""
    
    def test_parse_targets_empty(self):
        """Test parseo de lista vacía de targets."""
        xml = "<get_targets_response><target></target></get_targets_response>"
        parser = GVMParser()
        targets = parser.parse_targets(xml)
        assert isinstance(targets, list)
    
    def test_parse_tasks_empty(self):
        """Test parseo de lista vacía de tasks."""
        xml = "<get_tasks_response></get_tasks_response>"
        parser = GVMParser()
        tasks = parser.parse_tasks(xml)
        assert isinstance(tasks, list)


# =============================================================================
# Tests - Exceptions
# =============================================================================

class TestGVMExceptions:
    """Tests para excepciones GVM."""
    
    def test_gvm_error_str(self):
        """Test representación de error."""
        error = GVMError("Test error")
        assert "Test error" in str(error)
    
    def test_connection_error_message(self):
        """Test error de conexión."""
        error = GVMConnectionError("Failed to connect", host="localhost", port=9390)
        assert "Failed to connect" in str(error)
    
    def test_authentication_error_message(self):
        """Test error de autenticación."""
        error = GVMAuthenticationError("Invalid credentials", username="admin")
        assert "Invalid credentials" in str(error)
    
    def test_scan_error_message(self):
        """Test error de escaneo."""
        error = GVMScanError("Scan failed", task_id="task-123")
        assert "Scan failed" in str(error)
    
    def test_not_found_error_message(self):
        """Test error not found."""
        error = GVMNotFoundError("Target not found", resource_type="target", resource_id="abc")
        assert "Target not found" in str(error)


# =============================================================================
# Tests - Singleton
# =============================================================================

class TestGVMSingleton:
    """Tests para el patrón singleton del cliente."""
    
    def test_get_client_returns_same_instance(self):
        """Test que get_gvm_client retorna la misma instancia."""
        reset_gvm_client()
        
        client1 = get_gvm_client()
        client2 = get_gvm_client()
        
        assert client1 is client2
    
    def test_reset_client(self):
        """Test reset del cliente singleton."""
        client1 = get_gvm_client()
        reset_gvm_client()
        client2 = get_gvm_client()
        
        assert client1 is not client2
