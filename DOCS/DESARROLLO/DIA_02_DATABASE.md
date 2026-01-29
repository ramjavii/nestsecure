# =============================================================================
# NESTSECURE - Día 2: Capa de Base de Datos y ORM
# =============================================================================
# Fecha: 2026-01-29
# Objetivo: Implementar SQLAlchemy, modelos ORM, Alembic y schemas Pydantic
# =============================================================================

## ✅ Tareas Completadas

### 1. Configuración de SQLAlchemy Async (`backend/app/db/`)

#### **base.py** - Base declarativa y tipos cross-database
- [x] `Base` con `DeclarativeBase` de SQLAlchemy 2.0
- [x] `TimestampMixin` - Campos created_at/updated_at automáticos
- [x] `UUIDMixin` - ID UUID como primary key
- [x] TypeDecorators personalizados para compatibilidad PostgreSQL/SQLite:
  - `UUID` - UUID nativo en PostgreSQL, VARCHAR(36) en SQLite
  - `JSONB` - JSONB nativo en PostgreSQL, TEXT+JSON en SQLite
  - `INET` - INET nativo en PostgreSQL, VARCHAR(45) en SQLite
  - `StringArray` - ARRAY(String) en PostgreSQL, TEXT+JSON en SQLite

#### **session.py** - Gestión de sesiones async
- [x] `get_async_engine()` - Factory de engine con pooling
- [x] `get_async_session_maker()` - Sessionmaker configurado
- [x] `get_db()` - Dependency injection para FastAPI
- [x] `close_db_connections()` - Cleanup en shutdown

#### **init_db.py** - Inicialización de base de datos
- [x] `create_tables()` - Crear todas las tablas
- [x] `drop_tables()` - Drop todas las tablas
- [x] `create_first_superuser()` - Usuario admin inicial
- [x] `init_database()` - Setup completo

### 2. Modelos ORM Multi-tenant (`backend/app/models/`)

#### **organization.py** - Modelo de organización (tenant)
- [x] Campos: name, slug, description, license_key, license_expires_at
- [x] Configuración: max_assets, settings (JSONB)
- [x] Estado: is_active
- [x] Relaciones: users, assets (cascade delete)
- [x] Índices: slug (unique), name
- [x] Validación de slug único

#### **user.py** - Modelo de usuario
- [x] Campos: email, hashed_password, full_name, role
- [x] Permisos: permissions (JSONB), is_active, is_superuser
- [x] Multi-tenant: organization_id con foreign key
- [x] Metadata: last_login_at, avatar_url, preferences (JSONB)
- [x] Relación: organization con back_populates
- [x] Índices: email (unique), organization_id
- [x] Cascade delete cuando se elimina organización

#### **asset.py** - Modelo de activo/host
- [x] Identificación: ip_address (INET), hostname, mac_address
- [x] Sistema operativo: operating_system, os_version, os_cpe
- [x] Clasificación: asset_type, criticality, tags (ARRAY)
- [x] Estado: status, is_reachable
- [x] Vulnerabilidades: risk_score, contadores por severidad
- [x] Timestamps: first_seen, last_seen, last_scanned
- [x] Metadata: metadata_extra (JSONB)
- [x] Multi-tenant: organization_id con foreign key
- [x] Relaciones: organization, services (cascade delete)
- [x] Índices: ip_address, hostname, organization_id, status

#### **service.py** - Modelo de servicio/puerto
- [x] Puerto: port, protocol, state
- [x] Identificación: service_name, product, version, cpe
- [x] Detección: banner, detection_method, confidence
- [x] SSL: ssl_enabled, ssl_info (JSONB)
- [x] HTTP: http_title, http_technologies (ARRAY)
- [x] Metadata: extra_info (JSONB)
- [x] Relación: asset con foreign key (cascade delete)
- [x] Índices: asset_id, port, service_name

### 3. Schemas Pydantic (`backend/app/schemas/`)

#### **common.py** - Schemas base
- [x] `BaseSchema` - Config común (from_attributes=True)
- [x] `PaginationParams` - skip, limit, offset calculado
- [x] `PaginatedResponse[T]` - Respuesta paginada genérica
- [x] `MessageResponse` - Respuesta simple con mensaje
- [x] `ErrorResponse` - Respuesta de error estandarizada

#### **organization.py** - Schemas de organización
- [x] `OrganizationBase` - Campos comunes
- [x] `OrganizationCreate` - Validación de creación (slug lowercase)
- [x] `OrganizationUpdate` - Update parcial
- [x] `OrganizationInDB` - Datos completos con ID
- [x] `Organization` - Respuesta pública
- [x] Validadores: slug pattern, max_assets positivo

#### **user.py** - Schemas de usuario
- [x] `UserBase` - Campos comunes
- [x] `UserCreate` - Con password, validación email
- [x] `UserUpdate` - Update parcial opcional
- [x] `UserUpdatePassword` - Cambio de password
- [x] `UserInDB` - Con hashed_password
- [x] `User` - Respuesta pública (sin password)
- [x] Validadores: email, role enum, strong password

#### **asset.py** - Schemas de activo
- [x] `AssetBase` - Campos comunes
- [x] `AssetCreate` - Validación de creación
- [x] `AssetUpdate` - Update parcial
- [x] `AssetInDB` - Datos completos
- [x] `Asset` - Respuesta pública
- [x] Validadores: IP (v4/v6), MAC address, asset_type, criticality

#### **service.py** - Schemas de servicio
- [x] `ServiceBase` - Campos comunes
- [x] `ServiceCreate` - Validación de creación
- [x] `ServiceUpdate` - Update parcial
- [x] `ServiceInDB` - Datos completos
- [x] `Service` - Respuesta pública
- [x] Validadores: port (1-65535), protocol (tcp/udp), confidence (0-100)

### 4. Seguridad (`backend/app/core/security.py`)
- [x] `hash_password()` - Bcrypt hashing
- [x] `verify_password()` - Verificación de password
- [x] Configuración: rounds=12, auto_error=False

### 5. Configuración de Alembic

#### **alembic.ini**
- [x] Script location configurado
- [x] Template de nombres simplificado: `%(rev)s_%(slug)s`
- [x] Timezone UTC
- [x] Truncate slug a 40 caracteres

#### **alembic/env.py** - Entorno de migraciones
- [x] Imports de todos los modelos
- [x] URL de base de datos desde settings (sync con psycopg2)
- [x] Target metadata desde Base
- [x] Modo offline y online
- [x] Engine síncrono (no async) para compatibilidad
- [x] Opciones: compare_type=True, compare_server_default=True

#### **alembic/script.py.mako** - Template de migración
- [x] Template Mako correcto para generar archivos
- [x] Variables: revision, down_revision, branch_labels, depends_on
- [x] Funciones upgrade() y downgrade()
- [x] Import de tipos necesarios

#### **Migración inicial: `32be6e140ffc_initial_tables.py`**
- [x] Creación de tabla `organizations` con índices
- [x] Creación de tabla `assets` con foreign key y índices
- [x] Creación de tabla `users` con foreign key y índices
- [x] Creación de tabla `services` con foreign key y índices
- [x] Tipos PostgreSQL nativos: UUID, JSONB, INET, ARRAY
- [x] Función downgrade() para rollback completo

### 6. Tests de Base de Datos

#### **test_database/conftest.py** - Fixtures de testing
- [x] `test_db_engine` - Engine SQLite in-memory con StaticPool
- [x] `test_session_maker` - SessionMaker para tests
- [x] `db_session` - Session por test con rollback
- [x] StaticPool para compartir conexión SQLite en memoria

#### **test_database/test_models.py** - Tests de modelos (14 tests)
- [x] Organization: creación, defaults, timestamps, slug unique
- [x] User: creación, relación con org, defaults, cascade delete
- [x] Asset: creación, relación con org, risk_score default
- [x] Service: creación, relación con asset, confidence default

#### **test_database/test_schemas.py** - Tests de schemas (30 tests)
- [x] Organization: validación, slug lowercase, max_assets positivo
- [x] User: email válido, password fuerte, role válido
- [x] Asset: IP válida (v4/v6), MAC válida, tipos válidos
- [x] Service: port válido, protocol lowercase, confidence 0-100
- [x] Common: paginación, offset, límites, responses

## 🔧 Problemas Resueltos

### Problema 1: Python 3.13 Incompatibilidades
**Síntoma:** asyncpg y psycopg2-binary no compilan en Python 3.13

**Solución:**
- Cambio a `psycopg[binary,pool]>=3.1.0` (psycopg3)
- Upgrade de SQLAlchemy 2.0.25 → 2.0.46
- Actualización de config.py:
  - Async URL: `postgresql+psycopg://` (en lugar de `postgresql+asyncpg://`)
  - Sync URL: `postgresql+psycopg2://` (requiere psycopg2-binary)

### Problema 2: Tipos PostgreSQL en SQLite para tests
**Síntoma:** JSONB, INET, ARRAY no existen en SQLite, tests fallan

**Solución:** Creación de TypeDecorators en `app/db/base.py`:
```python
# UUID: PostgreSQL UUID nativo, SQLite VARCHAR(36)
class UUID(TypeDecorator):
    impl = String(36)
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

# Similar para JSONB, INET, StringArray
```

### Problema 3: SQLite in-memory no comparte estado
**Síntoma:** Tablas creadas en un test no existen en otro

**Solución:** StaticPool en conftest.py:
```python
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    poolclass=StaticPool,  # Compartir conexión
    connect_args={"check_same_thread": False}
)
```

### Problema 4: Archivo script.py.mako vacío
**Síntoma:** Alembic genera archivos de migración vacíos

**Solución:** Recrear template Mako completo con:
- Variables de revision
- Imports de alembic y sqlalchemy
- Funciones upgrade()/downgrade()

### Problema 5: Alembic usa tipos custom app.db.base.*
**Síntoma:** Migración referencia código de app, debe ser standalone

**Solución:** Editar migración para usar tipos nativos:
- `app.db.base.UUID` → `postgresql.UUID(as_uuid=True)`
- `app.db.base.JSONB` → `postgresql.JSONB(astext_type=sa.Text())`
- `app.db.base.INET` → `postgresql.INET()`
- `app.db.base.StringArray` → `postgresql.ARRAY(sa.String())`

## 📁 Archivos Creados/Modificados

```
backend/
├── requirements.txt                    # Actualizado: psycopg, SQLAlchemy 2.0.46
├── alembic.ini                        # Configuración Alembic
├── alembic/
│   ├── env.py                         # Entorno migraciones (sync)
│   ├── script.py.mako                 # Template Mako
│   └── versions/
│       └── 32be6e140ffc_initial_tables.py  # Migración inicial
└── app/
    ├── config.py                      # Actualizado: psycopg URLs
    ├── db/
    │   ├── __init__.py               # Exports
    │   ├── base.py                   # Base + TypeDecorators
    │   ├── session.py                # AsyncEngine + SessionMaker
    │   └── init_db.py                # Inicialización
    ├── models/
    │   ├── __init__.py               # Exports de modelos
    │   ├── organization.py           # Modelo Organization
    │   ├── user.py                   # Modelo User
    │   ├── asset.py                  # Modelo Asset
    │   └── service.py                # Modelo Service
    ├── schemas/
    │   ├── __init__.py               # Exports de schemas
    │   ├── common.py                 # Schemas base/comunes
    │   ├── organization.py           # Schemas Organization
    │   ├── user.py                   # Schemas User
    │   ├── asset.py                  # Schemas Asset
    │   └── service.py                # Schemas Service
    ├── core/
    │   ├── __init__.py
    │   └── security.py               # Password hashing
    └── tests/
        ├── test_config.py            # Actualizado: URLs psycopg
        └── test_database/
            ├── __init__.py
            ├── conftest.py           # Fixtures DB
            ├── test_models.py        # Tests modelos (14 tests)
            └── test_schemas.py       # Tests schemas (30 tests)
```

## 🧪 Ejecutar Tests

```bash
cd backend
source venv/bin/activate

# Todos los tests (82 total)
pytest -v

# Solo tests de base de datos (44 tests)
pytest app/tests/test_database/ -v

# Solo tests de modelos (14 tests)
pytest app/tests/test_database/test_models.py -v

# Solo tests de schemas (30 tests)
pytest app/tests/test_database/test_schemas.py -v

# Con coverage
pytest --cov=app --cov-report=html

# Tests con output detallado
pytest app/tests/test_database/ -v --tb=short
```

### Resultados de Tests

```
======================== test session starts =========================
collected 82 items

app/tests/test_api/test_health.py::TestHealthEndpoint ... (14 PASSED)
app/tests/test_config.py::TestSettings ...              (24 PASSED)
app/tests/test_database/test_models.py ...              (14 PASSED)
app/tests/test_database/test_schemas.py ...             (30 PASSED)

===================== 82 passed, 1 warning in 1.55s ==================
```

## 🗄️ Base de Datos

### Aplicar Migraciones

```bash
cd backend
source venv/bin/activate

# Ver estado de migraciones
alembic current

# Ver historial
alembic history --verbose

# Aplicar todas las migraciones
alembic upgrade head

# Rollback 1 versión
alembic downgrade -1

# Rollback completo
alembic downgrade base

# Generar nueva migración (autogenerate)
alembic revision --autogenerate -m "Descripción del cambio"
```

### Tablas Creadas (Migración 32be6e140ffc)

| Tabla | Columnas | Índices | Foreign Keys |
|-------|----------|---------|--------------|
| **organizations** | 11 | slug (unique), name | - |
| **users** | 13 | email (unique), organization_id | organization_id → organizations.id |
| **assets** | 23 | ip_address, hostname, organization_id, status | organization_id → organizations.id |
| **services** | 17 | asset_id, port, service_name | asset_id → assets.id |

### Verificar Conexión

```bash
# Health check (incluye latencia de DB)
curl http://localhost:8000/health/ready | jq

# Ejemplo de respuesta:
{
  "status": "ready",
  "timestamp": "2026-01-29T13:33:31.168844+00:00",
  "checks": {
    "database": {
      "status": "up",
      "latency_ms": 152.33
    },
    "redis": {
      "status": "up",
      "latency_ms": 0.53
    }
  },
  "uptime_seconds": 55.071229
}
```

### Conectar Directamente a PostgreSQL

```bash
# Desde host
docker exec -it nestsecure-postgres psql -U nestsecure_user -d nestsecure_db

# Comandos útiles en psql:
\dt                      # Listar tablas
\d organizations         # Describir tabla
\d+ assets              # Describir con info adicional
SELECT * FROM organizations;
\q                      # Salir
```

## 🐳 Docker Services

```bash
# Levantar servicios
docker-compose -f docker-compose.dev.yml up -d

# Ver logs del backend
docker-compose -f docker-compose.dev.yml logs -f backend

# Ver logs de PostgreSQL
docker-compose -f docker-compose.dev.yml logs -f postgres

# Recrear servicios
docker-compose -f docker-compose.dev.yml up -d --force-recreate

# Parar todo
docker-compose -f docker-compose.dev.yml down

# Parar y eliminar volúmenes (CUIDADO: elimina datos)
docker-compose -f docker-compose.dev.yml down -v
```

## 📊 Métricas del Día

| Métrica | Valor |
|---------|-------|
| Archivos creados/modificados | 22 |
| Líneas de código | ~2,800 |
| Tests nuevos | 44 (modelos + schemas) |
| Tests totales | 82 |
| Cobertura actual | ~75% |
| Modelos ORM | 4 |
| Schemas Pydantic | 20+ |
| Migraciones | 1 (4 tablas) |
| Tablas creadas | 4 |
| Índices creados | 13 |

## 🎯 Objetivos Cumplidos

- ✅ SQLAlchemy 2.0 async configurado
- ✅ 4 modelos ORM completos con relaciones
- ✅ TypeDecorators para cross-database compatibility
- ✅ Alembic configurado y migración inicial aplicada
- ✅ Schemas Pydantic con validación completa
- ✅ Sistema de seguridad (password hashing)
- ✅ Tests de modelos y schemas (44 tests)
- ✅ Compatibilidad Python 3.13 (psycopg3)
- ✅ PostgreSQL conectado y verificado

## 🧩 Dependencias Técnicas

### Nuevas Dependencias Instaladas
```
sqlalchemy>=2.0.30              # ORM con soporte async
alembic>=1.13.1                 # Migraciones
psycopg[binary,pool]>=3.1.0     # Driver PostgreSQL async/sync
psycopg2-binary>=2.9.11         # Driver sync para Alembic
aiosqlite>=0.20.0               # SQLite async para tests
bcrypt>=4.1.2                   # Password hashing
passlib[bcrypt]>=1.7.4          # Password utilities
```

### Estructura Multi-tenant
El sistema está diseñado con multi-tenancy a nivel de base de datos:
- Cada `Organization` es un tenant
- `User` y `Asset` tienen `organization_id` (foreign key con cascade delete)
- `Service` pertenece a `Asset` (cascade delete)
- Índices optimizados para queries por organización

## 🔜 Próximo: Día 3

### Endpoints CRUD
- [ ] `/api/v1/organizations` - CRUD completo
- [ ] `/api/v1/users` - CRUD con autenticación
- [ ] `/api/v1/assets` - CRUD con paginación
- [ ] `/api/v1/services` - CRUD anidado en assets

### Autenticación JWT
- [ ] Login endpoint
- [ ] Token generation y refresh
- [ ] Middleware de autenticación
- [ ] Dependency `get_current_user()`

### Multi-tenancy
- [ ] Middleware de tenant context
- [ ] Filters automáticos por organization_id
- [ ] Validación de permisos por tenant

### Tests de Integración
- [ ] Tests end-to-end con PostgreSQL real
- [ ] Tests de autenticación
- [ ] Tests de multi-tenancy
- [ ] Tests de endpoints CRUD

---
*Documentación generada para tracking del desarrollo - Día 2 completado exitosamente* 🎉
