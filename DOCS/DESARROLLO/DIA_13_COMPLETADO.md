# =============================================================================
# NESTSECURE - Día 13: Frontend Docker Deployment
# =============================================================================
# Fecha de Completación: 2026-02-04
# Estado: ✅ COMPLETADO
# Objetivo: Containerizar el frontend Next.js para desarrollo y producción
# =============================================================================

## 📋 Resumen Ejecutivo

El Día 13 se enfocó en containerizar el frontend Next.js 16 para ejecutarse en Docker,
eliminando la dependencia del entorno local (localhost) y preparando el sistema para
deployment en producción.

### 🎯 Objetivos Alcanzados

1. ✅ Dockerfile multi-stage para Next.js 16 con Node.js 20
2. ✅ Integración del frontend en docker-compose.dev.yml
3. ✅ Configuración de variables de entorno para Docker
4. ✅ Health check endpoint para el frontend
5. ✅ Configuración optimizada de Next.js para Turbopack
6. ✅ Scripts de automatización para Docker

---

## 📁 Archivos Creados

### 1. `frontend/Dockerfile` (~110 líneas)

Dockerfile multi-stage optimizado con 5 etapas:

| Etapa | Propósito |
|-------|-----------|
| `base` | Imagen base con dependencias del sistema |
| `deps` | Instalación de node_modules |
| `development` | Entorno de desarrollo con hot-reload |
| `builder` | Compilación para producción |
| `production` | Imagen mínima para producción |

**Características:**
- Node.js 20 Alpine (imagen ligera)
- Usuario no-root para seguridad
- Health checks integrados
- Variables de entorno para Turbopack
- Soporte para polling en Docker (hot-reload)

### 2. `frontend/.dockerignore` (~50 líneas)

Exclusión de archivos innecesarios:
- `node_modules/` (se instala en el contenedor)
- `.next/` (se regenera)
- `.git/`, `.env*`, documentación

### 3. `frontend/app/api/health/route.ts` (~55 líneas)

Endpoint de health check para el frontend:

```typescript
GET /api/health

Response:
{
  "status": "healthy",
  "timestamp": "2026-02-04T17:14:27.610Z",
  "version": "0.1.0",
  "environment": "development",
  "services": {
    "frontend": { "status": "healthy" },
    "backend": { "status": "healthy", "url": "http://backend:8000" }
  },
  "uptime": 136.87
}
```

**Funcionalidades:**
- Verifica estado del frontend
- Verifica conectividad con el backend
- Soporte para HEAD requests
- Timeout de 5 segundos para backend check

### 4. `frontend/.env.example` (~35 líneas)

Template de variables de entorno con ejemplos para:
- Desarrollo local
- Docker development
- Producción

### 5. `scripts/docker-dev.sh` (~190 líneas)

Script de automatización para Docker:

| Comando | Descripción |
|---------|-------------|
| `start` | Iniciar todos los servicios |
| `stop` | Detener todos los servicios |
| `restart` | Reiniciar servicios |
| `logs` | Ver logs |
| `logs-f` | Logs en tiempo real |
| `build` | Reconstruir imágenes |
| `clean` | Limpiar todo |
| `status` | Ver estado |
| `shell-be` | Shell en backend |
| `shell-fe` | Shell en frontend |
| `db` | Conectar a PostgreSQL |
| `redis` | Conectar a Redis |

---

## 📝 Archivos Modificados

### 1. `docker-compose.dev.yml`

**Adiciones:**
```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
    target: development
  container_name: nestsecure_frontend_dev
  environment:
    NODE_ENV: development
    NEXT_PUBLIC_API_URL: http://backend:8000/api/v1
    NEXT_PUBLIC_BROWSER_API_URL: http://localhost:8000/api/v1
    WATCHPACK_POLLING: "true"
  ports:
    - "3000:3000"
  volumes:
    - ./frontend:/app
    - /app/node_modules
    - /app/.next
  depends_on:
    backend:
      condition: service_healthy
```

**Cambios en backend:**
- CORS actualizado para incluir `http://frontend:3000`

**Nuevos volúmenes:**
- `frontend_node_modules`
- `frontend_next`

### 2. `frontend/next.config.mjs`

```javascript
const nextConfig = {
  output: 'standalone',  // Para Docker production
  turbopack: {},         // Silencia warning de Turbopack
  typescript: { ignoreBuildErrors: true },
  images: { unoptimized: true },
  async headers() { /* CORS headers */ },
  async rewrites() { /* Health proxy */ },
};
```

### 3. `frontend/lib/api.ts`

```typescript
function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    // Browser: usar localhost
    return process.env.NEXT_PUBLIC_BROWSER_API_URL || 
           process.env.NEXT_PUBLIC_API_URL || 
           'http://localhost:8000/api/v1';
  }
  // Server: usar URL interna de Docker
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
}
```

### 4. `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_BROWSER_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### 5. `Makefile`

Nuevos comandos agregados:
- `docker-up-build` - Levantar con rebuild
- `docker-logs-frontend` - Logs del frontend
- `docker-build-frontend` - Build solo frontend
- `docker-restart-frontend` - Restart solo frontend
- `docker-shell-frontend` - Shell en frontend

---

## 🐳 Arquitectura Docker

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NESTSECURE Docker Network                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │   Frontend  │───▶│   Backend   │───▶│  PostgreSQL │              │
│  │  (Next.js)  │    │  (FastAPI)  │    │             │              │
│  │    :3000    │    │    :8000    │    │    :5432    │              │
│  └─────────────┘    └──────┬──────┘    └─────────────┘              │
│                            │                                         │
│                            ▼                                         │
│                     ┌─────────────┐                                  │
│                     │    Redis    │                                  │
│                     │    :6379    │                                  │
│                     └──────┬──────┘                                  │
│                            │                                         │
│              ┌─────────────┴─────────────┐                          │
│              ▼                           ▼                          │
│       ┌───────────┐              ┌───────────┐                      │
│       │  Celery   │              │  Celery   │                      │
│       │  Worker   │              │   Beat    │                      │
│       └───────────┘              └───────────┘                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   Browser: :3000                Backend API: :8000
```

---

## 🔧 Variables de Entorno

### Frontend (Docker)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://backend:8000/api/v1` | URL interna para SSR |
| `NEXT_PUBLIC_BROWSER_API_URL` | `http://localhost:8000/api/v1` | URL para browser |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/ws` | WebSocket |
| `NODE_ENV` | `development` | Entorno |
| `WATCHPACK_POLLING` | `true` | Hot-reload en Docker |
| `CHOKIDAR_USEPOLLING` | `true` | File watching |

### Backend (Docker)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `BACKEND_CORS_ORIGINS` | `["http://localhost:3000","http://frontend:3000",...]` | CORS permitidos |

---

## ✅ Verificación de Deployment

### Servicios Activos

```bash
$ docker compose -f docker-compose.dev.yml ps

NAME                           STATUS          PORTS
nestsecure_frontend_dev        Up (healthy)    0.0.0.0:3000->3000/tcp
nestsecure_backend_dev         Up (healthy)    0.0.0.0:8000->8000/tcp
nestsecure_postgres_dev        Up (healthy)    0.0.0.0:5432->5432/tcp
nestsecure_redis_dev           Up (healthy)    0.0.0.0:6379->6379/tcp
nestsecure_celery_worker_dev   Up              8000/tcp
nestsecure_celery_beat_dev     Up              8000/tcp
```

### Health Checks

```bash
# Frontend
$ curl http://localhost:3000/login
→ 200 OK

# Frontend Health
$ curl http://localhost:3000/api/health
→ 200 OK { "status": "healthy", "services": {...} }

# Backend
$ curl http://localhost:8000/health
→ 200 OK
```

---

## 🚀 Comandos de Uso

### Inicio Rápido

```bash
# Opción 1: Usando script
./scripts/docker-dev.sh start

# Opción 2: Usando Make
make docker-up

# Opción 3: Docker Compose directo
docker compose -f docker-compose.dev.yml up -d
```

### Ver Logs

```bash
# Todos los servicios
make docker-logs

# Solo frontend
make docker-logs-frontend

# Solo backend
make docker-logs-backend
```

### Reconstruir

```bash
# Reconstruir todo
make docker-build

# Solo frontend
make docker-build-frontend
```

### Shell en Contenedores

```bash
# Frontend (sh)
make docker-shell-frontend

# Backend (bash)
make docker-shell-backend
```

---

## 📊 Estadísticas del Día 13

| Métrica | Valor |
|---------|-------|
| Archivos creados | 5 |
| Archivos modificados | 5 |
| Líneas de código | ~500 |
| Contenedores | 6 activos |
| Puertos expuestos | 4 (3000, 8000, 5432, 6379) |
| Tiempo de build frontend | ~45s |
| Tiempo de startup frontend | ~10s (primera compilación) |

---

## 🔗 URLs de Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| Frontend | http://localhost:3000 | Aplicación Next.js |
| Login | http://localhost:3000/login | Página de login |
| Dashboard | http://localhost:3000/dashboard | Dashboard principal |
| Backend API | http://localhost:8000 | FastAPI |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Health Frontend | http://localhost:3000/api/health | Health check |
| Health Backend | http://localhost:8000/health | Health check |

---

## 🔐 Credenciales de Demo

| Campo | Valor |
|-------|-------|
| Email | `admin@nestsecure.com` |
| Password | `Admin123!` |

---

## 📈 Próximos Pasos (Día 14-15)

1. **Día 14:** Completar componentes del frontend
   - Formularios de scans
   - Tablas de vulnerabilidades
   - Gráficos del dashboard

2. **Día 15:** Testing e integración
   - Tests E2E con Playwright/Cypress
   - Validación de flujos completos
   - Documentación de API

3. **Día 16:** Production deployment
   - Docker compose producción
   - Nginx como reverse proxy
   - SSL/TLS configuration

---

## 📝 Notas Técnicas

### Next.js 16 + Turbopack

Next.js 16 usa Turbopack por defecto en lugar de Webpack. Configuraciones importantes:

```javascript
// next.config.mjs
{
  turbopack: {},  // Silencia warning, usa Turbopack
  output: 'standalone',  // Para Docker production
}
```

### Hot Reload en Docker

Para que el hot-reload funcione en Docker, se necesitan estas variables:

```yaml
WATCHPACK_POLLING: "true"
CHOKIDAR_USEPOLLING: "true"
```

Y estos volúmenes en docker-compose:

```yaml
volumes:
  - ./frontend:/app
  - /app/node_modules    # Excluir node_modules
  - /app/.next           # Excluir .next cache
```

### API URL Strategy

El frontend necesita diferentes URLs según el contexto:

| Contexto | URL | Razón |
|----------|-----|-------|
| SSR (Server) | `http://backend:8000` | Red interna Docker |
| Browser | `http://localhost:8000` | Acceso desde host |

Esto se maneja en `lib/api.ts` con `getApiBaseUrl()`.

---

**Día 13 completado exitosamente.** ✅
