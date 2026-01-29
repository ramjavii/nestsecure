#!/bin/bash
# =============================================================================
# NESTSECURE - Script de Prueba Manual de Autenticación JWT
# =============================================================================
# Este script demuestra cómo probar manualmente los endpoints de auth

set -e

API_URL="http://localhost:8000/api/v1"
RESET="\033[0m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
RED="\033[0;31m"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BLUE}  NESTSECURE - Prueba Manual de Autenticación JWT${RESET}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# =============================================================================
# 1. Verificar que el API está corriendo
# =============================================================================
echo -e "${YELLOW}1. Verificando que el API está corriendo...${RESET}"
if curl -s -f "${API_URL%/api/v1}/health" > /dev/null; then
    echo -e "${GREEN}✓ API está corriendo en http://localhost:8000${RESET}"
else
    echo -e "${RED}✗ API no está respondiendo. Ejecuta 'make docker-up'${RESET}"
    exit 1
fi
echo ""

# =============================================================================
# 2. Crear usuario de prueba (via Python)
# =============================================================================
echo -e "${YELLOW}2. Creando usuario de prueba...${RESET}"
echo -e "${BLUE}   (Usando script Python para crear directamente en BD)${RESET}"

python3 << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/Users/fabianramos/Desktop/NESTSECURE/backend')

from sqlalchemy import select
from app.db.session import get_db_engine, get_async_session_maker
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def create_test_user():
    engine = get_db_engine()
    session_maker = get_async_session_maker(engine)
    
    async with session_maker() as session:
        # Verificar si existe la organización
        stmt = select(Organization).where(Organization.slug == "demo-org")
        result = await session.execute(stmt)
        org = result.scalar_one_or_none()
        
        if not org:
            org = Organization(
                name="Demo Organization",
                slug="demo-org",
                description="Organización de prueba",
                max_assets=100,
                is_active=True,
            )
            session.add(org)
            await session.commit()
            await session.refresh(org)
            print(f"  ✓ Organización creada: {org.name}")
        else:
            print(f"  ✓ Organización existe: {org.name}")
        
        # Verificar si existe el usuario
        stmt = select(User).where(User.email == "demo@nestsecure.com")
        result = await session.execute(stmt)
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
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"  ✓ Usuario creado: {user.email}")
        else:
            print(f"  ✓ Usuario existe: {user.email}")
        
        print(f"\n  📧 Email: demo@nestsecure.com")
        print(f"  🔑 Password: Demo123456!")
        print(f"  👤 Rol: {user.role}")
    
    await engine.dispose()

asyncio.run(create_test_user())
EOF

echo ""

# =============================================================================
# 3. Login con OAuth2 Form (para aplicaciones de terceros)
# =============================================================================
echo -e "${YELLOW}3. Test: Login con OAuth2 Form${RESET}"
echo -e "${BLUE}   POST /api/v1/auth/login (Content-Type: form-urlencoded)${RESET}"

RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo@nestsecure.com&password=Demo123456!")

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ Login exitoso${RESET}"
    ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
    REFRESH_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['refresh_token'])")
    echo -e "${GREEN}  → Access Token obtenido (primeros 50 chars): ${ACCESS_TOKEN:0:50}...${RESET}"
else
    echo -e "${RED}✗ Login falló${RESET}"
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
fi
echo ""

# =============================================================================
# 4. Login con JSON (para aplicaciones modernas)
# =============================================================================
echo -e "${YELLOW}4. Test: Login con JSON${RESET}"
echo -e "${BLUE}   POST /api/v1/auth/login/json${RESET}"

RESPONSE=$(curl -s -X POST "${API_URL}/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@nestsecure.com",
    "password": "Demo123456!"
  }')

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ Login JSON exitoso${RESET}"
    echo "$RESPONSE" | python3 -m json.tool | head -20
else
    echo -e "${RED}✗ Login JSON falló${RESET}"
    echo "$RESPONSE" | python3 -m json.tool
fi
echo ""

# =============================================================================
# 5. Usar el token para acceder a endpoint protegido
# =============================================================================
echo -e "${YELLOW}5. Test: Acceso a endpoint protegido con JWT${RESET}"
echo -e "${BLUE}   GET /api/v1/auth/me (con Authorization: Bearer token)${RESET}"

RESPONSE=$(curl -s -X GET "${API_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

if echo "$RESPONSE" | grep -q "email"; then
    echo -e "${GREEN}✓ Token válido, datos del usuario obtenidos${RESET}"
    echo "$RESPONSE" | python3 -m json.tool
else
    echo -e "${RED}✗ Token inválido o endpoint falló${RESET}"
    echo "$RESPONSE"
fi
echo ""

# =============================================================================
# 6. Intentar acceso sin token (debe fallar con 401)
# =============================================================================
echo -e "${YELLOW}6. Test: Acceso sin token (debe fallar)${RESET}"
echo -e "${BLUE}   GET /api/v1/auth/me (sin Authorization header)${RESET}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/auth/me")

if [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✓ Correctamente rechazado con 401 Unauthorized${RESET}"
else
    echo -e "${RED}✗ Código inesperado: ${HTTP_CODE} (esperaba 401)${RESET}"
fi
echo ""

# =============================================================================
# 7. Intentar con token inválido (debe fallar con 401)
# =============================================================================
echo -e "${YELLOW}7. Test: Token inválido (debe fallar)${RESET}"
echo -e "${BLUE}   GET /api/v1/auth/me (con token falso)${RESET}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/auth/me" \
  -H "Authorization: Bearer token_invalido_fake_123")

if [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✓ Token inválido correctamente rechazado con 401${RESET}"
else
    echo -e "${RED}✗ Código inesperado: ${HTTP_CODE} (esperaba 401)${RESET}"
fi
echo ""

# =============================================================================
# 8. Listar usuarios (requiere estar autenticado)
# =============================================================================
echo -e "${YELLOW}8. Test: Listar usuarios de mi organización${RESET}"
echo -e "${BLUE}   GET /api/v1/users (con JWT)${RESET}"

RESPONSE=$(curl -s -X GET "${API_URL}/users?page=1&page_size=10" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

if echo "$RESPONSE" | grep -q "items"; then
    echo -e "${GREEN}✓ Lista de usuarios obtenida${RESET}"
    TOTAL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])")
    echo -e "${GREEN}  → Total de usuarios en organización: ${TOTAL}${RESET}"
else
    echo -e "${RED}✗ No se pudo obtener lista de usuarios${RESET}"
fi
echo ""

# =============================================================================
# 9. Refresh token (renovar access token)
# =============================================================================
echo -e "${YELLOW}9. Test: Renovar access token con refresh token${RESET}"
echo -e "${BLUE}   POST /api/v1/auth/refresh${RESET}"

RESPONSE=$(curl -s -X POST "${API_URL}/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"${REFRESH_TOKEN}\"}")

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ Access token renovado exitosamente${RESET}"
    NEW_ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
    echo -e "${GREEN}  → Nuevo token (primeros 50 chars): ${NEW_ACCESS_TOKEN:0:50}...${RESET}"
else
    echo -e "${RED}✗ Refresh falló${RESET}"
    echo "$RESPONSE" | python3 -m json.tool
fi
echo ""

# =============================================================================
# 10. Decodificar JWT para ver el contenido
# =============================================================================
echo -e "${YELLOW}10. Bonus: Decodificar JWT (sin verificar firma)${RESET}"
echo -e "${BLUE}    Para ver el contenido del token${RESET}"

# Extraer payload del JWT (segunda parte entre los puntos)
PAYLOAD=$(echo "$ACCESS_TOKEN" | cut -d. -f2)
# Añadir padding si es necesario
while [ $((${#PAYLOAD} % 4)) -ne 0 ]; do
    PAYLOAD="${PAYLOAD}="
done

echo "$PAYLOAD" | base64 -d 2>/dev/null | python3 -m json.tool || echo -e "${YELLOW}   (El payload está en formato JWT estándar)${RESET}"
echo ""

# =============================================================================
# Resumen Final
# =============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}✓ Todas las pruebas de autenticación completadas${RESET}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "${YELLOW}📝 Comandos útiles para seguir probando:${RESET}"
echo ""
echo -e "  # Login y guardar token"
echo -e "  ${GREEN}TOKEN=\$(curl -s -X POST http://localhost:8000/api/v1/auth/login/json \\${RESET}"
echo -e "    ${GREEN}-H 'Content-Type: application/json' \\${RESET}"
echo -e "    ${GREEN}-d '{\"email\":\"demo@nestsecure.com\",\"password\":\"Demo123456!\"}' \\${RESET}"
echo -e "    ${GREEN}| python3 -c 'import sys,json; print(json.load(sys.stdin)[\"access_token\"])')${RESET}"
echo ""
echo -e "  # Usar token en cualquier endpoint"
echo -e "  ${GREEN}curl -H \"Authorization: Bearer \$TOKEN\" http://localhost:8000/api/v1/users${RESET}"
echo ""
echo -e "  # Ver documentación interactiva"
echo -e "  ${GREEN}open http://localhost:8000/docs${RESET}"
echo ""
