# =============================================================================
# NESTSECURE - Schemas de Nuclei
# =============================================================================
"""
Schemas Pydantic para endpoints de Nuclei.

Incluye:
- Request schemas para iniciar escaneos
- Response schemas para resultados
- Profile schemas para perfiles de escaneo
- Finding schemas para vulnerabilidades encontradas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class NucleiSeverity(str, Enum):
    """Severidad de vulnerabilidades Nuclei."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


class NucleiScanStatus(str, Enum):
    """Estados de un escaneo Nuclei."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class NucleiScanRequest(BaseModel):
    """
    Request para iniciar un escaneo Nuclei.
    
    Example:
        {
            "target": "https://example.com",
            "profile": "standard",
            "tags": ["cve", "rce"],
            "severities": ["critical", "high"],
            "timeout": 3600
        }
    """
    target: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="URL o IP objetivo del escaneo"
    )
    profile: str = Field(
        default="standard",
        description="Perfil de escaneo a usar (quick, standard, full, cves, web)"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Tags de templates a incluir (ej: cve, rce, sqli)"
    )
    severities: Optional[List[NucleiSeverity]] = Field(
        default=None,
        description="Filtrar por severidades específicas"
    )
    timeout: int = Field(
        default=3600,
        ge=60,
        le=14400,
        description="Timeout en segundos (1 min - 4 horas)"
    )
    scan_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Nombre opcional para el escaneo"
    )
    
    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        """Validar que el target sea una URL o IP válida."""
        v = v.strip()
        if not v:
            raise ValueError("Target cannot be empty")
        return v
    
    @field_validator("profile")
    @classmethod
    def validate_profile(cls, v: str) -> str:
        """Validar que el perfil exista."""
        valid_profiles = [
            "quick", "standard", "full", "cves", "web",
            "misconfig", "exposure", "takeover", "network", "tech-detect"
        ]
        if v.lower() not in valid_profiles:
            raise ValueError(f"Invalid profile. Valid profiles: {', '.join(valid_profiles)}")
        return v.lower()


class NucleiQuickScanRequest(BaseModel):
    """Request para escaneo rápido Nuclei."""
    target: str = Field(..., min_length=1, max_length=2048)
    scan_name: Optional[str] = Field(default=None, max_length=255)


class NucleiCVEScanRequest(BaseModel):
    """Request para escaneo de CVEs con Nuclei."""
    target: str = Field(..., min_length=1, max_length=2048)
    cve_ids: Optional[List[str]] = Field(
        default=None,
        description="Lista específica de CVE IDs a buscar"
    )
    scan_name: Optional[str] = Field(default=None, max_length=255)


class NucleiWebScanRequest(BaseModel):
    """Request para escaneo web con Nuclei."""
    target: str = Field(..., min_length=1, max_length=2048)
    scan_name: Optional[str] = Field(default=None, max_length=255)


# =============================================================================
# RESPONSE SCHEMAS - FINDINGS
# =============================================================================

class NucleiTemplateInfo(BaseModel):
    """Información del template que detectó la vulnerabilidad."""
    id: str = Field(..., description="ID del template")
    name: str = Field(..., description="Nombre del template")
    author: Optional[List[str]] = Field(default=None)
    description: Optional[str] = Field(default=None)
    reference: Optional[List[str]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


class NucleiFindingResponse(BaseModel):
    """
    Vulnerabilidad encontrada por Nuclei.
    
    Representa un hallazgo individual con toda su metadata.
    """
    template_id: str = Field(..., description="ID del template Nuclei")
    template_name: str = Field(..., description="Nombre descriptivo")
    severity: NucleiSeverity = Field(..., description="Severidad de la vulnerabilidad")
    host: str = Field(..., description="Host donde se encontró")
    matched_at: str = Field(..., description="URL exacta del match")
    ip: Optional[str] = Field(default=None, description="IP del host")
    timestamp: Optional[datetime] = Field(default=None, description="Fecha/hora de detección")
    
    # CVE Info
    cve_id: Optional[str] = Field(default=None, alias="cve", description="CVE ID si aplica")
    cvss_score: Optional[float] = Field(default=None, alias="cvss", ge=0, le=10)
    cwe_id: Optional[str] = Field(default=None)
    
    # Extra info
    description: Optional[str] = Field(default=None)
    references: Optional[List[str]] = Field(default=None)
    extracted: Optional[List[str]] = Field(default=None, description="Datos extraídos")
    matcher_name: Optional[str] = Field(default=None)
    
    class Config:
        populate_by_name = True


class NucleiSeveritySummary(BaseModel):
    """Resumen de severidades encontradas."""
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    total: int = 0


# =============================================================================
# RESPONSE SCHEMAS - SCAN
# =============================================================================

class NucleiScanResponse(BaseModel):
    """
    Response al crear un escaneo Nuclei.
    
    Incluye el task_id para tracking del escaneo.
    """
    task_id: str = Field(..., description="ID de la tarea Celery")
    scan_id: Optional[str] = Field(default=None, description="ID del scan en DB")
    status: NucleiScanStatus = Field(..., description="Estado del escaneo")
    target: str = Field(..., description="Objetivo del escaneo")
    profile: Optional[str] = Field(default=None, description="Perfil usado")
    started_at: Optional[datetime] = Field(default=None)
    message: Optional[str] = Field(default=None)


class NucleiScanStatusResponse(BaseModel):
    """Estado actual de un escaneo Nuclei."""
    task_id: str
    scan_id: Optional[str] = None
    status: NucleiScanStatus
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    target: str
    profile: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    
    # Summary (available when completed)
    summary: Optional[NucleiSeveritySummary] = None
    total_findings: Optional[int] = None
    unique_cves: Optional[List[str]] = None
    
    error_message: Optional[str] = None


class NucleiScanResultsResponse(BaseModel):
    """Resultados completos de un escaneo Nuclei."""
    task_id: str
    scan_id: Optional[str] = None
    status: NucleiScanStatus
    target: str
    profile: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    
    # Results
    summary: NucleiSeveritySummary
    findings: List[NucleiFindingResponse]
    total_findings: int
    unique_cves: List[str] = Field(default_factory=list)
    
    # Pagination
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# =============================================================================
# RESPONSE SCHEMAS - PROFILES
# =============================================================================

class NucleiProfileResponse(BaseModel):
    """Perfil de escaneo Nuclei."""
    name: str = Field(..., description="Identificador del perfil")
    display_name: str = Field(..., description="Nombre para mostrar")
    description: str = Field(..., description="Descripción del perfil")
    tags: List[str] = Field(default_factory=list)
    severities: List[str] = Field(default_factory=list)
    template_types: List[str] = Field(default_factory=list)
    speed: str = Field(default="normal")
    estimated_duration: Optional[str] = Field(default=None)
    recommended_for: Optional[str] = Field(default=None)


class NucleiProfilesListResponse(BaseModel):
    """Lista de perfiles disponibles."""
    profiles: List[NucleiProfileResponse]
    total: int
    default_profile: str = "standard"


# =============================================================================
# RESPONSE SCHEMAS - TEMPLATES
# =============================================================================

class NucleiTemplateResponse(BaseModel):
    """Información de un template Nuclei."""
    id: str
    name: str
    author: List[str] = Field(default_factory=list)
    severity: NucleiSeverity
    description: Optional[str] = None
    reference: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    template_type: str = "http"
    
    # Classification
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None


# =============================================================================
# LIST RESPONSES
# =============================================================================

class NucleiScanListItem(BaseModel):
    """Item de lista de escaneos Nuclei."""
    task_id: str
    scan_id: Optional[str] = None
    target: str
    profile: str
    status: NucleiScanStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0


class NucleiScanListResponse(BaseModel):
    """Lista paginada de escaneos Nuclei."""
    items: List[NucleiScanListItem]
    total: int
    page: int
    page_size: int
    pages: int


__all__ = [
    # Enums
    "NucleiSeverity",
    "NucleiScanStatus",
    
    # Requests
    "NucleiScanRequest",
    "NucleiQuickScanRequest",
    "NucleiCVEScanRequest",
    "NucleiWebScanRequest",
    
    # Responses - Findings
    "NucleiTemplateInfo",
    "NucleiFindingResponse",
    "NucleiSeveritySummary",
    
    # Responses - Scan
    "NucleiScanResponse",
    "NucleiScanStatusResponse",
    "NucleiScanResultsResponse",
    
    # Responses - Profiles
    "NucleiProfileResponse",
    "NucleiProfilesListResponse",
    
    # Responses - Templates
    "NucleiTemplateResponse",
    
    # List Responses
    "NucleiScanListItem",
    "NucleiScanListResponse",
]
