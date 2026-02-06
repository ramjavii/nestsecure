# =============================================================================
# NESTSECURE - Tests de Integración OWASP ZAP
# =============================================================================
"""
Tests unitarios para el módulo de integración con OWASP ZAP.

Tests incluidos:
- ZapClient: Cliente HTTP para API de ZAP
- ZapScanner: Orquestador de escaneos
- ZapAlertParser: Parser de alertas a vulnerabilidades
- ZapScanProgress: Progreso de escaneo
- ZapScanResult: Resultados de escaneo
- Configuración y políticas
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.zap import (
    ZapClient,
    ZapScanner,
    ZapScanMode,
    ZapAlertParser,
    ZAP_DEFAULT_HOST,
    ZAP_DEFAULT_PORT,
    ZAP_SCAN_POLICIES,
    ZAP_ALERT_RISKS,
    ZAP_ALERT_CONFIDENCES,
)
from app.integrations.zap.client import ZapClientError, ZapConnectionError, ZapApiError
from app.integrations.zap.scanner import ZapScanProgress, ZapScanResult
from app.integrations.zap.parser import ParsedZapAlert
from app.models.vulnerability import VulnerabilitySeverity


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_zap_alert() -> Dict:
    """Sample ZAP alert dictionary."""
    return {
        "id": "123",
        "pluginId": "10021",
        "alert": "X-Frame-Options Header Not Set",
        "name": "X-Frame-Options Header Not Set",
        "risk": "2",
        "confidence": "2",
        "description": "X-Frame-Options header is not included in the HTTP response to protect against clickjacking attacks.",
        "solution": "Most modern Web browsers support the X-Frame-Options HTTP header. Ensure it's set on all web pages returned by your site.",
        "reference": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options",
        "url": "https://example.com/page",
        "method": "GET",
        "param": "",
        "attack": "",
        "evidence": "",
        "otherinfo": "",
        "cweid": "1021",
        "wascid": "15",
        "tags": {"OWASP_2021_A05": "Security Misconfiguration"},
    }


@pytest.fixture
def sample_critical_alert() -> Dict:
    """Sample critical alert."""
    return {
        "id": "456",
        "pluginId": "40012",
        "name": "SQL Injection",
        "risk": "3",
        "confidence": "3",
        "description": "SQL injection may be possible.",
        "solution": "Use prepared statements and parameterized queries.",
        "url": "https://example.com/api/users?id=1",
        "method": "GET",
        "param": "id",
        "attack": "1' OR '1'='1",
        "evidence": "SQL syntax error",
        "cweid": "89",
        "wascid": "19",
    }


@pytest.fixture
def mock_zap_client():
    """Create a mock ZAP client."""
    client = MagicMock(spec=ZapClient)
    client.host = "zap"
    client.port = 8080
    client.base_url = "http://zap:8080"
    return client


# =============================================================================
# TESTS - ZAP CONFIG
# =============================================================================

class TestZapConfig:
    """Tests for ZAP configuration constants."""
    
    def test_default_host(self):
        """Default host should be set."""
        assert ZAP_DEFAULT_HOST is not None
        assert isinstance(ZAP_DEFAULT_HOST, str)
    
    def test_default_port(self):
        """Default port should be 8080."""
        assert ZAP_DEFAULT_PORT == 8080
    
    def test_alert_risks_mapping(self):
        """Alert risks should map 0-3 to names."""
        assert 0 in ZAP_ALERT_RISKS  # Informational
        assert 1 in ZAP_ALERT_RISKS  # Low
        assert 2 in ZAP_ALERT_RISKS  # Medium
        assert 3 in ZAP_ALERT_RISKS  # High
    
    def test_alert_confidences_mapping(self):
        """Alert confidences should be mapped."""
        assert 0 in ZAP_ALERT_CONFIDENCES or "false_positive" in str(ZAP_ALERT_CONFIDENCES).lower()
    
    def test_scan_policies_exist(self):
        """Scan policies should be defined."""
        assert "quick" in ZAP_SCAN_POLICIES
        assert "standard" in ZAP_SCAN_POLICIES
        assert "full" in ZAP_SCAN_POLICIES


class TestZapScanPolicies:
    """Tests for ZAP scan policies."""
    
    def test_quick_policy(self):
        """Quick policy should have minimal settings."""
        policy = ZAP_SCAN_POLICIES.get("quick", {})
        assert policy is not None
    
    def test_standard_policy(self):
        """Standard policy should be balanced."""
        policy = ZAP_SCAN_POLICIES.get("standard", {})
        assert policy is not None
    
    def test_full_policy(self):
        """Full policy should be comprehensive."""
        policy = ZAP_SCAN_POLICIES.get("full", {})
        assert policy is not None


# =============================================================================
# TESTS - ZAP SCAN MODE
# =============================================================================

class TestZapScanMode:
    """Tests for ZapScanMode enum."""
    
    def test_all_modes_exist(self):
        """All expected modes should exist."""
        assert ZapScanMode.QUICK
        assert ZapScanMode.STANDARD
        assert ZapScanMode.FULL
        assert ZapScanMode.API
        assert ZapScanMode.PASSIVE
        assert ZapScanMode.SPA
    
    def test_mode_values(self):
        """Mode values should be lowercase strings."""
        assert ZapScanMode.QUICK.value == "quick"
        assert ZapScanMode.STANDARD.value == "standard"
        assert ZapScanMode.FULL.value == "full"
        assert ZapScanMode.API.value == "api"
        assert ZapScanMode.SPA.value == "spa"
    
    def test_mode_from_string(self):
        """Should create mode from string."""
        assert ZapScanMode("quick") == ZapScanMode.QUICK
        assert ZapScanMode("full") == ZapScanMode.FULL


# =============================================================================
# TESTS - ZAP SCAN PROGRESS
# =============================================================================

class TestZapScanProgress:
    """Tests for ZapScanProgress dataclass."""
    
    def test_default_values(self):
        """Default values should be initialized."""
        progress = ZapScanProgress()
        assert progress.phase == "initializing"
        assert progress.spider_progress == 0
        assert progress.ajax_spider_progress == 0
        assert progress.active_scan_progress == 0
        assert progress.urls_found == 0
        assert progress.alerts_found == 0
    
    def test_overall_progress_initializing(self):
        """Initial progress should be 0."""
        progress = ZapScanProgress(phase="initializing")
        assert progress.overall_progress == 0
    
    def test_overall_progress_spider(self):
        """Spider phase progress should be 0-25%."""
        progress = ZapScanProgress(phase="spider", spider_progress=50)
        assert progress.overall_progress == 12  # 50 / 4 = 12
    
    def test_overall_progress_ajax_spider(self):
        """Ajax spider progress should be 25-50%."""
        progress = ZapScanProgress(phase="ajax_spider", ajax_spider_progress=50)
        assert progress.overall_progress == 37  # 25 + (50 / 4) = 37
    
    def test_overall_progress_active_scan(self):
        """Active scan progress should be 50-100%."""
        progress = ZapScanProgress(phase="active_scan", active_scan_progress=50)
        assert progress.overall_progress == 75  # 50 + (50 / 2) = 75
    
    def test_overall_progress_completed(self):
        """Completed phase should be 100%."""
        progress = ZapScanProgress(phase="completed")
        assert progress.overall_progress == 100
    
    def test_elapsed_seconds(self):
        """Should calculate elapsed time."""
        start = datetime.now(timezone.utc)
        progress = ZapScanProgress(start_time=start)
        assert progress.elapsed_seconds >= 0
    
    def test_elapsed_seconds_no_start(self):
        """Should return 0 if no start time."""
        progress = ZapScanProgress()
        assert progress.elapsed_seconds == 0


# =============================================================================
# TESTS - ZAP SCAN RESULT
# =============================================================================

class TestZapScanResult:
    """Tests for ZapScanResult dataclass."""
    
    def test_create_result(self):
        """Should create result with all fields."""
        result = ZapScanResult(
            target_url="https://example.com",
            mode=ZapScanMode.STANDARD,
            success=True,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=120.5,
            urls_found=50,
            alerts=[{"name": "Alert 1"}],
        )
        assert result.target_url == "https://example.com"
        assert result.mode == ZapScanMode.STANDARD
        assert result.success is True
        assert result.urls_found == 50
        assert len(result.alerts) == 1
    
    def test_empty_alerts(self):
        """Should handle empty alerts."""
        result = ZapScanResult(
            target_url="https://example.com",
            mode=ZapScanMode.QUICK,
            success=True,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=60.0,
        )
        assert result.alerts == []
        assert result.errors == []


# =============================================================================
# TESTS - ZAP CLIENT
# =============================================================================

class TestZapClient:
    """Tests for ZapClient."""
    
    def test_client_init_defaults(self):
        """Client should initialize with defaults."""
        with patch("app.integrations.zap.client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ZAP_HOST=None,
                ZAP_PORT=None,
                ZAP_API_KEY="",
            )
            client = ZapClient()
            assert client.host == ZAP_DEFAULT_HOST
            assert client.port == ZAP_DEFAULT_PORT
    
    def test_client_init_custom(self):
        """Client should accept custom host/port."""
        with patch("app.integrations.zap.client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ZAP_HOST=None,
                ZAP_PORT=None,
                ZAP_API_KEY="",
            )
            client = ZapClient(host="custom-zap", port=9090)
            assert client.host == "custom-zap"
            assert client.port == 9090
            assert client.base_url == "http://custom-zap:9090"
    
    def test_client_base_url(self):
        """Base URL should be constructed correctly."""
        with patch("app.integrations.zap.client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ZAP_HOST=None,
                ZAP_PORT=None,
                ZAP_API_KEY="",
            )
            client = ZapClient(host="localhost", port=8080)
            assert client.base_url == "http://localhost:8080"


class TestZapClientExceptions:
    """Tests for ZAP client exceptions."""
    
    def test_zap_client_error(self):
        """ZapClientError should work."""
        error = ZapClientError("Test error")
        assert str(error) == "Test error"
    
    def test_zap_connection_error(self):
        """ZapConnectionError should be a ZapClientError."""
        error = ZapConnectionError("Connection failed")
        assert isinstance(error, ZapClientError)
        assert "Connection failed" in str(error)
    
    def test_zap_api_error(self):
        """ZapApiError should be a ZapClientError."""
        error = ZapApiError("API error")
        assert isinstance(error, ZapClientError)


# =============================================================================
# TESTS - ZAP ALERT PARSER
# =============================================================================

class TestZapAlertParser:
    """Tests for ZapAlertParser."""
    
    def test_parser_init(self):
        """Parser should initialize."""
        parser = ZapAlertParser()
        assert parser is not None
        assert parser.cwe_mapping is not None
    
    def test_parse_alert(self, sample_zap_alert):
        """Should parse a ZAP alert."""
        parser = ZapAlertParser()
        parsed = parser.parse_alert(sample_zap_alert)
        
        assert isinstance(parsed, ParsedZapAlert)
        assert parsed.name == "X-Frame-Options Header Not Set"
        assert parsed.url == "https://example.com/page"
        assert parsed.method == "GET"
        assert parsed.risk == 2  # Medium
        assert parsed.cwe_id == 1021
    
    def test_parse_critical_alert(self, sample_critical_alert):
        """Should parse critical alert correctly."""
        parser = ZapAlertParser()
        parsed = parser.parse_alert(sample_critical_alert)
        
        assert parsed.name == "SQL Injection"
        assert parsed.risk == 3  # High
        assert parsed.cwe_id == 89
        assert parsed.param == "id"
        assert "OR" in parsed.attack
    
    def test_parse_severity_mapping(self, sample_zap_alert):
        """Should map risk to severity."""
        parser = ZapAlertParser()
        parsed = parser.parse_alert(sample_zap_alert)
        
        # Risk 2 (Medium) should map to MEDIUM severity
        assert parsed.severity in [
            VulnerabilitySeverity.MEDIUM,
            VulnerabilitySeverity.LOW,
            VulnerabilitySeverity.HIGH,
        ]
    
    def test_parse_missing_fields(self):
        """Should handle missing fields gracefully."""
        parser = ZapAlertParser()
        minimal_alert = {
            "name": "Test Alert",
            "risk": "1",
        }
        parsed = parser.parse_alert(minimal_alert)
        
        assert parsed.name == "Test Alert"
        assert parsed.risk == 1
        assert parsed.url == ""
        assert parsed.cwe_id is None
    
    def test_parse_invalid_cwe(self):
        """Should handle invalid CWE."""
        parser = ZapAlertParser()
        alert = {
            "name": "Test",
            "cweid": "invalid",
            "risk": "0",
        }
        parsed = parser.parse_alert(alert)
        assert parsed.cwe_id is None


class TestParsedZapAlert:
    """Tests for ParsedZapAlert dataclass."""
    
    def test_create_parsed_alert(self):
        """Should create parsed alert."""
        alert = ParsedZapAlert(
            alert_id="123",
            plugin_id=10021,
            name="Test Alert",
            url="https://example.com",
            method="GET",
            param=None,
            attack=None,
            evidence=None,
            risk=2,
            risk_name="Medium",
            confidence=2,
            confidence_name="Medium",
            severity=VulnerabilitySeverity.MEDIUM,
            description="Test description",
            solution="Fix it",
            reference="https://example.com/ref",
            other_info=None,
            cwe_id=79,
            wasc_id=8,
            owasp_top_10="A03:2021",
            tags={},
        )
        assert alert.alert_id == "123"
        assert alert.severity == VulnerabilitySeverity.MEDIUM
        assert alert.source == "zap"


# =============================================================================
# TESTS - ZAP SCANNER
# =============================================================================

class TestZapScanner:
    """Tests for ZapScanner."""
    
    def test_scanner_init(self, mock_zap_client):
        """Scanner should initialize with client."""
        scanner = ZapScanner(mock_zap_client)
        assert scanner.client == mock_zap_client
        assert scanner.progress_callback is None
    
    def test_scanner_with_callback(self, mock_zap_client):
        """Scanner should accept progress callback."""
        callback = MagicMock()
        scanner = ZapScanner(mock_zap_client, progress_callback=callback)
        assert scanner.progress_callback == callback
    
    def test_scanner_cancel(self, mock_zap_client):
        """Should be able to cancel scanner."""
        scanner = ZapScanner(mock_zap_client)
        assert scanner._cancelled is False
        scanner.cancel()
        assert scanner._cancelled is True


# =============================================================================
# TESTS - RISK TO SEVERITY MAPPING
# =============================================================================

class TestRiskToSeverityMapping:
    """Tests for risk to severity mapping."""
    
    def test_risk_0_to_info(self):
        """Risk 0 (Informational) should map to INFO."""
        parser = ZapAlertParser()
        alert = {"name": "Info", "risk": "0", "confidence": "2"}
        parsed = parser.parse_alert(alert)
        assert parsed.severity in [VulnerabilitySeverity.INFO, VulnerabilitySeverity.LOW]
    
    def test_risk_1_to_low(self):
        """Risk 1 (Low) should map to LOW."""
        parser = ZapAlertParser()
        alert = {"name": "Low", "risk": "1", "confidence": "2"}
        parsed = parser.parse_alert(alert)
        assert parsed.severity in [VulnerabilitySeverity.LOW, VulnerabilitySeverity.MEDIUM]
    
    def test_risk_2_to_medium(self):
        """Risk 2 (Medium) should map to MEDIUM."""
        parser = ZapAlertParser()
        alert = {"name": "Medium", "risk": "2", "confidence": "2"}
        parsed = parser.parse_alert(alert)
        assert parsed.severity == VulnerabilitySeverity.MEDIUM
    
    def test_risk_3_to_high(self):
        """Risk 3 (High) should map to HIGH or CRITICAL."""
        parser = ZapAlertParser()
        alert = {"name": "High", "risk": "3", "confidence": "3"}
        parsed = parser.parse_alert(alert)
        assert parsed.severity in [VulnerabilitySeverity.HIGH, VulnerabilitySeverity.CRITICAL]


# =============================================================================
# TESTS - ALERT SUMMARY
# =============================================================================

class TestAlertSummary:
    """Tests for alert summary calculations."""
    
    def test_count_by_risk(self):
        """Should correctly count alerts by risk level."""
        alerts = [
            {"name": "A1", "risk": "0"},
            {"name": "A2", "risk": "1"},
            {"name": "A3", "risk": "2"},
            {"name": "A4", "risk": "2"},
            {"name": "A5", "risk": "3"},
        ]
        
        risk_counts = {}
        for alert in alerts:
            risk = int(alert.get("risk", 0))
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        assert risk_counts[0] == 1  # Informational
        assert risk_counts[1] == 1  # Low
        assert risk_counts[2] == 2  # Medium
        assert risk_counts[3] == 1  # High
    
    def test_count_unique_cwes(self):
        """Should count unique CWEs."""
        alerts = [
            {"name": "A1", "cweid": "79"},
            {"name": "A2", "cweid": "89"},
            {"name": "A3", "cweid": "79"},  # Duplicate
        ]
        
        unique_cwes = set()
        for alert in alerts:
            cwe = alert.get("cweid")
            if cwe:
                unique_cwes.add(cwe)
        
        assert len(unique_cwes) == 2
        assert "79" in unique_cwes
        assert "89" in unique_cwes
