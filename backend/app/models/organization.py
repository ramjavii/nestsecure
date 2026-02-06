# =============================================================================
# NESTSECURE - Modelo de Organización
# =============================================================================
"""
Modelo SQLAlchemy para organizaciones (multi-tenant).

Las organizaciones son la unidad principal de aislamiento de datos.
Cada organización tiene sus propios usuarios, assets, escaneos, etc.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUID, JSONB

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.asset import Asset
    from app.models.scan import Scan
    from app.models.vulnerability import Vulnerability
    from app.models.report import Report


class Organization(Base, TimestampMixin):
    """
    Modelo de Organización.
    
    Representa una empresa u organización que usa NestSecure.
    Toda la información está aislada por organización (multi-tenant).
    
    Attributes:
        id: UUID único de la organización
        name: Nombre visible de la organización
        slug: Identificador único URL-friendly
        description: Descripción opcional
        license_key: Clave de licencia (si aplica)
        license_expires_at: Fecha de expiración de la licencia
        max_assets: Límite de assets según licencia
        settings: Configuración específica de la organización (JSON)
        is_active: Si la organización está activa
    """
    
    __tablename__ = "organizations"
    
    # -------------------------------------------------------------------------
    # Campos principales
    # -------------------------------------------------------------------------
    id: Mapped[str] = mapped_column(
        UUID(),
        primary_key=True,
        default=lambda: str(uuid4()).replace("-", ""),
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Licencia y límites
    # -------------------------------------------------------------------------
    license_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    license_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    max_assets: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )
    
    # -------------------------------------------------------------------------
    # Configuración
    # -------------------------------------------------------------------------
    settings: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
        default=dict,
    )
    
    # -------------------------------------------------------------------------
    # Estado
    # -------------------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # -------------------------------------------------------------------------
    # Relaciones
    # -------------------------------------------------------------------------
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    scans: Mapped[list["Scan"]] = relationship(
        "Scan",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        "Vulnerability",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    
    # -------------------------------------------------------------------------
    # Propiedades
    # -------------------------------------------------------------------------
    @property
    def is_license_valid(self) -> bool:
        """Verifica si la licencia está vigente."""
        if self.license_expires_at is None:
            return True  # Sin fecha = sin límite
        return self.license_expires_at > datetime.now(timezone.utc)
    
    @property
    def asset_count(self) -> int:
        """Retorna el número de assets."""
        return len(self.assets) if self.assets else 0
    
    @property
    def user_count(self) -> int:
        """Retorna el número de usuarios."""
        return len(self.users) if self.users else 0
    
    def can_add_asset(self) -> bool:
        """Verifica si se puede agregar otro asset."""
        return self.asset_count < self.max_assets
    
    # -------------------------------------------------------------------------
    # Métodos de utilidad
    # -------------------------------------------------------------------------
    def get_setting(self, key: str, default=None):
        """Obtiene un valor de configuración."""
        if not self.settings:
            return default
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value) -> None:
        """Establece un valor de configuración."""
        if self.settings is None:
            self.settings = {}
        self.settings[key] = value
    
    def __repr__(self) -> str:
        return f"Organization(id={self.id!r}, name={self.name!r}, slug={self.slug!r})"
