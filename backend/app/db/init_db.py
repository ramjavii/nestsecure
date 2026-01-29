# =============================================================================
# NESTSECURE - Inicialización de Base de Datos
# =============================================================================
"""
Scripts de inicialización y seed de la base de datos.

Este módulo maneja:
- Creación de tablas iniciales
- Seed de datos por defecto
- Creación del primer superusuario
"""

import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session_maker

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_first_superuser(session: AsyncSession) -> None:
    """
    Crea el primer superusuario si no existe.
    
    Usa las credenciales definidas en la configuración:
    - FIRST_SUPERUSER_EMAIL
    - FIRST_SUPERUSER_PASSWORD
    """
    from app.models.user import User
    from app.core.security import get_password_hash
    from sqlalchemy import select
    
    # Verificar si ya existe
    result = await session.execute(
        select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.info(f"Superusuario {settings.FIRST_SUPERUSER_EMAIL} ya existe")
        return
    
    # Primero necesitamos una organización por defecto
    from app.models.organization import Organization
    
    result = await session.execute(
        select(Organization).where(Organization.slug == "default")
    )
    default_org = result.scalar_one_or_none()
    
    if not default_org:
        default_org = Organization(
            name="Default Organization",
            slug="default",
            is_active=True,
        )
        session.add(default_org)
        await session.flush()
        logger.info("Organización por defecto creada")
    
    # Crear superusuario
    superuser = User(
        email=settings.FIRST_SUPERUSER_EMAIL,
        hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
        full_name="System Administrator",
        role="admin",
        organization_id=default_org.id,
        is_active=True,
        is_superuser=True,
    )
    session.add(superuser)
    await session.commit()
    
    logger.info(f"✅ Superusuario creado: {settings.FIRST_SUPERUSER_EMAIL}")


async def init_db_data() -> None:
    """
    Inicializa datos por defecto en la base de datos.
    
    Llamar después de aplicar migraciones.
    """
    session_maker = await get_session_maker()
    
    async with session_maker() as session:
        try:
            await create_first_superuser(session)
        except Exception as e:
            logger.error(f"Error inicializando datos: {e}")
            await session.rollback()
            raise


async def check_db_tables() -> dict[str, bool]:
    """
    Verifica qué tablas existen en la base de datos.
    
    Returns:
        Dict con nombre de tabla y si existe
    """
    from app.db.session import get_engine
    
    engine = get_engine()
    expected_tables = [
        "organizations",
        "users", 
        "assets",
        "services",
        "scans",
        "vulnerabilities",
    ]
    
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
        )
        existing = {row[0] for row in result.fetchall()}
    
    return {table: table in existing for table in expected_tables}
