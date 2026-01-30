# =============================================================================
# NESTSECURE - Sesiones de Base de Datos
# =============================================================================
"""
Configuración de SQLAlchemy async para conexión a PostgreSQL.

Este módulo maneja:
- Creación del engine async
- Configuración del session maker
- Dependency injection para FastAPI
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()


# =============================================================================
# Engine Async
# =============================================================================
def create_db_engine(
    database_url: str | None = None,
    echo: bool | None = None,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    pool_pre_ping: bool = True,
) -> AsyncEngine:
    """
    Crea un engine async de SQLAlchemy.
    
    Args:
        database_url: URL de conexión. Si no se proporciona, usa la configuración.
        echo: Si True, loguea todas las queries SQL.
        pool_size: Tamaño del pool de conexiones.
        max_overflow: Conexiones adicionales permitidas.
        pool_pre_ping: Verifica conexiones antes de usarlas.
    
    Returns:
        AsyncEngine configurado
    """
    url = database_url or settings.database_url_async
    
    # Configuración del pool
    pool_settings = {}
    
    # En testing, usar NullPool para evitar problemas con event loops
    if settings.is_testing:
        pool_settings["poolclass"] = NullPool
    else:
        pool_settings.update({
            "pool_size": pool_size or settings.DATABASE_POOL_SIZE,
            "max_overflow": max_overflow or settings.DATABASE_MAX_OVERFLOW,
            "pool_pre_ping": pool_pre_ping,
        })
    
    engine = create_async_engine(
        url,
        echo=echo if echo is not None else settings.DATABASE_ECHO,
        **pool_settings,
    )
    
    return engine


# Engine global de la aplicación
engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """
    Obtiene el engine global de la aplicación.
    
    Raises:
        RuntimeError si el engine no ha sido inicializado.
    """
    global engine
    if engine is None:
        raise RuntimeError(
            "Database engine not initialized. "
            "Call init_db() first during application startup."
        )
    return engine


async def init_db() -> AsyncEngine:
    """
    Inicializa la conexión a la base de datos.
    
    Debe llamarse durante el startup de la aplicación.
    
    Returns:
        AsyncEngine configurado y conectado
    """
    global engine
    engine = create_db_engine()
    return engine


async def close_db() -> None:
    """
    Cierra la conexión a la base de datos.
    
    Debe llamarse durante el shutdown de la aplicación.
    """
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None


# =============================================================================
# Session Maker
# =============================================================================
def create_session_maker(engine_instance: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Crea un session maker configurado.
    
    Args:
        engine_instance: Engine de SQLAlchemy
    
    Returns:
        async_sessionmaker configurado
    """
    return async_sessionmaker(
        bind=engine_instance,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Session maker global (se inicializa después de init_db)
async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Obtiene el session maker global.
    
    Returns:
        async_sessionmaker configurado
    
    Raises:
        RuntimeError si no está inicializado
    """
    global async_session_maker
    if async_session_maker is None:
        current_engine = get_engine()
        async_session_maker = create_session_maker(current_engine)
    return async_session_maker


# =============================================================================
# Dependency Injection
# =============================================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency de FastAPI para obtener una sesión de base de datos.
    
    Uso:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    La sesión se cierra automáticamente al finalizar la request.
    """
    session_factory = await get_session_maker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias para dependency injection más limpia
AsyncSessionDep = Annotated[AsyncSession, Depends(get_db)]


# =============================================================================
# Utilities
# =============================================================================
async def check_db_connection() -> dict:
    """
    Verifica la conexión a la base de datos.
    
    Returns:
        dict con status y latencia
    """
    import time
    from sqlalchemy import text
    
    try:
        current_engine = get_engine()
        start = time.perf_counter()
        
        async with current_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        latency = (time.perf_counter() - start) * 1000
        
        return {
            "status": "up",
            "latency_ms": round(latency, 2),
        }
    except RuntimeError:
        return {
            "status": "not_initialized",
            "message": "Database engine not initialized",
        }
    except Exception as e:
        return {
            "status": "down",
            "error": str(e),
        }


# =============================================================================
# Synchronous Session for Celery Workers
# =============================================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Crear engine síncrono para workers de Celery
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
)

# Session maker síncrono
SessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_sync_db() -> Session:
    """
    Obtiene una sesión síncrona de base de datos.
    
    Útil para workers de Celery que no pueden usar async.
    
    Uso:
        db = get_sync_db()
        try:
            # operaciones
            db.commit()
        finally:
            db.close()
    
    Returns:
        Session síncrona
    """
    return SessionLocal()
