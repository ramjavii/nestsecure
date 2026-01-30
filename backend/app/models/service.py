# =============================================================================
# NESTSECURE - Modelo de Servicio
# =============================================================================
"""
Modelo SQLAlchemy para servicios de red detectados en assets.

Un servicio representa un puerto abierto con un servicio en ejecución
detectado durante el escaneo de red.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUID, JSONB, StringArray

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.vulnerability import Vulnerability


class ServiceProtocol(str, Enum):
    """Protocolo del servicio."""
    TCP = "tcp"
    UDP = "udp"


class ServiceState(str, Enum):
    """Estado del puerto/servicio."""
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNKNOWN = "unknown"


class Service(Base, TimestampMixin):
    """
    Modelo de Servicio.
    
    Representa un servicio de red detectado en un asset.
    
    Attributes:
        id: UUID único del servicio
        asset_id: FK al asset donde se detectó
        port: Número de puerto
        protocol: TCP o UDP
        service_name: Nombre del servicio (http, ssh, etc.)
        product: Producto/software detectado
        version: Versión del servicio
        cpe: CPE del servicio
        banner: Banner capturado
        state: Estado del puerto
    """
    
    __tablename__ = "services"
    
    # -------------------------------------------------------------------------
    # Campos principales
    # -------------------------------------------------------------------------
    id: Mapped[str] = mapped_column(
        UUID(),
        primary_key=True,
        default=lambda: str(uuid4()).replace("-", ""),
    )
    
    asset_id: Mapped[str] = mapped_column(
        UUID(),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="services",
    )
    
    # -------------------------------------------------------------------------
    # Información del puerto
    # -------------------------------------------------------------------------
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    
    protocol: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=ServiceProtocol.TCP.value,
    )
    
    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ServiceState.OPEN.value,
    )
    
    # -------------------------------------------------------------------------
    # Información del servicio
    # -------------------------------------------------------------------------
    service_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    
    product: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    version: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    cpe: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    banner: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Información SSL/TLS
    # -------------------------------------------------------------------------
    ssl_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    ssl_info: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Información HTTP (si aplica)
    # -------------------------------------------------------------------------
    http_title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    http_technologies: Mapped[Optional[list]] = mapped_column(
        StringArray(),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Detección
    # -------------------------------------------------------------------------
    detection_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    confidence: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )
    
    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    extra_info: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    
    # -------------------------------------------------------------------------
    # Relaciones
    # -------------------------------------------------------------------------
    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        "Vulnerability",
        back_populates="service",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    # -------------------------------------------------------------------------
    # Propiedades
    # -------------------------------------------------------------------------
    @property
    def full_service_name(self) -> str:
        """Nombre completo del servicio con versión."""
        parts = [self.service_name or "unknown"]
        if self.product:
            parts.append(self.product)
        if self.version:
            parts.append(self.version)
        return " ".join(parts)
    
    @property
    def port_protocol(self) -> str:
        """Puerto y protocolo formateado (e.g., '443/tcp')."""
        return f"{self.port}/{self.protocol}"
    
    @property
    def is_web_service(self) -> bool:
        """Verifica si es un servicio web."""
        web_services = {"http", "https", "http-proxy", "http-alt"}
        return (
            self.service_name in web_services or
            self.port in [80, 443, 8080, 8443, 8000, 8888]
        )
    
    @property
    def is_database_service(self) -> bool:
        """Verifica si es un servicio de base de datos."""
        db_services = {"mysql", "postgresql", "mongodb", "redis", "mssql"}
        db_ports = [3306, 5432, 27017, 6379, 1433]
        return self.service_name in db_services or self.port in db_ports
    
    def __repr__(self) -> str:
        return f"Service(id={self.id!r}, port={self.port_protocol}, service={self.service_name!r})"
