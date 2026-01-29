# =============================================================================
# NESTSECURE - Endpoints de Usuarios
# =============================================================================
"""
Endpoints CRUD para gestión de usuarios.

Incluye:
- GET /: Listar usuarios de mi organización
- POST /: Crear usuario
- GET /{id}: Obtener usuario
- PATCH /{id}: Actualizar usuario
- DELETE /{id}: Eliminar usuario
- PATCH /{id}/password: Cambiar contraseña
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    CurrentActiveUser,
    require_role,
)
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.common import DeleteResponse, MessageResponse, PaginatedResponse
from app.schemas.user import (
    UserCreate,
    UserRead,
    UserReadWithOrg,
    UserUpdate,
    UserUpdatePassword,
)

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def get_user_or_404(
    db: AsyncSession,
    user_id: str,
    organization_id: str | None = None,
) -> User:
    """
    Obtiene un usuario por ID o lanza 404.
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        organization_id: Si se proporciona, verifica que el usuario pertenezca a esta org
    
    Returns:
        Usuario encontrado
    
    Raises:
        HTTPException 404: Si el usuario no existe o no pertenece a la organización
    """
    stmt = (
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == user_id)
    )
    
    if organization_id:
        stmt = stmt.where(User.organization_id == organization_id)
    
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    
    return user


# =============================================================================
# Endpoints
# =============================================================================
@router.get(
    "",
    response_model=PaginatedResponse[UserRead],
    summary="Listar usuarios",
    description="Lista todos los usuarios de mi organización",
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items por página"),
    search: str | None = Query(default=None, description="Buscar por email o nombre"),
    role: str | None = Query(default=None, description="Filtrar por rol"),
    is_active: bool | None = Query(default=None, description="Filtrar por estado activo"),
) -> PaginatedResponse[UserRead]:
    """
    Lista usuarios de la organización del usuario actual.
    
    Superusuarios pueden ver usuarios de todas las organizaciones.
    """
    # Base query - filtrar por organización (excepto superusers)
    stmt = select(User)
    count_stmt = select(func.count(User.id))
    
    if not current_user.is_superuser:
        stmt = stmt.where(User.organization_id == current_user.organization_id)
        count_stmt = count_stmt.where(User.organization_id == current_user.organization_id)
    
    # Aplicar filtros
    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            (User.email.ilike(search_filter)) | 
            (User.full_name.ilike(search_filter))
        )
        count_stmt = count_stmt.where(
            (User.email.ilike(search_filter)) | 
            (User.full_name.ilike(search_filter))
        )
    
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
        count_stmt = count_stmt.where(User.is_active == is_active)
    
    # Contar total
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Paginación y ordenamiento
    offset = (page - 1) * page_size
    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    description="Crea un nuevo usuario en la organización",
)
async def create_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN.value))],
    user_in: UserCreate,
) -> UserRead:
    """
    Crea un nuevo usuario.
    
    - Solo admins pueden crear usuarios
    - Solo superusers pueden crear usuarios en otras organizaciones
    - Solo superusers pueden crear otros superusers
    """
    # Verificar que el usuario no pueda crear en otra organización (a menos que sea superuser)
    if not current_user.is_superuser:
        if user_in.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede crear usuarios en otra organización",
            )
    
    # Verificar que el email no exista
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con este email",
        )
    
    # Crear usuario
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        organization_id=user_in.organization_id,
        is_active=user_in.is_active,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserRead.model_validate(user)


@router.get(
    "/me",
    response_model=UserReadWithOrg,
    summary="Obtener mi perfil",
    description="Retorna los datos del usuario autenticado",
)
async def get_my_profile(
    current_user: CurrentActiveUser,
) -> UserReadWithOrg:
    """
    Obtiene el perfil completo del usuario actual con info de organización.
    """
    return UserReadWithOrg.model_validate(current_user)


@router.get(
    "/{user_id}",
    response_model=UserReadWithOrg,
    summary="Obtener usuario",
    description="Obtiene los datos de un usuario específico",
)
async def get_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
) -> UserReadWithOrg:
    """
    Obtiene un usuario por ID.
    
    - Usuarios solo pueden ver usuarios de su organización
    - Superusuarios pueden ver cualquier usuario
    """
    organization_id = None if current_user.is_superuser else current_user.organization_id
    user = await get_user_or_404(db, user_id, organization_id)
    
    return UserReadWithOrg.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Actualizar usuario",
    description="Actualiza los datos de un usuario",
)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN.value))],
) -> UserRead:
    """
    Actualiza un usuario.
    
    - Solo admins pueden actualizar otros usuarios
    - Solo superusers pueden actualizar usuarios de otras organizaciones
    """
    organization_id = None if current_user.is_superuser else current_user.organization_id
    user = await get_user_or_404(db, user_id, organization_id)
    
    # Aplicar actualizaciones
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}/password",
    response_model=MessageResponse,
    summary="Cambiar contraseña",
    description="Cambia la contraseña de un usuario",
)
async def change_password(
    user_id: str,
    password_in: UserUpdatePassword,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
) -> MessageResponse:
    """
    Cambia la contraseña de un usuario.
    
    - Usuarios pueden cambiar su propia contraseña
    - Admins pueden cambiar la contraseña de usuarios de su organización
    - Superusers pueden cambiar cualquier contraseña
    """
    # Verificar permisos
    is_own_password = current_user.id == user_id
    is_admin_or_super = current_user.is_admin or current_user.is_superuser
    
    if not is_own_password and not is_admin_or_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para cambiar esta contraseña",
        )
    
    # Obtener usuario
    organization_id = None if current_user.is_superuser else current_user.organization_id
    user = await get_user_or_404(db, user_id, organization_id)
    
    # Verificar contraseña actual (solo si es el propio usuario)
    if is_own_password:
        if not verify_password(password_in.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta",
            )
    
    # Actualizar contraseña
    user.hashed_password = get_password_hash(password_in.new_password)
    await db.commit()
    
    return MessageResponse(message="Contraseña actualizada exitosamente")


@router.delete(
    "/{user_id}",
    response_model=DeleteResponse,
    summary="Eliminar usuario",
    description="Elimina un usuario del sistema",
)
async def delete_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN.value))],
) -> DeleteResponse:
    """
    Elimina un usuario.
    
    - Solo admins pueden eliminar usuarios
    - No se puede eliminar a uno mismo
    - Superusers pueden eliminar usuarios de cualquier organización
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminarse a sí mismo",
        )
    
    organization_id = None if current_user.is_superuser else current_user.organization_id
    user = await get_user_or_404(db, user_id, organization_id)
    
    # No permitir eliminar superusuarios (excepto otro superusuario)
    if user.is_superuser and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede eliminar un superusuario",
        )
    
    await db.delete(user)
    await db.commit()
    
    return DeleteResponse(deleted_id=user_id)


@router.patch(
    "/{user_id}/activate",
    response_model=UserRead,
    summary="Activar/Desactivar usuario",
    description="Activa o desactiva un usuario",
)
async def toggle_user_active(
    user_id: str,
    is_active: bool,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN.value))],
) -> UserRead:
    """
    Activa o desactiva un usuario.
    
    - No se puede desactivar a uno mismo
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivarse a sí mismo",
        )
    
    organization_id = None if current_user.is_superuser else current_user.organization_id
    user = await get_user_or_404(db, user_id, organization_id)
    
    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    
    return UserRead.model_validate(user)
