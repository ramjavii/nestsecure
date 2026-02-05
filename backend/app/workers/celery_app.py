# =============================================================================
# NESTSECURE - Configuración de Celery
# =============================================================================
"""
Configuración central de Celery para tareas asíncronas.

Incluye:
- Configuración del broker (Redis)
- Configuración del backend de resultados
- Autodiscovery de tareas
- Configuración de serialización y timeouts
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()


# =============================================================================
# Crear aplicación Celery
# =============================================================================
celery_app = Celery(
    "nestsecure",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=[
        "app.workers.nmap_worker",
        "app.workers.openvas_worker",
        "app.workers.nuclei_worker",
        "app.workers.zap_worker",
        "app.workers.cve_worker",
        "app.workers.report_worker",
        "app.workers.cleanup_worker",
    ],
)


# =============================================================================
# Configuración de Celery
# =============================================================================
celery_app.conf.update(
    # -------------------------------------------------------------------------
    # Serialización
    # -------------------------------------------------------------------------
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # -------------------------------------------------------------------------
    # Timezone
    # -------------------------------------------------------------------------
    timezone="UTC",
    enable_utc=True,
    
    # -------------------------------------------------------------------------
    # Tareas
    # -------------------------------------------------------------------------
    task_track_started=True,
    task_time_limit=3600,  # 1 hora máximo por tarea
    task_soft_time_limit=3300,  # Soft limit 55 minutos (para cleanup)
    task_acks_late=True,  # ACK después de completar (más robusto)
    task_reject_on_worker_lost=True,
    
    # -------------------------------------------------------------------------
    # Workers
    # -------------------------------------------------------------------------
    worker_prefetch_multiplier=1,  # Una tarea a la vez por worker
    worker_max_tasks_per_child=50,  # Reiniciar worker después de 50 tareas
    worker_concurrency=3,  # 3 workers por defecto
    
    # -------------------------------------------------------------------------
    # Resultados
    # -------------------------------------------------------------------------
    result_expires=86400,  # Resultados expiran en 24 horas
    result_extended=True,  # Información extendida de resultados
    
    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    task_default_rate_limit="10/m",  # Máximo 10 tareas por minuto por defecto
    
    # -------------------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------------------
    task_default_retry_delay=60,  # Retry después de 1 minuto
    task_max_retries=3,  # Máximo 3 reintentos
    
    # -------------------------------------------------------------------------
    # Routes (opcional - para diferentes colas)
    # -------------------------------------------------------------------------
    task_routes={
        "app.workers.nmap_worker.*": {"queue": "default"},
        "app.workers.openvas_worker.*": {"queue": "default"},
        "app.workers.nuclei_worker.*": {"queue": "default"},
        "app.workers.zap_worker.*": {"queue": "default"},
        "app.workers.cve_worker.*": {"queue": "default"},
        "app.workers.report_worker.*": {"queue": "default"},
        "app.workers.cleanup_worker.*": {"queue": "default"},
    },
    
    # -------------------------------------------------------------------------
    # Beat Schedule (tareas periódicas)
    # -------------------------------------------------------------------------
    beat_schedule={
        # Limpieza diaria de assets inactivos
        "cleanup-stale-assets": {
            "task": "app.workers.cleanup_worker.cleanup_stale_assets",
            "schedule": 86400,  # Cada 24 horas
        },
        # Actualización de CVE cache
        "update-cve-cache": {
            "task": "app.workers.cve_worker.update_cve_cache",
            "schedule": 43200,  # Cada 12 horas
        },
    },
)


# =============================================================================
# Task Base Class (opcional)
# =============================================================================
class BaseTask(celery_app.Task):
    """
    Clase base para tareas con logging y manejo de errores común.
    """
    
    abstract = True
    
    def on_success(self, retval, task_id, args, kwargs):
        """Callback cuando la tarea termina exitosamente."""
        pass
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Callback cuando la tarea falla."""
        # TODO: Enviar alerta, loggear a Sentry, etc.
        pass
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Callback cuando la tarea se reintenta."""
        pass


# =============================================================================
# Helpers
# =============================================================================
def get_task_status(task_id: str) -> dict:
    """
    Obtiene el estado de una tarea por su ID.
    
    Args:
        task_id: ID de la tarea
    
    Returns:
        dict con estado, resultado, etc.
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() and result.successful() else None,
        "error": str(result.result) if result.ready() and not result.successful() else None,
    }


def cancel_task(task_id: str) -> bool:
    """
    Cancela una tarea en ejecución.
    
    Args:
        task_id: ID de la tarea
    
    Returns:
        True si se envió la señal de cancelación
    """
    celery_app.control.revoke(task_id, terminate=True)
    return True
