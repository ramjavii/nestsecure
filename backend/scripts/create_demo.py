#!/usr/bin/env python3
"""Script para crear usuario demo en la base de datos"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import init_db, get_db
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.core.security import get_password_hash


async def create_demo_user():
    """Crear organización y usuario demo"""
    # Inicializar la base de datos
    await init_db()
    
    async for db in get_db():
        # Crear organización
        stmt = select(Organization).where(Organization.slug == 'demo-org')
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        
        if not org:
            org = Organization(
                name='Demo Organization',
                slug='demo-org',
                description='Organización de demostración',
                max_assets=100,
                is_active=True,
            )
            db.add(org)
            await db.commit()
            await db.refresh(org)
            print('✓ Organización creada')
        else:
            print('✓ Organización ya existe')
        
        # Crear usuario
        stmt = select(User).where(User.email == 'admin@nestsecure.com')
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email='admin@nestsecure.com',
                hashed_password=get_password_hash('Admin123!'),
                full_name='Admin Demo',
                organization_id=org.id,
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=False,
            )
            db.add(user)
            await db.commit()
            print('✓ Usuario creado')
        else:
            print('✓ Usuario ya existe')
        
        print('\n' + '='*50)
        print('Usuario demo creado exitosamente')
        print('='*50)
        print('📧 Email: admin@nestsecure.com')
        print('🔑 Password: Admin123!')
        print('👤 Role: ADMIN')
        print('🏢 Organización: Demo Organization')
        print('='*50)
        
        break


if __name__ == '__main__':
    asyncio.run(create_demo_user())
