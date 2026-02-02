# =============================================================================
# NESTSECURE - API de Scans
# =============================================================================
"""
Endpoints para gestión de escaneos de seguridad.

Endpoints:
- POST /scans: Crear y ejecutar nuevo scan
- GET /scans: Listar scans de la organización
- GET /scans/{id}: Obtener detalle de scan
- GET /scans/{id}/status: Obtener estado del scan
- GET /scans/{id}/results: Obtener resultados
- POST /scans/{id}/stop: Detener scan en ejecución
- DELETE /scans/{id}: Eliminar scan
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.vulnerability import Vulnerability
from app.utils.logger import get_logger
from app.workers.openvas_worker import openvas_full_scan, openvas_stop_scan, openvas_check_status

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class ScanCreate(BaseModel):
    """Schema para crear un scan."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scan_type: ScanType = ScanType.VULNERABILITY
    targets: List[str] = Field(..., min_items=1)
    excluded_targets: Optional[List[str]] = None
    port_range: Optional[str] = None


class ScanResponse(BaseModel):
    """Schema de respuesta de scan."""
    id: str
    name: str
    description: Optional[str]
    scan_type: str
    targets: List[str]
    status: str
    progress: int
    current_phase: Optional[str]
    
    total_hosts_scanned: int
    total_hosts_up: int
    total_vulnerabilities: int
    vuln_critical: int
    vuln_high: int
    vuln_medium: int
    vuln_low: int
    
    celery_task_id: Optional[str]
    gvm_target_id: Optional[str]
    gvm_task_id: Optional[str]
    gvm_report_id: Optional[str]
    
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    error_message: Optional[str]
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanListResponse(BaseModel):
    """Respuesta paginada de scans."""
    items: List[ScanResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ScanStatusResponse(BaseModel):
    """Estado actual del scan."""
    id: str
    status: str
    progress: int
    current_phase: Optional[str]
    gvm_progress: Optional[int]
    is_running: bool
    is_done: bool
    error_message: Optional[str]


class VulnerabilitySummary(BaseModel):
    """Resumen de vulnerabilidad."""
    id: str
    name: str
    severity: float
    severity_class: str
    host: str
    port: Optional[int]
    cve_ids: List[str]


class ScanResultsResponse(BaseModel):
    """Resultados del scan."""
    scan_id: str
    status: str
    summary: dict
    vulnerabilities: List[VulnerabilitySummary]
    total_vulnerabilities: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear y ejecutar nuevo scan",
)
async def create_scan(
    scan_data: ScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crear un nuevo scan de seguridad y ejecutarlo.
    
    El scan se encola en Celery y comienza a ejecutarse inmediatamente.
    Usa polling en GET /scans/{id}/status para monitorear el progreso.
    """
    # Crear registro del scan
    scan = Scan(
        id=str(uuid4()).replace("-", ""),
        organization_id=current_user.organization_id,
        name=scan_data.name,
        description=scan_data.description,
        scan_type=scan_data.scan_type.value,
        targets=scan_data.targets,
        excluded_targets=scan_data.excluded_targets or [],
        port_range=scan_data.port_range,
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    
    logger.info(f"Created scan {scan.id} for targets {scan_data.targets}")
    
    # Encolar tarea de Celery
    try:
        targets_str = ",".join(scan_data.targets)
        
        # Ejecutar scan de OpenVAS
        task = openvas_full_scan.delay(
            scan_id=scan.id,
            targets=targets_str,
            scan_name=scan.name,
            organization_id=str(current_user.organization_id),
        )
        
        # Guardar ID de tarea Celery
        scan.celery_task_id = task.id
        scan.status = ScanStatus.QUEUED.value
        await db.commit()
        await db.refresh(scan)
        
        logger.info(f"Scan {scan.id} queued with Celery task {task.id}")
        
    except Exception as e:
        logger.error(f"Failed to queue scan {scan.id}: {e}")
        scan.status = ScanStatus.FAILED.value
        scan.error_message = f"Failed to queue: {str(e)}"
        await db.commit()
        await db.refresh(scan)
    
    return scan


@router.get(
    "",
    response_model=ScanListResponse,
    summary="Listar scans",
)
async def list_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[ScanStatus] = Query(None, alias="status"),
    scan_type_filter: Optional[ScanType] = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar todos los scans de la organización."""
    # Query base
    query = select(Scan).where(Scan.organization_id == current_user.organization_id)
    count_query = select(func.count(Scan.id)).where(Scan.organization_id == current_user.organization_id)
    
    # Filtros
    if status_filter:
        query = query.where(Scan.status == status_filter.value)
        count_query = count_query.where(Scan.status == status_filter.value)
    
    if scan_type_filter:
        query = query.where(Scan.scan_type == scan_type_filter.value)
        count_query = count_query.where(Scan.scan_type == scan_type_filter.value)
    
    # Total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginación
    offset = (page - 1) * page_size
    query = query.order_by(desc(Scan.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    scans = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size
    
    return ScanListResponse(
        items=[ScanResponse.model_validate(s) for s in scans],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{scan_id}",
    response_model=ScanResponse,
    summary="Obtener detalle de scan",
)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener detalle completo de un scan."""
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return scan


@router.get(
    "/{scan_id}/status",
    response_model=ScanStatusResponse,
    summary="Obtener estado del scan",
)
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estado actual del scan.
    
    Usa este endpoint para polling durante la ejecución del scan.
    """
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Si hay un task de GVM activo, consultar estado real
    gvm_progress = None
    if scan.gvm_task_id and scan.status == ScanStatus.RUNNING.value:
        try:
            gvm_status = openvas_check_status.delay(scan.gvm_task_id).get(timeout=10)
            gvm_progress = gvm_status.get("progress")
        except Exception:
            pass  # Si falla, usar datos locales
    
    is_running = scan.status in [ScanStatus.RUNNING.value, ScanStatus.QUEUED.value]
    is_done = scan.status in [ScanStatus.COMPLETED.value, ScanStatus.FAILED.value, ScanStatus.CANCELLED.value]
    
    return ScanStatusResponse(
        id=scan.id,
        status=scan.status,
        progress=scan.progress,
        current_phase=scan.current_phase,
        gvm_progress=gvm_progress,
        is_running=is_running,
        is_done=is_done,
        error_message=scan.error_message,
    )


@router.get(
    "/{scan_id}/results",
    response_model=ScanResultsResponse,
    summary="Obtener resultados del scan",
)
async def get_scan_results(
    scan_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    min_severity: Optional[float] = Query(None, ge=0, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener vulnerabilidades encontradas en el scan."""
    # Verificar scan existe
    scan_query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    scan_result = await db.execute(scan_query)
    scan = scan_result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Query vulnerabilidades
    vuln_query = select(Vulnerability).where(Vulnerability.scan_id == scan_id)
    count_query = select(func.count(Vulnerability.id)).where(Vulnerability.scan_id == scan_id)
    
    if min_severity is not None:
        vuln_query = vuln_query.where(Vulnerability.severity >= min_severity)
        count_query = count_query.where(Vulnerability.severity >= min_severity)
    
    # Total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginación
    offset = (page - 1) * page_size
    vuln_query = vuln_query.order_by(desc(Vulnerability.severity)).offset(offset).limit(page_size)
    
    vuln_result = await db.execute(vuln_query)
    vulns = vuln_result.scalars().all()
    
    vulnerabilities = [
        VulnerabilitySummary(
            id=v.id,
            name=v.name,
            severity=v.severity,
            severity_class=v.severity_class,
            host=v.host,
            port=v.port,
            cve_ids=v.cve_ids or [],
        )
        for v in vulns
    ]
    
    summary = {
        "total": scan.total_vulnerabilities,
        "critical": scan.vuln_critical,
        "high": scan.vuln_high,
        "medium": scan.vuln_medium,
        "low": scan.vuln_low,
        "info": scan.vuln_info,
        "hosts_scanned": scan.total_hosts_scanned,
        "hosts_up": scan.total_hosts_up,
    }
    
    return ScanResultsResponse(
        scan_id=scan.id,
        status=scan.status,
        summary=summary,
        vulnerabilities=vulnerabilities,
        total_vulnerabilities=total,
    )


@router.post(
    "/{scan_id}/stop",
    response_model=ScanStatusResponse,
    summary="Detener scan en ejecución",
)
async def stop_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detener un scan que está en ejecución."""
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan.status not in [ScanStatus.RUNNING.value, ScanStatus.QUEUED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot stop scan in status: {scan.status}"
        )
    
    # Detener en GVM si hay task activo
    if scan.gvm_task_id:
        try:
            openvas_stop_scan.delay(scan.gvm_task_id)
        except Exception as e:
            logger.warning(f"Failed to stop GVM task: {e}")
    
    # Actualizar estado local
    scan.cancel()
    await db.commit()
    await db.refresh(scan)
    
    logger.info(f"Scan {scan_id} stopped by user {current_user.id}")
    
    return ScanStatusResponse(
        id=scan.id,
        status=scan.status,
        progress=scan.progress,
        current_phase=scan.current_phase,
        gvm_progress=None,
        is_running=False,
        is_done=True,
        error_message=None,
    )


@router.delete(
    "/{scan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar scan",
)
async def delete_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Eliminar un scan y todas sus vulnerabilidades asociadas.
    
    No se puede eliminar un scan en ejecución (debe detenerse primero).
    """
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan.status in [ScanStatus.RUNNING.value, ScanStatus.QUEUED.value]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete running scan. Stop it first."
        )
    
    await db.delete(scan)
    await db.commit()
    
    logger.info(f"Scan {scan_id} deleted by user {current_user.id}")
