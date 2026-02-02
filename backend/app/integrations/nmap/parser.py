# =============================================================================
# NESTSECURE - Nmap XML Parser
# =============================================================================
"""
Parser avanzado para resultados XML de Nmap.

Este módulo procesa el output XML de Nmap y lo convierte en
objetos Python tipados (dataclasses) para fácil manipulación.

Características:
- Parseo de hosts, puertos y servicios
- Extracción de vulnerabilidades de scripts NSE
- Detección de OS
- Soporte para XML estándar y gzip
"""

import xml.etree.ElementTree as ET
import gzip
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from io import BytesIO

from .models import (
    NmapScanResult,
    NmapHost,
    NmapPort,
    NmapVulnerability,
    NmapOS,
    PortState,
    HostState,
)
from .exceptions import NmapParseError


class NmapParser:
    """
    Parser para output XML de Nmap.
    
    Soporta tanto XML directo como comprimido con gzip.
    Extrae información de hosts, puertos, servicios, scripts y vulnerabilidades.
    
    Uso:
        parser = NmapParser()
        result = parser.parse_file("/path/to/scan.xml")
        # o
        result = parser.parse_string(xml_content)
    """
    
    # Regex para extraer CVEs de output de scripts
    CVE_PATTERN = re.compile(r'CVE-\d{4}-\d{4,7}', re.IGNORECASE)
    
    # Regex para extraer CVSS de output de scripts
    CVSS_PATTERN = re.compile(r'CVSS(?:v[23])?\s*(?:Score)?[:\s]+(\d+\.?\d*)', re.IGNORECASE)
    
    # Scripts conocidos de vulnerabilidades
    VULN_SCRIPTS = {
        'vuln', 'exploit', 'http-vuln', 'smb-vuln', 'ssl-vuln',
        'smtp-vuln', 'ftp-vuln', 'mysql-vuln', 'ssh-vuln',
    }
    
    def __init__(self, extract_vulnerabilities: bool = True):
        """
        Inicializar parser.
        
        Args:
            extract_vulnerabilities: Si extraer vulnerabilidades de scripts
        """
        self.extract_vulnerabilities = extract_vulnerabilities
    
    def parse_file(self, filepath: str) -> NmapScanResult:
        """
        Parsear archivo XML de Nmap.
        
        Args:
            filepath: Ruta al archivo XML (puede ser .xml o .xml.gz)
            
        Returns:
            NmapScanResult con todos los datos del escaneo
            
        Raises:
            NmapParseError: Si hay error parseando el archivo
        """
        try:
            # Detectar si es gzip
            if filepath.endswith('.gz'):
                with gzip.open(filepath, 'rb') as f:
                    xml_content = f.read().decode('utf-8')
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
            
            return self.parse_string(xml_content)
            
        except ET.ParseError as e:
            raise NmapParseError(
                f"Error parsing XML file: {str(e)}",
                raw_output=filepath
            )
        except FileNotFoundError:
            raise NmapParseError(
                f"XML file not found: {filepath}",
                raw_output=filepath
            )
        except Exception as e:
            raise NmapParseError(
                f"Unexpected error parsing file: {str(e)}",
                raw_output=filepath
            )
    
    def parse_string(self, xml_content: str) -> NmapScanResult:
        """
        Parsear string XML de Nmap.
        
        Args:
            xml_content: Contenido XML como string
            
        Returns:
            NmapScanResult con todos los datos del escaneo
            
        Raises:
            NmapParseError: Si hay error parseando el XML
        """
        try:
            root = ET.fromstring(xml_content)
            return self._parse_root(root, xml_content)
            
        except ET.ParseError as e:
            raise NmapParseError(
                f"Invalid XML format: {str(e)}",
                raw_output=xml_content[:500] if len(xml_content) > 500 else xml_content
            )
        except Exception as e:
            raise NmapParseError(
                f"Error parsing XML: {str(e)}",
                raw_output=xml_content[:500] if len(xml_content) > 500 else xml_content
            )
    
    def parse_bytes(self, xml_bytes: bytes) -> NmapScanResult:
        """
        Parsear bytes XML (puede ser gzip).
        
        Args:
            xml_bytes: Contenido XML como bytes
            
        Returns:
            NmapScanResult
        """
        # Intentar decompresión gzip
        try:
            with gzip.GzipFile(fileobj=BytesIO(xml_bytes)) as f:
                xml_content = f.read().decode('utf-8')
        except gzip.BadGzipFile:
            xml_content = xml_bytes.decode('utf-8')
        
        return self.parse_string(xml_content)
    
    def _parse_root(self, root: ET.Element, xml_content: str) -> NmapScanResult:
        """
        Parsear elemento raíz del XML.
        
        Args:
            root: Elemento raíz XML
            xml_content: Contenido XML original
            
        Returns:
            NmapScanResult
        """
        result = NmapScanResult()
        result.xml_output = xml_content
        
        # Información del escaneo
        result.scanner_version = root.get('scanner', 'nmap') + " " + root.get('version', '')
        result.arguments = root.get('args', '')
        result.scan_type = self._infer_scan_type(result.arguments)
        
        # Timestamps
        start = root.get('start')
        if start:
            result.start_time = datetime.fromtimestamp(int(start))
        
        # Runstats (estadísticas finales)
        runstats = root.find('runstats')
        if runstats is not None:
            finished = runstats.find('finished')
            if finished is not None:
                end_time = finished.get('time')
                if end_time:
                    result.end_time = datetime.fromtimestamp(int(end_time))
                elapsed = finished.get('elapsed')
                if elapsed:
                    result.elapsed_seconds = float(elapsed)
            
            hosts_elem = runstats.find('hosts')
            if hosts_elem is not None:
                result.hosts_up = int(hosts_elem.get('up', 0))
                result.hosts_down = int(hosts_elem.get('down', 0))
                result.hosts_total = int(hosts_elem.get('total', 0))
        
        # Parsear hosts
        for host_elem in root.findall('host'):
            host = self._parse_host(host_elem)
            if host:
                result.hosts.append(host)
        
        return result
    
    def _parse_host(self, host_elem: ET.Element) -> Optional[NmapHost]:
        """
        Parsear elemento host.
        
        Args:
            host_elem: Elemento XML del host
            
        Returns:
            NmapHost o None
        """
        # Estado del host
        status = host_elem.find('status')
        if status is not None:
            state = HostState.from_string(status.get('state', 'unknown'))
        else:
            state = HostState.UNKNOWN
        
        # Dirección IP
        address = host_elem.find('address')
        if address is None:
            return None
        
        ip_address = address.get('addr', '')
        if not ip_address:
            return None
        
        host = NmapHost(
            ip_address=ip_address,
            state=state,
        )
        
        # MAC address (si hay múltiples address elements)
        for addr in host_elem.findall('address'):
            addr_type = addr.get('addrtype', '')
            if addr_type == 'mac':
                host.mac_address = addr.get('addr')
                host.vendor = addr.get('vendor')
        
        # Hostname
        hostnames = host_elem.find('hostnames')
        if hostnames is not None:
            hostname_elem = hostnames.find('hostname')
            if hostname_elem is not None:
                host.hostname = hostname_elem.get('name')
        
        # Puertos
        ports = host_elem.find('ports')
        if ports is not None:
            for port_elem in ports.findall('port'):
                port = self._parse_port(port_elem)
                if port:
                    host.ports.append(port)
                    # Extraer vulnerabilidades del puerto
                    if self.extract_vulnerabilities:
                        vulns = self._extract_port_vulnerabilities(port_elem, port)
                        host.vulnerabilities.extend(vulns)
        
        # OS Detection
        os_elem = host_elem.find('os')
        if os_elem is not None:
            host.os = self._parse_os(os_elem)
        
        # Host scripts
        hostscript = host_elem.find('hostscript')
        if hostscript is not None:
            for script in hostscript.findall('script'):
                script_id = script.get('id', '')
                script_output = script.get('output', '')
                host.scripts[script_id] = script_output
                
                # Extraer vulnerabilidades de host scripts
                if self.extract_vulnerabilities:
                    vulns = self._extract_script_vulnerabilities(script, None, None)
                    host.vulnerabilities.extend(vulns)
        
        # Uptime
        uptime_elem = host_elem.find('uptime')
        if uptime_elem is not None:
            seconds = uptime_elem.get('seconds')
            if seconds:
                host.uptime = int(seconds)
        
        # Distance (traceroute)
        distance_elem = host_elem.find('distance')
        if distance_elem is not None:
            value = distance_elem.get('value')
            if value:
                host.distance = int(value)
        
        return host
    
    def _parse_port(self, port_elem: ET.Element) -> Optional[NmapPort]:
        """
        Parsear elemento port.
        
        Args:
            port_elem: Elemento XML del puerto
            
        Returns:
            NmapPort o None
        """
        port_num = port_elem.get('portid')
        protocol = port_elem.get('protocol', 'tcp')
        
        if not port_num:
            return None
        
        # Estado del puerto
        state_elem = port_elem.find('state')
        if state_elem is not None:
            state = PortState.from_string(state_elem.get('state', 'unknown'))
        else:
            state = PortState.UNKNOWN
        
        port = NmapPort(
            port=int(port_num),
            protocol=protocol,
            state=state,
        )
        
        # Información del servicio
        service = port_elem.find('service')
        if service is not None:
            port.service_name = service.get('name')
            port.product = service.get('product')
            port.version = service.get('version')
            port.extra_info = service.get('extrainfo')
            
            # CPE
            for cpe in service.findall('cpe'):
                if cpe.text:
                    port.cpe = cpe.text
                    break
            
            # SSL/TLS
            tunnel = service.get('tunnel')
            if tunnel and 'ssl' in tunnel.lower():
                port.ssl_enabled = True
            
            # Confidence
            conf = service.get('conf')
            if conf:
                port.confidence = int(conf)
        
        # Scripts del puerto
        for script in port_elem.findall('script'):
            script_id = script.get('id', '')
            script_output = script.get('output', '')
            port.scripts[script_id] = script_output
            
            # Detectar SSL de scripts
            if 'ssl' in script_id.lower() and 'cert' in script_id.lower():
                port.ssl_enabled = True
        
        return port
    
    def _parse_os(self, os_elem: ET.Element) -> Optional[NmapOS]:
        """
        Parsear información de OS.
        
        Args:
            os_elem: Elemento XML de OS
            
        Returns:
            NmapOS o None
        """
        # Buscar el mejor match
        osmatch = os_elem.find('osmatch')
        if osmatch is None:
            return None
        
        name = osmatch.get('name', 'Unknown OS')
        accuracy = int(osmatch.get('accuracy', 0))
        
        os_info = NmapOS(
            name=name,
            accuracy=accuracy,
        )
        
        # Clase de OS
        osclass = osmatch.find('osclass')
        if osclass is not None:
            os_info.family = osclass.get('osfamily')
            os_info.generation = osclass.get('osgen')
            
            # CPE
            for cpe in osclass.findall('cpe'):
                if cpe.text:
                    os_info.cpe = cpe.text
                    break
        
        return os_info
    
    def _extract_port_vulnerabilities(
        self,
        port_elem: ET.Element,
        port: NmapPort
    ) -> List[NmapVulnerability]:
        """
        Extraer vulnerabilidades de scripts de un puerto.
        
        Args:
            port_elem: Elemento XML del puerto
            port: Objeto NmapPort
            
        Returns:
            Lista de vulnerabilidades detectadas
        """
        vulnerabilities = []
        
        for script in port_elem.findall('script'):
            vulns = self._extract_script_vulnerabilities(
                script,
                port.port,
                port.protocol
            )
            vulnerabilities.extend(vulns)
        
        return vulnerabilities
    
    def _extract_script_vulnerabilities(
        self,
        script: ET.Element,
        port: Optional[int],
        protocol: Optional[str]
    ) -> List[NmapVulnerability]:
        """
        Extraer vulnerabilidades de un script NSE.
        
        Args:
            script: Elemento XML del script
            port: Número de puerto (None si es host script)
            protocol: Protocolo (tcp/udp)
            
        Returns:
            Lista de vulnerabilidades
        """
        vulnerabilities = []
        script_id = script.get('id', '')
        script_output = script.get('output', '')
        
        # Solo procesar scripts relevantes
        if not self._is_vuln_script(script_id):
            return vulnerabilities
        
        # Primero intentar parsear la estructura completa del script
        vuln = self._parse_script_structure(script, script_id, script_output, port, protocol)
        if vuln:
            vulnerabilities.append(vuln)
            return vulnerabilities
        
        # Buscar tabla de vulnerabilidades tradicional
        for table in script.findall('.//table'):
            if table.get('key') == 'ids':
                # Skip tables de IDs, se procesan en _parse_script_structure
                continue
            vuln = self._parse_vuln_table(
                table, script_id, script_output, port, protocol
            )
            if vuln:
                vulnerabilities.append(vuln)
        
        # Si no hay tablas pero el output indica vulnerabilidad
        if not vulnerabilities and 'VULNERABLE' in script_output.upper():
            vuln = self._parse_vuln_from_output(
                script_id, script_output, port, protocol
            )
            if vuln:
                vulnerabilities.append(vuln)
        
        return vulnerabilities
    
    def _parse_script_structure(
        self,
        script: ET.Element,
        script_id: str,
        script_output: str,
        port: Optional[int],
        protocol: Optional[str]
    ) -> Optional[NmapVulnerability]:
        """
        Parsear estructura mixta de script (elem a nivel script + tables).
        
        Args:
            script: Elemento XML del script
            script_id: ID del script
            script_output: Output del script
            port: Puerto
            protocol: Protocolo
            
        Returns:
            NmapVulnerability o None
        """
        state = ""
        cves = []
        cvss = None
        
        # Buscar estado en elem directo del script
        for elem in script.findall('elem'):
            key = elem.get('key', '').lower()
            value = elem.text or ""
            if key == 'state':
                state = value
        
        # Buscar CVEs en table[@key="ids"] 
        ids_table = script.find('.//table[@key="ids"]')
        if ids_table is not None:
            for elem in ids_table.findall('elem'):
                text = elem.text or ""
                cve_match = self.CVE_PATTERN.search(text)
                if cve_match:
                    cves.append(cve_match.group().upper())
        
        # También extraer CVEs del script_id
        cves_from_id = self.CVE_PATTERN.findall(script_id)
        cves.extend([c.upper() for c in cves_from_id])
        
        # Extraer CVEs del output
        cves_from_output = self.CVE_PATTERN.findall(script_output)
        cves.extend([c.upper() for c in cves_from_output])
        
        # Eliminar duplicados
        cves = list(set(cves))
        
        # Si no hay estado, deducir del output
        if not state:
            if 'VULNERABLE' in script_output.upper():
                state = 'VULNERABLE'
            elif 'NOT VULNERABLE' in script_output.upper():
                state = 'NOT VULNERABLE'
        
        # Si no hay indicación de vulnerabilidad, no crear
        if not state or state.upper() == 'NOT VULNERABLE':
            return None
        
        return NmapVulnerability(
            script_id=script_id,
            title=script_id,
            state=state,
            description=None,
            cvss=cvss,
            cves=cves,
            references=[],
            output=script_output,
            port=port,
            protocol=protocol,
        )
    
    def _is_vuln_script(self, script_id: str) -> bool:
        """Verificar si es un script de vulnerabilidades."""
        script_lower = script_id.lower()
        return any(vs in script_lower for vs in self.VULN_SCRIPTS)
    
    def _parse_vuln_table(
        self,
        table: ET.Element,
        script_id: str,
        script_output: str,
        port: Optional[int],
        protocol: Optional[str]
    ) -> Optional[NmapVulnerability]:
        """
        Parsear tabla de vulnerabilidad NSE.
        
        Args:
            table: Elemento XML de tabla
            script_id: ID del script
            script_output: Output del script
            port: Puerto
            protocol: Protocolo
            
        Returns:
            NmapVulnerability o None
        """
        # Buscar campos comunes en tablas de vuln
        state = ""
        title = script_id
        description = ""
        cvss = None
        cves = []
        refs = []
        
        for elem in table.findall('elem'):
            key = elem.get('key', '').lower()
            value = elem.text or ""
            
            if key == 'state':
                state = value
            elif key == 'title':
                title = value
            elif key == 'description':
                description = value
            elif key in ('cvss', 'cvss_score'):
                try:
                    cvss = float(value)
                except ValueError:
                    pass
            elif key == 'cve':
                cves.append(value)
        
        # Buscar IDs en tablas anidadas
        ids_table = table.find('.//table[@key="ids"]')
        if ids_table is not None:
            for elem in ids_table.findall('elem'):
                cve_match = self.CVE_PATTERN.search(elem.text or "")
                if cve_match:
                    cves.append(cve_match.group())
        
        # Buscar refs
        refs_table = table.find('.//table[@key="refs"]')
        if refs_table is not None:
            for elem in refs_table.findall('elem'):
                if elem.text:
                    refs.append(elem.text)
        
        # Extraer CVEs del output si no se encontraron
        if not cves:
            cves = self.CVE_PATTERN.findall(script_output)
        
        # También buscar CVEs en el nombre del script (ej: http-vuln-cve2021-41773)
        cves_from_script_id = self.CVE_PATTERN.findall(script_id)
        cves.extend(cves_from_script_id)
        
        # Normalizar CVEs a mayúsculas y eliminar duplicados
        cves = list(set(cve.upper() for cve in cves))
        
        # Extraer CVSS del output si no se encontró
        if cvss is None:
            cvss_match = self.CVSS_PATTERN.search(script_output)
            if cvss_match:
                try:
                    cvss = float(cvss_match.group(1))
                except ValueError:
                    pass
        
        # Determinar estado
        if not state:
            if 'VULNERABLE' in script_output.upper():
                state = 'VULNERABLE'
            elif 'NOT VULNERABLE' in script_output.upper():
                state = 'NOT VULNERABLE'
            else:
                state = 'UNKNOWN'
        
        # Solo crear si hay algo útil
        if state.upper() == 'NOT VULNERABLE':
            return None
        
        return NmapVulnerability(
            script_id=script_id,
            title=title,
            state=state,
            description=description or None,
            cvss=cvss,
            cves=cves,  # Ya sin duplicados
            references=refs,
            output=script_output,
            port=port,
            protocol=protocol,
        )
    
    def _parse_vuln_from_output(
        self,
        script_id: str,
        script_output: str,
        port: Optional[int],
        protocol: Optional[str]
    ) -> Optional[NmapVulnerability]:
        """
        Parsear vulnerabilidad del output cuando no hay tabla.
        
        Args:
            script_id: ID del script
            script_output: Output del script
            port: Puerto
            protocol: Protocolo
            
        Returns:
            NmapVulnerability o None
        """
        # Extraer CVEs del output Y del script_id (ej: http-vuln-cve2021-41773)
        cves = self.CVE_PATTERN.findall(script_output)
        
        # También buscar CVEs en el nombre del script
        cves_from_script_id = self.CVE_PATTERN.findall(script_id)
        cves.extend(cves_from_script_id)
        
        # Eliminar duplicados y normalizar formato
        cves = list(set(cve.upper() for cve in cves))
        
        # Extraer CVSS
        cvss = None
        cvss_match = self.CVSS_PATTERN.search(script_output)
        if cvss_match:
            try:
                cvss = float(cvss_match.group(1))
            except ValueError:
                pass
        
        # Generar título del script ID
        title = script_id.replace('-', ' ').replace('_', ' ').title()
        
        # Determinar estado
        if 'LIKELY VULNERABLE' in script_output.upper():
            state = 'LIKELY VULNERABLE'
        elif 'VULNERABLE' in script_output.upper():
            state = 'VULNERABLE'
        else:
            return None
        
        return NmapVulnerability(
            script_id=script_id,
            title=title,
            state=state,
            cvss=cvss,
            cves=list(set(cves)),
            output=script_output,
            port=port,
            protocol=protocol,
        )
    
    def _infer_scan_type(self, arguments: str) -> str:
        """
        Inferir tipo de escaneo de los argumentos.
        
        Args:
            arguments: Argumentos de Nmap
            
        Returns:
            Tipo de escaneo inferido
        """
        args_lower = arguments.lower()
        
        if '-sn' in args_lower or '--ping' in args_lower:
            return 'discovery'
        elif '-sv' in args_lower and '-sc' in args_lower:
            return 'version_and_scripts'
        elif '-sv' in args_lower:
            return 'version'
        elif '-ss' in args_lower:
            return 'syn'
        elif '-st' in args_lower:
            return 'connect'
        elif '-su' in args_lower:
            return 'udp'
        elif '-sa' in args_lower:
            return 'ack'
        elif '--script' in args_lower and 'vuln' in args_lower:
            return 'vulnerability'
        elif '-a' in args_lower:
            return 'aggressive'
        elif '-p-' in args_lower:
            return 'full_port'
        else:
            return 'standard'


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def parse_nmap_xml(xml_content: Union[str, bytes]) -> NmapScanResult:
    """
    Parsear XML de Nmap.
    
    Función de conveniencia que detecta automáticamente
    si el contenido es string o bytes.
    
    Args:
        xml_content: XML como string o bytes
        
    Returns:
        NmapScanResult
    """
    parser = NmapParser()
    if isinstance(xml_content, bytes):
        return parser.parse_bytes(xml_content)
    return parser.parse_string(xml_content)


def parse_nmap_file(filepath: str) -> NmapScanResult:
    """
    Parsear archivo XML de Nmap.
    
    Función de conveniencia.
    
    Args:
        filepath: Ruta al archivo XML
        
    Returns:
        NmapScanResult
    """
    parser = NmapParser()
    return parser.parse_file(filepath)
