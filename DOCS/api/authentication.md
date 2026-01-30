# Autenticación - NESTSECURE

## Visión General

NESTSECURE utiliza autenticación basada en JWT (JSON Web Tokens) con soporte para:
- Access tokens (corta duración)
- Refresh tokens (larga duración)
- Roles y permisos
- Multi-tenancy (organizaciones)

## Flujo de Autenticación

```
┌─────────┐                    ┌─────────┐
│ Cliente │                    │ Backend │
└────┬────┘                    └────┬────┘
     │                              │
     │  POST /api/v1/auth/login     │
     │  (email + password)          │
     │─────────────────────────────▶│
     │                              │
     │  {access_token, refresh_token}
     │◀─────────────────────────────│
     │                              │
     │  GET /api/v1/assets          │
     │  Authorization: Bearer <token>
     │─────────────────────────────▶│
     │                              │
     │  200 OK + data               │
     │◀─────────────────────────────│
     │                              │
     │  (token expira)              │
     │                              │
     │  POST /api/v1/auth/refresh   │
     │  {refresh_token}             │
     │─────────────────────────────▶│
     │                              │
     │  {nuevo access_token}        │
     │◀─────────────────────────────│
```

## Endpoints de Autenticación

### 1. Login (OAuth2 Form)

El método principal de login usando OAuth2 password flow:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=Password123!"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 2. Login (JSON)

Alternativa usando JSON en el body:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Password123!"
  }'
```

### 3. Refresh Token

Obtener nuevo access token usando el refresh token:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 4. Obtener Usuario Actual

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "full_name": "Admin User",
  "role": "admin",
  "organization_id": "550e8400-e29b-41d4-a716-446655440001",
  "organization": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "My Company",
    "slug": "my-company"
  },
  "is_active": true,
  "is_superuser": false,
  "last_login_at": "2026-01-30T10:30:00Z"
}
```

### 5. Test Token

Verificar que un token es válido:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/test-token" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Tokens JWT

### Estructura del Token

Un JWT tiene tres partes separadas por puntos:

```
header.payload.signature
```

**Ejemplo de payload decodificado:**
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "type": "access",
  "exp": 1706615400,
  "iat": 1706613600,
  "organization_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

### Configuración de Tokens

| Parámetro | Valor Default | Descripción |
|-----------|---------------|-------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Duración del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Duración del refresh token |
| `JWT_ALGORITHM` | HS256 | Algoritmo de firma |

### Tipos de Token

| Tipo | Duración | Uso |
|------|----------|-----|
| `access` | 30 min | Autenticar requests |
| `refresh` | 7 días | Obtener nuevo access token |

## Sistema de Roles

### Roles Disponibles

| Rol | Nivel | Descripción |
|-----|-------|-------------|
| `admin` | 4 | Administrador - acceso total |
| `operator` | 3 | Operador - CRUD completo |
| `analyst` | 2 | Analista - lectura + comentarios |
| `viewer` | 1 | Viewer - solo lectura |

### Jerarquía de Permisos

```
admin (4)
  └── Puede todo
      └── operator (3)
          └── CRUD de datos
              └── analyst (2)
                  └── Lectura + comentarios
                      └── viewer (1)
                          └── Solo lectura
```

### Permisos por Endpoint

| Endpoint | Viewer | Analyst | Operator | Admin |
|----------|--------|---------|----------|-------|
| GET (listar/ver) | ✅ | ✅ | ✅ | ✅ |
| POST (crear) | ❌ | ❌ | ✅ | ✅ |
| PATCH (actualizar) | ❌ | ❌ | ✅ | ✅ |
| DELETE (eliminar) | ❌ | ❌ | ❌ | ✅ |
| Comentarios | ❌ | ✅ | ✅ | ✅ |
| Gestión usuarios | ❌ | ❌ | ❌ | ✅ |

## Multi-tenancy

### Organizaciones

Cada usuario pertenece a una organización (tenant). Los datos están completamente aislados entre organizaciones.

```
Organización A
├── Usuarios de A
├── Assets de A
├── Vulnerabilidades de A
└── Scans de A

Organización B
├── Usuarios de B
├── Assets de B
├── Vulnerabilidades de B
└── Scans de B
```

### Reglas de Acceso

1. **Usuarios normales**: Solo ven datos de su organización
2. **Superusers**: Pueden acceder a todas las organizaciones
3. **Filtrado automático**: Todas las queries incluyen `organization_id`

## Usando la Autenticación

### En cURL

```bash
# 1. Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=Password123!" | jq -r '.access_token')

# 2. Usar el token
curl -X GET "http://localhost:8000/api/v1/assets" \
  -H "Authorization: Bearer $TOKEN"
```

### En JavaScript/TypeScript

```typescript
// Login
const response = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: new URLSearchParams({
    username: 'admin@example.com',
    password: 'Password123!',
  }),
});

const { access_token, refresh_token } = await response.json();

// Usar el token
const assets = await fetch('/api/v1/assets', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
  },
});
```

### En Python

```python
import httpx

# Login
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/auth/login",
        data={
            "username": "admin@example.com",
            "password": "Password123!",
        },
    )
    tokens = response.json()
    access_token = tokens["access_token"]
    
    # Usar el token
    response = await client.get(
        "http://localhost:8000/api/v1/assets",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assets = response.json()
```

## Manejo de Errores

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

**Causas:**
- Token no proporcionado
- Token malformado
- Token expirado
- Firma inválida

### 403 Forbidden

```json
{
  "detail": "Not enough permissions"
}
```

**Causas:**
- Rol insuficiente para la operación
- Acceso a recurso de otra organización
- Usuario desactivado

## Seguridad

### Mejores Prácticas

1. **Almacenar tokens de forma segura**
   - HttpOnly cookies para web
   - Secure storage para móvil

2. **Renovar tokens antes de expirar**
   - Implementar interceptor de refresh

3. **Logout**
   - Eliminar tokens del cliente
   - (Opcional) Blacklist de tokens en servidor

4. **HTTPS en producción**
   - Nunca transmitir tokens en HTTP

### Configuración de Producción

```env
# .env
SECRET_KEY=your-very-long-and-random-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15  # Reducir en producción
REFRESH_TOKEN_EXPIRE_DAYS=1     # Reducir en producción
```

## Errores Comunes

### "Invalid credentials"

```bash
# Verificar que el usuario existe y está activo
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=WRONG"
```

### "Token has expired"

```bash
# Usar el refresh token para obtener uno nuevo
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "..."}'
```

### "Organization not active"

El usuario pertenece a una organización desactivada. Contactar al administrador del sistema.

---

*Última actualización: 30 Enero 2026*
