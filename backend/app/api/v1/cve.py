# =============================================================================
# NESTSECURE - Endpoints de CVE
# =============================================================================
"""
Endpoints para gestión del caché de CVEs.

Incluye:
- GET /: Buscar CVEs en el caché
- GET /{cve_id}: Obtener CVE específico
- POST /sync: Sincronizar CVEs desde NVD
- GET /sync/status: Estado de sincronización
- GET /stats: Estadísticas del caché
"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentActiveUser, require_role
from app.db.session import get_db
from app.models.cve_cache import CVECache
from app.models.user import UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.cve import (
    CVERead,
    CVEReadMinimal,
    CVESearch,
    CVEStats,
    CVESyncRequest,
    CVESyncStatus,
)

router = APIRouter()


# =============================================================================
# Search CVEs
# =============================================================================
@router.get(
    "",
    response_model=PaginatedResponse[CVEReadMinimal],
    summary="Buscar CVEs",
    description="Busca CVEs en el caché local",
)
async def search_cves(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items por página"),
    search: str | None = Query(default=None, description="Buscar por CVE ID o descripción"),
    severity: str | None = Query(default=None, description="Filtrar por severidad"),
    min_cvss: float | None = Query(default=None, ge=0, le=10, description="CVSS mínimo"),
    max_cvss: float | None = Query(default=None, ge=0, le=10, description="CVSS máximo"),
    has_exploit: bool | None = Query(default=None, description="Con exploit conocido"),
    in_cisa_kev: bool | None = Query(default=None, description="En lista CISA KEV"),
    year: int | None = Query(default=None, ge=1999, description="Año del CVE"),
    order_by: str = Query(default="cvss_v3_score", description="Campo para ordenar"),
    order_desc: bool = Query(default=True, description="Orden descendente"),
):
    """
    Busca CVEs en el caché local.
    
    Filtros disponibles:
    - search: Busca en CVE ID y descripción (ILIKE)
    - severity: critical, high, medium, low
    - min_cvss, max_cvss: Rango de puntuación CVSS v3
    - has_exploit: true = solo CVEs con exploit conocido
    - in_cisa_kev: true = solo CVEs en lista CISA Known Exploited Vulnerabilities
    - year: Filtra por año de publicación (ej: 2024)
    
    Ordenamiento:
    - order_by: cvss_v3_score (default), published_date, epss_score
    - order_desc: true (default) para descendente
    """
    stmt = select(CVECache)
    
    # Aplicar filtros
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                CVECache.cve_id.ilike(search_pattern),
                CVECache.description.ilike(search_pattern),
            )
        )
    
    if severity:
        severity_ranges = {
            "critical": (9.0, 10.0),
            "high": (7.0, 8.9),
            "medium": (4.0, 6.9),
            "low": (0.1, 3.9),
        }
        if severity in severity_ranges:
            min_s, max_s = severity_ranges[severity]
            stmt = stmt.where(
                and_(
                    CVECache.cvss_v3_score >= min_s,
                    CVECache.cvss_v3_score <= max_s,
                )
            )
    
    if min_cvss is not None:
        stmt = stmt.where(CVECache.cvss_v3_score >= min_cvss)
    
    if max_cvss is not None:
        stmt = stmt.where(CVECache.cvss_v3_score <= max_cvss)
    
    if has_exploit is not None:
        stmt = stmt.where(CVECache.exploit_available == has_exploit)
    
    if in_cisa_kev is not None:
        stmt = stmt.where(CVECache.in_cisa_kev == in_cisa_kev)
    
    if year:
        stmt = stmt.where(CVECache.cve_id.like(f"CVE-{year}-%"))
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Ordenamiento
    order_columns = {
        "cvss_v3_score": CVECache.cvss_v3_score,
        "published_date": CVECache.published_date,
        "epss_score": CVECache.epss_score,
        "cve_id": CVECache.cve_id,
        "hit_count": CVECache.hit_count,
    }
    order_column = order_columns.get(order_by, CVECache.cvss_v3_score)
    
    if order_desc:
        stmt = stmt.order_by(order_column.desc().nullslast())
    else:
        stmt = stmt.order_by(order_column.asc().nullsfirst())
    
    # Paginación
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    cves = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[CVEReadMinimal.model_validate(c) for c in cves],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Get CVE Details
# =============================================================================
@router.get(
    "/{cve_id}",
    response_model=CVERead,
    summary="Obtener CVE",
    description="Obtiene un CVE específico por su ID",
)
async def get_cve(
    cve_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene un CVE por su ID (ej: CVE-2024-1234).
    
    Si el CVE no está en caché, intenta obtenerlo de la API de NVD.
    Incrementa el contador de hits para priorizar CVEs populares.
    """
    # Buscar en caché
    stmt = select(CVECache).where(CVECache.cve_id == cve_id.upper())
    result = await db.execute(stmt)
    cve = result.scalar_one_or_none()
    
    if cve:
        # Incrementar hit count
        cve.increment_hit_count()
        await db.commit()
        return CVERead.model_validate(cve)
    
    # TODO: Si no está en caché, podríamos obtenerlo de NVD API
    # Por ahora, retornamos 404
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"CVE {cve_id} no encontrado en caché. Ejecuta una sincronización.",
    )


# =============================================================================
# Trigger CVE Sync
# =============================================================================
@router.post(
    "/sync",
    response_model=MessageResponse,
    summary="Sincronizar CVEs",
    description="Inicia la sincronización de CVEs desde NVD",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def sync_cves(
    sync_request: CVESyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Inicia la sincronización de CVEs desde la API de NVD.
    
    Solo disponible para administradores.
    
    Opciones:
    - full_sync: Sincroniza todos los CVEs (puede tardar horas)
    - days_back: Solo sincroniza los últimos N días (recomendado)
    - cve_ids: Lista específica de CVEs a sincronizar
    - keywords: Buscar CVEs por palabras clave
    """
    # TODO: Enviar tarea a Celery para sincronización
    # cve_sync_task.delay(
    #     full_sync=sync_request.full_sync,
    #     days_back=sync_request.days_back,
    #     cve_ids=sync_request.cve_ids,
    #     keywords=sync_request.keywords,
    # )
    
    if sync_request.full_sync:
        message = "Sincronización completa iniciada. Puede tardar varias horas."
    elif sync_request.cve_ids:
        message = f"Sincronización de {len(sync_request.cve_ids)} CVEs específicos iniciada."
    else:
        days = sync_request.days_back or 7
        message = f"Sincronización de los últimos {days} días iniciada."
    
    return MessageResponse(message=message)


# =============================================================================
# Get Sync Status
# =============================================================================
@router.get(
    "/sync/status",
    response_model=CVESyncStatus,
    summary="Estado de sincronización",
    description="Obtiene el estado actual de la sincronización de CVEs",
)
async def get_sync_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene el estado de la última/actual sincronización de CVEs.
    
    Incluye:
    - is_running: Si hay una sincronización en curso
    - last_sync: Fecha de última sincronización exitosa
    - progress: Porcentaje de progreso si está en curso
    - total_cves: Total de CVEs en caché
    - cves_synced: CVEs sincronizados en el ciclo actual
    """
    # Contar total de CVEs en caché
    total_stmt = select(func.count()).select_from(CVECache)
    total_result = await db.execute(total_stmt)
    total_cves = total_result.scalar() or 0
    
    # Obtener fecha del CVE más reciente (aproximación de última sync)
    last_sync_stmt = select(func.max(CVECache.last_modified_date))
    last_sync_result = await db.execute(last_sync_stmt)
    last_sync = last_sync_result.scalar()
    
    # CVEs actualizados en las últimas 24 horas
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_stmt = select(func.count()).select_from(CVECache).where(
        CVECache.updated_at >= yesterday
    )
    recent_result = await db.execute(recent_stmt)
    recent_synced = recent_result.scalar() or 0
    
    # TODO: Obtener estado real del worker de Celery
    # Por ahora, retornamos datos estáticos
    return CVESyncStatus(
        is_running=False,  # TODO: Verificar con Celery
        last_sync=last_sync,
        progress=0,
        total_cves=total_cves,
        cves_synced=recent_synced,
        errors=[],
    )


# =============================================================================
# CVE Statistics
# =============================================================================
@router.get(
    "/stats/summary",
    response_model=CVEStats,
    summary="Estadísticas de CVEs",
    description="Obtiene estadísticas del caché de CVEs",
)
async def get_cve_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene estadísticas del caché de CVEs:
    - Total de CVEs
    - Por severidad
    - Con exploit disponible
    - En lista CISA KEV
    - Top CVEs más consultados
    """
    # Total
    total_stmt = select(func.count()).select_from(CVECache)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0
    
    # Por severidad (basado en CVSS v3)
    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    
    # Critical (9.0-10.0)
    critical_stmt = select(func.count()).select_from(CVECache).where(
        CVECache.cvss_v3_score >= 9.0
    )
    critical_result = await db.execute(critical_stmt)
    severity_counts["critical"] = critical_result.scalar() or 0
    
    # High (7.0-8.9)
    high_stmt = select(func.count()).select_from(CVECache).where(
        and_(
            CVECache.cvss_v3_score >= 7.0,
            CVECache.cvss_v3_score < 9.0,
        )
    )
    high_result = await db.execute(high_stmt)
    severity_counts["high"] = high_result.scalar() or 0
    
    # Medium (4.0-6.9)
    medium_stmt = select(func.count()).select_from(CVECache).where(
        and_(
            CVECache.cvss_v3_score >= 4.0,
            CVECache.cvss_v3_score < 7.0,
        )
    )
    medium_result = await db.execute(medium_stmt)
    severity_counts["medium"] = medium_result.scalar() or 0
    
    # Low (0.1-3.9)
    low_stmt = select(func.count()).select_from(CVECache).where(
        and_(
            CVECache.cvss_v3_score >= 0.1,
            CVECache.cvss_v3_score < 4.0,
        )
    )
    low_result = await db.execute(low_stmt)
    severity_counts["low"] = low_result.scalar() or 0
    
    # Con exploit
    exploit_stmt = select(func.count()).select_from(CVECache).where(
        CVECache.exploit_available == True
    )
    exploit_result = await db.execute(exploit_stmt)
    with_exploit = exploit_result.scalar() or 0
    
    # En CISA KEV
    kev_stmt = select(func.count()).select_from(CVECache).where(
        CVECache.in_cisa_kev == True
    )
    kev_result = await db.execute(kev_stmt)
    in_cisa_kev = kev_result.scalar() or 0
    
    # Promedio CVSS
    avg_stmt = select(func.avg(CVECache.cvss_v3_score)).where(
        CVECache.cvss_v3_score.isnot(None)
    )
    avg_result = await db.execute(avg_stmt)
    avg_cvss = avg_result.scalar() or 0.0
    
    # CVEs más consultados
    top_stmt = select(CVECache).order_by(
        CVECache.hit_count.desc()
    ).limit(10)
    top_result = await db.execute(top_stmt)
    top_cves = top_result.scalars().all()
    
    return CVEStats(
        total=total,
        by_severity=severity_counts,
        with_exploit=with_exploit,
        in_cisa_kev=in_cisa_kev,
        average_cvss=round(float(avg_cvss), 2),
        top_cves=[
            {
                "cve_id": c.cve_id,
                "cvss_score": c.cvss_v3_score,
                "hit_count": c.hit_count,
            }
            for c in top_cves
        ],
    )


# =============================================================================
# Lookup specific CVE (quick endpoint)
# =============================================================================
@router.get(
    "/lookup/{cve_id}",
    response_model=CVEReadMinimal | None,
    summary="Buscar CVE rápido",
    description="Busca un CVE específico (endpoint ligero)",
)
async def lookup_cve(
    cve_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Busca un CVE por su ID sin incrementar el contador.
    
    Útil para verificar si un CVE existe en caché rápidamente.
    Retorna null si no existe (en lugar de 404).
    """
    stmt = select(CVECache).where(CVECache.cve_id == cve_id.upper())
    result = await db.execute(stmt)
    cve = result.scalar_one_or_none()
    
    if cve:
        return CVEReadMinimal.model_validate(cve)
    
    return None
