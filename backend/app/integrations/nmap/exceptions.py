# =============================================================================
# NESTSECURE - Nmap Exceptions
# =============================================================================
"""
Excepciones específicas para operaciones Nmap.

Jerarquía:
- NmapError (base)
  - NmapNotFoundError (binario no encontrado)
  - NmapTimeoutError (timeout durante escaneo)
  - NmapPermissionError (permisos insuficientes)
  - NmapParseError (error parseando XML)
  - NmapTargetError (target inválido)
"""

from typing import Optional, Dict, Any


class NmapError(Exception):
    """
    Error base de Nmap.
    
    Attributes:
        message: Mensaje de error descriptivo
        details: Diccionario con detalles adicionales
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización."""
        return {
            "error": self.__class__.__name__,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            **self.details
        }
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class NmapNotFoundError(NmapError):
    """
    Nmap no está instalado o no se encuentra en el path especificado.
    
    Este error ocurre cuando:
    - Nmap no está instalado en el sistema
    - El path configurado es incorrecto
    - El binario no tiene permisos de ejecución
    """
    
    def __init__(self, path: str = "nmap"):
        super().__init__(
            f"Nmap binary not found at: {path}",
            {"path": path}
        )
        self.path = path


class NmapTimeoutError(NmapError):
    """
    Timeout durante un escaneo Nmap.
    
    Este error ocurre cuando:
    - El escaneo excede el tiempo límite configurado
    - La red es muy grande para el timeout
    - El host no responde en tiempo razonable
    """
    
    def __init__(self, target: str, timeout: int):
        super().__init__(
            f"Scan timeout for {target} after {timeout}s",
            {"target": target, "timeout_seconds": timeout}
        )
        self.target = target
        self.timeout = timeout


class NmapPermissionError(NmapError):
    """
    Permisos insuficientes para ejecutar el tipo de escaneo.
    
    Este error ocurre cuando:
    - Se intenta hacer -sS (SYN scan) sin root
    - Se intenta hacer -O (OS detection) sin root
    - Permisos de raw socket no disponibles
    """
    
    def __init__(self, message: str = "Root privileges required", scan_type: str = ""):
        details = {}
        if scan_type:
            details["scan_type"] = scan_type
        
        super().__init__(message, details)
        self.scan_type = scan_type


class NmapParseError(NmapError):
    """
    Error parseando output XML de Nmap.
    
    Este error ocurre cuando:
    - El XML está malformado
    - Elementos esperados no existen
    - Formato inesperado de salida
    """
    
    def __init__(self, message: str, xml_snippet: str = "", raw_output: str = ""):
        details = {}
        if xml_snippet:
            # Solo primeros 500 chars para no llenar logs
            details["xml_snippet"] = xml_snippet[:500]
        if raw_output:
            details["raw_output"] = raw_output[:500]
        
        super().__init__(f"XML Parse Error: {message}", details)
        self.raw_output = raw_output


class NmapTargetError(NmapError):
    """
    Target de escaneo inválido o no alcanzable.
    
    Este error ocurre cuando:
    - IP o hostname inválido
    - CIDR malformado
    - Target no alcanzable después de múltiples intentos
    """
    
    def __init__(self, target: str, reason: str = "Invalid target"):
        super().__init__(
            f"{reason}: {target}",
            {"target": target, "reason": reason}
        )
        self.target = target
        self.reason = reason


class NmapExecutionError(NmapError):
    """
    Error durante la ejecución del comando Nmap.
    
    Este error ocurre cuando:
    - Nmap retorna código de error no esperado
    - Error de memoria o recursos
    - Error interno de Nmap
    """
    
    def __init__(
        self, 
        message: str = "",
        exit_code: int = 1,
        stderr: str = "", 
        command: str = "",
        return_code: int = None
    ):
        # Compatibilidad con ambos nombres de parámetro
        actual_code = return_code if return_code is not None else exit_code
        
        if not message:
            message = f"Nmap execution failed with code {actual_code}"
            if stderr:
                message += f": {stderr[:200]}"
        
        super().__init__(
            message,
            {
                "return_code": actual_code,
                "exit_code": actual_code,
                "stderr": stderr[:500] if stderr else "",
                "command": command[:200] if command else "",
            }
        )
        self.return_code = actual_code
        self.exit_code = actual_code
        self.stderr = stderr
        self.command = command
