# =============================================================================
# NESTSECURE - Schemas de CVE
# =============================================================================
"""
Schemas Pydantic para operaciones con CVEs.

Incluye validación de datos para:
- Lectura de CVEs desde cache
- Búsqueda de CVEs
- Sincronización con NVD
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


# =============================================================================
# CVE Schemas
# =============================================================================
class CVEBase(BaseSchema):
    """Campos base de un CVE."""
    
    cve_id: str = Field(
        ..., 
        pattern=r"^CVE-\d{4}-\d{4,}$",
        description="ID del CVE (ej: CVE-2024-1234)"
    )
    description: str = Field(..., description="Descripción del CVE")


class CVERead(CVEBase, TimestampSchema):
    """
    Schema para leer un CVE desde cache.
    
    Incluye información de CVSS, exploits y CISA KEV.
    """
    
    # Fechas NVD
    published_date: datetime
    last_modified_date: datetime
    
    # CVSS v3
    cvss_v3_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    cvss_v3_vector: Optional[str]
    cvss_v3_severity: Optional[str]
    cvss_v3_attack_vector: Optional[str]
    cvss_v3_attack_complexity: Optional[str]
    cvss_v3_privileges_required: Optional[str]
    cvss_v3_user_interaction: Optional[str]
    
    # CVSS v2 (legacy)
    cvss_v2_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    cvss_v2_severity: Optional[str]
    
    # CPEs afectados
    affected_cpes: Optional[list[str]]
    affected_vendors: Optional[list[str]]
    affected_products: Optional[list[str]]
    
    # Exploits
    exploit_available: bool
    exploit_code_maturity: Optional[str]
    
    # EPSS
    epss_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    epss_percentile: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    # CISA KEV
    in_cisa_kev: bool
    cisa_date_added: Optional[datetime]
    cisa_due_date: Optional[datetime]
    cisa_required_action: Optional[str]
    
    # CWE
    cwe_ids: Optional[list[str]]
    
    # Cache info
    last_synced_at: datetime
    sync_source: str


class CVEReadMinimal(BaseSchema):
    """Schema mínimo para referencias a CVEs."""
    
    cve_id: str
    cvss_v3_score: Optional[float]
    cvss_v3_severity: Optional[str]
    exploit_available: bool
    in_cisa_kev: bool


class CVESearch(BaseSchema):
    """Schema para búsqueda de CVEs."""
    
    query: str = Field(..., min_length=3, description="Texto de búsqueda")
    min_cvss: Optional[float] = Field(None, ge=0.0, le=10.0)
    max_cvss: Optional[float] = Field(None, ge=0.0, le=10.0)
    has_exploit: Optional[bool] = None
    in_kev: Optional[bool] = None
    vendor: Optional[str] = None
    product: Optional[str] = None
    published_after: Optional[datetime] = None
    published_before: Optional[datetime] = None


class CVESyncRequest(BaseSchema):
    """Schema para solicitar sincronización de CVEs."""
    
    full_sync: bool = Field(
        default=False,
        description="Sincronizar todos los CVEs (puede tardar horas)"
    )
    days_back: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Días hacia atrás para sincronizar"
    )
    cve_ids: Optional[list[str]] = Field(
        default=None,
        description="Lista específica de CVEs a sincronizar"
    )
    keywords: Optional[list[str]] = Field(
        default=None,
        description="Palabras clave para buscar CVEs"
    )
    force: bool = Field(
        default=False,
        description="Forzar actualización incluso si ya están sincronizados"
    )


class CVESyncStatus(BaseSchema):
    """Estado de sincronización de CVEs."""
    
    task_id: Optional[str] = None
    status: Optional[str] = None  # pending, running, completed, failed
    is_running: bool = False
    progress: int = Field(0, ge=0, le=100)
    total_cves: int = 0
    synced_cves: int = 0
    cves_synced: int = 0  # Alias para compatibilidad
    updated_cves: int = 0
    failed_cves: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None
    errors: list[str] = Field(default_factory=list)


class CVEStats(BaseSchema):
    """Estadísticas del cache de CVEs."""
    
    total: int = 0
    total_cves: int = 0  # Alias para compatibilidad
    total_cached: int = 0  # Alias para compatibilidad
    with_exploit: int = 0
    with_exploits: int = 0  # Alias
    in_cisa_kev: int = 0
    kev_count: int = 0  # Alias
    by_severity: dict = Field(
        default_factory=dict,
        description="Conteo por severidad"
    )
    average_cvss: float = 0.0
    top_cves: list = Field(default_factory=list)
    last_sync: Optional[datetime] = None
    oldest_cve: Optional[str] = None
    newest_cve: Optional[str] = None
