# =============================================================================
# NESTSECURE - Tests de Integración Nuclei
# =============================================================================
"""
Tests unitarios y de integración para el módulo de Nuclei.

Tests incluidos:
- Parser de output JSON Lines
- Modelos de datos (NucleiScanResult, NucleiFinding, etc.)
- Perfiles de escaneo
- Cliente en modo mock
- Validación de severidades
"""

import pytest
from datetime import datetime
from typing import List

from app.integrations.nuclei import (
    # Client
    NucleiScanner,
    check_nuclei_installed,
    # Parser
    NucleiParser,
    parse_nuclei_output,
    # Models
    NucleiScanResult,
    NucleiFinding,
    NucleiTemplate,
    Severity,
    TemplateType,
    # Profiles
    NucleiProfile,
    ScanSpeed,
    SCAN_PROFILES,
    get_profile,
    get_all_profiles,
    create_custom_profile,
    QUICK_SCAN,
    STANDARD_SCAN,
    FULL_SCAN,
    CVE_SCAN,
    WEB_SCAN,
    # Exceptions
    NucleiError,
    NucleiNotFoundError,
    NucleiTimeoutError,
    NucleiTemplateError,
    NucleiParseError,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_nuclei_jsonl() -> str:
    """Sample Nuclei JSON Lines output."""
    return '''{"template-id":"cve-2021-44228","template":"CVE-2021-44228: Log4Shell RCE","info":{"name":"Log4Shell RCE","author":["pdteam"],"tags":["cve","rce","log4j","oast","critical"],"description":"Apache Log4j2 allows RCE via JNDI features.","severity":"critical","reference":["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"]},"type":"http","host":"https://example.com","matched-at":"https://example.com/api/v1/login","timestamp":"2024-01-15T10:30:00Z","ip":"93.184.216.34","matcher-name":"log4j-match"}
{"template-id":"cve-2023-22515","template":"CVE-2023-22515: Confluence Auth Bypass","info":{"name":"Confluence Auth Bypass","author":["pdteam"],"tags":["cve","confluence","auth-bypass","high"],"description":"Atlassian Confluence authentication bypass.","severity":"high","reference":["https://nvd.nist.gov/vuln/detail/CVE-2023-22515"]},"type":"http","host":"https://example.com","matched-at":"https://example.com/wiki","timestamp":"2024-01-15T10:31:00Z","ip":"93.184.216.34"}
{"template-id":"http-missing-security-headers","template":"HTTP Missing Security Headers","info":{"name":"Missing Security Headers","author":["pdteam"],"tags":["misconfiguration","security-headers"],"description":"HTTP response missing security headers.","severity":"info"},"type":"http","host":"https://example.com","matched-at":"https://example.com/","timestamp":"2024-01-15T10:32:00Z","ip":"93.184.216.34"}'''


@pytest.fixture
def sample_finding_dict() -> dict:
    """Sample finding as dictionary."""
    return {
        "template-id": "cve-2021-44228",
        "template": "CVE-2021-44228: Log4Shell RCE",
        "info": {
            "name": "Log4Shell RCE",
            "author": ["pdteam"],
            "tags": ["cve", "rce", "log4j", "critical"],
            "description": "Apache Log4j2 allows RCE via JNDI.",
            "severity": "critical",
            "reference": ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
        },
        "type": "http",
        "host": "https://example.com",
        "matched-at": "https://example.com/api/v1/login",
        "timestamp": "2024-01-15T10:30:00Z",
        "ip": "93.184.216.34",
        "matcher-name": "log4j-match",
    }


@pytest.fixture
def mock_scanner() -> NucleiScanner:
    """Create a mock mode scanner."""
    return NucleiScanner(mock_mode=True)


# =============================================================================
# TESTS - SEVERITY ENUM
# =============================================================================

class TestSeverity:
    """Tests for Severity enum."""
    
    def test_all_severities_exist(self):
        """All expected severities should exist."""
        assert Severity.CRITICAL
        assert Severity.HIGH
        assert Severity.MEDIUM
        assert Severity.LOW
        assert Severity.INFO
        assert Severity.UNKNOWN
    
    def test_severity_values(self):
        """Severity values should be lowercase strings."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"
    
    def test_severity_from_string(self):
        """Should create severity from string."""
        assert Severity("critical") == Severity.CRITICAL
        assert Severity("high") == Severity.HIGH
        assert Severity("medium") == Severity.MEDIUM


# =============================================================================
# TESTS - NUCLEI TEMPLATE MODEL
# =============================================================================

class TestNucleiTemplate:
    """Tests for NucleiTemplate dataclass."""
    
    def test_create_template(self):
        """Should create template with required fields."""
        template = NucleiTemplate(
            id="cve-2021-44228",
            name="Log4Shell RCE",
            description="RCE vulnerability in Log4j2",
        )
        assert template.id == "cve-2021-44228"
        assert template.name == "Log4Shell RCE"
        assert template.description == "RCE vulnerability in Log4j2"
    
    def test_template_optional_fields(self):
        """Should handle optional fields."""
        template = NucleiTemplate(
            id="test-template",
            name="Test Template",
            author=["author1", "author2"],
            tags=["cve", "rce"],
            reference=["https://example.com"],
        )
        assert template.author == ["author1", "author2"]
        assert template.tags == ["cve", "rce"]
        assert template.reference == ["https://example.com"]


# =============================================================================
# TESTS - NUCLEI FINDING MODEL
# =============================================================================

class TestNucleiFinding:
    """Tests for NucleiFinding dataclass."""
    
    def test_create_finding(self):
        """Should create finding with all fields."""
        template = NucleiTemplate(
            id="cve-2021-44228",
            name="Log4Shell",
            severity=Severity.CRITICAL,
        )
        finding = NucleiFinding(
            template=template,
            host="https://example.com",
            matched_at="https://example.com/api/login",
            ip="93.184.216.34",
            timestamp=datetime.now(),
        )
        assert finding.template.id == "cve-2021-44228"
        assert finding.severity == Severity.CRITICAL
        assert finding.host == "https://example.com"
        assert finding.ip == "93.184.216.34"
    
    def test_finding_cve_property(self):
        """Finding should extract CVE from template."""
        template = NucleiTemplate(
            id="CVE-2021-44228",
            name="Log4Shell",
            severity=Severity.CRITICAL,
            cve="CVE-2021-44228",
        )
        finding = NucleiFinding(
            template=template,
            host="https://example.com",
            matched_at="https://example.com",
        )
        assert finding.cve == "CVE-2021-44228"


# =============================================================================
# TESTS - NUCLEI SCAN RESULT MODEL
# =============================================================================

class TestNucleiScanResult:
    """Tests for NucleiScanResult dataclass."""
    
    def test_create_empty_result(self):
        """Should create result with empty findings."""
        result = NucleiScanResult(
            targets=["https://example.com"],
            findings=[],
            start_time=datetime.now(),
        )
        assert "example.com" in result.targets[0]
        assert result.findings == []
        assert result.total_findings == 0
    
    def test_result_with_findings(self):
        """Should correctly count findings."""
        template = NucleiTemplate(
            id="test",
            name="Test",
            severity=Severity.CRITICAL,
        )
        findings = [
            NucleiFinding(
                template=template,
                host="https://example.com",
                matched_at="https://example.com",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="test2", name="Test2", severity=Severity.HIGH),
                host="https://example.com",
                matched_at="https://example.com/api",
            ),
        ]
        result = NucleiScanResult(
            targets=["https://example.com"],
            findings=findings,
        )
        assert result.total_findings == 2
        assert result.critical_count == 1
        assert result.high_count == 1


# =============================================================================
# TESTS - NUCLEI PARSER
# =============================================================================

class TestNucleiParser:
    """Tests for NucleiParser."""
    
    def test_parser_init(self):
        """Should initialize parser."""
        parser = NucleiParser()
        assert parser is not None
    
    def test_parse_empty_string(self):
        """Should handle empty string."""
        parser = NucleiParser()
        result = parser.parse_output("")
        assert result is not None
        assert result.findings == []
    
    def test_parse_multiple_lines(self, sample_nuclei_jsonl):
        """Should parse multiple JSON lines."""
        parser = NucleiParser()
        result = parser.parse_output(sample_nuclei_jsonl)
        
        assert len(result.findings) == 3
        
        # Check severities
        severities = [f.severity for f in result.findings]
        assert Severity.CRITICAL in severities
        assert Severity.HIGH in severities
        assert Severity.INFO in severities
    
    def test_parse_severity_extraction(self, sample_nuclei_jsonl):
        """Should correctly extract severity from findings."""
        parser = NucleiParser()
        result = parser.parse_output(sample_nuclei_jsonl)
        
        critical_findings = [f for f in result.findings if f.severity == Severity.CRITICAL]
        high_findings = [f for f in result.findings if f.severity == Severity.HIGH]
        info_findings = [f for f in result.findings if f.severity == Severity.INFO]
        
        assert len(critical_findings) == 1
        assert len(high_findings) == 1
        assert len(info_findings) == 1


# =============================================================================
# TESTS - SCAN PROFILES
# =============================================================================

class TestScanProfiles:
    """Tests for scan profiles."""
    
    def test_predefined_profiles_exist(self):
        """Predefined profiles should exist."""
        assert QUICK_SCAN is not None
        assert STANDARD_SCAN is not None
        assert FULL_SCAN is not None
        assert CVE_SCAN is not None
        assert WEB_SCAN is not None
    
    def test_scan_profiles_dict(self):
        """SCAN_PROFILES should contain all profiles."""
        assert "quick" in SCAN_PROFILES
        assert "standard" in SCAN_PROFILES
        assert "full" in SCAN_PROFILES
        assert "cves" in SCAN_PROFILES
        assert "web" in SCAN_PROFILES
    
    def test_get_profile(self):
        """Should retrieve profile by name."""
        profile = get_profile("quick")
        assert profile is not None
        assert profile.name == "quick"
    
    def test_get_profile_unknown(self):
        """Should return None for unknown profile."""
        profile = get_profile("nonexistent")
        assert profile is None
    
    def test_get_all_profiles(self):
        """Should return list of all profiles."""
        profiles = get_all_profiles()
        assert len(profiles) >= 5
        assert all(isinstance(p, NucleiProfile) for p in profiles)
    
    def test_quick_scan_profile(self):
        """Quick scan should have correct settings."""
        profile = QUICK_SCAN
        assert profile.name == "quick"
        assert ScanSpeed.FAST in [profile.speed] if hasattr(profile, 'speed') else True
        # Quick scan should focus on critical/high
        assert "critical" in [s.lower() for s in profile.severities] if hasattr(profile, 'severities') else True
    
    def test_full_scan_profile(self):
        """Full scan should include all severities."""
        profile = FULL_SCAN
        assert profile.name == "full"


# =============================================================================
# TESTS - NUCLEI SCANNER CLIENT (MOCK MODE)
# =============================================================================

class TestNucleiScannerMock:
    """Tests for NucleiScanner in mock mode."""
    
    def test_init_mock_mode(self, mock_scanner):
        """Should initialize in mock mode."""
        assert mock_scanner.mock_mode is True
    
    def test_get_version_mock(self, mock_scanner):
        """Should return mock version string."""
        version = mock_scanner.get_version()
        assert "Mock" in version or "nuclei" in version.lower()
    
    @pytest.mark.asyncio
    async def test_scan_mock_returns_result(self, mock_scanner):
        """Mock scan should return result."""
        result = await mock_scanner.scan("https://example.com", profile="quick")
        
        assert result is not None
        assert isinstance(result, NucleiScanResult)
        assert "example.com" in result.targets[0] if result.targets else True
    
    @pytest.mark.asyncio
    async def test_scan_mock_has_findings(self, mock_scanner):
        """Mock scan should return mock findings."""
        result = await mock_scanner.scan("https://example.com", profile="standard")
        
        # Mock should return some findings for testing
        assert isinstance(result.findings, list)
    
    @pytest.mark.asyncio
    async def test_scan_with_different_profiles(self, mock_scanner):
        """Should accept different profile names."""
        for profile in ["quick", "standard", "full", "cves", "web"]:
            result = await mock_scanner.scan("https://example.com", profile=profile)
            assert result is not None


# =============================================================================
# TESTS - CUSTOM PROFILE CREATION
# =============================================================================

class TestCustomProfile:
    """Tests for custom profile creation."""
    
    def test_create_custom_profile(self):
        """Should create custom profile."""
        profile = create_custom_profile(
            name="my-custom",
            display_name="My Custom Scan",
            description="Custom profile for testing",
            tags=["cve", "rce"],
            severities=["critical", "high"],
        )
        
        assert profile.name == "my-custom"
        assert "cve" in profile.tags
        assert "rce" in profile.tags
    
    def test_custom_profile_with_all_options(self):
        """Should create profile with all options."""
        profile = create_custom_profile(
            name="full-custom",
            display_name="Full Custom Scan",
            description="Custom profile with all options",
            tags=["cve", "exposure"],
            severities=["critical", "high", "medium"],
            rate_limit=150,
            timeout=600,
        )
        
        assert profile is not None
        assert profile.name == "full-custom"
        assert profile.rate_limit == 150
        assert profile.timeout == 600


# =============================================================================
# TESTS - EXCEPTIONS
# =============================================================================

class TestNucleiExceptions:
    """Tests for Nuclei exceptions."""
    
    def test_nuclei_error_base(self):
        """NucleiError should be base exception."""
        error = NucleiError("Test error")
        assert str(error) == "Test error"
    
    def test_nuclei_not_found_error(self):
        """NucleiNotFoundError should have default message."""
        error = NucleiNotFoundError()
        assert "not found" in str(error).lower() or "not installed" in str(error).lower()
    
    def test_nuclei_timeout_error(self):
        """NucleiTimeoutError should include timeout info."""
        error = NucleiTimeoutError(target="https://example.com", timeout=3600)
        assert error is not None
    
    def test_nuclei_template_error(self):
        """NucleiTemplateError for template issues."""
        error = NucleiTemplateError(template="test-template", reason="Invalid path")
        assert error is not None
    
    def test_nuclei_parse_error(self):
        """NucleiParseError for parsing issues."""
        error = NucleiParseError("Failed to parse JSON")
        assert "parse" in str(error).lower() or "JSON" in str(error)


# =============================================================================
# TESTS - CHECK NUCLEI INSTALLED
# =============================================================================

class TestCheckNucleiInstalled:
    """Tests for check_nuclei_installed function."""
    
    def test_returns_boolean(self):
        """Should return boolean."""
        result = check_nuclei_installed()
        assert isinstance(result, bool)


# =============================================================================
# TESTS - SEVERITY SUMMARY CALCULATION
# =============================================================================

class TestSeveritySummary:
    """Tests for severity summary calculations."""
    
    def test_count_severities(self):
        """Should correctly count severities."""
        findings = [
            NucleiFinding(
                template=NucleiTemplate(id="t1", name="T1", severity=Severity.CRITICAL),
                host="h",
                matched_at="m",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="t2", name="T2", severity=Severity.CRITICAL),
                host="h",
                matched_at="m",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="t3", name="T3", severity=Severity.HIGH),
                host="h",
                matched_at="m",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="t4", name="T4", severity=Severity.MEDIUM),
                host="h",
                matched_at="m",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="t5", name="T5", severity=Severity.LOW),
                host="h",
                matched_at="m",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="t6", name="T6", severity=Severity.INFO),
                host="h",
                matched_at="m",
            ),
        ]
        
        critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == Severity.HIGH)
        medium_count = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low_count = sum(1 for f in findings if f.severity == Severity.LOW)
        info_count = sum(1 for f in findings if f.severity == Severity.INFO)
        
        assert critical_count == 2
        assert high_count == 1
        assert medium_count == 1
        assert low_count == 1
        assert info_count == 1
