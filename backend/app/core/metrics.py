# =============================================================================
# NESTSECURE - Métricas Prometheus
# =============================================================================
"""
Sistema de métricas para monitoreo con Prometheus.

Métricas incluidas:
- Requests HTTP (contador, histograma)
- Escaneos activos (gauge)
- Vulnerabilidades encontradas (contador)
- Conexiones de base de datos (gauge)
- Tareas Celery (contador)
"""

import time
from functools import wraps
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Intentar importar prometheus_client, si no está disponible usar mocks
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mocks para cuando prometheus_client no está instalado
    class MockMetric:
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
        def dec(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def info(self, *args, **kwargs):
            pass
    
    Counter = Gauge = Histogram = Info = lambda *args, **kwargs: MockMetric()
    CONTENT_TYPE_LATEST = "text/plain"
    def generate_latest(*args):
        return b"# Prometheus client not installed\n"


# =============================================================================
# Definición de Métricas
# =============================================================================

# Info de la aplicación
APP_INFO = Info(
    "nestsecure_app",
    "Información de la aplicación NestSecure"
)

# Requests HTTP
HTTP_REQUESTS_TOTAL = Counter(
    "nestsecure_http_requests_total",
    "Total de requests HTTP",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "nestsecure_http_request_duration_seconds",
    "Duración de requests HTTP en segundos",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "nestsecure_http_requests_in_progress",
    "Requests HTTP en progreso",
    ["method", "endpoint"]
)

# Escaneos
ACTIVE_SCANS = Gauge(
    "nestsecure_active_scans",
    "Número de escaneos activos",
    ["scan_type"]
)

SCANS_TOTAL = Counter(
    "nestsecure_scans_total",
    "Total de escaneos realizados",
    ["scan_type", "status"]
)

SCAN_DURATION_SECONDS = Histogram(
    "nestsecure_scan_duration_seconds",
    "Duración de escaneos en segundos",
    ["scan_type"],
    buckets=[60, 120, 300, 600, 1200, 1800, 3600, 7200]
)

# Vulnerabilidades
VULNERABILITIES_FOUND_TOTAL = Counter(
    "nestsecure_vulnerabilities_found_total",
    "Total de vulnerabilidades encontradas",
    ["severity"]
)

VULNERABILITIES_CURRENT = Gauge(
    "nestsecure_vulnerabilities_current",
    "Vulnerabilidades actuales por severidad",
    ["severity", "status"]
)

# Base de datos
DB_CONNECTIONS_ACTIVE = Gauge(
    "nestsecure_db_connections_active",
    "Conexiones activas a la base de datos"
)

DB_CONNECTIONS_IDLE = Gauge(
    "nestsecure_db_connections_idle",
    "Conexiones inactivas a la base de datos"
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "nestsecure_db_query_duration_seconds",
    "Duración de queries en segundos",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Celery tasks
CELERY_TASKS_TOTAL = Counter(
    "nestsecure_celery_tasks_total",
    "Total de tareas Celery ejecutadas",
    ["task_name", "status"]
)

CELERY_TASKS_ACTIVE = Gauge(
    "nestsecure_celery_tasks_active",
    "Tareas Celery activas",
    ["queue"]
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "nestsecure_celery_task_duration_seconds",
    "Duración de tareas Celery en segundos",
    ["task_name"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800]
)

# Cache (Redis)
CACHE_HITS_TOTAL = Counter(
    "nestsecure_cache_hits_total",
    "Total de cache hits"
)

CACHE_MISSES_TOTAL = Counter(
    "nestsecure_cache_misses_total",
    "Total de cache misses"
)

# Assets
ASSETS_TOTAL = Gauge(
    "nestsecure_assets_total",
    "Total de assets por tipo",
    ["asset_type", "criticality"]
)


# =============================================================================
# Middleware de Métricas
# =============================================================================
class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware para recolectar métricas de requests HTTP.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # No medir el endpoint de métricas
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        # Normalizar path para evitar alta cardinalidad
        endpoint = self._normalize_path(request.url.path)
        
        # Incrementar requests en progreso
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        
        # Medir tiempo
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Calcular duración
            duration = time.perf_counter() - start_time
            
            # Registrar métricas
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            HTTP_REQUESTS_IN_PROGRESS.labels(
                method=method,
                endpoint=endpoint
            ).dec()
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Normaliza paths para evitar alta cardinalidad.
        Reemplaza IDs por placeholders.
        """
        import re
        
        # Reemplazar UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE
        )
        
        # Reemplazar IDs numéricos
        path = re.sub(r"/\d+", "/{id}", path)
        
        return path


# =============================================================================
# Helpers para Métricas
# =============================================================================
def track_scan(scan_type: str):
    """
    Decorador para trackear escaneos.
    
    Usage:
        @track_scan("nmap")
        async def run_nmap_scan(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            ACTIVE_SCANS.labels(scan_type=scan_type).inc()
            start_time = time.perf_counter()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failed"
                raise
            finally:
                duration = time.perf_counter() - start_time
                ACTIVE_SCANS.labels(scan_type=scan_type).dec()
                SCANS_TOTAL.labels(scan_type=scan_type, status=status).inc()
                SCAN_DURATION_SECONDS.labels(scan_type=scan_type).observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            ACTIVE_SCANS.labels(scan_type=scan_type).inc()
            start_time = time.perf_counter()
            status = "success"
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failed"
                raise
            finally:
                duration = time.perf_counter() - start_time
                ACTIVE_SCANS.labels(scan_type=scan_type).dec()
                SCANS_TOTAL.labels(scan_type=scan_type, status=status).inc()
                SCAN_DURATION_SECONDS.labels(scan_type=scan_type).observe(duration)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def track_celery_task(task_name: str, queue: str = "default"):
    """
    Decorador para trackear tareas Celery.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            CELERY_TASKS_ACTIVE.labels(queue=queue).inc()
            start_time = time.perf_counter()
            status = "success"
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failed"
                raise
            finally:
                duration = time.perf_counter() - start_time
                CELERY_TASKS_ACTIVE.labels(queue=queue).dec()
                CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()
                CELERY_TASK_DURATION_SECONDS.labels(task_name=task_name).observe(duration)
        
        return wrapper
    return decorator


def record_vulnerability(severity: str, count: int = 1):
    """Registra vulnerabilidades encontradas."""
    VULNERABILITIES_FOUND_TOTAL.labels(severity=severity).inc(count)


def update_vulnerability_gauge(severity: str, status: str, count: int):
    """Actualiza el gauge de vulnerabilidades actuales."""
    VULNERABILITIES_CURRENT.labels(severity=severity, status=status).set(count)


def record_cache_hit():
    """Registra un cache hit."""
    CACHE_HITS_TOTAL.inc()


def record_cache_miss():
    """Registra un cache miss."""
    CACHE_MISSES_TOTAL.inc()


def update_assets_gauge(asset_type: str, criticality: str, count: int):
    """Actualiza el gauge de assets."""
    ASSETS_TOTAL.labels(asset_type=asset_type, criticality=criticality).set(count)


# =============================================================================
# Endpoint de Métricas
# =============================================================================
async def metrics_endpoint(request: Request) -> Response:
    """
    Endpoint que expone métricas para Prometheus.
    
    Returns:
        Response con métricas en formato Prometheus
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# =============================================================================
# Registro en FastAPI
# =============================================================================
def setup_metrics(app: FastAPI, app_version: str = "1.0.0") -> None:
    """
    Configura el sistema de métricas en la aplicación.
    
    Args:
        app: Instancia de FastAPI
        app_version: Versión de la aplicación
    """
    # Registrar info de la app
    if PROMETHEUS_AVAILABLE:
        APP_INFO.info({
            "version": app_version,
            "name": "nestsecure",
        })
    
    # Agregar middleware
    app.add_middleware(MetricsMiddleware)
    
    # Agregar endpoint de métricas
    app.add_api_route(
        "/metrics",
        metrics_endpoint,
        methods=["GET"],
        include_in_schema=False,  # Ocultar de Swagger
        tags=["monitoring"]
    )


# =============================================================================
# Exportar
# =============================================================================
__all__ = [
    # Setup
    "setup_metrics",
    "MetricsMiddleware",
    "metrics_endpoint",
    # Métricas
    "APP_INFO",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "HTTP_REQUESTS_IN_PROGRESS",
    "ACTIVE_SCANS",
    "SCANS_TOTAL",
    "SCAN_DURATION_SECONDS",
    "VULNERABILITIES_FOUND_TOTAL",
    "VULNERABILITIES_CURRENT",
    "DB_CONNECTIONS_ACTIVE",
    "DB_CONNECTIONS_IDLE",
    "DB_QUERY_DURATION_SECONDS",
    "CELERY_TASKS_TOTAL",
    "CELERY_TASKS_ACTIVE",
    "CELERY_TASK_DURATION_SECONDS",
    "CACHE_HITS_TOTAL",
    "CACHE_MISSES_TOTAL",
    "ASSETS_TOTAL",
    # Helpers
    "track_scan",
    "track_celery_task",
    "record_vulnerability",
    "update_vulnerability_gauge",
    "record_cache_hit",
    "record_cache_miss",
    "update_assets_gauge",
    # Constantes
    "PROMETHEUS_AVAILABLE",
]
