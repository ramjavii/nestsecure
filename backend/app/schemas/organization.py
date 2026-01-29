# =============================================================================
# NESTSECURE - Schemas de Organización
# =============================================================================
"""
Schemas Pydantic para el modelo Organization.

Incluye:
- OrganizationCreate: Para crear organizaciones
- OrganizationUpdate: Para actualizar organizaciones
- OrganizationRead: Para leer organizaciones
- OrganizationInDB: Representación completa de la DB
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


# =============================================================================
# Base Schema
# =============================================================================
class OrganizationBase(BaseSchema):
    """Campos comunes de Organization."""
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nombre de la organización",
        examples=["Empresa ABC"],
    )
    
    slug: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Identificador URL-friendly único",
        examples=["empresa-abc"],
    )
    
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Descripción de la organización",
    )


# =============================================================================
# Create Schema
# =============================================================================
class OrganizationCreate(BaseSchema):
    """Schema para crear una organización."""
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nombre de la organización",
        examples=["Empresa ABC"],
    )
    
    slug: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Identificador URL-friendly único (será convertido a minúsculas)",
        examples=["empresa-abc"],
    )
    
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Descripción de la organización",
    )
    
    max_assets: int = Field(
        default=100,
        ge=1,
        le=100000,
        description="Límite de assets permitidos",
    )
    
    settings: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Configuración personalizada",
    )
    
    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Convierte a minúsculas y valida formato de slug."""
        v = v.lower()
        import re
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError(
                "El slug solo puede contener letras minúsculas, números y guiones"
            )
        return v


# =============================================================================
# Update Schema
# =============================================================================
class OrganizationUpdate(BaseSchema):
    """Schema para actualizar una organización."""
    
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
    )
    
    description: Optional[str] = Field(
        None,
        max_length=1000,
    )
    
    max_assets: Optional[int] = Field(
        None,
        ge=1,
        le=100000,
    )
    
    settings: Optional[dict[str, Any]] = None
    
    is_active: Optional[bool] = None
    
    license_key: Optional[str] = None
    
    license_expires_at: Optional[datetime] = None


# =============================================================================
# Read Schemas
# =============================================================================
class OrganizationRead(OrganizationBase, IDSchema, TimestampSchema):
    """Schema para leer una organización (respuesta de API)."""
    
    max_assets: int
    is_active: bool
    license_expires_at: Optional[datetime] = None
    
    # Campos calculados
    user_count: int = Field(default=0, description="Número de usuarios")
    asset_count: int = Field(default=0, description="Número de assets")


class OrganizationReadMinimal(IDSchema):
    """Schema mínimo de organización para referencias."""
    
    name: str
    slug: str


class OrganizationInDB(OrganizationRead):
    """Schema completo como está en la base de datos."""
    
    license_key: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


# =============================================================================
# Schemas Adicionales
# =============================================================================
class OrganizationStats(BaseSchema):
    """Estadísticas de una organización."""
    
    organization_id: str
    user_count: int
    asset_count: int
    scan_count: int
    vulnerability_count: int
    critical_vulnerabilities: int
    high_vulnerabilities: int


class OrganizationSettings(BaseSchema):
    """Configuración de una organización."""
    
    scan_defaults: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Configuración por defecto para escaneos",
    )
    
    notification_settings: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Configuración de notificaciones",
    )
    
    retention_days: int = Field(
        default=365,
        ge=30,
        le=3650,
        description="Días de retención de datos",
    )
