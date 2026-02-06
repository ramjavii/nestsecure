# =============================================================================
# NESTSECURE - Modelo de Report
# =============================================================================
"""
Modelo SQLAlchemy para reportes generados.

Un reporte representa un documento generado con información de seguridad
como vulnerabilidades, assets, scans, etc.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUID, JSONB

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class ReportType(str, Enum):
    """Tipos de reporte disponibles."""
    EXECUTIVE = "executive"          # Resumen ejecutivo
    TECHNICAL = "technical"          # Detalles técnicos
    COMPLIANCE = "compliance"        # Cumplimiento normativo
    VULNERABILITY = "vulnerability"  # Lista de vulnerabilidades
    ASSET_INVENTORY = "asset_inventory"  # Inventario de assets
    SCAN_SUMMARY = "scan_summary"    # Resumen de escaneos


class ReportFormat(str, Enum):
    """Formatos de reporte soportados."""
    PDF = "pdf"
    XLSX = "xlsx"
    JSON = "json"
    CSV = "csv"


class ReportStatus(str, Enum):
    """Estados de generación del reporte."""
    PENDING = "pending"        # En cola
    GENERATING = "generating"  # Generando
    COMPLETED = "completed"    # Completado
    FAILED = "failed"          # Fallido


class Report(Base, TimestampMixin):
    """
    Modelo de Report.
    
    Representa un reporte generado por el sistema.
    
    Attributes:
        id: UUID único del reporte
        organization_id: FK a la organización propietaria
        created_by_id: FK al usuario que lo solicitó
        name: Nombre del reporte
        report_type: Tipo de reporte (executive, technical, etc.)
        format: Formato del archivo (pdf, xlsx, json)
        status: Estado de generación
        file_path: Ruta al archivo generado
        file_size: Tamaño del archivo en bytes
        parameters: Parámetros usados para generar
        error_message: Mensaje de error si falló
        completed_at: Fecha de completado
    """
    
    __tablename__ = "reports"
    
    # -------------------------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------------------------
    id: Mapped[str] = mapped_column(
        UUID,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    # -------------------------------------------------------------------------
    # Foreign Keys
    # -------------------------------------------------------------------------
    organization_id: Mapped[str] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    created_by_id: Mapped[str] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # -------------------------------------------------------------------------
    # Report Info
    # -------------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReportType.VULNERABILITY.value,
    )
    
    format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=ReportFormat.PDF.value,
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReportStatus.PENDING.value,
        index=True,
    )
    
    # -------------------------------------------------------------------------
    # File Info
    # -------------------------------------------------------------------------
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Parameters & Metadata
    # -------------------------------------------------------------------------
    parameters: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="reports",
    )
    
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="reports",
    )
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    def mark_generating(self) -> None:
        """Marca el reporte como en generación."""
        self.status = ReportStatus.GENERATING.value
    
    def mark_completed(self, file_path: str, file_size: int) -> None:
        """Marca el reporte como completado."""
        self.status = ReportStatus.COMPLETED.value
        self.file_path = file_path
        self.file_size = file_size
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_failed(self, error: str) -> None:
        """Marca el reporte como fallido."""
        self.status = ReportStatus.FAILED.value
        self.error_message = error
        self.completed_at = datetime.now(timezone.utc)
    
    @property
    def is_downloadable(self) -> bool:
        """Verifica si el reporte está listo para descargar."""
        return self.status == ReportStatus.COMPLETED.value and self.file_path is not None
    
    def __repr__(self) -> str:
        return f"<Report(id={self.id}, name='{self.name}', type={self.report_type}, status={self.status})>"
