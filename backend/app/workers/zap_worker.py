# =============================================================================
# NESTSECURE - Worker de OWASP ZAP
# =============================================================================
"""
Worker de Celery para integración con OWASP ZAP.

Proporciona tareas asíncronas para:
- Escaneo completo (Spider + Ajax Spider + Active Scan)
- Escaneo rápido (Spider + Passive Scan)
- Escaneo de API (con importación OpenAPI)
- Escaneo de SPA (Spider + Ajax Spider + Active Scan)

Cada tarea:
1. Conecta con ZAP
2. Configura contexto de escaneo
3. Ejecuta las fases correspondientes
4. Recolecta alertas
5. Crea vulnerabilidades en la base de datos
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded

from app.workers.celery_app import celery_app
from app.utils.logger import get_logger
from app.config import get_settings
from app.integrations.zap import (
    ZapClient,
    ZapScanner,
    ZapScanMode,
    ZapAlertParser,
    ZAP_SCAN_POLICIES,
)
from app.integrations.zap.client import ZapClientError, ZapConnectionError


logger = get_logger(__name__)
settings = get_settings()


# =============================================================================
# UTILIDADES
# =============================================================================

def run_async(coro):
    """Ejecutar corutina en worker Celery."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def update_task_state(state: str, meta: Dict) -> None:
    """Actualizar estado de la tarea actual."""
    if current_task:
        current_task.update_state(state=state, meta=meta)


# =============================================================================
# TAREAS DE ESCANEO
# =============================================================================

@celery_app.task(
    bind=True,
    name="zap.scan",
    queue="scanning",
    soft_time_limit=7200,  # 2 horas
    time_limit=7500,
    autoretry_for=(ZapConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
    track_started=True,
)
def zap_scan(
    self,
    target_url: str,
    mode: str = "standard",
    organization_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    scan_id: Optional[str] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    create_vulnerabilities: bool = True,
) -> Dict:
    """
    Ejecutar escaneo ZAP completo.
    
    Args:
        target_url: URL objetivo a escanear
        mode: Modo de escaneo (quick, standard, full, api, spa, passive)
        organization_id: ID de la organización
        asset_id: ID del asset asociado
        scan_id: ID del scan de NESTSECURE
        include_patterns: Patrones a incluir en el contexto
        exclude_patterns: Patrones a excluir del contexto
        timeout: Timeout en segundos
        create_vulnerabilities: Si True, crear vulnerabilidades en BD
    
    Returns:
        Dict con resultados del escaneo
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Iniciando escaneo ZAP: {target_url} (modo: {mode})")
    
    update_task_state("STARTED", {
        "phase": "initializing",
        "target_url": target_url,
        "mode": mode,
    })
    
    try:
        scan_mode = ZapScanMode(mode)
    except ValueError:
        scan_mode = ZapScanMode.STANDARD
    
    async def _execute_scan():
        progress_data = {
            "phase": "connecting",
            "spider_progress": 0,
            "ajax_spider_progress": 0,
            "active_scan_progress": 0,
            "urls_found": 0,
            "alerts_found": 0,
        }
        
        def progress_callback(progress):
            """Callback para actualizar progreso."""
            progress_data.update({
                "phase": progress.phase,
                "spider_progress": progress.spider_progress,
                "ajax_spider_progress": progress.ajax_spider_progress,
                "active_scan_progress": progress.active_scan_progress,
                "passive_scan_pending": progress.passive_scan_pending,
                "urls_found": progress.urls_found,
                "alerts_found": progress.alerts_found,
                "overall_progress": progress.overall_progress,
                "elapsed_seconds": progress.elapsed_seconds,
            })
            update_task_state("PROGRESS", progress_data)
        
        async with ZapClient() as client:
            # Verificar disponibilidad
            if not await client.is_available():
                raise ZapConnectionError("ZAP no está disponible")
            
            version = await client.get_version()
            logger.info(f"[{task_id}] Conectado a ZAP v{version}")
            
            # Crear escáner con callback de progreso
            scanner = ZapScanner(client, progress_callback=progress_callback)
            
            # Ejecutar escaneo
            result = await scanner.scan(
                url=target_url,
                mode=scan_mode,
                timeout=timeout,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            )
            
            return result
    
    try:
        result = run_async(_execute_scan())
        
        # Parsear alertas
        parser = ZapAlertParser()
        parsed_alerts = parser.parse_alerts(result.alerts)
        severity_summary = parser.get_severity_summary(parsed_alerts)
        
        # Construir respuesta
        response = {
            "success": result.success,
            "target_url": result.target_url,
            "mode": result.mode.value,
            "started_at": result.start_time.isoformat(),
            "completed_at": result.end_time.isoformat(),
            "duration_seconds": result.duration_seconds,
            "urls_found": result.urls_found,
            "alerts_count": len(result.alerts),
            "alerts_summary": severity_summary,
            "alerts": [
                {
                    "id": a.alert_id,
                    "name": a.name,
                    "risk": a.risk_name.lower(),
                    "confidence": a.confidence_name.lower(),
                    "url": a.url,
                    "method": a.method,
                    "param": a.param,
                    "description": a.description[:500] if a.description else None,
                    "solution": a.solution[:500] if a.solution else None,
                    "cwe_id": a.cwe_id,
                    "owasp_top_10": a.owasp_top_10,
                }
                for a in parsed_alerts[:100]  # Limitar a 100 alertas en respuesta
            ],
            "errors": result.errors,
            "spider_scan_id": result.spider_scan_id,
            "active_scan_id": result.active_scan_id,
            "context_name": result.context_name,
        }
        
        # TODO: Crear vulnerabilidades en BD si create_vulnerabilities=True
        # Esto requiere acceso a la base de datos asíncrona
        
        logger.info(
            f"[{task_id}] Escaneo ZAP completado: "
            f"{result.urls_found} URLs, {len(result.alerts)} alertas"
        )
        
        return response
        
    except SoftTimeLimitExceeded:
        logger.error(f"[{task_id}] Timeout en escaneo ZAP")
        return {
            "success": False,
            "target_url": target_url,
            "mode": mode,
            "error": "Escaneo excedió el tiempo límite",
            "alerts": [],
        }
    except ZapConnectionError as e:
        logger.error(f"[{task_id}] Error de conexión ZAP: {e}")
        raise
    except Exception as e:
        logger.error(f"[{task_id}] Error en escaneo ZAP: {e}")
        return {
            "success": False,
            "target_url": target_url,
            "mode": mode,
            "error": str(e),
            "alerts": [],
        }


@celery_app.task(
    bind=True,
    name="zap.quick_scan",
    queue="scanning",
    soft_time_limit=600,  # 10 minutos
    time_limit=700,
    track_started=True,
)
def zap_quick_scan(
    self,
    target_url: str,
    organization_id: Optional[str] = None,
    asset_id: Optional[str] = None,
) -> Dict:
    """
    Escaneo rápido ZAP (Spider + Passive Scan).
    
    Ideal para verificación rápida de vulnerabilidades obvias.
    """
    return zap_scan(
        target_url=target_url,
        mode="quick",
        organization_id=organization_id,
        asset_id=asset_id,
        timeout=300,
    )


@celery_app.task(
    bind=True,
    name="zap.full_scan",
    queue="scanning",
    soft_time_limit=7200,  # 2 horas
    time_limit=7500,
    track_started=True,
)
def zap_full_scan(
    self,
    target_url: str,
    organization_id: Optional[str] = None,
    asset_id: Optional[str] = None,
) -> Dict:
    """
    Escaneo completo ZAP (Spider + Ajax Spider + Active Scan).
    
    Escaneo exhaustivo para aplicaciones web.
    """
    return zap_scan(
        target_url=target_url,
        mode="full",
        organization_id=organization_id,
        asset_id=asset_id,
    )


@celery_app.task(
    bind=True,
    name="zap.api_scan",
    queue="scanning",
    soft_time_limit=3600,  # 1 hora
    time_limit=3700,
    track_started=True,
)
def zap_api_scan(
    self,
    target_url: str,
    openapi_url: Optional[str] = None,
    organization_id: Optional[str] = None,
    asset_id: Optional[str] = None,
) -> Dict:
    """
    Escaneo de API REST/GraphQL.
    
    Opcionalmente importa especificación OpenAPI para mejor cobertura.
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Iniciando escaneo de API ZAP: {target_url}")
    
    async def _execute_api_scan():
        async with ZapClient() as client:
            if not await client.is_available():
                raise ZapConnectionError("ZAP no está disponible")
            
            # Importar OpenAPI si está disponible
            if openapi_url:
                try:
                    await client.import_openapi(url=openapi_url, target=target_url)
                    logger.info(f"[{task_id}] OpenAPI importado desde {openapi_url}")
                except Exception as e:
                    logger.warning(f"[{task_id}] No se pudo importar OpenAPI: {e}")
            
            scanner = ZapScanner(client)
            return await scanner.scan(target_url, mode=ZapScanMode.API)
    
    try:
        result = run_async(_execute_api_scan())
        
        parser = ZapAlertParser()
        parsed_alerts = parser.parse_alerts(result.alerts)
        
        return {
            "success": result.success,
            "target_url": result.target_url,
            "mode": "api",
            "openapi_url": openapi_url,
            "urls_found": result.urls_found,
            "alerts_count": len(result.alerts),
            "alerts_summary": parser.get_severity_summary(parsed_alerts),
            "alerts": [
                {
                    "name": a.name,
                    "risk": a.risk_name.lower(),
                    "url": a.url,
                    "cwe_id": a.cwe_id,
                }
                for a in parsed_alerts[:50]
            ],
            "errors": result.errors,
        }
    except Exception as e:
        logger.error(f"[{task_id}] Error en API scan: {e}")
        return {
            "success": False,
            "target_url": target_url,
            "mode": "api",
            "error": str(e),
        }


@celery_app.task(
    bind=True,
    name="zap.spa_scan",
    queue="scanning",
    soft_time_limit=5400,  # 1.5 horas
    time_limit=5500,
    track_started=True,
)
def zap_spa_scan(
    self,
    target_url: str,
    organization_id: Optional[str] = None,
    asset_id: Optional[str] = None,
) -> Dict:
    """
    Escaneo de Single Page Application.
    
    Usa Ajax Spider para descubrir contenido dinámico.
    """
    return zap_scan(
        target_url=target_url,
        mode="spa",
        organization_id=organization_id,
        asset_id=asset_id,
    )


# =============================================================================
# TAREAS DE CONSULTA
# =============================================================================

@celery_app.task(
    name="zap.get_version",
    queue="default",
)
def zap_get_version() -> Dict:
    """Obtener versión de ZAP."""
    async def _get_version():
        async with ZapClient() as client:
            try:
                version = await client.get_version()
                return {
                    "available": True,
                    "version": version,
                    "host": client.host,
                    "port": client.port,
                }
            except Exception as e:
                return {
                    "available": False,
                    "error": str(e),
                    "host": client.host,
                    "port": client.port,
                }
    
    return run_async(_get_version())


@celery_app.task(
    name="zap.get_alerts",
    queue="default",
)
def zap_get_alerts(
    base_url: Optional[str] = None,
    risk_id: Optional[int] = None,
    start: int = 0,
    count: int = 100,
) -> Dict:
    """Obtener alertas de ZAP."""
    async def _get_alerts():
        async with ZapClient() as client:
            alerts = await client.get_alerts(
                base_url=base_url,
                risk_id=str(risk_id) if risk_id is not None else None,
                start=start,
                count=count,
            )
            total = await client.get_alerts_count(base_url=base_url, risk_id=str(risk_id) if risk_id is not None else None)
            summary = await client.get_alerts_summary(base_url=base_url)
            
            return {
                "alerts": alerts,
                "total": total,
                "summary": summary,
            }
    
    return run_async(_get_alerts())


@celery_app.task(
    name="zap.clear_session",
    queue="default",
)
def zap_clear_session() -> Dict:
    """Limpiar sesión de ZAP (nueva sesión)."""
    async def _clear_session():
        async with ZapClient() as client:
            await client.new_session(overwrite=True)
            await client.delete_all_alerts()
            return {"success": True, "message": "Sesión limpiada"}
    
    return run_async(_clear_session())


@celery_app.task(
    name="zap.get_scan_policies",
    queue="default",
)
def zap_get_scan_policies() -> Dict:
    """Obtener políticas de escaneo disponibles."""
    return {
        "policies": [
            {
                "id": key,
                "name": value["name"],
                "description": value["description"],
                "spider": value.get("spider", True),
                "ajax_spider": value.get("ajax_spider", False),
                "active_scan": value.get("active_scan", True),
                "api_scan": value.get("api_scan", False),
                "timeout": value.get("timeout", 1800),
            }
            for key, value in ZAP_SCAN_POLICIES.items()
        ]
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "zap_scan",
    "zap_quick_scan",
    "zap_full_scan",
    "zap_api_scan",
    "zap_spa_scan",
    "zap_get_version",
    "zap_get_alerts",
    "zap_clear_session",
    "zap_get_scan_policies",
]

