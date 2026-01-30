# =============================================================================
# NESTSECURE - Modelo de Scan
# =============================================================================
"""
Modelo SQLAlchemy para scans de seguridad.

Un scan representa una tarea de escaneo ejecutada sobre uno o más assets,
que puede incluir descubrimiento de hosts, escaneo de puertos y detección
de vulnerabilidades.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUID, JSONB, StringArray

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.vulnerability import Vulnerability


class ScanType(str, Enum):
    """Tipos de scan disponibles."""
    DISCOVERY = "discovery"          # Nmap ping scan - descubrir hosts
    PORT_SCAN = "port_scan"          # Nmap port scan
    SERVICE_SCAN = "service_scan"    # Detección de servicios y versiones
    VULNERABILITY = "vulnerability"  # Escaneo de vulnerabilidades
    FULL = "full"                    # Todos los anteriores


class ScanStatus(str, Enum):
    """Estados posibles de un scan."""
    PENDING = "pending"      # Creado, esperando ejecución
    QUEUED = "queued"        # En cola de Celery
    RUNNING = "running"      # En ejecución
    COMPLETED = "completed"  # Completado exitosamente
    FAILED = "failed"        # Falló con error
    CANCELLED = "cancelled"  # Cancelado por usuario


class Scan(Base, TimestampMixin):
    """
    Modelo de Scan.
    
    Representa un escaneo de seguridad ejecutado sobre targets específicos.
    
    Attributes:
        id: UUID único del scan
        organization_id: FK a la organización propietaria
        name: Nombre descriptivo del scan
        scan_type: Tipo de escaneo a realizar
        targets: Lista de IPs, CIDRs o hostnames a escanear
        status: Estado actual del scan
        progress: Porcentaje de progreso (0-100)
    """
    
    __tablename__ = "scans"
    
    # -------------------------------------------------------------------------
    # Campos principales
    # -------------------------------------------------------------------------
    id: Mapped[str] = mapped_column(
        UUID(),
        primary_key=True,
        default=lambda: str(uuid4()).replace("-", ""),
    )
    
    organization_id: Mapped[str] = mapped_column(
        UUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # -------------------------------------------------------------------------
    # Configuración del scan
    # -------------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    scan_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ScanType.PORT_SCAN.value,
    )
    
    # Lista de targets (IPs, CIDRs, hostnames)
    targets: Mapped[list[str]] = mapped_column(
        StringArray(),
        nullable=False,
        default=list,
    )
    
    # IPs excluidas del escaneo
    excluded_targets: Mapped[list[str]] = mapped_column(
        StringArray(),
        nullable=True,
        default=list,
    )
    
    # Puertos a escanear (ej: "22,80,443" o "1-1024")
    port_range: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Configuración específica por engine
    engine_config: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
        default=dict,
    )
    
    # -------------------------------------------------------------------------
    # Scheduling
    # -------------------------------------------------------------------------
    is_scheduled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    cron_expression: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Estado de ejecución
    # -------------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ScanStatus.PENDING.value,
        index=True,
    )
    
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    current_phase: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # ID de la tarea de Celery
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Resultados
    # -------------------------------------------------------------------------
    total_hosts_scanned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    total_hosts_up: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    total_services_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    total_vulnerabilities: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Conteo por severidad
    vuln_critical: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    vuln_high: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    vuln_medium: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    vuln_low: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    vuln_info: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # -------------------------------------------------------------------------
    # Timing
    # -------------------------------------------------------------------------
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Metadata y errores
    # -------------------------------------------------------------------------
    created_by_id: Mapped[str] = mapped_column(
        UUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Logs de ejecución
    logs: Mapped[Optional[list]] = mapped_column(
        JSONB(),
        nullable=True,
        default=list,
    )
    
    # Raw output de los scanners
    raw_output: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Relaciones
    # -------------------------------------------------------------------------
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="scans",
    )
    
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    
    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        "Vulnerability",
        back_populates="scan",
        cascade="all, delete-orphan",
    )
    
    # -------------------------------------------------------------------------
    # Métodos de utilidad
    # -------------------------------------------------------------------------
    def start(self) -> None:
        """Marca el scan como iniciado."""
        self.status = ScanStatus.RUNNING.value
        self.started_at = datetime.now(timezone.utc)
    
    def complete(self) -> None:
        """Marca el scan como completado."""
        self.status = ScanStatus.COMPLETED.value
        self.completed_at = datetime.now(timezone.utc)
        self.progress = 100
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
    
    def fail(self, error: str) -> None:
        """Marca el scan como fallido."""
        self.status = ScanStatus.FAILED.value
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
    
    def cancel(self) -> None:
        """Cancela el scan."""
        self.status = ScanStatus.CANCELLED.value
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
    
    def add_log(self, message: str, level: str = "info") -> None:
        """Añade una entrada al log del scan."""
        if self.logs is None:
            self.logs = []
        self.logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        })
    
    def update_progress(self, progress: int, phase: Optional[str] = None) -> None:
        """Actualiza el progreso del scan."""
        self.progress = min(max(progress, 0), 100)
        if phase:
            self.current_phase = phase
