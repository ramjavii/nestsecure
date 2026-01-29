# =============================================================================
# NESTSECURE - Schemas Module
# =============================================================================
"""
Módulo de schemas Pydantic.

Exports todos los schemas para uso en la API.
"""

from app.schemas.asset import (
    AssetBase,
    AssetBulkCreate,
    AssetCreate,
    AssetInDB,
    AssetRead,
    AssetReadMinimal,
    AssetReadWithOrg,
    AssetSummary,
    AssetUpdate,
    AssetVulnerabilityStats,
)
from app.schemas.common import (
    BaseSchema,
    BulkOperationResponse,
    DateRangeFilter,
    DeleteResponse,
    ErrorResponse,
    IDSchema,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    SearchFilter,
    TimestampSchema,
)
from app.schemas.organization import (
    OrganizationBase,
    OrganizationCreate,
    OrganizationInDB,
    OrganizationRead,
    OrganizationReadMinimal,
    OrganizationSettings,
    OrganizationStats,
    OrganizationUpdate,
)
from app.schemas.service import (
    ServiceBase,
    ServiceCreate,
    ServiceInDB,
    ServiceRead,
    ServiceReadMinimal,
    ServiceUpdate,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserInDB,
    UserLogin,
    UserRead,
    UserReadMinimal,
    UserReadWithOrg,
    UserRegister,
    UserUpdate,
    UserUpdatePassword,
)

__all__ = [
    # Common
    "BaseSchema",
    "IDSchema",
    "TimestampSchema",
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    "DeleteResponse",
    "BulkOperationResponse",
    "DateRangeFilter",
    "SearchFilter",
    # Organization
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationUpdate",
    "OrganizationRead",
    "OrganizationReadMinimal",
    "OrganizationInDB",
    "OrganizationStats",
    "OrganizationSettings",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserUpdatePassword",
    "UserRead",
    "UserReadMinimal",
    "UserReadWithOrg",
    "UserInDB",
    "UserLogin",
    "UserRegister",
    # Asset
    "AssetBase",
    "AssetCreate",
    "AssetUpdate",
    "AssetRead",
    "AssetReadMinimal",
    "AssetReadWithOrg",
    "AssetInDB",
    "AssetSummary",
    "AssetVulnerabilityStats",
    "AssetBulkCreate",
    # Service
    "ServiceBase",
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceRead",
    "ServiceReadMinimal",
    "ServiceInDB",
]
