# =============================================================================
# NESTSECURE - Schemas Comunes
# =============================================================================
"""
Schemas Pydantic compartidos entre diferentes módulos.

Incluye:
- Modelos base con configuración común
- Schemas de paginación
- Schemas de respuesta estándar
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Type variable para schemas genéricos
T = TypeVar("T")


# =============================================================================
# Base Schemas
# =============================================================================
class BaseSchema(BaseModel):
    """
    Schema base con configuración común.
    
    Todos los schemas deben heredar de este.
    """
    
    model_config = ConfigDict(
        from_attributes=True,  # Permite crear desde objetos ORM
        populate_by_name=True,  # Permite usar alias
        str_strip_whitespace=True,  # Elimina espacios en strings
    )


class TimestampSchema(BaseSchema):
    """Schema con campos de timestamp."""
    
    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """Schema con campo ID."""
    
    id: str = Field(..., description="UUID único del recurso")


# =============================================================================
# Paginación
# =============================================================================
class PaginationParams(BaseSchema):
    """Parámetros de paginación para queries."""
    
    page: int = Field(default=1, ge=1, description="Número de página")
    page_size: int = Field(default=20, ge=1, le=100, description="Items por página")
    
    @property
    def offset(self) -> int:
        """Calcula el offset para la query."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema, Generic[T]):
    """
    Respuesta paginada genérica.
    
    Uso:
        PaginatedResponse[UserRead](items=[...], total=100, ...)
    """
    
    items: list[T]
    total: int = Field(..., description="Total de items")
    page: int = Field(..., description="Página actual")
    page_size: int = Field(..., description="Items por página")
    pages: int = Field(..., description="Total de páginas")
    
    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Factory method para crear respuesta paginada."""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


# =============================================================================
# Respuestas Estándar
# =============================================================================
class MessageResponse(BaseSchema):
    """Respuesta con mensaje simple."""
    
    message: str
    success: bool = True


class ErrorResponse(BaseSchema):
    """Respuesta de error."""
    
    detail: str
    error_code: str | None = None
    errors: list[dict[str, Any]] | None = None


class DeleteResponse(BaseSchema):
    """Respuesta de eliminación."""
    
    message: str = "Recurso eliminado exitosamente"
    deleted_id: str


class BulkOperationResponse(BaseSchema):
    """Respuesta de operación masiva."""
    
    success_count: int
    error_count: int
    errors: list[dict[str, Any]] | None = None


# =============================================================================
# Filtros Comunes
# =============================================================================
class DateRangeFilter(BaseSchema):
    """Filtro por rango de fechas."""
    
    start_date: datetime | None = None
    end_date: datetime | None = None


class SearchFilter(BaseSchema):
    """Filtro de búsqueda con texto."""
    
    query: str | None = Field(None, min_length=1, max_length=255)
    fields: list[str] | None = None  # Campos donde buscar
