# =============================================================================
# NESTSECURE - Modelo Base (re-export)
# =============================================================================
"""
Re-export de las clases base desde db.base.

Mantiene compatibilidad con imports desde app.models.base
"""

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

__all__ = ["Base", "TimestampMixin", "UUIDMixin", "SoftDeleteMixin"]
