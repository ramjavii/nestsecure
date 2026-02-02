# =============================================================================
# NESTSECURE - Sistema de Logging Estructurado
# =============================================================================
"""
Logging estructurado para NestSecure.

Características:
- JSON logging para producción
- Text logging para desarrollo
- Contexto automático (request_id, user_id, org_id)
- Integración con Celery tasks
- Filtrado de información sensible
"""

import json
import logging
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

# Context variables para información de request
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
org_id_ctx: ContextVar[str] = ContextVar("org_id", default="")
task_id_ctx: ContextVar[str] = ContextVar("task_id", default="")


# =============================================================================
# Filtro de Información Sensible
# =============================================================================
SENSITIVE_FIELDS = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credential",
    "private_key",
    "secret_key",
}


def filter_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Filtra campos sensibles de los logs."""
    if not isinstance(data, dict):
        return data
    
    filtered = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(field in key_lower for field in SENSITIVE_FIELDS):
            filtered[key] = "***REDACTED***"
        elif isinstance(value, dict):
            filtered[key] = filter_sensitive_data(value)
        elif isinstance(value, list):
            filtered[key] = [
                filter_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            filtered[key] = value
    return filtered


# =============================================================================
# JSON Formatter para Producción
# =============================================================================
class JSONFormatter(logging.Formatter):
    """
    Formateador JSON para logs estructurados.
    Ideal para producción y análisis con herramientas como ELK/Splunk.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Agregar contexto de request si existe
        if request_id := request_id_ctx.get():
            log_data["request_id"] = request_id
        if user_id := user_id_ctx.get():
            log_data["user_id"] = user_id
        if org_id := org_id_ctx.get():
            log_data["org_id"] = org_id
        if task_id := task_id_ctx.get():
            log_data["task_id"] = task_id
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }
        
        # Agregar datos extra si existen
        if hasattr(record, "extra_data"):
            log_data["data"] = filter_sensitive_data(record.extra_data)
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


# =============================================================================
# Text Formatter para Desarrollo
# =============================================================================
class ColoredFormatter(logging.Formatter):
    """
    Formateador con colores para desarrollo local.
    Más legible para debugging interactivo.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Construir contexto
        context_parts = []
        if request_id := request_id_ctx.get():
            context_parts.append(f"req={request_id[:8]}")
        if user_id := user_id_ctx.get():
            context_parts.append(f"user={user_id[:8]}")
        if task_id := task_id_ctx.get():
            context_parts.append(f"task={task_id[:8]}")
        
        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        formatted = (
            f"{color}{timestamp} | {record.levelname:8}{self.RESET} | "
            f"{record.name}:{record.funcName}:{record.lineno}{context_str} - "
            f"{record.getMessage()}"
        )
        
        if record.exc_info:
            formatted += f"\n{''.join(traceback.format_exception(*record.exc_info))}"
        
        return formatted


# =============================================================================
# Logger Personalizado
# =============================================================================
class NestSecureLogger(logging.Logger):
    """Logger personalizado con métodos adicionales para contexto."""
    
    def with_context(self, **kwargs) -> "LoggerAdapter":
        """Retorna un adapter con contexto adicional."""
        return LoggerAdapter(self, kwargs)
    
    def _log_with_data(
        self,
        level: int,
        msg: str,
        args: tuple,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log con datos estructurados adicionales."""
        if data:
            kwargs["extra"] = kwargs.get("extra", {})
            kwargs["extra"]["extra_data"] = data
        super()._log(level, msg, args, **kwargs)
    
    def info_data(self, msg: str, data: Dict[str, Any], *args, **kwargs):
        """Log INFO con datos estructurados."""
        self._log_with_data(logging.INFO, msg, args, data, **kwargs)
    
    def warning_data(self, msg: str, data: Dict[str, Any], *args, **kwargs):
        """Log WARNING con datos estructurados."""
        self._log_with_data(logging.WARNING, msg, args, data, **kwargs)
    
    def error_data(self, msg: str, data: Dict[str, Any], *args, **kwargs):
        """Log ERROR con datos estructurados."""
        self._log_with_data(logging.ERROR, msg, args, data, **kwargs)


class LoggerAdapter(logging.LoggerAdapter):
    """Adapter para agregar contexto adicional a los logs."""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


# =============================================================================
# Configuración Global del Logging
# =============================================================================
def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    service_name: str = "nestsecure"
) -> logging.Logger:
    """
    Configura el sistema de logging global.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Formato de salida ("json" o "text")
        service_name: Nombre del servicio para identificación
    
    Returns:
        Logger raíz configurado
    """
    # Registrar clase de logger personalizada
    logging.setLoggerClass(NestSecureLogger)
    
    # Obtener logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Crear handler para stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Elegir formatter según el formato
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter()
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Configurar loggers de terceros
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logging.getLogger(logger_name).handlers = []
    
    # Reducir verbosidad de algunos loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logging.getLogger(service_name)


def get_logger(name: str) -> NestSecureLogger:
    """
    Obtiene un logger con el nombre especificado.
    
    Args:
        name: Nombre del logger (típicamente __name__)
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


# =============================================================================
# Context Managers para Request/Task Context
# =============================================================================
def set_request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None
):
    """Establece el contexto de request para los logs."""
    if request_id:
        request_id_ctx.set(request_id)
    if user_id:
        user_id_ctx.set(user_id)
    if org_id:
        org_id_ctx.set(org_id)


def set_task_context(task_id: str):
    """Establece el contexto de task de Celery."""
    task_id_ctx.set(task_id)


def clear_context():
    """Limpia todo el contexto."""
    request_id_ctx.set("")
    user_id_ctx.set("")
    org_id_ctx.set("")
    task_id_ctx.set("")


# =============================================================================
# Decoradores para Logging
# =============================================================================
def log_execution(logger: Optional[logging.Logger] = None):
    """
    Decorador para loggear la ejecución de funciones.
    
    Registra:
    - Inicio de ejecución con argumentos
    - Fin de ejecución con resultado
    - Errores con traceback
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__qualname__
            filtered_kwargs = filter_sensitive_data(kwargs)
            
            logger.debug(f"→ Iniciando {func_name}", extra={
                "extra_data": {"args_count": len(args), "kwargs": filtered_kwargs}
            })
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"✓ Completado {func_name}")
                return result
            except Exception as e:
                logger.error(
                    f"✗ Error en {func_name}: {str(e)}",
                    exc_info=True,
                    extra={"extra_data": {"kwargs": filtered_kwargs}}
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__qualname__
            filtered_kwargs = filter_sensitive_data(kwargs)
            
            logger.debug(f"→ Iniciando {func_name}", extra={
                "extra_data": {"args_count": len(args), "kwargs": filtered_kwargs}
            })
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"✓ Completado {func_name}")
                return result
            except Exception as e:
                logger.error(
                    f"✗ Error en {func_name}: {str(e)}",
                    exc_info=True,
                    extra={"extra_data": {"kwargs": filtered_kwargs}}
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# =============================================================================
# Exportar componentes principales
# =============================================================================
__all__ = [
    "get_logger",
    "setup_logging",
    "set_request_context",
    "set_task_context",
    "clear_context",
    "log_execution",
    "filter_sensitive_data",
    "JSONFormatter",
    "ColoredFormatter",
    "NestSecureLogger",
    "request_id_ctx",
    "user_id_ctx",
    "org_id_ctx",
    "task_id_ctx",
]
