# =============================================================================
# NESTSECURE - Tests para Módulo Nmap Integration
# =============================================================================
"""
Tests unitarios para el módulo de integración Nmap.

Cubre:
- Modelos de datos (NmapHost, NmapPort, NmapScanResult, etc.)
- Perfiles de escaneo
- Parser XML
- Cliente NmapScanner (modo mock)
- Excepciones
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import xml.etree.ElementTree as ET

# Importar módulo Nmap
from app.integrations.nmap import (
    # Cliente
    NmapScanner,
    check_nmap_installed,
    
    # Parser
    NmapParser,
    parse_nmap_xml,
    
    # Modelos
    NmapScanResult,
    NmapHost,
    NmapPort,
    NmapVulnerability,
    NmapOS,
    PortState,
    HostState,
    
    # Perfiles
    NmapProfile,
    SCAN_PROFILES,
    get_profile,
    get_all_profiles,
    get_profiles_by_category,
    
    # Excepciones
    NmapError,
    NmapNotFoundError,
    NmapTimeoutError,
    NmapPermissionError,
    NmapParseError,
    NmapTargetError,
    NmapExecutionError,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_nmap_xml():
    """XML de ejemplo para testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV -sC -O 192.168.1.1" start="1700000000" version="7.94">
    <host starttime="1700000000" endtime="1700000060">
        <status state="up" reason="echo-reply"/>
        <address addr="192.168.1.1" addrtype="ipv4"/>
        <address addr="AA:BB:CC:DD:EE:FF" addrtype="mac" vendor="TestVendor"/>
        <hostnames>
            <hostname name="test-host.local" type="PTR"/>
        </hostnames>
        <ports>
            <port protocol="tcp" portid="22">
                <state state="open" reason="syn-ack"/>
                <service name="ssh" product="OpenSSH" version="8.9p1" conf="10">
                    <cpe>cpe:/a:openbsd:openssh:8.9p1</cpe>
                </service>
            </port>
            <port protocol="tcp" portid="80">
                <state state="open" reason="syn-ack"/>
                <service name="http" product="nginx" version="1.18.0" conf="10" tunnel="ssl">
                    <cpe>cpe:/a:nginx:nginx:1.18.0</cpe>
                </service>
                <script id="http-vuln-cve2021-41773" output="VULNERABLE: Apache Path Traversal">
                    <table key="ids">
                        <elem>CVE-2021-41773</elem>
                    </table>
                    <elem key="state">VULNERABLE</elem>
                </script>
            </port>
            <port protocol="tcp" portid="443">
                <state state="filtered" reason="no-response"/>
                <service name="https"/>
            </port>
        </ports>
        <os>
            <osmatch name="Linux 5.4 - 5.10" accuracy="96">
                <osclass osfamily="Linux" osgen="5.x">
                    <cpe>cpe:/o:linux:linux_kernel:5</cpe>
                </osclass>
            </osmatch>
        </os>
        <uptime seconds="86400"/>
        <distance value="1"/>
    </host>
    <runstats>
        <finished time="1700000060" timestr="Test" elapsed="60.00"/>
        <hosts up="1" down="0" total="1"/>
    </runstats>
</nmaprun>"""


@pytest.fixture
def mock_scanner():
    """Scanner en modo mock."""
    return NmapScanner(mock_mode=True)


# =============================================================================
# TESTS DE MODELOS
# =============================================================================

class TestPortState:
    """Tests para enum PortState."""
    
    def test_from_string_open(self):
        """Convertir string 'open' a PortState."""
        assert PortState.from_string("open") == PortState.OPEN
    
    def test_from_string_closed(self):
        """Convertir string 'closed' a PortState."""
        assert PortState.from_string("closed") == PortState.CLOSED
    
    def test_from_string_filtered(self):
        """Convertir string 'filtered' a PortState."""
        assert PortState.from_string("filtered") == PortState.FILTERED
    
    def test_from_string_unknown(self):
        """String desconocido retorna UNKNOWN."""
        assert PortState.from_string("invalid") == PortState.UNKNOWN
    
    def test_from_string_case_insensitive(self):
        """Conversión es case-insensitive."""
        assert PortState.from_string("OPEN") == PortState.OPEN
        assert PortState.from_string("Open") == PortState.OPEN


class TestHostState:
    """Tests para enum HostState."""
    
    def test_from_string_up(self):
        """Convertir string 'up' a HostState."""
        assert HostState.from_string("up") == HostState.UP
    
    def test_from_string_down(self):
        """Convertir string 'down' a HostState."""
        assert HostState.from_string("down") == HostState.DOWN
    
    def test_from_string_unknown(self):
        """String desconocido retorna UNKNOWN."""
        assert HostState.from_string("invalid") == HostState.UNKNOWN


class TestNmapPort:
    """Tests para NmapPort."""
    
    def test_create_port(self):
        """Crear puerto con datos básicos."""
        port = NmapPort(
            port=22,
            protocol="tcp",
            state=PortState.OPEN,
            service_name="ssh",
        )
        assert port.port == 22
        assert port.protocol == "tcp"
        assert port.state == PortState.OPEN
        assert port.service_name == "ssh"
    
    def test_is_open(self):
        """Propiedad is_open funciona correctamente."""
        open_port = NmapPort(port=22, protocol="tcp", state=PortState.OPEN)
        closed_port = NmapPort(port=23, protocol="tcp", state=PortState.CLOSED)
        
        assert open_port.is_open is True
        assert closed_port.is_open is False
    
    def test_service_string(self):
        """Generar string de servicio."""
        port = NmapPort(
            port=22,
            protocol="tcp",
            state=PortState.OPEN,
            service_name="ssh",
            product="OpenSSH",
            version="8.9",
        )
        assert port.service_string == "ssh OpenSSH 8.9"
    
    def test_service_string_unknown(self):
        """String de servicio cuando no hay datos."""
        port = NmapPort(port=22, protocol="tcp", state=PortState.OPEN)
        assert port.service_string == "unknown"
    
    def test_to_dict(self):
        """Convertir puerto a diccionario."""
        port = NmapPort(
            port=22,
            protocol="tcp",
            state=PortState.OPEN,
            service_name="ssh",
        )
        d = port.to_dict()
        
        assert d["port"] == 22
        assert d["protocol"] == "tcp"
        assert d["state"] == "open"
        assert d["service_name"] == "ssh"


class TestNmapVulnerability:
    """Tests para NmapVulnerability."""
    
    def test_create_vulnerability(self):
        """Crear vulnerabilidad con datos básicos."""
        vuln = NmapVulnerability(
            script_id="http-vuln-cve2021-41773",
            title="Apache Path Traversal",
            state="VULNERABLE",
            cvss=7.5,
            cves=["CVE-2021-41773"],
        )
        assert vuln.script_id == "http-vuln-cve2021-41773"
        assert vuln.cvss == 7.5
        assert "CVE-2021-41773" in vuln.cves
    
    def test_is_vulnerable(self):
        """Propiedad is_vulnerable funciona correctamente."""
        vulnerable = NmapVulnerability(
            script_id="test", title="Test", state="VULNERABLE"
        )
        not_vulnerable = NmapVulnerability(
            script_id="test", title="Test", state="NOT VULNERABLE"
        )
        likely = NmapVulnerability(
            script_id="test", title="Test", state="LIKELY VULNERABLE"
        )
        
        assert vulnerable.is_vulnerable is True
        assert not_vulnerable.is_vulnerable is False
        assert likely.is_vulnerable is True
    
    def test_severity_from_cvss(self):
        """Calcular severidad desde CVSS."""
        critical = NmapVulnerability(
            script_id="test", title="Test", state="VULNERABLE", cvss=9.5
        )
        high = NmapVulnerability(
            script_id="test", title="Test", state="VULNERABLE", cvss=7.5
        )
        medium = NmapVulnerability(
            script_id="test", title="Test", state="VULNERABLE", cvss=5.0
        )
        low = NmapVulnerability(
            script_id="test", title="Test", state="VULNERABLE", cvss=2.0
        )
        
        assert critical.severity == "critical"
        assert high.severity == "high"
        assert medium.severity == "medium"
        assert low.severity == "low"
    
    def test_primary_cve(self):
        """Obtener CVE primario."""
        vuln = NmapVulnerability(
            script_id="test",
            title="Test",
            state="VULNERABLE",
            cves=["CVE-2021-44228", "CVE-2021-45046"],
        )
        assert vuln.primary_cve == "CVE-2021-44228"
    
    def test_primary_cve_none(self):
        """CVE primario es None cuando no hay CVEs."""
        vuln = NmapVulnerability(
            script_id="test", title="Test", state="VULNERABLE"
        )
        assert vuln.primary_cve is None


class TestNmapHost:
    """Tests para NmapHost."""
    
    def test_create_host(self):
        """Crear host con datos básicos."""
        host = NmapHost(
            ip_address="192.168.1.1",
            state=HostState.UP,
            hostname="test.local",
        )
        assert host.ip_address == "192.168.1.1"
        assert host.state == HostState.UP
        assert host.hostname == "test.local"
    
    def test_is_up(self):
        """Propiedad is_up funciona correctamente."""
        up_host = NmapHost(ip_address="192.168.1.1", state=HostState.UP)
        down_host = NmapHost(ip_address="192.168.1.2", state=HostState.DOWN)
        
        assert up_host.is_up is True
        assert down_host.is_up is False
    
    def test_open_ports(self):
        """Filtrar solo puertos abiertos."""
        host = NmapHost(
            ip_address="192.168.1.1",
            state=HostState.UP,
            ports=[
                NmapPort(port=22, protocol="tcp", state=PortState.OPEN),
                NmapPort(port=23, protocol="tcp", state=PortState.CLOSED),
                NmapPort(port=80, protocol="tcp", state=PortState.OPEN),
            ],
        )
        
        assert len(host.open_ports) == 2
        assert host.open_port_numbers == [22, 80]
    
    def test_services(self):
        """Obtener nombres de servicios."""
        host = NmapHost(
            ip_address="192.168.1.1",
            state=HostState.UP,
            ports=[
                NmapPort(port=22, protocol="tcp", state=PortState.OPEN, service_name="ssh"),
                NmapPort(port=80, protocol="tcp", state=PortState.OPEN, service_name="http"),
            ],
        )
        
        assert "ssh" in host.services
        assert "http" in host.services
    
    def test_has_vulnerabilities(self):
        """Verificar si tiene vulnerabilidades."""
        host_with_vulns = NmapHost(
            ip_address="192.168.1.1",
            state=HostState.UP,
            vulnerabilities=[
                NmapVulnerability(script_id="test", title="Test", state="VULNERABLE"),
            ],
        )
        host_without_vulns = NmapHost(
            ip_address="192.168.1.2",
            state=HostState.UP,
        )
        
        assert host_with_vulns.has_vulnerabilities is True
        assert host_without_vulns.has_vulnerabilities is False


class TestNmapScanResult:
    """Tests para NmapScanResult."""
    
    def test_create_result(self):
        """Crear resultado de escaneo."""
        result = NmapScanResult(
            hosts=[
                NmapHost(ip_address="192.168.1.1", state=HostState.UP),
                NmapHost(ip_address="192.168.1.2", state=HostState.UP),
            ],
            hosts_up=2,
            hosts_total=3,
            elapsed_seconds=60.0,
        )
        
        assert len(result.hosts) == 2
        assert result.hosts_up == 2
        assert result.elapsed_seconds == 60.0
    
    def test_total_open_ports(self):
        """Contar total de puertos abiertos."""
        result = NmapScanResult(
            hosts=[
                NmapHost(
                    ip_address="192.168.1.1",
                    state=HostState.UP,
                    ports=[
                        NmapPort(port=22, protocol="tcp", state=PortState.OPEN),
                        NmapPort(port=80, protocol="tcp", state=PortState.OPEN),
                    ],
                ),
                NmapHost(
                    ip_address="192.168.1.2",
                    state=HostState.UP,
                    ports=[
                        NmapPort(port=443, protocol="tcp", state=PortState.OPEN),
                    ],
                ),
            ],
        )
        
        assert result.total_open_ports == 3
    
    def test_total_vulnerabilities(self):
        """Contar total de vulnerabilidades."""
        result = NmapScanResult(
            hosts=[
                NmapHost(
                    ip_address="192.168.1.1",
                    state=HostState.UP,
                    vulnerabilities=[
                        NmapVulnerability(script_id="v1", title="V1", state="VULNERABLE"),
                        NmapVulnerability(script_id="v2", title="V2", state="VULNERABLE"),
                    ],
                ),
            ],
        )
        
        assert result.total_vulnerabilities == 2
    
    def test_get_summary(self):
        """Obtener resumen del escaneo."""
        result = NmapScanResult(
            scan_type="standard",
            hosts_up=5,
            hosts_down=2,
            hosts_total=7,
        )
        
        summary = result.get_summary()
        
        assert summary["scan_type"] == "standard"
        assert summary["hosts_up"] == 5
        assert summary["hosts_total"] == 7


# =============================================================================
# TESTS DE PERFILES
# =============================================================================

class TestNmapProfiles:
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
    
    def test_profile_to_dict(self):
        """Convertir perfil a diccionario."""
        profile = get_profile("quick")
        d = profile.to_dict()
        
        assert "name" in d
        assert "display_name" in d
        assert "description" in d
    
    def test_profile_get_full_command(self):
        """Generar comando completo de Nmap."""
        profile = get_profile("quick")
        cmd = profile.get_full_command("192.168.1.1", "/tmp/output.xml")
        
        assert "nmap" in cmd
        assert "192.168.1.1" in cmd
        assert "/tmp/output.xml" in cmd
    
    def test_scan_profiles_dict(self):
        """SCAN_PROFILES contiene perfiles esperados."""
        assert "quick" in SCAN_PROFILES
        assert "standard" in SCAN_PROFILES
        assert "full" in SCAN_PROFILES
        assert "vulnerability" in SCAN_PROFILES
        assert "web" in SCAN_PROFILES
    
    def test_get_profiles_by_category(self):
        """Filtrar perfiles por categoría."""
        vuln_profiles = get_profiles_by_category("vulnerability")
        assert len(vuln_profiles) > 0


# =============================================================================
# TESTS DE PARSER
# =============================================================================

class TestNmapParser:
    """Tests para NmapParser."""
    
    def test_parse_string(self, sample_nmap_xml):
        """Parsear XML como string."""
        parser = NmapParser()
        result = parser.parse_string(sample_nmap_xml)
        
        assert len(result.hosts) == 1
        assert result.hosts_up == 1
        assert result.elapsed_seconds == 60.0
    
    def test_parse_host(self, sample_nmap_xml):
        """Parsear información de host."""
        parser = NmapParser()
        result = parser.parse_string(sample_nmap_xml)
        host = result.hosts[0]
        
        assert host.ip_address == "192.168.1.1"
        assert host.state == HostState.UP
        assert host.hostname == "test-host.local"
        assert host.mac_address == "AA:BB:CC:DD:EE:FF"
        assert host.vendor == "TestVendor"
    
    def test_parse_ports(self, sample_nmap_xml):
        """Parsear puertos."""
        parser = NmapParser()
        result = parser.parse_string(sample_nmap_xml)
        host = result.hosts[0]
        
        assert len(host.ports) == 3
        
        # Puerto 22
        ssh_port = next(p for p in host.ports if p.port == 22)
        assert ssh_port.state == PortState.OPEN
        assert ssh_port.service_name == "ssh"
        assert ssh_port.product == "OpenSSH"
        assert ssh_port.version == "8.9p1"
        assert ssh_port.cpe == "cpe:/a:openbsd:openssh:8.9p1"
        
        # Puerto 443 (filtered)
        https_port = next(p for p in host.ports if p.port == 443)
        assert https_port.state == PortState.FILTERED
    
    def test_parse_os(self, sample_nmap_xml):
        """Parsear detección de OS."""
        parser = NmapParser()
        result = parser.parse_string(sample_nmap_xml)
        host = result.hosts[0]
        
        assert host.os is not None
        assert "Linux" in host.os.name
        assert host.os.accuracy == 96
        assert host.os.family == "Linux"
    
    def test_parse_vulnerabilities(self, sample_nmap_xml):
        """Parsear vulnerabilidades de scripts."""
        parser = NmapParser()
        result = parser.parse_string(sample_nmap_xml)
        host = result.hosts[0]
        
        assert len(host.vulnerabilities) >= 1
        vuln = host.vulnerabilities[0]
        assert vuln.script_id == "http-vuln-cve2021-41773"
        assert "CVE-2021-41773" in vuln.cves
    
    def test_parse_invalid_xml(self):
        """Error al parsear XML inválido."""
        parser = NmapParser()
        
        with pytest.raises(NmapParseError):
            parser.parse_string("not valid xml")
    
    def test_parse_empty_xml(self):
        """Parsear XML vacío sin hosts."""
        xml = """<?xml version="1.0"?>
        <nmaprun scanner="nmap">
            <runstats>
                <hosts up="0" down="0" total="0"/>
            </runstats>
        </nmaprun>"""
        
        parser = NmapParser()
        result = parser.parse_string(xml)
        
        assert len(result.hosts) == 0
    
    def test_parse_nmap_xml_convenience(self, sample_nmap_xml):
        """Función de conveniencia parse_nmap_xml."""
        result = parse_nmap_xml(sample_nmap_xml)
        assert len(result.hosts) == 1


# =============================================================================
# TESTS DE CLIENTE
# =============================================================================

class TestNmapScanner:
    """Tests para NmapScanner."""
    
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
        result = await mock_scanner.scan("192.168.1.1", profile="quick")
        
        assert isinstance(result, NmapScanResult)
        assert len(result.hosts) >= 1
        assert result.hosts[0].ip_address == "192.168.1.1"
    
    @pytest.mark.asyncio
    async def test_mock_quick_scan(self, mock_scanner):
        """Escaneo rápido en modo mock."""
        result = await mock_scanner.quick_scan("192.168.1.1")
        
        assert isinstance(result, NmapScanResult)
    
    @pytest.mark.asyncio
    async def test_mock_discovery_scan(self, mock_scanner):
        """Escaneo de descubrimiento en modo mock."""
        result = await mock_scanner.discovery_scan("192.168.1.0/24")
        
        assert isinstance(result, NmapScanResult)
        assert len(result.hosts) >= 1
    
    @pytest.mark.asyncio
    async def test_mock_vulnerability_scan(self, mock_scanner):
        """Escaneo de vulnerabilidades en modo mock."""
        result = await mock_scanner.vulnerability_scan("192.168.1.1")
        
        assert isinstance(result, NmapScanResult)
        # El perfil de vulnerabilidades debería detectar algo
        assert result.total_vulnerabilities >= 0
    
    def test_check_root_privileges(self, mock_scanner):
        """Verificar privilegios de root."""
        # No debería fallar, solo retornar bool
        result = mock_scanner.check_root_privileges()
        assert isinstance(result, bool)
    
    def test_validate_target_empty(self, mock_scanner):
        """Target vacío genera error."""
        with pytest.raises(NmapTargetError):
            mock_scanner._validate_target("")
    
    def test_validate_target_dangerous_chars(self, mock_scanner):
        """Caracteres peligrosos generan error."""
        with pytest.raises(NmapTargetError):
            mock_scanner._validate_target("192.168.1.1; rm -rf /")
    
    def test_validate_target_valid(self, mock_scanner):
        """Target válido no genera error."""
        # No debería lanzar excepción
        mock_scanner._validate_target("192.168.1.1")
        mock_scanner._validate_target("192.168.1.0/24")
        mock_scanner._validate_target("example.com")


# =============================================================================
# TESTS DE EXCEPCIONES
# =============================================================================

class TestNmapExceptions:
    """Tests para excepciones de Nmap."""
    
    def test_nmap_error(self):
        """NmapError base."""
        error = NmapError("Test error")
        assert str(error) == "Test error"
        d = error.to_dict()
        assert d["error_type"] == "NmapError"
    
    def test_nmap_not_found_error(self):
        """NmapNotFoundError."""
        error = NmapNotFoundError()
        assert "not installed" in str(error).lower() or "not found" in str(error).lower()
    
    def test_nmap_timeout_error(self):
        """NmapTimeoutError."""
        error = NmapTimeoutError("192.168.1.1", 300)
        assert "300" in str(error)
        assert "192.168.1.1" in str(error)
        assert error.timeout == 300
        assert error.target == "192.168.1.1"
    
    def test_nmap_permission_error(self):
        """NmapPermissionError."""
        error = NmapPermissionError("SYN scan requires root")
        assert "root" in str(error).lower() or "permission" in str(error).lower()
    
    def test_nmap_parse_error(self):
        """NmapParseError."""
        error = NmapParseError("Invalid XML", raw_output="<invalid>")
        d = error.to_dict()
        assert "raw_output" in d.get("details", d)
    
    def test_nmap_target_error(self):
        """NmapTargetError."""
        error = NmapTargetError("192.168.1.1;evil", "Invalid character")
        assert error.target == "192.168.1.1;evil"
        assert error.reason == "Invalid character"
    
    def test_nmap_execution_error(self):
        """NmapExecutionError."""
        error = NmapExecutionError("Exit code 1", exit_code=1, stderr="Error details")
        assert error.exit_code == 1
        assert error.stderr == "Error details"
