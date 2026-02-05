# =============================================================================
# NESTSECURE - Endpoints de Assets
# =============================================================================
"""
Endpoints CRUD para gestión de assets (activos de infraestructura).

Incluye:
- GET /: Listar assets de mi organización
- POST /: Crear asset
- GET /{id}: Obtener asset con servicios
- PATCH /{id}: Actualizar asset
- DELETE /{id}: Eliminar asset
- GET /{id}/services: Listar servicios del asset
- GET /{id}/stats: Estadísticas del asset
- POST /{id}/scan: Iniciar escaneo del asset
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentActiveUser, require_role
from app.db.session import get_db
from app.models.asset import Asset, AssetCriticality, AssetStatus, AssetType
from app.models.service import Service
from app.models.user import UserRole
from app.schemas.asset import (
    AssetCreate,
    AssetRead,
    AssetReadWithOrg,
    AssetSummary,
    AssetUpdate,
    AssetVulnerabilityStats,
)
from app.schemas.common import DeleteResponse, MessageResponse, PaginatedResponse
from app.schemas.service import ServiceRead

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def get_asset_or_404(
    db: AsyncSession,
    asset_id: str,
    organization_id: str,
    include_services: bool = False,
) -> Asset:
    """
    Obtiene un asset por ID o lanza 404.
    
    Args:
        db: Sesión de base de datos
        asset_id: ID del asset
        organization_id: ID de la organización del usuario
        include_services: Si incluir los servicios relacionados
    
    Returns:
        Asset encontrado
    
    Raises:
        HTTPException 404: Si el asset no existe o no pertenece a la organización
    """
    stmt = select(Asset).where(
        and_(
            Asset.id == asset_id,
            Asset.organization_id == organization_id,
        )
    )
    
    if include_services:
        stmt = stmt.options(selectinload(Asset.services))
    
    stmt = stmt.options(selectinload(Asset.organization))
    
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()
    
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset no encontrado",
        )
    
    return asset


async def check_ip_unique(
    db: AsyncSession,
    ip_address: str,
    organization_id: str,
    exclude_id: str | None = None,
) -> None:
    """
    Verifica que la IP sea única en la organización.
    
    Raises:
        HTTPException 409: Si la IP ya existe en la organización
    """
    stmt = select(Asset.id).where(
        and_(
            Asset.ip_address == ip_address,
            Asset.organization_id == organization_id,
        )
    )
    
    if exclude_id:
        stmt = stmt.where(Asset.id != exclude_id)
    
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un asset con la IP {ip_address} en esta organización",
        )


# =============================================================================
# List Assets
# =============================================================================
@router.get(
    "",
    response_model=PaginatedResponse[AssetRead],
    summary="Listar assets",
    description="Lista todos los assets de mi organización con filtros y paginación",
)
async def list_assets(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=100, ge=1, le=1000, description="Items por página"),
    search: str | None = Query(default=None, description="Buscar por IP o hostname"),
    status: str | None = Query(default=None, description="Filtrar por estado"),
    criticality: str | None = Query(default=None, description="Filtrar por criticidad"),
    asset_type: str | None = Query(default=None, description="Filtrar por tipo"),
    is_reachable: bool | None = Query(default=None, description="Filtrar por alcanzabilidad"),
    has_vulnerabilities: bool | None = Query(default=None, description="Solo con vulnerabilidades"),
    order_by: str = Query(default="risk_score", description="Campo para ordenar"),
    order_desc: bool = Query(default=True, description="Orden descendente"),
):
    """
    Lista assets con filtros avanzados.
    
    Filtros disponibles:
    - search: Busca en IP y hostname (ILIKE)
    - status: active, inactive, maintenance, decommissioned
    - criticality: critical, high, medium, low
    - asset_type: server, workstation, network_device, etc.
    - is_reachable: true/false
    - has_vulnerabilities: true = solo assets con vulnerabilidades
    
    Ordenamiento:
    - order_by: risk_score (default), ip_address, hostname, last_seen, created_at
    - order_desc: true (default) para descendente
    """
    # Base query - solo assets de mi organización
    stmt = select(Asset).where(Asset.organization_id == current_user.organization_id)
    
    # Aplicar filtros
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Asset.ip_address.ilike(search_pattern),
                Asset.hostname.ilike(search_pattern),
            )
        )
    
    if status:
        if status not in {s.value for s in AssetStatus}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {status}",
            )
        stmt = stmt.where(Asset.status == status)
    
    if criticality:
        if criticality not in {c.value for c in AssetCriticality}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Criticidad inválida: {criticality}",
            )
        stmt = stmt.where(Asset.criticality == criticality)
    
    if asset_type:
        if asset_type not in {t.value for t in AssetType}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo inválido: {asset_type}",
            )
        stmt = stmt.where(Asset.asset_type == asset_type)
    
    if is_reachable is not None:
        stmt = stmt.where(Asset.is_reachable == is_reachable)
    
    if has_vulnerabilities:
        stmt = stmt.where(
            (Asset.vuln_critical_count > 0) |
            (Asset.vuln_high_count > 0) |
            (Asset.vuln_medium_count > 0) |
            (Asset.vuln_low_count > 0)
        )
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Ordenamiento
    order_columns = {
        "risk_score": Asset.risk_score,
        "ip_address": Asset.ip_address,
        "hostname": Asset.hostname,
        "last_seen": Asset.last_seen,
        "created_at": Asset.created_at,
        "criticality": Asset.criticality,
    }
    order_column = order_columns.get(order_by, Asset.risk_score)
    
    if order_desc:
        stmt = stmt.order_by(order_column.desc().nullslast())
    else:
        stmt = stmt.order_by(order_column.asc().nullsfirst())
    
    # Paginación
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    assets = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[AssetRead.model_validate(a) for a in assets],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Create Asset
# =============================================================================
@router.post(
    "",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear asset",
    description="Crea un nuevo asset manualmente",
    dependencies=[Depends(require_role(UserRole.OPERATOR))],
)
async def create_asset(
    asset_in: AssetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Crea un nuevo asset.
    
    - Solo puede crear assets en su propia organización
    - La IP debe ser única dentro de la organización
    - Inicializa contadores de vulnerabilidades en 0
    """
    # Forzar organization_id del usuario actual (seguridad multi-tenant)
    organization_id = current_user.organization_id
    
    # Verificar IP única
    await check_ip_unique(db, asset_in.ip_address, organization_id)
    
    # Crear asset
    asset = Asset(
        organization_id=organization_id,
        ip_address=asset_in.ip_address,
        hostname=asset_in.hostname,
        mac_address=asset_in.mac_address,
        operating_system=asset_in.operating_system,
        os_version=asset_in.os_version,
        asset_type=asset_in.asset_type,
        criticality=asset_in.criticality,
        tags=asset_in.tags or [],
        description=asset_in.description,
        status=AssetStatus.ACTIVE.value,
        is_reachable=True,
        risk_score=0.0,
        vuln_critical_count=0,
        vuln_high_count=0,
        vuln_medium_count=0,
        vuln_low_count=0,
    )
    
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    return AssetRead.model_validate(asset)


# =============================================================================
# Get Asset
# =============================================================================
@router.get(
    "/{asset_id}",
    response_model=AssetReadWithOrg,
    summary="Obtener asset",
    description="Obtiene un asset por ID con información de organización",
)
async def get_asset(
    asset_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene un asset específico.
    
    - Solo puede ver assets de su organización
    - Incluye información de la organización
    """
    asset = await get_asset_or_404(
        db, asset_id, current_user.organization_id, include_services=False
    )
    return AssetReadWithOrg.model_validate(asset)


# =============================================================================
# Update Asset
# =============================================================================
@router.patch(
    "/{asset_id}",
    response_model=AssetRead,
    summary="Actualizar asset",
    description="Actualiza campos de un asset",
    dependencies=[Depends(require_role(UserRole.OPERATOR))],
)
async def update_asset(
    asset_id: str,
    asset_in: AssetUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Actualiza un asset existente.
    
    Campos actualizables:
    - hostname, mac_address, operating_system, os_version
    - asset_type, criticality, status
    - tags, description
    
    NO se puede cambiar: ip_address, organization_id
    """
    asset = await get_asset_or_404(db, asset_id, current_user.organization_id)
    
    # Actualizar solo campos proporcionados
    update_data = asset_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    await db.commit()
    await db.refresh(asset)
    
    return AssetRead.model_validate(asset)


# =============================================================================
# Delete Asset
# =============================================================================
@router.delete(
    "/{asset_id}",
    response_model=DeleteResponse,
    summary="Eliminar asset",
    description="Elimina un asset y sus servicios asociados",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_asset(
    asset_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Elimina un asset.
    
    - Requiere rol ADMIN
    - Elimina en cascada todos los servicios asociados
    """
    asset = await get_asset_or_404(db, asset_id, current_user.organization_id)
    
    await db.delete(asset)
    await db.commit()
    
    return DeleteResponse(
        success=True,
        message="Asset eliminado correctamente",
        deleted_id=asset_id,
    )


# =============================================================================
# Get Asset Services
# =============================================================================
@router.get(
    "/{asset_id}/services",
    response_model=list[ServiceRead],
    summary="Servicios del asset",
    description="Lista todos los servicios detectados en el asset",
)
async def get_asset_services(
    asset_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    state: str | None = Query(default=None, description="Filtrar por estado (open, closed, filtered)"),
    protocol: str | None = Query(default=None, description="Filtrar por protocolo (tcp, udp)"),
):
    """
    Lista los servicios de un asset.
    
    Filtros:
    - state: open, closed, filtered
    - protocol: tcp, udp
    """
    # Verificar que el asset existe y pertenece a la organización
    asset = await get_asset_or_404(db, asset_id, current_user.organization_id)
    
    # Query de servicios
    stmt = select(Service).where(Service.asset_id == asset_id)
    
    if state:
        stmt = stmt.where(Service.state == state)
    
    if protocol:
        stmt = stmt.where(Service.protocol == protocol.lower())
    
    stmt = stmt.order_by(Service.port.asc())
    
    result = await db.execute(stmt)
    services = result.scalars().all()
    
    return [ServiceRead.model_validate(s) for s in services]


# =============================================================================
# Get Asset Stats
# =============================================================================
@router.get(
    "/{asset_id}/stats",
    response_model=AssetVulnerabilityStats,
    summary="Estadísticas del asset",
    description="Obtiene estadísticas de vulnerabilidades del asset",
)
async def get_asset_stats(
    asset_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene estadísticas de vulnerabilidades de un asset.
    """
    asset = await get_asset_or_404(db, asset_id, current_user.organization_id)
    
    return AssetVulnerabilityStats(
        asset_id=asset.id,
        critical=asset.vuln_critical_count,
        high=asset.vuln_high_count,
        medium=asset.vuln_medium_count,
        low=asset.vuln_low_count,
        total=(
            asset.vuln_critical_count +
            asset.vuln_high_count +
            asset.vuln_medium_count +
            asset.vuln_low_count
        ),
        risk_score=asset.risk_score,
    )


# =============================================================================
# Scan Asset
# =============================================================================
@router.post(
    "/{asset_id}/scan",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escanear asset",
    description="Inicia un escaneo de puertos y servicios en el asset",
)
async def scan_asset(
    asset_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    scan_type: str = Query(default="quick", description="Tipo de escaneo: quick, full, custom"),
):
    """
    Inicia un escaneo del asset.
    
    Tipos de escaneo:
    - quick: Top 100 puertos (-F)
    - full: Todos los puertos (1-65535)
    - custom: Configuración personalizada
    
    El escaneo se ejecuta en background con Celery.
    """
    # Verificar que el asset existe
    asset = await get_asset_or_404(db, asset_id, current_user.organization_id)
    
    # Validar tipo de escaneo
    valid_types = {"quick", "full", "custom"}
    if scan_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de escaneo inválido. Debe ser: {valid_types}",
        )
    
    # TODO: Enviar tarea a Celery
    # from app.workers.nmap_worker import port_scan
    # task = port_scan.delay(asset_id, scan_type)
    
    return MessageResponse(
        message=f"Escaneo {scan_type} iniciado para {asset.ip_address}",
        # task_id=task.id  # Cuando Celery esté configurado
    )


# =============================================================================
# Get Assets Summary
# =============================================================================
@router.get(
    "/summary/all",
    response_model=list[AssetSummary],
    summary="Resumen de assets",
    description="Obtiene un resumen de todos los assets para dashboards",
)
async def get_assets_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    limit: int = Query(default=10, ge=1, le=100, description="Número de assets"),
    order_by: str = Query(default="risk_score", description="risk_score o critical_vulnerabilities"),
):
    """
    Obtiene resumen de assets ordenados por riesgo.
    
    Útil para dashboards que muestran "Top 10 assets más riesgosos".
    """
    stmt = select(Asset).where(Asset.organization_id == current_user.organization_id)
    
    if order_by == "critical_vulnerabilities":
        stmt = stmt.order_by(Asset.vuln_critical_count.desc())
    else:
        stmt = stmt.order_by(Asset.risk_score.desc())
    
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    assets = result.scalars().all()
    
    return [
        AssetSummary(
            id=a.id,
            ip_address=a.ip_address,
            hostname=a.hostname,
            criticality=a.criticality,
            risk_score=a.risk_score,
            total_vulnerabilities=(
                a.vuln_critical_count + a.vuln_high_count +
                a.vuln_medium_count + a.vuln_low_count
            ),
            critical_vulnerabilities=a.vuln_critical_count,
        )
        for a in assets
    ]
