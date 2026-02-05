# =============================================================================
# NESTSECURE - DÍA 21: SERVICE-TO-CVE CORRELATION
# =============================================================================
# Fecha: 2026-02-05
# Estado: ✅ COMPLETADO
# Tiempo: ~4 horas
# =============================================================================

## 📋 RESUMEN EJECUTIVO

El Día 21 implementa **correlación automática entre servicios detectados y CVEs**.
Cuando Nmap detecta un servicio (ej: Apache/2.4.49), el sistema automáticamente:
1. Construye un CPE (Common Platform Enumeration)
2. Busca CVEs relacionados en NVD (National Vulnerability Database)
3. Crea vulnerabilidades vinculadas al servicio

### Flujo de Correlación

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Nmap detecta   │     │  Construir CPE   │     │  Buscar en NVD  │
│  Apache/2.4.49  │ ──▶ │  cpe:2.3:a:...   │ ──▶ │  por CPE        │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Mostrar en UI  │ ◀── │  Crear Vuln en   │ ◀── │  Encontrar      │
│  con severidad  │     │  base de datos   │     │  CVE-2021-41773 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 🛠️ ARCHIVOS CREADOS/MODIFICADOS

### Backend (7 archivos)

| Archivo | Acción | Líneas | Descripción |
|---------|--------|--------|-------------|
| `app/utils/cpe_utils.py` | ✏️ MOD | +180 | Funciones para construir CPEs desde servicios |
| `app/services/correlation_service.py` | ✅ NUEVO | ~580 | Servicio de correlación async |
| `app/api/v1/correlation.py` | ✅ NUEVO | ~320 | API endpoints de correlación |
| `app/api/v1/router.py` | ✏️ MOD | +8 | Agregar correlation router |
| `app/workers/correlation_worker.py` | ✅ NUEVO | ~450 | Worker Celery para correlación |
| `app/workers/celery_app.py` | ✏️ MOD | +1 | Registrar correlation_worker |
| `app/tests/test_utils/test_cpe_utils.py` | ✅ NUEVO | ~400 | 38 tests para CPE utilities |

### Frontend (4 archivos)

| Archivo | Acción | Líneas | Descripción |
|---------|--------|--------|-------------|
| `lib/api.ts` | ✏️ MOD | +85 | Métodos API para correlación |
| `hooks/use-correlation.ts` | ✅ NUEVO | ~210 | Hooks React Query |
| `components/correlation/correlate-button.tsx` | ✅ NUEVO | ~280 | Componente UI |

---

## 📁 DETALLE DE IMPLEMENTACIÓN

### 1. CPE Utilities (`backend/app/utils/cpe_utils.py`)

**Nuevas funciones agregadas:**

```python
# Mapeos de productos Nmap a CPE
NMAP_TO_CPE_VENDOR = {
    "apache httpd": "apache",
    "nginx": "nginx",
    "openssh": "openbsd",
    "mysql": "oracle",
    # ... más mapeos
}

# Construir CPE desde info de servicio
build_cpe_from_service_info(
    service_name="http",
    product="Apache httpd",
    version="2.4.49"
)
# Retorna: "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*"

# Confianza del CPE
get_cpe_confidence("nmap_cpe", has_version=True)  # 95
get_cpe_confidence("constructed", has_version=True)  # 75
get_cpe_confidence("constructed", has_version=False)  # 55
```

### 2. Correlation Service (`backend/app/services/correlation_service.py`)

**Clase principal:**

```python
class CorrelationService:
    """Servicio para correlacionar servicios con CVEs."""
    
    async def correlate_service(
        self,
        service: Service,
        scan_id: Optional[str] = None,
        auto_create_vuln: bool = True,
        max_cves: int = 20,
    ) -> Dict[str, Any]:
        """
        Correlaciona un servicio con CVEs.
        
        Returns:
            {
                'service_id': str,
                'cpe': str | None,
                'cpe_confidence': int,
                'cves_found': int,
                'vulnerabilities_created': int,
                'status': 'success' | 'no_cpe' | 'no_cves' | 'error',
                'cves': List[str],
            }
        """
    
    async def correlate_scan_services(
        self,
        scan_id: str,
        auto_create: bool = True,
    ) -> Dict[str, Any]:
        """Correlaciona todos los servicios de un scan."""
    
    async def correlate_asset_services(
        self,
        asset_id: str,
        auto_create: bool = True,
    ) -> Dict[str, Any]:
        """Correlaciona todos los servicios de un asset."""
```

### 3. API Endpoints (`backend/app/api/v1/correlation.py`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/correlation/services/{id}/correlate` | POST | Correlacionar un servicio |
| `/correlation/scans/{id}/correlate` | POST | Correlacionar servicios de un scan |
| `/correlation/assets/{id}/correlate` | POST | Correlacionar servicios de un asset |
| `/correlation/cpe/{service_id}` | GET | Obtener CPE de un servicio |
| `/correlation/stats` | GET | Estadísticas de correlación |

**Ejemplo de uso:**

```bash
# Correlacionar un scan completo
curl -X POST "http://localhost:8000/api/v1/correlation/scans/{scan_id}/correlate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Response:
{
  "scan_id": "abc123",
  "services_processed": 15,
  "services_with_cpe": 12,
  "cves_found": 8,
  "vulnerabilities_created": 8,
  "status": "success",
  "services": [
    {
      "service_id": "svc1",
      "cpe": "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*",
      "cves_found": 3,
      "vulnerabilities_created": 3
    },
    ...
  ]
}
```

### 4. Celery Worker (`backend/app/workers/correlation_worker.py`)

**Tareas disponibles:**

```python
# Correlacionar servicios de un scan (background)
correlate_scan_cves.delay(scan_id, auto_create_vulns=True)

# Correlacionar un servicio individual
correlate_service_cves.delay(service_id)

# Correlacionar servicios de un asset
correlate_asset_cves.delay(asset_id)
```

**Rate limiting:**
- Con NVD_API_KEY: 0.6 segundos entre requests
- Sin API key: 6 segundos entre requests (rate limit público)

### 5. Frontend Components

**Hook `useCorrelateService`:**

```typescript
const { mutate: correlate, isPending } = useCorrelateService();

// Usar
correlate({
  serviceId: "svc-123",
  autoCreateVuln: true,
  maxCves: 10,
});
```

**Componente `CorrelateButton`:**

```tsx
<CorrelateButton
  type="scan"
  resourceId={scan.id}
  resourceName={scan.name}
  onComplete={(result) => console.log(result)}
/>
```

---

## 🧪 TESTS

### Tests CPE Utilities (38 tests)

```bash
pytest app/tests/test_utils/test_cpe_utils.py -v
# ✅ 38 passed in 0.15s
```

**Clases de tests:**

| Clase | Tests | Descripción |
|-------|-------|-------------|
| `TestCPEDataclass` | 6 | Clase CPE y métodos |
| `TestParseCPE` | 4 | Parseo de CPEs |
| `TestIsValidCPE` | 2 | Validación de CPEs |
| `TestCreateCPE` | 2 | Creación de CPEs |
| `TestExtractVendorProduct` | 2 | Extracción de vendor/product |
| `TestExtractVersion` | 2 | Extracción de versión |
| `TestNormalizeCPE` | 2 | Normalización |
| `TestCPEToHumanReadable` | 2 | Conversión legible |
| `TestBuildCPESearchQuery` | 2 | Construcción de queries |
| `TestBuildCPEFromServiceInfo` | 7 | Construcción desde servicios |
| `TestGetCPEConfidence` | 4 | Cálculo de confianza |
| `TestCPEIntegration` | 3 | Tests de integración |

---

## 📊 MÉTRICAS

| Métrica | Valor |
|---------|-------|
| Archivos backend nuevos | 4 |
| Archivos backend modificados | 3 |
| Archivos frontend nuevos | 2 |
| Archivos frontend modificados | 1 |
| Líneas de código nuevas | ~2,500 |
| Tests nuevos | 38 |
| Endpoints nuevos | 5 |
| Productos soportados | 40+ |
| Tiempo de implementación | ~4 horas |

---

## 🔧 CONFIGURACIÓN

### Variables de Entorno

```bash
# API key de NVD (opcional, mejora rate limits)
NVD_API_KEY=your-api-key-here

# Sin API key: 10 requests/minuto
# Con API key: 100 requests/minuto
```

### Obtener API Key de NVD

1. Ir a https://nvd.nist.gov/developers/request-an-api-key
2. Solicitar API key (gratuita)
3. Agregar a `.env`: `NVD_API_KEY=xxx`

---

## ✅ CHECKLIST COMPLETADO

- [x] Agregar funciones a `cpe_utils.py` para construir CPEs desde servicios
- [x] Crear `correlation_service.py` con lógica async
- [x] Crear API endpoints `/correlation/*`
- [x] Crear `correlation_worker.py` para Celery
- [x] Registrar worker en `celery_app.py`
- [x] Crear hook `use-correlation.ts`
- [x] Crear componente `CorrelateButton`
- [x] Agregar métodos API en `lib/api.ts`
- [x] Crear tests unitarios (38 tests pasando)
- [x] Documentar en `DIA_21_COMPLETADO.md`

---

## 🚀 PRÓXIMOS PASOS (Día 22)

### Nuclei Integration

El Día 22 implementará integración con Nuclei para escaneos de vulnerabilidades:

1. **Actualizar Dockerfile** con instalación de Nuclei
2. **Descargar templates** de nuclei-templates
3. **Crear worker** `nuclei_worker.py` completo
4. **Tests de instalación** y funcionamiento
5. **Tests E2E** de scan real

---

## 📝 NOTAS TÉCNICAS

### CPE 2.3 Format

```
cpe:2.3:part:vendor:product:version:update:edition:language:sw_edition:target_sw:target_hw:other

Ejemplos:
- cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*
- cpe:2.3:a:openbsd:openssh:8.9:*:*:*:*:*:*:*
- cpe:2.3:a:nginx:nginx:1.18.0:*:*:*:*:*:*:*
```

### NVD API 2.0

La API de NVD soporta búsqueda por CPE:

```
GET https://services.nvd.nist.gov/rest/json/cves/2.0?cpeName=cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*
```

Retorna CVEs que afectan a ese CPE específico.

### Productos Soportados

La correlación funciona automáticamente para:
- **Web Servers**: Apache, Nginx, IIS, Tomcat, Jetty, Caddy, Lighttpd
- **SSH**: OpenSSH, Dropbear
- **Databases**: MySQL, MariaDB, PostgreSQL, MongoDB, Redis, Elasticsearch
- **Mail**: Postfix, Exim, Dovecot
- **FTP**: vsftpd, ProFTPD, Pure-FTPd
- **DNS**: BIND, dnsmasq, PowerDNS
- **Otros**: Samba, OpenLDAP, PHP, HAProxy, Varnish, Squid
