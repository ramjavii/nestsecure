#!/usr/bin/env python
# =============================================================================
# Script para crear datos de demo en la base de datos
# =============================================================================
"""
Crea una organización y usuario de demo para probar la API.

Usuario: demo@nestsecure.com
Password: Demo123!
Rol: admin
"""

import asyncio
import sys
sys.path.insert(0, '/app')

from app.db.session import create_db_engine, create_session_maker
from app.models import User, Organization
from app.core.security import get_password_hash
from sqlalchemy import select


async def create_demo_data():
    """Crea datos de demo si no existen."""
    # Crear engine y session
    engine = create_db_engine()
    session_maker = create_session_maker(engine)
    
    async with session_maker() as session:
        # Check if org exists
        result = await session.execute(
            select(Organization).where(Organization.slug == "demo-org")
        )
        org = result.scalar_one_or_none()
        
        if not org:
            org = Organization(name="Demo Organization", slug="demo-org")
            session.add(org)
            await session.flush()
            print(f"✅ Organization created: {org.id}")
        else:
            print(f"ℹ️  Organization exists: {org.id}")
        
        # Check if user exists
        result = await session.execute(
            select(User).where(User.email == "demo@nestsecure.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email="demo@nestsecure.com",
                hashed_password=get_password_hash("Demo123!"),
                full_name="Demo Admin",
                role="admin",
                organization_id=org.id,
                is_active=True
            )
            session.add(user)
            print("✅ User created: demo@nestsecure.com / Demo123!")
        else:
            print(f"ℹ️  User exists: {user.email}")
        
        await session.commit()
        print("\n🎉 Demo data ready!")
        print("\nCredentials:")
        print("  Email: demo@nestsecure.com")
        print("  Password: Demo123!")


if __name__ == "__main__":
    asyncio.run(create_demo_data())
