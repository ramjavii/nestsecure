# DÍA 3: API CRUD + Autenticación JWT

**Fecha:** 29 Enero 2026  
**Duración:** ~3 horas  
**Tests:** 82 → 132 (+50 nuevos tests)

## 📋 Resumen

En el Día 3 implementamos el sistema completo de autenticación JWT y los endpoints CRUD para usuarios y organizaciones con soporte multi-tenant.

## ✅ Objetivos Completados

### 1. Sistema de Autenticación JWT

#### Schemas de Autenticación (`app/schemas/auth.py`)
```python
# Request schemas
- LoginRequest: email + password para login JSON
- RefreshTokenRequest: refresh_token para renovar tokens

# Response schemas  
- Token: access_token + refresh_token + token_type + expires_in
- TokenPayload: datos decodificados del JWT (sub, type, exp, iat)
- AuthUser: datos mínimos del usuario autenticado
- LoginResponse: tokens + datos del usuario
```

#### Dependencias de API (`app/api/deps.py`)
```python
# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Dependencias de autenticación
get_current_user()        # Decodifica JWT y obtiene usuario
get_current_active_user() # Verifica usuario activo
get_current_superuser()   # Verifica superusuario

# Type aliases para inyección de dependencias
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]

# Autorización por rol
require_role(role: str)       # Requiere rol mínimo
require_permission(perm: str) # Requiere permiso específico
```

### 2. Endpoints de Autenticación (`app/api/v1/auth.py`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login OAuth2 (form-data) |
| POST | `/api/v1/auth/login/json` | Login JSON (alternativo) |
| POST | `/api/v1/auth/refresh` | Renovar tokens |
| GET | `/api/v1/auth/me` | Obtener usuario actual |
| POST | `/api/v1/auth/test-token` | Verificar token válido |

**Características:**
- Tokens JWT con `access_token` (30 min) y `refresh_token` (7 días)
- Verificación de usuario activo y organización activa
- Actualización de `last_login_at` en cada login

### 3. CRUD de Usuarios (`app/api/v1/users.py`)

| Método | Endpoint | Permisos | Descripción |
|--------|----------|----------|-------------|
| GET | `/users` | Autenticado | Listar usuarios (paginado) |
| POST | `/users` | Admin | Crear usuario |
| GET | `/users/me` | Autenticado | Mi perfil |
| GET | `/users/{id}` | Autenticado | Obtener usuario |
| PATCH | `/users/{id}` | Admin | Actualizar usuario |
| DELETE | `/users/{id}` | Admin | Eliminar usuario |
| PATCH | `/users/{id}/password` | Self/Admin | Cambiar contraseña |
| PATCH | `/users/{id}/activate` | Admin | Activar/desactivar |

**Características Multi-tenant:**
- Usuarios solo ven usuarios de su organización
- Superusuarios pueden ver/editar usuarios de cualquier organización
- Filtros por `search`, `role`, `is_active`
- Paginación con `page` y `page_size`

### 4. CRUD de Organizaciones (`app/api/v1/organizations.py`)

| Método | Endpoint | Permisos | Descripción |
|--------|----------|----------|-------------|
| GET | `/organizations` | Autenticado | Listar organizaciones |
| POST | `/organizations` | Superuser | Crear organización |
| GET | `/organizations/{id}` | Auth+Org | Obtener organización |
| PATCH | `/organizations/{id}` | Admin | Actualizar organización |
| DELETE | `/organizations/{id}` | Superuser | Eliminar organización |
| GET | `/organizations/{id}/stats` | Auth+Org | Estadísticas |
| PATCH | `/organizations/{id}/activate` | Superuser | Activar/desactivar |

**Características:**
- Usuarios normales solo ven su propia organización
- Superusuarios ven todas las organizaciones
- Estadísticas incluyen conteo de usuarios, assets, vulnerabilidades
- Incluye `user_count` y `asset_count` en respuestas

### 5. Integración de Routers (`app/api/v1/router.py`)

```python
api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Autenticación"])
api_router.include_router(users_router, prefix="/users", tags=["Usuarios"])
api_router.include_router(organizations_router, prefix="/organizations", tags=["Organizaciones"])

# Health check de API
@api_router.get("/health")
async def api_health() -> dict:
    return {"status": "healthy", "api_version": "v1"}
```

**Actualización de `main.py`:**
```python
from app.api.v1.router import api_router
application.include_router(api_router, prefix=settings.API_V1_PREFIX)
```

## 🧪 Tests Implementados

### Tests de Autenticación (16 tests)
```
app/tests/test_api/test_auth.py
├── TestLoginOAuth2
│   ├── test_login_success
│   ├── test_login_invalid_email
│   ├── test_login_invalid_password
│   └── test_login_inactive_user
├── TestLoginJSON
│   ├── test_login_json_success
│   └── test_login_json_invalid_credentials
├── TestRefreshToken
│   ├── test_refresh_token_success
│   ├── test_refresh_token_invalid
│   └── test_refresh_with_access_token_fails
├── TestGetMe
│   ├── test_get_me_success
│   ├── test_get_me_without_token
│   └── test_get_me_invalid_token
├── TestTestToken
│   ├── test_test_token_valid
│   └── test_test_token_expired
└── TestAuthSecurity
    ├── test_password_not_in_response
    └── test_token_includes_user_claims
```

### Tests de Usuarios (18 tests)
```
app/tests/test_api/test_users.py
├── TestListUsers (4 tests)
├── TestCreateUser (3 tests)
├── TestGetCurrentUser (1 test)
├── TestGetUser (2 tests)
├── TestUpdateUser (2 tests)
├── TestDeleteUser (2 tests)
├── TestChangePassword (2 tests)
└── TestActivateUser (2 tests)
```

### Tests de Organizaciones (16 tests)
```
app/tests/test_api/test_organizations.py
├── TestListOrganizations (3 tests)
├── TestCreateOrganization (3 tests)
├── TestGetOrganization (3 tests)
├── TestUpdateOrganization (2 tests)
├── TestDeleteOrganization (2 tests)
├── TestOrganizationStats (1 test)
└── TestActivateOrganization (2 tests)
```

## 📁 Archivos Creados/Modificados

### Creados
```
app/schemas/auth.py           # Schemas de autenticación
app/api/deps.py               # Dependencias de API
app/api/v1/auth.py            # Endpoints de auth
app/api/v1/users.py           # CRUD de usuarios
app/api/v1/organizations.py   # CRUD de organizaciones
app/api/v1/router.py          # Router agregador
app/tests/test_api/test_auth.py         # Tests de auth
app/tests/test_api/test_users.py        # Tests de usuarios
app/tests/test_api/test_organizations.py # Tests de orgs
```

### Modificados
```
app/main.py                   # Incluir API router
app/tests/conftest.py         # Fixtures de auth
```

## 🔧 Fixtures de Testing Añadidos

```python
# app/tests/conftest.py

# Fixtures de datos de prueba
test_organization    # Organización de prueba
test_user           # Usuario con rol VIEWER
test_admin          # Usuario con rol ADMIN
test_superuser      # Usuario superusuario

# Fixtures de autenticación
auth_headers_factory    # Factory para crear headers
auth_headers           # Headers para test_user
admin_auth_headers     # Headers para test_admin
superuser_auth_headers # Headers para test_superuser

# Cliente con DB inyectada
api_client            # Cliente HTTP con override de get_db
```

## 📊 Métricas Finales

| Métrica | Valor |
|---------|-------|
| Tests totales | 132 |
| Tests nuevos | 50 |
| Endpoints creados | 15 |
| Archivos nuevos | 9 |
| Líneas de código | ~2,500 |

## 🔐 Notas de Seguridad

1. **JWT Security:**
   - Tokens firmados con HS256
   - Access tokens expiran en 30 minutos
   - Refresh tokens expiran en 7 días
   - Tipo de token incluido en claims (`type: "access" | "refresh"`)

2. **Multi-tenancy:**
   - Todas las consultas filtradas por `organization_id`
   - Superusuarios bypass del filtro de organización
   - Verificación de permisos por rol

3. **Validación:**
   - Passwords con mínimo 8 caracteres
   - Emails validados con Pydantic
   - Roles validados contra enum `UserRole`

## 🐛 Problemas Resueltos

1. **bcrypt 5.0 incompatible con passlib:**
   - Solución: `pip install "bcrypt>=4.0,<5.0"`

2. **UserRole.USER no existe:**
   - Los roles válidos son: `ADMIN`, `OPERATOR`, `ANALYST`, `VIEWER`

3. **OAuth2 form requiere Content-Type específico:**
   - Usar `application/x-www-form-urlencoded` para `/login`

## 📝 Próximos Pasos (Día 4)

- Celery + Redis para tareas asíncronas
- Worker de descubrimiento de red con nmap
- Colas de escaneo con rate limiting
- ~20 nuevos tests

---

**Estado:** ✅ Completado  
**Tests:** 132/132 pasando  
**Cobertura estimada:** ~70%
