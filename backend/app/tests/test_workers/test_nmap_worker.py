# =============================================================================
# NESTSECURE - Tests de Nmap Worker
# =============================================================================
"""
Tests para el worker de Nmap.

Incluye:
- Tests unitarios de parsing XML
- Tests de tareas con mocks
- Tests de integración con DB
- Tests de manejo de errores
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from app.workers.nmap_worker import (
    parse_discovery_xml,
    parse_port_scan_xml,
    run_nmap,
)


# =============================================================================
# Sample XML Data for Testing
# =============================================================================
SAMPLE_DISCOVERY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sn 192.168.1.0/24" start="1706500000">
<host>
    <status state="up" reason="arp-response"/>
    <address addr="192.168.1.1" addrtype="ipv4"/>
    <address addr="AA:BB:CC:DD:EE:FF" addrtype="mac" vendor="Cisco"/>
    <hostnames>
        <hostname name="router.local" type="PTR"/>
    </hostnames>
</host>
<host>
    <status state="up" reason="syn-ack"/>
    <address addr="192.168.1.100" addrtype="ipv4"/>
    <hostnames>
        <hostname name="server.local" type="PTR"/>
    </hostnames>
</host>
<host>
    <status state="down" reason="no-response"/>
    <address addr="192.168.1.50" addrtype="ipv4"/>
</host>
</nmaprun>
"""

SAMPLE_PORT_SCAN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV 192.168.1.100" start="1706500000">
<host>
    <status state="up"/>
    <address addr="192.168.1.100" addrtype="ipv4"/>
    <address addr="DE:AD:BE:EF:CA:FE" addrtype="mac"/>
    <hostnames>
        <hostname name="webserver.local" type="PTR"/>
    </hostnames>
    <os>
        <osmatch name="Linux 5.4" accuracy="96"/>
    </os>
    <ports>
        <port protocol="tcp" portid="22">
            <state state="open" reason="syn-ack"/>
            <service name="ssh" product="OpenSSH" version="8.9p1"/>
        </port>
        <port protocol="tcp" portid="80">
            <state state="open" reason="syn-ack"/>
            <service name="http" product="nginx" version="1.24.0" tunnel="ssl"/>
            <script id="banner" output="nginx/1.24.0"/>
        </port>
        <port protocol="tcp" portid="443">
            <state state="open" reason="syn-ack"/>
            <service name="https" product="nginx" version="1.24.0" tunnel="ssl">
                <cpe>cpe:/a:nginx:nginx:1.24.0</cpe>
            </service>
        </port>
        <port protocol="tcp" portid="3306">
            <state state="filtered" reason="no-response"/>
            <service name="mysql"/>
        </port>
    </ports>
</host>
</nmaprun>
"""

SAMPLE_EMPTY_XML = """<?xml version="1.0"?>
<nmaprun scanner="nmap">
</nmaprun>
"""

SAMPLE_INVALID_XML = """not valid xml at all"""


# =============================================================================
# Tests: parse_discovery_xml
# =============================================================================
class TestParseDiscoveryXml:
    """Tests para la función parse_discovery_xml."""
    
    def test_parse_discovery_finds_up_hosts(self):
        """Debe encontrar hosts con estado 'up'."""
        hosts = parse_discovery_xml(SAMPLE_DISCOVERY_XML)
        
        assert len(hosts) == 2
        
        # Primer host (router)
        router = hosts[0]
        assert router["ip_address"] == "192.168.1.1"
        assert router["hostname"] == "router.local"
        assert router["mac_address"] == "AA:BB:CC:DD:EE:FF"
        assert router["vendor"] == "Cisco"
        
        # Segundo host (server)
        server = hosts[1]
        assert server["ip_address"] == "192.168.1.100"
        assert server["hostname"] == "server.local"
    
    def test_parse_discovery_ignores_down_hosts(self):
        """No debe incluir hosts con estado 'down'."""
        hosts = parse_discovery_xml(SAMPLE_DISCOVERY_XML)
        
        ips = [h["ip_address"] for h in hosts]
        assert "192.168.1.50" not in ips
    
    def test_parse_discovery_empty_xml(self):
        """Debe retornar lista vacía para XML sin hosts."""
        hosts = parse_discovery_xml(SAMPLE_EMPTY_XML)
        assert hosts == []
    
    def test_parse_discovery_invalid_xml(self):
        """Debe retornar lista vacía para XML inválido."""
        hosts = parse_discovery_xml(SAMPLE_INVALID_XML)
        assert hosts == []
    
    def test_parse_discovery_handles_missing_hostname(self):
        """Debe manejar hosts sin hostname."""
        xml = """<?xml version="1.0"?>
        <nmaprun>
        <host>
            <status state="up"/>
            <address addr="10.0.0.1" addrtype="ipv4"/>
        </host>
        </nmaprun>
        """
        hosts = parse_discovery_xml(xml)
        
        assert len(hosts) == 1
        assert hosts[0]["ip_address"] == "10.0.0.1"
        assert hosts[0]["hostname"] is None


# =============================================================================
# Tests: parse_port_scan_xml
# =============================================================================
class TestParsePortScanXml:
    """Tests para la función parse_port_scan_xml."""
    
    def test_parse_port_scan_extracts_host_info(self):
        """Debe extraer información del host correctamente."""
        result = parse_port_scan_xml(SAMPLE_PORT_SCAN_XML)
        
        host_info = result["host_info"]
        assert host_info["ip_address"] == "192.168.1.100"
        assert host_info["hostname"] == "webserver.local"
        assert host_info["mac_address"] == "DE:AD:BE:EF:CA:FE"
        assert host_info["os_match"] == "Linux 5.4"
        assert host_info["os_accuracy"] == 96
    
    def test_parse_port_scan_extracts_services(self):
        """Debe extraer servicios correctamente."""
        result = parse_port_scan_xml(SAMPLE_PORT_SCAN_XML)
        
        services = result["services"]
        assert len(services) == 4
        
        # SSH
        ssh = next(s for s in services if s["port"] == 22)
        assert ssh["protocol"] == "tcp"
        assert ssh["state"] == "open"
        assert ssh["service_name"] == "ssh"
        assert ssh["product"] == "OpenSSH"
        assert ssh["version"] == "8.9p1"
        
        # HTTP
        http = next(s for s in services if s["port"] == 80)
        assert http["service_name"] == "http"
        assert http["product"] == "nginx"
        assert http["banner"] == "nginx/1.24.0"
        
        # HTTPS with CPE
        https = next(s for s in services if s["port"] == 443)
        assert https["cpe"] == "cpe:/a:nginx:nginx:1.24.0"
        assert https["ssl_enabled"] is True
        
        # Filtered port
        mysql = next(s for s in services if s["port"] == 3306)
        assert mysql["state"] == "filtered"
    
    def test_parse_port_scan_empty_xml(self):
        """Debe manejar XML sin hosts."""
        result = parse_port_scan_xml(SAMPLE_EMPTY_XML)
        
        assert result["host_info"]["ip_address"] is None
        assert result["services"] == []
    
    def test_parse_port_scan_invalid_xml(self):
        """Debe manejar XML inválido."""
        result = parse_port_scan_xml(SAMPLE_INVALID_XML)
        
        assert result["host_info"]["ip_address"] is None
        assert result["services"] == []


# =============================================================================
# Tests: run_nmap
# =============================================================================
class TestRunNmap:
    """Tests para la función run_nmap."""
    
    @patch("subprocess.run")
    def test_run_nmap_success(self, mock_run):
        """Debe ejecutar nmap y retornar stdout."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="<xml>result</xml>",
            stderr=""
        )
        
        result = run_nmap(["-sn", "192.168.1.0/24"])
        
        assert result == "<xml>result</xml>"
        mock_run.assert_called_once()
        
        # Verificar argumentos
        call_args = mock_run.call_args[0][0]
        assert "-sn" in call_args
        assert "192.168.1.0/24" in call_args
        assert "-oX" in call_args
        assert "-" in call_args  # Output to stdout
    
    @patch("subprocess.run")
    def test_run_nmap_timeout(self, mock_run):
        """Debe propagar TimeoutExpired."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="nmap", timeout=60)
        
        with pytest.raises(subprocess.TimeoutExpired):
            run_nmap(["-sn", "192.168.1.0/24"], timeout=60)
    
    @patch("subprocess.run")
    def test_run_nmap_error(self, mock_run):
        """Debe propagar CalledProcessError."""
        import subprocess
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: Network unreachable"
        )
        
        with pytest.raises(subprocess.CalledProcessError):
            run_nmap(["-sn", "192.168.1.0/24"])
    
    @patch("subprocess.run")
    def test_run_nmap_host_down_not_error(self, mock_run):
        """No debe lanzar error si el host parece down."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="<xml>empty</xml>",
            stderr="Note: Host seems down."
        )
        
        # No debe lanzar excepción
        result = run_nmap(["-sn", "192.168.1.1"])
        assert result == "<xml>empty</xml>"


# =============================================================================
# Tests: Discovery Scan Task
# =============================================================================
class TestDiscoveryScanTask:
    """Tests para la tarea discovery_scan."""
    
    @patch("app.workers.nmap_worker.get_sync_db")
    @patch("app.workers.nmap_worker.run_nmap")
    def test_discovery_scan_creates_assets(self, mock_run_nmap, mock_get_db):
        """Debe crear assets para hosts descubiertos."""
        from app.workers.nmap_worker import discovery_scan
        
        # Mock nmap output
        mock_run_nmap.return_value = SAMPLE_DISCOVERY_XML
        
        # Mock database
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_get_db.return_value = mock_db
        
        # Execute
        result = discovery_scan("192.168.1.0/24", "org-123")
        
        # Verify
        assert result["hosts_found"] == 2
        assert result["hosts_created"] == 2
        assert len(result["hosts"]) == 2
        mock_db.commit.assert_called()
    
    @patch("app.workers.nmap_worker.get_sync_db")
    @patch("app.workers.nmap_worker.run_nmap")
    def test_discovery_scan_updates_existing_assets(self, mock_run_nmap, mock_get_db):
        """Debe actualizar assets existentes."""
        from app.workers.nmap_worker import discovery_scan
        
        mock_run_nmap.return_value = SAMPLE_DISCOVERY_XML
        
        # Mock existing asset
        mock_asset = Mock()
        mock_asset.hostname = None
        mock_asset.mac_address = None
        
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_asset
        mock_get_db.return_value = mock_db
        
        result = discovery_scan("192.168.1.0/24", "org-123")
        
        assert result["hosts_updated"] == 2
        assert result["hosts_created"] == 0


# =============================================================================
# Tests: Port Scan Task
# =============================================================================
class TestPortScanTask:
    """Tests para la tarea port_scan."""
    
    @patch("app.workers.nmap_worker.get_sync_db")
    @patch("app.workers.nmap_worker.run_nmap")
    def test_port_scan_creates_services(self, mock_run_nmap, mock_get_db):
        """Debe crear servicios para puertos encontrados."""
        from app.workers.nmap_worker import port_scan
        
        mock_run_nmap.return_value = SAMPLE_PORT_SCAN_XML
        
        # Mock asset
        mock_asset = Mock()
        mock_asset.id = "asset-123"
        mock_asset.ip_address = "192.168.1.100"
        mock_asset.hostname = None
        
        mock_db = MagicMock()
        # First call returns asset, subsequent calls for services return None
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_asset,  # Asset lookup
            None, None, None, None,  # Service lookups (4 services)
        ]
        mock_get_db.return_value = mock_db
        
        result = port_scan("asset-123", "quick")
        
        assert result["services_found"] == 4
        assert result["services_created"] == 4
        mock_db.commit.assert_called()
    
    @patch("app.workers.nmap_worker.get_sync_db")
    @patch("app.workers.nmap_worker.run_nmap")
    def test_port_scan_asset_not_found(self, mock_run_nmap, mock_get_db):
        """Debe manejar asset no encontrado."""
        from app.workers.nmap_worker import port_scan
        
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_get_db.return_value = mock_db
        
        result = port_scan("nonexistent-asset", "quick")
        
        assert "Asset nonexistent-asset no encontrado" in result["errors"]
        mock_run_nmap.assert_not_called()


# =============================================================================
# Tests: Execute Scan Task (Integration)
# =============================================================================
class TestExecuteScanTask:
    """Tests para la tarea execute_scan_task."""
    
    @patch("app.workers.nmap_worker.get_sync_db")
    @patch("app.workers.nmap_worker.run_nmap")
    def test_execute_scan_discovery_updates_db(self, mock_run_nmap, mock_get_db):
        """Debe actualizar el scan en DB durante discovery."""
        from app.workers.nmap_worker import execute_scan_task
        
        mock_run_nmap.return_value = SAMPLE_DISCOVERY_XML
        
        # Mock scan
        mock_scan = Mock()
        mock_scan.id = "scan-123"
        mock_scan.status = "queued"
        mock_scan.logs = []
        mock_scan.targets = ["192.168.1.0/24"]
        mock_scan.add_log = Mock()
        mock_scan.start = Mock()
        mock_scan.complete = Mock()
        mock_scan.update_progress = Mock()
        
        mock_db = MagicMock()
        # Sequence: scan lookup, then asset lookups
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_scan,  # Initial scan lookup
            None, None,  # Asset lookups for 2 hosts
        ]
        mock_get_db.return_value = mock_db
        
        result = execute_scan_task(
            scan_id="scan-123",
            scan_type="discovery",
            targets=["192.168.1.0/24"],
            organization_id="org-123",
        )
        
        assert result["success"] is True
        mock_scan.start.assert_called_once()
        mock_scan.complete.assert_called_once()
        mock_scan.update_progress.assert_called()
    
    @patch("app.workers.nmap_worker.get_sync_db")
    def test_execute_scan_cancelled_scan_aborts(self, mock_get_db):
        """Debe abortar si el scan está cancelado."""
        from app.workers.nmap_worker import execute_scan_task
        
        mock_scan = Mock()
        mock_scan.id = "scan-123"
        mock_scan.status = "cancelled"
        
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_scan
        mock_get_db.return_value = mock_db
        
        result = execute_scan_task(
            scan_id="scan-123",
            scan_type="discovery",
            targets=["192.168.1.0/24"],
            organization_id="org-123",
        )
        
        assert result["success"] is False
        assert "cancelado" in result["errors"][0].lower()
    
    @patch("app.workers.nmap_worker.get_sync_db")
    def test_execute_scan_not_found(self, mock_get_db):
        """Debe manejar scan no encontrado."""
        from app.workers.nmap_worker import execute_scan_task
        
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_get_db.return_value = mock_db
        
        result = execute_scan_task(
            scan_id="nonexistent",
            scan_type="discovery",
            targets=["192.168.1.0/24"],
            organization_id="org-123",
        )
        
        assert result["success"] is False
        assert "no encontrado" in result["errors"][0].lower()


# =============================================================================
# Tests: Error Handling
# =============================================================================
class TestErrorHandling:
    """Tests para manejo de errores."""
    
    @patch("app.workers.nmap_worker.get_sync_db")
    @patch("app.workers.nmap_worker.run_nmap")
    def test_nmap_timeout_handled(self, mock_run_nmap, mock_get_db):
        """Debe manejar timeout de nmap gracefully."""
        from app.workers.nmap_worker import execute_scan_task
        import subprocess
        
        mock_run_nmap.side_effect = subprocess.TimeoutExpired(cmd="nmap", timeout=60)
        
        mock_scan = Mock()
        mock_scan.id = "scan-123"
        mock_scan.status = "queued"
        mock_scan.add_log = Mock()
        mock_scan.start = Mock()
        mock_scan.update_progress = Mock()
        
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_scan
        mock_get_db.return_value = mock_db
        
        result = execute_scan_task(
            scan_id="scan-123",
            scan_type="discovery",
            targets=["192.168.1.0/24"],
            organization_id="org-123",
        )
        
        assert "Timeout" in str(result["errors"])
    
    def test_parse_invalid_xml_no_crash(self):
        """El parser no debe crashear con XML inválido."""
        # Estos no deben lanzar excepciones
        result1 = parse_discovery_xml("")
        result2 = parse_discovery_xml("not xml")
        result3 = parse_discovery_xml("<incomplete>")
        result4 = parse_port_scan_xml(None if False else "")
        
        assert result1 == []
        assert result2 == []
        assert result3 == []
        assert result4["services"] == []


# =============================================================================
# Tests: Edge Cases
# =============================================================================
class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_parse_discovery_ipv6(self):
        """Debe manejar direcciones IPv6."""
        xml = """<?xml version="1.0"?>
        <nmaprun>
        <host>
            <status state="up"/>
            <address addr="::1" addrtype="ipv6"/>
        </host>
        </nmaprun>
        """
        hosts = parse_discovery_xml(xml)
        
        assert len(hosts) == 1
        assert hosts[0]["ip_address"] == "::1"
    
    def test_parse_port_scan_no_version(self):
        """Debe manejar servicios sin versión."""
        xml = """<?xml version="1.0"?>
        <nmaprun>
        <host>
            <status state="up"/>
            <address addr="192.168.1.1" addrtype="ipv4"/>
            <ports>
                <port protocol="tcp" portid="8080">
                    <state state="open"/>
                    <service name="http-proxy"/>
                </port>
            </ports>
        </host>
        </nmaprun>
        """
        result = parse_port_scan_xml(xml)
        
        assert len(result["services"]) == 1
        svc = result["services"][0]
        assert svc["port"] == 8080
        assert svc["service_name"] == "http-proxy"
        assert svc["version"] is None
        assert svc["product"] is None
    
    def test_parse_discovery_multiple_ips(self):
        """Debe usar la primera IP encontrada."""
        xml = """<?xml version="1.0"?>
        <nmaprun>
        <host>
            <status state="up"/>
            <address addr="192.168.1.1" addrtype="ipv4"/>
            <address addr="10.0.0.1" addrtype="ipv4"/>
        </host>
        </nmaprun>
        """
        hosts = parse_discovery_xml(xml)
        
        # Debe usar la última IP (sobreescribe)
        assert len(hosts) == 1
        assert hosts[0]["ip_address"] in ["192.168.1.1", "10.0.0.1"]
