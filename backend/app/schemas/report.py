# =============================================================================
# NESTSECURE - Schemas de Report
# =============================================================================
"""
Schemas Pydantic para operaciones CRUD de Reports.

Incluye validación de datos para:
- Generación de reportes
- Lectura de reportes
- Filtros y descargas
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


# =============================================================================
# Enums como literales para validación
# =============================================================================
REPORT_TYPES = ["executive", "technical", "compliance", "vulnerability", "asset_inventory", "scan_summary"]
REPORT_FORMATS = ["pdf", "xlsx", "json", "csv"]
REPORT_STATUSES = ["pending", "generating", "completed", "failed"]


# =============================================================================
# Report Schemas
# =============================================================================
class ReportBase(BaseSchema):
    """Campos base de un reporte."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del reporte")
    report_type: str = Field(..., description="Tipo de reporte")
    format: str = Field(default="pdf", description="Formato del archivo")


class ReportCreate(ReportBase):
    """
    Schema para solicitar generación de un reporte.
    
    Ejemplo:
        {
            "name": "Reporte Ejecutivo Q1 2026",
            "report_type": "executive",
            "format": "pdf",
            "parameters": {
                "date_from": "2026-01-01",
                "date_to": "2026-03-31",
                "severity_filter": ["critical", "high"]
            }
        }
    """
    
    description: Optional[str] = Field(None, max_length=1000)
    parameters: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Parámetros para filtrar el reporte"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Reporte de Vulnerabilidades Críticas",
                "report_type": "vulnerability",
                "format": "pdf",
                "description": "Reporte mensual de vulnerabilidades críticas y altas",
                "parameters": {
                    "severity_filter": ["critical", "high"],
                    "status_filter": ["open", "in_progress"]
                }
            }
        }


class ReportRead(IDSchema, TimestampSchema):
    """
    Schema de respuesta para un reporte.
    
    Incluye todos los campos públicos del reporte.
    """
    
    name: str
    report_type: str
    format: str
    status: str
    description: Optional[str] = None
    file_size: Optional[int] = None
    parameters: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_by_id: Optional[str] = None
    
    # Campos calculados
    is_downloadable: bool = False
    
    class Config:
        from_attributes = True


class ReportReadWithCreator(ReportRead):
    """Schema con información del creador."""
    
    created_by_name: Optional[str] = None
    created_by_email: Optional[str] = None


class ReportSummary(IDSchema):
    """Schema resumido para listas."""
    
    name: str
    report_type: str
    format: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    is_downloadable: bool = False
    
    class Config:
        from_attributes = True


# =============================================================================
# Request/Response Schemas
# =============================================================================
class GenerateReportRequest(BaseSchema):
    """Request para generar un reporte."""
    
    name: str = Field(..., min_length=1, max_length=255)
    report_type: str = Field(..., description="Tipo: executive, technical, vulnerability, etc.")
    format: str = Field(default="pdf", description="Formato: pdf, xlsx, json, csv")
    description: Optional[str] = Field(None, max_length=1000)
    
    # Filtros comunes
    date_from: Optional[datetime] = Field(None, description="Fecha inicio del período")
    date_to: Optional[datetime] = Field(None, description="Fecha fin del período")
    severity_filter: Optional[list[str]] = Field(None, description="Filtrar por severidades")
    status_filter: Optional[list[str]] = Field(None, description="Filtrar por estados")
    asset_ids: Optional[list[str]] = Field(None, description="Filtrar por assets específicos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Reporte Ejecutivo Febrero 2026",
                "report_type": "executive",
                "format": "pdf",
                "date_from": "2026-02-01T00:00:00Z",
                "date_to": "2026-02-28T23:59:59Z",
                "severity_filter": ["critical", "high"]
            }
        }


class GenerateReportResponse(BaseSchema):
    """Response de solicitud de generación."""
    
    id: str = Field(..., description="ID del reporte")
    status: str = Field(..., description="Estado inicial (pending)")
    message: str = Field(..., description="Mensaje de confirmación")


class ReportListResponse(BaseSchema):
    """Response para lista de reportes."""
    
    reports: list[ReportSummary]
    total: int
    page: int
    page_size: int
