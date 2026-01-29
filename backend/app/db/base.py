# =============================================================================
# NESTSECURE - SQLAlchemy Base y Mixins
# =============================================================================
"""
Configuración base de SQLAlchemy con DeclarativeBase y mixins reutilizables.

Este módulo define:
- Base class para todos los modelos
- Mixins comunes (timestamps, soft delete, etc.)
- Tipos personalizados que funcionan con PostgreSQL y SQLite
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, MetaData, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB, INET as PG_INET, ARRAY as PG_ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.types import TypeDecorator, TEXT, VARCHAR
import json


# =============================================================================
# Tipos personalizados compatibles con SQLite y PostgreSQL
# =============================================================================
class JSONB(TypeDecorator):
    """
    Tipo JSONB que funciona con PostgreSQL (nativo) y SQLite (como TEXT).
    """
    impl = TEXT
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(TEXT())
    
    def process_bind_param(self, value, dialect):
        if value is not None and dialect.name != 'postgresql':
            return json.dumps(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None and dialect.name != 'postgresql':
            return json.loads(value)
        return value


class UUID(TypeDecorator):
    """
    Tipo UUID que funciona con PostgreSQL (nativo) y SQLite (como VARCHAR).
    """
    impl = VARCHAR(36)
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(VARCHAR(36))
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value


class INET(TypeDecorator):
    """
    Tipo INET que funciona con PostgreSQL (nativo) y SQLite (como VARCHAR).
    """
    impl = VARCHAR(45)  # IPv6 = 45 chars max
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_INET())
        return dialect.type_descriptor(VARCHAR(45))


class StringArray(TypeDecorator):
    """
    Tipo ARRAY de strings que funciona con PostgreSQL (nativo) y SQLite (como JSON).
    """
    impl = TEXT
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_ARRAY(String(255)))
        return dialect.type_descriptor(TEXT())
    
    def process_bind_param(self, value, dialect):
        if value is not None and dialect.name != 'postgresql':
            return json.dumps(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None and dialect.name != 'postgresql':
            if isinstance(value, str):
                return json.loads(value)
        return value or []

# =============================================================================
# Convenciones de nombres para constraints
# =============================================================================
# Esto facilita las migraciones de Alembic al tener nombres consistentes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


# =============================================================================
# Base Class
# =============================================================================
class Base(DeclarativeBase):
    """
    Base class para todos los modelos SQLAlchemy.
    
    Incluye:
    - Metadata con convenciones de nombres
    - Configuración por defecto para todos los modelos
    """
    
    metadata = metadata
    
    # Configuración para serialización
    type_annotation_map = {
        str: String(255),
    }
    
    def to_dict(self) -> dict[str, Any]:
        """Convierte el modelo a diccionario."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def __repr__(self) -> str:
        """Representación legible del modelo."""
        class_name = self.__class__.__name__
        attrs = ", ".join(
            f"{k}={v!r}" 
            for k, v in self.to_dict().items() 
            if not k.startswith("_")
        )
        return f"{class_name}({attrs})"


# =============================================================================
# Mixins
# =============================================================================
class TimestampMixin:
    """
    Mixin que añade campos de timestamps automáticos.
    
    Campos:
    - created_at: Fecha de creación (automática)
    - updated_at: Fecha de última actualización (automática)
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class UUIDMixin:
    """
    Mixin que añade un campo ID de tipo UUID.
    
    Usa UUID v4 generado por PostgreSQL.
    """
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("gen_random_uuid()"),
    )


class SoftDeleteMixin:
    """
    Mixin para soft delete (borrado lógico).
    
    En lugar de eliminar el registro, marca deleted_at.
    """
    
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    
    @property
    def is_deleted(self) -> bool:
        """Retorna True si el registro está marcado como eliminado."""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Marca el registro como eliminado."""
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Restaura un registro eliminado."""
        self.deleted_at = None
