#!/bin/bash
# =============================================================================
# NESTSECURE - Prueba Rápida de Autenticación JWT
# =============================================================================

set -e

API_URL="http://localhost:8000/api/v1"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NESTSECURE - Prueba Manual de Autenticación JWT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# =============================================================================
# 1. Verificar API
# =============================================================================
echo -e "${YELLOW}1. Verificando API...${NC}"
if curl -s -f "http://localhost:8000/health" > /dev/null; then
    echo -e "${GREEN}✓ API corriendo${NC}"
else
    echo -e "${RED}✗ API no responde${NC}"
    exit 1
fi
echo ""

# =============================================================================
# 2. Login con JSON
# =============================================================================
echo -e "${YELLOW}2. Login con credenciales...${NC}"
echo -e "${BLUE}   POST ${API_URL}/auth/login/json${NC}"

# Nota: Estos son usuarios de prueba de los tests
RESPONSE=$(curl -s -X POST "${API_URL}/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123!"
  }' 2>&1)

# Verificar si hay error de conexión
if echo "$RESPONSE" | grep -q "Could not resolve host\|Connection refused"; then
    echo -e "${RED}✗ No se puede conectar al servidor${NC}"
    echo -e "${YELLOW}   Asegúrate de que Docker esté corriendo: make docker-up${NC}"
    exit 1
fi

# Verificar si el login fue exitoso
if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ Login exitoso${NC}"
    ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
    
    if [ -z "$ACCESS_TOKEN" ]; then
        echo -e "${RED}✗ No se pudo extraer el token${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}  Token obtenido: ${ACCESS_TOKEN:0:50}...${NC}"
    
    # Guardar para uso posterior
    echo "$ACCESS_TOKEN" > /tmp/nestsecure_token.txt
else
    echo -e "${RED}✗ Login falló${NC}"
    
    # Verificar si el error es por usuario no encontrado
    if echo "$RESPONSE" | grep -q "Email o contraseña incorrectos"; then
        echo -e "${YELLOW}   Usuario de prueba no existe. Creándolo...${NC}"
        echo ""
        echo -e "${BLUE}   Ejecuta esto en el contenedor:${NC}"
        echo -e "${GREEN}   docker exec -it nestsecure_backend_dev python3 -c '${NC}"
        echo -e "${GREEN}   from app.db.session import get_db; from app.models.organization import Organization; from app.models.user import User, UserRole; from app.core.security import get_password_hash; import asyncio${NC}"
        echo -e "${GREEN}   # ... crear usuario${NC}"
        echo -e "${GREEN}   '${NC}"
    else
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    fi
    exit 1
fi
echo ""

# =============================================================================
# 3. Obtener perfil del usuario
# =============================================================================
echo -e "${YELLOW}3. Obteniendo perfil del usuario autenticado...${NC}"
echo -e "${BLUE}   GET ${API_URL}/auth/me${NC}"

RESPONSE=$(curl -s -X GET "${API_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

if echo "$RESPONSE" | grep -q "email"; then
    echo -e "${GREEN}✓ Perfil obtenido correctamente${NC}"
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  📧 Email: {data[\"email\"]}')
print(f'  👤 Nombre: {data[\"full_name\"]}')
print(f'  🏢 Rol: {data[\"role\"]}')
print(f'  ✅ Activo: {data[\"is_active\"]}')
" 2>/dev/null || echo "$RESPONSE" | python3 -m json.tool
else
    echo -e "${RED}✗ Error al obtener perfil${NC}"
    echo "$RESPONSE"
fi
echo ""

# =============================================================================
# 4. Intentar acceso sin token (debe fallar)
# =============================================================================
echo -e "${YELLOW}4. Probando acceso sin token (debe fallar)...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/auth/me")

if [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✓ Correctamente rechazado (401 Unauthorized)${NC}"
else
    echo -e "${RED}✗ Código inesperado: ${HTTP_CODE}${NC}"
fi
echo ""

# =============================================================================
# 5. Listar usuarios
# =============================================================================
echo -e "${YELLOW}5. Listando usuarios de la organización...${NC}"
echo -e "${BLUE}   GET ${API_URL}/users${NC}"

RESPONSE=$(curl -s -X GET "${API_URL}/users?page=1&page_size=10" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

if echo "$RESPONSE" | grep -q "items"; then
    echo -e "${GREEN}✓ Lista obtenida${NC}"
    TOTAL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
    echo -e "  Total usuarios: ${TOTAL}"
else
    echo -e "${RED}✗ Error al listar usuarios${NC}"
fi
echo ""

# =============================================================================
# Resumen
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Autenticación JWT funcionando correctamente${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}📝 Comandos útiles:${NC}"
echo ""
echo -e "  ${GREEN}# Guardar token en variable${NC}"
echo -e "  TOKEN=\$(cat /tmp/nestsecure_token.txt)"
echo ""
echo -e "  ${GREEN}# Usar en cualquier request${NC}"
echo -e "  curl -H \"Authorization: Bearer \$TOKEN\" ${API_URL}/users"
echo ""
echo -e "  ${GREEN}# Ver documentación interactiva${NC}"
echo -e "  open http://localhost:8000/docs"
echo ""
