"""
Script para crear usuario de prueba en NESTSECURE
"""
import asyncio
from sqlalchemy import select
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def create_demo_user():
    """Crea usuario y organización de demostración."""
    
    async for db in get_db():
        # 1. Crear organización de demo
        stmt = select(Organization).where(Organization.slug == "demo-org")
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        
        if not org:
            org = Organization(
                name="Demo Organization",
                slug="demo-org",
                description="Organización de demostración",
                max_assets=100,
                is_active=True,
            )
            db.add(org)
            await db.commit()
            await db.refresh(org)
            print(f"✓ Organización creada: {org.name} (ID: {org.id})")
        else:
            print(f"✓ Organización existente: {org.name}")
        
        # 2. Crear usuario demo
        stmt = select(User).where(User.email == "demo@nestsecure.com")
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email="demo@nestsecure.com",
                hashed_password=get_password_hash("Demo123456!"),
                full_name="Demo User",
                organization_id=org.id,
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=False,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"✓ Usuario creado: {user.email}")
        else:
            print(f"✓ Usuario existente: {user.email}")
        
        print("\n" + "="*60)
        print("CREDENCIALES DE PRUEBA:")
        print("="*60)
        print(f"📧 Email:    demo@nestsecure.com")
        print(f"🔑 Password: Demo123456!")
        print(f"👤 Rol:      {user.role}")
        print(f"🏢 Org:      {org.name}")
        print("="*60)
        
        break  # Solo necesitamos una sesión

if __name__ == "__main__":
    asyncio.run(create_demo_user())
