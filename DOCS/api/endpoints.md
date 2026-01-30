# API Endpoints - NESTSECURE

## Visión General

La API de NESTSECURE sigue los principios REST y está disponible en `/api/v1/`. Todas las respuestas están en formato JSON.

**URL Base:** `http://localhost:8000/api/v1`

**Documentación Interactiva:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Autenticación (`/api/v1/auth`)

### Login con OAuth2

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin@example.com&password=Password123!
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Login JSON (alternativo)

```http
POST /api/v1/auth/login/json
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "Password123!"
}
```

### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Obtener Usuario Actual

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### Test Token

```http
POST /api/v1/auth/test-token
Authorization: Bearer <access_token>
```

---

## Usuarios (`/api/v1/users`)

### Listar Usuarios

```http
GET /api/v1/users?page=1&page_size=20&role=admin&is_active=true&search=john
Authorization: Bearer <token>
```

**Parámetros:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| page | int | Página (default: 1) |
| page_size | int | Items por página (default: 20, max: 100) |
| role | string | Filtrar por rol (admin, operator, analyst, viewer) |
| is_active | bool | Filtrar por estado activo |
| search | string | Buscar en email y nombre |

### Crear Usuario

```http
POST /api/v1/users
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "email": "nuevo@example.com",
  "password": "SecurePass123!",
  "full_name": "Nuevo Usuario",
  "role": "analyst"
}
```

### Obtener Usuario

```http
GET /api/v1/users/{user_id}
Authorization: Bearer <token>
```

### Actualizar Usuario

```http
PATCH /api/v1/users/{user_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "full_name": "Nombre Actualizado",
  "role": "operator"
}
```

### Cambiar Contraseña

```http
PATCH /api/v1/users/{user_id}/password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

### Activar/Desactivar Usuario

```http
PATCH /api/v1/users/{user_id}/activate
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "is_active": false
}
```

### Eliminar Usuario

```http
DELETE /api/v1/users/{user_id}
Authorization: Bearer <admin_token>
```

---

## Organizaciones (`/api/v1/organizations`)

### Listar Organizaciones

```http
GET /api/v1/organizations?page=1&is_active=true
Authorization: Bearer <token>
```

### Crear Organización

```http
POST /api/v1/organizations
Authorization: Bearer <superuser_token>
Content-Type: application/json

{
  "name": "Nueva Empresa",
  "slug": "nueva-empresa",
  "description": "Descripción de la empresa",
  "max_assets": 500
}
```

### Obtener Organización

```http
GET /api/v1/organizations/{org_id}
Authorization: Bearer <token>
```

### Estadísticas de Organización

```http
GET /api/v1/organizations/{org_id}/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_count": 15,
  "asset_count": 234,
  "vulnerability_count": 89,
  "active_scans": 2
}
```

---

## Assets (`/api/v1/assets`)

### Listar Assets

```http
GET /api/v1/assets?status=active&criticality=high&asset_type=server&search=192.168
Authorization: Bearer <token>
```

**Parámetros:**
| Param | Tipo | Valores |
|-------|------|---------|
| status | string | active, inactive, maintenance, decommissioned |
| criticality | string | critical, high, medium, low, info |
| asset_type | string | server, workstation, router, switch, firewall, etc. |
| search | string | Buscar en IP, hostname |

### Crear Asset

```http
POST /api/v1/assets
Authorization: Bearer <operator_token>
Content-Type: application/json

{
  "ip_address": "192.168.1.100",
  "hostname": "web-server-01",
  "asset_type": "server",
  "criticality": "high",
  "description": "Servidor web principal",
  "tags": ["produccion", "web"]
}
```

### Obtener Asset

```http
GET /api/v1/assets/{asset_id}
Authorization: Bearer <token>
```

### Actualizar Asset

```http
PATCH /api/v1/assets/{asset_id}
Authorization: Bearer <operator_token>
Content-Type: application/json

{
  "criticality": "critical",
  "status": "maintenance"
}
```

### Servicios del Asset

```http
GET /api/v1/assets/{asset_id}/services
Authorization: Bearer <token>
```

### Importar Assets (CSV)

```http
POST /api/v1/assets/import
Authorization: Bearer <operator_token>
Content-Type: multipart/form-data

file=@assets.csv
```

### Exportar Assets

```http
GET /api/v1/assets/export?format=csv
Authorization: Bearer <token>
```

---

## Servicios (`/api/v1/services`)

### Listar Servicios

```http
GET /api/v1/services?port=443&protocol=tcp&state=open&asset_id=<uuid>
Authorization: Bearer <token>
```

### Crear Servicio

```http
POST /api/v1/services
Authorization: Bearer <operator_token>
Content-Type: application/json

{
  "asset_id": "uuid-del-asset",
  "port": 443,
  "protocol": "tcp",
  "service_name": "https",
  "product": "nginx",
  "version": "1.18.0",
  "state": "open"
}
```

### Actualizar Servicio

```http
PATCH /api/v1/services/{service_id}
Authorization: Bearer <operator_token>
```

### Eliminar Servicio

```http
DELETE /api/v1/services/{service_id}
Authorization: Bearer <operator_token>
```

---

## Escaneos (`/api/v1/scans`)

### Listar Escaneos

```http
GET /api/v1/scans?scan_type=quick&status=completed&order_by=created_at&order_desc=true
Authorization: Bearer <token>
```

### Crear/Iniciar Escaneo

```http
POST /api/v1/scans
Authorization: Bearer <operator_token>
Content-Type: application/json

{
  "name": "Escaneo de red interna",
  "scan_type": "quick",
  "targets": ["192.168.1.0/24", "10.0.0.1-10"],
  "options": {
    "ports": "1-1000",
    "timing": "T4"
  }
}
```

**Tipos de escaneo:**
| Tipo | Descripción |
|------|-------------|
| quick | Top 100 puertos |
| full | Todos los puertos (1-65535) |
| targeted | Puertos específicos |
| port_scan | Solo descubrimiento |
| vuln_scan | Búsqueda de vulnerabilidades |

### Obtener Escaneo

```http
GET /api/v1/scans/{scan_id}
Authorization: Bearer <token>
```

### Progreso del Escaneo

```http
GET /api/v1/scans/{scan_id}/progress
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "running",
  "progress_percent": 45,
  "current_target": "192.168.1.50",
  "targets_completed": 45,
  "targets_total": 100,
  "vulnerabilities_found": 12,
  "elapsed_time": "00:05:32",
  "estimated_remaining": "00:06:45"
}
```

### Cancelar Escaneo

```http
PATCH /api/v1/scans/{scan_id}/cancel
Authorization: Bearer <operator_token>
```

### Vulnerabilidades del Escaneo

```http
GET /api/v1/scans/{scan_id}/vulnerabilities
Authorization: Bearer <token>
```

### Estadísticas de Escaneos

```http
GET /api/v1/scans/stats
Authorization: Bearer <token>
```

---

## Vulnerabilidades (`/api/v1/vulnerabilities`)

### Listar Vulnerabilidades

```http
GET /api/v1/vulnerabilities?severity=critical&status=open&has_exploit=true&cve_id=CVE-2024
Authorization: Bearer <token>
```

**Parámetros:**
| Param | Tipo | Valores |
|-------|------|---------|
| severity | string | critical, high, medium, low, info |
| status | string | open, confirmed, in_progress, resolved, false_positive |
| has_exploit | bool | true/false |
| asset_id | uuid | Filtrar por asset |
| cve_id | string | Filtrar por CVE |
| assigned_to | uuid | Filtrar por asignación |

### Crear Vulnerabilidad

```http
POST /api/v1/vulnerabilities
Authorization: Bearer <operator_token>
Content-Type: application/json

{
  "title": "SQL Injection en formulario de login",
  "description": "Se detectó una vulnerabilidad de inyección SQL...",
  "severity": "critical",
  "asset_id": "uuid-del-asset",
  "cve_id": "CVE-2024-1234",
  "cvss_score": 9.8,
  "solution": "Sanitizar inputs y usar prepared statements"
}
```

### Obtener Vulnerabilidad

```http
GET /api/v1/vulnerabilities/{vuln_id}
Authorization: Bearer <token>
```

### Actualizar Vulnerabilidad

```http
PATCH /api/v1/vulnerabilities/{vuln_id}
Authorization: Bearer <operator_token>
Content-Type: application/json

{
  "status": "in_progress",
  "assigned_to_id": "uuid-del-usuario"
}
```

### Actualización Masiva

```http
PATCH /api/v1/vulnerabilities/bulk
Authorization: Bearer <operator_token>
Content-Type: application/json

{
  "vulnerability_ids": ["uuid1", "uuid2", "uuid3"],
  "update": {
    "status": "resolved"
  }
}
```

### Añadir Comentario

```http
POST /api/v1/vulnerabilities/{vuln_id}/comment
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Se ha aplicado el parche de seguridad"
}
```

### Estadísticas de Vulnerabilidades

```http
GET /api/v1/vulnerabilities/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total": 156,
  "by_severity": {
    "critical": 12,
    "high": 34,
    "medium": 67,
    "low": 43
  },
  "by_status": {
    "open": 89,
    "in_progress": 23,
    "resolved": 44
  },
  "with_exploit": 15,
  "average_age_days": 12.5,
  "resolution_rate": 0.28
}
```

---

## CVE (`/api/v1/cve`)

### Buscar CVEs

```http
GET /api/v1/cve/search?keyword=apache&severity=critical&min_cvss=9.0&has_exploit=true
Authorization: Bearer <token>
```

**Parámetros:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| keyword | string | Buscar en descripción |
| severity | string | critical, high, medium, low |
| min_cvss | float | CVSS mínimo |
| max_cvss | float | CVSS máximo |
| has_exploit | bool | Solo con exploit |
| in_cisa_kev | bool | Solo en CISA KEV |
| vendor | string | Filtrar por vendor |
| product | string | Filtrar por producto |

### Obtener CVE

```http
GET /api/v1/cve/CVE-2024-1234
Authorization: Bearer <token>
```

### Lookup Múltiples CVEs

```http
POST /api/v1/cve/lookup
Authorization: Bearer <token>
Content-Type: application/json

{
  "cve_ids": ["CVE-2024-1234", "CVE-2024-5678", "CVE-2023-9999"]
}
```

### Estadísticas de CVEs

```http
GET /api/v1/cve/stats
Authorization: Bearer <token>
```

### Sincronizar con NVD (Admin)

```http
POST /api/v1/cve/sync
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "full_sync": false
}
```

### Estado de Sincronización

```http
GET /api/v1/cve/sync/status
Authorization: Bearer <admin_token>
```

---

## Dashboard (`/api/v1/dashboard`)

### Estadísticas Generales

```http
GET /api/v1/dashboard/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
  "assets": {
    "total": 234,
    "by_status": {"active": 200, "inactive": 34},
    "by_criticality": {"critical": 10, "high": 45, ...}
  },
  "vulnerabilities": {
    "total": 156,
    "by_severity": {"critical": 12, "high": 34, ...},
    "open_count": 89
  },
  "scans": {
    "total": 50,
    "running": 2,
    "last_scan": "2026-01-30T10:00:00Z"
  }
}
```

### Assets Recientes

```http
GET /api/v1/dashboard/recent-assets?limit=10
Authorization: Bearer <token>
```

### Assets de Mayor Riesgo

```http
GET /api/v1/dashboard/top-risky-assets?limit=10
Authorization: Bearer <token>
```

### Distribución de Puertos

```http
GET /api/v1/dashboard/ports-distribution
Authorization: Bearer <token>
```

### Timeline de Assets

```http
GET /api/v1/dashboard/asset-timeline?days=30
Authorization: Bearer <token>
```

### Tendencia de Vulnerabilidades

```http
GET /api/v1/dashboard/vulnerability-trend?days=30
Authorization: Bearer <token>
```

---

## Códigos de Estado

| Código | Significado |
|--------|-------------|
| 200 | OK - Operación exitosa |
| 201 | Created - Recurso creado |
| 204 | No Content - Eliminación exitosa |
| 400 | Bad Request - Datos inválidos |
| 401 | Unauthorized - Token inválido/expirado |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 409 | Conflict - Recurso ya existe |
| 422 | Unprocessable Entity - Error de validación |
| 500 | Internal Server Error - Error del servidor |

## Paginación

Todas las listas soportan paginación:

```http
GET /api/v1/assets?page=2&page_size=50
```

**Response:**
```json
{
  "items": [...],
  "total": 234,
  "page": 2,
  "page_size": 50,
  "pages": 5
}
```

---

*Última actualización: 30 Enero 2026*
