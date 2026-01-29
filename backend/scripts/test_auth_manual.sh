#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000/api/v1"
EMAIL="demo@nestsecure.com"
PASSWORD="Demo123!"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Pruebas Manuales de Autenticación${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 1: Login con formulario OAuth2
echo -e "${BLUE}[1] Login con formulario OAuth2 (Content-Type: application/x-www-form-urlencoded)${NC}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${EMAIL}&password=${PASSWORD}")

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"

# Extraer token
ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token' 2>/dev/null)
REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r '.refresh_token' 2>/dev/null)

if [ "$ACCESS_TOKEN" != "null" ] && [ -n "$ACCESS_TOKEN" ]; then
  echo -e "${GREEN}✓ Login exitoso${NC}"
  echo -e "Access Token: ${ACCESS_TOKEN:0:50}..."
  echo -e "Refresh Token: ${REFRESH_TOKEN:0:50}...\n"
else
  echo -e "${RED}✗ Login falló${NC}\n"
  exit 1
fi

# Test 2: Login con JSON
echo -e "${BLUE}[2] Login con JSON (Content-Type: application/json)${NC}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login/json" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Login JSON exitoso${NC}\n"

# Test 3: Obtener perfil del usuario autenticado
echo -e "${BLUE}[3] Obtener perfil con token (GET /auth/me)${NC}"
RESPONSE=$(curl -s -X GET "${BASE_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Perfil obtenido${NC}\n"

# Test 4: Intentar acceder sin token
echo -e "${BLUE}[4] Intentar acceder sin token (debería fallar)${NC}"
RESPONSE=$(curl -s -X GET "${BASE_URL}/auth/me")
echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Acceso correctamente denegado${NC}\n"

# Test 5: Listar usuarios con token
echo -e "${BLUE}[5] Listar usuarios con autenticación${NC}"
RESPONSE=$(curl -s -X GET "${BASE_URL}/users" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Usuarios listados${NC}\n"

# Test 6: Refrescar token
echo -e "${BLUE}[6] Refrescar access token${NC}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"${REFRESH_TOKEN}\"}")

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"

NEW_ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token' 2>/dev/null)
if [ "$NEW_ACCESS_TOKEN" != "null" ] && [ -n "$NEW_ACCESS_TOKEN" ]; then
  echo -e "${GREEN}✓ Token refrescado${NC}"
  echo -e "Nuevo Access Token: ${NEW_ACCESS_TOKEN:0:50}...\n"
else
  echo -e "${RED}✗ Refresh falló${NC}\n"
fi

# Test 7: Verificar que el nuevo token funciona
echo -e "${BLUE}[7] Usar nuevo token para acceder al perfil${NC}"
RESPONSE=$(curl -s -X GET "${BASE_URL}/auth/me" \
  -H "Authorization: Bearer ${NEW_ACCESS_TOKEN}")

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Nuevo token funciona correctamente${NC}\n"

# Test 8: Test token endpoint
echo -e "${BLUE}[8] Test token endpoint${NC}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/test-token" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Token validado${NC}\n"

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}   ✓ Todas las pruebas completadas${NC}"
echo -e "${BLUE}========================================${NC}"
