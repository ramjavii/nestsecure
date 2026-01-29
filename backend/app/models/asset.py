# =============================================================================
# NESTSECURE - Modelo de Asset
# =============================================================================
"""
Modelo SQLAlchemy para assets (activos de infraestructura).

Un asset representa un dispositivo o servidor en la red que puede
ser escaneado para detectar vulnerabilidades.
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

from app.db.base import Base, TimestampMixin, UUID, INET, JSONB, StringArray

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.service import Service


class AssetType(str, Enum):
    """Tipos de asset."""
    SERVER = "server"
    WORKSTATION = "workstation"
    NETWORK_DEVICE = "network_device"
    CONTAINER = "container"
    CLOUD_INSTANCE = "cloud_instance"
    IOT_DEVICE = "iot_device"
    OTHER = "other"


class AssetCriticality(str, Enum):
    """Nivel de criticidad del asset."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AssetStatus(str, Enum):
    """Estado del asset."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class Asset(Base, TimestampMixin):
    """
    Modelo de Asset.
    
    Representa un activo de infraestructura que puede ser escaneado.
    
    Attributes:
        id: UUID único del asset
        organization_id: FK a la organización propietaria
        ip_address: Dirección IP principal
        hostname: Nombre del host
        mac_address: Dirección MAC (si se conoce)
        operating_system: Sistema operativo detectado
        os_version: Versión del SO
        os_cpe: CPE del sistema operativo
        asset_type: Tipo de asset
        criticality: Nivel de criticidad
        tags: Etiquetas para categorización
        status: Estado actual del asset
        risk_score: Puntuación de riesgo calculada (0-100)
        vulnerability_counts: Conteo de vulnerabilidades por severidad
    """
    
    __tablename__ = "assets"
    
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
    
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="assets",
    )
    
    # -------------------------------------------------------------------------
    # Identificación de red
    # -------------------------------------------------------------------------
    ip_address: Mapped[str] = mapped_column(
        INET(),
        nullable=False,
        index=True,
    )
    
    hostname: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    
    mac_address: Mapped[Optional[str]] = mapped_column(
        String(17),  # XX:XX:XX:XX:XX:XX
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Información del sistema
    # -------------------------------------------------------------------------
    operating_system: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    os_version: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    os_cpe: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Clasificación
    # -------------------------------------------------------------------------
    asset_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AssetType.SERVER.value,
    )
    
    criticality: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AssetCriticality.MEDIUM.value,
    )
    
    tags: Mapped[Optional[list]] = mapped_column(
        StringArray(),
        nullable=True,
        default=list,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Estado
    # -------------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AssetStatus.ACTIVE.value,
        index=True,
    )
    
    is_reachable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # -------------------------------------------------------------------------
    # Métricas de riesgo
    # -------------------------------------------------------------------------
    risk_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    
    vuln_critical_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    vuln_high_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    vuln_medium_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    vuln_low_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    # -------------------------------------------------------------------------
    # Timestamps de descubrimiento
    # -------------------------------------------------------------------------
    first_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )
    
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    last_scanned: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Metadata adicional
    # -------------------------------------------------------------------------
    metadata_extra: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
        default=dict,
    )
    
    # -------------------------------------------------------------------------
    # Relaciones
    # -------------------------------------------------------------------------
    services: Mapped[list["Service"]] = relationship(
        "Service",
        back_populates="asset",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    # -------------------------------------------------------------------------
    # Propiedades
    # -------------------------------------------------------------------------
    @property
    def total_vulnerabilities(self) -> int:
        """Total de vulnerabilidades."""
        return (
            self.vuln_critical_count +
            self.vuln_high_count +
            self.vuln_medium_count +
            self.vuln_low_count
        )
    
    @property
    def is_critical_asset(self) -> bool:
        """Verifica si es un asset crítico."""
        return self.criticality == AssetCriticality.CRITICAL.value
    
    @property
    def has_critical_vulnerabilities(self) -> bool:
        """Verifica si tiene vulnerabilidades críticas."""
        return self.vuln_critical_count > 0
    
    @property
    def service_count(self) -> int:
        """Número de servicios detectados."""
        return len(self.services) if self.services else 0
    
    # -------------------------------------------------------------------------
    # Métodos de utilidad
    # -------------------------------------------------------------------------
    def update_risk_score(self) -> None:
        """
        Calcula y actualiza el risk_score basado en vulnerabilidades.
        
        Fórmula: (critical*40 + high*20 + medium*5 + low*1) / max * 100
        Cap at 100
        """
        weighted_score = (
            self.vuln_critical_count * 40 +
            self.vuln_high_count * 20 +
            self.vuln_medium_count * 5 +
            self.vuln_low_count * 1
        )
        
        # Normalizar a 0-100
        self.risk_score = min(100.0, weighted_score)
    
    def mark_scanned(self) -> None:
        """Marca el asset como escaneado ahora."""
        now = datetime.now(timezone.utc)
        self.last_scanned = now
        self.last_seen = now
    
    def add_tag(self, tag: str) -> None:
        """Añade una etiqueta si no existe."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Elimina una etiqueta."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def __repr__(self) -> str:
        return f"Asset(id={self.id!r}, ip={self.ip_address!r}, hostname={self.hostname!r})"
