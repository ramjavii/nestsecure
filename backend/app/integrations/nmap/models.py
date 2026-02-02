# =============================================================================
# NESTSECURE - Nmap Data Models
# =============================================================================
"""
Modelos de datos tipados para resultados de escaneos Nmap.

Estos dataclasses proporcionan una interfaz tipada y pythónica
para trabajar con los resultados de Nmap.

Modelos principales:
- NmapPort: Puerto detectado con servicio
- NmapVulnerability: Vulnerabilidad detectada por script NSE
- NmapOS: Sistema operativo detectado
- NmapHost: Host completo con puertos y vulnerabilidades
- NmapScanResult: Resultado completo de un escaneo
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class PortState(Enum):
    """
    Estados posibles de un puerto según Nmap.
    
    Estados:
    - OPEN: Puerto abierto y aceptando conexiones
    - CLOSED: Puerto cerrado (responde pero sin servicio)
    - FILTERED: No se puede determinar (firewall)
    - UNFILTERED: Accesible pero no se sabe si abierto/cerrado
    - OPEN_FILTERED: Abierto o filtrado (no se puede determinar)
    - CLOSED_FILTERED: Cerrado o filtrado
    """
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNFILTERED = "unfiltered"
    OPEN_FILTERED = "open|filtered"
    CLOSED_FILTERED = "closed|filtered"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, state: str) -> "PortState":
        """Convertir string a PortState."""
        state_lower = state.lower().strip()
        for s in cls:
            if s.value == state_lower:
                return s
        return cls.UNKNOWN


class HostState(Enum):
    """
    Estados posibles de un host.
    
    Estados:
    - UP: Host activo y respondiendo
    - DOWN: Host no responde
    - UNKNOWN: Estado desconocido
    """
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, state: str) -> "HostState":
        """Convertir string a HostState."""
        state_lower = state.lower().strip()
        for s in cls:
            if s.value == state_lower:
                return s
        return cls.UNKNOWN


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class NmapPort:
    """
    Puerto detectado en un host.
    
    Attributes:
        port: Número de puerto (1-65535)
        protocol: Protocolo (tcp, udp, sctp)
        state: Estado del puerto
        service_name: Nombre del servicio (ssh, http, etc.)
        product: Producto detectado (OpenSSH, Apache, etc.)
        version: Versión del producto
        extra_info: Información adicional
        cpe: Common Platform Enumeration
        banner: Banner del servicio
        ssl_enabled: Si tiene SSL/TLS
        scripts: Output de scripts NSE ejecutados
    """
    port: int
    protocol: str
    state: PortState
    service_name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    extra_info: Optional[str] = None
    cpe: Optional[str] = None
    banner: Optional[str] = None
    ssl_enabled: bool = False
    confidence: int = 0  # 0-10 de nmap
    scripts: Dict[str, str] = field(default_factory=dict)
    
    @property
    def is_open(self) -> bool:
        """¿Está el puerto abierto?"""
        return self.state == PortState.OPEN
    
    @property
    def service_string(self) -> str:
        """Generar string descriptivo del servicio."""
        parts = []
        if self.service_name:
            parts.append(self.service_name)
        if self.product:
            parts.append(self.product)
        if self.version:
            parts.append(self.version)
        return " ".join(parts) if parts else "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "port": self.port,
            "protocol": self.protocol,
            "state": self.state.value,
            "service_name": self.service_name,
            "product": self.product,
            "version": self.version,
            "cpe": self.cpe,
            "ssl_enabled": self.ssl_enabled,
            "banner": self.banner,
        }


@dataclass
class NmapVulnerability:
    """
    Vulnerabilidad detectada por script NSE.
    
    Attributes:
        script_id: ID del script NSE (ej: http-vuln-cve2017-5638)
        title: Título legible de la vulnerabilidad
        state: Estado (VULNERABLE, NOT VULNERABLE, LIKELY VULNERABLE)
        description: Descripción completa
        cvss: Score CVSS si disponible
        cves: Lista de CVEs asociados
        references: URLs de referencia
        output: Output raw del script
        port: Puerto donde se detectó
        protocol: Protocolo (tcp/udp)
    """
    script_id: str
    title: str
    state: str  # VULNERABLE, NOT VULNERABLE, LIKELY VULNERABLE, ERROR
    description: Optional[str] = None
    cvss: Optional[float] = None
    cves: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    output: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    
    @property
    def is_vulnerable(self) -> bool:
        """¿Es una vulnerabilidad confirmada?"""
        return "VULNERABLE" in self.state.upper() and "NOT" not in self.state.upper()
    
    @property
    def severity(self) -> str:
        """
        Mapear CVSS a severidad NestSecure.
        
        Returns:
            Severidad: critical, high, medium, low, info
        """
        if self.cvss is None:
            # Sin CVSS, inferir de keywords
            if any(kw in self.title.lower() for kw in ['critical', 'rce', 'remote code']):
                return "critical"
            elif any(kw in self.title.lower() for kw in ['high', 'injection', 'bypass']):
                return "high"
            return "medium"  # Default
        
        if self.cvss >= 9.0:
            return "critical"
        elif self.cvss >= 7.0:
            return "high"
        elif self.cvss >= 4.0:
            return "medium"
        elif self.cvss > 0:
            return "low"
        return "info"
    
    @property
    def primary_cve(self) -> Optional[str]:
        """Obtener el CVE principal (primero de la lista)."""
        return self.cves[0] if self.cves else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "script_id": self.script_id,
            "title": self.title,
            "state": self.state,
            "severity": self.severity,
            "cvss": self.cvss,
            "cves": self.cves,
            "references": self.references,
            "port": self.port,
            "protocol": self.protocol,
            "is_vulnerable": self.is_vulnerable,
        }


@dataclass
class NmapOS:
    """
    Sistema operativo detectado.
    
    Attributes:
        name: Nombre completo del OS
        accuracy: Porcentaje de confianza (0-100)
        family: Familia de OS (Linux, Windows, etc.)
        generation: Generación o versión general
        cpe: CPE del OS
    """
    name: str
    accuracy: int
    family: Optional[str] = None
    generation: Optional[str] = None
    cpe: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "name": self.name,
            "accuracy": self.accuracy,
            "family": self.family,
            "generation": self.generation,
            "cpe": self.cpe,
        }


@dataclass
class NmapHost:
    """
    Host escaneado con todos sus datos.
    
    Attributes:
        ip_address: Dirección IP (v4 o v6)
        state: Estado del host
        hostname: Hostname si se resolvió
        mac_address: Dirección MAC si disponible
        vendor: Vendor de la NIC
        os: Sistema operativo detectado
        ports: Lista de puertos detectados
        vulnerabilities: Vulnerabilidades encontradas
        scripts: Output de host scripts
        uptime: Uptime en segundos si detectado
        distance: Distancia en hops (traceroute)
    """
    ip_address: str
    state: HostState
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    os: Optional[NmapOS] = None
    ports: List[NmapPort] = field(default_factory=list)
    vulnerabilities: List[NmapVulnerability] = field(default_factory=list)
    scripts: Dict[str, str] = field(default_factory=dict)
    uptime: Optional[int] = None
    distance: Optional[int] = None
    
    @property
    def is_up(self) -> bool:
        """¿Está el host activo?"""
        return self.state == HostState.UP
    
    @property
    def open_ports(self) -> List[NmapPort]:
        """Obtener solo puertos abiertos."""
        return [p for p in self.ports if p.is_open]
    
    @property
    def open_port_numbers(self) -> List[int]:
        """Obtener números de puertos abiertos."""
        return [p.port for p in self.open_ports]
    
    @property
    def services(self) -> List[str]:
        """Obtener nombres de servicios detectados."""
        return [p.service_name for p in self.open_ports if p.service_name]
    
    @property
    def confirmed_vulnerabilities(self) -> List[NmapVulnerability]:
        """Obtener solo vulnerabilidades confirmadas."""
        return [v for v in self.vulnerabilities if v.is_vulnerable]
    
    @property
    def has_vulnerabilities(self) -> bool:
        """¿Tiene vulnerabilidades confirmadas?"""
        return len(self.confirmed_vulnerabilities) > 0
    
    @property
    def critical_vulns(self) -> List[NmapVulnerability]:
        """Obtener vulnerabilidades críticas."""
        return [v for v in self.confirmed_vulnerabilities if v.severity == "critical"]
    
    @property
    def high_vulns(self) -> List[NmapVulnerability]:
        """Obtener vulnerabilidades altas."""
        return [v for v in self.confirmed_vulnerabilities if v.severity == "high"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "ip_address": self.ip_address,
            "state": self.state.value,
            "hostname": self.hostname,
            "mac_address": self.mac_address,
            "vendor": self.vendor,
            "os": self.os.to_dict() if self.os else None,
            "ports": [p.to_dict() for p in self.ports],
            "open_ports_count": len(self.open_ports),
            "vulnerabilities_count": len(self.confirmed_vulnerabilities),
        }


@dataclass
class NmapScanResult:
    """
    Resultado completo de un escaneo Nmap.
    
    Attributes:
        hosts: Lista de hosts escaneados
        scan_type: Tipo de escaneo inferido
        arguments: Argumentos usados en el escaneo
        start_time: Timestamp de inicio
        end_time: Timestamp de fin
        elapsed_seconds: Duración del escaneo
        hosts_up: Cantidad de hosts activos
        hosts_down: Cantidad de hosts inactivos
        hosts_total: Total de hosts escaneados
        scanner_version: Versión de Nmap
        xml_output: XML raw para debug
    """
    hosts: List[NmapHost] = field(default_factory=list)
    scan_type: str = ""
    arguments: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    elapsed_seconds: float = 0.0
    hosts_up: int = 0
    hosts_down: int = 0
    hosts_total: int = 0
    scanner_version: Optional[str] = None
    xml_output: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Duración del escaneo en segundos."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return self.elapsed_seconds
    
    @property
    def total_open_ports(self) -> int:
        """Total de puertos abiertos en todos los hosts."""
        return sum(len(h.open_ports) for h in self.hosts)
    
    @property
    def total_services(self) -> int:
        """Total de servicios detectados."""
        return sum(len(h.services) for h in self.hosts)
    
    @property
    def total_vulnerabilities(self) -> int:
        """Total de vulnerabilidades confirmadas."""
        return sum(len(h.confirmed_vulnerabilities) for h in self.hosts)
    
    @property
    def all_vulnerabilities(self) -> List[NmapVulnerability]:
        """Obtener todas las vulnerabilidades de todos los hosts."""
        vulns = []
        for host in self.hosts:
            vulns.extend(host.confirmed_vulnerabilities)
        return vulns
    
    @property
    def critical_count(self) -> int:
        """Cantidad de vulnerabilidades críticas."""
        return sum(1 for v in self.all_vulnerabilities if v.severity == "critical")
    
    @property
    def high_count(self) -> int:
        """Cantidad de vulnerabilidades altas."""
        return sum(1 for v in self.all_vulnerabilities if v.severity == "high")
    
    @property
    def medium_count(self) -> int:
        """Cantidad de vulnerabilidades medias."""
        return sum(1 for v in self.all_vulnerabilities if v.severity == "medium")
    
    @property
    def low_count(self) -> int:
        """Cantidad de vulnerabilidades bajas."""
        return sum(1 for v in self.all_vulnerabilities if v.severity == "low")
    
    @property
    def unique_cves(self) -> List[str]:
        """Obtener lista de CVEs únicos."""
        cves = set()
        for vuln in self.all_vulnerabilities:
            cves.update(vuln.cves)
        return sorted(list(cves))
    
    @property
    def all_open_ports(self) -> Dict[int, List[str]]:
        """Obtener todos los puertos abiertos con los hosts que los tienen."""
        ports: Dict[int, List[str]] = {}
        for host in self.hosts:
            for port in host.open_ports:
                if port.port not in ports:
                    ports[port.port] = []
                ports[port.port].append(host.ip_address)
        return ports
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtener resumen del escaneo."""
        return {
            "scan_type": self.scan_type,
            "duration_seconds": self.duration,
            "hosts_total": self.hosts_total,
            "hosts_up": self.hosts_up,
            "hosts_down": self.hosts_down,
            "total_open_ports": self.total_open_ports,
            "total_services": self.total_services,
            "total_vulnerabilities": self.total_vulnerabilities,
            "critical_vulns": self.critical_count,
            "high_vulns": self.high_count,
            "medium_vulns": self.medium_count,
            "low_vulns": self.low_count,
            "unique_cves": len(self.unique_cves),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario completo."""
        return {
            "scan_type": self.scan_type,
            "arguments": self.arguments,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_seconds": self.elapsed_seconds,
            "scanner_version": self.scanner_version,
            "summary": self.get_summary(),
            "hosts": [h.to_dict() for h in self.hosts],
        }
