# =============================================================================
# NESTSECURE - Tests de Retry Logic
# =============================================================================
"""
Tests para el módulo de retry logic.

Prueba:
- Decorador retry para funciones síncronas
- Decorador async_retry para funciones asíncronas
- Backoff exponencial
- Callback on_retry
- RetryExhaustedError
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock

from app.utils.retry import (
    retry,
    async_retry,
    with_retry,
    with_async_retry,
    RetryExhaustedError,
)


# =============================================================================
# TESTS DE RETRY SÍNCRONO
# =============================================================================

class TestRetryDecorator:
    """Tests para el decorador retry."""
    
    def test_successful_on_first_attempt(self):
        """Función exitosa no hace retry."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        def success():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success()
        
        assert result == "success"
        assert call_count == 1
    
    def test_eventually_succeeds(self):
        """Retry hasta que tenga éxito."""
        call_count = 0
        
        @retry(max_attempts=5, delay=0.05)
        def succeeds_on_third():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = succeeds_on_third()
        
        assert result == "success"
        assert call_count == 3
    
    def test_exhausted_raises_error(self):
        """Retry agotado lanza RetryExhaustedError."""
        @retry(max_attempts=3, delay=0.05)
        def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            always_fails()
        
        assert exc_info.value.attempts == 3
        assert "always_fails" in exc_info.value.operation
    
    def test_only_catches_specified_exceptions(self):
        """Solo captura excepciones especificadas."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.05, exceptions=(ValueError,))
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not caught")
        
        with pytest.raises(TypeError):
            raises_type_error()
        
        # Solo 1 intento porque TypeError no está en exceptions
        assert call_count == 1
    
    def test_preserves_function_metadata(self):
        """Preserva nombre y docstring de función."""
        @retry()
        def documented_func():
            """This is the docstring."""
            pass
        
        assert documented_func.__name__ == "documented_func"
        assert "docstring" in documented_func.__doc__
    
    def test_callback_on_retry(self):
        """Callback se ejecuta en cada retry."""
        call_count = 0
        callback_calls = []
        
        def my_callback(attempt, error):
            callback_calls.append((attempt, str(error)))
        
        @retry(max_attempts=3, delay=0.05, on_retry=my_callback)
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Fail {call_count}")
            return "ok"
        
        result = fails_twice()
        
        assert result == "ok"
        assert len(callback_calls) == 2  # 2 retries antes del éxito
        assert callback_calls[0][0] == 1  # Primer retry
        assert callback_calls[1][0] == 2  # Segundo retry
    
    def test_no_reraise_returns_none(self):
        """Con reraise=False retorna None en lugar de excepción."""
        @retry(max_attempts=2, delay=0.05, reraise=False)
        def always_fails():
            raise ValueError("fail")
        
        result = always_fails()
        
        assert result is None


# =============================================================================
# TESTS DE BACKOFF EXPONENCIAL
# =============================================================================

class TestBackoffExponential:
    """Tests del backoff exponencial."""
    
    def test_delay_increases_exponentially(self):
        """Delay aumenta exponencialmente."""
        delays = []
        
        def record_delay(attempt, error):
            delays.append(time.time())
        
        @retry(max_attempts=4, delay=0.1, backoff=2.0, on_retry=record_delay)
        def fails_thrice():
            if len(delays) < 3:
                raise ValueError("fail")
            return "ok"
        
        start = time.time()
        fails_thrice()
        
        # Verificar que los delays aumentan
        # delay_1 ~= 0.1s, delay_2 ~= 0.2s, delay_3 ~= 0.4s
        if len(delays) >= 2:
            interval1 = delays[1] - delays[0]
            interval2 = delays[2] - delays[1] if len(delays) > 2 else 0
            # El segundo intervalo debe ser mayor (con tolerancia)
            assert interval2 >= interval1 * 1.5  # backoff ~2x
    
    def test_max_delay_respected(self):
        """max_delay limita el delay máximo."""
        call_count = 0
        start_times = []
        
        @retry(max_attempts=5, delay=0.1, backoff=10.0, max_delay=0.2)
        def fails_multiple():
            nonlocal call_count
            start_times.append(time.time())
            call_count += 1
            if call_count < 4:
                raise ValueError("fail")
            return "ok"
        
        fails_multiple()
        
        # Verificar que ningún intervalo excede max_delay + tolerancia
        for i in range(1, len(start_times)):
            interval = start_times[i] - start_times[i-1]
            assert interval <= 0.3  # max_delay=0.2 + tolerancia


# =============================================================================
# TESTS DE RETRY ASÍNCRONO
# =============================================================================

class TestAsyncRetryDecorator:
    """Tests para el decorador async_retry."""
    
    @pytest.mark.asyncio
    async def test_async_successful_on_first(self):
        """Función async exitosa no hace retry."""
        call_count = 0
        
        @async_retry(max_attempts=3, delay=0.05)
        async def async_success():
            nonlocal call_count
            call_count += 1
            return "async_success"
        
        result = await async_success()
        
        assert result == "async_success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_eventually_succeeds(self):
        """Async retry hasta que tenga éxito."""
        call_count = 0
        
        @async_retry(max_attempts=5, delay=0.05)
        async def async_succeeds_on_third():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if call_count < 3:
                raise ValueError("Not yet")
            return "async_success"
        
        result = await async_succeeds_on_third()
        
        assert result == "async_success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_exhausted_raises_error(self):
        """Async retry agotado lanza RetryExhaustedError."""
        @async_retry(max_attempts=3, delay=0.05)
        async def async_always_fails():
            await asyncio.sleep(0.01)
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            await async_always_fails()
        
        assert exc_info.value.attempts == 3
    
    @pytest.mark.asyncio
    async def test_async_callback_on_retry(self):
        """Callback async se ejecuta en cada retry."""
        call_count = 0
        callback_calls = []
        
        async def async_callback(attempt, error):
            callback_calls.append(attempt)
        
        @async_retry(max_attempts=3, delay=0.05, on_retry=async_callback)
        async def async_fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Fail {call_count}")
            return "ok"
        
        result = await async_fails_twice()
        
        assert result == "ok"
        assert len(callback_calls) == 2


# =============================================================================
# TESTS DE WITH_RETRY (SIN DECORADOR)
# =============================================================================

class TestWithRetry:
    """Tests para with_retry function."""
    
    def test_with_retry_success(self):
        """with_retry funciona con función exitosa."""
        def my_func(x, y):
            return x + y
        
        result = with_retry(my_func, 1, 2, max_attempts=3)
        
        assert result == 3
    
    def test_with_retry_eventual_success(self):
        """with_retry maneja éxito eventual."""
        call_count = 0
        
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "success"
        
        result = with_retry(
            fails_then_succeeds,
            max_attempts=3,
            delay=0.05
        )
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_with_async_retry(self):
        """with_async_retry funciona correctamente."""
        async def async_func(x):
            return x * 2
        
        result = await with_async_retry(
            async_func, 5,
            max_attempts=3
        )
        
        assert result == 10


# =============================================================================
# TESTS DE RETRY EXHAUSTED ERROR
# =============================================================================

class TestRetryExhaustedError:
    """Tests para RetryExhaustedError."""
    
    def test_error_attributes(self):
        """Error tiene atributos correctos."""
        error = RetryExhaustedError(
            operation="my_operation",
            attempts=3,
            last_error=ValueError("last error")
        )
        
        assert error.operation == "my_operation"
        assert error.attempts == 3
        assert isinstance(error.last_error, ValueError)
    
    def test_error_message(self):
        """Mensaje de error es descriptivo."""
        error = RetryExhaustedError(
            operation="fetch_data",
            attempts=5,
            last_error=ConnectionError("timeout")
        )
        
        assert "fetch_data" in str(error)
        assert "5" in str(error)
        assert "timeout" in str(error)
    
    def test_error_to_dict(self):
        """Error se convierte a dict."""
        error = RetryExhaustedError(
            operation="sync_data",
            attempts=3,
            last_error=TimeoutError("connection timeout"),
            details={"extra": "info"}
        )
        
        data = error.to_dict()
        
        assert data["operation"] == "sync_data"
        assert data["attempts"] == 3
        assert data["extra"] == "info"
        assert "timeout" in data["last_error"].lower()


# =============================================================================
# TESTS DE CONFIGURACIÓN
# =============================================================================

class TestRetryConfiguration:
    """Tests de configuración del retry."""
    
    def test_retry_config_stored(self):
        """Configuración se almacena en la función."""
        @retry(max_attempts=5, delay=2.0, backoff=3.0)
        def configured_func():
            pass
        
        config = configured_func._retry_config
        
        assert config["max_attempts"] == 5
        assert config["delay"] == 2.0
        assert config["backoff"] == 3.0
    
    def test_multiple_exception_types(self):
        """Múltiples tipos de excepción se capturan."""
        call_count = 0
        
        @retry(max_attempts=5, delay=0.05, exceptions=(ValueError, TypeError))
        def raises_different():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first")
            elif call_count == 2:
                raise TypeError("second")
            return "ok"
        
        result = raises_different()
        
        assert result == "ok"
        assert call_count == 3  # 2 fallos + 1 éxito
