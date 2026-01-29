# =============================================================================
# NESTSECURE - Dependencies de API
# =============================================================================
"""
Dependencies de FastAPI para autenticación y autorización.

Incluye:
- OAuth2 scheme para JWT
- get_current_user: Obtener usuario del token
- get_current_active_user: Usuario activo requerido
- require_role: Factory para verificar roles
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

settings = get_settings()


# =============================================================================
# OAuth2 Scheme
# =============================================================================
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=True,
)

# Version opcional que no lanza error (para endpoints que aceptan anónimos)
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


# =============================================================================
# Excepciones
# =============================================================================
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)

inactive_user_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Usuario inactivo",
)

permission_denied_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="No tiene permisos para realizar esta acción",
)


# =============================================================================
# Dependencies de Usuario
# =============================================================================
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency para obtener el usuario actual desde el token JWT.
    
    Args:
        token: Token JWT del header Authorization
        db: Sesión de base de datos
    
    Returns:
        Usuario autenticado
    
    Raises:
        HTTPException 401: Si el token es inválido o el usuario no existe
    """
    # Decodificar token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    # Verificar tipo de token
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener user_id del token
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Buscar usuario en la base de datos
    stmt = (
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency para obtener el usuario actual activo.
    
    Args:
        current_user: Usuario del token
    
    Returns:
        Usuario activo
    
    Raises:
        HTTPException 403: Si el usuario está inactivo
    """
    if not current_user.is_active:
        raise inactive_user_exception
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Dependency para obtener el usuario actual si es superusuario.
    
    Args:
        current_user: Usuario activo
    
    Returns:
        Usuario superusuario
    
    Raises:
        HTTPException 403: Si el usuario no es superusuario
    """
    if not current_user.is_superuser:
        raise permission_denied_exception
    return current_user


# =============================================================================
# Factory de Permisos por Rol
# =============================================================================
def require_role(*roles: str):
    """
    Factory para crear dependency que requiere roles específicos.
    
    Args:
        *roles: Roles permitidos (admin, operator, analyst, viewer)
    
    Returns:
        Dependency function
    
    Uso:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: User = Depends(require_role("admin"))
        ):
            ...
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        # Superusuarios tienen todos los permisos
        if current_user.is_superuser:
            return current_user
        
        # Verificar si el rol del usuario está en los roles permitidos
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los siguientes roles: {', '.join(roles)}",
            )
        
        return current_user
    
    return role_checker


def require_permission(permission: str):
    """
    Factory para crear dependency que requiere un permiso específico.
    
    Args:
        permission: Nombre del permiso requerido
    
    Returns:
        Dependency function
    
    Uso:
        @router.delete("/assets/{id}")
        async def delete_asset(
            user: User = Depends(require_permission("assets.delete"))
        ):
            ...
    """
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {permission}",
            )
        
        return current_user
    
    return permission_checker


# =============================================================================
# Type Aliases para uso más limpio
# =============================================================================
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
