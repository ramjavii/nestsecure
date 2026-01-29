# =============================================================================
# NESTSECURE - Endpoints de Organizaciones
# =============================================================================
"""
Endpoints CRUD para gestión de organizaciones.

Incluye:
- GET /: Listar organizaciones
- POST /: Crear organización (superuser)
- GET /{id}: Obtener organización
- PATCH /{id}: Actualizar organización
- DELETE /{id}: Eliminar organización
- GET /{id}/stats: Estadísticas de la organización
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentActiveUser,
    CurrentSuperuser,
    require_role,
)
from app.db.session import get_db
from app.models.asset import Asset
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.common import DeleteResponse, MessageResponse, PaginatedResponse
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationInDB,
    OrganizationRead,
    OrganizationStats,
    OrganizationUpdate,
)

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def get_organization_or_404(
    db: AsyncSession,
    org_id: str,
) -> Organization:
    """
    Obtiene una organización por ID o lanza 404.
    
    Args:
        db: Sesión de base de datos
        org_id: ID de la organización
    
    Returns:
        Organización encontrada
    
    Raises:
        HTTPException 404: Si la organización no existe
    """
    stmt = select(Organization).where(Organization.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organización no encontrada",
        )
    
    return org


async def get_org_with_counts(
    db: AsyncSession,
    org: Organization,
) -> dict:
    """
    Obtiene una organización con conteos de usuarios y assets.
    """
    # Contar usuarios
    user_count_stmt = select(func.count(User.id)).where(
        User.organization_id == org.id
    )
    user_count_result = await db.execute(user_count_stmt)
    user_count = user_count_result.scalar() or 0
    
    # Contar assets
    asset_count_stmt = select(func.count(Asset.id)).where(
        Asset.organization_id == org.id
    )
    asset_count_result = await db.execute(asset_count_stmt)
    asset_count = asset_count_result.scalar() or 0
    
    return {
        **{c.name: getattr(org, c.name) for c in org.__table__.columns},
        "user_count": user_count,
        "asset_count": asset_count,
    }


# =============================================================================
# Endpoints
# =============================================================================
@router.get(
    "",
    response_model=PaginatedResponse[OrganizationRead],
    summary="Listar organizaciones",
    description="Lista todas las organizaciones (superuser) o solo la propia",
)
async def list_organizations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items por página"),
    search: str | None = Query(default=None, description="Buscar por nombre o slug"),
    is_active: bool | None = Query(default=None, description="Filtrar por estado activo"),
) -> PaginatedResponse[OrganizationRead]:
    """
    Lista organizaciones.
    
    - Superusuarios ven todas las organizaciones
    - Usuarios normales solo ven su propia organización
    """
    # Si no es superusuario, solo puede ver su organización
    if not current_user.is_superuser:
        org = await get_organization_or_404(db, current_user.organization_id)
        org_data = await get_org_with_counts(db, org)
        return PaginatedResponse.create(
            items=[OrganizationRead(**org_data)],
            total=1,
            page=1,
            page_size=page_size,
        )
    
    # Superusuario: listar todas
    stmt = select(Organization)
    count_stmt = select(func.count(Organization.id))
    
    # Aplicar filtros
    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            (Organization.name.ilike(search_filter)) | 
            (Organization.slug.ilike(search_filter))
        )
        count_stmt = count_stmt.where(
            (Organization.name.ilike(search_filter)) | 
            (Organization.slug.ilike(search_filter))
        )
    
    if is_active is not None:
        stmt = stmt.where(Organization.is_active == is_active)
        count_stmt = count_stmt.where(Organization.is_active == is_active)
    
    # Contar total
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Paginación y ordenamiento
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Organization.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    orgs = result.scalars().all()
    
    # Agregar conteos a cada organización
    items = []
    for org in orgs:
        org_data = await get_org_with_counts(db, org)
        items.append(OrganizationRead(**org_data))
    
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear organización",
    description="Crea una nueva organización (solo superusers)",
)
async def create_organization(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentSuperuser,  # Solo superusuarios pueden crear organizaciones
    org_in: OrganizationCreate,
) -> OrganizationRead:
    """
    Crea una nueva organización.
    
    Solo superusuarios pueden crear organizaciones.
    """
    # Verificar que el slug no exista
    stmt = select(Organization).where(Organization.slug == org_in.slug)
    result = await db.execute(stmt)
    existing_org = result.scalar_one_or_none()
    
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una organización con este slug",
        )
    
    # Crear organización
    org = Organization(
        name=org_in.name,
        slug=org_in.slug,
        description=org_in.description,
        max_assets=org_in.max_assets,
        settings=org_in.settings or {},
    )
    
    db.add(org)
    await db.commit()
    await db.refresh(org)
    
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        max_assets=org.max_assets,
        is_active=org.is_active,
        license_expires_at=org.license_expires_at,
        created_at=org.created_at,
        updated_at=org.updated_at,
        user_count=0,
        asset_count=0,
    )


@router.get(
    "/{org_id}",
    response_model=OrganizationInDB,
    summary="Obtener organización",
    description="Obtiene los datos de una organización específica",
)
async def get_organization(
    org_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
) -> OrganizationInDB:
    """
    Obtiene una organización por ID.
    
    - Usuarios solo pueden ver su propia organización
    - Superusuarios pueden ver cualquier organización
    """
    # Verificar permisos
    if not current_user.is_superuser and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver esta organización",
        )
    
    org = await get_organization_or_404(db, org_id)
    org_data = await get_org_with_counts(db, org)
    
    return OrganizationInDB(**org_data)


@router.patch(
    "/{org_id}",
    response_model=OrganizationRead,
    summary="Actualizar organización",
    description="Actualiza los datos de una organización",
)
async def update_organization(
    org_id: str,
    org_in: OrganizationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN.value))],
) -> OrganizationRead:
    """
    Actualiza una organización.
    
    - Admins pueden actualizar su propia organización
    - Superusuarios pueden actualizar cualquier organización
    """
    # Verificar permisos
    if not current_user.is_superuser and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para actualizar esta organización",
        )
    
    org = await get_organization_or_404(db, org_id)
    
    # Aplicar actualizaciones
    update_data = org_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    
    await db.commit()
    await db.refresh(org)
    
    org_data = await get_org_with_counts(db, org)
    return OrganizationRead(**org_data)


@router.delete(
    "/{org_id}",
    response_model=DeleteResponse,
    summary="Eliminar organización",
    description="Elimina una organización (solo superusers)",
)
async def delete_organization(
    org_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentSuperuser,  # Solo superusuarios pueden eliminar
) -> DeleteResponse:
    """
    Elimina una organización.
    
    ⚠️ CUIDADO: Esto eliminará todos los usuarios, assets y datos asociados.
    Solo superusuarios pueden eliminar organizaciones.
    """
    org = await get_organization_or_404(db, org_id)
    
    # Verificar que no sea la organización del superusuario actual
    if current_user.organization_id == org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia organización",
        )
    
    await db.delete(org)
    await db.commit()
    
    return DeleteResponse(deleted_id=org_id)


@router.get(
    "/{org_id}/stats",
    response_model=OrganizationStats,
    summary="Estadísticas de organización",
    description="Obtiene estadísticas detalladas de una organización",
)
async def get_organization_stats(
    org_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
) -> OrganizationStats:
    """
    Obtiene estadísticas de una organización.
    
    Incluye conteos de usuarios, assets, scans y vulnerabilidades.
    """
    # Verificar permisos
    if not current_user.is_superuser and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver esta organización",
        )
    
    # Verificar que existe
    await get_organization_or_404(db, org_id)
    
    # Contar usuarios
    user_count_stmt = select(func.count(User.id)).where(
        User.organization_id == org_id
    )
    user_count_result = await db.execute(user_count_stmt)
    user_count = user_count_result.scalar() or 0
    
    # Contar assets
    asset_count_stmt = select(func.count(Asset.id)).where(
        Asset.organization_id == org_id
    )
    asset_count_result = await db.execute(asset_count_stmt)
    asset_count = asset_count_result.scalar() or 0
    
    # Contar vulnerabilidades por severidad (suma de contadores en assets)
    vuln_stmt = select(
        func.sum(Asset.vuln_critical_count).label("critical"),
        func.sum(Asset.vuln_high_count).label("high"),
    ).where(Asset.organization_id == org_id)
    vuln_result = await db.execute(vuln_stmt)
    vuln_row = vuln_result.first()
    
    critical_vulns = int(vuln_row.critical or 0) if vuln_row else 0
    high_vulns = int(vuln_row.high or 0) if vuln_row else 0
    total_vulns = critical_vulns + high_vulns  # Simplificado, se expandirá con más datos
    
    return OrganizationStats(
        organization_id=org_id,
        user_count=user_count,
        asset_count=asset_count,
        scan_count=0,  # TODO: Implementar cuando exista modelo Scan
        vulnerability_count=total_vulns,
        critical_vulnerabilities=critical_vulns,
        high_vulnerabilities=high_vulns,
    )


@router.patch(
    "/{org_id}/activate",
    response_model=OrganizationRead,
    summary="Activar/Desactivar organización",
    description="Activa o desactiva una organización (solo superusers)",
)
async def toggle_organization_active(
    org_id: str,
    is_active: bool,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentSuperuser,
) -> OrganizationRead:
    """
    Activa o desactiva una organización.
    
    Usuarios de organizaciones desactivadas no podrán hacer login.
    """
    org = await get_organization_or_404(db, org_id)
    
    org.is_active = is_active
    await db.commit()
    await db.refresh(org)
    
    org_data = await get_org_with_counts(db, org)
    return OrganizationRead(**org_data)
