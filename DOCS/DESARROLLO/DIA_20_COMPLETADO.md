# =============================================================================
# NESTSECURE - DÍA 20: NETWORK SCANNING & VALIDATION
# =============================================================================
# Fecha: 2026-02-05
# Estado: ✅ COMPLETADO
# Tiempo: ~4 horas
# =============================================================================

## 📋 RESUMEN EJECUTIVO

El Día 20 implementa **validación de red completa** para restringir escaneos 
**SOLO A REDES LOCALES PRIVADAS (RFC 1918)**.

### Problema Resuelto

**ANTES (CRÍTICO):**
```python
# ❌ Aceptaba CUALQUIER IP/CIDR
nmap_output = run_nmap(["-sn", "8.8.8.8"])  # Google DNS - PERMITIDO!
nmap_output = run_nmap(["-sn", "1.1.1.1"])   # Cloudflare - PERMITIDO!
```

**DESPUÉS (SEGURO):**
```python
# ✅ Solo permite redes privadas
validate_scan_target("8.8.8.8")  # ❌ HTTPException 400
validate_scan_target("192.168.1.0/24")  # ✅ Permitido
```

---

## 🛠️ ARCHIVOS CREADOS/MODIFICADOS

### Backend (6 archivos)

| Archivo | Acción | Líneas | Descripción |
|---------|--------|--------|-------------|
| `app/utils/network_utils.py` | ✅ NUEVO | ~400 | Utilidades de validación de red |
| `app/tests/test_utils/test_network_utils.py` | ✅ NUEVO | ~600 | Tests completos para validación |
| `app/api/v1/network.py` | ✅ NUEVO | ~220 | Endpoints de validación de red |
| `app/api/v1/router.py` | ✏️ MOD | +6 | Agregar network router |
| `app/api/v1/scans.py` | ✏️ MOD | +8 | Validar targets antes de crear scan |
| `app/workers/nmap_worker.py` | ✏️ MOD | +50 | Validación en todas las tareas |

### Frontend (2 archivos)

| Archivo | Acción | Líneas | Descripción |
|---------|--------|--------|-------------|
| `hooks/use-network.ts` | ✅ NUEVO | ~200 | Hooks y utilidades de validación |
| `components/scans/scan-form-modal.tsx` | ✏️ MOD | +80 | Validación en tiempo real |
| `lib/api.ts` | ✏️ MOD | +75 | Métodos API para validación |

---

## 📁 DETALLE DE IMPLEMENTACIÓN

### 1. Network Utils (`backend/app/utils/network_utils.py`)

**Funciones principales:**

```python
# Verificar si una IP es privada
is_private_ip("192.168.1.1")  # True
is_private_ip("8.8.8.8")       # False

# Verificar si una red CIDR es privada
is_private_network("192.168.1.0/24")  # True
is_private_network("8.8.8.0/24")       # False

# Validar target para escaneo (principal)
validate_scan_target("192.168.1.1")    # ('192.168.1.1', 'ip')
validate_scan_target("10.0.0.0/24")    # ('10.0.0.0/24', 'cidr')
validate_scan_target("8.8.8.8")        # HTTPException 400
validate_scan_target("google.com")     # HTTPException 400 (hostnames bloqueados)

# Información de red
get_network_info("192.168.1.0/24")
# {
#   'network': '192.168.1.0',
#   'netmask': '255.255.255.0',
#   'broadcast': '192.168.1.255',
#   'num_hosts': 254,
#   'first_host': '192.168.1.1',
#   'last_host': '192.168.1.254',
#   'prefix_length': 24,
#   'is_private': True
# }
```

**Rangos privados (RFC 1918):**
- `10.0.0.0/8` - Clase A (16M hosts)
- `172.16.0.0/12` - Clase B (1M hosts)  
- `192.168.0.0/16` - Clase C (65K hosts)
- `127.0.0.0/8` - Localhost
- `169.254.0.0/16` - Link-local

### 2. API de Network (`backend/app/api/v1/network.py`)

**Nuevos endpoints:**

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/network/validate` | POST | Validar un target |
| `/network/validate-multiple` | POST | Validar múltiples targets |
| `/network/info/{cidr}` | GET | Info de red CIDR |
| `/network/private-ranges` | GET | Rangos permitidos |
| `/network/check-ip/{ip}` | GET | Verificar si IP es privada |

**Ejemplo de uso:**

```bash
# Validar un target
curl -X POST http://localhost:8000/api/v1/network/validate \
  -H "Content-Type: application/json" \
  -d '{"target": "192.168.1.0/24"}'

# Response:
{
  "valid": true,
  "target": "192.168.1.0/24",
  "type": "cidr",
  "error": null,
  "info": {
    "network": "192.168.1.0",
    "num_hosts": 254,
    "is_private": true
  }
}

# Target inválido
curl -X POST http://localhost:8000/api/v1/network/validate \
  -H "Content-Type: application/json" \
  -d '{"target": "8.8.8.8"}'

# Response:
{
  "valid": false,
  "target": "8.8.8.8",
  "type": null,
  "error": "Public IP address '8.8.8.8' is not allowed for scanning...",
  "info": null
}
```

### 3. Integración en API de Scans

**Modificación en `create_scan`:**

```python
@router.post("", response_model=ScanResponse)
async def create_scan(scan_data: ScanCreate, ...):
    # ✅ NUEVO: Validar targets antes de crear scan
    validated_targets = validate_targets_list(scan_data.targets)
    
    scan = Scan(
        targets=validated_targets,  # Usar targets validados
        ...
    )
```

### 4. Integración en Nmap Worker

**Segunda capa de seguridad en cada tarea:**

```python
def discovery_scan(self, target: str, ...):
    # ✅ NUEVO: Validar antes de escanear
    for single_target in target.split(","):
        if not validate_target_security(single_target.strip()):
            error_msg = f"Security: Target '{single_target}' is not a private network"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            if scan_id:
                update_scan_status_in_db(scan_id, ScanStatus.FAILED.value, error_message=error_msg)
            return result
    
    # Continuar con escaneo...
```

**Tareas protegidas:**
- ✅ `discovery_scan`
- ✅ `quick_scan`
- ✅ `full_scan`
- ✅ `vulnerability_scan`

### 5. Frontend - Hook de Validación

**Archivo: `frontend/hooks/use-network.ts`**

```typescript
// Validación local instantánea (sin servidor)
const result = validateTargetLocally("192.168.1.1");
// { valid: true, target: "192.168.1.1", type: "ip", error: null }

// Validación múltiple
const results = validateMultipleTargetsLocally([
  "192.168.1.1",
  "8.8.8.8",
  "10.0.0.0/24"
]);
// { valid: false, validCount: 2, invalidCount: 1, results: [...] }

// Hook para validar con servidor (más preciso)
const { mutate: validateTarget } = useValidateTarget();
validateTarget("192.168.1.0/24");
```

### 6. Frontend - Formulario de Scan

**Mejoras en `ScanFormModal`:**

1. **Validación en tiempo real**: Los targets se validan mientras el usuario escribe
2. **Feedback visual**: Indicadores de válido/inválido por cada target
3. **Bloqueo de submit**: No se puede enviar si hay targets inválidos
4. **Mensajes de ayuda**: Explicación clara de qué está permitido

```tsx
// Nuevo comportamiento del formulario:
<Textarea
  placeholder="192.168.1.0/24&#10;10.0.0.1&#10;172.16.0.100"
  className={hasErrors ? 'border-destructive' : ''}
/>

{/* Mostrar validación */}
{targetValidation?.valid ? (
  <CheckCircle2 /> {validCount} target(s) válido(s)
) : (
  <Alert variant="destructive">
    {invalidCount} target(s) inválido(s):
    <ul>
      {errors.map(e => <li>{e}</li>)}
    </ul>
  </Alert>
)}

{/* Info de seguridad */}
<Alert>
  Por seguridad, solo se permiten escaneos a redes privadas (RFC 1918).
</Alert>

{/* Botón deshabilitado si hay errores */}
<Button disabled={!targetValidation?.valid}>
  Iniciar Escaneo
</Button>
```

---

## 🧪 TESTS

### Tests Unitarios (`test_network_utils.py`)

**Clases de tests:**

| Clase | Tests | Descripción |
|-------|-------|-------------|
| `TestIsPrivateIP` | 15 | Verificación de IPs privadas |
| `TestIsPrivateNetwork` | 12 | Verificación de redes CIDR |
| `TestValidateScanTarget` | 20 | Función principal de validación |
| `TestValidateMultipleTargets` | 5 | Validación de múltiples targets |
| `TestGetNetworkInfo` | 6 | Información de redes |
| `TestSecurityScenarios` | 8 | Escenarios de seguridad críticos |
| `TestRealWorldUseCases` | 5 | Casos de uso reales |

**Ejecutar tests:**

```bash
cd backend
pytest app/tests/test_utils/test_network_utils.py -v
```

**Escenarios de seguridad testeados:**
- ✅ Bloqueo de Google DNS (8.8.8.8)
- ✅ Bloqueo de Cloudflare DNS (1.1.1.1)
- ✅ Bloqueo de redes externas (151.101.x.x, etc.)
- ✅ Bloqueo de hostnames (google.com, etc.)
- ✅ Permiso de redes privadas (192.168.x, 10.x, 172.16-31.x)
- ✅ Permiso de localhost (127.x.x.x)

---

## 🔒 CAPAS DE SEGURIDAD

La validación se implementa en **3 capas**:

```
┌─────────────────────────────────────────────────────────────┐
│  CAPA 1: Frontend (Validación Instantánea)                  │
│  ├─ validateTargetLocally() - Sin llamada a servidor        │
│  ├─ UI feedback inmediato                                   │
│  └─ Bloqueo de submit si hay errores                       │
├─────────────────────────────────────────────────────────────┤
│  CAPA 2: API Backend (Validación en Endpoint)               │
│  ├─ validate_targets_list() en create_scan                  │
│  ├─ HTTPException 400 si target inválido                    │
│  └─ Log de intento bloqueado                               │
├─────────────────────────────────────────────────────────────┤
│  CAPA 3: Worker (Validación en Ejecución)                   │
│  ├─ validate_target_security() antes de nmap               │
│  ├─ Scan fallido si target inválido                        │
│  └─ Log de seguridad (SECURITY: Blocked...)                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 MÉTRICAS

| Métrica | Valor |
|---------|-------|
| Archivos nuevos | 4 |
| Archivos modificados | 5 |
| Líneas de código nuevas | ~1,600 |
| Tests nuevos | 71 |
| Endpoints nuevos | 5 |
| Tiempo de implementación | ~4 horas |

---

## ✅ CHECKLIST COMPLETADO

- [x] Crear `network_utils.py` con funciones de validación
- [x] Crear tests unitarios completos (~70 tests)
- [x] Crear API endpoints `/network/*`
- [x] Integrar validación en `create_scan`
- [x] Integrar validación en todas las tareas de nmap_worker
- [x] Crear hook `use-network.ts` para frontend
- [x] Actualizar `ScanFormModal` con validación en tiempo real
- [x] Agregar métodos de API en `lib/api.ts`
- [x] Documentar en `DIA_20_COMPLETADO.md`

---

## 🚀 PRÓXIMOS PASOS (Día 21)

### Service-to-CVE Correlation

El Día 21 implementará la correlación automática de servicios detectados con CVEs:

1. **Construir CPE** desde servicios detectados (ej: Apache/2.4.49 → cpe:/a:apache:http_server:2.4.49)
2. **Buscar CVEs** por CPE en cache local y NVD
3. **Crear vulnerabilidades automáticamente** cuando se encuentren CVEs
4. **UI para mostrar CVEs vinculados** a cada servicio

---

## 📝 NOTAS

### Por qué no se permiten hostnames

Los hostnames están bloqueados por seguridad porque:
1. Podrían resolver a IPs públicas (ej: google.com → 142.250.x.x)
2. El DNS podría ser manipulado (DNS spoofing)
3. La resolución podría cambiar entre validación y ejecución

### Casos especiales

- **169.254.169.254**: Es la IP de AWS metadata. Actualmente se permite como link-local, pero podría agregarse a una blacklist específica en el futuro.
- **IPv6**: Actualmente solo se valida IPv4. IPv6 se puede agregar en el futuro.
