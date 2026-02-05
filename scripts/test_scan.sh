#!/bin/bash
# Script para probar que los scans funcionan

echo "=== Verificando servicios ==="
echo ""

# 1. Health check
echo "1. Health check del backend:"
curl -s http://localhost:8000/health
echo ""
echo ""

# 2. Login para obtener token
echo "2. Obteniendo token de autenticación..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo@nestsecure.com&password=Demo123!" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "ERROR: No se pudo obtener token. Verifica las credenciales."
  echo "Intentando con admin..."
  TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin@nestsecure.com&password=Admin123!" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
fi

if [ -z "$TOKEN" ]; then
  echo "ERROR: No se pudo obtener token con ninguna credencial."
  echo "Puede que necesites crear el usuario demo primero:"
  echo "  docker exec nestsecure_backend_dev python3 /app/scripts/create_demo.py"
  exit 1
fi

echo "Token obtenido: ${TOKEN:0:30}..."
echo ""

# 3. Crear un scan de prueba
echo "3. Creando scan de prueba (Nmap discovery en localhost)..."
SCAN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Scan Manual", "scan_type": "discovery", "targets": ["127.0.0.1"]}')

echo "Respuesta: $SCAN_RESPONSE"
echo ""

# 4. Extraer scan_id
SCAN_ID=$(echo $SCAN_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -z "$SCAN_ID" ]; then
  echo "ERROR: No se pudo crear el scan."
  exit 1
fi

echo "Scan ID: $SCAN_ID"
echo ""

# 5. Verificar estado del scan
echo "4. Estado del scan:"
curl -s "http://localhost:8000/api/v1/scans/$SCAN_ID/status" \
  -H "Authorization: Bearer $TOKEN"
echo ""
echo ""

echo "=== Para monitorear el scan ==="
echo "Ejecuta en otra terminal:"
echo "  docker compose -f docker-compose.dev.yml logs -f celery_worker"
echo ""
echo "Para ver el estado del scan:"
echo "  curl -s http://localhost:8000/api/v1/scans/$SCAN_ID/status -H 'Authorization: Bearer $TOKEN'"
