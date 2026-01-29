# =============================================================================
# NESTSECURE - Schemas de Autenticación
# =============================================================================
"""
Schemas Pydantic para autenticación y tokens JWT.

Incluye:
- Token: Respuesta con access y refresh tokens
- TokenPayload: Datos decodificados del JWT
- LoginRequest: Datos para login
"""

from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


# =============================================================================
# Request Schemas
# =============================================================================
class LoginRequest(BaseSchema):
    """Schema para solicitud de login."""
    
    email: EmailStr = Field(
        ...,
        description="Email del usuario",
        examples=["usuario@ejemplo.com"],
    )
    
    password: str = Field(
        ...,
        min_length=1,
        description="Contraseña del usuario",
    )


class RefreshTokenRequest(BaseSchema):
    """Schema para solicitud de refresh token."""
    
    refresh_token: str = Field(
        ...,
        description="Token de refresco válido",
    )


# =============================================================================
# Response Schemas
# =============================================================================
class Token(BaseSchema):
    """Schema de respuesta con tokens JWT."""
    
    access_token: str = Field(
        ...,
        description="Token de acceso JWT",
    )
    
    refresh_token: str = Field(
        ...,
        description="Token de refresco JWT",
    )
    
    token_type: str = Field(
        default="bearer",
        description="Tipo de token (siempre 'bearer')",
    )
    
    expires_in: int = Field(
        ...,
        description="Segundos hasta que expire el access token",
    )


class TokenPayload(BaseSchema):
    """
    Schema del payload decodificado del JWT.
    
    Usado internamente para validar tokens.
    """
    
    sub: str = Field(
        ...,
        description="Subject (user_id)",
    )
    
    exp: datetime = Field(
        ...,
        description="Fecha de expiración",
    )
    
    type: Literal["access", "refresh"] = Field(
        ...,
        description="Tipo de token",
    )


# =============================================================================
# Schemas de Usuario para Auth
# =============================================================================
class AuthUser(BaseSchema):
    """Schema de usuario autenticado para respuestas de auth."""
    
    id: str
    email: EmailStr
    full_name: str
    role: str
    organization_id: str
    is_active: bool
    is_superuser: bool


class LoginResponse(BaseSchema):
    """Schema de respuesta completa de login."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser
