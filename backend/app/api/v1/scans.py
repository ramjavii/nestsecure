# =============================================================================
# NESTSECURE - Endpoints de Escaneos
# =============================================================================
"""
Endpoints para gestión de escaneos de seguridad.

Incluye:
- GET /: Listar escaneos de mi organización
- GET /{id}: Obtener escaneo con detalles
- POST /: Crear/iniciar nuevo escaneo
- PATCH /{id}/cancel: Cancelar escaneo en curso
- GET /{id}/progress: Obtener progreso del escaneo
- GET /{id}/vulnerabilities: Listar vulnerabilidades del escaneo
- GET /stats: Estadísticas de escaneos
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentActiveUser, require_role
from app.db.session import get_db
from app.models.asset import Asset
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.user import UserRole
from app.models.vulnerability import Vulnerability
from app.schemas.common import DeleteResponse, MessageResponse, PaginatedResponse
from app.schemas.scan import (
    ScanCreate,
    ScanProgress,
    ScanRead,
    ScanReadMinimal,
    ScanReadWithLogs,
    ScanStats,
    ScanUpdate,
)
from app.schemas.vulnerability import VulnerabilityReadMinimal

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def get_scan_or_404(
    db: AsyncSession,
    scan_id: str,
    organization_id: str,
    include_relations: bool = False,
) -> Scan:
    """
    Obtiene un escaneo por ID o lanza 404.
    
    Args:
        db: Sesión de base de datos
        scan_id: ID del escaneo
        organization_id: ID de la organización del usuario
        include_relations: Si incluir relaciones
    
    Returns:
        Scan encontrado
    
    Raises:
        HTTPException 404: Si no existe o no pertenece a la organización
    """
    stmt = select(Scan).where(
        and_(
            Scan.id == scan_id,
            Scan.organization_id == organization_id,
        )
    )
    
    if include_relations:
        stmt = stmt.options(
            selectinload(Scan.created_by),
            selectinload(Scan.organization),
        )
    
    result = await db.execute(stmt)
    scan = result.scalar_one_or_none()
    
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escaneo no encontrado",
        )
    
    return scan


# =============================================================================
# List Scans
# =============================================================================
@router.get(
    "",
    response_model=PaginatedResponse[ScanRead],
    summary="Listar escaneos",
    description="Lista todos los escaneos de mi organización",
)
async def list_scans(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items por página"),
    scan_type: str | None = Query(default=None, description="Filtrar por tipo"),
    status_filter: str | None = Query(default=None, alias="status", description="Filtrar por estado"),
    order_by: str = Query(default="created_at", description="Campo para ordenar"),
    order_desc: bool = Query(default=True, description="Orden descendente"),
):
    """
    Lista escaneos con filtros.
    
    Filtros disponibles:
    - scan_type: full, quick, targeted, port_scan, vuln_scan, compliance
    - status: pending, running, completed, failed, cancelled
    
    Ordenamiento:
    - order_by: created_at (default), started_at, completed_at, name
    - order_desc: true (default) para descendente
    """
    # Base query - solo escaneos de mi organización
    stmt = select(Scan).where(
        Scan.organization_id == current_user.organization_id
    )
    
    # Aplicar filtros
    if scan_type:
        if scan_type not in {t.value for t in ScanType}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de escaneo inválido: {scan_type}",
            )
        stmt = stmt.where(Scan.scan_type == scan_type)
    
    if status_filter:
        if status_filter not in {s.value for s in ScanStatus}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {status_filter}",
            )
        stmt = stmt.where(Scan.status == status_filter)
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Ordenamiento
    order_columns = {
        "created_at": Scan.created_at,
        "started_at": Scan.started_at,
        "completed_at": Scan.completed_at,
        "name": Scan.name,
        "progress": Scan.progress,
    }
    order_column = order_columns.get(order_by, Scan.created_at)
    
    if order_desc:
        stmt = stmt.order_by(order_column.desc().nullslast())
    else:
        stmt = stmt.order_by(order_column.asc().nullsfirst())
    
    # Paginación
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    # Include created_by
    stmt = stmt.options(selectinload(Scan.created_by))
    
    result = await db.execute(stmt)
    scans = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[ScanRead.model_validate(s) for s in scans],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Get Scan Details
# =============================================================================
@router.get(
    "/{scan_id}",
    response_model=ScanReadWithLogs,
    summary="Obtener escaneo",
    description="Obtiene un escaneo con todos sus detalles y logs",
)
async def get_scan(
    scan_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene un escaneo con:
    - Datos completos del escaneo
    - Usuario que lo creó
    - Logs del escaneo
    - Conteo de vulnerabilidades encontradas
    """
    scan = await get_scan_or_404(
        db, scan_id, current_user.organization_id, include_relations=True
    )
    return ScanReadWithLogs.model_validate(scan)


# =============================================================================
# Create Scan
# =============================================================================
@router.post(
    "",
    response_model=ScanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear escaneo",
    description="Crea y programa un nuevo escaneo",
    dependencies=[Depends(require_role(UserRole.OPERATOR))],
)
async def create_scan(
    scan_in: ScanCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Crea un nuevo escaneo.
    
    El escaneo se crea en estado 'pending' y debe ser
    ejecutado por un worker de Celery.
    
    Targets pueden ser:
    - IPs individuales: ["192.168.1.1", "192.168.1.2"]
    - Rangos CIDR: ["192.168.1.0/24"]
    - Asset IDs: ["uuid-del-asset"]
    - Mixto: combinación de los anteriores
    """
    organization_id = current_user.organization_id
    
    # Validar targets si son asset IDs
    validated_targets = []
    for target in scan_in.targets:
        # Si parece un UUID, verificar que el asset existe
        if len(target) == 36 and "-" in target:
            asset_stmt = select(Asset).where(
                and_(
                    Asset.id == target,
                    Asset.organization_id == organization_id,
                )
            )
            asset_result = await db.execute(asset_stmt)
            asset = asset_result.scalar_one_or_none()
            
            if asset:
                # Usar la IP del asset como target real
                validated_targets.append(asset.ip_address)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Asset no encontrado: {target}",
                )
        else:
            # Es una IP o rango, usar directamente
            validated_targets.append(target)
    
    # Verificar que no hay otro escaneo en curso
    running_stmt = select(Scan).where(
        and_(
            Scan.organization_id == organization_id,
            Scan.status.in_(["pending", "running"]),
        )
    )
    running_result = await db.execute(running_stmt)
    running_scan = running_result.scalar_one_or_none()
    
    if running_scan:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay un escaneo en curso. Espera a que termine o cancélalo.",
        )
    
    # Crear escaneo
    scan = Scan(
        organization_id=organization_id,
        created_by_id=current_user.id,
        name=scan_in.name,
        description=scan_in.description,
        scan_type=scan_in.scan_type,
        targets=validated_targets,
        excluded_targets=scan_in.excluded_targets or [],
        port_range=scan_in.port_range,
        engine_config=scan_in.engine_config or {},
        is_scheduled=scan_in.is_scheduled,
        cron_expression=scan_in.cron_expression,
        status=ScanStatus.PENDING.value,
        progress=0,
        logs=[
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": "Escaneo creado y programado",
            }
        ],
    )
    
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    
    # TODO: Enviar tarea a Celery para ejecutar el escaneo
    # scan_task.delay(scan.id)
    
    return ScanRead.model_validate(scan)


# =============================================================================
# Cancel Scan
# =============================================================================
@router.patch(
    "/{scan_id}/cancel",
    response_model=ScanRead,
    summary="Cancelar escaneo",
    description="Cancela un escaneo en curso",
    dependencies=[Depends(require_role(UserRole.OPERATOR))],
)
async def cancel_scan(
    scan_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Cancela un escaneo en curso.
    
    Solo se pueden cancelar escaneos en estado 'pending' o 'running'.
    """
    scan = await get_scan_or_404(
        db, scan_id, current_user.organization_id
    )
    
    if scan.status not in [ScanStatus.PENDING.value, ScanStatus.RUNNING.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede cancelar un escaneo en estado '{scan.status}'",
        )
    
    scan.cancel()
    await db.commit()
    await db.refresh(scan)
    
    # TODO: Enviar señal a Celery para detener la tarea
    # celery_app.control.revoke(scan.celery_task_id, terminate=True)
    
    return ScanRead.model_validate(scan)


# =============================================================================
# Get Scan Progress
# =============================================================================
@router.get(
    "/{scan_id}/progress",
    response_model=ScanProgress,
    summary="Obtener progreso",
    description="Obtiene el progreso actual de un escaneo",
)
async def get_scan_progress(
    scan_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene el progreso de un escaneo.
    
    Útil para polling desde el frontend mientras
    un escaneo está en curso.
    """
    scan = await get_scan_or_404(
        db, scan_id, current_user.organization_id
    )
    
    return ScanProgress(
        scan_id=scan.id,
        status=scan.status,
        progress=scan.progress,
        current_target=scan.current_phase,  # Using current_phase as current target
        targets_scanned=scan.total_hosts_scanned,
        targets_total=len(scan.targets) if scan.targets else 0,
        vulnerabilities_found=scan.vuln_critical + scan.vuln_high + 
                             scan.vuln_medium + scan.vuln_low,
        started_at=scan.started_at,
        estimated_completion=None,  # TODO: Calcular basado en progreso
    )


# =============================================================================
# Get Scan Vulnerabilities
# =============================================================================
@router.get(
    "/{scan_id}/vulnerabilities",
    response_model=PaginatedResponse[VulnerabilityReadMinimal],
    summary="Vulnerabilidades del escaneo",
    description="Lista las vulnerabilidades encontradas en un escaneo",
)
async def get_scan_vulnerabilities(
    scan_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items por página"),
    severity: str | None = Query(default=None, description="Filtrar por severidad"),
):
    """
    Lista las vulnerabilidades encontradas en un escaneo específico.
    """
    # Verificar que el escaneo existe y pertenece a la organización
    await get_scan_or_404(
        db, scan_id, current_user.organization_id
    )
    
    # Query de vulnerabilidades del escaneo
    stmt = select(Vulnerability).where(Vulnerability.scan_id == scan_id)
    
    if severity:
        stmt = stmt.where(Vulnerability.severity == severity)
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Ordenar por severidad y CVSS
    stmt = stmt.order_by(
        Vulnerability.severity.asc(),  # critical primero
        Vulnerability.cvss_score.desc().nullslast(),
    )
    
    # Paginación
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    vulns = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[VulnerabilityReadMinimal.model_validate(v) for v in vulns],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Scan Statistics
# =============================================================================
@router.get(
    "/stats/summary",
    response_model=ScanStats,
    summary="Estadísticas de escaneos",
    description="Obtiene estadísticas agregadas de escaneos",
)
async def get_scan_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene estadísticas de escaneos:
    - Total de escaneos
    - Por tipo
    - Por estado
    - Promedio de vulnerabilidades encontradas
    - Último escaneo completado
    """
    org_id = current_user.organization_id
    
    # Total
    total_stmt = select(func.count()).select_from(Scan).where(
        Scan.organization_id == org_id
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0
    
    # Por tipo
    type_counts = {}
    for scan_type in ScanType:
        count_stmt = select(func.count()).select_from(Scan).where(
            and_(
                Scan.organization_id == org_id,
                Scan.scan_type == scan_type.value,
            )
        )
        result = await db.execute(count_stmt)
        type_counts[scan_type.value] = result.scalar() or 0
    
    # Por estado
    status_counts = {}
    for scan_status in ScanStatus:
        count_stmt = select(func.count()).select_from(Scan).where(
            and_(
                Scan.organization_id == org_id,
                Scan.status == scan_status.value,
            )
        )
        result = await db.execute(count_stmt)
        status_counts[scan_status.value] = result.scalar() or 0
    
    # Completados
    completed_stmt = select(func.count()).select_from(Scan).where(
        and_(
            Scan.organization_id == org_id,
            Scan.status == ScanStatus.COMPLETED.value,
        )
    )
    completed_result = await db.execute(completed_stmt)
    completed = completed_result.scalar() or 0
    
    # Promedio de vulnerabilidades en escaneos completados
    avg_vulns_stmt = select(
        func.avg(
            Scan.vuln_critical + Scan.vuln_high +
            Scan.vuln_medium + Scan.vuln_low
        )
    ).where(
        and_(
            Scan.organization_id == org_id,
            Scan.status == ScanStatus.COMPLETED.value,
        )
    )
    avg_result = await db.execute(avg_vulns_stmt)
    avg_vulns = avg_result.scalar() or 0
    
    # Último escaneo completado
    last_stmt = select(Scan).where(
        and_(
            Scan.organization_id == org_id,
            Scan.status == ScanStatus.COMPLETED.value,
        )
    ).order_by(Scan.completed_at.desc()).limit(1)
    last_result = await db.execute(last_stmt)
    last_scan = last_result.scalar_one_or_none()
    
    return ScanStats(
        total=total,
        by_type=type_counts,
        by_status=status_counts,
        completed=completed,
        failed=status_counts.get("failed", 0),
        running=status_counts.get("running", 0),
        average_vulnerabilities=round(float(avg_vulns), 1),
        last_scan_date=last_scan.completed_at if last_scan else None,
    )


# =============================================================================
# Update Scan (limited)
# =============================================================================
@router.patch(
    "/{scan_id}",
    response_model=ScanRead,
    summary="Actualizar escaneo",
    description="Actualiza metadatos de un escaneo",
    dependencies=[Depends(require_role(UserRole.OPERATOR))],
)
async def update_scan(
    scan_id: str,
    scan_in: ScanUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Actualiza metadatos de un escaneo.
    
    Solo permite actualizar nombre y descripción.
    El estado se gestiona mediante acciones específicas (cancel, etc.)
    """
    scan = await get_scan_or_404(
        db, scan_id, current_user.organization_id
    )
    
    update_data = scan_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(scan, field, value)
    
    await db.commit()
    await db.refresh(scan)
    
    return ScanRead.model_validate(scan)


# =============================================================================
# Delete Scan
# =============================================================================
@router.delete(
    "/{scan_id}",
    response_model=DeleteResponse,
    summary="Eliminar escaneo",
    description="Elimina un escaneo y sus vulnerabilidades asociadas",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_scan(
    scan_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Elimina un escaneo y sus vulnerabilidades asociadas.
    
    Solo disponible para administradores.
    No se puede eliminar un escaneo en curso.
    """
    scan = await get_scan_or_404(
        db, scan_id, current_user.organization_id
    )
    
    if scan.status == ScanStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un escaneo en curso. Cancélalo primero.",
        )
    
    deleted_id = scan.id
    
    # Las vulnerabilidades se eliminan por CASCADE
    await db.delete(scan)
    await db.commit()
    
    return DeleteResponse(
        message="Escaneo eliminado correctamente",
        deleted_id=deleted_id
    )
