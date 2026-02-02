# =============================================================================
# NESTSECURE - GVM Data Models
# =============================================================================
"""
Modelos de datos para GVM/OpenVAS.

Estos dataclasses representan las estructuras de datos de GVM
de forma tipada y pythónica.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class GVMSeverity(Enum):
    """
    Severidades de GVM mapeadas a niveles estándar.
    
    GVM usa CVSS scores que mapeamos a categorías:
    - LOG: 0.0 (informativo)
    - LOW: 0.1 - 3.9
    - MEDIUM: 4.0 - 6.9
    - HIGH: 7.0 - 8.9
    - CRITICAL: 9.0 - 10.0
    """
    LOG = "log"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    @classmethod
    def from_cvss(cls, cvss: float) -> "GVMSeverity":
        """
        Convertir CVSS score a severidad.
        
        Args:
            cvss: Score CVSS (0.0 - 10.0)
        
        Returns:
            GVMSeverity correspondiente
        """
        if cvss <= 0:
            return cls.LOG
        elif cvss < 4.0:
            return cls.LOW
        elif cvss < 7.0:
            return cls.MEDIUM
        elif cvss < 9.0:
            return cls.HIGH
        else:
            return cls.CRITICAL
    
    @classmethod
    def from_threat(cls, threat: str) -> "GVMSeverity":
        """
        Convertir threat level de GVM a severidad.
        
        Args:
            threat: Threat level (Log, Low, Medium, High, Critical)
        
        Returns:
            GVMSeverity correspondiente
        """
        mapping = {
            "log": cls.LOG,
            "low": cls.LOW,
            "medium": cls.MEDIUM,
            "high": cls.HIGH,
            "critical": cls.CRITICAL,
        }
        return mapping.get(threat.lower(), cls.LOG)
    
    def to_nestsecure(self) -> str:
        """Convertir a severidad de NestSecure."""
        mapping = {
            self.LOG: "info",
            self.LOW: "low",
            self.MEDIUM: "medium",
            self.HIGH: "high",
            self.CRITICAL: "critical",
        }
        return mapping.get(self, "info")


class GVMTaskStatus(Enum):
    """
    Estados posibles de una tarea GVM.
    
    Ciclo de vida:
    New -> Requested -> Running -> Done
                    -> Stop Requested -> Stopped
                    -> Pause Requested -> Paused -> Resume Requested -> Running
    """
    NEW = "New"
    REQUESTED = "Requested"
    QUEUED = "Queued"
    RUNNING = "Running"
    PAUSE_REQUESTED = "Pause Requested"
    PAUSED = "Paused"
    RESUME_REQUESTED = "Resume Requested"
    STOP_REQUESTED = "Stop Requested"
    STOPPED = "Stopped"
    DONE = "Done"
    CONTAINER = "Container"
    DELETE_REQUESTED = "Delete Requested"
    ULTIMATE_DELETE_REQUESTED = "Ultimate Delete Requested"
    
    @property
    def is_running(self) -> bool:
        """¿Está el scan en ejecución?"""
        return self in [
            GVMTaskStatus.REQUESTED,
            GVMTaskStatus.QUEUED,
            GVMTaskStatus.RUNNING,
            GVMTaskStatus.RESUME_REQUESTED,
        ]
    
    @property
    def is_finished(self) -> bool:
        """¿Ha terminado el scan?"""
        return self in [
            GVMTaskStatus.DONE,
            GVMTaskStatus.STOPPED,
            GVMTaskStatus.CONTAINER,
        ]
    
    @property
    def is_pending(self) -> bool:
        """¿Está pendiente de iniciar?"""
        return self in [
            GVMTaskStatus.NEW,
            GVMTaskStatus.REQUESTED,
            GVMTaskStatus.QUEUED,
        ]


# =============================================================================
# DATACLASSES - Configuración
# =============================================================================

@dataclass
class GVMScanConfig:
    """
    Configuración de escaneo disponible en GVM.
    
    GVM tiene varias configuraciones predefinidas:
    - Discovery: Solo descubrimiento de hosts
    - Host Discovery: Identificación de hosts vivos
    - System Discovery: Descubrimiento de sistemas
    - Full and fast: Balance entre velocidad y cobertura
    - Full and fast ultimate: Más exhaustivo
    - Full and very deep: Escaneo completo y profundo
    - Full and very deep ultimate: Máxima cobertura
    """
    id: str
    name: str
    type: str = "0"  # 0=OpenVAS, 1=OSP
    family_count: int = 0
    nvt_count: int = 0
    comment: Optional[str] = None
    
    # Configs predefinidas conocidas
    DISCOVERY = "8715c877-47a0-438d-98a3-27c7a6ab2196"
    HOST_DISCOVERY = "2d3f051c-55ba-11e3-bf43-406186ea4fc5"
    SYSTEM_DISCOVERY = "bbca7412-a950-11e3-9109-406186ea4fc5"
    FULL_AND_FAST = "daba56c8-73ec-11df-a475-002264764cea"
    FULL_AND_FAST_ULTIMATE = "698f691e-7489-11df-9d8c-002264764cea"
    FULL_AND_DEEP = "708f25c4-7489-11df-8094-002264764cea"
    FULL_AND_DEEP_ULTIMATE = "74db13d6-7489-11df-91b9-002264764cea"


@dataclass
class GVMPortList:
    """
    Lista de puertos para escaneo.
    
    Define qué puertos se escanearán en el target.
    """
    id: str
    name: str
    port_count: int = 0
    tcp_ports: Optional[str] = None
    udp_ports: Optional[str] = None
    comment: Optional[str] = None
    
    # Port lists predefinidas conocidas
    ALL_IANA_TCP = "33d0cd82-57c6-11e1-8ed1-406186ea4fc5"
    ALL_IANA_TCP_UDP = "730ef368-57e2-11e1-a90f-406186ea4fc5"
    ALL_TCP = "4a4717fe-57d2-11e1-9a26-406186ea4fc5"
    ALL_TCP_NMAP_TOP_100 = "e3c1a8b0-e9dc-11e4-9b4d-406186ea4fc5"
    ALL_TCP_NMAP_TOP_1000 = "96a3c78c-2a97-11e5-9d86-406186ea4fc5"


# =============================================================================
# DATACLASSES - Targets
# =============================================================================

@dataclass
class GVMCredential:
    """Credencial para autenticación en targets."""
    id: str
    name: str
    type: str  # ssh, smb, snmp, esxi
    login: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class GVMTarget:
    """
    Target de escaneo en GVM.
    
    Representa un host o rango de hosts a escanear.
    """
    id: str
    name: str
    hosts: str  # IPs o CIDRs separados por coma
    port_list_id: Optional[str] = None
    port_list_name: Optional[str] = None
    comment: Optional[str] = None
    creation_time: Optional[datetime] = None
    modification_time: Optional[datetime] = None
    exclude_hosts: Optional[str] = None
    ssh_credential: Optional[GVMCredential] = None
    smb_credential: Optional[GVMCredential] = None
    alive_test: str = "Scan Config Default"
    
    @property
    def host_list(self) -> List[str]:
        """Lista de hosts como array."""
        if not self.hosts:
            return []
        return [h.strip() for h in self.hosts.split(",")]
    
    @property
    def host_count(self) -> int:
        """Número aproximado de hosts (sin expandir CIDRs)."""
        return len(self.host_list)


# =============================================================================
# DATACLASSES - Tasks
# =============================================================================

@dataclass
class GVMTask:
    """
    Tarea de escaneo en GVM.
    
    Una task combina un target con una configuración de escaneo.
    """
    id: str
    name: str
    status: str
    progress: int = 0
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    config_id: Optional[str] = None
    config_name: Optional[str] = None
    scanner_id: Optional[str] = None
    scanner_name: Optional[str] = None
    last_report_id: Optional[str] = None
    creation_time: Optional[datetime] = None
    modification_time: Optional[datetime] = None
    comment: Optional[str] = None
    
    # Contadores del último reporte
    result_count: int = 0
    severity: Optional[float] = None
    
    @property
    def status_enum(self) -> GVMTaskStatus:
        """Estado como enum."""
        try:
            return GVMTaskStatus(self.status)
        except ValueError:
            return GVMTaskStatus.NEW
    
    @property
    def is_running(self) -> bool:
        """¿Está en ejecución?"""
        return self.status_enum.is_running
    
    @property
    def is_done(self) -> bool:
        """¿Ha terminado?"""
        return self.status_enum.is_finished


# =============================================================================
# DATACLASSES - Results
# =============================================================================

@dataclass
class GVMVulnerability:
    """
    Vulnerabilidad individual encontrada.
    
    Representa un resultado de escaneo para un host/puerto específico.
    """
    id: str
    name: str
    host: str
    port: Optional[str] = None
    protocol: Optional[str] = None
    severity: float = 0.0
    severity_class: GVMSeverity = GVMSeverity.LOG
    cvss_base: Optional[float] = None
    cvss_vector: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    solution: Optional[str] = None
    solution_type: Optional[str] = None
    insight: Optional[str] = None
    impact: Optional[str] = None
    affected: Optional[str] = None
    detection: Optional[str] = None
    cve_ids: List[str] = field(default_factory=list)
    bid_ids: List[str] = field(default_factory=list)  # Bugtraq IDs
    cert_ids: List[str] = field(default_factory=list)  # CERT advisories
    xrefs: List[str] = field(default_factory=list)  # Referencias externas
    threat: Optional[str] = None
    family: Optional[str] = None
    nvt_oid: Optional[str] = None  # OID del NVT
    qod: int = 0  # Quality of Detection (0-100)
    qod_type: Optional[str] = None
    
    def __post_init__(self):
        """Calcular severity_class desde severity si no está seteado."""
        if self.severity > 0 and self.severity_class == GVMSeverity.LOG:
            self.severity_class = GVMSeverity.from_cvss(self.severity)
    
    @property
    def port_number(self) -> Optional[int]:
        """Extraer número de puerto."""
        if not self.port:
            return None
        try:
            # Formato: "443/tcp" o "general/tcp"
            port_str = self.port.split("/")[0]
            if port_str.isdigit():
                return int(port_str)
        except (ValueError, IndexError):
            pass
        return None
    
    @property
    def has_cve(self) -> bool:
        """¿Tiene CVEs asociados?"""
        return len(self.cve_ids) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "severity": self.severity,
            "severity_class": self.severity_class.value,
            "cvss_base": self.cvss_base,
            "description": self.description,
            "solution": self.solution,
            "cve_ids": self.cve_ids,
            "family": self.family,
            "qod": self.qod,
        }


@dataclass
class GVMHostResult:
    """
    Resultados agrupados por host.
    
    Contiene todas las vulnerabilidades encontradas en un host específico.
    """
    ip: str
    hostname: Optional[str] = None
    os: Optional[str] = None
    os_cpe: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    scan_duration_seconds: Optional[int] = None
    vulnerabilities: List[GVMVulnerability] = field(default_factory=list)
    ports: List[str] = field(default_factory=list)
    
    @property
    def total_vulns(self) -> int:
        """Total de vulnerabilidades."""
        return len(self.vulnerabilities)
    
    @property
    def critical_count(self) -> int:
        """Vulnerabilidades críticas."""
        return sum(1 for v in self.vulnerabilities 
                   if v.severity_class == GVMSeverity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        """Vulnerabilidades altas."""
        return sum(1 for v in self.vulnerabilities 
                   if v.severity_class == GVMSeverity.HIGH)
    
    @property
    def medium_count(self) -> int:
        """Vulnerabilidades medias."""
        return sum(1 for v in self.vulnerabilities 
                   if v.severity_class == GVMSeverity.MEDIUM)
    
    @property
    def low_count(self) -> int:
        """Vulnerabilidades bajas."""
        return sum(1 for v in self.vulnerabilities 
                   if v.severity_class == GVMSeverity.LOW)
    
    @property
    def max_severity(self) -> float:
        """Severidad máxima encontrada."""
        if not self.vulnerabilities:
            return 0.0
        return max(v.severity for v in self.vulnerabilities)
    
    @property
    def unique_cves(self) -> List[str]:
        """Lista única de CVEs encontrados."""
        cves = set()
        for vuln in self.vulnerabilities:
            cves.update(vuln.cve_ids)
        return sorted(list(cves))


@dataclass
class GVMReport:
    """
    Reporte completo de escaneo GVM.
    
    Contiene todos los resultados de un escaneo agrupados por host.
    """
    id: str
    task_id: str
    task_name: Optional[str] = None
    scan_start: Optional[datetime] = None
    scan_end: Optional[datetime] = None
    timezone: str = "UTC"
    hosts: List[GVMHostResult] = field(default_factory=list)
    
    # Contadores (calculados)
    host_count: int = 0
    vuln_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    log_count: int = 0
    
    # Metadata
    scan_run_status: Optional[str] = None
    filter_string: Optional[str] = None
    
    def calculate_stats(self) -> None:
        """Calcular estadísticas del reporte."""
        self.host_count = len(self.hosts)
        self.vuln_count = 0
        self.critical_count = 0
        self.high_count = 0
        self.medium_count = 0
        self.low_count = 0
        self.log_count = 0
        
        for host in self.hosts:
            for vuln in host.vulnerabilities:
                self.vuln_count += 1
                match vuln.severity_class:
                    case GVMSeverity.CRITICAL:
                        self.critical_count += 1
                    case GVMSeverity.HIGH:
                        self.high_count += 1
                    case GVMSeverity.MEDIUM:
                        self.medium_count += 1
                    case GVMSeverity.LOW:
                        self.low_count += 1
                    case GVMSeverity.LOG:
                        self.log_count += 1
    
    @property
    def scan_duration_seconds(self) -> Optional[int]:
        """Duración del escaneo en segundos."""
        if self.scan_start and self.scan_end:
            return int((self.scan_end - self.scan_start).total_seconds())
        return None
    
    @property
    def max_severity(self) -> float:
        """Severidad máxima encontrada."""
        if not self.hosts:
            return 0.0
        return max(h.max_severity for h in self.hosts)
    
    @property
    def all_cves(self) -> List[str]:
        """Lista única de todos los CVEs."""
        cves = set()
        for host in self.hosts:
            cves.update(host.unique_cves)
        return sorted(list(cves))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "scan_start": self.scan_start.isoformat() if self.scan_start else None,
            "scan_end": self.scan_end.isoformat() if self.scan_end else None,
            "duration_seconds": self.scan_duration_seconds,
            "host_count": self.host_count,
            "vuln_count": self.vuln_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "log_count": self.log_count,
            "all_cves": self.all_cves,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtener resumen ejecutivo del reporte."""
        return {
            "report_id": self.id,
            "task_name": self.task_name,
            "scan_duration": self.scan_duration_seconds,
            "hosts_scanned": self.host_count,
            "total_vulnerabilities": self.vuln_count,
            "severity_breakdown": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "log": self.log_count,
            },
            "unique_cves": len(self.all_cves),
            "max_severity": self.max_severity,
        }
