# =============================================================================
# NESTSECURE - Schemas de Scan
# =============================================================================
"""
Schemas Pydantic para operaciones CRUD de Scans.

Incluye validación de datos para:
- Creación de scans
- Lectura de scans
- Actualización de estado
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


# =============================================================================
# Enums como literales para validación
# =============================================================================
SCAN_TYPES = ["discovery", "port_scan", "service_scan", "vulnerability", "full"]
SCAN_STATUSES = ["pending", "queued", "running", "completed", "failed", "cancelled"]


# =============================================================================
# Scan Schemas
# =============================================================================
class ScanBase(BaseSchema):
    """Campos base de un scan."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del scan")
    scan_type: str = Field(
        default="port_scan",
        description="Tipo de scan a ejecutar"
    )


class ScanCreate(ScanBase):
    """
    Schema para crear un nuevo scan.
    
    Ejemplo:
        {
            "name": "Scan Red Interna",
            "scan_type": "full",
            "targets": ["192.168.1.0/24"],
            "port_range": "1-1000"
        }
    """
    
    description: Optional[str] = Field(None, max_length=2000)
    targets: list[str] = Field(
        ...,
        min_length=1,
        description="Lista de IPs, CIDRs o hostnames a escanear"
    )
    excluded_targets: Optional[list[str]] = Field(
        default_factory=list,
        description="IPs a excluir del escaneo"
    )
    port_range: Optional[str] = Field(
        None,
        max_length=500,
        description="Puertos a escanear (ej: '22,80,443' o '1-1024')"
    )
    engine_config: Optional[dict] = Field(
        default_factory=dict,
        description="Configuración específica del engine"
    )
    is_scheduled: bool = Field(
        default=False,
        description="Si el scan es programado"
    )
    cron_expression: Optional[str] = Field(
        None,
        max_length=100,
        description="Expresión cron para scans programados"
    )


class ScanUpdate(BaseSchema):
    """Schema para actualizar un scan (solo campos modificables)."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = Field(None, description="Nuevo estado del scan")


class ScanRead(ScanBase, IDSchema, TimestampSchema):
    """
    Schema para leer un scan.
    
    Incluye todos los campos públicos del scan.
    """
    
    organization_id: str
    description: Optional[str]
    targets: list[str]
    excluded_targets: Optional[list[str]]
    port_range: Optional[str]
    status: str
    progress: int = Field(..., ge=0, le=100)
    current_phase: Optional[str]
    
    # Resultados
    total_hosts_scanned: int
    total_hosts_up: int
    total_services_found: int
    total_vulnerabilities: int
    vuln_critical: int
    vuln_high: int
    vuln_medium: int
    vuln_low: int
    vuln_info: int
    
    # Timing
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    
    # Metadata
    created_by_id: Optional[str]
    error_message: Optional[str]


class ScanReadMinimal(IDSchema):
    """Schema minimo para referencias a scans."""
    
    name: str
    scan_type: str
    status: str
    created_at: datetime


class ScanReadWithLogs(ScanRead):
    """Scan con logs de ejecución incluidos."""
    
    logs: Optional[list] = Field(default_factory=list)


class ScanProgress(BaseSchema):
    """Schema para progreso de un scan."""
    
    scan_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)
    current_target: Optional[str] = None
    targets_scanned: int = 0
    targets_total: int = 0
    vulnerabilities_found: int = 0
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None


class ScanStats(BaseSchema):
    """Estadísticas agregadas de scans."""
    
    total: int
    by_type: dict = Field(default_factory=dict)
    by_status: dict = Field(default_factory=dict)
    completed: int = 0
    failed: int = 0
    running: int = 0
    average_vulnerabilities: float = 0.0
    last_scan_date: Optional[datetime] = None
