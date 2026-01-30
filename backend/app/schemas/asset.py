# =============================================================================
# NESTSECURE - Schemas de Asset
# =============================================================================
"""
Schemas Pydantic para el modelo Asset.

Incluye:
- AssetCreate: Para crear assets
- AssetUpdate: Para actualizar assets
- AssetRead: Para leer assets
- AssetInDB: Representación completa de la DB
"""

from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Optional, Union

from pydantic import Field, IPvAnyAddress, field_serializer, field_validator

from app.models.asset import AssetCriticality, AssetStatus, AssetType
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema
from app.schemas.organization import OrganizationReadMinimal


# =============================================================================
# Base Schema
# =============================================================================
class AssetBase(BaseSchema):
    """Campos comunes de Asset."""
    
    ip_address: str = Field(
        ...,
        description="Dirección IP del asset",
        examples=["192.168.1.100", "10.0.0.1"],
    )
    
    hostname: Optional[str] = Field(
        None,
        max_length=255,
        description="Nombre del host",
        examples=["server-prod-01", "web-server"],
    )
    
    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Valida que sea una IP válida."""
        try:
            # Esto validará IPv4 e IPv6
            IPvAnyAddress(v)
            return v
        except ValueError:
            raise ValueError(f"'{v}' no es una dirección IP válida")


# =============================================================================
# Create Schema
# =============================================================================
class AssetCreate(AssetBase):
    """Schema para crear un asset."""
    
    organization_id: Optional[str] = Field(
        None,
        description="ID de la organización propietaria (opcional, se usa la del usuario)",
    )
    
    mac_address: Optional[str] = Field(
        None,
        pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
        description="Dirección MAC",
        examples=["AA:BB:CC:DD:EE:FF"],
    )
    
    operating_system: Optional[str] = Field(
        None,
        max_length=255,
        description="Sistema operativo",
        examples=["Ubuntu 22.04", "Windows Server 2019"],
    )
    
    os_version: Optional[str] = Field(
        None,
        max_length=100,
    )
    
    asset_type: str = Field(
        default=AssetType.SERVER.value,
        description="Tipo de asset",
    )
    
    criticality: str = Field(
        default=AssetCriticality.MEDIUM.value,
        description="Nivel de criticidad",
    )
    
    tags: Optional[list[str]] = Field(
        default_factory=list,
        description="Etiquetas para categorización",
        examples=[["production", "web", "critical"]],
    )
    
    description: Optional[str] = Field(
        None,
        max_length=1000,
    )
    
    @field_validator("asset_type")
    @classmethod
    def validate_asset_type(cls, v: str) -> str:
        """Valida el tipo de asset."""
        valid_types = {t.value for t in AssetType}
        if v not in valid_types:
            raise ValueError(f"Tipo inválido. Debe ser uno de: {valid_types}")
        return v
    
    @field_validator("criticality")
    @classmethod
    def validate_criticality(cls, v: str) -> str:
        """Valida la criticidad."""
        valid = {c.value for c in AssetCriticality}
        if v not in valid:
            raise ValueError(f"Criticidad inválida. Debe ser una de: {valid}")
        return v
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[list[str]]) -> list[str]:
        """Limpia y valida las etiquetas."""
        if v is None:
            return []
        return [tag.strip().lower() for tag in v if tag.strip()]


# =============================================================================
# Update Schema
# =============================================================================
class AssetUpdate(BaseSchema):
    """Schema para actualizar un asset."""
    
    hostname: Optional[str] = Field(
        None,
        max_length=255,
    )
    
    mac_address: Optional[str] = Field(
        None,
        pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
    )
    
    operating_system: Optional[str] = Field(
        None,
        max_length=255,
    )
    
    os_version: Optional[str] = Field(
        None,
        max_length=100,
    )
    
    asset_type: Optional[str] = None
    
    criticality: Optional[str] = None
    
    tags: Optional[list[str]] = None
    
    description: Optional[str] = Field(
        None,
        max_length=1000,
    )
    
    status: Optional[str] = None
    
    @field_validator("asset_type")
    @classmethod
    def validate_asset_type(cls, v: Optional[str]) -> Optional[str]:
        """Valida el tipo de asset si se proporciona."""
        if v is None:
            return v
        valid_types = {t.value for t in AssetType}
        if v not in valid_types:
            raise ValueError(f"Tipo inválido. Debe ser uno de: {valid_types}")
        return v
    
    @field_validator("criticality")
    @classmethod
    def validate_criticality(cls, v: Optional[str]) -> Optional[str]:
        """Valida la criticidad si se proporciona."""
        if v is None:
            return v
        valid = {c.value for c in AssetCriticality}
        if v not in valid:
            raise ValueError(f"Criticidad inválida. Debe ser una de: {valid}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Valida el estado si se proporciona."""
        if v is None:
            return v
        valid = {s.value for s in AssetStatus}
        if v not in valid:
            raise ValueError(f"Estado inválido. Debe ser uno de: {valid}")
        return v


# =============================================================================
# Read Schemas
# =============================================================================
class AssetRead(AssetBase, IDSchema, TimestampSchema):
    """Schema para leer un asset (respuesta de API)."""
    
    # Aceptar tanto str como IPv4Address/IPv6Address del modelo INET
    ip_address: Union[str, IPv4Address, IPv6Address]
    
    organization_id: str
    mac_address: Optional[str] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    asset_type: str
    criticality: str
    tags: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    status: str
    is_reachable: bool
    
    # Métricas
    risk_score: float
    vuln_critical_count: int
    vuln_high_count: int
    vuln_medium_count: int
    vuln_low_count: int
    
    @field_serializer("ip_address")
    def serialize_ip(self, ip: Union[str, IPv4Address, IPv6Address]) -> str:
        """Convierte IPv4Address/IPv6Address a string."""
        return str(ip)
    
    # Timestamps
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    last_scanned: Optional[datetime] = None


class AssetReadMinimal(IDSchema):
    """Schema mínimo de asset para referencias."""
    
    ip_address: Union[str, IPv4Address, IPv6Address]
    hostname: Optional[str] = None
    status: str
    criticality: str
    
    @field_serializer("ip_address")
    def serialize_ip(self, ip: Union[str, IPv4Address, IPv6Address]) -> str:
        """Convierte IPv4Address/IPv6Address a string."""
        return str(ip)


class AssetReadWithOrg(AssetRead):
    """Schema de asset con información de organización."""
    
    organization: OrganizationReadMinimal


class AssetInDB(AssetRead):
    """Schema completo como está en la base de datos."""
    
    os_cpe: Optional[str] = None
    metadata_extra: Optional[dict[str, Any]] = None


# =============================================================================
# Schemas Adicionales
# =============================================================================
class AssetSummary(BaseSchema):
    """Resumen de un asset."""
    
    id: str
    ip_address: Union[str, IPv4Address, IPv6Address]
    hostname: Optional[str] = None
    criticality: str
    risk_score: float
    total_vulnerabilities: int
    critical_vulnerabilities: int
    
    @field_serializer("ip_address")
    def serialize_ip(self, ip: Union[str, IPv4Address, IPv6Address]) -> str:
        """Convierte IPv4Address/IPv6Address a string."""
        return str(ip)


class AssetVulnerabilityStats(BaseSchema):
    """Estadísticas de vulnerabilidades de un asset."""
    
    asset_id: str
    critical: int
    high: int
    medium: int
    low: int
    total: int
    risk_score: float


class AssetBulkCreate(BaseSchema):
    """Schema para crear múltiples assets."""
    
    organization_id: str
    assets: list[AssetCreate] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Lista de assets a crear",
    )
