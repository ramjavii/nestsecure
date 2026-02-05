docker compose up -d
docker compose logs -f  # Ver logs en tiempo real# 🧪 GUÍA DE TESTING MANUAL - NESTSECURE

## 📋 ÍNDICE
1. [Apagar Todo](#1-apagar-todo)
2. [Iniciar el Sistema](#2-iniciar-el-sistema)
3. [Verificar que Todo Está Corriendo](#3-verificar-que-todo-está-corriendo)
4. [Login y Crear Scans](#4-login-y-crear-scans)
5. [Ver Progreso Real de Scans](#5-ver-progreso-real-de-scans)
6. [Verificar Workers y Celery](#6-verificar-workers-y-celery)
7. [Ver si Nmap se Ejecutó](#7-ver-si-nmap-se-ejecutó)
8. [Ver Vulnerabilidades y CVEs](#8-ver-vulnerabilidades-y-cves)
9. [Logs Útiles](#9-logs-útiles)

---

## 1. APAGAR TODO

### Opción A: Apagar con Docker Compose (Recomendado)
```bash
cd /Users/fabianramos/Desktop/NESTSECURE

# Apagar todos los contenedores
docker compose down

# Si quieres borrar también los volúmenes (datos):
docker compose down -v

# Verificar que todo está apagado
docker ps
```

### Opción B: Apagar procesos individuales
```bash
# Apagar frontend Next.js
pkill -f "next dev"
# o buscar el proceso
lsof -i :3000
kill -9 <PID>

# Apagar backend uvicorn
pkill -f "uvicorn"
lsof -i :8000
kill -9 <PID>

# Apagar Celery worker
pkill -f "celery"

# Apagar Redis (si corre local)
pkill -f "redis-server"

# Apagar PostgreSQL (si corre local)
brew services stop postgresql
```

---

## 2. INICIAR EL SISTEMA

### Paso 1: Iniciar con Docker Compose
```bash
cd /Users/fabianramos/Desktop/NESTSECURE

# Iniciar todos los servicios
docker compose up -d

# Ver los contenedores corriendo
docker compose ps
```

### Servicios que deberían estar corriendo:
| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| frontend | 3000 | Next.js UI |
| backend | 8000 | FastAPI API |
| db | 5432 | PostgreSQL |
| redis | 6379 | Cache/Cola |
| celery_worker | - | Worker de tareas |
| celery_beat | - | Scheduler |

### Paso 2: Verificar logs iniciales
```bash
# Ver logs de todos los servicios
docker compose logs -f

# Ver logs solo del backend
docker compose logs -f backend

# Ver logs solo del worker
docker compose logs -f celery_worker
```

---

## 3. VERIFICAR QUE TODO ESTÁ CORRIENDO

### Health Checks:
```bash
# Backend API
curl http://localhost:8000/health
# Respuesta esperada: {"status": "healthy", ...}

# Frontend
curl -I http://localhost:3000
# Respuesta esperada: HTTP/1.1 200 OK

# Redis
docker compose exec redis redis-cli ping
# Respuesta esperada: PONG

# PostgreSQL
docker compose exec db psql -U nestsecure -d nestsecure -c "SELECT 1"
# Respuesta esperada: 1
```

### Ver estado de Celery:
```bash
# Inspeccionar workers activos
docker compose exec celery_worker celery -A app.celery_app inspect active

# Ver colas
docker compose exec celery_worker celery -A app.celery_app inspect reserved

# Ver estadísticas
docker compose exec celery_worker celery -A app.celery_app inspect stats
```

---

## 4. LOGIN Y CREAR SCANS

### 4.1 Acceder al Frontend
1. Abrir navegador: **http://localhost:3000**
2. Login con credenciales:
   - Email: `admin@nestsecure.com`
   - Password: `Admin123!`

### 4.2 Crear un Scan desde la UI
1. Ir a **Scans** en el menú lateral
2. Click en **"Nuevo Scan"** o **"+ New Scan"**
3. Llenar el formulario:
   - **Nombre**: Test Scan Manual
   - **Tipo**: Vulnerability (OpenVAS) o Nmap
   - **Targets**: `192.168.1.0/24` o una IP específica
4. Click en **"Crear"** o **"Start Scan"**

### 4.3 Crear Scan via API (curl)
```bash
# Primero obtener token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@nestsecure.com&password=Admin123!" \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# Crear scan Nmap
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Nmap Scan",
    "scan_type": "discovery",
    "targets": ["192.168.1.1", "192.168.1.0/24"]
  }'

# Crear scan Nuclei
curl -X POST http://localhost:8000/api/v1/nuclei \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Nuclei Scan",
    "target": "https://example.com",
    "profile": "standard"
  }'
```

---

## 5. VER PROGRESO REAL DE SCANS

### 5.1 Desde la UI
1. Ir a **Scans** → Click en el scan creado
2. Ver el panel de **Progreso** con:
   - Estado: pending → running → completed
   - Porcentaje de progreso
   - Fase actual
   - Tiempo transcurrido

### 5.2 Via API
```bash
# Obtener estado de un scan específico
SCAN_ID="<uuid-del-scan>"

curl -X GET "http://localhost:8000/api/v1/scans/$SCAN_ID" \
  -H "Authorization: Bearer $TOKEN" | jq

# Ver estado rápido
curl -X GET "http://localhost:8000/api/v1/scans/$SCAN_ID/status" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 5.3 Ver resultados cuando complete
```bash
curl -X GET "http://localhost:8000/api/v1/scans/$SCAN_ID/results" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 6. VERIFICAR WORKERS Y CELERY

### 6.1 Ver tareas en tiempo real
```bash
# Terminal 1: Ver logs del worker
docker compose logs -f celery_worker

# Deberías ver mensajes como:
# [2024-01-15 10:00:00,000: INFO/MainProcess] Task app.workers.nmap_worker.run_nmap_scan[abc123] received
# [2024-01-15 10:00:05,000: INFO/ForkPoolWorker-1] Starting nmap scan on 192.168.1.0/24
# [2024-01-15 10:01:00,000: INFO/ForkPoolWorker-1] Nmap scan completed, found 10 hosts
```

### 6.2 Monitorear colas de Celery
```bash
# Ver tareas activas
docker compose exec celery_worker celery -A app.celery_app inspect active

# Ver tareas reservadas (en cola)
docker compose exec celery_worker celery -A app.celery_app inspect reserved

# Ver tareas programadas
docker compose exec celery_worker celery -A app.celery_app inspect scheduled
```

### 6.3 Ver eventos de Celery en tiempo real
```bash
# En una terminal separada
docker compose exec celery_worker celery -A app.celery_app events

# O con más detalle
docker compose exec celery_worker celery -A app.celery_app events --dump
```

### 6.4 Usar Flower (Monitor Web de Celery)
```bash
# Si tienes Flower configurado, acceder a:
# http://localhost:5555

# Si no está, puedes iniciarlo:
docker compose exec celery_worker celery -A app.celery_app flower --port=5555
```

---

## 7. VER SI NMAP SE EJECUTÓ

### 7.1 Ver logs específicos de Nmap
```bash
# Buscar en logs del worker
docker compose logs celery_worker 2>&1 | grep -i nmap

# Ver ejecución en tiempo real
docker compose logs -f celery_worker 2>&1 | grep -i "nmap\|scan\|host"
```

### 7.2 Verificar resultados en base de datos
```bash
# Conectar a PostgreSQL
docker compose exec db psql -U nestsecure -d nestsecure

# Ver scans
SELECT id, name, scan_type, status, progress, total_hosts_scanned, total_hosts_up 
FROM scans 
ORDER BY created_at DESC 
LIMIT 5;

# Ver servicios descubiertos
SELECT a.ip_address, s.port, s.protocol, s.name, s.version 
FROM services s 
JOIN assets a ON s.asset_id = a.id 
ORDER BY s.created_at DESC 
LIMIT 20;

# Salir
\q
```

### 7.3 Ver archivos de salida de Nmap
```bash
# Los resultados de nmap se guardan en el worker
docker compose exec celery_worker ls -la /tmp/nmap_results/

# Ver contenido de un resultado
docker compose exec celery_worker cat /tmp/nmap_results/<scan_id>.xml
```

### 7.4 Ejecutar Nmap manualmente para verificar
```bash
# Ejecutar nmap directo desde el worker
docker compose exec celery_worker nmap -sV -sC -T4 192.168.1.1

# Si nmap no está instalado en el worker, verificar:
docker compose exec celery_worker which nmap
docker compose exec celery_worker nmap --version
```

---

## 8. VER VULNERABILIDADES Y CVES

### 8.1 Ver vulnerabilidades detectadas
```bash
# Via API
curl -X GET "http://localhost:8000/api/v1/scans/$SCAN_ID/results" \
  -H "Authorization: Bearer $TOKEN" | jq '.vulnerabilities'

# O todas las vulnerabilidades del dashboard
curl -X GET "http://localhost:8000/api/v1/dashboard/stats" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 8.2 Ver asociación de CVEs a servicios
```bash
# En PostgreSQL
docker compose exec db psql -U nestsecure -d nestsecure

# Ver vulnerabilidades con sus CVEs
SELECT 
    v.name,
    v.severity,
    v.cve_id,
    v.cvss_score,
    a.ip_address as host,
    s.port,
    s.name as service
FROM vulnerabilities v
LEFT JOIN assets a ON v.asset_id = a.id
LEFT JOIN services s ON v.service_id = s.id
ORDER BY v.severity DESC, v.created_at DESC
LIMIT 20;

# Ver caché de CVEs
SELECT cve_id, severity, cvss_score, description 
FROM cve_cache 
ORDER BY updated_at DESC 
LIMIT 10;

\q
```

### 8.3 Verificar llamadas a NVD/CVE API
```bash
# Ver logs de requests a NVD
docker compose logs backend 2>&1 | grep -i "nvd\|cve\|nist"

# Ver logs del worker para CVE enrichment
docker compose logs celery_worker 2>&1 | grep -i "cve\|enrich\|nvd"
```

### 8.4 Desde la UI
1. Ir a **Dashboard** → Ver cards de vulnerabilidades por severidad
2. Ir a **Vulnerabilities** → Ver lista completa con CVEs asociados
3. Click en una vulnerabilidad → Ver detalles con:
   - CVE ID
   - CVSS Score
   - Descripción
   - Referencias
   - Asset/Servicio afectado

---

## 9. LOGS ÚTILES

### Ver todos los logs juntos
```bash
docker compose logs -f --tail=100
```

### Logs específicos por servicio
```bash
# Backend API (requests, errors)
docker compose logs -f backend

# Worker (scans, tasks)
docker compose logs -f celery_worker

# Base de datos
docker compose logs -f db

# Redis
docker compose logs -f redis
```

### Filtrar logs por tipo
```bash
# Solo errores
docker compose logs backend 2>&1 | grep -i "error\|exception\|failed"

# Solo scans
docker compose logs celery_worker 2>&1 | grep -i "scan"

# Solo vulnerabilidades
docker compose logs 2>&1 | grep -i "vuln\|cve"
```

### Ver logs en archivo
```bash
# Guardar logs para análisis
docker compose logs > /tmp/nestsecure_logs.txt 2>&1

# Ver logs del backend específico
docker compose logs backend > /tmp/backend_logs.txt 2>&1
```

---

## 🔧 TROUBLESHOOTING

### El scan se queda en "pending"
```bash
# Verificar que el worker esté corriendo
docker compose ps celery_worker

# Reiniciar el worker
docker compose restart celery_worker

# Ver si hay errores
docker compose logs celery_worker --tail=50
```

### Nmap no encuentra hosts
```bash
# Verificar conectividad desde el worker
docker compose exec celery_worker ping -c 3 192.168.1.1

# Verificar que nmap puede ejecutarse
docker compose exec celery_worker nmap --version
```

### No se asocian CVEs
```bash
# Verificar configuración de NVD API
docker compose exec backend env | grep NVD

# Ver si hay rate limiting
docker compose logs backend 2>&1 | grep -i "rate\|limit\|429"
```

### Frontend no carga
```bash
# Verificar que el backend responde
curl http://localhost:8000/health

# Reiniciar frontend
docker compose restart frontend
```

---

## 📊 RESUMEN DE COMANDOS RÁPIDOS

```bash
# === APAGAR ===
docker compose down

# === INICIAR ===
docker compose up -d

# === VER LOGS ===
docker compose logs -f

# === ESTADO ===
docker compose ps

# === REINICIAR TODO ===
docker compose down && docker compose up -d

# === LOGIN Y TOKEN ===
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@nestsecure.com&password=Admin123!" | jq -r '.access_token')

# === CREAR SCAN ===
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Mi Scan", "scan_type": "discovery", "targets": ["192.168.1.0/24"]}'

# === VER SCANS ===
curl http://localhost:8000/api/v1/scans -H "Authorization: Bearer $TOKEN" | jq

# === VER WORKER ===
docker compose exec celery_worker celery -A app.celery_app inspect active
```

---

**¡Listo! Con esta guía puedes probar todo el flujo de NestSecure de principio a fin.**
