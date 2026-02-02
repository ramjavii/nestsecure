# =============================================================================
# NESTSECURE - Día 6: Integración API ↔ Workers + Testing
# =============================================================================
# Fecha: 2026-02-02
# Objetivo: Integrar completamente la API de Scans con los Workers de Celery
# =============================================================================

## 📊 Resumen de Implementación

| Componente | Estado | Tests | Notas |
|------------|--------|-------|-------|
| API → Celery Integration | ✅ Completado | - | Despacho automático de tareas |
| Worker → DB Updates | ✅ Completado | 25/25 | Actualización de estado en tiempo real |
| Cancelación Real | ✅ Completado | - | Revoke de tareas en Celery |
| Tests de Workers | ✅ Completado | 25/25 | Cobertura completa |
| Tests de Scans API | ✅ Actualizado | +1 | Mock de Celery |

**Tests Día 6:** 25 nuevos tests de workers
**Tests Acumulados:** 259 tests (234 anteriores + 25 nuevos)
**Duración:** ~4 horas

---

## ✅ Tareas Completadas

### 1. Integración API → Celery Workers

#### Flujo de Creación de Scan

```
Usuario → POST /api/v1/scans → Validación → Crear en DB
                                          ↓
                           execute_scan_task.delay()
                                          ↓
                              Celery Queue (scanning)
                                          ↓
                              Worker ejecuta Nmap
                                          ↓
                              Actualiza DB (status, progress)
                                          ↓
                              Crea vulnerabilidades/servicios
```

#### Código de Integración (`scans.py`)

```python
# Despachar tarea a Celery según el tipo de scan
try:
    from app.workers.nmap_worker import execute_scan_task
    
    task = execute_scan_task.delay(
        scan_id=scan.id,
        scan_type=scan_in.scan_type,
        targets=validated_targets,
        organization_id=organization_id,
        port_range=scan_in.port_range,
        engine_config=scan_in.engine_config or {},
    )
    
    # Guardar el ID de la tarea en el scan
    scan.celery_task_id = task.id
    scan.status = ScanStatus.QUEUED.value
    scan.add_log(f"Tarea Celery iniciada: {task.id}", "info")
    
except Exception as e:
    scan.status = ScanStatus.FAILED.value
    scan.error_message = f"Error al encolar tarea: {str(e)}"
```

---

### 2. Worker → DB Updates

#### Tarea Principal: `execute_scan_task`

La tarea orquesta todo el flujo de escaneo:

```python
@shared_task(
    name="app.workers.nmap_worker.execute_scan_task",
    bind=True,
    max_retries=3,
    soft_time_limit=3300,
    time_limit=3600,
)
def execute_scan_task(
    self,
    scan_id: str,
    scan_type: str,
    targets: list[str],
    organization_id: str,
    port_range: str | None = None,
    engine_config: dict | None = None,
) -> dict:
    """
    Tarea principal que ejecuta un scan completo.
    
    1. Obtiene scan de DB y marca como RUNNING
    2. Ejecuta scan según tipo (discovery, port_scan, full)
    3. Actualiza progreso en DB
    4. Crea assets/services/vulnerabilidades
    5. Marca scan como COMPLETED o FAILED
    """
```

#### Estados del Scan

| Estado | Descripción | Momento |
|--------|-------------|---------|
| `queued` | Tarea enviada a Celery | POST /scans exitoso |
| `running` | Worker procesando | Worker inicia |
| `completed` | Scan finalizado | Worker termina OK |
| `failed` | Error en ejecución | Excepción en worker |
| `cancelled` | Cancelado por usuario | PATCH /cancel |

#### Actualización de Progreso

```python
# Dentro del worker
scan.update_progress(25)  # Iniciando
db.commit()

# Después de cada target
for i, target in enumerate(targets):
    progress = int((i + 1) / len(targets) * 100)
    scan.update_progress(progress)
    db.commit()

# Al finalizar
scan.complete()  # status=completed, progress=100
db.commit()
```

---

### 3. Cancelación Real de Scans

#### Endpoint de Cancelación

```python
@router.patch("/{scan_id}/cancel")
async def cancel_scan(...):
    # Cancelar tarea en Celery si existe
    if scan.celery_task_id:
        try:
            cancel_task(scan.celery_task_id)
            logger.info(f"Tarea Celery {scan.celery_task_id} cancelada")
        except Exception as e:
            logger.warning(f"Error cancelando tarea: {e}")
    
    scan.cancel()  # status=cancelled
    await db.commit()
```

#### Función de Cancelación en Celery

```python
def cancel_task(task_id: str, terminate: bool = True) -> bool:
    """
    Cancela una tarea de Celery.
    
    Args:
        task_id: ID de la tarea a cancelar
        terminate: Si True, termina el proceso (SIGTERM)
    
    Returns:
        True si se envió la señal de cancelación
    """
    celery_app.control.revoke(task_id, terminate=terminate)
    return True
```

---

### 4. Tests de Workers (25 tests)

#### Estructura de Tests

```
test_workers/
└── test_nmap_worker.py (25 tests)
    ├── TestParseDiscoveryXml (5 tests)
    │   ├── test_parse_discovery_finds_up_hosts
    │   ├── test_parse_discovery_ignores_down_hosts
    │   ├── test_parse_discovery_empty_xml
    │   ├── test_parse_discovery_invalid_xml
    │   └── test_parse_discovery_handles_missing_hostname
    │
    ├── TestParsePortScanXml (4 tests)
    │   ├── test_parse_port_scan_extracts_host_info
    │   ├── test_parse_port_scan_extracts_services
    │   ├── test_parse_port_scan_empty_xml
    │   └── test_parse_port_scan_invalid_xml
    │
    ├── TestRunNmap (4 tests)
    │   ├── test_run_nmap_success
    │   ├── test_run_nmap_timeout
    │   ├── test_run_nmap_error
    │   └── test_run_nmap_host_down_not_error
    │
    ├── TestDiscoveryScanTask (2 tests)
    │   ├── test_discovery_scan_creates_assets
    │   └── test_discovery_scan_updates_existing_assets
    │
    ├── TestPortScanTask (2 tests)
    │   ├── test_port_scan_creates_services
    │   └── test_port_scan_asset_not_found
    │
    ├── TestExecuteScanTask (3 tests)
    │   ├── test_execute_scan_discovery_updates_db
    │   ├── test_execute_scan_cancelled_scan_aborts
    │   └── test_execute_scan_not_found
    │
    ├── TestErrorHandling (2 tests)
    │   ├── test_nmap_timeout_handled
    │   └── test_parse_invalid_xml_no_crash
    │
    └── TestEdgeCases (3 tests)
        ├── test_parse_discovery_ipv6
        ├── test_parse_port_scan_no_version
        └── test_parse_discovery_multiple_ips
```

#### Ejemplo de Test con Mock

```python
@patch("app.workers.nmap_worker.get_sync_db")
@patch("app.workers.nmap_worker.run_nmap")
def test_execute_scan_discovery_updates_db(self, mock_run_nmap, mock_get_db):
    """Debe actualizar el scan en DB durante discovery."""
    from app.workers.nmap_worker import execute_scan_task
    
    mock_run_nmap.return_value = SAMPLE_DISCOVERY_XML
    
    mock_scan = Mock()
    mock_scan.id = "scan-123"
    mock_scan.status = "queued"
    mock_scan.start = Mock()
    mock_scan.complete = Mock()
    
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar_one_or_none.side_effect = [
        mock_scan,  # Initial scan lookup
        None, None,  # Asset lookups
    ]
    mock_get_db.return_value = mock_db
    
    result = execute_scan_task(
        scan_id="scan-123",
        scan_type="discovery",
        targets=["192.168.1.0/24"],
        organization_id="org-123",
    )
    
    assert result["success"] is True
    mock_scan.start.assert_called_once()
    mock_scan.complete.assert_called_once()
```

---

### 5. Correcciones Realizadas

#### 5.1 Test de Creación de Scan

El test original fallaba porque no mockeaba Celery:

```python
# ANTES (fallaba sin Celery corriendo)
async def test_create_scan_success(self, api_client, auth_headers_operator):
    response = await api_client.post("/api/v1/scans", ...)
    assert data["status"] == "pending"  # ❌ Era "failed"

# DESPUÉS (con mock de Celery)
@patch('app.workers.nmap_worker.execute_scan_task')
async def test_create_scan_success(self, mock_task, api_client, auth_headers_operator):
    mock_async_result = Mock()
    mock_async_result.id = "test-task-id-123"
    mock_task.delay.return_value = mock_async_result
    
    response = await api_client.post("/api/v1/scans", ...)
    assert data["status"] == "queued"  # ✅ Correcto
    mock_task.delay.assert_called_once()
```

#### 5.2 Compatibilidad bcrypt

Se detectó incompatibilidad entre bcrypt 5.0 y passlib:

```bash
# Error
AttributeError: module 'bcrypt' has no attribute '__about__'

# Solución
pip install "bcrypt<5.0.0"
```

---

## 📁 Archivos Modificados

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| `api/v1/scans.py` | Integración Celery | +50 |
| `workers/nmap_worker.py` | execute_scan_task | +200 |
| `workers/celery_app.py` | cancel_task, get_task_status | +30 |
| `tests/test_workers/test_nmap_worker.py` | Tests completos | +580 |
| `tests/test_api/test_scans.py` | Mock de Celery | +15 |

---

## 🔧 Configuración de Docker

### Servicios de Celery en docker-compose.yml

```yaml
# Worker para tareas de scanning
celery_worker_scanning:
  build:
    context: ./backend
    target: production
  command: celery -A app.workers.celery_app:celery_app worker 
           -Q scanning -c 2 --loglevel=info
  depends_on:
    - redis
    - postgres
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/1

# Worker para tareas de enrichment (CVE)
celery_worker_enrichment:
  command: celery -A app.workers.celery_app:celery_app worker 
           -Q enrichment -c 1 --loglevel=info

# Celery Beat para tareas programadas
celery_beat:
  command: celery -A app.workers.celery_app:celery_app beat 
           --loglevel=info
```

### Nmap en Dockerfile

```dockerfile
# Instalar nmap
RUN apt-get update && apt-get install -y \
    nmap \
    && rm -rf /var/lib/apt/lists/*
```

---

## 📈 Métricas del Día 6

| Métrica | Valor |
|---------|-------|
| Tests nuevos | 25 |
| Tests totales | 259 |
| Líneas de código | +875 |
| Archivos modificados | 5 |
| Cobertura workers | 100% |

---

## 🎯 Próximos Pasos (Día 7)

### Testing y Refinamiento

1. **Performance Testing**
   - Tests de carga con locust
   - Benchmark de scans concurrentes
   - Medición de tiempos de respuesta

2. **Security Testing**
   - Validación de inputs en targets
   - Rate limiting en creación de scans
   - Sanitización de outputs de Nmap

3. **Refactoring**
   - Crear `scan_service.py` con lógica de negocio
   - Mejorar manejo de errores en workers
   - Logging estructurado con correlation IDs

4. **Documentación**
   - OpenAPI schemas completos
   - Guía de troubleshooting de scans
   - Runbook de operaciones

---

## ✅ Criterios de Aceptación Cumplidos

- [x] POST /scans despacha tarea a Celery
- [x] Worker actualiza scan.status durante ejecución
- [x] Worker actualiza scan.progress en tiempo real
- [x] PATCH /cancel termina tarea de Celery
- [x] GET /progress retorna datos reales
- [x] 25+ tests de workers pasando
- [x] Tests de API usan mocks de Celery
- [x] Documentación actualizada
