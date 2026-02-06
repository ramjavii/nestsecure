# =============================================================================
# NESTSECURE - Schemas ZAP
# =============================================================================
"""
Schemas Pydantic para la integración con OWASP ZAP.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# =============================================================================
# ENUMS
# =============================================================================

class ZapScanMode(str, Enum):
    """Modos de escaneo disponibles."""
    QUICK = "quick"
    STANDARD = "standard"
    FULL = "full"
    API = "api"
    PASSIVE = "passive"
    SPA = "spa"
    SPIDER_ONLY = "spider_only"
    ACTIVE_ONLY = "active_only"


class ZapScanStatus(str, Enum):
    """Estados posibles de un escaneo ZAP."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ZapAlertRisk(str, Enum):
    """Niveles de riesgo de alertas ZAP."""
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ZapAlertConfidence(str, Enum):
    """Niveles de confianza de alertas ZAP."""
    FALSE_POSITIVE = "false_positive"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CONFIRMED = "confirmed"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class ZapScanRequest(BaseModel):
    """Request para iniciar un escaneo ZAP."""
    target_url: str = Field(
        ...,
        description="URL objetivo a escanear",
        examples=["http://target.local", "https://webapp.local:8080"],
    )
    mode: ZapScanMode = Field(
        default=ZapScanMode.STANDARD,
        description="Modo de escaneo",
    )
    asset_id: Optional[UUID] = Field(
        default=None,
        description="ID del asset asociado (opcional)",
    )
    include_patterns: Optional[List[str]] = Field(
        default=None,
        description="Patrones regex a incluir en el contexto",
    )
    exclude_patterns: Optional[List[str]] = Field(
        default=None,
        description="Patrones regex a excluir del contexto",
    )
    timeout: Optional[int] = Field(
        default=None,
        ge=60,
        le=7200,
        description="Timeout en segundos (60-7200)",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_url": "http://webapp.local:8080",
                "mode": "standard",
                "include_patterns": [".*\\.local.*"],
                "timeout": 1800,
            }
        }


class ZapQuickScanRequest(BaseModel):
    """Request para escaneo rápido."""
    target_url: str = Field(
        ...,
        description="URL objetivo",
    )
    asset_id: Optional[UUID] = None


class ZapApiScanRequest(BaseModel):
    """Request para escaneo de API."""
    target_url: str = Field(
        ...,
        description="URL base de la API",
    )
    openapi_url: Optional[str] = Field(
        default=None,
        description="URL de la especificación OpenAPI/Swagger",
    )
    asset_id: Optional[UUID] = None


class ZapSpaScanRequest(BaseModel):
    """Request para escaneo de SPA."""
    target_url: str = Field(
        ...,
        description="URL de la Single Page Application",
    )
    asset_id: Optional[UUID] = None


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class ZapScanResponse(BaseModel):
    """Response al iniciar un escaneo ZAP."""
    task_id: str = Field(..., description="ID de la tarea Celery")
    target_url: str
    mode: ZapScanMode
    status: ZapScanStatus = ZapScanStatus.PENDING
    message: str = "Escaneo ZAP iniciado"
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123-def456-ghi789",
                "target_url": "http://webapp.local:8080",
                "mode": "standard",
                "status": "pending",
                "message": "Escaneo ZAP iniciado",
            }
        }


class ZapScanProgress(BaseModel):
    """Progreso de un escaneo ZAP."""
    phase: str = Field(..., description="Fase actual del escaneo")
    spider_progress: int = Field(default=0, ge=0, le=100)
    ajax_spider_progress: int = Field(default=0, ge=0, le=100)
    active_scan_progress: int = Field(default=0, ge=0, le=100)
    passive_scan_pending: int = Field(default=0, ge=0)
    urls_found: int = Field(default=0, ge=0)
    alerts_found: int = Field(default=0, ge=0)
    overall_progress: int = Field(default=0, ge=0, le=100)
    elapsed_seconds: float = Field(default=0, ge=0)


class ZapScanStatusResponse(BaseModel):
    """Estado de un escaneo ZAP."""
    task_id: str
    status: ZapScanStatus
    progress: Optional[ZapScanProgress] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class ZapAlertResponse(BaseModel):
    """Una alerta individual de ZAP."""
    id: str
    name: str
    risk: ZapAlertRisk
    confidence: ZapAlertConfidence
    url: str
    method: str = "GET"
    param: Optional[str] = None
    attack: Optional[str] = None
    evidence: Optional[str] = None
    description: str
    solution: str
    reference: Optional[str] = None
    cwe_id: Optional[int] = None
    wasc_id: Optional[int] = None
    owasp_top_10: Optional[str] = None
    plugin_id: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "1",
                "name": "Cross-Site Scripting (Reflected)",
                "risk": "high",
                "confidence": "medium",
                "url": "http://target.local/search?q=test",
                "method": "GET",
                "param": "q",
                "attack": "<script>alert(1)</script>",
                "evidence": "<script>",
                "description": "Cross-site scripting vulnerability...",
                "solution": "Validate all input and encode output...",
                "cwe_id": 79,
                "plugin_id": 40012,
            }
        }


class ZapAlertsSummary(BaseModel):
    """Resumen de alertas por nivel de riesgo."""
    informational: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    total: int = 0


class ZapScanResultsResponse(BaseModel):
    """Resultados completos de un escaneo ZAP."""
    task_id: str
    target_url: str
    mode: ZapScanMode
    status: ZapScanStatus
    success: bool
    
    # Tiempos
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    
    # Métricas
    urls_found: int = 0
    alerts_count: int = 0
    alerts_summary: ZapAlertsSummary = Field(default_factory=ZapAlertsSummary)
    
    # Alertas (pueden ser muchas)
    alerts: List[ZapAlertResponse] = Field(default_factory=list)
    
    # Errores
    errors: List[str] = Field(default_factory=list)
    
    # IDs internos de ZAP
    spider_scan_id: Optional[str] = None
    active_scan_id: Optional[str] = None
    context_name: Optional[str] = None


class ZapProfileResponse(BaseModel):
    """Perfil de escaneo ZAP."""
    id: str
    name: str
    description: str
    spider: bool = True
    ajax_spider: bool = False
    active_scan: bool = True
    api_scan: bool = False
    timeout: int = 1800


class ZapProfilesListResponse(BaseModel):
    """Lista de perfiles disponibles."""
    profiles: List[ZapProfileResponse]
    total: int


class ZapVersionResponse(BaseModel):
    """Versión y estado de ZAP."""
    version: str
    available: bool
    host: str
    port: int


class ZapScanListItem(BaseModel):
    """Item de lista de escaneos ZAP."""
    task_id: str
    target_url: str
    mode: ZapScanMode
    status: ZapScanStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    alerts_count: int = 0
    urls_found: int = 0


class ZapScanListResponse(BaseModel):
    """Lista de escaneos ZAP."""
    scans: List[ZapScanListItem]
    total: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# WEBSOCKET SCHEMAS
# =============================================================================

class ZapProgressUpdate(BaseModel):
    """Actualización de progreso vía WebSocket."""
    task_id: str
    type: str = "zap_progress"
    progress: ZapScanProgress
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
