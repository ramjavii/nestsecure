# =============================================================================
# NESTSECURE - FASE 2: PLAN COMPLETO DE IMPLEMENTACIÓN
# =============================================================================
# Fecha Inicio: 2026-02-03 (Día 8)
# Duración Estimada: 10-12 días de desarrollo
# Objetivo: Sistema completo, funcional y desplegable en NUC
# =============================================================================

## 📋 ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estado Actual (Fase 1 Completada)](#estado-actual)
3. [Arquitectura Fase 2](#arquitectura-fase-2)
4. [Días 8-9: OpenVAS/GVM Integration](#días-8-9)
5. [Días 10-11: Nmap Mejorado + Nuclei](#días-10-11)
6. [Día 12: Error Handling Global](#día-12)
7. [Días 13-15: Frontend React](#días-13-15)
8. [Día 16: Docker Production + NUC Deploy](#día-16)
9. [Día 17: Testing E2E + Validación](#día-17)
10. [Checklist Final](#checklist-final)

---

## 📊 RESUMEN EJECUTIVO

### Objetivos de la Fase 2

La Fase 2 transforma NESTSECURE de un backend funcional a un **sistema completo de gestión de vulnerabilidades** listo para producción en tu NUC.

**Componentes Clave:**
- ✅ **Backend API Completa** - Ya implementada en Fase 1
- 🔧 **OpenVAS Integration** - Día 8 (completado)
- 🔧 **Scanners Adicionales** - Días 10-11
- 🔧 **Error Handling Robusto** - Día 12
- 🎨 **Frontend React** - Días 13-15
- 🚀 **Production Deployment** - Día 16
- ✅ **Testing E2E** - Día 17

### Métricas Objetivo

| Métrica | Fase 1 | Objetivo Fase 2 |
|---------|--------|-----------------|
| Tests | 265 | 400+ |
| Cobertura | ~85% | >90% |
| Endpoints API | 64 | 80+ |
| Scanners | 0 funcionales | 3 completos |
| Frontend | No | Completo |
| Deployment | Local | NUC Production |

---

## 🎯 ESTADO ACTUAL (FASE 1 COMPLETADA)

### ✅ Componentes Implementados

| Componente | Estado | Tests | Notas |
|------------|--------|-------|-------|
| FastAPI Backend | ✅ | 265 | Auth, CRUD completo |
| PostgreSQL + TimescaleDB | ✅ | - | Multi-tenant |
| Redis + Celery | ✅ | - | Async tasks |
| Auth JWT | ✅ | 16 | Access + Refresh tokens |
| Multi-tenancy | ✅ | - | Organizations |
| Assets Management | ✅ | 23 | CRUD completo |
| Dashboard API | ✅ | 13 | Stats y métricas |
| OpenVAS/GVM | ✅ | - | Día 8 completado |
| Prometheus Metrics | ✅ | - | Monitoreo básico |
| Structured Logging | ✅ | - | JSON + context |

### 📁 Estructura Actual

```
NESTSECURE/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # 64 endpoints
│   │   ├── models/          # 6 modelos principales
│   │   ├── schemas/         # 50+ schemas
│   │   ├── workers/         # Celery tasks
│   │   ├── integrations/
│   │   │   └── gvm/        # ✅ OpenVAS completo
│   │   ├── core/           # Config, security, metrics
│   │   └── utils/          # Helpers, validators
│   ├── alembic/            # Migraciones DB
│   └── tests/              # 265 tests
├── docker-compose.dev.yml  # ✅ Con GVM
└── DOCS/
    └── DESARROLLO/         # Días 1-8 documentados
```

---

## 🏗️ ARQUITECTURA FASE 2

```
┌────────────────────────────────────────────────────────────────────┐
│                        NESTSECURE - FASE 2                          │
├────────────────────────────────────────────────────────────────────┤
│  FRONTEND (React + TypeScript)                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Dashboard │ Assets │ Scans │ Vulnerabilities │ Reports     │  │
│  │  ├── Login/Auth                                              │  │
│  │  ├── Real-time scan progress                                 │  │
│  │  ├── Vulnerability management                                │  │
│  │  └── Charts & metrics                                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────┤
│  BACKEND API (FastAPI)                                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Auth │ Assets │ Scans │ Vulnerabilities │ CVE │ Reports    │  │
│  │  + Error Handling Global                                     │  │
│  │  + Rate Limiting                                             │  │
│  │  + Request Validation                                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────┤
│  SCANNERS (Celery Workers)                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  OpenVAS/GVM    Nmap Enhanced    Nuclei    [Future: ZAP]    │  │
│  │  ✅ Completo    🔧 Mejorado      🔧 Nuevo   📝 Placeholder   │  │
│  └──────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL │ Redis │ Prometheus │ Nginx │ Docker          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 📅 DÍAS 8-9: OPENVAS/GVM INTEGRATION

**Estado:** ✅ **COMPLETADO**  
**Fecha:** 2026-02-03  
**Tests:** 265/265 passing  
**Duración Real:** 1 día

### ✅ Implementado

#### 8.1 Docker GVM Setup
- ✅ Servicio GVM en docker-compose.dev.yml
- ✅ Volúmenes configurados (gvm_data, gvm_scap, gvm_cert, openvas_plugins)
- ✅ Health check configurado
- ✅ Memory limits (4GB reserved, 6GB limit)
- ✅ Ports: 9392 (web), 9390 (API)

#### 8.2 GVM Integration Module
```
app/integrations/gvm/
├── __init__.py              ✅ Exports completos
├── client.py (~700 lines)   ✅ GVMClient con singleton
├── models.py (~550 lines)   ✅ Dataclasses + Enums
├── parser.py (~350 lines)   ✅ XML Parser
└── exceptions.py (~170 lines) ✅ 7 excepciones custom
```

#### 8.3 OpenVAS Worker
```python
app/workers/openvas_worker.py (~450 lines)
├── openvas_full_scan()        # Orquesta scan completo
├── openvas_create_target()    # Crea target en GVM
├── openvas_check_status()     # Polling de estado
├── openvas_get_results()      # Obtiene vulnerabilidades
├── openvas_stop_scan()        # Cancela scan
├── openvas_cleanup()          # Limpia recursos
└── openvas_health_check()     # Verifica GVM
```

#### 8.4 Scans API
```
app/api/v1/scans.py (~460 lines)
├── POST   /scans                 # Crear y ejecutar scan
├── GET    /scans                 # Listar con filtros
├── GET    /scans/{id}            # Detalle de scan
├── GET    /scans/{id}/status     # Estado actual
├── GET    /scans/{id}/results    # Vulnerabilidades
├── POST   /scans/{id}/stop       # Detener scan
└── DELETE /scans/{id}            # Eliminar scan
```

#### 8.5 Modelo de Scan Actualizado
```python
# app/models/scan.py
class Scan(Base, UUIDMixin, TimestampMixin):
    # GVM Integration Fields
    gvm_target_id: Optional[str]
    gvm_task_id: Optional[str]
    gvm_report_id: Optional[str]
```

### 📊 Resultados Día 8

| Métrica | Valor |
|---------|-------|
| Archivos creados | 7 |
| Archivos modificados | 4 |
| Líneas de código | ~2,000 |
| Tests | 265 passing |
| Tiempo real | 1 día |

---

## 📅 DÍAS 10-11: NMAP MEJORADO + NUCLEI

**Estado:** 🔧 **POR IMPLEMENTAR**  
**Duración Estimada:** 2 días  
**Objetivo:** Agregar scanners adicionales con integración completa

### Día 10: Nmap Enhanced Scanner

#### 10.1 Nmap Integration Module
```python
# app/integrations/nmap/
├── __init__.py
├── client.py              # NmapScanner class
├── models.py              # NmapResult, NmapHost, NmapPort
├── parser.py              # Parse XML output
└── exceptions.py          # NmapError, NmapTimeoutError
```

**Características:**
- Wrapper mejorado sobre python-nmap
- Detección de OS y servicios
- Scripts NSE para detección de vulnerabilidades
- Rate limiting y timeouts configurables
- Output en JSON y XML

#### 10.2 Nmap Worker Mejorado
```python
# app/workers/nmap_worker.py (reemplazo completo)

@celery_app.task
def nmap_discovery_scan(targets, options):
    """Descubrimiento de hosts vivos."""
    # -sn ping scan
    pass

@celery_app.task
def nmap_port_scan(host_id, scan_type):
    """Escaneo de puertos con detección de servicios."""
    # -sV -sC para service detection
    pass

@celery_app.task
def nmap_vulnerability_scan(host_id):
    """Escaneo con scripts NSE de vulnerabilidades."""
    # --script vuln,exploit
    pass

@celery_app.task
def nmap_os_detection(host_id):
    """Detección de sistema operativo."""
    # -O
    pass
```

#### 10.3 Perfiles de Escaneo Nmap
```python
# app/integrations/nmap/profiles.py

SCAN_PROFILES = {
    "quick": "-sV --version-light -T4",
    "full": "-sV -sC -O -T3",
    "stealth": "-sS -T2",
    "aggressive": "-A -T4",
    "vulnerability": "-sV --script vuln,exploit -T3",
    "web": "-p 80,443,8080,8443 -sV --script http-*"
}
```

#### 10.4 API Endpoints Nmap
```
POST   /api/v1/nmap/scan/discovery     # Quick discovery
POST   /api/v1/nmap/scan/ports          # Port scan
POST   /api/v1/nmap/scan/vulnerabilities  # NSE vuln scan
GET    /api/v1/nmap/profiles            # Available profiles
```

### Día 11: Nuclei Scanner

#### 11.1 Nuclei Integration
```python
# app/integrations/nuclei/
├── __init__.py
├── client.py              # NucleiScanner class
├── models.py              # NucleiResult, NucleiTemplate
├── parser.py              # Parse JSONL output
└── exceptions.py          # NucleiError
```

**Características:**
- Wrapper sobre Nuclei CLI
- Templates customizados
- Severidad mapping a nuestro sistema
- Rate limiting
- Target validation

#### 11.2 Nuclei Worker
```python
# app/workers/nuclei_worker.py

@celery_app.task
def nuclei_web_scan(target_url, templates):
    """Escaneo web con Nuclei."""
    pass

@celery_app.task
def nuclei_update_templates():
    """Actualizar templates de Nuclei."""
    pass

@celery_app.task
def nuclei_custom_scan(target, template_path):
    """Escaneo con templates custom."""
    pass
```

#### 11.3 Nuclei Template Manager
```python
# app/integrations/nuclei/template_manager.py

class TemplateManager:
    def list_templates(self) -> List[Template]:
        """Listar templates disponibles."""
        pass
    
    def update_templates(self) -> bool:
        """Actualizar desde GitHub."""
        pass
    
    def filter_by_severity(self, severity: str) -> List[Template]:
        """Filtrar por severidad."""
        pass
    
    def filter_by_tag(self, tag: str) -> List[Template]:
        """Filtrar por tag (cve, xss, sqli, etc)."""
        pass
```

#### 11.4 Docker Setup Nuclei
```yaml
# docker-compose.dev.yml
nuclei:
  image: projectdiscovery/nuclei:latest
  volumes:
    - nuclei_templates:/root/nuclei-templates
    - ./nuclei_custom:/custom-templates
  command: ["sleep", "infinity"]  # Keep running
```

#### 11.5 API Endpoints Nuclei
```
POST   /api/v1/nuclei/scan              # Run scan
GET    /api/v1/nuclei/templates         # List templates
POST   /api/v1/nuclei/templates/update  # Update templates
GET    /api/v1/nuclei/templates/stats   # Template stats
```

### 📦 Entregables Días 10-11

| Componente | Archivos | Tests | LOC |
|------------|----------|-------|-----|
| Nmap Integration | 5 | 20 | ~800 |
| Nmap Worker | 1 | 15 | ~500 |
| Nuclei Integration | 5 | 15 | ~600 |
| Nuclei Worker | 1 | 10 | ~400 |
| API Endpoints | 2 | 20 | ~400 |
| **Total** | **14** | **80** | **~2,700** |

---

## 📅 DÍA 12: ERROR HANDLING GLOBAL

**Estado:** 🔧 **POR IMPLEMENTAR**  
**Duración Estimada:** 1 día  
**Objetivo:** Sistema robusto de manejo de errores para producción

### 12.1 Exception Hierarchy Completa

```python
# app/core/exceptions.py (~600 lines)

class NestSecureException(Exception):
    """Base exception."""
    def __init__(self, message, code, status_code=500, details=None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
    
    def to_dict(self):
        """RFC 7807 Problem Details."""
        return {
            "type": f"https://nestsecure.io/errors/{self.code}",
            "title": self.__class__.__name__,
            "status": self.status_code,
            "detail": self.message,
            **self.details
        }

# Authentication Errors
class AuthenticationError(NestSecureException):
    def __init__(self, message="Authentication failed"):
        super().__init__(message, "AUTH_001", 401)

class InvalidCredentialsError(AuthenticationError):
    def __init__(self):
        super().__init__("Invalid email or password", "AUTH_002", 401)

class TokenExpiredError(AuthenticationError):
    def __init__(self):
        super().__init__("Token has expired", "AUTH_003", 401)

class InvalidTokenError(AuthenticationError):
    def __init__(self):
        super().__init__("Invalid or malformed token", "AUTH_004", 401)

# Authorization Errors
class AuthorizationError(NestSecureException):
    def __init__(self, message="Insufficient permissions"):
        super().__init__(message, "AUTHZ_001", 403)

class InsufficientPermissionsError(AuthorizationError):
    def __init__(self, required_role=None):
        msg = f"Requires role: {required_role}" if required_role else "Insufficient permissions"
        super().__init__(msg, "AUTHZ_002", 403)

# Resource Errors
class NotFoundError(NestSecureException):
    def __init__(self, resource, resource_id=None):
        msg = f"{resource} not found"
        if resource_id:
            msg += f": {resource_id}"
        super().__init__(msg, "RESOURCE_001", 404)

class AlreadyExistsError(NestSecureException):
    def __init__(self, resource, field=None):
        msg = f"{resource} already exists"
        if field:
            msg += f" with {field}"
        super().__init__(msg, "RESOURCE_002", 409)

# Validation Errors
class ValidationError(NestSecureException):
    def __init__(self, message, field=None):
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_001", 422, details)

class InvalidInputError(ValidationError):
    pass

# Scanner Errors
class ScannerError(NestSecureException):
    def __init__(self, scanner, message):
        super().__init__(f"{scanner}: {message}", "SCANNER_001", 500)

class ScanTimeoutError(ScannerError):
    def __init__(self, scanner):
        super().__init__(scanner, "Scan timed out", "SCANNER_002", 504)

class ScannerUnavailableError(ScannerError):
    def __init__(self, scanner):
        super().__init__(scanner, "Scanner is unavailable", "SCANNER_003", 503)

# GVM Specific
class GVMError(ScannerError):
    def __init__(self, message):
        super().__init__("GVM", message)

class GVMConnectionError(GVMError):
    def __init__(self):
        super().__init__("Failed to connect to GVM")

# Database Errors
class DatabaseError(NestSecureException):
    def __init__(self, message):
        super().__init__(message, "DB_001", 500)

class DatabaseConnectionError(DatabaseError):
    def __init__(self):
        super().__init__("Database connection failed", "DB_002", 503)

# External Service Errors
class ExternalServiceError(NestSecureException):
    def __init__(self, service, message):
        super().__init__(f"{service}: {message}", "EXTERNAL_001", 502)

class NVDAPIError(ExternalServiceError):
    def __init__(self, message):
        super().__init__("NVD API", message)

# Rate Limiting
class RateLimitError(NestSecureException):
    def __init__(self, retry_after=60):
        super().__init__(
            "Rate limit exceeded",
            "RATE_LIMIT_001",
            429,
            {"retry_after": retry_after}
        )
```

### 12.2 Global Exception Handlers

```python
# app/core/exception_handlers.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.exceptions import NestSecureException
from app.utils.logger import get_logger

logger = get_logger(__name__)

async def nestsecure_exception_handler(
    request: Request,
    exc: NestSecureException
) -> JSONResponse:
    """Handler para todas las excepciones custom."""
    
    # Log según severidad
    if exc.status_code >= 500:
        logger.error(
            f"Server error: {exc.message}",
            extra={
                "error_code": exc.code,
                "path": request.url.path,
                "method": request.method,
                "details": exc.details
            }
        )
    else:
        logger.warning(
            f"Client error: {exc.message}",
            extra={"error_code": exc.code, "path": request.url.path}
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handler para errores de validación Pydantic."""
    
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error on {request.url.path}",
        extra={"errors": errors}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "type": "https://nestsecure.io/errors/VALIDATION_001",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request validation failed",
            "errors": errors
        }
    )

async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handler para excepciones no controladas."""
    
    logger.exception(
        f"Unhandled exception on {request.url.path}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_str": str(exc)
        }
    )
    
    # En producción, no exponer detalles
    from app.config import get_settings
    settings = get_settings()
    
    detail = str(exc) if settings.ENVIRONMENT == "development" else "Internal server error"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "https://nestsecure.io/errors/INTERNAL_001",
            "title": "Internal Server Error",
            "status": 500,
            "detail": detail
        }
    )

def register_exception_handlers(app):
    """Registrar todos los handlers."""
    from fastapi.exceptions import RequestValidationError
    
    app.add_exception_handler(NestSecureException, nestsecure_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
```

### 12.3 Request Validation Middleware

```python
# app/core/middleware.py

from fastapi import Request
from app.core.exceptions import ValidationError
import re

IP_PATTERN = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
CIDR_PATTERN = re.compile(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$')

async def validate_scan_target(target: str) -> None:
    """Validar que un target sea seguro."""
    
    # Prevenir escaneos a localhost/private IPs
    private_ranges = [
        "127.", "10.", "192.168.", "172.16.",
        "172.17.", "172.18.", "172.19.", "172.20.",
        "172.21.", "172.22.", "172.23.", "172.24.",
        "172.25.", "172.26.", "172.27.", "172.28.",
        "172.29.", "172.30.", "172.31."
    ]
    
    if any(target.startswith(pr) for pr in private_ranges):
        raise ValidationError(
            "Scanning private/local IPs is not allowed",
            field="target"
        )
    
    # Validar formato
    if not (IP_PATTERN.match(target) or CIDR_PATTERN.match(target)):
        raise ValidationError(
            "Invalid IP or CIDR format",
            field="target"
        )
```

### 12.4 Circuit Breaker para Servicios Externos

```python
# app/core/circuit_breaker.py

from datetime import datetime, timedelta
from typing import Callable, Any
from app.core.exceptions import ExternalServiceError

class CircuitBreaker:
    """Circuit breaker para servicios externos."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_duration: int = 60,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.name = name
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Ejecutar función con circuit breaker."""
        
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise ExternalServiceError(
                    self.name,
                    "Circuit breaker is OPEN"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Reset on successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Increment failure counter."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try again."""
        return (
            self.last_failure_time is not None and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout_duration)
        )

# Singleton instances
gvm_circuit_breaker = CircuitBreaker(name="GVM")
nvd_circuit_breaker = CircuitBreaker(name="NVD")
```

### 12.5 Retry Logic

```python
# app/utils/retry.py

from functools import wraps
from time import sleep
from typing import Callable
from app.utils.logger import get_logger

logger = get_logger(__name__)

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator para reintentar operaciones fallidas."""
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"Max retries reached for {func.__name__}",
                            extra={"attempts": attempt, "error": str(e)}
                        )
                        raise
                    
                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__}",
                        extra={"delay": current_delay, "error": str(e)}
                    )
                    
                    sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
        
        return wrapper
    return decorator

# Ejemplo de uso
@retry(max_attempts=3, delay=2.0, exceptions=(GVMConnectionError,))
def connect_to_gvm():
    """Conectar a GVM con retry."""
    pass
```

### 📦 Entregables Día 12

| Componente | LOC | Tests |
|------------|-----|-------|
| Exception Classes | ~600 | 20 |
| Exception Handlers | ~200 | 10 |
| Circuit Breaker | ~150 | 8 |
| Retry Logic | ~100 | 5 |
| Validation Middleware | ~150 | 7 |
| **Total** | **~1,200** | **50** |

---

## 📅 DÍAS 13-15: FRONTEND REACT

**Estado:** 🔧 **POR IMPLEMENTAR**  
**Duración Estimada:** 3 días  
**Objetivo:** Frontend completo y funcional

### Stack Tecnológico

```
Frontend/
├── React 18 + TypeScript
├── Vite (build tool)
├── TanStack Query (data fetching)
├── React Router v6 (routing)
├── Tailwind CSS (styling)
├── shadcn/ui (components)
├── Recharts (charts)
├── React Hook Form (forms)
└── Zod (validation)
```

### Día 13: Setup + Auth + Layout

#### 13.1 Project Setup

```bash
# Crear proyecto
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# Dependencias principales
npm install @tanstack/react-query axios react-router-dom
npm install -D tailwindcss postcss autoprefixer
npm install @hookform/resolvers zod react-hook-form
npm install lucide-react recharts date-fns

# Setup Tailwind
npx tailwindcss init -p

# shadcn/ui components
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card input form table
npx shadcn-ui@latest add dropdown-menu dialog alert toast
npx shadcn-ui@latest add badge progress tabs
```

#### 13.2 Estructura del Proyecto

```
frontend/
├── src/
│   ├── api/                  # API client
│   │   ├── client.ts         # Axios instance
│   │   ├── auth.ts           # Auth endpoints
│   │   ├── assets.ts         # Assets endpoints
│   │   ├── scans.ts          # Scans endpoints
│   │   └── vulnerabilities.ts
│   │
│   ├── components/           # React components
│   │   ├── ui/               # shadcn components
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── dashboard/
│   │   │   ├── StatsCard.tsx
│   │   │   └── ChartWidget.tsx
│   │   ├── assets/
│   │   │   ├── AssetList.tsx
│   │   │   ├── AssetDetail.tsx
│   │   │   └── AssetForm.tsx
│   │   ├── scans/
│   │   │   ├── ScanList.tsx
│   │   │   ├── ScanForm.tsx
│   │   │   └── ScanProgress.tsx
│   │   └── vulnerabilities/
│   │       ├── VulnList.tsx
│   │       ├── VulnDetail.tsx
│   │       └── VulnFilters.tsx
│   │
│   ├── hooks/                # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useAssets.ts
│   │   ├── useScans.ts
│   │   └── useWebSocket.ts
│   │
│   ├── pages/                # Page components
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Assets.tsx
│   │   ├── AssetDetail.tsx
│   │   ├── Scans.tsx
│   │   ├── ScanDetail.tsx
│   │   ├── Vulnerabilities.tsx
│   │   └── Settings.tsx
│   │
│   ├── store/                # State management
│   │   ├── authStore.ts      # Zustand store
│   │   └── types.ts
│   │
│   ├── utils/
│   │   ├── constants.ts
│   │   ├── formatters.ts
│   │   └── validators.ts
│   │
│   ├── types/                # TypeScript types
│   │   ├── api.ts
│   │   ├── models.ts
│   │   └── index.ts
│   │
│   ├── App.tsx
│   ├── main.tsx
│   └── router.tsx            # React Router config
│
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

#### 13.3 API Client

```typescript
// src/api/client.ts
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor para agregar token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor para refresh token
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = localStorage.getItem('refresh_token');
            const response = await this.client.post('/auth/refresh', {
              refresh_token: refreshToken,
            });

            const { access_token } = response.data;
            localStorage.setItem('access_token', access_token);

            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  getClient(): AxiosInstance {
    return this.client;
  }
}

export const apiClient = new APIClient().getClient();
```

```typescript
// src/api/auth.ts
import { apiClient } from './client';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    role: string;
  };
}

export const authAPI = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post('/auth/login/json', data);
    return response.data;
  },

  getMe: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};
```

#### 13.4 Authentication

```typescript
// src/hooks/useAuth.ts
import { create } from 'zustand';
import { authAPI, LoginRequest } from '@/api/auth';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (credentials) => {
    const response = await authAPI.login(credentials);
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
    set({ user: response.user, isAuthenticated: true });
  },

  logout: () => {
    authAPI.logout();
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        set({ isLoading: false, isAuthenticated: false });
        return;
      }

      const user = await authAPI.getMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
```

```typescript
// src/components/auth/ProtectedRoute.tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/hooks/useAuth';

export const ProtectedRoute = () => {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
```

#### 13.5 Layout Components

```typescript
// src/components/layout/Layout.tsx
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export const Layout = () => {
  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
```

#### 13.6 Router Setup

```typescript
// src/router.tsx
import { createBrowserRouter } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { Login } from '@/pages/Login';
import { Dashboard } from '@/pages/Dashboard';
import { Assets } from '@/pages/Assets';
import { Scans } from '@/pages/Scans';
import { Vulnerabilities } from '@/pages/Vulnerabilities';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <Layout />,
        children: [
          { index: true, element: <Dashboard /> },
          { path: 'assets', element: <Assets /> },
          { path: 'scans', element: <Scans /> },
          { path: 'vulnerabilities', element: <Vulnerabilities /> },
        ],
      },
    ],
  },
]);
```

### Día 14: Assets + Scans UI

#### 14.1 Assets Management

```typescript
// src/api/assets.ts
import { apiClient } from './client';

export const assetsAPI = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
  }) => {
    const response = await apiClient.get('/assets', { params });
    return response.data;
  },

  get: async (id: string) => {
    const response = await apiClient.get(`/assets/${id}`);
    return response.data;
  },

  create: async (data: any) => {
    const response = await apiClient.post('/assets', data);
    return response.data;
  },

  update: async (id: string, data: any) => {
    const response = await apiClient.put(`/assets/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    await apiClient.delete(`/assets/${id}`);
  },
};
```

```typescript
// src/hooks/useAssets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assetsAPI } from '@/api/assets';

export const useAssets = (params?: any) => {
  return useQuery({
    queryKey: ['assets', params],
    queryFn: () => assetsAPI.list(params),
  });
};

export const useAsset = (id: string) => {
  return useQuery({
    queryKey: ['asset', id],
    queryFn: () => assetsAPI.get(id),
    enabled: !!id,
  });
};

export const useCreateAsset = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: assetsAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
};
```

```typescript
// src/pages/Assets.tsx
import { useState } from 'react';
import { useAssets, useCreateAsset } from '@/hooks/useAssets';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AssetList } from '@/components/assets/AssetList';
import { AssetForm } from '@/components/assets/AssetForm';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';

export const Assets = () => {
  const [search, setSearch] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { data, isLoading } = useAssets({ search });
  const createAsset = useCreateAsset();

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Assets</h1>
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>Add Asset</Button>
          </DialogTrigger>
          <DialogContent>
            <AssetForm
              onSubmit={async (data) => {
                await createAsset.mutateAsync(data);
                setIsDialogOpen(false);
              }}
            />
          </DialogContent>
        </Dialog>
      </div>

      <Input
        placeholder="Search assets..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <AssetList assets={data?.items || []} isLoading={isLoading} />
    </div>
  );
};
```

#### 14.2 Scans Management con Real-time Updates

```typescript
// src/hooks/useScans.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scansAPI } from '@/api/scans';
import { useEffect } from 'react';

export const useScans = (params?: any) => {
  return useQuery({
    queryKey: ['scans', params],
    queryFn: () => scansAPI.list(params),
    refetchInterval: 5000, // Poll every 5 seconds
  });
};

export const useScanStatus = (scanId: string) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['scan-status', scanId],
    queryFn: () => scansAPI.getStatus(scanId),
    refetchInterval: (data) => {
      // Stop polling if scan is done
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
    enabled: !!scanId,
  });

  // Invalidate scans list when status changes
  useEffect(() => {
    if (query.data?.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['scans'] });
    }
  }, [query.data?.status, queryClient]);

  return query;
};
```

```typescript
// src/components/scans/ScanProgress.tsx
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useScanStatus } from '@/hooks/useScans';

interface ScanProgressProps {
  scanId: string;
}

export const ScanProgress = ({ scanId }: ScanProgressProps) => {
  const { data, isLoading } = useScanStatus(scanId);

  if (isLoading) return <div>Loading...</div>;

  const statusColors = {
    pending: 'bg-gray-500',
    running: 'bg-blue-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <Badge className={statusColors[data.status]}>
          {data.status.toUpperCase()}
        </Badge>
        <span className="text-sm text-gray-600">
          {data.progress}%
        </span>
      </div>
      
      <Progress value={data.progress} />
      
      {data.current_step && (
        <p className="text-sm text-gray-600">{data.current_step}</p>
      )}
      
      {data.estimated_remaining && (
        <p className="text-xs text-gray-500">
          ETA: {data.estimated_remaining}
        </p>
      )}
    </div>
  );
};
```

### Día 15: Vulnerabilities + Dashboard + Charts

#### 15.1 Dashboard con Estadísticas

```typescript
// src/pages/Dashboard.tsx
import { useQuery } from '@tanstack/react-query';
import { dashboardAPI } from '@/api/dashboard';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { VulnerabilityChart } from '@/components/dashboard/VulnerabilityChart';
import { AssetTimelineChart } from '@/components/dashboard/AssetTimelineChart';
import { TopRiskyAssets } from '@/components/dashboard/TopRiskyAssets';

export const Dashboard = () => {
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardAPI.getStats,
  });

  const { data: vulnTrend } = useQuery({
    queryKey: ['vuln-trend'],
    queryFn: () => dashboardAPI.getVulnerabilityTrend({ days: 30 }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Assets"
          value={stats?.assets.total || 0}
          change={stats?.assets.change_7d}
          icon="server"
        />
        <StatsCard
          title="Critical Vulns"
          value={stats?.vulnerabilities.critical || 0}
          severity="critical"
          icon="alert-triangle"
        />
        <StatsCard
          title="Active Scans"
          value={stats?.scans.running || 0}
          icon="activity"
        />
        <StatsCard
          title="Risk Score"
          value={stats?.risk_score || 0}
          max={100}
          icon="shield"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <VulnerabilityChart data={vulnTrend} />
        <AssetTimelineChart />
      </div>

      {/* Top Risky Assets */}
      <TopRiskyAssets />
    </div>
  );
};
```

```typescript
// src/components/dashboard/VulnerabilityChart.tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export const VulnerabilityChart = ({ data }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Vulnerability Trend (30 days)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="critical"
              stroke="#dc2626"
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="high"
              stroke="#ea580c"
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="medium"
              stroke="#ca8a04"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};
```

#### 15.2 Vulnerabilities Management

```typescript
// src/pages/Vulnerabilities.tsx
import { useState } from 'react';
import { useVulnerabilities } from '@/hooks/useVulnerabilities';
import { VulnList } from '@/components/vulnerabilities/VulnList';
import { VulnFilters } from '@/components/vulnerabilities/VulnFilters';
import { VulnDetail } from '@/components/vulnerabilities/VulnDetail';

export const Vulnerabilities = () => {
  const [filters, setFilters] = useState({
    severity: '',
    status: '',
    search: '',
  });
  const [selectedVuln, setSelectedVuln] = useState(null);

  const { data, isLoading } = useVulnerabilities(filters);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Vulnerabilities</h1>

      <VulnFilters filters={filters} onChange={setFilters} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <VulnList
            vulnerabilities={data?.items || []}
            onSelect={setSelectedVuln}
            isLoading={isLoading}
          />
        </div>

        {selectedVuln && (
          <div className="lg:col-span-1">
            <VulnDetail vulnerability={selectedVuln} />
          </div>
        )}
      </div>
    </div>
  );
};
```

### 📦 Entregables Días 13-15

| Día | Componente | Archivos | LOC |
|-----|------------|----------|-----|
| 13 | Setup + Auth + Layout | 15 | ~1,200 |
| 14 | Assets + Scans UI | 12 | ~1,000 |
| 15 | Vulnerabilities + Dashboard | 15 | ~1,200 |
| **Total** | **Frontend Completo** | **42** | **~3,400** |

---

## 📅 DÍA 16: DOCKER PRODUCTION + NUC DEPLOY

**Estado:** 🔧 **POR IMPLEMENTAR**  
**Duración Estimada:** 1 día  
**Objetivo:** Deployment en tu NUC listo para producción

### 16.1 Docker Production Setup

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: nestsecure_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
    networks:
      - nestsecure

  # Backend FastAPI
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: nestsecure_backend
    restart: unless-stopped
    env_file:
      - .env.production
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://nestsecure:${DB_PASSWORD}@postgres:5432/nestsecure
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - nestsecure
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL
  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: nestsecure_postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=nestsecure
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=nestsecure
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    networks:
      - nestsecure
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nestsecure"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: nestsecure_redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - nestsecure
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Celery Worker - Scanning
  celery_worker_scanning:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: nestsecure_celery_scanning
    restart: unless-stopped
    command: celery -A app.workers.celery_app:celery_app worker -Q scanning -l info --concurrency=2
    env_file:
      - .env.production
    depends_on:
      - redis
      - postgres
    networks:
      - nestsecure

  # Celery Worker - Enrichment
  celery_worker_enrichment:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: nestsecure_celery_enrichment
    restart: unless-stopped
    command: celery -A app.workers.celery_app:celery_app worker -Q enrichment -l info --concurrency=4
    env_file:
      - .env.production
    depends_on:
      - redis
      - postgres
    networks:
      - nestsecure

  # Celery Beat
  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: nestsecure_celery_beat
    restart: unless-stopped
    command: celery -A app.workers.celery_app:celery_app beat -l info
    env_file:
      - .env.production
    depends_on:
      - redis
      - postgres
    networks:
      - nestsecure

  # GVM/OpenVAS
  gvm:
    image: greenbone/community-container:stable
    container_name: nestsecure_gvm
    restart: unless-stopped
    ports:
      - "127.0.0.1:9392:9392"
      - "127.0.0.1:9390:9390"
    environment:
      - PASSWORD=${GVM_ADMIN_PASSWORD}
    volumes:
      - gvm_data:/var/lib/gvm
      - gvm_scap:/var/lib/openvas/plugins
      - gvm_cert:/var/lib/gvm/cert-data
      - openvas_plugins:/var/lib/openvas/plugins
    mem_limit: 6g
    mem_reservation: 4g
    networks:
      - nestsecure

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: nestsecure_prometheus
    restart: unless-stopped
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    networks:
      - nestsecure

networks:
  nestsecure:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  gvm_data:
  gvm_scap:
  gvm_cert:
  openvas_plugins:
  prometheus_data:
```

### 16.2 Nginx Configuration

```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 50M;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/rss+xml font/truetype font/opentype 
               application/vnd.ms-fontobject image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # Backend upstream
    upstream backend {
        server backend:8000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name nestsecure.local;  # Cambia esto

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security Headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

        # Frontend
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        # API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Login rate limiting
        location /api/v1/auth/login {
            limit_req zone=login burst=3 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # Health check (no auth)
        location /health {
            proxy_pass http://backend;
            access_log off;
        }

        # Metrics (restrict access)
        location /metrics {
            allow 127.0.0.1;
            deny all;
            proxy_pass http://backend;
        }
    }
}
```

### 16.3 Environment Configuration

```.env
# .env.production (template)

# Application
ENVIRONMENT=production
SECRET_KEY=your-very-secure-secret-key-min-32-chars
API_V1_PREFIX=/api/v1
PROJECT_NAME=NESTSECURE
VERSION=1.0.0

# Database
DB_PASSWORD=your-secure-db-password
DATABASE_URL=postgresql+asyncpg://nestsecure:${DB_PASSWORD}@postgres:5432/nestsecure
DATABASE_URL_SYNC=postgresql+psycopg2://nestsecure:${DB_PASSWORD}@postgres:5432/nestsecure

# Redis
REDIS_PASSWORD=your-secure-redis-password
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=https://your-domain.com

# GVM/OpenVAS
GVM_HOST=gvm
GVM_PORT=9390
GVM_USERNAME=admin
GVM_PASSWORD=${GVM_ADMIN_PASSWORD}
GVM_ADMIN_PASSWORD=your-gvm-admin-password
GVM_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Email (opcional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@nestsecure.com
```

### 16.4 Deploy Script

```bash
#!/bin/bash
# deploy.sh - Script de deployment en NUC

set -e

echo "🚀 NESTSECURE Production Deployment"
echo "===================================="

# Variables
ENV_FILE=".env.production"
COMPOSE_FILE="docker-compose.prod.yml"

# Validar archivos
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE not found"
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Error: $COMPOSE_FILE not found"
    exit 1
fi

# Cargar variables
source $ENV_FILE

echo "📦 Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "🐳 Building Docker images..."
docker-compose -f $COMPOSE_FILE build --no-cache

echo "🛑 Stopping old containers..."
docker-compose -f $COMPOSE_FILE down

echo "🗑️ Pruning old images..."
docker image prune -f

echo "▶️  Starting services..."
docker-compose -f $COMPOSE_FILE up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Health checks
echo "🏥 Checking backend health..."
curl -f http://localhost/health || echo "⚠️  Backend not ready yet"

echo "🏥 Checking GVM..."
docker-compose -f $COMPOSE_FILE exec -T gvm gvm-cli --gmp-username admin --gmp-password $GVM_ADMIN_PASSWORD socket --socketpath /run/gvmd/gvmd.sock --xml "<get_version/>" || echo "⚠️  GVM not ready yet"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service URLs:"
echo "   - Frontend: https://localhost"
echo "   - API: https://localhost/api/v1"
echo "   - Health: https://localhost/health"
echo "   - GVM Web UI: http://localhost:9392 (admin / $GVM_ADMIN_PASSWORD)"
echo "   - Prometheus: http://localhost:9090"
echo ""
echo "📝 View logs:"
echo "   docker-compose -f $COMPOSE_FILE logs -f [service]"
echo ""
echo "🔒 Don't forget to:"
echo "   1. Configure firewall rules"
echo "   2. Set up SSL certificates"
echo "   3. Configure backup cron jobs"
echo "   4. Set up monitoring alerts"
```

### 16.5 NUC Setup Checklist

```bash
# CHECKLIST DE CONFIGURACIÓN NUC

## 1. Prerequisitos del Sistema
- [ ] Ubuntu Server 22.04 LTS instalado
- [ ] Docker Engine 24+ instalado
- [ ] Docker Compose v2+ instalado
- [ ] Git instalado
- [ ] Firewall configurado (ufw)
- [ ] 16GB+ RAM disponible
- [ ] 100GB+ almacenamiento disponible

## 2. Configuración de Red
- [ ] IP estática configurada
- [ ] DNS configurado
- [ ] Hostname configurado (nestsecure.local)
- [ ] Puertos abiertos:
      - 80 (HTTP)
      - 443 (HTTPS)
      - 22 (SSH - restringido a tu IP)

## 3. Seguridad
- [ ] Usuario no-root creado
- [ ] SSH key-based auth configurado
- [ ] Password auth SSH deshabilitado
- [ ] Fail2ban instalado y configurado
- [ ] UFW firewall activo
- [ ] Automatic security updates habilitado

## 4. SSL Certificates
# Opción A: Let's Encrypt (dominio público)
certbot certonly --standalone -d your-domain.com

# Opción B: Self-signed (desarrollo/LAN)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem

## 5. Deployment
git clone https://github.com/yourusername/nestsecure.git
cd nestsecure
cp .env.production.example .env.production
# Editar .env.production con tus valores
chmod +x deploy.sh
./deploy.sh

## 6. Post-Deployment
- [ ] Crear superusuario inicial
- [ ] Configurar backup automático
- [ ] Configurar monitoreo (Prometheus alerts)
- [ ] Documentar credenciales en gestor de contraseñas
- [ ] Configurar logs rotation
- [ ] Programar actualizaciones de GVM feeds

## 7. Backup Configuration
# Crontab para backups diarios
0 2 * * * /opt/nestsecure/scripts/backup.sh

## 8. Monitoreo
- [ ] Prometheus scraping backend
- [ ] Alertas configuradas (opcional: AlertManager)
- [ ] Health checks automáticos
```

### 📦 Entregables Día 16

| Componente | Archivos | Notas |
|------------|----------|-------|
| docker-compose.prod.yml | 1 | Producción completa |
| Nginx config | 1 | HTTPS + rate limiting |
| .env.production | 1 | Template de variables |
| deploy.sh | 1 | Script automatizado |
| Backup script | 1 | Backup DB + volúmenes |
| Documentación NUC | 1 | Setup completo |

---

## 📅 DÍA 17: TESTING E2E + VALIDACIÓN

**Estado:** 🔧 **POR IMPLEMENTAR**  
**Duración Estimada:** 1 día  
**Objetivo:** Validar sistema completo end-to-end

### 17.1 Tests End-to-End

```typescript
// frontend/tests/e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should login successfully', async ({ page }) => {
    await page.goto('http://localhost');
    
    await page.fill('[name="email"]', 'admin@nestsecure.com');
    await page.fill('[name="password"]', 'SecurePassword123!');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('http://localhost/login');
    
    await page.fill('[name="email"]', 'invalid@email.com');
    await page.fill('[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('.error-message')).toBeVisible();
  });
});

test.describe('Scan Workflow', () => {
  test('should create and execute scan', async ({ page }) => {
    // Login
    await page.goto('http://localhost');
    await page.fill('[name="email"]', 'admin@nestsecure.com');
    await page.fill('[name="password"]', 'SecurePassword123!');
    await page.click('button[type="submit"]');
    
    // Navigate to scans
    await page.click('text=Scans');
    await expect(page).toHaveURL('/scans');
    
    // Create new scan
    await page.click('text=New Scan');
    await page.fill('[name="name"]', 'Test Scan E2E');
    await page.fill('[name="target"]', '192.168.1.100');
    await page.selectOption('[name="scan_type"]', 'quick');
    await page.click('button:has-text("Start Scan")');
    
    // Verify scan created
    await expect(page.locator('.scan-list')).toContainText('Test Scan E2E');
    await expect(page.locator('.scan-status')).toContainText('running');
    
    // Wait for completion (max 2 min)
    await page.waitForSelector('.scan-status:has-text("completed")', {
      timeout: 120000
    });
    
    // Check results
    await page.click('.scan-item:has-text("Test Scan E2E")');
    await expect(page.locator('.scan-detail')).toBeVisible();
  });
});
```

### 17.2 Integration Tests

```python
# backend/tests/integration/test_full_scan_workflow.py
import pytest
from app.api.v1.scans import create_scan
from app.workers.openvas_worker import openvas_full_scan

@pytest.mark.integration
async def test_full_scan_workflow(async_db, test_user, test_organization):
    """Test complete scan workflow from API to worker."""
    
    # Create scan via API
    scan_data = {
        "name": "Integration Test Scan",
        "scan_type": "discovery",
        "targets": ["192.168.1.1/24"]
    }
    
    response = await create_scan(
        scan_data,
        current_user=test_user,
        db=async_db
    )
    
    assert response.status == "pending"
    scan_id = response.id
    
    # Execute worker task (synchronously for testing)
    result = openvas_full_scan.apply(
        args=[str(scan_id)],
        throw=True
    )
    
    assert result.successful()
    
    # Verify scan completed
    scan = await async_db.get(Scan, scan_id)
    assert scan.status == "completed"
    assert scan.progress == 100
    
    # Verify assets were discovered
    assets = await async_db.execute(
        select(Asset).where(Asset.organization_id == test_organization.id)
    )
    assert len(assets.scalars().all()) > 0
```

### 17.3 Load Testing

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class NestSecureUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before starting tasks."""
        response = self.client.post("/api/v1/auth/login/json", json={
            "email": "loadtest@nestsecure.com",
            "password": "LoadTest123!"
        })
        self.token = response.json()["access_token"]
        self.client.headers.update({
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/api/v1/dashboard/stats")
    
    @task(2)
    def list_assets(self):
        self.client.get("/api/v1/assets?page=1&page_size=20")
    
    @task(1)
    def list_vulnerabilities(self):
        self.client.get("/api/v1/vulnerabilities?page=1&page_size=20")
    
    @task(1)
    def view_scan_status(self):
        # Simulate checking scan status
        self.client.get("/api/v1/scans?status=running")

# Run with: locust -f locustfile.py --host=http://localhost:8000
```

### 17.4 Validation Checklist

```markdown
# VALIDATION CHECKLIST

## Backend API
- [ ] Todos los endpoints responden correctamente
- [ ] Authentication funciona (login, refresh, logout)
- [ ] Multi-tenancy aislando datos por organización
- [ ] Validación de inputs rechazando datos inválidos
- [ ] Error handling devolviendo errores consistentes
- [ ] Rate limiting funcionando
- [ ] CORS configurado correctamente
- [ ] Health checks respondiendo

## Scanners
- [ ] OpenVAS/GVM conecta correctamente
- [ ] Scans se ejecutan sin errores
- [ ] Resultados se parsean correctamente
- [ ] Vulnerabilidades se almacenan en DB
- [ ] Progress updates en tiempo real
- [ ] Cancelación de scans funciona
- [ ] Cleanup de recursos GVM

## Workers (Celery)
- [ ] Tasks se ejecutan correctamente
- [ ] Retries funcionan en fallos
- [ ] Dead letter queue captura errores
- [ ] Monitoring de tasks activas
- [ ] Scheduled tasks (beat) ejecutando

## Frontend
- [ ] Login/logout funciona
- [ ] Navegación entre páginas
- [ ] Dashboard muestra estadísticas
- [ ] Assets CRUD completo
- [ ] Scans CRUD completo
- [ ] Progress bars actualizándose
- [ ] Vulnerabilities filtrado funciona
- [ ] Responsive design en móvil/tablet

## Database
- [ ] Migraciones aplicadas correctamente
- [ ] Índices creados
- [ ] Relaciones con cascade funcionando
- [ ] Backups automáticos configurados
- [ ] Connection pooling funcionando

## Docker & Infrastructure
- [ ] Todos los containers iniciando
- [ ] Health checks pasando
- [ ] Volúmenes persistiendo datos
- [ ] Logs accesibles
- [ ] Resource limits respetados
- [ ] Networks aislando servicios

## Security
- [ ] Passwords hasheados
- [ ] JWT tokens expirando
- [ ] HTTPS funcionando
- [ ] Rate limiting bloqueando
- [ ] Input validation previendo injection
- [ ] No credentials en logs
- [ ] Headers de seguridad configurados

## Performance
- [ ] Tiempos de respuesta < 200ms (API)
- [ ] Queries DB optimizadas
- [ ] Frontend carga < 2s
- [ ] Scans completan en tiempo razonable
- [ ] No memory leaks en workers

## Monitoring
- [ ] Prometheus scraping métricas
- [ ] Logs estructurados en JSON
- [ ] Error tracking funcionando
- [ ] Health checks monitoreados
```

---

## ✅ CHECKLIST FINAL - FASE 2 COMPLETA

### Backend (80 endpoints API)
- [x] Auth JWT (Día 3) - 5 endpoints
- [x] Users CRUD (Día 3) - 8 endpoints
- [x] Organizations CRUD (Día 3) - 7 endpoints
- [x] Assets CRUD (Día 4) - 8 endpoints
- [x] Services CRUD (Día 4) - 5 endpoints
- [x] Dashboard Stats (Día 4) - 6 endpoints
- [x] Scans API (Día 8) - 7 endpoints
- [x] OpenVAS Integration (Día 8) - ✅ Completo
- [ ] Nmap API (Día 10) - 4 endpoints
- [ ] Nuclei API (Día 11) - 4 endpoints
- [ ] CVE API (Día 5) - 6 endpoints
- [ ] Vulnerabilities CRUD (Día 5) - 9 endpoints

### Scanners (3 integrados)
- [x] OpenVAS/GVM (Día 8) - ✅ Completo
- [ ] Nmap Enhanced (Día 10)
- [ ] Nuclei (Día 11)

### Error Handling (Día 12)
- [ ] Exception hierarchy (30+ clases)
- [ ] Global handlers
- [ ] Circuit breakers
- [ ] Retry logic
- [ ] Request validation

### Frontend (Días 13-15)
- [ ] Auth flow completo
- [ ] Dashboard con charts
- [ ] Assets management
- [ ] Scans management con real-time
- [ ] Vulnerabilities management
- [ ] Responsive design

### Infrastructure (Día 16)
- [ ] Docker production setup
- [ ] Nginx reverse proxy
- [ ] SSL/TLS configuration
- [ ] Deploy script
- [ ] NUC configuration
- [ ] Backup automation

### Testing (Día 17)
- [ ] E2E tests con Playwright
- [ ] Integration tests
- [ ] Load tests con Locust
- [ ] Validation complete

---

## 📈 RESUMEN DE MÉTRICAS

| Categoría | Objetivo | Estado |
|-----------|----------|--------|
| **Backend** |
| Endpoints API | 80+ | 64/80 (80%) ✅ |
| Tests | 400+ | 265/400 (66%) 🔧 |
| Cobertura | >90% | ~85% 🔧 |
| **Frontend** |
| Páginas | 8 | 0/8 (0%) 🔧 |
| Componentes | 40+ | 0/40 (0%) 🔧 |
| **Scanners** |
| Integrados | 3 | 1/3 (33%) 🔧 |
| **Infrastructure** |
| Docker Prod | ✅ | 0% 🔧 |
| NUC Deploy | ✅ | 0% 🔧 |

---

## 🎯 PRIORIDADES

### 🔥 Crítico (Días 10-12)
1. Nmap Enhanced (Día 10)
2. Nuclei Integration (Día 11)
3. Error Handling Global (Día 12)

### 🚀 Alto (Días 13-15)
4. Frontend React Setup (Día 13)
5. Frontend Assets + Scans (Día 14)
6. Frontend Dashboard + Vulns (Día 15)

### 🛠️ Necesario (Días 16-17)
7. Docker Production + NUC Deploy (Día 16)
8. Testing E2E + Validation (Día 17)

---

## 📞 PRÓXIMOS PASOS

1. **Revisar este documento** y confirmar prioridades
2. **Iniciar Día 10** (Nmap Enhanced) si estás de acuerdo
3. **Ajustar timeline** si necesitas más/menos tiempo
4. **Preparar NUC** para deployment (Día 16)

**¿Listo para empezar con el Día 10?** 🚀
