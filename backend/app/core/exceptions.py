# =============================================================================
# NESTSECURE - Excepciones Personalizadas
# =============================================================================
"""
Sistema de excepciones personalizadas para manejo de errores consistente.

Características:
- Jerarquía de excepciones clara
- Códigos de error estandarizados
- Información contextual para debugging
- Compatibilidad con RFC 7807 (Problem Details)
"""

from typing import Any, Dict, Optional

from app.utils.constants import ErrorCode


# =============================================================================
# Excepción Base
# =============================================================================
class NestSecureException(Exception):
    """
    Excepción base para todas las excepciones de NestSecure.
    
    Attributes:
        message: Mensaje de error legible
        error_code: Código de error estandarizado
        details: Información adicional del error
        status_code: Código HTTP sugerido
    """
    
    status_code: int = 500
    error_code: str = ErrorCode.INTERNAL_ERROR
    
    def __init__(
        self,
        message: str = "Error interno del servidor",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        self.message = message
        self.error_code = error_code or self.__class__.error_code
        self.details = details or {}
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para respuesta API."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }
    
    def to_problem_details(self, instance: Optional[str] = None) -> Dict[str, Any]:
        """
        Convierte a formato RFC 7807 Problem Details.
        
        Returns:
            Diccionario compatible con RFC 7807
        """
        return {
            "type": f"https://nestsecure.io/errors/{self.error_code}",
            "title": self.__class__.__name__,
            "status": self.status_code,
            "detail": self.message,
            "instance": instance,
            **self.details,
        }


# =============================================================================
# Excepciones de Autenticación
# =============================================================================
class AuthenticationError(NestSecureException):
    """Error de autenticación."""
    
    status_code = 401
    error_code = ErrorCode.AUTH_INVALID_CREDENTIALS
    
    def __init__(
        self,
        message: str = "Credenciales inválidas",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details, self.status_code)


class InvalidCredentialsError(AuthenticationError):
    """Credenciales inválidas (email/password incorrectos)."""
    
    error_code = ErrorCode.AUTH_INVALID_CREDENTIALS
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Email o contraseña incorrectos",
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    """Token de acceso expirado."""
    
    error_code = ErrorCode.AUTH_TOKEN_EXPIRED
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="El token ha expirado",
            details=details,
        )


class TokenInvalidError(AuthenticationError):
    """Token inválido o malformado."""
    
    error_code = ErrorCode.AUTH_TOKEN_INVALID
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Token inválido",
            details=details,
        )


class AccountDisabledError(AuthenticationError):
    """Cuenta deshabilitada."""
    
    status_code = 403
    error_code = ErrorCode.AUTH_ACCOUNT_DISABLED
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="La cuenta está deshabilitada",
            details=details,
        )


class AccountLockedError(AuthenticationError):
    """Cuenta bloqueada por intentos fallidos."""
    
    status_code = 403
    error_code = ErrorCode.AUTH_ACCOUNT_LOCKED
    
    def __init__(
        self,
        locked_until: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if locked_until:
            details["locked_until"] = locked_until
        super().__init__(
            message="La cuenta está bloqueada temporalmente",
            details=details,
        )


# =============================================================================
# Excepciones de Autorización
# =============================================================================
class AuthorizationError(NestSecureException):
    """Error de autorización (permisos insuficientes)."""
    
    status_code = 403
    error_code = ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS
    
    def __init__(
        self,
        message: str = "Permisos insuficientes",
        required_role: Optional[str] = None,
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if required_role:
            details["required_role"] = required_role
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(message, self.error_code, details, self.status_code)


class InsufficientPermissionsError(AuthorizationError):
    """Permisos insuficientes para la operación."""
    
    def __init__(
        self,
        operation: str,
        required_role: Optional[str] = None,
    ):
        super().__init__(
            message=f"No tienes permisos para: {operation}",
            required_role=required_role,
        )


# =============================================================================
# Excepciones de Validación
# =============================================================================
class ValidationError(NestSecureException):
    """Error de validación de datos."""
    
    status_code = 422
    error_code = ErrorCode.VALIDATION_INVALID_FORMAT
    
    def __init__(
        self,
        message: str = "Error de validación",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)[:100]  # Truncar valores largos
        super().__init__(message, self.error_code, details, self.status_code)


class RequiredFieldError(ValidationError):
    """Campo requerido faltante."""
    
    error_code = ErrorCode.VALIDATION_REQUIRED_FIELD
    
    def __init__(self, field: str):
        super().__init__(
            message=f"El campo '{field}' es requerido",
            field=field,
        )


class InvalidFormatError(ValidationError):
    """Formato de datos inválido."""
    
    error_code = ErrorCode.VALIDATION_INVALID_FORMAT
    
    def __init__(self, field: str, expected_format: str, value: Optional[Any] = None):
        super().__init__(
            message=f"El campo '{field}' tiene formato inválido. Esperado: {expected_format}",
            field=field,
            value=value,
            details={"expected_format": expected_format},
        )


class DuplicateError(ValidationError):
    """Valor duplicado."""
    
    status_code = 409
    error_code = ErrorCode.VALIDATION_DUPLICATE
    
    def __init__(self, field: str, value: Optional[Any] = None):
        super().__init__(
            message=f"Ya existe un registro con este valor de '{field}'",
            field=field,
            value=value,
        )


# =============================================================================
# Excepciones de Recursos
# =============================================================================
class ResourceError(NestSecureException):
    """Error relacionado con recursos."""
    
    status_code = 400
    error_code = ErrorCode.RESOURCE_NOT_FOUND
    
    def __init__(
        self,
        message: str = "Error de recurso",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = str(resource_id)
        super().__init__(message, self.error_code, details)


class NotFoundError(ResourceError):
    """Recurso no encontrado."""
    
    status_code = 404
    error_code = ErrorCode.RESOURCE_NOT_FOUND
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
    ):
        message = f"{resource_type} no encontrado"
        if resource_id:
            message = f"{resource_type} con ID '{resource_id}' no encontrado"
        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
        )


class ResourceExistsError(ResourceError):
    """El recurso ya existe."""
    
    status_code = 409
    error_code = ErrorCode.RESOURCE_ALREADY_EXISTS
    
    def __init__(
        self,
        resource_type: str,
        identifier: Optional[str] = None,
    ):
        message = f"{resource_type} ya existe"
        if identifier:
            message = f"{resource_type} '{identifier}' ya existe"
        super().__init__(
            message=message,
            resource_type=resource_type,
        )


class ResourceLockedError(ResourceError):
    """Recurso bloqueado."""
    
    status_code = 423
    error_code = ErrorCode.RESOURCE_LOCKED
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        message = f"{resource_type} está bloqueado"
        details = {}
        if reason:
            details["reason"] = reason
        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )


# =============================================================================
# Excepciones de Escaneo
# =============================================================================
class ScanError(NestSecureException):
    """Error durante escaneo."""
    
    status_code = 500
    error_code = ErrorCode.SCAN_FAILED
    
    def __init__(
        self,
        message: str = "Error durante el escaneo",
        scan_id: Optional[str] = None,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if scan_id:
            details["scan_id"] = scan_id
        if target:
            details["target"] = target
        super().__init__(message, self.error_code, details)


class ScanTimeoutError(ScanError):
    """Timeout durante escaneo."""
    
    error_code = ErrorCode.SCAN_TIMEOUT
    
    def __init__(
        self,
        scan_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(
            message="El escaneo excedió el tiempo máximo permitido",
            scan_id=scan_id,
            details=details,
        )


class TargetUnreachableError(ScanError):
    """Target no alcanzable."""
    
    status_code = 400
    error_code = ErrorCode.SCAN_TARGET_UNREACHABLE
    
    def __init__(self, target: str):
        super().__init__(
            message=f"No se puede alcanzar el objetivo: {target}",
            target=target,
        )


class InvalidTargetError(ScanError):
    """Target inválido."""
    
    status_code = 400
    error_code = ErrorCode.SCAN_INVALID_TARGET
    
    def __init__(self, target: str, reason: Optional[str] = None):
        message = f"Objetivo inválido: {target}"
        if reason:
            message += f". {reason}"
        super().__init__(
            message=message,
            target=target,
            details={"reason": reason} if reason else None,
        )


class ScanQuotaExceededError(ScanError):
    """Cuota de escaneos excedida."""
    
    status_code = 429
    error_code = ErrorCode.SCAN_QUOTA_EXCEEDED
    
    def __init__(
        self,
        current: int,
        limit: int,
        reset_at: Optional[str] = None,
    ):
        super().__init__(
            message=f"Cuota de escaneos excedida ({current}/{limit})",
            details={
                "current": current,
                "limit": limit,
                "reset_at": reset_at,
            },
        )


# =============================================================================
# Excepciones de Base de Datos
# =============================================================================
class DatabaseError(NestSecureException):
    """Error de base de datos."""
    
    status_code = 500
    error_code = ErrorCode.DB_CONNECTION_FAILED
    
    def __init__(
        self,
        message: str = "Error de base de datos",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(message, self.error_code, details)


class ConnectionError(DatabaseError):
    """Error de conexión a base de datos."""
    
    error_code = ErrorCode.DB_CONNECTION_FAILED
    
    def __init__(self, database: str = "PostgreSQL"):
        super().__init__(
            message=f"No se pudo conectar a {database}",
        )


class QueryError(DatabaseError):
    """Error en query."""
    
    error_code = ErrorCode.DB_QUERY_FAILED
    
    def __init__(self, operation: str):
        super().__init__(
            message=f"Error ejecutando operación: {operation}",
            operation=operation,
        )


class IntegrityError(DatabaseError):
    """Error de integridad de datos."""
    
    status_code = 409
    error_code = ErrorCode.DB_INTEGRITY_ERROR
    
    def __init__(self, constraint: Optional[str] = None):
        message = "Violación de integridad de datos"
        if constraint:
            message += f": {constraint}"
        super().__init__(
            message=message,
            details={"constraint": constraint} if constraint else None,
        )


# =============================================================================
# Excepciones de Servicios Externos
# =============================================================================
class ExternalServiceError(NestSecureException):
    """Error de servicio externo."""
    
    status_code = 502
    error_code = ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE
    
    def __init__(
        self,
        service: str,
        message: str = "Servicio externo no disponible",
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["service"] = service
        super().__init__(message, self.error_code, details)


class ServiceTimeoutError(ExternalServiceError):
    """Timeout de servicio externo."""
    
    error_code = ErrorCode.EXTERNAL_SERVICE_TIMEOUT
    
    def __init__(self, service: str, timeout_seconds: int):
        super().__init__(
            service=service,
            message=f"Timeout conectando a {service} ({timeout_seconds}s)",
            details={"timeout_seconds": timeout_seconds},
        )


class ServiceUnavailableError(ExternalServiceError):
    """Servicio externo no disponible."""
    
    status_code = 503
    error_code = ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE
    
    def __init__(self, service: str, retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            service=service,
            message=f"El servicio {service} no está disponible",
            details=details,
        )


# =============================================================================
# Excepciones de Configuración
# =============================================================================
class ConfigurationError(NestSecureException):
    """Error de configuración."""
    
    status_code = 500
    error_code = ErrorCode.CONFIGURATION_ERROR
    
    def __init__(
        self,
        message: str = "Error de configuración",
        setting: Optional[str] = None,
    ):
        details = {}
        if setting:
            details["setting"] = setting
        super().__init__(message, self.error_code, details)


class NotImplementedError(NestSecureException):
    """Funcionalidad no implementada."""
    
    status_code = 501
    error_code = ErrorCode.NOT_IMPLEMENTED
    
    def __init__(self, feature: str):
        super().__init__(
            message=f"Funcionalidad no implementada: {feature}",
            details={"feature": feature},
        )


# =============================================================================
# Exportar excepciones
# =============================================================================
__all__ = [
    # Base
    "NestSecureException",
    # Autenticación
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenInvalidError",
    "AccountDisabledError",
    "AccountLockedError",
    # Autorización
    "AuthorizationError",
    "InsufficientPermissionsError",
    # Validación
    "ValidationError",
    "RequiredFieldError",
    "InvalidFormatError",
    "DuplicateError",
    # Recursos
    "ResourceError",
    "NotFoundError",
    "ResourceExistsError",
    "ResourceLockedError",
    # Escaneo
    "ScanError",
    "ScanTimeoutError",
    "TargetUnreachableError",
    "InvalidTargetError",
    "ScanQuotaExceededError",
    # Base de datos
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "IntegrityError",
    # Servicios externos
    "ExternalServiceError",
    "ServiceTimeoutError",
    "ServiceUnavailableError",
    # Configuración
    "ConfigurationError",
    "NotImplementedError",
]
