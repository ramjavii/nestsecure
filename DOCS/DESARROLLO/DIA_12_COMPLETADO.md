# Día 12 - Error Handling & Resilience ✅

**Fecha de Completación:** 2026-02-04  
**Estado:** COMPLETADO  
**Tests Totales:** 368 (308 previos + 60 nuevos)

---

## 🎯 Objetivos del Día 12

1. ✅ Implementar patrón Circuit Breaker para servicios externos
2. ✅ Crear decoradores de retry con backoff exponencial
3. ✅ Unificar excepciones de la aplicación
4. ✅ Agregar endpoint de health check para servicios
5. ✅ Tests completos para componentes de resiliencia

---

## 📁 Archivos Creados

### 1. `app/core/circuit_breaker.py` (~500 líneas)

**Patrón Circuit Breaker completo:**

```python
# Estados del Circuit Breaker
class CircuitState(Enum):
    CLOSED = "closed"      # Normal - permite llamadas
    OPEN = "open"          # Fallo detectado - rechaza llamadas
    HALF_OPEN = "half_open" # Probando recuperación

# Configuración personalizable
class CircuitBreakerConfig:
    failure_threshold: int = 5     # Fallos antes de abrir
    success_threshold: int = 2     # Éxitos para cerrar
    timeout: float = 30.0          # Segundos antes de half-open
    excluded_exceptions: tuple     # Excepciones a ignorar

# Clase principal
class CircuitBreaker:
    def call(self, func, *args, **kwargs)      # Ejecución sync
    def call_async(self, func, *args, **kwargs) # Ejecución async
    def protect(self, func)                     # Decorador
    def reset()                                 # Reset manual
    def get_metrics() -> CircuitBreakerMetrics  # Estadísticas
```

**Instancias Globales Pre-configuradas:**
- `gvm_circuit_breaker` - Para OpenVAS/GVM
- `nvd_circuit_breaker` - Para API NVD
- `nmap_circuit_breaker` - Para escaneos Nmap
- `nuclei_circuit_breaker` - Para Nuclei scanner
- `redis_circuit_breaker` - Para conexión Redis
- `db_circuit_breaker` - Para base de datos

**Funciones Auxiliares:**
- `get_all_circuit_breakers()` - Obtener todos los breakers
- `get_circuit_breaker(name)` - Obtener por nombre
- `get_all_metrics()` - Métricas de todos
- `reset_all()` - Reiniciar todos

---

### 2. `app/utils/retry.py` (~350 líneas)

**Decoradores de Retry con Backoff Exponencial:**

```python
# Decorador síncrono
@retry(max_attempts=3, delay=1.0, backoff=2.0)
def risky_operation():
    # Se reintentará hasta 3 veces con delays: 1s, 2s, 4s
    pass

# Decorador asíncrono
@async_retry(max_attempts=5, exceptions=(TimeoutError,))
async def async_risky_operation():
    # Solo reintenta TimeoutError
    pass

# Funciones wrapper
with_retry(func, *args, **kwargs)        # Ejecutar con retry
with_async_retry(func, *args, **kwargs)  # Ejecutar async con retry
```

**Características:**
- `max_attempts` - Número máximo de intentos
- `delay` - Delay inicial entre reintentos
- `backoff` - Multiplicador exponencial
- `max_delay` - Tope máximo de delay
- `exceptions` - Tupla de excepciones a reintentar
- `on_retry` - Callback en cada reintento
- Jitter automático para evitar thundering herd

**Excepción Especial:**
```python
class RetryExhaustedError(Exception):
    attempts: int
    last_exception: Exception
    total_time: float
    def to_dict() -> dict  # Para logging/API
```

---

### 3. `app/main.py` - Endpoint `/health/services`

**Nuevo endpoint de health check:**

```python
GET /health/services

Response:
{
    "status": "healthy" | "degraded" | "unhealthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "services": {
        "gvm": {
            "name": "gvm",
            "state": "closed",
            "is_available": true,
            "failure_count": 0,
            "success_count": 10,
            "metrics": {...},
            "config": {...}
        },
        "nvd": {...},
        "nmap": {...},
        "nuclei": {...},
        "redis": {...},
        "database": {...}
    },
    "summary": {
        "total_services": 6,
        "healthy": 6,
        "degraded": 0,
        "unhealthy": 0
    }
}
```

**Estados:**
- `healthy` - Todos los servicios funcionando
- `degraded` - Algunos servicios en half_open
- `unhealthy` - Algún servicio con circuito abierto

---

## 🧪 Tests Creados (60 nuevos)

### `app/tests/test_core/test_circuit_breaker.py` (28 tests)

| Clase | Tests | Descripción |
|-------|-------|-------------|
| TestCircuitBreakerInit | 3 | Inicialización y configuración |
| TestCircuitBreakerSuccess | 3 | Llamadas exitosas |
| TestCircuitBreakerFailure | 4 | Manejo de fallos |
| TestCircuitBreakerTransitions | 4 | Transiciones de estado |
| TestCircuitBreakerMetrics | 3 | Métricas y estadísticas |
| TestCircuitBreakerContextManager | 2 | Context manager |
| TestCircuitBreakerDecorator | 3 | Decorador @protect |
| TestGlobalCircuitBreakers | 3 | Instancias globales |
| TestCircuitBreakerOpenError | 2 | Excepción CircuitBreakerOpenError |
| TestCircuitBreakerAvailability | 1 | Método is_available() |

### `app/tests/test_utils/test_retry.py` (25 tests)

| Clase | Tests | Descripción |
|-------|-------|-------------|
| TestRetryDecorator | 6 | Decorador @retry básico |
| TestBackoffExponential | 4 | Backoff exponencial |
| TestAsyncRetryDecorator | 5 | Decorador @async_retry |
| TestWithRetry | 3 | Función with_retry() |
| TestRetryExhaustedError | 4 | Excepción y to_dict() |
| TestRetryConfiguration | 3 | Configuraciones edge case |

### `app/tests/test_api/test_health_services.py` (7 tests)

| Test | Descripción |
|------|-------------|
| test_health_services_returns_200 | Endpoint accesible |
| test_health_services_structure | Estructura response |
| test_health_services_includes_all_breakers | 6 servicios presentes |
| test_health_services_healthy_by_default | Estado inicial healthy |
| test_health_services_service_details | Detalles de servicio |
| test_health_services_after_failure | Estado tras fallos |
| test_health_services_degraded_when_open | Estado degraded |

---

## 📊 Resumen de Tests

```
==================== 368 passed, 1 warning in 64.16s ====================

Desglose:
- Tests Día 1-11: 308
- Tests Día 12:    60
  - Circuit Breaker: 28
  - Retry Logic:     25
  - Health Services:  7
```

---

## 🔧 Cómo Usar los Componentes

### Circuit Breaker

```python
from app.core.circuit_breaker import gvm_circuit_breaker, CircuitBreakerOpenError

# Método 1: call()
try:
    result = gvm_circuit_breaker.call(external_api_call, param1, param2)
except CircuitBreakerOpenError as e:
    # El servicio está temporalmente no disponible
    return cached_result_or_error()

# Método 2: Decorador
@gvm_circuit_breaker.protect
def protected_function():
    return call_gvm_api()

# Método 3: Context Manager
with gvm_circuit_breaker:
    result = call_gvm_api()
```

### Retry Logic

```python
from app.utils.retry import retry, async_retry, RetryExhaustedError

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def fetch_data():
    return requests.get("https://api.example.com/data")

@async_retry(max_attempts=5, exceptions=(aiohttp.ClientError,))
async def async_fetch():
    async with session.get(url) as response:
        return await response.json()

# Con callback
@retry(on_retry=lambda e, a, d: logger.warning(f"Attempt {a} failed: {e}"))
def monitored_operation():
    pass
```

### Combinando Ambos

```python
@gvm_circuit_breaker.protect
@retry(max_attempts=3, delay=0.5)
async def resilient_gvm_call():
    """Llamada protegida con circuit breaker Y reintentos"""
    return await gvm_client.scan(target)
```

---

## 🚀 Instrucciones de Testing Manual

### 1. Iniciar el Backend

```bash
cd /Users/fabianramos/Desktop/NESTSECURE/backend
source ../.venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### 2. Verificar Health Check de Servicios

```bash
# Ver estado de todos los circuit breakers
curl http://localhost:8000/health/services | python -m json.tool

# Respuesta esperada: todos los servicios "healthy"
```

### 3. Ejecutar Tests

```bash
# Todos los tests
cd backend
pytest app/tests/ tests/integration/ -v

# Solo tests del Día 12
pytest app/tests/test_core/test_circuit_breaker.py \
       app/tests/test_utils/test_retry.py \
       app/tests/test_api/test_health_services.py -v

# Con coverage
pytest --cov=app --cov-report=html
```

### 4. Explorar API Documentation

```
http://localhost:8000/docs
```

---

## 📈 Estado del Proyecto - Fin Fase 2

| Métrica | Valor |
|---------|-------|
| Tests Totales | 368 |
| Cobertura Estimada | >80% |
| Endpoints API | 25+ |
| Modelos SQLAlchemy | 8+ |
| Workers Celery | 4 |
| Integraciones | GVM, NVD, Nmap, Nuclei |

### Componentes Backend Completados:

- ✅ Autenticación JWT con refresh tokens
- ✅ CRUD completo de Scans, Reports, Assets
- ✅ Workers Celery para escaneos
- ✅ Integración OpenVAS/GVM
- ✅ Integración NVD API
- ✅ Scanner Nmap con perfiles
- ✅ Scanner Nuclei con templates
- ✅ Circuit Breaker para resiliencia
- ✅ Retry logic con backoff
- ✅ Health checks detallados
- ✅ Manejo global de excepciones

---

## ✅ Día 12 Completado - Listo para Frontend

El backend de NESTSECURE está ahora **production-ready** con:
- Resiliencia ante fallos de servicios externos
- Recuperación automática de errores transitorios
- Monitoreo en tiempo real del estado de servicios
- Tests comprehensivos de todos los componentes

**Próximo paso:** Iniciar desarrollo del Frontend (Fase 3)
