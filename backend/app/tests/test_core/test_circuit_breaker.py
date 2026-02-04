# =============================================================================
# NESTSECURE - Tests de Circuit Breaker
# =============================================================================
"""
Tests para el módulo de Circuit Breaker.

Prueba:
- Estados del circuit breaker (closed, open, half-open)
- Transiciones de estado
- Métricas y contadores
- Context manager y decorador
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenError,
    get_all_circuit_breakers,
    get_circuit_breaker,
    get_all_metrics,
    reset_all,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def basic_breaker():
    """Circuit breaker básico para tests."""
    return CircuitBreaker(
        "test_service",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1,  # 1 segundo para tests rápidos
        )
    )


@pytest.fixture
def strict_breaker():
    """Circuit breaker estricto (se abre con 1 fallo)."""
    return CircuitBreaker(
        "strict_service",
        config=CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,
            timeout=1,
        )
    )


@pytest.fixture(autouse=True)
def reset_breakers():
    """Resetear circuit breakers globales antes de cada test."""
    reset_all()
    yield
    reset_all()


# =============================================================================
# TESTS DE ESTADO INICIAL
# =============================================================================

class TestCircuitBreakerInit:
    """Tests de inicialización del circuit breaker."""
    
    def test_starts_in_closed_state(self, basic_breaker):
        """Circuit breaker inicia en estado CLOSED."""
        assert basic_breaker.state == CircuitState.CLOSED
    
    def test_initial_metrics_are_zero(self, basic_breaker):
        """Métricas iniciales son cero."""
        metrics = basic_breaker.get_metrics()
        
        assert metrics["failure_count"] == 0
        assert metrics["success_count"] == 0
        assert metrics["total_calls"] == 0
        assert metrics["state_changes"] == 0
    
    def test_config_is_applied(self, basic_breaker):
        """Configuración se aplica correctamente."""
        metrics = basic_breaker.get_metrics()
        
        assert metrics["config"]["failure_threshold"] == 3
        assert metrics["config"]["success_threshold"] == 2
        assert metrics["config"]["timeout"] == 1
    
    def test_default_config(self):
        """Config por defecto funciona."""
        cb = CircuitBreaker("default_test")
        
        assert cb.config.failure_threshold == 5
        assert cb.config.success_threshold == 2
        assert cb.config.timeout == 60


# =============================================================================
# TESTS DE ÉXITO
# =============================================================================

class TestCircuitBreakerSuccess:
    """Tests para llamadas exitosas."""
    
    def test_successful_call_returns_result(self, basic_breaker):
        """Llamada exitosa retorna resultado."""
        result = basic_breaker.call(lambda: "success")
        
        assert result == "success"
    
    def test_successful_call_increments_counters(self, basic_breaker):
        """Llamada exitosa incrementa contadores."""
        basic_breaker.call(lambda: "ok")
        
        metrics = basic_breaker.get_metrics()
        assert metrics["total_calls"] == 1
        assert metrics["total_successes"] == 1
        assert metrics["total_failures"] == 0
    
    def test_success_resets_failure_count(self, basic_breaker):
        """Éxito resetea contador de fallos."""
        # Causar algunos fallos (sin abrir circuit)
        for _ in range(2):
            try:
                basic_breaker.call(lambda: 1/0)
            except:
                pass
        
        # Éxito debe resetear failures
        basic_breaker.call(lambda: "ok")
        
        assert basic_breaker.metrics.failure_count == 0
    
    def test_stays_closed_on_success(self, basic_breaker):
        """Permanece CLOSED con éxitos."""
        for _ in range(10):
            basic_breaker.call(lambda: "ok")
        
        assert basic_breaker.state == CircuitState.CLOSED


# =============================================================================
# TESTS DE FALLO
# =============================================================================

class TestCircuitBreakerFailure:
    """Tests para llamadas fallidas."""
    
    def test_failure_increments_counter(self, basic_breaker):
        """Fallo incrementa contador."""
        try:
            basic_breaker.call(lambda: 1/0)
        except:
            pass
        
        assert basic_breaker.metrics.failure_count == 1
    
    def test_failure_propagates_exception(self, basic_breaker):
        """Fallo propaga la excepción original."""
        with pytest.raises(ZeroDivisionError):
            basic_breaker.call(lambda: 1/0)
    
    def test_opens_after_threshold_failures(self, basic_breaker):
        """Se abre después de alcanzar threshold de fallos."""
        # 3 fallos para abrir (threshold=3)
        for _ in range(3):
            try:
                basic_breaker.call(lambda: 1/0)
            except ZeroDivisionError:
                pass
        
        assert basic_breaker.state == CircuitState.OPEN
    
    def test_rejects_calls_when_open(self, strict_breaker):
        """Rechaza llamadas cuando está OPEN."""
        # Abrir circuit con 1 fallo
        try:
            strict_breaker.call(lambda: 1/0)
        except:
            pass
        
        # Siguiente llamada debe ser rechazada
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            strict_breaker.call(lambda: "should_fail")
        
        assert exc_info.value.service_name == "strict_service"


# =============================================================================
# TESTS DE TRANSICIONES
# =============================================================================

class TestCircuitBreakerTransitions:
    """Tests de transiciones de estado."""
    
    def test_transition_to_half_open_after_timeout(self, strict_breaker):
        """Transiciona a HALF_OPEN después del timeout."""
        # Abrir circuit
        try:
            strict_breaker.call(lambda: 1/0)
        except:
            pass
        
        assert strict_breaker.state == CircuitState.OPEN
        
        # Esperar timeout
        time.sleep(1.1)
        
        # Siguiente llamada debe transicionar a HALF_OPEN
        strict_breaker.call(lambda: "ok")
        
        # Después de éxito en half-open con threshold=1, debe cerrarse
        assert strict_breaker.state == CircuitState.CLOSED
    
    def test_closes_after_successes_in_half_open(self, basic_breaker):
        """Cierra después de éxitos en HALF_OPEN."""
        # Abrir circuit
        for _ in range(3):
            try:
                basic_breaker.call(lambda: 1/0)
            except:
                pass
        
        # Esperar timeout
        time.sleep(1.1)
        
        # 2 éxitos para cerrar (threshold=2)
        basic_breaker.call(lambda: "ok")
        assert basic_breaker.state == CircuitState.HALF_OPEN
        
        basic_breaker.call(lambda: "ok")
        assert basic_breaker.state == CircuitState.CLOSED
    
    def test_reopens_on_failure_in_half_open(self, basic_breaker):
        """Se reabre con fallo en HALF_OPEN."""
        # Abrir circuit
        for _ in range(3):
            try:
                basic_breaker.call(lambda: 1/0)
            except:
                pass
        
        # Esperar timeout
        time.sleep(1.1)
        
        # Fallo en half-open debe reabrir
        try:
            basic_breaker.call(lambda: 1/0)
        except:
            pass
        
        assert basic_breaker.state == CircuitState.OPEN


# =============================================================================
# TESTS DE MÉTRICAS
# =============================================================================

class TestCircuitBreakerMetrics:
    """Tests de métricas del circuit breaker."""
    
    def test_metrics_structure(self, basic_breaker):
        """Estructura de métricas es correcta."""
        metrics = basic_breaker.get_metrics()
        
        assert "name" in metrics
        assert "state" in metrics
        assert "failure_count" in metrics
        assert "success_count" in metrics
        assert "total_calls" in metrics
        assert "total_failures" in metrics
        assert "total_successes" in metrics
        assert "state_changes" in metrics
        assert "last_failure" in metrics
        assert "last_success" in metrics
        assert "config" in metrics
    
    def test_state_changes_counted(self, strict_breaker):
        """Cambios de estado se cuentan."""
        # Abrir (1 cambio: closed -> open)
        try:
            strict_breaker.call(lambda: 1/0)
        except:
            pass
        
        time.sleep(1.1)
        
        # Recuperar (2 cambios: open -> half_open -> closed)
        strict_breaker.call(lambda: "ok")
        
        # Total: 2 cambios (closed->open, half_open->closed)
        # Nota: half_open es transitorio
        assert strict_breaker.metrics.state_changes >= 2
    
    def test_last_failure_timestamp(self, basic_breaker):
        """Timestamp de último fallo se registra."""
        try:
            basic_breaker.call(lambda: 1/0)
        except:
            pass
        
        assert basic_breaker.metrics.last_failure_time is not None
        assert isinstance(basic_breaker.metrics.last_failure_time, datetime)


# =============================================================================
# TESTS DE CONTEXT MANAGER
# =============================================================================

class TestCircuitBreakerContextManager:
    """Tests del context manager."""
    
    def test_context_manager_success(self, basic_breaker):
        """Context manager funciona con éxito."""
        with basic_breaker:
            result = "success"
        
        assert basic_breaker.metrics.total_successes == 1
    
    def test_context_manager_failure(self, basic_breaker):
        """Context manager maneja fallos."""
        with pytest.raises(ValueError):
            with basic_breaker:
                raise ValueError("test error")
        
        assert basic_breaker.metrics.failure_count == 1


# =============================================================================
# TESTS DE DECORADOR
# =============================================================================

class TestCircuitBreakerDecorator:
    """Tests del decorador protect."""
    
    def test_decorator_on_success(self, basic_breaker):
        """Decorador funciona con éxito."""
        @basic_breaker.protect
        def my_function():
            return "decorated_result"
        
        result = my_function()
        
        assert result == "decorated_result"
        assert basic_breaker.metrics.total_successes == 1
    
    def test_decorator_on_failure(self, basic_breaker):
        """Decorador maneja fallos."""
        @basic_breaker.protect
        def failing_function():
            raise RuntimeError("error")
        
        with pytest.raises(RuntimeError):
            failing_function()
        
        assert basic_breaker.metrics.failure_count == 1


# =============================================================================
# TESTS DE FUNCIONES GLOBALES
# =============================================================================

class TestGlobalCircuitBreakers:
    """Tests de funciones globales."""
    
    def test_get_all_circuit_breakers(self):
        """get_all_circuit_breakers retorna lista."""
        breakers = get_all_circuit_breakers()
        
        assert isinstance(breakers, list)
        assert len(breakers) > 0
        assert all(isinstance(b, CircuitBreaker) for b in breakers)
    
    def test_get_circuit_breaker_by_name(self):
        """get_circuit_breaker encuentra por nombre."""
        gvm = get_circuit_breaker("GVM")
        
        assert gvm is not None
        assert gvm.name == "GVM"
    
    def test_get_circuit_breaker_not_found(self):
        """get_circuit_breaker retorna None si no existe."""
        result = get_circuit_breaker("nonexistent")
        
        assert result is None
    
    def test_get_all_metrics(self):
        """get_all_metrics retorna dict de métricas."""
        metrics = get_all_metrics()
        
        assert isinstance(metrics, dict)
        assert "GVM" in metrics
        assert "NVD" in metrics
    
    def test_reset_all(self):
        """reset_all resetea todos los breakers."""
        gvm = get_circuit_breaker("GVM")
        
        # Causar un fallo
        try:
            gvm.call(lambda: 1/0)
        except:
            pass
        
        assert gvm.metrics.failure_count > 0
        
        # Resetear
        reset_all()
        
        assert gvm.metrics.failure_count == 0
        assert gvm.state == CircuitState.CLOSED


# =============================================================================
# TESTS DE ERROR
# =============================================================================

class TestCircuitBreakerOpenError:
    """Tests de CircuitBreakerOpenError."""
    
    def test_error_attributes(self):
        """Error tiene atributos correctos."""
        error = CircuitBreakerOpenError(
            service_name="test",
            retry_after=60
        )
        
        assert error.service_name == "test"
        assert error.retry_after == 60
        assert "test" in str(error)
    
    def test_error_to_dict(self):
        """Error se convierte a dict."""
        error = CircuitBreakerOpenError(
            service_name="test",
            retry_after=30,
            details={"extra": "info"}
        )
        
        data = error.to_dict()
        
        assert data["service"] == "test"
        assert data["retry_after"] == 30
        assert data["extra"] == "info"


# =============================================================================
# TESTS DE DISPONIBILIDAD
# =============================================================================

class TestCircuitBreakerAvailability:
    """Tests del método is_available."""
    
    def test_available_when_closed(self, basic_breaker):
        """Disponible cuando está CLOSED."""
        assert basic_breaker.is_available() is True
    
    def test_not_available_when_open(self, strict_breaker):
        """No disponible cuando está OPEN (sin timeout)."""
        try:
            strict_breaker.call(lambda: 1/0)
        except:
            pass
        
        # Sin esperar timeout
        assert strict_breaker.is_available() is False
    
    def test_available_after_timeout(self, strict_breaker):
        """Disponible después del timeout."""
        try:
            strict_breaker.call(lambda: 1/0)
        except:
            pass
        
        time.sleep(1.1)
        
        assert strict_breaker.is_available() is True
