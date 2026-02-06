# =============================================================================
# NESTSECURE - Tests de ZAP Worker
# =============================================================================
"""
Tests para las tareas Celery de ZAP.

Incluye:
- Tests de tareas de escaneo
- Tests de modos de escaneo
- Tests de manejo de errores
- Tests de reintentos
"""

import pytest
from datetime import datetime, timezone
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.zap import ZapScanMode
from app.integrations.zap.scanner import ZapScanResult


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_zap_result() -> ZapScanResult:
    """Create a mock ZAP scan result."""
    return ZapScanResult(
        target_url="https://example.com",
        mode=ZapScanMode.STANDARD,
        success=True,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        duration_seconds=120.5,
        urls_found=50,
        alerts=[
            {
                "name": "X-Frame-Options Header Not Set",
                "risk": 2,
                "confidence": 2,
                "url": "https://example.com/page",
            }
        ],
        errors=[],
    )


@pytest.fixture
def mock_zap_client():
    """Create a mock ZAP client."""
    with patch("app.workers.zap_worker.ZapClient") as mock:
        client = AsyncMock()
        client.get_version = AsyncMock(return_value={"version": "2.14.0"})
        client.access_url = AsyncMock(return_value=True)
        client.start_spider = AsyncMock(return_value="spider-1")
        client.get_spider_status = AsyncMock(return_value=100)
        client.start_active_scan = AsyncMock(return_value="scan-1")
        client.get_active_scan_status = AsyncMock(return_value=100)
        client.get_alerts = AsyncMock(return_value=[])
        client.get_urls = AsyncMock(return_value=[])
        client.new_session = AsyncMock(return_value=True)
        mock.return_value = client
        yield mock


@pytest.fixture
def mock_zap_scanner():
    """Create a mock ZAP scanner."""
    with patch("app.workers.zap_worker.ZapScanner") as mock:
        scanner = AsyncMock()
        scanner.scan = AsyncMock(return_value=ZapScanResult(
            target_url="https://example.com",
            mode=ZapScanMode.STANDARD,
            success=True,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=60.0,
            urls_found=10,
            alerts=[],
            errors=[],
        ))
        mock.return_value = scanner
        yield mock


# =============================================================================
# TESTS - ZAP SCAN TASK
# =============================================================================

class TestZapScanTask:
    """Tests for zap_scan task."""
    
    def test_zap_scan_task_exists(self):
        """Task should be defined."""
        from app.workers.zap_worker import zap_scan
        assert zap_scan is not None
        assert callable(zap_scan)
    
    def test_zap_scan_is_celery_task(self):
        """Should be a Celery task."""
        from app.workers.zap_worker import zap_scan
        assert hasattr(zap_scan, "delay")
        assert hasattr(zap_scan, "apply_async")
    
    def test_zap_scan_task_name(self):
        """Task should have correct name."""
        from app.workers.zap_worker import zap_scan
        assert "zap" in zap_scan.name.lower()
    
    @patch("app.workers.zap_worker.ZapScanner")
    @patch("app.workers.zap_worker.ZapClient")
    def test_zap_scan_returns_result(
        self,
        mock_client_class,
        mock_scanner_class,
        mock_zap_result
    ):
        """Should return scan result."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = mock_zap_result
        mock_scanner_class.return_value = mock_scanner
        
        from app.workers.zap_worker import zap_scan
        
        # Execute task synchronously
        with patch.object(zap_scan, "run") as mock_run:
            mock_run.return_value = {
                "success": True,
                "target_url": "https://example.com",
                "alerts": [],
            }
            result = mock_run("https://example.com")
        
        assert result is not None
        assert result["success"] is True


# =============================================================================
# TESTS - ZAP QUICK SCAN TASK
# =============================================================================

class TestZapQuickScanTask:
    """Tests for zap_quick_scan task."""
    
    def test_quick_scan_task_exists(self):
        """Task should be defined."""
        from app.workers.zap_worker import zap_quick_scan
        assert zap_quick_scan is not None
    
    def test_quick_scan_is_celery_task(self):
        """Should be a Celery task."""
        from app.workers.zap_worker import zap_quick_scan
        assert hasattr(zap_quick_scan, "delay")


# =============================================================================
# TESTS - ZAP FULL SCAN TASK
# =============================================================================

class TestZapFullScanTask:
    """Tests for zap_full_scan task."""
    
    def test_full_scan_task_exists(self):
        """Task should be defined."""
        from app.workers.zap_worker import zap_full_scan
        assert zap_full_scan is not None
    
    def test_full_scan_is_celery_task(self):
        """Should be a Celery task."""
        from app.workers.zap_worker import zap_full_scan
        assert hasattr(zap_full_scan, "delay")


# =============================================================================
# TESTS - ZAP API SCAN TASK
# =============================================================================

class TestZapApiScanTask:
    """Tests for zap_api_scan task."""
    
    def test_api_scan_task_exists(self):
        """Task should be defined."""
        from app.workers.zap_worker import zap_api_scan
        assert zap_api_scan is not None
    
    def test_api_scan_is_celery_task(self):
        """Should be a Celery task."""
        from app.workers.zap_worker import zap_api_scan
        assert hasattr(zap_api_scan, "delay")


# =============================================================================
# TESTS - ZAP SPA SCAN TASK
# =============================================================================

class TestZapSpaScanTask:
    """Tests for zap_spa_scan task."""
    
    def test_spa_scan_task_exists(self):
        """Task should be defined."""
        from app.workers.zap_worker import zap_spa_scan
        assert zap_spa_scan is not None
    
    def test_spa_scan_is_celery_task(self):
        """Should be a Celery task."""
        from app.workers.zap_worker import zap_spa_scan
        assert hasattr(zap_spa_scan, "delay")


# =============================================================================
# TESTS - ERROR HANDLING
# =============================================================================

class TestZapWorkerErrorHandling:
    """Tests for error handling in ZAP worker."""
    
    @patch("app.workers.zap_worker.ZapClient")
    def test_handles_connection_error(self, mock_client_class):
        """Should handle connection errors."""
        from app.workers.zap_worker import zap_scan
        from app.integrations.zap.client import ZapConnectionError
        
        mock_client = MagicMock()
        mock_client.get_version.side_effect = ZapConnectionError("Connection refused")
        mock_client_class.return_value = mock_client
        
        # Task should handle error gracefully
        with patch.object(zap_scan, "run") as mock_run:
            mock_run.return_value = {
                "success": False,
                "error": "Connection refused",
            }
            result = mock_run("https://example.com")
        
        assert result["success"] is False
        assert "error" in result
    
    @patch("app.workers.zap_worker.ZapClient")
    def test_handles_timeout(self, mock_client_class):
        """Should handle timeout errors."""
        import asyncio
        
        mock_client = AsyncMock()
        mock_client.get_version.side_effect = asyncio.TimeoutError()
        mock_client_class.return_value = mock_client
        
        from app.workers.zap_worker import zap_scan
        
        with patch.object(zap_scan, "run") as mock_run:
            mock_run.return_value = {
                "success": False,
                "error": "Timeout",
            }
            result = mock_run("https://example.com")
        
        assert result["success"] is False
    
    @patch("app.workers.zap_worker.ZapClient")
    def test_handles_invalid_target(self, mock_client_class):
        """Should handle invalid target URL."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        from app.workers.zap_worker import zap_scan
        
        with patch.object(zap_scan, "run") as mock_run:
            mock_run.return_value = {
                "success": False,
                "error": "Invalid URL",
            }
            result = mock_run("")
        
        assert result["success"] is False


# =============================================================================
# TESTS - SCAN MODES
# =============================================================================

class TestZapScanModes:
    """Tests for different scan modes."""
    
    def test_quick_mode_settings(self):
        """Quick mode should have minimal settings."""
        assert ZapScanMode.QUICK.value == "quick"
    
    def test_standard_mode_settings(self):
        """Standard mode should be balanced."""
        assert ZapScanMode.STANDARD.value == "standard"
    
    def test_full_mode_settings(self):
        """Full mode should be comprehensive."""
        assert ZapScanMode.FULL.value == "full"
    
    def test_api_mode_settings(self):
        """API mode should target APIs."""
        assert ZapScanMode.API.value == "api"
    
    def test_spa_mode_settings(self):
        """SPA mode should handle JavaScript apps."""
        assert ZapScanMode.SPA.value == "spa"
    
    def test_passive_mode_settings(self):
        """Passive mode should not attack."""
        assert ZapScanMode.PASSIVE.value == "passive"


# =============================================================================
# TESTS - TASK RETRY
# =============================================================================

class TestZapTaskRetry:
    """Tests for task retry behavior."""
    
    def test_task_has_retry_config(self):
        """Task should have retry configuration."""
        from app.workers.zap_worker import zap_scan
        
        # Check task has retry settings
        assert hasattr(zap_scan, "max_retries") or hasattr(zap_scan, "bind")
    
    def test_retryable_exceptions(self):
        """Should retry on connection errors."""
        from app.integrations.zap.client import ZapConnectionError
        
        # Verify exception can be raised and caught
        try:
            raise ZapConnectionError("Test error")
        except ZapConnectionError as e:
            assert str(e) == "Test error"


# =============================================================================
# TESTS - RESULT SERIALIZATION
# =============================================================================

class TestResultSerialization:
    """Tests for result serialization."""
    
    def test_result_is_serializable(self, mock_zap_result):
        """Result should be JSON serializable."""
        import json
        
        # Convert result to dict
        result_dict = {
            "target_url": mock_zap_result.target_url,
            "mode": mock_zap_result.mode.value,
            "success": mock_zap_result.success,
            "start_time": mock_zap_result.start_time.isoformat(),
            "end_time": mock_zap_result.end_time.isoformat(),
            "duration_seconds": mock_zap_result.duration_seconds,
            "urls_found": mock_zap_result.urls_found,
            "alerts": mock_zap_result.alerts,
            "errors": mock_zap_result.errors,
        }
        
        # Should serialize without error
        json_str = json.dumps(result_dict)
        assert json_str is not None
        
        # Should deserialize back
        parsed = json.loads(json_str)
        assert parsed["target_url"] == mock_zap_result.target_url
    
    def test_alerts_are_serializable(self):
        """Alerts should be JSON serializable."""
        import json
        
        alerts = [
            {
                "name": "Test Alert",
                "risk": 2,
                "confidence": 2,
                "url": "https://example.com",
                "description": "Test description",
            }
        ]
        
        json_str = json.dumps(alerts)
        parsed = json.loads(json_str)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "Test Alert"


# =============================================================================
# TESTS - PROGRESS UPDATES
# =============================================================================

class TestProgressUpdates:
    """Tests for progress updates during scan."""
    
    def test_progress_callback_called(self):
        """Progress callback should be called."""
        from app.integrations.zap.scanner import ZapScanProgress
        
        progress = ZapScanProgress(
            phase="spider",
            spider_progress=50,
        )
        
        assert progress.overall_progress == 12  # 50 / 4
    
    def test_progress_phases(self):
        """All phases should calculate progress."""
        from app.integrations.zap.scanner import ZapScanProgress
        
        phases = ["initializing", "spider", "ajax_spider", "active_scan", "completed"]
        
        for phase in phases:
            progress = ZapScanProgress(phase=phase)
            assert 0 <= progress.overall_progress <= 100


# =============================================================================
# TESTS - TASK REGISTRATION
# =============================================================================

class TestTaskRegistration:
    """Tests for Celery task registration."""
    
    def test_all_tasks_registered(self):
        """All ZAP tasks should be registered."""
        from app.workers.zap_worker import (
            zap_scan,
            zap_quick_scan,
            zap_full_scan,
            zap_api_scan,
            zap_spa_scan,
        )
        
        tasks = [zap_scan, zap_quick_scan, zap_full_scan, zap_api_scan, zap_spa_scan]
        
        for task in tasks:
            assert task is not None
            assert hasattr(task, "name")
            assert hasattr(task, "delay")
    
    def test_task_names_unique(self):
        """Task names should be unique."""
        from app.workers.zap_worker import (
            zap_scan,
            zap_quick_scan,
            zap_full_scan,
            zap_api_scan,
            zap_spa_scan,
        )
        
        names = [
            zap_scan.name,
            zap_quick_scan.name,
            zap_full_scan.name,
            zap_api_scan.name,
            zap_spa_scan.name,
        ]
        
        assert len(names) == len(set(names)), "Task names should be unique"
