# =============================================================================
# NESTSECURE - Endpoints de Autenticación
# =============================================================================
"""
Endpoints para autenticación de usuarios.

Incluye:
- POST /login: Login con email/password
- POST /refresh: Refrescar access token
- GET /me: Obtener usuario actual
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentActiveUser, oauth2_scheme
from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthUser,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    Token,
)
from app.schemas.user import UserReadWithOrg

settings = get_settings()

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """
    Autentica un usuario por email y password.
    
    Args:
        db: Sesión de base de datos
        email: Email del usuario
        password: Contraseña en texto plano
    
    Returns:
        Usuario si las credenciales son válidas, None en caso contrario
    """
    stmt = (
        select(User)
        .options(selectinload(User.organization))
        .where(User.email == email)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def create_tokens(user_id: str) -> dict:
    """
    Crea access y refresh tokens para un usuario.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Dict con access_token, refresh_token, token_type, expires_in
    """
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # en segundos
    }


# =============================================================================
# Endpoints
# =============================================================================
@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login de usuario",
    description="Autentica un usuario y retorna tokens JWT",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """
    Autentica un usuario con email y password.
    
    - **username**: Email del usuario (OAuth2 usa 'username' para el campo)
    - **password**: Contraseña del usuario
    
    Returns:
        Tokens JWT y datos del usuario
    """
    # Autenticar usuario
    user = await authenticate_user(db, form_data.username, form_data.password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar que el usuario esté activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    
    # Actualizar último login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    
    # Crear tokens
    tokens = create_tokens(user.id)
    
    # Preparar respuesta
    return LoginResponse(
        **tokens,
        user=AuthUser(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=user.organization_id,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
        ),
    )


@router.post(
    "/login/json",
    response_model=LoginResponse,
    summary="Login de usuario (JSON)",
    description="Autentica un usuario usando JSON body en lugar de form data",
)
async def login_json(
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """
    Autentica un usuario con email y password usando JSON.
    
    Alternativa al endpoint /login para clientes que prefieren JSON.
    """
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    
    tokens = create_tokens(user.id)
    
    return LoginResponse(
        **tokens,
        user=AuthUser(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=user.organization_id,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
        ),
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refrescar token",
    description="Obtiene un nuevo access token usando el refresh token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Refresca el access token usando un refresh token válido.
    
    - **refresh_token**: Token de refresco válido
    
    Returns:
        Nuevos tokens JWT
    """
    # Decodificar refresh token
    payload = decode_token(body.refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar que sea un refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar que el usuario exista y esté activo
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear nuevos tokens
    tokens = create_tokens(user.id)
    
    return Token(**tokens)


@router.get(
    "/me",
    response_model=UserReadWithOrg,
    summary="Obtener usuario actual",
    description="Retorna los datos del usuario autenticado",
)
async def get_me(
    current_user: CurrentActiveUser,
) -> UserReadWithOrg:
    """
    Obtiene los datos del usuario actualmente autenticado.
    
    Requiere token de acceso válido en el header Authorization.
    """
    return UserReadWithOrg.model_validate(current_user)


@router.post(
    "/test-token",
    response_model=AuthUser,
    summary="Test de token",
    description="Verifica que el token sea válido",
)
async def test_token(
    current_user: CurrentActiveUser,
) -> AuthUser:
    """
    Endpoint para verificar que un token es válido.
    
    Útil para debugging y verificación de autenticación.
    """
    return AuthUser(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
    )
