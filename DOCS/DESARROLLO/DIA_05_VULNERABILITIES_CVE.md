# =============================================================================
# NESTSECURE - Día 5: Vulnerabilities + CVE Integration
# =============================================================================
# Fecha: 2026-01-30
# Objetivo: Implementar gestión de Vulnerabilidades, Scans y CVE
# =============================================================================

## 📊 Resumen de Implementación

| Componente | Estado | Tests | Notas |
|------------|--------|-------|-------|
| Vulnerabilities CRUD API | ✅ Completado | 17/17 | 9 endpoints |
| Scans CRUD API | ✅ Completado | 19/19 | 10 endpoints |
| CVE API | ✅ Completado | 17/17 | 6 endpoints |
| CVE Worker | ✅ Completado | - | Sincronización NVD |
| Risk Calculator Service | ✅ Completado | - | Cálculo CVSS |

**Tests Día 5:** 53 nuevos tests  
**Tests Acumulados:** 234 tests (181 anteriores + 53 nuevos)  
**Duración:** ~5 horas

---

## ✅ Tareas Completadas

### 1. Vulnerabilities CRUD API (`backend/app/api/v1/vulnerabilities.py`)

#### Endpoints Implementados

| Método | Endpoint | Descripción | Permisos |
|--------|----------|-------------|----------|
| GET | `/api/v1/vulnerabilities` | Listar vulnerabilidades con filtros | Todos |
| GET | `/api/v1/vulnerabilities/{id}` | Obtener vulnerabilidad con detalles | Todos |
| POST | `/api/v1/vulnerabilities` | Crear vulnerabilidad (scanners) | Operator+ |
| PATCH | `/api/v1/vulnerabilities/{id}` | Actualizar estado/asignación | Operator+ |
| DELETE | `/api/v1/vulnerabilities/{id}` | Eliminar vulnerabilidad | Admin |
| GET | `/api/v1/vulnerabilities/stats` | Estadísticas de vulnerabilidades | Todos |
| POST | `/api/v1/vulnerabilities/{id}/comment` | Añadir comentario | Todos |
| PATCH | `/api/v1/vulnerabilities/bulk` | Actualización masiva | Operator+ |
| GET | `/api/v1/vulnerabilities/export` | Exportar a CSV/JSON | Todos |

#### Filtros Disponibles

```python
# Parámetros de filtrado
severity: VulnerabilitySeverity  # critical, high, medium, low, info
status: VulnerabilityStatus      # open, confirmed, in_progress, resolved, false_positive
asset_id: str                    # Filtrar por asset específico
cve_id: str                      # Filtrar por CVE (ej: CVE-2024-1234)
has_exploit: bool                # Solo con exploit conocido
assigned_to: str                 # Asignado a usuario
search: str                      # Busca en título, descripción, CVE
```

#### Schemas de Vulnerabilidad

```python
class VulnerabilityCreate(BaseModel):
    title: str                    # Título descriptivo
    description: str              # Descripción detallada
    severity: VulnerabilitySeverity
    asset_id: str                 # Asset afectado
    service_id: Optional[str]     # Servicio afectado
    cve_id: Optional[str]         # CVE relacionado
    cvss_score: Optional[float]   # Score CVSS
    solution: Optional[str]       # Solución recomendada
    references: List[str] = []    # URLs de referencia

class VulnerabilityStats(BaseModel):
    total: int
    by_severity: dict[str, int]   # {critical: 5, high: 10, ...}
    by_status: dict[str, int]     # {open: 20, resolved: 15, ...}
    with_exploit: int
    average_age_days: float
    resolution_rate: float
```

---

### 2. Scans CRUD API (`backend/app/api/v1/scans.py`)

#### Endpoints Implementados

| Método | Endpoint | Descripción | Permisos |
|--------|----------|-------------|----------|
| GET | `/api/v1/scans` | Listar escaneos | Todos |
| GET | `/api/v1/scans/{id}` | Obtener escaneo con logs | Todos |
| POST | `/api/v1/scans` | Crear/iniciar escaneo | Operator+ |
| PATCH | `/api/v1/scans/{id}/cancel` | Cancelar escaneo | Operator+ |
| GET | `/api/v1/scans/{id}/progress` | Progreso del escaneo | Todos |
| GET | `/api/v1/scans/{id}/vulnerabilities` | Vulnerabilidades encontradas | Todos |
| GET | `/api/v1/scans/stats` | Estadísticas de escaneos | Todos |
| PATCH | `/api/v1/scans/{id}` | Actualizar escaneo | Operator+ |
| DELETE | `/api/v1/scans/{id}` | Eliminar escaneo | Admin |
| GET | `/api/v1/scans/types` | Tipos de escaneo disponibles | Todos |

#### Tipos de Escaneo

```python
class ScanType(str, Enum):
    FULL = "full"           # Escaneo completo (todos los puertos)
    QUICK = "quick"         # Top 100 puertos
    TARGETED = "targeted"   # Puertos específicos
    PORT_SCAN = "port_scan" # Solo descubrimiento de puertos
    VULN_SCAN = "vuln_scan" # Búsqueda de vulnerabilidades
    COMPLIANCE = "compliance" # Verificación de compliance
```

#### Estados de Escaneo

```python
class ScanStatus(str, Enum):
    PENDING = "pending"       # En cola
    RUNNING = "running"       # Ejecutándose
    COMPLETED = "completed"   # Finalizado
    FAILED = "failed"         # Error
    CANCELLED = "cancelled"   # Cancelado por usuario
```

#### Schemas de Scan

```python
class ScanCreate(BaseModel):
    name: str                     # Nombre descriptivo
    scan_type: ScanType           # Tipo de escaneo
    targets: List[str]            # IPs, rangos CIDR, hostnames
    scheduled_at: Optional[datetime]  # Programar para después
    options: dict = {}            # Opciones adicionales

class ScanProgress(BaseModel):
    status: ScanStatus
    progress_percent: int         # 0-100
    current_target: Optional[str]
    targets_completed: int
    targets_total: int
    vulnerabilities_found: int
    elapsed_time: str
    estimated_remaining: Optional[str]
```

---

### 3. CVE API (`backend/app/api/v1/cve.py`)

#### Endpoints Implementados

| Método | Endpoint | Descripción | Permisos |
|--------|----------|-------------|----------|
| GET | `/api/v1/cve/search` | Buscar CVEs con filtros | Todos |
| GET | `/api/v1/cve/{cve_id}` | Obtener CVE por ID | Todos |
| POST | `/api/v1/cve/lookup` | Lookup múltiples CVEs | Todos |
| GET | `/api/v1/cve/stats` | Estadísticas de CVEs | Todos |
| POST | `/api/v1/cve/sync` | Sincronizar con NVD | Admin |
| GET | `/api/v1/cve/sync/status` | Estado de sincronización | Admin |

#### Filtros de Búsqueda CVE

```python
# Parámetros de búsqueda
keyword: str                   # Buscar en descripción
severity: str                  # critical, high, medium, low
min_cvss: float               # CVSS mínimo (0-10)
max_cvss: float               # CVSS máximo (0-10)
has_exploit: bool             # Solo con exploit conocido
in_cisa_kev: bool             # Solo en CISA KEV catalog
published_after: datetime     # Publicados después de fecha
published_before: datetime    # Publicados antes de fecha
vendor: str                   # Filtrar por vendor
product: str                  # Filtrar por producto
```

#### Schemas de CVE

```python
class CVERead(BaseModel):
    cve_id: str                   # CVE-2024-1234
    description: str
    cvss_v3_score: Optional[float]
    cvss_v3_severity: Optional[str]
    cvss_v3_vector: Optional[str]
    published_date: datetime
    last_modified_date: datetime
    references: List[str]
    affected_products: List[dict]
    weaknesses: List[str]         # CWE IDs
    has_exploit: bool
    in_cisa_kev: bool
    epss_score: Optional[float]   # Exploit Prediction Score

class CVEStats(BaseModel):
    total: int
    by_severity: dict[str, int]
    with_exploit: int
    in_kev: int
    average_cvss: float
    recent_critical: int          # Últimos 30 días
```

---

### 4. CVE Worker (`backend/app/workers/cve_worker.py`)

#### Tareas Implementadas

```python
@celery_app.task
def sync_nvd_database(full_sync: bool = False):
    """
    Sincroniza CVEs desde NVD API.
    - full_sync=False: Solo últimos 7 días
    - full_sync=True: Histórico completo
    """

@celery_app.task  
def lookup_cve(cve_id: str):
    """Busca un CVE específico en NVD."""

@celery_app.task
def update_epss_scores():
    """Actualiza EPSS scores desde FIRST."""

@celery_app.task
def sync_cisa_kev():
    """Sincroniza CISA Known Exploited Vulnerabilities."""
```

---

### 5. Modelos de Base de Datos

#### Modelo Vulnerability

```python
class Vulnerability(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vulnerabilities"
    
    # Identificación
    title: str
    description: str
    severity: VulnerabilitySeverity
    status: VulnerabilityStatus = "open"
    
    # Puntuación
    cvss_score: Optional[float]
    cvss_vector: Optional[str]
    risk_score: float = 0.0
    
    # Relaciones
    organization_id: str  # FK -> organizations
    asset_id: str         # FK -> assets
    service_id: Optional[str]  # FK -> services
    scan_id: Optional[str]     # FK -> scans
    cve_id: Optional[str]      # FK -> cve_cache
    assigned_to_id: Optional[str]  # FK -> users
    
    # Metadata
    first_seen: datetime
    last_seen: datetime
    solution: Optional[str]
    references: List[str]
    false_positive: bool = False
    verified: bool = False
```

#### Modelo Scan

```python
class Scan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scans"
    
    name: str
    scan_type: ScanType
    status: ScanStatus = "pending"
    
    # Targets
    targets: List[str]
    targets_completed: int = 0
    
    # Timing
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Results
    assets_found: int = 0
    services_found: int = 0
    vulnerabilities_found: int = 0
    
    # Relaciones
    organization_id: str
    created_by_id: str
    
    # Logs
    logs: List[dict] = []
    error_message: Optional[str]
```

#### Modelo CVECache

```python
class CVECache(Base, TimestampMixin):
    __tablename__ = "cve_cache"
    
    cve_id: str  # PK: CVE-2024-1234
    description: str
    
    # CVSS v3
    cvss_v3_score: Optional[float]
    cvss_v3_severity: Optional[str]
    cvss_v3_vector: Optional[str]
    
    # CVSS v2 (legacy)
    cvss_v2_score: Optional[float]
    
    # Metadata
    published_date: datetime
    last_modified_date: datetime
    references: List[str]
    affected_products: List[dict]  # CPE entries
    weaknesses: List[str]          # CWE IDs
    
    # Enrichment
    has_exploit: bool = False
    exploit_urls: List[str] = []
    in_cisa_kev: bool = False
    epss_score: Optional[float]
```

---

### 6. Migración de Base de Datos

**Archivo:** `alembic/versions/0680cdb4620c_add_scans_vulnerabilities_cve_cache.py`

```python
# Tablas creadas:
# - scans
# - vulnerabilities
# - vulnerability_comments
# - cve_cache

# Índices creados:
# - ix_vulnerabilities_severity
# - ix_vulnerabilities_status
# - ix_vulnerabilities_asset_id
# - ix_vulnerabilities_cve_id
# - ix_scans_status
# - ix_scans_organization_id
# - ix_cve_cache_severity
# - ix_cve_cache_published_date
```

---

## 🧪 Tests Implementados

### Tests de Vulnerabilities (`test_api/test_vulnerabilities.py` - 17 tests)

| Categoría | Tests | Estado |
|-----------|-------|--------|
| Listar Vulnerabilities | 4 | ✅ |
| Crear Vulnerability | 3 | ✅ |
| Obtener Vulnerability | 2 | ✅ |
| Actualizar Vulnerability | 2 | ✅ |
| Eliminar Vulnerability | 2 | ✅ |
| Stats | 2 | ✅ |
| Multi-tenancy | 2 | ✅ |

### Tests de Scans (`test_api/test_scans.py` - 19 tests)

| Categoría | Tests | Estado |
|-----------|-------|--------|
| Listar Scans | 4 | ✅ |
| Crear Scan | 3 | ✅ |
| Obtener Scan | 2 | ✅ |
| Cancelar Scan | 2 | ✅ |
| Progreso Scan | 2 | ✅ |
| Stats | 2 | ✅ |
| Eliminar Scan | 2 | ✅ |
| Multi-tenancy | 2 | ✅ |

### Tests de CVE (`test_api/test_cve.py` - 17 tests)

| Categoría | Tests | Estado |
|-----------|-------|--------|
| Search CVEs | 4 | ✅ |
| Get CVE | 2 | ✅ |
| Lookup CVEs | 3 | ✅ |
| CVE Stats | 3 | ✅ |
| Sync Status | 2 | ✅ |
| Authentication | 3 | ✅ |

---

## 📁 Archivos Creados/Modificados

### Archivos Nuevos

```
backend/app/
├── api/v1/
│   ├── vulnerabilities.py     # 848 líneas
│   ├── scans.py               # 632 líneas
│   └── cve.py                 # 450 líneas
├── models/
│   ├── vulnerability.py       # Modelo principal
│   ├── vulnerability_comment.py
│   ├── scan.py
│   └── cve_cache.py
├── schemas/
│   ├── vulnerability.py       # 15+ schemas
│   ├── scan.py               # 12+ schemas
│   └── cve.py                # 10+ schemas
├── workers/
│   └── cve_worker.py         # Sincronización NVD
├── services/
│   └── risk_calculator.py    # Cálculo de riesgo
└── tests/test_api/
    ├── test_vulnerabilities.py  # 17 tests
    ├── test_scans.py           # 19 tests
    └── test_cve.py             # 17 tests

alembic/versions/
└── 0680cdb4620c_add_scans_vulnerabilities_cve_cache.py
```

### Archivos Modificados

```
backend/app/
├── api/v1/router.py          # Nuevos routers incluidos
├── models/__init__.py        # Exports actualizados
├── schemas/__init__.py       # Exports actualizados
└── tests/conftest.py         # Nuevas fixtures
```

---

## 🔧 Problemas Resueltos Durante el Desarrollo

### 1. DeleteResponse sin deleted_id
**Problema:** Los endpoints DELETE fallaban con ValidationError porque faltaba `deleted_id`.  
**Solución:** Agregar `deleted_id=item.id` antes de hacer el delete en vulnerabilities.py y scans.py.

### 2. Serialización de Asset en get_vulnerability
**Problema:** `PydanticSerializationError` al intentar serializar relaciones SQLAlchemy.  
**Solución:** Construir el dict de respuesta manualmente en lugar de usar `model_validate()`.

### 3. Campo severity en CVE model
**Problema:** El campo `severity` es una propiedad híbrida (readonly), no se puede asignar directamente.  
**Solución:** Usar `cvss_v3_severity` para asignar el valor en los tests.

### 4. Campo cisa_kev no existe
**Problema:** El modelo usa `in_cisa_kev` no `cisa_kev`.  
**Solución:** Actualizar filtros en cve.py y tests para usar el nombre correcto.

### 5. CVE fixture fields
**Problema:** Tests fallaban por campos incorrectos en fixtures.  
**Solución:** 
- `modified_date` → `last_modified_date`
- Eliminar `kev_date_added` (no existe en el modelo)

---

## 📊 Métricas del Día

| Métrica | Valor |
|---------|-------|
| Archivos creados | 12 |
| Archivos modificados | 5 |
| Líneas de código | ~3,500 |
| Tests escritos | 53 |
| Endpoints nuevos | 25 |
| Modelos nuevos | 4 |
| Schemas nuevos | 37+ |

---

## 🔜 Próximo: Día 6-7 (Testing + Refinamiento)

- [ ] Tests de integración end-to-end
- [ ] Integrar Nmap worker con API de scans
- [ ] Documentación de API (OpenAPI)
- [ ] Performance testing
- [ ] Revisión de seguridad

---

*Documentación generada: 30 Enero 2026*
