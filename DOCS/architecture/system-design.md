# Arquitectura del Sistema - NESTSECURE

## Visión General

NESTSECURE es un sistema de escaneo de vulnerabilidades on-premise diseñado para despliegue en Intel NUC o servidores Linux. La arquitectura sigue un patrón de microservicios con comunicación asíncrona.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NESTSECURE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │   Frontend  │────▶│    Nginx    │────▶│   Backend   │                   │
│  │   (React)   │     │   (Proxy)   │     │  (FastAPI)  │                   │
│  └─────────────┘     └─────────────┘     └──────┬──────┘                   │
│                                                  │                          │
│                           ┌──────────────────────┼──────────────────────┐   │
│                           │                      │                      │   │
│                           ▼                      ▼                      ▼   │
│                    ┌─────────────┐       ┌─────────────┐       ┌──────────┐ │
│                    │ PostgreSQL  │       │    Redis    │       │  Celery  │ │
│                    │ +TimescaleDB│       │   (Cache)   │       │ Workers  │ │
│                    └─────────────┘       └─────────────┘       └──────────┘ │
│                                                                      │      │
│                                          ┌───────────────────────────┼──┐   │
│                                          │                           │  │   │
│                                          ▼           ▼           ▼   ▼  │   │
│                                    ┌─────────┐ ┌─────────┐ ┌─────────┐  │   │
│                                    │  Nmap   │ │ OpenVAS │ │ Nuclei  │  │   │
│                                    │ Scanner │ │ Scanner │ │ Scanner │  │   │
│                                    └─────────┘ └─────────┘ └─────────┘  │   │
│                                                                         │   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Componentes Principales

### 1. Frontend (React + TypeScript)

**Tecnologías:**
- React 18
- TypeScript 5
- Tailwind CSS + shadcn/ui
- TanStack Query (data fetching)
- Recharts (visualizaciones)
- Zustand (state management)

**Responsabilidades:**
- Dashboard interactivo con métricas
- Gestión de assets y vulnerabilidades
- Visualización de scans en tiempo real
- Generación y visualización de reportes
- Configuración del sistema

### 2. Backend (FastAPI + Python)

**Tecnologías:**
- Python 3.13
- FastAPI 0.109+
- SQLAlchemy 2.0 (async)
- Pydantic v2
- python-jose (JWT)

**Responsabilidades:**
- API REST para todas las operaciones
- Autenticación y autorización (JWT)
- Validación de datos
- Orquestación de scans
- Multi-tenancy (organizaciones)

### 3. Base de Datos (PostgreSQL + TimescaleDB)

**Características:**
- PostgreSQL 15
- TimescaleDB para datos time-series
- Soporte para JSONB, arrays, INET
- Conexión async via psycopg3

**Modelos Principales:**
```
organizations ─┬─▶ users
               ├─▶ assets ──▶ services
               ├─▶ scans ──▶ scan_results
               └─▶ vulnerabilities ──▶ comments
                        │
                        └─▶ cve_cache (global)
```

### 4. Cola de Tareas (Celery + Redis)

**Colas definidas:**
- `default`: Tareas generales
- `scanning`: Escaneos de red
- `reports`: Generación de reportes
- `notifications`: Alertas y notificaciones

**Workers:**
- `nmap_worker`: Escaneos con Nmap
- `cve_worker`: Sincronización de CVEs
- `report_worker`: Generación de reportes
- `cleanup_worker`: Limpieza de datos

### 5. Scanners

| Scanner | Propósito | Estado |
|---------|-----------|--------|
| **Nmap** | Descubrimiento de hosts y puertos | ✅ Implementado |
| **OpenVAS** | Escaneo de vulnerabilidades | 📝 Pendiente |
| **Nuclei** | Templates de vulnerabilidades | 📝 Pendiente |
| **OWASP ZAP** | Escaneo de aplicaciones web | 📝 Pendiente |

## Flujo de Datos

### Flujo de Autenticación

```
Usuario ──▶ POST /api/v1/auth/login
                    │
                    ▼
            Verificar credenciales
                    │
                    ▼
            Generar JWT (access + refresh)
                    │
                    ▼
            Retornar tokens al cliente
```

### Flujo de Escaneo

```
Usuario ──▶ POST /api/v1/scans
                    │
                    ▼
            Crear registro Scan (status=pending)
                    │
                    ▼
            Encolar tarea en Celery
                    │
                    ▼
        ┌───────────────────────────┐
        │      Celery Worker        │
        │                           │
        │  1. Actualizar status     │
        │  2. Ejecutar Nmap         │
        │  3. Parsear resultados    │
        │  4. Crear Assets/Services │
        │  5. Buscar CVEs           │
        │  6. Crear Vulnerabilidades│
        │  7. Actualizar stats      │
        └───────────────────────────┘
                    │
                    ▼
            Scan completado
```

## Seguridad

### Autenticación

- **JWT tokens** con access (30 min) y refresh (7 días)
- **OAuth2 password flow**
- **Bcrypt** para hash de contraseñas (rounds=12)

### Autorización

**Roles disponibles:**
| Rol | Nivel | Permisos |
|-----|-------|----------|
| ADMIN | 4 | Todo |
| OPERATOR | 3 | CRUD completo |
| ANALYST | 2 | Lectura + comentarios |
| VIEWER | 1 | Solo lectura |

### Multi-tenancy

- Cada organización es un tenant aislado
- Todos los datos filtrados por `organization_id`
- Users solo acceden a su organización
- Superusers pueden acceder a todo

## Base de Datos - Esquema

### Tablas Principales

```sql
-- Organizaciones (tenants)
organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    slug VARCHAR(50) UNIQUE,
    is_active BOOLEAN,
    max_assets INTEGER,
    settings JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

-- Usuarios
users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255),
    full_name VARCHAR(100),
    role VARCHAR(20),
    organization_id UUID REFERENCES organizations,
    is_active BOOLEAN,
    is_superuser BOOLEAN,
    last_login_at TIMESTAMP
)

-- Assets (hosts/dispositivos)
assets (
    id UUID PRIMARY KEY,
    ip_address INET,
    hostname VARCHAR(255),
    mac_address VARCHAR(17),
    asset_type VARCHAR(50),
    criticality VARCHAR(20),
    status VARCHAR(20),
    risk_score FLOAT,
    organization_id UUID REFERENCES organizations,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
)

-- Servicios (puertos)
services (
    id UUID PRIMARY KEY,
    asset_id UUID REFERENCES assets,
    port INTEGER,
    protocol VARCHAR(10),
    service_name VARCHAR(100),
    version VARCHAR(100),
    state VARCHAR(20)
)

-- Escaneos
scans (
    id UUID PRIMARY KEY,
    name VARCHAR(200),
    scan_type VARCHAR(50),
    status VARCHAR(20),
    targets TEXT[],
    organization_id UUID,
    created_by_id UUID,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    vulnerabilities_found INTEGER
)

-- Vulnerabilidades
vulnerabilities (
    id UUID PRIMARY KEY,
    title VARCHAR(500),
    description TEXT,
    severity VARCHAR(20),
    status VARCHAR(20),
    cvss_score FLOAT,
    cve_id VARCHAR(20),
    asset_id UUID REFERENCES assets,
    organization_id UUID,
    first_seen TIMESTAMP,
    solution TEXT
)

-- Cache de CVEs (global)
cve_cache (
    cve_id VARCHAR(20) PRIMARY KEY,
    description TEXT,
    cvss_v3_score FLOAT,
    cvss_v3_severity VARCHAR(20),
    published_date TIMESTAMP,
    has_exploit BOOLEAN,
    in_cisa_kev BOOLEAN
)
```

## API - Estructura de Endpoints

```
/api/v1/
├── auth/           # Autenticación
│   ├── login
│   ├── refresh
│   └── me
├── users/          # Gestión de usuarios
├── organizations/  # Gestión de organizaciones
├── assets/         # Gestión de assets
├── services/       # Gestión de servicios
├── scans/          # Gestión de escaneos
├── vulnerabilities/ # Gestión de vulnerabilidades
├── cve/            # Búsqueda y sync de CVEs
├── dashboard/      # Estadísticas y métricas
├── reports/        # Generación de reportes
├── alerts/         # Configuración de alertas
└── settings/       # Configuración del sistema
```

## Despliegue

### Desarrollo

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Producción

```bash
docker-compose up -d
```

### Requisitos de Hardware

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| CPU | Intel i5 / 4 cores | Intel i7 / 8 cores |
| RAM | 16 GB | 32 GB |
| Disco | 100 GB SSD | 500 GB NVMe |
| Red | 1 Gbps | 10 Gbps |

## Monitoreo

### Health Checks

- `GET /health` - Check básico
- `GET /health/ready` - Readiness (DB, Redis)
- `GET /health/live` - Liveness (para K8s)

### Métricas Disponibles

- Scans activos/completados
- Vulnerabilidades por severidad
- Assets por estado
- Tiempo de respuesta de API
- Cola de Celery

---

*Última actualización: 30 Enero 2026*
