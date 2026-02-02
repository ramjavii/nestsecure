# =============================================================================
# NESTSECURE - Módulo Core
# =============================================================================
"""
Módulo core con funcionalidades centrales de la aplicación.

Incluye:
- security: Funciones de seguridad y hashing de passwords
- exceptions: Excepciones personalizadas
- exception_handlers: Handlers globales para FastAPI
- metrics: Sistema de métricas Prometheus
"""

from .exceptions import (
    AccountDisabledError,
    AccountLockedError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DatabaseError,
    DuplicateError,
    ExternalServiceError,
    InsufficientPermissionsError,
    IntegrityError,
    InvalidCredentialsError,
    InvalidFormatError,
    InvalidTargetError,
    NestSecureException,
    NotFoundError,
    NotImplementedError,
    QueryError,
    RequiredFieldError,
    ResourceError,
    ResourceExistsError,
    ResourceLockedError,
    ScanError,
    ScanQuotaExceededError,
    ScanTimeoutError,
    ServiceTimeoutError,
    ServiceUnavailableError,
    TargetUnreachableError,
    TokenExpiredError,
    TokenInvalidError,
    ValidationError,
)
from .exception_handlers import register_exception_handlers
from .metrics import setup_metrics, track_scan, track_celery_task
from .security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    decode_token,
)

__all__ = [
    # Security
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    # Exceptions
    "NestSecureException",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenInvalidError",
    "AccountDisabledError",
    "AccountLockedError",
    "AuthorizationError",
    "InsufficientPermissionsError",
    "ValidationError",
    "RequiredFieldError",
    "InvalidFormatError",
    "DuplicateError",
    "ResourceError",
    "NotFoundError",
    "ResourceExistsError",
    "ResourceLockedError",
    "ScanError",
    "ScanTimeoutError",
    "TargetUnreachableError",
    "InvalidTargetError",
    "ScanQuotaExceededError",
    "DatabaseError",
    "QueryError",
    "IntegrityError",
    "ExternalServiceError",
    "ServiceTimeoutError",
    "ServiceUnavailableError",
    "ConfigurationError",
    "NotImplementedError",
    # Handlers
    "register_exception_handlers",
    # Metrics
    "setup_metrics",
    "track_scan",
    "track_celery_task",
]
