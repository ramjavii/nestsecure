#!/usr/bin/env python3
"""
Script para inicializar datos de demostración en NESTSECURE.
Se ejecuta dentro del contenedor Docker con el entorno configurado.
"""
import sys
import asyncio
from pathlib import Path

# Añadir el directorio raíz al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import get_session_maker, init_db
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.core.security import get_password_hash


async def create_demo_data():
    """Crea usuario y organización de demostración."""
    
    # Inicializar DB y obtener session maker
    await init_db()
    session_maker = await get_session_maker()
    
    # Crear sesión async
    async with session_maker() as db:
        try:
            # 1. Crear organización de demo
            stmt = select(Organization).where(Organization.slug == "demo-org")
            result = await db.execute(stmt)
            org = result.scalar_one_or_none()
            
            if not org:
                org = Organization(
                    name="Demo Organization",
                    slug="demo-org",
                    description="Organización de demostración para pruebas",
                    max_assets=100,
                    is_active=True,
                )
                db.add(org)
                await db.commit()
                await db.refresh(org)
                print(f"✅ Organización creada: {org.name} (ID: {org.id})")
            else:
                print(f"ℹ️  Organización existente: {org.name}")
            
            # 2. Crear usuario admin demo
            stmt = select(User).where(User.email == "admin@nestsecure.com")
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    email="admin@nestsecure.com",
                    hashed_password=get_password_hash("Admin123456!"),
                    full_name="Admin Demo",
                    organization_id=org.id,
                    role=UserRole.ADMIN,
                    is_active=True,
                    is_superuser=False,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                print(f"✅ Usuario admin creado: {user.email}")
                print(f"   Email: admin@nestsecure.com")
                print(f"   Password: Admin123456!")
            else:
                print(f"ℹ️  Usuario admin existente: {user.email}")
            
            # 3. Crear usuario operator demo
            stmt = select(User).where(User.email == "operator@nestsecure.com")
            result = await db.execute(stmt)
            user_op = result.scalar_one_or_none()
            
            if not user_op:
                user_op = User(
                    email="operator@nestsecure.com",
                    hashed_password=get_password_hash("Operator123!"),
                    full_name="Operator Demo",
                    organization_id=org.id,
                    role=UserRole.OPERATOR,
                    is_active=True,
                    is_superuser=False,
                )
                db.add(user_op)
                await db.commit()
                await db.refresh(user_op)
                print(f"✅ Usuario operator creado: {user_op.email}")
                print(f"   Email: operator@nestsecure.com")
                print(f"   Password: Operator123!")
            else:
                print(f"ℹ️  Usuario operator existente: {user_op.email}")
            
            print("\n" + "="*60)
            print("🎉 Datos de demostración inicializados correctamente")
            print("="*60)
            print("\n📝 Credenciales disponibles:")
            print("   Admin:    admin@nestsecure.com / Admin123456!")
            print("   Operator: operator@nestsecure.com / Operator123!")
            print("\n🔗 API Docs: http://localhost:8000/docs")
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_demo_data())
