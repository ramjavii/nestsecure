# =============================================================================
# NESTSECURE - Nuclei Exceptions
# =============================================================================
"""
Excepciones personalizadas para la integración con Nuclei.

Proporciona excepciones específicas para diferentes tipos de errores
que pueden ocurrir durante los escaneos de Nuclei.
"""

from typing import Optional, Dict, Any


class NucleiError(Exception):
    """
    Excepción base para errores de Nuclei.
    
    Todas las excepciones específicas de Nuclei heredan de esta clase.
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializar excepción.
        
        Args:
            message: Mensaje de error
            details: Diccionario con detalles adicionales
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir excepción a diccionario."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class NucleiNotFoundError(NucleiError):
    """
    Nuclei no está instalado o no se encuentra en el PATH.
    
    Ocurre cuando el binario de Nuclei no está disponible
    en el sistema.
    """
    
    def __init__(self, path: Optional[str] = None):
        """
        Inicializar excepción.
        
        Args:
            path: Ruta donde se buscó Nuclei (opcional)
        """
        message = "Nuclei is not installed or not found in PATH"
        if path:
            message = f"Nuclei not found at: {path}"
        
        super().__init__(
            message,
            details={"searched_path": path}
        )


class NucleiTimeoutError(NucleiError):
    """
    El escaneo de Nuclei excedió el timeout.
    
    Ocurre cuando un escaneo tarda más del tiempo permitido.
    """
    
    def __init__(self, timeout: int, target: str):
        """
        Inicializar excepción.
        
        Args:
            timeout: Timeout en segundos
            target: Target que se estaba escaneando
        """
        super().__init__(
            f"Nuclei scan timed out after {timeout} seconds for target: {target}",
            details={
                "timeout_seconds": timeout,
                "target": target,
            }
        )
        self.timeout = timeout
        self.target = target


class NucleiTemplateError(NucleiError):
    """
    Error relacionado con templates de Nuclei.
    
    Ocurre cuando hay problemas con los templates:
    - Template no encontrado
    - Template inválido
    - Template path incorrecto
    """
    
    def __init__(
        self,
        template: str,
        reason: str,
        template_path: Optional[str] = None
    ):
        """
        Inicializar excepción.
        
        Args:
            template: Nombre o ID del template
            reason: Razón del error
            template_path: Ruta donde se buscó el template
        """
        super().__init__(
            f"Template error '{template}': {reason}",
            details={
                "template": template,
                "reason": reason,
                "template_path": template_path,
            }
        )
        self.template = template
        self.reason = reason


class NucleiParseError(NucleiError):
    """
    Error al parsear output de Nuclei.
    
    Ocurre cuando el output de Nuclei no tiene el formato esperado.
    """
    
    def __init__(
        self,
        message: str,
        raw_output: Optional[str] = None,
        line_number: Optional[int] = None
    ):
        """
        Inicializar excepción.
        
        Args:
            message: Mensaje de error
            raw_output: Output raw que falló al parsear
            line_number: Línea donde ocurrió el error
        """
        super().__init__(
            f"Failed to parse Nuclei output: {message}",
            details={
                "raw_output": raw_output[:500] if raw_output else None,
                "line_number": line_number,
            }
        )


class NucleiTargetError(NucleiError):
    """
    Error con el target especificado.
    
    Ocurre cuando:
    - Target vacío o inválido
    - URL malformada
    - Target no alcanzable
    """
    
    def __init__(self, target: str, reason: str):
        """
        Inicializar excepción.
        
        Args:
            target: Target que causó el error
            reason: Razón del error
        """
        super().__init__(
            f"Invalid target '{target}': {reason}",
            details={
                "target": target,
                "reason": reason,
            }
        )
        self.target = target
        self.reason = reason


class NucleiExecutionError(NucleiError):
    """
    Error durante la ejecución de Nuclei.
    
    Ocurre cuando Nuclei falla al ejecutarse:
    - Exit code no cero
    - Error de memoria
    - Error de permisos
    """
    
    def __init__(
        self,
        message: str,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None
    ):
        """
        Inicializar excepción.
        
        Args:
            message: Mensaje de error
            exit_code: Código de salida del proceso
            stderr: Output de stderr
        """
        super().__init__(
            message,
            details={
                "exit_code": exit_code,
                "stderr": stderr[:1000] if stderr else None,
            }
        )
        self.exit_code = exit_code
        self.stderr = stderr


class NucleiRateLimitError(NucleiError):
    """
    Error por rate limiting.
    
    Ocurre cuando Nuclei detecta rate limiting en el target.
    """
    
    def __init__(self, target: str, retry_after: Optional[int] = None):
        """
        Inicializar excepción.
        
        Args:
            target: Target que aplicó rate limit
            retry_after: Segundos a esperar antes de reintentar
        """
        message = f"Rate limited by target: {target}"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        
        super().__init__(
            message,
            details={
                "target": target,
                "retry_after_seconds": retry_after,
            }
        )
        self.target = target
        self.retry_after = retry_after
