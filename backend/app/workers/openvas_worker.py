# =============================================================================
# NESTSECURE - OpenVAS Worker
# =============================================================================
"""
Celery Worker para OpenVAS/GVM.

Maneja tareas asíncronas de escaneo de vulnerabilidades usando
Greenbone Vulnerability Manager.

Tasks disponibles:
- openvas_full_scan: Escaneo completo (target + task + monitoreo + resultados)
- openvas_create_target: Solo crear target
- openvas_start_scan: Solo iniciar escaneo (requiere task existente)
- openvas_check_status: Verificar estado de escaneo
- openvas_get_results: Obtener resultados de escaneo completado
- openvas_stop_scan: Detener escaneo en curso
- openvas_cleanup: Limpiar recursos de GVM
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from celery import shared_task, current_task
from celery.exceptions import SoftTimeLimitExceeded

from app.workers.celery_app import celery_app
from app.utils.logger import get_logger
from app.core.metrics import (
    SCAN_DURATION_SECONDS,
    ACTIVE_SCANS,
    VULNERABILITIES_FOUND_TOTAL,
)
from app.integrations.gvm import (
    GVMClient,
    GVMError,
    GVMConnectionError,
    GVMScanError,
    GVMTimeoutError,
    GVMReport,
)

logger = get_logger(__name__)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

QUEUE_NAME = "openvas"
DEFAULT_SCAN_TIMEOUT = 7200  # 2 horas
DEFAULT_POLL_INTERVAL = 30  # segundos
MAX_RETRIES = 3


# =============================================================================
# HELPERS
# =============================================================================

def run_async(coro):
    """Ejecutar coroutine en event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def update_task_state(task, state: str, progress: int = 0, status: str = "", **meta) -> None:
    """Actualizar estado de la tarea Celery."""
    if task:
        task.update_state(state=state, meta={"progress": progress, "status": status, **meta})


# =============================================================================
# TASK: FULL SCAN
# =============================================================================

@celery_app.task(
    bind=True,
    name="openvas.full_scan",
    queue=QUEUE_NAME,
    max_retries=MAX_RETRIES,
    default_retry_delay=60,
    soft_time_limit=DEFAULT_SCAN_TIMEOUT,
    time_limit=DEFAULT_SCAN_TIMEOUT + 300,
    track_started=True,
)
def openvas_full_scan(
    self,
    scan_id: str,
    targets: str,
    scan_name: Optional[str] = None,
    config_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
) -> Dict[str, Any]:
    """
    Ejecutar escaneo completo de OpenVAS.
    
    Orquesta: crear target -> crear task -> ejecutar -> monitorear -> resultados
    """
    return run_async(
        _async_full_scan(self, scan_id, targets, scan_name, config_id, organization_id, poll_interval)
    )


async def _async_full_scan(
    task, scan_id: str, targets: str, scan_name: Optional[str],
    config_id: Optional[str], organization_id: Optional[str], poll_interval: int,
) -> Dict[str, Any]:
    """Implementación async del full scan."""
    start_time = datetime.utcnow()
    target_id = task_id = report_id = None
    
    if not scan_name:
        scan_name = f"NestSecure-{scan_id[:8]}"
    
    ACTIVE_SCANS.labels(scanner="openvas").inc()
    logger.info(f"Starting OpenVAS scan {scan_id}", extra={"scan_id": scan_id, "targets": targets})
    
    try:
        async with GVMClient() as gvm:
            health = await gvm.health_check()
            if health.get("status") != "healthy":
                raise GVMConnectionError("GVM is not healthy")
            
            update_task_state(task, "PROGRESS", 5, "connecting")
            
            # 1. Crear target
            target_id = await gvm.create_target(
                name=f"{scan_name}-target", hosts=targets, comment=f"NestSecure scan ID: {scan_id}"
            )
            update_task_state(task, "PROGRESS", 10, "target_created", target_id=target_id)
            
            # 2. Crear task
            task_id = await gvm.create_task(
                name=scan_name, target_id=target_id, config_id=config_id, comment=f"NestSecure scan ID: {scan_id}"
            )
            update_task_state(task, "PROGRESS", 15, "task_created", target_id=target_id, task_id=task_id)
            
            # 3. Iniciar escaneo
            report_id = await gvm.start_task(task_id)
            update_task_state(task, "PROGRESS", 20, "scan_started", target_id=target_id, task_id=task_id, report_id=report_id)
            
            # 4. Monitorear progreso
            while True:
                try:
                    task_status = await gvm.get_task_status(task_id)
                    overall_progress = 20 + int(task_status.progress * 0.7)
                    update_task_state(
                        task, "PROGRESS", overall_progress, task_status.status,
                        gvm_progress=task_status.progress, target_id=target_id, task_id=task_id, report_id=report_id
                    )
                    
                    if task_status.is_done:
                        break
                    
                    if task_status.status in ["Stopped", "Stop Requested"]:
                        raise GVMScanError(f"Scan was stopped: {task_status.status}", task_id=task_id)
                    
                    await asyncio.sleep(poll_interval)
                except SoftTimeLimitExceeded:
                    await gvm.stop_task(task_id)
                    raise GVMTimeoutError("Scan exceeded time limit", operation="full_scan", timeout_seconds=DEFAULT_SCAN_TIMEOUT)
            
            # 5. Obtener resultados
            update_task_state(task, "PROGRESS", 92, "getting_results")
            report = await gvm.get_report(report_id)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            SCAN_DURATION_SECONDS.labels(scanner="openvas", status="success").observe(duration)
            VULNERABILITIES_FOUND_TOTAL.labels(scanner="openvas", severity="critical").inc(report.critical_count)
            VULNERABILITIES_FOUND_TOTAL.labels(scanner="openvas", severity="high").inc(report.high_count)
            VULNERABILITIES_FOUND_TOTAL.labels(scanner="openvas", severity="medium").inc(report.medium_count)
            VULNERABILITIES_FOUND_TOTAL.labels(scanner="openvas", severity="low").inc(report.low_count)
            
            update_task_state(task, "PROGRESS", 100, "completed")
            
            return {
                "scan_id": scan_id, "status": "completed", "target_id": target_id, "task_id": task_id,
                "report_id": report_id, "hosts_scanned": report.host_count, "vulnerabilities_found": report.vuln_count,
                "critical": report.critical_count, "high": report.high_count, "medium": report.medium_count,
                "low": report.low_count, "duration_seconds": duration, "all_cves": report.all_cves[:100],
            }
    
    except GVMTimeoutError as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        SCAN_DURATION_SECONDS.labels(scanner="openvas", status="timeout").observe(duration)
        return {"scan_id": scan_id, "status": "timeout", "target_id": target_id, "task_id": task_id, "report_id": report_id, "duration_seconds": duration, "error": str(e)}
    
    except GVMError as e:
        logger.error(f"GVM error in scan {scan_id}: {e}", extra=e.to_dict())
        duration = (datetime.utcnow() - start_time).total_seconds()
        SCAN_DURATION_SECONDS.labels(scanner="openvas", status="error").observe(duration)
        return {"scan_id": scan_id, "status": "failed", "target_id": target_id, "task_id": task_id, "report_id": report_id, "duration_seconds": duration, "error": str(e)}
    
    except Exception as e:
        logger.error(f"Unexpected error in scan {scan_id}: {e}")
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {"scan_id": scan_id, "status": "failed", "target_id": target_id, "task_id": task_id, "report_id": report_id, "duration_seconds": duration, "error": f"Unexpected: {e}"}
    
    finally:
        ACTIVE_SCANS.labels(scanner="openvas").dec()


# =============================================================================
# TASK: CREATE TARGET
# =============================================================================

@celery_app.task(name="openvas.create_target", queue=QUEUE_NAME, max_retries=MAX_RETRIES, default_retry_delay=30)
def openvas_create_target(hosts: str, name: Optional[str] = None, port_list_id: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
    """Crear un target en GVM."""
    return run_async(_async_create_target(hosts, name, port_list_id, comment))


async def _async_create_target(hosts: str, name: Optional[str], port_list_id: Optional[str], comment: Optional[str]) -> Dict[str, Any]:
    try:
        async with GVMClient() as gvm:
            if not name:
                name = f"NestSecure-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            target_id = await gvm.create_target(name=name, hosts=hosts, port_list_id=port_list_id, comment=comment)
            return {"status": "success", "target_id": target_id, "name": name, "hosts": hosts}
    except GVMError as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# TASK: CHECK STATUS
# =============================================================================

@celery_app.task(name="openvas.check_status", queue=QUEUE_NAME)
def openvas_check_status(task_id: str) -> Dict[str, Any]:
    """Verificar estado de un escaneo."""
    return run_async(_async_check_status(task_id))


async def _async_check_status(task_id: str) -> Dict[str, Any]:
    try:
        async with GVMClient() as gvm:
            task_status = await gvm.get_task_status(task_id)
            return {
                "task_id": task_id, "status": task_status.status, "progress": task_status.progress,
                "is_running": task_status.is_running, "is_done": task_status.is_done, "last_report_id": task_status.last_report_id,
            }
    except GVMError as e:
        return {"task_id": task_id, "status": "error", "error": str(e)}


# =============================================================================
# TASK: GET RESULTS
# =============================================================================

@celery_app.task(name="openvas.get_results", queue=QUEUE_NAME, soft_time_limit=300)
def openvas_get_results(report_id: str, include_log_level: bool = False) -> Dict[str, Any]:
    """Obtener resultados de un escaneo."""
    return run_async(_async_get_results(report_id, include_log_level))


async def _async_get_results(report_id: str, include_log_level: bool) -> Dict[str, Any]:
    try:
        async with GVMClient() as gvm:
            report = await gvm.get_report(report_id, include_log_level)
            vulnerabilities = []
            for host in report.hosts:
                for vuln in host.vulnerabilities:
                    vulnerabilities.append({
                        "id": vuln.id, "name": vuln.name, "host": vuln.host, "port": vuln.port,
                        "severity": vuln.severity, "severity_class": vuln.severity_class.value,
                        "cve_ids": vuln.cve_ids, "description": vuln.description[:500] if vuln.description else None,
                        "solution": vuln.solution[:500] if vuln.solution else None, "family": vuln.family, "qod": vuln.qod,
                    })
            return {"report_id": report_id, "status": "success", "summary": report.get_summary(), "vulnerabilities": vulnerabilities[:1000], "total_vulnerabilities": report.vuln_count}
    except GVMError as e:
        return {"report_id": report_id, "status": "error", "error": str(e)}


# =============================================================================
# TASK: STOP SCAN
# =============================================================================

@celery_app.task(name="openvas.stop_scan", queue=QUEUE_NAME)
def openvas_stop_scan(task_id: str) -> Dict[str, Any]:
    """Detener un escaneo en curso."""
    return run_async(_async_stop_scan(task_id))


async def _async_stop_scan(task_id: str) -> Dict[str, Any]:
    try:
        async with GVMClient() as gvm:
            success = await gvm.stop_task(task_id)
            return {"task_id": task_id, "status": "stopped" if success else "error"}
    except GVMError as e:
        return {"task_id": task_id, "status": "error", "error": str(e)}


# =============================================================================
# TASK: CLEANUP
# =============================================================================

@celery_app.task(name="openvas.cleanup", queue=QUEUE_NAME)
def openvas_cleanup(target_id: Optional[str] = None, task_id: Optional[str] = None) -> Dict[str, Any]:
    """Limpiar recursos en GVM."""
    return run_async(_async_cleanup(target_id, task_id))


async def _async_cleanup(target_id: Optional[str], task_id: Optional[str]) -> Dict[str, Any]:
    results = {"status": "success", "deleted": [], "errors": []}
    try:
        async with GVMClient() as gvm:
            if task_id:
                try:
                    if await gvm.delete_task(task_id):
                        results["deleted"].append(f"task:{task_id}")
                    else:
                        results["errors"].append(f"Failed to delete task:{task_id}")
                except GVMError as e:
                    results["errors"].append(f"task:{task_id}: {e}")
            
            if target_id:
                try:
                    if await gvm.delete_target(target_id):
                        results["deleted"].append(f"target:{target_id}")
                    else:
                        results["errors"].append(f"Failed to delete target:{target_id}")
                except GVMError as e:
                    results["errors"].append(f"target:{target_id}: {e}")
            
            if results["errors"]:
                results["status"] = "partial"
            return results
    except GVMError as e:
        results["status"] = "error"
        results["errors"].append(str(e))
        return results


# =============================================================================
# TASK: HEALTH CHECK
# =============================================================================

@celery_app.task(name="openvas.health_check", queue=QUEUE_NAME)
def openvas_health_check() -> Dict[str, Any]:
    """Verificar estado de GVM."""
    return run_async(_async_health_check())


async def _async_health_check() -> Dict[str, Any]:
    try:
        async with GVMClient() as gvm:
            return await gvm.health_check()
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


__all__ = [
    "openvas_full_scan",
    "openvas_create_target",
    "openvas_check_status",
    "openvas_get_results",
    "openvas_stop_scan",
    "openvas_cleanup",
    "openvas_health_check",
]
