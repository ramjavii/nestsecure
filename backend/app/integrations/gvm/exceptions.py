# =============================================================================
# NESTSECURE - GVM Exceptions
# =============================================================================
"""
Excepciones específicas para la integración con GVM/OpenVAS.
"""

from typing import Optional, Dict, Any


class GVMError(Exception):
    """
    Excepción base para errores de GVM.
    
    Attributes:
        message: Mensaje de error
        details: Detalles adicionales del error
        gvm_status: Código de estado de GVM si aplica
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        gvm_status: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.gvm_status = gvm_status
        super().__init__(self.message)
    
    def __str__(self) -> str:
        base = f"GVMError: {self.message}"
        if self.gvm_status:
            base += f" (status: {self.gvm_status})"
        return base
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para logging/serialización."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "gvm_status": self.gvm_status,
        }


class GVMConnectionError(GVMError):
    """
    Error de conexión con GVM.
    
    Se lanza cuando:
    - No se puede establecer conexión con el socket/TLS
    - Se pierde la conexión durante una operación
    - Timeout de conexión
    """
    
    def __init__(
        self,
        message: str = "Cannot connect to GVM",
        host: Optional[str] = None,
        port: Optional[int] = None,
        socket_path: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details.update({
            "host": host,
            "port": port,
            "socket_path": socket_path,
        })
        super().__init__(message, details=details, **kwargs)
        self.host = host
        self.port = port
        self.socket_path = socket_path


class GVMAuthenticationError(GVMError):
    """
    Error de autenticación con GVM.
    
    Se lanza cuando:
    - Credenciales inválidas
    - Usuario no existe
    - Sesión expirada
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        username: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["username"] = username
        super().__init__(message, details=details, **kwargs)
        self.username = username


class GVMTimeoutError(GVMError):
    """
    Error de timeout en operación GVM.
    
    Se lanza cuando:
    - Una operación excede el tiempo límite
    - Un escaneo tarda demasiado
    """
    
    def __init__(
        self,
        message: str = "Operation timed out",
        operation: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details.update({
            "operation": operation,
            "timeout_seconds": timeout_seconds,
        })
        super().__init__(message, details=details, **kwargs)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class GVMScanError(GVMError):
    """
    Error durante un escaneo.
    
    Se lanza cuando:
    - Falla al crear target/task
    - Error al iniciar escaneo
    - Escaneo termina con error
    """
    
    def __init__(
        self,
        message: str = "Scan error",
        scan_id: Optional[str] = None,
        task_id: Optional[str] = None,
        target_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details.update({
            "scan_id": scan_id,
            "task_id": task_id,
            "target_id": target_id,
        })
        super().__init__(message, details=details, **kwargs)
        self.scan_id = scan_id
        self.task_id = task_id
        self.target_id = target_id


class GVMNotFoundError(GVMError):
    """
    Recurso no encontrado en GVM.
    
    Se lanza cuando:
    - Target no existe
    - Task no existe
    - Report no existe
    """
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details.update({
            "resource_type": resource_type,
            "resource_id": resource_id,
        })
        super().__init__(message, details=details, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id


class GVMConfigurationError(GVMError):
    """
    Error de configuración de GVM.
    
    Se lanza cuando:
    - Configuración inválida
    - Faltan parámetros requeridos
    - Port list o scan config no válidos
    """
    
    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details.update({
            "config_key": config_key,
            "config_value": config_value,
        })
        super().__init__(message, details=details, **kwargs)
        self.config_key = config_key
        self.config_value = config_value
