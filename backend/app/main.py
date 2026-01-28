# =============================================================================
# NESTSECURE - Aplicación Principal FastAPI
# =============================================================================
# Punto de entrada de la API REST del sistema de escaneo de vulnerabilidades.
# Este módulo configura la aplicación FastAPI con todos sus middlewares,
# routers y event handlers.
# =============================================================================

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable

import redis.asyncio as redis
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings

# Configuración del logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Obtener configuración
settings = get_settings()


# =============================================================================
# Estado Global de la Aplicación
# =============================================================================
class AppState:
    """
    Clase para mantener el estado global de la aplicación.
    Incluye conexiones a servicios externos y métricas.
    """
    
    def __init__(self):
        self.startup_time: datetime = datetime.now(timezone.utc)
        self.redis_client: redis.Redis | None = None
        self.db_connected: bool = False
        self.redis_connected: bool = False
        self.version: str = settings.APP_VERSION
        self.environment: str = settings.ENVIRONMENT


app_state = AppState()


# =============================================================================
# Lifecycle Events (Startup/Shutdown)
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestiona el ciclo de vida de la aplicación.
    
    Startup:
    - Inicializa conexiones a bases de datos
    - Configura clientes de servicios externos
    - Carga caches
    
    Shutdown:
    - Cierra conexiones de forma ordenada
    - Libera recursos
    """
    # -------------------------------------------------------------------------
    # STARTUP
    # -------------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📍 Entorno: {settings.ENVIRONMENT}")
    logger.info("=" * 60)
    
    # Conectar a Redis
    try:
        app_state.redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        # Verificar conexión
        await app_state.redis_client.ping()
        app_state.redis_connected = True
        logger.info("✅ Conexión a Redis establecida")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo conectar a Redis: {e}")
        app_state.redis_connected = False
    
    # TODO: Día 2 - Conectar a PostgreSQL con SQLAlchemy async
    # TODO: Día 3 - Inicializar Celery workers
    
    logger.info(f"✅ {settings.APP_NAME} iniciado correctamente")
    logger.info(f"📡 API disponible en: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    logger.info(f"📚 Documentación: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}/docs")
    
    yield  # La aplicación está corriendo
    
    # -------------------------------------------------------------------------
    # SHUTDOWN
    # -------------------------------------------------------------------------
    logger.info("🛑 Apagando aplicación...")
    
    # Cerrar conexión Redis
    if app_state.redis_client:
        await app_state.redis_client.close()
        logger.info("✅ Conexión a Redis cerrada")
    
    # TODO: Cerrar pool de conexiones a PostgreSQL
    
    logger.info(f"👋 {settings.APP_NAME} apagado correctamente")


# =============================================================================
# Crear Aplicación FastAPI
# =============================================================================
def create_application() -> FastAPI:
    """
    Factory function para crear la aplicación FastAPI.
    
    Permite crear múltiples instancias (útil para testing)
    y centraliza toda la configuración.
    """
    application = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # -------------------------------------------------------------------------
    # Middlewares
    # -------------------------------------------------------------------------
    
    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Compresión Gzip
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Middleware para logging de requests
    @application.middleware("http")
    async def log_requests(request: Request, call_next: Callable) -> Response:
        """Registra todas las requests entrantes con timing."""
        start_time = time.perf_counter()
        
        # Procesar request
        response = await call_next(request)
        
        # Calcular tiempo de procesamiento
        process_time = (time.perf_counter() - start_time) * 1000
        
        # Log en formato estructurado
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.2f}ms"
        )
        
        # Añadir header con tiempo de procesamiento
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        
        return response
    
    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Manejador global de excepciones no capturadas."""
        logger.error(f"Error no manejado: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Error interno del servidor",
                "error_type": type(exc).__name__,
                # Solo mostrar detalles en desarrollo
                "message": str(exc) if settings.DEBUG else None,
            }
        )
    
    # -------------------------------------------------------------------------
    # Incluir Routers
    # -------------------------------------------------------------------------
    # TODO: Día 5+ - Añadir routers de API
    # from app.api.v1 import api_router
    # application.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    return application


# Crear instancia de la aplicación
app = create_application()


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check básico",
    description="Verifica que la API está respondiendo. No verifica servicios externos.",
    response_model=dict,
    responses={
        200: {
            "description": "API funcionando correctamente",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2026-01-28T12:00:00Z",
                        "version": "1.0.0"
                    }
                }
            }
        }
    }
)
async def health_check() -> dict:
    """
    Health check básico.
    
    Retorna el estado de la API sin verificar servicios externos.
    Útil para load balancers y probes de Kubernetes.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get(
    "/health/ready",
    tags=["Health"],
    summary="Readiness Check",
    description="Verifica que la API y todos los servicios dependientes están listos.",
    response_model=dict,
    responses={
        200: {
            "description": "Todos los servicios están listos",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ready",
                        "checks": {
                            "database": {"status": "up", "latency_ms": 5.2},
                            "redis": {"status": "up", "latency_ms": 1.1}
                        }
                    }
                }
            }
        },
        503: {
            "description": "Uno o más servicios no están disponibles"
        }
    }
)
async def readiness_check() -> JSONResponse:
    """
    Readiness check completo.
    
    Verifica la conexión a todos los servicios dependientes:
    - PostgreSQL
    - Redis
    
    Retorna 503 si algún servicio no está disponible.
    """
    checks = {}
    all_healthy = True
    
    # Check Redis
    redis_status = await _check_redis()
    checks["redis"] = redis_status
    if redis_status["status"] != "up":
        all_healthy = False
    
    # TODO: Día 2 - Check PostgreSQL
    checks["database"] = {
        "status": "not_configured",
        "message": "Pendiente de implementación"
    }
    
    # Construir respuesta
    response_data = {
        "status": "ready" if all_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "uptime_seconds": (datetime.now(timezone.utc) - app_state.startup_time).total_seconds()
    }
    
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(content=response_data, status_code=status_code)


@app.get(
    "/health/live",
    tags=["Health"],
    summary="Liveness Check",
    description="Verifica que el proceso está vivo. Para Kubernetes liveness probes.",
    response_model=dict,
)
async def liveness_check() -> dict:
    """
    Liveness check.
    
    Verifica que el proceso de la aplicación está vivo.
    No verifica servicios externos.
    Útil para Kubernetes liveness probes.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": __import__("os").getpid(),
    }


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get(
    "/",
    tags=["Root"],
    summary="Información de la API",
    description="Retorna información básica sobre la API y enlaces útiles.",
)
async def root() -> dict:
    """
    Endpoint raíz con información de la API.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_url": "/health",
        "api_prefix": settings.API_V1_PREFIX,
        "links": {
            "documentation": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "health_ready": "/health/ready",
            "health_live": "/health/live",
        }
    }


# =============================================================================
# Funciones auxiliares para health checks
# =============================================================================

async def _check_redis() -> dict:
    """
    Verifica la conexión a Redis.
    
    Returns:
        dict con status y latencia
    """
    if not app_state.redis_client:
        return {
            "status": "down",
            "message": "Cliente Redis no configurado"
        }
    
    try:
        start = time.perf_counter()
        await app_state.redis_client.ping()
        latency = (time.perf_counter() - start) * 1000
        
        return {
            "status": "up",
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        return {
            "status": "down",
            "error": str(e)
        }


# =============================================================================
# Para ejecutar directamente (desarrollo)
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
