# =============================================================================
# NESTSECURE - Schemas de Usuario
# =============================================================================
"""
Schemas Pydantic para el modelo User.

Incluye:
- UserCreate: Para crear usuarios
- UserUpdate: Para actualizar usuarios
- UserRead: Para leer usuarios (sin password)
- UserInDB: Representación completa con password hasheado
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.schemas.organization import OrganizationReadMinimal


# =============================================================================
# Base Schema
# =============================================================================
class UserBase(BaseSchema):
    """Campos comunes de User."""
    
    email: EmailStr = Field(
        ...,
        description="Email único del usuario",
        examples=["usuario@ejemplo.com"],
    )
    
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nombre completo del usuario",
        examples=["Juan Pérez"],
    )
    
    role: str = Field(
        default=UserRole.VIEWER.value,
        description="Rol del usuario en el sistema",
        examples=["viewer", "analyst", "operator", "admin"],
    )
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Valida que el rol sea válido."""
        valid_roles = {r.value for r in UserRole}
        if v not in valid_roles:
            raise ValueError(f"Rol inválido. Debe ser uno de: {valid_roles}")
        return v


# =============================================================================
# Create Schema
# =============================================================================
class UserCreate(UserBase):
    """Schema para crear un usuario."""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Contraseña del usuario",
    )
    
    organization_id: str = Field(
        ...,
        description="ID de la organización a la que pertenece",
    )
    
    is_active: bool = Field(
        default=True,
        description="Si el usuario puede hacer login",
    )
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Valida que la contraseña sea segura.
        
        Requisitos:
        - Al menos 8 caracteres
        - Al menos una mayúscula
        - Al menos una minúscula
        - Al menos un número
        """
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe tener al menos una mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe tener al menos una minúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe tener al menos un número")
        return v


# =============================================================================
# Update Schema
# =============================================================================
class UserUpdate(BaseSchema):
    """Schema para actualizar un usuario."""
    
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
    )
    
    role: Optional[str] = None
    
    is_active: Optional[bool] = None
    
    avatar_url: Optional[str] = Field(
        None,
        max_length=500,
    )
    
    preferences: Optional[dict[str, Any]] = None
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Valida que el rol sea válido si se proporciona."""
        if v is None:
            return v
        valid_roles = {r.value for r in UserRole}
        if v not in valid_roles:
            raise ValueError(f"Rol inválido. Debe ser uno de: {valid_roles}")
        return v


class UserUpdatePassword(BaseSchema):
    """Schema para cambiar contraseña."""
    
    current_password: str = Field(
        ...,
        description="Contraseña actual",
    )
    
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Nueva contraseña",
    )
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Valida que la nueva contraseña sea segura."""
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe tener al menos una mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe tener al menos una minúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe tener al menos un número")
        return v


# =============================================================================
# Read Schemas
# =============================================================================
class UserRead(UserBase, IDSchema, TimestampSchema):
    """Schema para leer un usuario (respuesta de API)."""
    
    organization_id: str
    is_active: bool
    is_superuser: bool = False
    last_login_at: Optional[datetime] = None
    avatar_url: Optional[str] = None


class UserReadWithOrg(UserRead):
    """Schema de usuario con información de organización."""
    
    organization: OrganizationReadMinimal


class UserReadMinimal(IDSchema):
    """Schema mínimo de usuario para referencias."""
    
    email: EmailStr
    full_name: str
    role: str


class UserInDB(UserRead):
    """Schema completo como está en la base de datos."""
    
    hashed_password: str
    permissions: Optional[dict[str, Any]] = None
    preferences: Optional[dict[str, Any]] = None


# =============================================================================
# Schemas de Autenticación
# =============================================================================
class UserLogin(BaseSchema):
    """Schema para login."""
    
    email: EmailStr
    password: str


class UserRegister(UserCreate):
    """Schema para registro (igual que create por ahora)."""
    pass
