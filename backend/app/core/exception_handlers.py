# =============================================================================
# NESTSECURE - Exception Handlers Globales
# =============================================================================
"""
Handlers globales para excepciones en FastAPI.

Proporciona respuestas consistentes para todos los tipos de errores,
incluyendo logging automático y formato RFC 7807.
"""

import traceback
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError

from app.utils.logger import get_logger

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    IntegrityError,
    NestSecureException,
    NotFoundError,
    ScanError,
    ValidationError,
)

logger = get_logger(__name__)


# =============================================================================
# Response Helpers
# =============================================================================
def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: dict = None,
    request: Request = None,
) -> JSONResponse:
    """
    Crea una respuesta de error consistente.
    
    Returns:
        JSONResponse con formato RFC 7807-like
    """
    content = {
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    
    if details:
        content["error"]["details"] = details
    
    # Agregar path si está disponible
    if request:
        content["error"]["path"] = str(request.url.path)
    
    return JSONResponse(
        status_code=status_code,
        content=content,
    )


# =============================================================================
# Exception Handlers
# =============================================================================
async def nestsecure_exception_handler(
    request: Request,
    exc: NestSecureException
) -> JSONResponse:
    """Handler para excepciones personalizadas de NestSecure."""
    
    # Log según la severidad
    if exc.status_code >= 500:
        logger.error(
            f"Error interno: {exc.message}",
            exc_info=True,
            extra={"extra_data": exc.details}
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"Error de cliente: {exc.message}",
            extra={"extra_data": exc.details}
        )
    
    return create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        request=request,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handler para errores de validación de FastAPI/Pydantic."""
    
    # Extraer errores de validación
    errors = []
    for error in exc.errors():
        loc = ".".join(str(l) for l in error["loc"] if l != "body")
        errors.append({
            "field": loc,
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        f"Error de validación en {request.url.path}",
        extra={"extra_data": {"errors": errors}}
    )
    
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VAL_2002",
        message="Error de validación en los datos enviados",
        details={"validation_errors": errors},
        request=request,
    )


async def pydantic_validation_handler(
    request: Request,
    exc: PydanticValidationError
) -> JSONResponse:
    """Handler para errores de validación de Pydantic puro."""
    
    errors = []
    for error in exc.errors():
        loc = ".".join(str(l) for l in error["loc"])
        errors.append({
            "field": loc,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VAL_2002",
        message="Error de validación",
        details={"validation_errors": errors},
        request=request,
    )


async def sqlalchemy_integrity_handler(
    request: Request,
    exc: SQLAlchemyIntegrityError
) -> JSONResponse:
    """Handler para errores de integridad de SQLAlchemy."""
    
    # Extraer información del constraint violado
    constraint = None
    if hasattr(exc, "orig") and exc.orig:
        error_str = str(exc.orig)
        if "unique constraint" in error_str.lower():
            constraint = "unique"
        elif "foreign key" in error_str.lower():
            constraint = "foreign_key"
    
    logger.warning(
        f"Error de integridad de datos: {str(exc)[:200]}",
        extra={"extra_data": {"constraint": constraint}}
    )
    
    return create_error_response(
        status_code=status.HTTP_409_CONFLICT,
        error_code="DB_5004",
        message="Conflicto de datos. El registro ya existe o viola una restricción.",
        details={"constraint_type": constraint} if constraint else None,
        request=request,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handler genérico para excepciones no manejadas."""
    
    # Log completo del error
    logger.error(
        f"Error no manejado: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "extra_data": {
                "path": str(request.url.path),
                "method": request.method,
                "exception_type": type(exc).__name__,
            }
        }
    )
    
    # En desarrollo, incluir más detalles
    details = None
    # TODO: Obtener esto de settings.DEBUG
    # if settings.DEBUG:
    #     details = {
    #         "exception_type": type(exc).__name__,
    #         "traceback": traceback.format_exc().split("\n")[-5:],
    #     }
    
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INT_9001",
        message="Error interno del servidor",
        details=details,
        request=request,
    )


# =============================================================================
# Registro de Handlers
# =============================================================================
def register_exception_handlers(app: FastAPI) -> None:
    """
    Registra todos los exception handlers en la aplicación FastAPI.
    
    Args:
        app: Instancia de FastAPI
    """
    # Excepciones personalizadas de NestSecure
    app.add_exception_handler(NestSecureException, nestsecure_exception_handler)
    
    # Excepciones específicas (por si se necesita manejo diferente)
    app.add_exception_handler(AuthenticationError, nestsecure_exception_handler)
    app.add_exception_handler(AuthorizationError, nestsecure_exception_handler)
    app.add_exception_handler(NotFoundError, nestsecure_exception_handler)
    app.add_exception_handler(ValidationError, nestsecure_exception_handler)
    app.add_exception_handler(ScanError, nestsecure_exception_handler)
    app.add_exception_handler(DatabaseError, nestsecure_exception_handler)
    
    # Errores de validación de FastAPI
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Errores de Pydantic
    app.add_exception_handler(PydanticValidationError, pydantic_validation_handler)
    
    # Errores de SQLAlchemy
    app.add_exception_handler(SQLAlchemyIntegrityError, sqlalchemy_integrity_handler)
    
    # Handler genérico para todo lo demás (debe ser el último)
    app.add_exception_handler(Exception, generic_exception_handler)


# =============================================================================
# Exportar
# =============================================================================
__all__ = [
    "register_exception_handlers",
    "create_error_response",
    "nestsecure_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
]
