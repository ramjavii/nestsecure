# =============================================================================
# NESTSECURE - Nuclei Data Models
# =============================================================================
"""
Modelos de datos tipados para resultados de escaneos Nuclei.

Estos dataclasses proporcionan una interfaz tipada para trabajar
con los resultados de Nuclei en formato JSON.

Modelos principales:
- NucleiTemplate: Información del template usado
- NucleiFinding: Hallazgo individual
- NucleiScanResult: Resultado completo del escaneo
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class Severity(Enum):
    """
    Severidades de Nuclei.
    
    Mapeo:
    - CRITICAL: Impacto crítico, explotación trivial
    - HIGH: Impacto alto, puede comprometer sistema
    - MEDIUM: Impacto moderado
    - LOW: Impacto bajo
    - INFO: Informativo, sin impacto directo
    - UNKNOWN: Severidad no determinada
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, severity: str) -> "Severity":
        """Convertir string a Severity."""
        severity_lower = severity.lower().strip()
        for s in cls:
            if s.value == severity_lower:
                return s
        return cls.UNKNOWN
    
    @property
    def weight(self) -> int:
        """Peso numérico para ordenamiento."""
        weights = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
            Severity.UNKNOWN: 0,
        }
        return weights.get(self, 0)


class TemplateType(Enum):
    """
    Tipos de templates de Nuclei.
    """
    HTTP = "http"
    DNS = "dns"
    FILE = "file"
    NETWORK = "network"
    HEADLESS = "headless"
    SSL = "ssl"
    WEBSOCKET = "websocket"
    WHOIS = "whois"
    CODE = "code"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, type_str: str) -> "TemplateType":
        """Convertir string a TemplateType."""
        type_lower = type_str.lower().strip()
        for t in cls:
            if t.value == type_lower:
                return t
        return cls.UNKNOWN


@dataclass
class NucleiTemplate:
    """
    Información del template de Nuclei.
    
    Attributes:
        id: ID único del template
        name: Nombre del template
        author: Autor(es) del template
        severity: Severidad del hallazgo
        description: Descripción del template
        reference: URLs de referencia
        tags: Tags del template
        template_type: Tipo de template
        cve: CVE asociado si existe
        cvss: Score CVSS si existe
        cwe: CWE ID si existe
    """
    id: str
    name: str
    author: List[str] = field(default_factory=list)
    severity: Severity = Severity.UNKNOWN
    description: Optional[str] = None
    reference: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    template_type: TemplateType = TemplateType.UNKNOWN
    cve: Optional[str] = None
    cvss: Optional[float] = None
    cwe: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NucleiTemplate":
        """
        Crear template desde diccionario JSON de Nuclei.
        
        Args:
            data: Diccionario con info del template
            
        Returns:
            NucleiTemplate
        """
        info = data.get("info", data)
        
        # Extraer severidad
        severity_str = info.get("severity", "unknown")
        severity = Severity.from_string(severity_str)
        
        # Extraer author (puede ser string o lista)
        author = info.get("author", [])
        if isinstance(author, str):
            author = [author]
        
        # Extraer referencias (puede ser string o lista)
        reference = info.get("reference", [])
        if isinstance(reference, str):
            reference = [reference]
        
        # Extraer tags (puede ser string o lista)
        tags = info.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        
        # Extraer CVE de la clasificación
        classification = info.get("classification", {})
        cve = classification.get("cve-id")
        if isinstance(cve, list):
            cve = cve[0] if cve else None
        
        return cls(
            id=data.get("template-id", data.get("template", "")),
            name=info.get("name", "Unknown"),
            author=author,
            severity=severity,
            description=info.get("description"),
            reference=reference,
            tags=tags,
            template_type=TemplateType.from_string(data.get("type", "unknown")),
            cve=cve,
            cvss=classification.get("cvss-score"),
            cwe=classification.get("cwe-id"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "severity": self.severity.value,
            "description": self.description,
            "reference": self.reference,
            "tags": self.tags,
            "template_type": self.template_type.value,
            "cve": self.cve,
            "cvss": self.cvss,
            "cwe": self.cwe,
        }


@dataclass
class NucleiMatcher:
    """
    Información del matcher que encontró el hallazgo.
    
    Attributes:
        name: Nombre del matcher
        matcher_type: Tipo de matcher (word, regex, status, etc.)
        matched: Valor que hizo match
    """
    name: Optional[str] = None
    matcher_type: Optional[str] = None
    matched: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "name": self.name,
            "type": self.matcher_type,
            "matched": self.matched,
        }


@dataclass
class NucleiFinding:
    """
    Hallazgo individual de Nuclei.
    
    Attributes:
        template: Template que generó el hallazgo
        host: Host donde se encontró
        matched_at: URL/endpoint específico
        ip: IP del host
        timestamp: Cuando se encontró
        request: Request HTTP enviado (si aplica)
        response: Response HTTP recibido (si aplica)
        matcher: Información del matcher
        extracted: Datos extraídos por extractors
        curl_command: Comando curl para reproducir
    """
    template: NucleiTemplate
    host: str
    matched_at: str
    ip: Optional[str] = None
    timestamp: Optional[datetime] = None
    request: Optional[str] = None
    response: Optional[str] = None
    matcher: Optional[NucleiMatcher] = None
    extracted: List[str] = field(default_factory=list)
    curl_command: Optional[str] = None
    
    @property
    def severity(self) -> Severity:
        """Severidad del hallazgo (del template)."""
        return self.template.severity
    
    @property
    def title(self) -> str:
        """Título del hallazgo."""
        return self.template.name
    
    @property
    def cve(self) -> Optional[str]:
        """CVE asociado."""
        return self.template.cve
    
    @property
    def cvss(self) -> Optional[float]:
        """Score CVSS."""
        return self.template.cvss
    
    @classmethod
    def from_json_line(cls, data: Dict[str, Any]) -> "NucleiFinding":
        """
        Crear finding desde línea JSON de Nuclei.
        
        Args:
            data: Diccionario JSON de una línea de output
            
        Returns:
            NucleiFinding
        """
        # Crear template
        template = NucleiTemplate.from_dict(data)
        
        # Extraer timestamp
        timestamp = None
        ts = data.get("timestamp")
        if ts:
            try:
                # Nuclei usa formato RFC3339
                timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except:
                pass
        
        # Extraer matcher info
        matcher = None
        matcher_name = data.get("matcher-name")
        if matcher_name:
            matcher = NucleiMatcher(
                name=matcher_name,
                matcher_type=data.get("matcher-type"),
                matched=data.get("matched"),
            )
        
        # Extraer extracted results
        extracted = data.get("extracted-results", [])
        if isinstance(extracted, str):
            extracted = [extracted]
        
        return cls(
            template=template,
            host=data.get("host", ""),
            matched_at=data.get("matched-at", data.get("host", "")),
            ip=data.get("ip"),
            timestamp=timestamp,
            request=data.get("request"),
            response=data.get("response"),
            matcher=matcher,
            extracted=extracted,
            curl_command=data.get("curl-command"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "template_id": self.template.id,
            "template_name": self.template.name,
            "severity": self.severity.value,
            "host": self.host,
            "matched_at": self.matched_at,
            "ip": self.ip,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "cve": self.cve,
            "cvss": self.cvss,
            "matcher": self.matcher.to_dict() if self.matcher else None,
            "extracted": self.extracted,
        }


@dataclass
class NucleiScanResult:
    """
    Resultado completo de un escaneo Nuclei.
    
    Attributes:
        findings: Lista de hallazgos
        targets: Lista de targets escaneados
        templates_used: Lista de templates utilizados
        start_time: Inicio del escaneo
        end_time: Fin del escaneo
        total_requests: Requests totales enviados
        matched_requests: Requests con match
        error_count: Cantidad de errores
    """
    findings: List[NucleiFinding] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)
    templates_used: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_requests: int = 0
    matched_requests: int = 0
    error_count: int = 0
    
    @property
    def duration(self) -> float:
        """Duración del escaneo en segundos."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def total_findings(self) -> int:
        """Total de hallazgos."""
        return len(self.findings)
    
    @property
    def critical_count(self) -> int:
        """Cantidad de hallazgos críticos."""
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        """Cantidad de hallazgos altos."""
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)
    
    @property
    def medium_count(self) -> int:
        """Cantidad de hallazgos medios."""
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)
    
    @property
    def low_count(self) -> int:
        """Cantidad de hallazgos bajos."""
        return sum(1 for f in self.findings if f.severity == Severity.LOW)
    
    @property
    def info_count(self) -> int:
        """Cantidad de hallazgos informativos."""
        return sum(1 for f in self.findings if f.severity == Severity.INFO)
    
    @property
    def unique_cves(self) -> List[str]:
        """Lista de CVEs únicos."""
        cves = set()
        for f in self.findings:
            if f.cve:
                cves.add(f.cve)
        return sorted(list(cves))
    
    @property
    def findings_by_severity(self) -> Dict[str, List[NucleiFinding]]:
        """Hallazgos agrupados por severidad."""
        grouped: Dict[str, List[NucleiFinding]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
        }
        for f in self.findings:
            grouped[f.severity.value].append(f)
        return grouped
    
    @property
    def findings_by_host(self) -> Dict[str, List[NucleiFinding]]:
        """Hallazgos agrupados por host."""
        grouped: Dict[str, List[NucleiFinding]] = {}
        for f in self.findings:
            if f.host not in grouped:
                grouped[f.host] = []
            grouped[f.host].append(f)
        return grouped
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtener resumen del escaneo."""
        return {
            "duration_seconds": self.duration,
            "targets_count": len(self.targets),
            "templates_count": len(self.templates_used),
            "total_findings": self.total_findings,
            "critical": self.critical_count,
            "high": self.high_count,
            "medium": self.medium_count,
            "low": self.low_count,
            "info": self.info_count,
            "unique_cves": len(self.unique_cves),
            "total_requests": self.total_requests,
            "errors": self.error_count,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario completo."""
        return {
            "summary": self.get_summary(),
            "targets": self.targets,
            "templates_used": self.templates_used,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "findings": [f.to_dict() for f in self.findings],
        }
