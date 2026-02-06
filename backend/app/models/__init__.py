# =============================================================================
# NESTSECURE - Models Module
# =============================================================================
"""
Módulo de modelos SQLAlchemy.

Exports todos los modelos para uso en la aplicación y migraciones.
"""

from app.models.asset import Asset, AssetCriticality, AssetStatus, AssetType
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.cve_cache import CVECache
from app.models.organization import Organization
from app.models.report import Report, ReportFormat, ReportStatus, ReportType
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.service import Service, ServiceProtocol, ServiceState
from app.models.user import User, UserRole
from app.models.vulnerability import Vulnerability, VulnerabilitySeverity, VulnerabilityStatus
from app.models.vulnerability_comment import VulnerabilityComment

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "SoftDeleteMixin",
    # Models
    "Organization",
    "User",
    "Asset",
    "Service",
    "Scan",
    "CVECache",
    "Report",
    "Vulnerability",
    "VulnerabilityComment",
    # Enums
    "UserRole",
    "AssetType",
    "AssetCriticality",
    "AssetStatus",
    "ServiceProtocol",
    "ServiceState",
    "ScanType",
    "ScanStatus",
    "ReportType",
    "ReportFormat",
    "ReportStatus",
    "VulnerabilitySeverity",
    "VulnerabilityStatus",
]
