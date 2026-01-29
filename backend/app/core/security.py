# =============================================================================
# NESTSECURE - Módulo de Seguridad
# =============================================================================
"""
Utilidades de seguridad para autenticación y autorización.

Incluye:
- Hashing de passwords con bcrypt
- Verificación de passwords
- Generación de tokens JWT (futuro)
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# Contexto de hashing con bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.PASSWORD_HASH_ROUNDS,
)


def get_password_hash(password: str) -> str:
    """
    Genera el hash de una contraseña.
    
    Args:
        password: Contraseña en texto plano
    
    Returns:
        Hash bcrypt de la contraseña
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash.
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash almacenado
    
    Returns:
        True si coinciden, False en caso contrario
    """
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT Token Functions (para Día 3+)
# =============================================================================
def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Crea un token de acceso JWT.
    
    Args:
        subject: ID del usuario u otro identificador
        expires_delta: Tiempo de expiración personalizado
    
    Returns:
        Token JWT codificado
    """
    from jose import jwt
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Crea un token de refresco JWT.
    
    Args:
        subject: ID del usuario
        expires_delta: Tiempo de expiración personalizado
    
    Returns:
        Token JWT de refresco
    """
    from jose import jwt
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """
    Decodifica y valida un token JWT.
    
    Args:
        token: Token JWT a decodificar
    
    Returns:
        Payload del token si es válido, None si no lo es
    """
    from jose import JWTError, jwt
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None
