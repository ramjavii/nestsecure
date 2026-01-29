# =============================================================================
# NESTSECURE - Database Module
# =============================================================================
"""
Módulo de base de datos.

Exports:
- Base: Clase base para modelos SQLAlchemy
- get_db: Dependency de FastAPI para obtener sesión
- init_db: Inicializa la conexión a la base de datos
- close_db: Cierra la conexión
"""

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.db.session import (
    AsyncSessionDep,
    check_db_connection,
    close_db,
    create_db_engine,
    get_db,
    get_engine,
    init_db,
)

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "SoftDeleteMixin",
    # Session management
    "get_db",
    "AsyncSessionDep",
    "init_db",
    "close_db",
    "get_engine",
    "create_db_engine",
    "check_db_connection",
]
