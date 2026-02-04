# =============================================================================
# NESTSECURE - Circuit Breaker
# =============================================================================
"""
Circuit Breaker para servicios externos.

Implementa el patrón Circuit Breaker para proteger el sistema
contra fallos en cascada de servicios externos.

Estados:
- CLOSED: Funcionamiento normal
- OPEN: Servicio considerado caído, rechaza requests
- HALF_OPEN: Probando si el servicio se recuperó

Uso:
    from app.core.circuit_breaker import gvm_circuit_breaker
    
    # Opción 1: Context manager
    with gvm_circuit_breaker:
        result = gvm_client.connect()
    
    # Opción 2: Método call
    result = gvm_circuit_breaker.call(gvm_client.connect)
    
    # Opción 3: Decorador
    @gvm_circuit_breaker.protect
    def connect_gvm():
        return gvm_client.connect()
"""

import time
import logging
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Callable, Any, Optional, Dict, Type, Tuple
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS Y CONFIGURACIÓN
# =============================================================================

class CircuitState(Enum):
    """Estados del circuit breaker."""
    CLOSED = "closed"        # Funcionando normal
    OPEN = "open"            # Rechazando requests
    HALF_OPEN = "half_open"  # Probando recuperación


@dataclass
class CircuitBreakerConfig:
    """Configuración del circuit breaker."""
    failure_threshold: int = 5        # Fallos antes de abrir
    success_threshold: int = 2        # Éxitos para cerrar desde half-open
    timeout: int = 60                 # Segundos antes de intentar half-open
    expected_exceptions: Tuple[Type[Exception], ...] = (Exception,)


@dataclass
class CircuitBreakerMetrics:
    """Métricas del circuit breaker."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


# =============================================================================
# EXCEPCIONES
# =============================================================================

class CircuitBreakerError(Exception):
    """Error base de Circuit Breaker."""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """Circuit breaker está abierto."""
    
    def __init__(
        self,
        service_name: str,
        retry_after: int = 60,
        details: Optional[Dict[str, Any]] = None
    ):
        self.service_name = service_name
        self.retry_after = retry_after
        self.details = details or {}
        
        message = f"Service '{service_name}' is temporarily unavailable (circuit breaker open)"
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "error": "circuit_breaker_open",
            "service": self.service_name,
            "retry_after": self.retry_after,
            "message": str(self),
            **self.details
        }


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker para servicios externos.
    
    Protege el sistema contra fallos en cascada de servicios externos
    implementando el patrón Circuit Breaker.
    
    Example:
        >>> gvm_breaker = CircuitBreaker("GVM", failure_threshold=5)
        >>> 
        >>> # Opción 1: call method
        >>> result = gvm_breaker.call(connect_to_gvm)
        >>> 
        >>> # Opción 2: Decorador
        >>> @gvm_breaker.protect
        >>> def connect_to_gvm():
        >>>     pass
        >>> 
        >>> # Opción 3: Context manager
        >>> with gvm_breaker:
        >>>     connect_to_gvm()
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Inicializar circuit breaker.
        
        Args:
            name: Nombre identificador del servicio
            config: Configuración opcional
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = Lock()
        
        logger.info(
            f"Circuit breaker '{name}' initialized",
            extra={
                "circuit_breaker": name,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout
                }
            }
        )
    
    @property
    def state(self) -> CircuitState:
        """Estado actual del circuit breaker."""
        return self._state
    
    @state.setter
    def state(self, new_state: CircuitState):
        """Setter para estado con logging."""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self.metrics.state_changes += 1
            
            log_level = logging.WARNING if new_state == CircuitState.OPEN else logging.INFO
            logger.log(
                log_level,
                f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}",
                extra={
                    "circuit_breaker": self.name,
                    "old_state": old_state.value,
                    "new_state": new_state.value,
                    "failure_count": self.metrics.failure_count
                }
            )
    
    def __enter__(self):
        """Context manager entry."""
        self._check_state()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None and issubclass(exc_type, self.config.expected_exceptions):
            self._on_failure(exc_val)
            return False  # Re-raise the exception
        elif exc_type is None:
            self._on_success()
        return False
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecutar función con protección de circuit breaker.
        
        Args:
            func: Función a ejecutar
            *args, **kwargs: Argumentos de la función
            
        Returns:
            Resultado de la función
            
        Raises:
            CircuitBreakerOpenError: Si el circuit está abierto
        """
        self._check_state()
        self.metrics.total_calls += 1
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.config.expected_exceptions as e:
            self._on_failure(e)
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecutar función async con protección de circuit breaker.
        
        Args:
            func: Función async a ejecutar
            *args, **kwargs: Argumentos de la función
            
        Returns:
            Resultado de la función
            
        Raises:
            CircuitBreakerOpenError: Si el circuit está abierto
        """
        self._check_state()
        self.metrics.total_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.config.expected_exceptions as e:
            self._on_failure(e)
            raise
    
    def protect(self, func: Callable) -> Callable:
        """
        Decorador para proteger función con circuit breaker.
        
        Example:
            @circuit_breaker.protect
            def call_external_service():
                pass
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def _check_state(self):
        """Verificar estado y lanzar excepción si está abierto."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    raise CircuitBreakerOpenError(
                        service_name=self.name,
                        retry_after=self._get_retry_after()
                    )
    
    def _should_attempt_reset(self) -> bool:
        """Verificar si es momento de intentar resetear."""
        if not self.metrics.last_failure_time:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self.metrics.last_failure_time).total_seconds()
        return elapsed >= self.config.timeout
    
    def _get_retry_after(self) -> int:
        """Calcular segundos hasta siguiente intento."""
        if not self.metrics.last_failure_time:
            return 0
        
        elapsed = (datetime.now(timezone.utc) - self.metrics.last_failure_time).total_seconds()
        remaining = self.config.timeout - elapsed
        return max(0, int(remaining))
    
    def _on_success(self):
        """Manejar éxito de llamada."""
        with self._lock:
            self.metrics.success_count += 1
            self.metrics.total_successes += 1
            self.metrics.failure_count = 0
            self.metrics.last_success_time = datetime.now(timezone.utc)
            
            if self._state == CircuitState.HALF_OPEN:
                if self.metrics.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
    
    def _on_failure(self, exception: Exception = None):
        """Manejar fallo de llamada."""
        with self._lock:
            self.metrics.failure_count += 1
            self.metrics.total_failures += 1
            self.metrics.last_failure_time = datetime.now(timezone.utc)
            self.metrics.success_count = 0
            
            if exception:
                logger.warning(
                    f"Circuit breaker '{self.name}' recorded failure",
                    extra={
                        "circuit_breaker": self.name,
                        "failure_count": self.metrics.failure_count,
                        "threshold": self.config.failure_threshold,
                        "error": str(exception),
                        "error_type": type(exception).__name__
                    }
                )
            
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            
            elif self.metrics.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
    
    def _transition_to_open(self):
        """Transición a estado OPEN."""
        self.state = CircuitState.OPEN
        
        logger.warning(
            f"Circuit breaker '{self.name}' OPENED - service unavailable",
            extra={
                "circuit_breaker": self.name,
                "failures": self.metrics.failure_count,
                "timeout": self.config.timeout
            }
        )
    
    def _transition_to_half_open(self):
        """Transición a estado HALF_OPEN."""
        self.state = CircuitState.HALF_OPEN
        self.metrics.success_count = 0
        
        logger.info(
            f"Circuit breaker '{self.name}' HALF-OPENED - testing recovery",
            extra={"circuit_breaker": self.name}
        )
    
    def _transition_to_closed(self):
        """Transición a estado CLOSED."""
        self.state = CircuitState.CLOSED
        self.metrics.failure_count = 0
        
        logger.info(
            f"Circuit breaker '{self.name}' CLOSED - service recovered",
            extra={"circuit_breaker": self.name}
        )
    
    def reset(self):
        """Resetear circuit breaker manualmente."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.metrics.failure_count = 0
            self.metrics.success_count = 0
            
            logger.info(
                f"Circuit breaker '{self.name}' manually reset",
                extra={"circuit_breaker": self.name}
            )
    
    def get_metrics(self) -> dict:
        """Obtener métricas actuales."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count,
            "state_changes": self.metrics.state_changes,
            "total_calls": self.metrics.total_calls,
            "total_failures": self.metrics.total_failures,
            "total_successes": self.metrics.total_successes,
            "last_failure": self.metrics.last_failure_time.isoformat() 
                if self.metrics.last_failure_time else None,
            "last_success": self.metrics.last_success_time.isoformat()
                if self.metrics.last_success_time else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }
    
    def is_available(self) -> bool:
        """Verificar si el servicio está disponible (sin lanzar excepción)."""
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return True
        if self._state == CircuitState.OPEN:
            return self._should_attempt_reset()
        return False


# =============================================================================
# INSTANCIAS GLOBALES DE CIRCUIT BREAKERS
# =============================================================================

# GVM/OpenVAS - Servicio remoto crítico
gvm_circuit_breaker = CircuitBreaker(
    "GVM",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=120,  # 2 minutos
        expected_exceptions=(Exception,)
    )
)

# NVD API - Servicio externo con rate limits
nvd_circuit_breaker = CircuitBreaker(
    "NVD",
    config=CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=1,
        timeout=300,  # 5 minutos (NVD puede estar ocupado)
        expected_exceptions=(Exception,)
    )
)

# Nmap - Herramienta local, más tolerante a fallos
nmap_circuit_breaker = CircuitBreaker(
    "Nmap",
    config=CircuitBreakerConfig(
        failure_threshold=10,
        success_threshold=3,
        timeout=60,
        expected_exceptions=(Exception,)
    )
)

# Nuclei - Herramienta local, más tolerante a fallos
nuclei_circuit_breaker = CircuitBreaker(
    "Nuclei",
    config=CircuitBreakerConfig(
        failure_threshold=10,
        success_threshold=3,
        timeout=60,
        expected_exceptions=(Exception,)
    )
)

# Redis - Cache, puede fallar sin afectar funcionalidad core
redis_circuit_breaker = CircuitBreaker(
    "Redis",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=30,
        expected_exceptions=(Exception,)
    )
)

# Database - Crítico, bajo threshold
db_circuit_breaker = CircuitBreaker(
    "Database",
    config=CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=1,
        timeout=60,
        expected_exceptions=(Exception,)
    )
)


def get_all_circuit_breakers() -> list:
    """Obtener todos los circuit breakers para monitoreo."""
    return [
        gvm_circuit_breaker,
        nvd_circuit_breaker,
        nmap_circuit_breaker,
        nuclei_circuit_breaker,
        redis_circuit_breaker,
        db_circuit_breaker,
    ]


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Obtener circuit breaker por nombre."""
    for cb in get_all_circuit_breakers():
        if cb.name.lower() == name.lower():
            return cb
    return None


def get_all_metrics() -> dict:
    """Obtener métricas de todos los circuit breakers."""
    return {
        cb.name: cb.get_metrics()
        for cb in get_all_circuit_breakers()
    }


def reset_all():
    """Resetear todos los circuit breakers (útil para tests)."""
    for cb in get_all_circuit_breakers():
        cb.reset()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Classes
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "CircuitState",
    "CircuitBreakerError",
    "CircuitBreakerOpenError",
    # Global instances
    "gvm_circuit_breaker",
    "nvd_circuit_breaker",
    "nmap_circuit_breaker",
    "nuclei_circuit_breaker",
    "redis_circuit_breaker",
    "db_circuit_breaker",
    # Functions
    "get_all_circuit_breakers",
    "get_circuit_breaker",
    "get_all_metrics",
    "reset_all",
]
