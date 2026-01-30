# =============================================================================
# NESTSECURE - Endpoints de Services
# =============================================================================
"""
Endpoints CRUD para gestión de servicios detectados en assets.

Incluye:
- GET /: Listar servicios con filtros
- GET /{id}: Obtener servicio
- PATCH /{id}: Actualizar servicio
- DELETE /{id}: Eliminar servicio
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentActiveUser, require_role
from app.db.session import get_db
from app.models.asset import Asset
from app.models.service import Service, ServiceProtocol, ServiceState
from app.models.user import UserRole
from app.schemas.common import DeleteResponse, PaginatedResponse
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def get_service_or_404(
    db: AsyncSession,
    service_id: str,
    organization_id: str,
) -> Service:
    """
    Obtiene un servicio por ID verificando pertenencia a la organización.
    
    Args:
        db: Sesión de base de datos
        service_id: ID del servicio
        organization_id: ID de la organización del usuario
    
    Returns:
        Servicio encontrado
    
    Raises:
        HTTPException 404: Si el servicio no existe o no pertenece a la organización
    """
    # Join con Asset para verificar organización
    stmt = (
        select(Service)
        .join(Asset)
        .where(
            and_(
                Service.id == service_id,
                Asset.organization_id == organization_id,
            )
        )
        .options(selectinload(Service.asset))
    )
    
    result = await db.execute(stmt)
    service = result.scalar_one_or_none()
    
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    
    return service


async def verify_asset_ownership(
    db: AsyncSession,
    asset_id: str,
    organization_id: str,
) -> Asset:
    """
    Verifica que un asset pertenezca a la organización.
    
    Raises:
        HTTPException 404: Si el asset no existe o no pertenece a la organización
    """
    stmt = select(Asset).where(
        and_(
            Asset.id == asset_id,
            Asset.organization_id == organization_id,
        )
    )
    
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()
    
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset no encontrado",
        )
    
    return asset


# =============================================================================
# List Services
# =============================================================================
@router.get(
    "",
    response_model=PaginatedResponse[ServiceRead],
    summary="Listar servicios",
    description="Lista todos los servicios de assets en mi organización",
)
async def list_services(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items por página"),
    asset_id: str | None = Query(default=None, description="Filtrar por asset"),
    port: int | None = Query(default=None, ge=1, le=65535, description="Filtrar por puerto"),
    protocol: str | None = Query(default=None, description="Filtrar por protocolo (tcp/udp)"),
    state: str | None = Query(default=None, description="Filtrar por estado (open/closed/filtered)"),
    service_name: str | None = Query(default=None, description="Buscar por nombre de servicio"),
    ssl_enabled: bool | None = Query(default=None, description="Filtrar por SSL"),
):
    """
    Lista servicios con filtros avanzados.
    
    Filtros disponibles:
    - asset_id: Servicios de un asset específico
    - port: Número de puerto exacto
    - protocol: tcp o udp
    - state: open, closed, filtered
    - service_name: Busca parcialmente (ILIKE)
    - ssl_enabled: true/false
    """
    # Base query con join para filtrar por organización
    stmt = (
        select(Service)
        .join(Asset)
        .where(Asset.organization_id == current_user.organization_id)
    )
    
    # Aplicar filtros
    if asset_id:
        # Verificar que el asset pertenece a la organización
        await verify_asset_ownership(db, asset_id, current_user.organization_id)
        stmt = stmt.where(Service.asset_id == asset_id)
    
    if port is not None:
        stmt = stmt.where(Service.port == port)
    
    if protocol:
        protocol_lower = protocol.lower()
        if protocol_lower not in {p.value for p in ServiceProtocol}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Protocolo inválido: {protocol}",
            )
        stmt = stmt.where(Service.protocol == protocol_lower)
    
    if state:
        if state not in {s.value for s in ServiceState}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {state}",
            )
        stmt = stmt.where(Service.state == state)
    
    if service_name:
        stmt = stmt.where(Service.service_name.ilike(f"%{service_name}%"))
    
    if ssl_enabled is not None:
        stmt = stmt.where(Service.ssl_enabled == ssl_enabled)
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Ordenar y paginar
    stmt = stmt.order_by(Service.port.asc())
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    services = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[ServiceRead.model_validate(s) for s in services],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Create Service
# =============================================================================
@router.post(
    "",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear servicio",
    description="Crea un nuevo servicio manualmente",
)
async def create_service(
    service_in: ServiceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Crea un nuevo servicio manualmente.
    
    - El asset debe pertenecer a la organización del usuario
    - Verifica que no exista un servicio con el mismo puerto/protocolo en el asset
    """
    # Verificar que el asset pertenece a la organización
    await verify_asset_ownership(db, service_in.asset_id, current_user.organization_id)
    
    # Verificar duplicado (mismo puerto/protocolo en el asset)
    stmt = select(Service.id).where(
        and_(
            Service.asset_id == service_in.asset_id,
            Service.port == service_in.port,
            Service.protocol == service_in.protocol.lower(),
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un servicio en puerto {service_in.port}/{service_in.protocol} para este asset",
        )
    
    # Crear servicio
    service = Service(
        asset_id=service_in.asset_id,
        port=service_in.port,
        protocol=service_in.protocol.lower(),
        state=service_in.state,
        service_name=service_in.service_name,
        product=service_in.product,
        version=service_in.version,
        banner=service_in.banner,
        ssl_enabled=service_in.ssl_enabled,
        detection_method="manual",
        confidence=100,
    )
    
    db.add(service)
    await db.commit()
    await db.refresh(service)
    
    return ServiceRead.model_validate(service)


# =============================================================================
# Get Service
# =============================================================================
@router.get(
    "/{service_id}",
    response_model=ServiceRead,
    summary="Obtener servicio",
    description="Obtiene un servicio por ID",
)
async def get_service(
    service_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene un servicio específico.
    
    Solo puede ver servicios de assets en su organización.
    """
    service = await get_service_or_404(db, service_id, current_user.organization_id)
    return ServiceRead.model_validate(service)


# =============================================================================
# Update Service
# =============================================================================
@router.patch(
    "/{service_id}",
    response_model=ServiceRead,
    summary="Actualizar servicio",
    description="Actualiza información de un servicio",
)
async def update_service(
    service_id: str,
    service_in: ServiceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Actualiza un servicio existente.
    
    Campos actualizables:
    - state, service_name, product, version
    - banner, ssl_enabled, cpe
    
    NO se puede cambiar: port, protocol, asset_id
    """
    service = await get_service_or_404(db, service_id, current_user.organization_id)
    
    # Actualizar solo campos proporcionados
    update_data = service_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(service, field, value)
    
    await db.commit()
    await db.refresh(service)
    
    return ServiceRead.model_validate(service)


# =============================================================================
# Delete Service
# =============================================================================
@router.delete(
    "/{service_id}",
    response_model=DeleteResponse,
    summary="Eliminar servicio",
    description="Elimina un servicio",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_service(
    service_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Elimina un servicio.
    
    Requiere rol ADMIN.
    """
    service = await get_service_or_404(db, service_id, current_user.organization_id)
    
    await db.delete(service)
    await db.commit()
    
    return DeleteResponse(
        success=True,
        message="Servicio eliminado correctamente",
        deleted_id=service_id,
    )


# =============================================================================
# Get Open Ports Summary
# =============================================================================
@router.get(
    "/summary/ports",
    summary="Resumen de puertos",
    description="Obtiene estadísticas de puertos abiertos en la organización",
)
async def get_ports_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    limit: int = Query(default=20, ge=1, le=100, description="Número de puertos"),
):
    """
    Obtiene los puertos más comunes en la organización.
    
    Útil para dashboards que muestran "Top 20 puertos abiertos".
    """
    stmt = (
        select(
            Service.port,
            Service.service_name,
            func.count(Service.id).label("count"),
        )
        .join(Asset)
        .where(
            and_(
                Asset.organization_id == current_user.organization_id,
                Service.state == ServiceState.OPEN.value,
            )
        )
        .group_by(Service.port, Service.service_name)
        .order_by(func.count(Service.id).desc())
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "port": row.port,
            "service_name": row.service_name,
            "count": row.count,
        }
        for row in rows
    ]
