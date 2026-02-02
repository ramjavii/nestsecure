# =============================================================================
# NESTSECURE - Tests para Módulo Nuclei Integration
# =============================================================================
"""
Tests unitarios para el módulo de integración Nuclei.

Cubre:
- Modelos de datos (NucleiFinding, NucleiTemplate, NucleiScanResult, etc.)
- Perfiles de escaneo
- Parser JSON Lines
- Cliente NucleiScanner (modo mock)
- Excepciones
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Importar módulo Nuclei
from app.integrations.nuclei import (
    # Cliente
    NucleiScanner,
    check_nuclei_installed,
    
    # Parser
    NucleiParser,
    parse_nuclei_output,
    
    # Modelos
    NucleiScanResult,
    NucleiFinding,
    NucleiTemplate,
    NucleiMatcher,
    Severity,
    TemplateType,
    
    # Perfiles
    NucleiProfile,
    SCAN_PROFILES,
    get_profile,
    get_all_profiles,
    
    # Excepciones
    NucleiError,
    NucleiNotFoundError,
    NucleiTimeoutError,
    NucleiTemplateError,
    NucleiParseError,
    NucleiTargetError,
    NucleiExecutionError,
    NucleiRateLimitError,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_nuclei_jsonl():
    """JSON Lines de ejemplo para testing."""
    lines = [
        {
            "template-id": "http-missing-security-headers",
            "template": "http-missing-security-headers",
            "info": {
                "name": "HTTP Missing Security Headers",
                "author": ["projectdiscovery"],
                "severity": "info",
                "description": "Security headers are missing.",
                "tags": "misconfig,headers",
            },
            "type": "http",
            "host": "https://example.com",
            "matched-at": "https://example.com/",
            "ip": "93.184.216.34",
            "timestamp": "2024-01-15T10:30:00Z",
        },
        {
            "template-id": "cve-2021-44228-log4j-rce",
            "template": "cve-2021-44228-log4j-rce",
            "info": {
                "name": "Apache Log4j RCE (CVE-2021-44228)",
                "author": ["projectdiscovery", "dwisiswant0"],
                "severity": "critical",
                "description": "Apache Log4j2 vulnerable to RCE.",
                "reference": [
                    "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"
                ],
                "tags": "cve,rce,log4j",
                "classification": {
                    "cve-id": "CVE-2021-44228",
                    "cvss-score": 10.0,
                    "cwe-id": "CWE-502",
                }
            },
            "type": "http",
            "host": "https://example.com",
            "matched-at": "https://example.com/vulnerable",
            "ip": "93.184.216.34",
            "timestamp": "2024-01-15T10:35:00Z",
            "matcher-name": "log4j-detected",
            "matcher-type": "word",
            "matched": "${jndi:ldap://...",
            "extracted-results": ["log4j-2.14.1"],
        },
    ]
    return "\n".join(json.dumps(line) for line in lines)


@pytest.fixture
def mock_scanner():
    """Scanner en modo mock."""
    return NucleiScanner(mock_mode=True)


# =============================================================================
# TESTS DE MODELOS - SEVERITY
# =============================================================================

class TestSeverity:
    """Tests para enum Severity."""
    
    def test_from_string_critical(self):
        """Convertir string 'critical' a Severity."""
        assert Severity.from_string("critical") == Severity.CRITICAL
    
    def test_from_string_high(self):
        """Convertir string 'high' a Severity."""
        assert Severity.from_string("high") == Severity.HIGH
    
    def test_from_string_medium(self):
        """Convertir string 'medium' a Severity."""
        assert Severity.from_string("medium") == Severity.MEDIUM
    
    def test_from_string_low(self):
        """Convertir string 'low' a Severity."""
        assert Severity.from_string("low") == Severity.LOW
    
    def test_from_string_info(self):
        """Convertir string 'info' a Severity."""
        assert Severity.from_string("info") == Severity.INFO
    
    def test_from_string_unknown(self):
        """String desconocido retorna UNKNOWN."""
        assert Severity.from_string("invalid") == Severity.UNKNOWN
    
    def test_from_string_case_insensitive(self):
        """Conversión es case-insensitive."""
        assert Severity.from_string("CRITICAL") == Severity.CRITICAL
        assert Severity.from_string("Critical") == Severity.CRITICAL
    
    def test_severity_weight(self):
        """Pesos de severidad para ordenamiento."""
        assert Severity.CRITICAL.weight > Severity.HIGH.weight
        assert Severity.HIGH.weight > Severity.MEDIUM.weight
        assert Severity.MEDIUM.weight > Severity.LOW.weight
        assert Severity.LOW.weight > Severity.INFO.weight


class TestTemplateType:
    """Tests para enum TemplateType."""
    
    def test_from_string_http(self):
        """Convertir string 'http' a TemplateType."""
        assert TemplateType.from_string("http") == TemplateType.HTTP
    
    def test_from_string_dns(self):
        """Convertir string 'dns' a TemplateType."""
        assert TemplateType.from_string("dns") == TemplateType.DNS
    
    def test_from_string_network(self):
        """Convertir string 'network' a TemplateType."""
        assert TemplateType.from_string("network") == TemplateType.NETWORK
    
    def test_from_string_unknown(self):
        """String desconocido retorna UNKNOWN."""
        assert TemplateType.from_string("invalid") == TemplateType.UNKNOWN


# =============================================================================
# TESTS DE MODELOS - TEMPLATE
# =============================================================================

class TestNucleiTemplate:
    """Tests para NucleiTemplate."""
    
    def test_create_template(self):
        """Crear template con datos básicos."""
        template = NucleiTemplate(
            id="test-template",
            name="Test Template",
            author=["tester"],
            severity=Severity.HIGH,
            tags=["test", "web"],
        )
        
        assert template.id == "test-template"
        assert template.name == "Test Template"
        assert template.severity == Severity.HIGH
        assert "test" in template.tags
    
    def test_from_dict(self):
        """Crear template desde diccionario."""
        data = {
            "template-id": "cve-2021-44228",
            "info": {
                "name": "Log4j RCE",
                "author": ["projectdiscovery"],
                "severity": "critical",
                "tags": "cve,rce",
                "classification": {
                    "cve-id": "CVE-2021-44228",
                    "cvss-score": 10.0,
                }
            },
            "type": "http",
        }
        
        template = NucleiTemplate.from_dict(data)
        
        assert template.id == "cve-2021-44228"
        assert template.name == "Log4j RCE"
        assert template.severity == Severity.CRITICAL
        assert template.cve == "CVE-2021-44228"
        assert template.cvss == 10.0
        assert template.template_type == TemplateType.HTTP
    
    def test_from_dict_author_string(self):
        """Manejar author como string."""
        data = {
            "template-id": "test",
            "info": {
                "name": "Test",
                "author": "single-author",
                "severity": "info",
            }
        }
        
        template = NucleiTemplate.from_dict(data)
        assert "single-author" in template.author
    
    def test_to_dict(self):
        """Convertir template a diccionario."""
        template = NucleiTemplate(
            id="test",
            name="Test",
            severity=Severity.HIGH,
        )
        
        d = template.to_dict()
        
        assert d["id"] == "test"
        assert d["name"] == "Test"
        assert d["severity"] == "high"


# =============================================================================
# TESTS DE MODELOS - FINDING
# =============================================================================

class TestNucleiFinding:
    """Tests para NucleiFinding."""
    
    def test_create_finding(self):
        """Crear finding con datos básicos."""
        template = NucleiTemplate(
            id="test",
            name="Test Vuln",
            severity=Severity.HIGH,
        )
        
        finding = NucleiFinding(
            template=template,
            host="https://example.com",
            matched_at="https://example.com/vuln",
            ip="93.184.216.34",
        )
        
        assert finding.host == "https://example.com"
        assert finding.severity == Severity.HIGH
        assert finding.title == "Test Vuln"
    
    def test_from_json_line(self):
        """Crear finding desde línea JSON."""
        data = {
            "template-id": "cve-2021-44228",
            "info": {
                "name": "Log4j RCE",
                "author": ["projectdiscovery"],
                "severity": "critical",
                "classification": {
                    "cve-id": "CVE-2021-44228",
                    "cvss-score": 10.0,
                }
            },
            "type": "http",
            "host": "https://target.com",
            "matched-at": "https://target.com/app",
            "ip": "192.168.1.1",
            "timestamp": "2024-01-15T10:30:00Z",
            "matcher-name": "log4j-detected",
        }
        
        finding = NucleiFinding.from_json_line(data)
        
        assert finding.host == "https://target.com"
        assert finding.cve == "CVE-2021-44228"
        assert finding.cvss == 10.0
        assert finding.severity == Severity.CRITICAL
        assert finding.matcher.name == "log4j-detected"
    
    def test_to_dict(self):
        """Convertir finding a diccionario."""
        template = NucleiTemplate(
            id="test",
            name="Test",
            severity=Severity.MEDIUM,
        )
        
        finding = NucleiFinding(
            template=template,
            host="https://example.com",
            matched_at="https://example.com/path",
        )
        
        d = finding.to_dict()
        
        assert d["template_id"] == "test"
        assert d["severity"] == "medium"
        assert d["host"] == "https://example.com"


# =============================================================================
# TESTS DE MODELOS - SCAN RESULT
# =============================================================================

class TestNucleiScanResult:
    """Tests para NucleiScanResult."""
    
    def test_create_result(self):
        """Crear resultado de escaneo."""
        result = NucleiScanResult(
            targets=["https://example.com"],
            templates_used=["template1", "template2"],
            total_requests=100,
            matched_requests=5,
        )
        
        assert len(result.targets) == 1
        assert len(result.templates_used) == 2
        assert result.total_requests == 100
    
    def test_severity_counts(self):
        """Contar hallazgos por severidad."""
        findings = [
            NucleiFinding(
                template=NucleiTemplate(id="c1", name="C1", severity=Severity.CRITICAL),
                host="https://example.com",
                matched_at="https://example.com",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="h1", name="H1", severity=Severity.HIGH),
                host="https://example.com",
                matched_at="https://example.com",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="h2", name="H2", severity=Severity.HIGH),
                host="https://example.com",
                matched_at="https://example.com",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="i1", name="I1", severity=Severity.INFO),
                host="https://example.com",
                matched_at="https://example.com",
            ),
        ]
        
        result = NucleiScanResult(findings=findings)
        
        assert result.critical_count == 1
        assert result.high_count == 2
        assert result.medium_count == 0
        assert result.info_count == 1
        assert result.total_findings == 4
    
    def test_unique_cves(self):
        """Obtener CVEs únicos."""
        findings = [
            NucleiFinding(
                template=NucleiTemplate(
                    id="t1", name="T1", severity=Severity.HIGH, cve="CVE-2021-44228"
                ),
                host="h1",
                matched_at="h1",
            ),
            NucleiFinding(
                template=NucleiTemplate(
                    id="t2", name="T2", severity=Severity.HIGH, cve="CVE-2021-44228"
                ),
                host="h2",
                matched_at="h2",
            ),
            NucleiFinding(
                template=NucleiTemplate(
                    id="t3", name="T3", severity=Severity.HIGH, cve="CVE-2022-12345"
                ),
                host="h3",
                matched_at="h3",
            ),
        ]
        
        result = NucleiScanResult(findings=findings)
        
        assert len(result.unique_cves) == 2
        assert "CVE-2021-44228" in result.unique_cves
        assert "CVE-2022-12345" in result.unique_cves
    
    def test_findings_by_severity(self):
        """Agrupar hallazgos por severidad."""
        findings = [
            NucleiFinding(
                template=NucleiTemplate(id="c1", name="C1", severity=Severity.CRITICAL),
                host="h1",
                matched_at="h1",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="h1", name="H1", severity=Severity.HIGH),
                host="h1",
                matched_at="h1",
            ),
        ]
        
        result = NucleiScanResult(findings=findings)
        grouped = result.findings_by_severity
        
        assert len(grouped["critical"]) == 1
        assert len(grouped["high"]) == 1
        assert len(grouped["medium"]) == 0
    
    def test_findings_by_host(self):
        """Agrupar hallazgos por host."""
        findings = [
            NucleiFinding(
                template=NucleiTemplate(id="t1", name="T1", severity=Severity.HIGH),
                host="https://host1.com",
                matched_at="https://host1.com",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="t2", name="T2", severity=Severity.HIGH),
                host="https://host1.com",
                matched_at="https://host1.com",
            ),
            NucleiFinding(
                template=NucleiTemplate(id="t3", name="T3", severity=Severity.HIGH),
                host="https://host2.com",
                matched_at="https://host2.com",
            ),
        ]
        
        result = NucleiScanResult(findings=findings)
        grouped = result.findings_by_host
        
        assert len(grouped["https://host1.com"]) == 2
        assert len(grouped["https://host2.com"]) == 1
    
    def test_get_summary(self):
        """Obtener resumen del escaneo."""
        result = NucleiScanResult(
            targets=["https://example.com"],
            templates_used=["t1", "t2", "t3"],
            total_requests=100,
            error_count=5,
        )
        
        summary = result.get_summary()
        
        assert summary["targets_count"] == 1
        assert summary["templates_count"] == 3
        assert summary["total_requests"] == 100
        assert summary["errors"] == 5


# =============================================================================
# TESTS DE PERFILES
# =============================================================================

class TestNucleiProfiles:
    """Tests para perfiles de escaneo."""
    
    def test_get_profile_exists(self):
        """Obtener perfil existente."""
        profile = get_profile("quick")
        assert profile is not None
        assert profile.name == "quick"
    
    def test_get_profile_not_exists(self):
        """Perfil inexistente retorna None."""
        profile = get_profile("nonexistent")
        assert profile is None
    
    def test_get_all_profiles(self):
        """Obtener todos los perfiles."""
        profiles = get_all_profiles()
        assert len(profiles) > 0
        assert any(p.name == "quick" for p in profiles)
        assert any(p.name == "standard" for p in profiles)
        assert any(p.name == "full" for p in profiles)
    
    def test_profile_get_arguments(self):
        """Generar argumentos de línea de comandos."""
        profile = get_profile("quick")
        args = profile.get_arguments()
        
        assert "-json" in args  # Siempre incluye JSON output
        assert "-rate-limit" in args
        assert "-c" in args
    
    def test_profile_to_dict(self):
        """Convertir perfil a diccionario."""
        profile = get_profile("standard")
        d = profile.to_dict()
        
        assert "name" in d
        assert "display_name" in d
        assert "description" in d
        assert "tags" in d
    
    def test_scan_profiles_dict(self):
        """SCAN_PROFILES contiene perfiles esperados."""
        assert "quick" in SCAN_PROFILES
        assert "standard" in SCAN_PROFILES
        assert "full" in SCAN_PROFILES
        assert "cves" in SCAN_PROFILES
        assert "web" in SCAN_PROFILES


# =============================================================================
# TESTS DE PARSER
# =============================================================================

class TestNucleiParser:
    """Tests para NucleiParser."""
    
    def test_parse_output(self, sample_nuclei_jsonl):
        """Parsear output JSON Lines."""
        parser = NucleiParser()
        result = parser.parse_output(sample_nuclei_jsonl)
        
        assert len(result.findings) == 2
        assert "https://example.com" in result.targets
    
    def test_parse_finding_info(self, sample_nuclei_jsonl):
        """Parsear información de finding."""
        parser = NucleiParser()
        result = parser.parse_output(sample_nuclei_jsonl)
        
        # Buscar el finding crítico
        critical_finding = next(
            f for f in result.findings if f.severity == Severity.CRITICAL
        )
        
        assert critical_finding.template.name == "Apache Log4j RCE (CVE-2021-44228)"
        assert critical_finding.cve == "CVE-2021-44228"
        assert critical_finding.cvss == 10.0
    
    def test_parse_single_line(self):
        """Parsear una sola línea JSON."""
        parser = NucleiParser()
        line = json.dumps({
            "template-id": "test",
            "info": {
                "name": "Test",
                "severity": "high",
            },
            "host": "https://target.com",
            "matched-at": "https://target.com/path",
        })
        
        finding = parser._parse_line(line)
        
        assert finding is not None
        assert finding.template.id == "test"
        assert finding.severity == Severity.HIGH
    
    def test_parse_empty_line(self):
        """Línea vacía retorna None."""
        parser = NucleiParser()
        result = parser._parse_line("")
        assert result is None
    
    def test_parse_non_json_line(self):
        """Línea no JSON retorna None (logs)."""
        parser = NucleiParser()
        result = parser._parse_line("[INF] Starting scan...")
        assert result is None
    
    def test_parse_invalid_json(self):
        """JSON inválido genera error."""
        parser = NucleiParser()
        
        with pytest.raises(NucleiParseError):
            parser._parse_line("{invalid json", line_num=1)
    
    def test_parse_empty_output(self):
        """Output vacío retorna resultado vacío."""
        parser = NucleiParser()
        result = parser.parse_output("")
        
        assert len(result.findings) == 0
    
    def test_extract_stats(self):
        """Extraer estadísticas de stderr."""
        parser = NucleiParser()
        stderr = """
        [INF] Running scan...
        [INF] 1000 requests sent
        [INF] 5 matched
        [INF] 2 errors encountered
        """
        
        stats = parser.extract_stats(stderr)
        
        assert stats["total_requests"] == 1000
        assert stats["matched"] == 5
        assert stats["errors"] == 2


# =============================================================================
# TESTS DE CLIENTE
# =============================================================================

class TestNucleiScanner:
    """Tests para NucleiScanner."""
    
    def test_create_mock_scanner(self, mock_scanner):
        """Crear scanner en modo mock."""
        assert mock_scanner.mock_mode is True
    
    def test_mock_get_version(self, mock_scanner):
        """Obtener versión en modo mock."""
        version = mock_scanner.get_version()
        assert "Mock" in version
    
    @pytest.mark.asyncio
    async def test_mock_scan(self, mock_scanner):
        """Ejecutar escaneo en modo mock."""
        result = await mock_scanner.scan("https://example.com", profile="quick")
        
        assert isinstance(result, NucleiScanResult)
        assert "https://example.com" in result.targets
    
    @pytest.mark.asyncio
    async def test_mock_quick_scan(self, mock_scanner):
        """Escaneo rápido en modo mock."""
        result = await mock_scanner.quick_scan("https://example.com")
        
        assert isinstance(result, NucleiScanResult)
    
    @pytest.mark.asyncio
    async def test_mock_full_scan(self, mock_scanner):
        """Escaneo completo en modo mock."""
        result = await mock_scanner.full_scan("https://example.com")
        
        assert isinstance(result, NucleiScanResult)
    
    @pytest.mark.asyncio
    async def test_mock_cve_scan(self, mock_scanner):
        """Escaneo de CVEs en modo mock."""
        result = await mock_scanner.cve_scan("https://example.com")
        
        assert isinstance(result, NucleiScanResult)
    
    @pytest.mark.asyncio
    async def test_mock_web_scan(self, mock_scanner):
        """Escaneo web en modo mock."""
        result = await mock_scanner.web_scan("https://example.com")
        
        assert isinstance(result, NucleiScanResult)
    
    @pytest.mark.asyncio
    async def test_mock_update_templates(self, mock_scanner):
        """Actualizar templates en modo mock."""
        result = await mock_scanner.update_templates()
        assert result is True
    
    def test_validate_target_empty(self, mock_scanner):
        """Target vacío genera error."""
        with pytest.raises(NucleiTargetError):
            mock_scanner._validate_target("")
    
    def test_validate_target_dangerous_chars(self, mock_scanner):
        """Caracteres peligrosos generan error."""
        with pytest.raises(NucleiTargetError):
            mock_scanner._validate_target("https://example.com; rm -rf /")
    
    def test_validate_target_too_long(self, mock_scanner):
        """URL muy larga genera error."""
        with pytest.raises(NucleiTargetError):
            mock_scanner._validate_target("https://example.com/" + "a" * 3000)
    
    def test_validate_target_valid(self, mock_scanner):
        """Target válido no genera error."""
        mock_scanner._validate_target("https://example.com")
        mock_scanner._validate_target("http://192.168.1.1:8080")
        mock_scanner._validate_target("https://subdomain.example.com/path?query=1")


# =============================================================================
# TESTS DE EXCEPCIONES
# =============================================================================

class TestNucleiExceptions:
    """Tests para excepciones de Nuclei."""
    
    def test_nuclei_error(self):
        """NucleiError base."""
        error = NucleiError("Test error")
        assert str(error) == "Test error"
        d = error.to_dict()
        assert d["error_type"] == "NucleiError"
    
    def test_nuclei_not_found_error(self):
        """NucleiNotFoundError."""
        error = NucleiNotFoundError()
        assert "not installed" in str(error).lower() or "not found" in str(error).lower()
    
    def test_nuclei_not_found_error_with_path(self):
        """NucleiNotFoundError con ruta."""
        error = NucleiNotFoundError("/usr/bin/nuclei")
        assert "/usr/bin/nuclei" in str(error)
    
    def test_nuclei_timeout_error(self):
        """NucleiTimeoutError."""
        error = NucleiTimeoutError(300, "https://example.com")
        assert "300" in str(error)
        assert "https://example.com" in str(error)
        assert error.timeout == 300
        assert error.target == "https://example.com"
    
    def test_nuclei_template_error(self):
        """NucleiTemplateError."""
        error = NucleiTemplateError(
            template="cve-2021-44228",
            reason="Template not found"
        )
        assert error.template == "cve-2021-44228"
        assert error.reason == "Template not found"
    
    def test_nuclei_parse_error(self):
        """NucleiParseError."""
        error = NucleiParseError(
            message="Invalid JSON",
            raw_output="{invalid}",
            line_number=5
        )
        d = error.to_dict()
        assert d["details"]["line_number"] == 5
    
    def test_nuclei_target_error(self):
        """NucleiTargetError."""
        error = NucleiTargetError("https://bad;url", "Invalid character")
        assert error.target == "https://bad;url"
        assert error.reason == "Invalid character"
    
    def test_nuclei_execution_error(self):
        """NucleiExecutionError."""
        error = NucleiExecutionError(
            message="Exit code 1",
            exit_code=1,
            stderr="Error details"
        )
        assert error.exit_code == 1
        assert error.stderr == "Error details"
    
    def test_nuclei_rate_limit_error(self):
        """NucleiRateLimitError."""
        error = NucleiRateLimitError(
            target="https://example.com",
            retry_after=60
        )
        assert error.target == "https://example.com"
        assert error.retry_after == 60
        assert "60" in str(error)
