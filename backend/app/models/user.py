# =============================================================================
# NESTSECURE - Modelo de Usuario
# =============================================================================
"""
Modelo SQLAlchemy para usuarios del sistema.

Los usuarios pertenecen a una organización y tienen roles que definen
sus permisos dentro del sistema.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUID, JSONB

if TYPE_CHECKING:
    from app.models.organization import Organization


class UserRole(str, Enum):
    """
    Roles de usuario disponibles.
    
    - admin: Acceso completo a la organización
    - operator: Ejecuta escaneos, gestiona assets
    - analyst: Analiza vulnerabilidades, gestiona estados
    - viewer: Solo lectura
    """
    ADMIN = "admin"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base, TimestampMixin):
    """
    Modelo de Usuario.
    
    Representa un usuario del sistema con autenticación y autorización.
    
    Attributes:
        id: UUID único del usuario
        email: Email único (usado para login)
        hashed_password: Password hasheado con bcrypt
        full_name: Nombre completo
        role: Rol del usuario (admin, operator, analyst, viewer)
        organization_id: FK a la organización
        permissions: Permisos adicionales específicos (JSON)
        is_active: Si el usuario puede hacer login
        is_superuser: Si tiene permisos de superusuario
        last_login_at: Última fecha de login
    """
    
    __tablename__ = "users"
    
    # -------------------------------------------------------------------------
    # Campos principales
    # -------------------------------------------------------------------------
    id: Mapped[str] = mapped_column(
        UUID(),
        primary_key=True,
        default=lambda: str(uuid4()).replace("-", ""),
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # -------------------------------------------------------------------------
    # Rol y permisos
    # -------------------------------------------------------------------------
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.VIEWER.value,
    )
    
    permissions: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
        default=dict,
    )
    
    # -------------------------------------------------------------------------
    # Organización
    # -------------------------------------------------------------------------
    organization_id: Mapped[str] = mapped_column(
        UUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="users",
    )
    
    # -------------------------------------------------------------------------
    # Estado y metadatos
    # -------------------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Configuración del usuario
    # -------------------------------------------------------------------------
    preferences: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
        default=dict,
    )
    
    # -------------------------------------------------------------------------
    # Propiedades
    # -------------------------------------------------------------------------
    @property
    def is_admin(self) -> bool:
        """Verifica si el usuario es admin."""
        return self.role == UserRole.ADMIN.value or self.is_superuser
    
    @property
    def is_operator(self) -> bool:
        """Verifica si el usuario es operator o superior."""
        return self.role in [UserRole.ADMIN.value, UserRole.OPERATOR.value] or self.is_superuser
    
    @property
    def is_analyst(self) -> bool:
        """Verifica si el usuario es analyst o superior."""
        return self.role in [
            UserRole.ADMIN.value, 
            UserRole.OPERATOR.value, 
            UserRole.ANALYST.value
        ] or self.is_superuser
    
    @property
    def display_name(self) -> str:
        """Nombre para mostrar (full_name o email)."""
        return self.full_name or self.email.split("@")[0]
    
    # -------------------------------------------------------------------------
    # Métodos de utilidad
    # -------------------------------------------------------------------------
    def has_permission(self, permission: str) -> bool:
        """
        Verifica si el usuario tiene un permiso específico.
        
        Los superusuarios y admins tienen todos los permisos.
        """
        if self.is_superuser or self.is_admin:
            return True
        
        if not self.permissions:
            return False
        
        return self.permissions.get(permission, False)
    
    def record_login(self) -> None:
        """Registra el timestamp del login."""
        self.last_login_at = datetime.now(timezone.utc)
    
    def get_preference(self, key: str, default=None):
        """Obtiene una preferencia del usuario."""
        if not self.preferences:
            return default
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value) -> None:
        """Establece una preferencia del usuario."""
        if self.preferences is None:
            self.preferences = {}
        self.preferences[key] = value
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r}, role={self.role!r})"
