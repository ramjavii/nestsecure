# =============================================================================
# NESTSECURE - Retry Logic
# =============================================================================
"""
Retry logic con backoff exponencial.

Proporciona decoradores para reintentar operaciones fallidas
con estrategias configurables de backoff.

Uso:
    # Decorador síncrono
    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    def fetch_data():
        return requests.get(url)
    
    # Decorador asíncrono
    @async_retry(max_attempts=3, delay=1.0)
    async def fetch_data_async():
        async with aiohttp.get(url) as resp:
            return await resp.json()
    
    # Con excepciones específicas
    @retry(exceptions=(ConnectionError, TimeoutError))
    def connect():
        pass
"""

import time
import asyncio
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any, Union

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPCIONES
# =============================================================================

class RetryExhaustedError(Exception):
    """Se agotaron los reintentos."""
    
    def __init__(
        self,
        operation: str,
        attempts: int,
        last_error: Optional[Exception] = None,
        details: Optional[dict] = None
    ):
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error
        self.details = details or {}
        
        message = f"Retry exhausted for '{operation}' after {attempts} attempts"
        if last_error:
            message += f": {str(last_error)}"
        
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "error": "retry_exhausted",
            "operation": self.operation,
            "attempts": self.attempts,
            "last_error": str(self.last_error) if self.last_error else None,
            "message": str(self),
            **self.details
        }


# =============================================================================
# DECORADOR SÍNCRONO
# =============================================================================

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    reraise: bool = True
) -> Callable:
    """
    Decorador para reintentar funciones síncronas.
    
    Args:
        max_attempts: Número máximo de intentos (default: 3)
        delay: Delay inicial en segundos (default: 1.0)
        backoff: Factor de multiplicación del delay (default: 2.0)
        max_delay: Delay máximo en segundos (default: 60.0)
        exceptions: Tupla de excepciones a capturar
        on_retry: Callback a ejecutar antes de cada retry (attempt, exception)
        reraise: Si True, lanza RetryExhaustedError; si False, retorna None
    
    Returns:
        Decorador configurado
    
    Example:
        @retry(max_attempts=3, delay=2.0, exceptions=(ConnectionError,))
        def fetch_data():
            return requests.get(url).json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 1
            current_delay = delay
            last_exception: Optional[Exception] = None
            
            while attempt <= max_attempts:
                try:
                    result = func(*args, **kwargs)
                    
                    # Log si hubo retries
                    if attempt > 1:
                        logger.info(
                            f"Operation '{func.__name__}' succeeded after {attempt} attempts",
                            extra={
                                "operation": func.__name__,
                                "attempts": attempt,
                                "total_delay": sum(
                                    min(delay * (backoff ** i), max_delay) 
                                    for i in range(attempt - 1)
                                )
                            }
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Max retries ({max_attempts}) reached for '{func.__name__}'",
                            extra={
                                "operation": func.__name__,
                                "attempts": attempt,
                                "error": str(e),
                                "error_type": type(e).__name__
                            },
                            exc_info=True
                        )
                        
                        if reraise:
                            raise RetryExhaustedError(
                                operation=func.__name__,
                                attempts=max_attempts,
                                last_error=e
                            ) from e
                        return None
                    
                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for '{func.__name__}'",
                        extra={
                            "operation": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": current_delay,
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                    
                    # Callback opcional
                    if on_retry:
                        try:
                            on_retry(attempt, e)
                        except Exception as callback_error:
                            logger.warning(
                                f"on_retry callback failed: {callback_error}",
                                extra={"operation": func.__name__}
                            )
                    
                    time.sleep(current_delay)
                    current_delay = min(current_delay * backoff, max_delay)
                    attempt += 1
            
            # No debería llegar aquí, pero por seguridad
            if last_exception:
                raise last_exception
            return None
        
        # Agregar metadata al wrapper
        wrapper._retry_config = {
            "max_attempts": max_attempts,
            "delay": delay,
            "backoff": backoff,
            "max_delay": max_delay,
            "exceptions": exceptions
        }
        
        return wrapper
    return decorator


# =============================================================================
# DECORADOR ASÍNCRONO
# =============================================================================

def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], Any]] = None,
    reraise: bool = True
) -> Callable:
    """
    Decorador para reintentar funciones asíncronas.
    
    Similar a retry() pero para funciones async/await.
    
    Args:
        max_attempts: Número máximo de intentos
        delay: Delay inicial en segundos
        backoff: Factor de multiplicación del delay
        max_delay: Delay máximo en segundos
        exceptions: Tupla de excepciones a capturar
        on_retry: Callback a ejecutar antes de cada retry (puede ser async)
        reraise: Si True, lanza RetryExhaustedError; si False, retorna None
    
    Example:
        @async_retry(max_attempts=3, delay=1.0)
        async def fetch_async():
            async with aiohttp.get(url) as resp:
                return await resp.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            attempt = 1
            current_delay = delay
            last_exception: Optional[Exception] = None
            
            while attempt <= max_attempts:
                try:
                    result = await func(*args, **kwargs)
                    
                    if attempt > 1:
                        logger.info(
                            f"Async operation '{func.__name__}' succeeded after {attempt} attempts",
                            extra={
                                "operation": func.__name__,
                                "attempts": attempt
                            }
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Max async retries ({max_attempts}) reached for '{func.__name__}'",
                            extra={
                                "operation": func.__name__,
                                "attempts": attempt,
                                "error": str(e),
                                "error_type": type(e).__name__
                            },
                            exc_info=True
                        )
                        
                        if reraise:
                            raise RetryExhaustedError(
                                operation=func.__name__,
                                attempts=max_attempts,
                                last_error=e
                            ) from e
                        return None
                    
                    logger.warning(
                        f"Async retry {attempt}/{max_attempts} for '{func.__name__}'",
                        extra={
                            "operation": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": current_delay,
                            "error": str(e)
                        }
                    )
                    
                    # Callback opcional (soporta async)
                    if on_retry:
                        try:
                            if asyncio.iscoroutinefunction(on_retry):
                                await on_retry(attempt, e)
                            else:
                                on_retry(attempt, e)
                        except Exception as callback_error:
                            logger.warning(
                                f"on_retry callback failed: {callback_error}",
                                extra={"operation": func.__name__}
                            )
                    
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * backoff, max_delay)
                    attempt += 1
            
            if last_exception:
                raise last_exception
            return None
        
        wrapper._retry_config = {
            "max_attempts": max_attempts,
            "delay": delay,
            "backoff": backoff,
            "max_delay": max_delay,
            "exceptions": exceptions
        }
        
        return wrapper
    return decorator


# =============================================================================
# UTILIDADES
# =============================================================================

def with_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> Any:
    """
    Ejecutar función con retry sin decorador.
    
    Útil cuando no se puede decorar la función (ej: métodos de librerías externas).
    
    Args:
        func: Función a ejecutar
        *args: Argumentos posicionales
        max_attempts: Número máximo de intentos
        delay: Delay inicial
        backoff: Factor de backoff
        exceptions: Excepciones a capturar
        **kwargs: Argumentos con nombre
    
    Example:
        result = with_retry(
            requests.get,
            "https://api.example.com",
            max_attempts=3,
            timeout=30
        )
    """
    @retry(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        exceptions=exceptions
    )
    def wrapped():
        return func(*args, **kwargs)
    
    return wrapped()


async def with_async_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> Any:
    """
    Ejecutar función async con retry sin decorador.
    
    Versión async de with_retry().
    """
    @async_retry(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        exceptions=exceptions
    )
    async def wrapped():
        return await func(*args, **kwargs)
    
    return await wrapped()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "retry",
    "async_retry",
    "with_retry",
    "with_async_retry",
    "RetryExhaustedError",
]
