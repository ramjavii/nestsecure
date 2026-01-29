# =============================================================================
# NESTSECURE - Schemas de Servicio
# =============================================================================
"""
Schemas Pydantic para el modelo Service.
"""

from typing import Any, Optional

from pydantic import Field, field_validator

from app.models.service import ServiceProtocol, ServiceState
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


# =============================================================================
# Base Schema
# =============================================================================
class ServiceBase(BaseSchema):
    """Campos comunes de Service."""
    
    port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Número de puerto",
        examples=[80, 443, 22],
    )
    
    protocol: str = Field(
        default=ServiceProtocol.TCP.value,
        description="Protocolo (tcp/udp)",
    )
    
    service_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Nombre del servicio",
        examples=["http", "ssh", "postgresql"],
    )
    
    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        """Valida el protocolo."""
        valid = {p.value for p in ServiceProtocol}
        if v.lower() not in valid:
            raise ValueError(f"Protocolo inválido. Debe ser uno de: {valid}")
        return v.lower()


# =============================================================================
# Create Schema
# =============================================================================
class ServiceCreate(ServiceBase):
    """Schema para crear un servicio."""
    
    asset_id: str = Field(
        ...,
        description="ID del asset donde se detectó el servicio",
    )
    
    state: str = Field(
        default=ServiceState.OPEN.value,
        description="Estado del puerto",
    )
    
    product: Optional[str] = Field(
        None,
        max_length=255,
        description="Producto/software detectado",
    )
    
    version: Optional[str] = Field(
        None,
        max_length=100,
        description="Versión del servicio",
    )
    
    banner: Optional[str] = Field(
        None,
        description="Banner capturado",
    )
    
    ssl_enabled: bool = Field(
        default=False,
        description="Si tiene SSL/TLS habilitado",
    )


# =============================================================================
# Update Schema
# =============================================================================
class ServiceUpdate(BaseSchema):
    """Schema para actualizar un servicio."""
    
    state: Optional[str] = None
    service_name: Optional[str] = Field(None, max_length=100)
    product: Optional[str] = Field(None, max_length=255)
    version: Optional[str] = Field(None, max_length=100)
    banner: Optional[str] = None
    ssl_enabled: Optional[bool] = None
    cpe: Optional[str] = Field(None, max_length=500)
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Valida el estado si se proporciona."""
        if v is None:
            return v
        valid = {s.value for s in ServiceState}
        if v not in valid:
            raise ValueError(f"Estado inválido. Debe ser uno de: {valid}")
        return v


# =============================================================================
# Read Schemas
# =============================================================================
class ServiceRead(ServiceBase, IDSchema, TimestampSchema):
    """Schema para leer un servicio."""
    
    asset_id: str
    state: str
    product: Optional[str] = None
    version: Optional[str] = None
    cpe: Optional[str] = None
    banner: Optional[str] = None
    ssl_enabled: bool
    http_title: Optional[str] = None
    http_technologies: Optional[list[str]] = None


class ServiceReadMinimal(IDSchema):
    """Schema mínimo de servicio."""
    
    port: int
    protocol: str
    service_name: Optional[str] = None
    state: str


class ServiceInDB(ServiceRead):
    """Schema completo como está en la base de datos."""
    
    ssl_info: Optional[dict[str, Any]] = None
    detection_method: Optional[str] = None
    confidence: int
    extra_info: Optional[dict[str, Any]] = None
