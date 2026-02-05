# Plan de Corrección de Bugs - Pre Día 19

**Fecha:** 5 de febrero de 2026  
**Prioridad:** CRÍTICA - Resolver antes de continuar con Fase 3

---

## 📋 Resumen de Problemáticas

| # | Problema | Severidad | Archivos Afectados | Solución |
|---|----------|-----------|-------------------|----------|
| 1 | Scan status no actualiza en frontend | 🔴 CRÍTICA | `nmap_worker.py`, `scans.py` | Actualizar DB al completar |
| 2 | Assets no aparecen en página (sí en dashboard) | 🔴 CRÍTICA | `api.ts`, `use-assets.ts` | Fix paginación/endpoint |
| 3 | Port scan: `targets` vs `target` typo | 🔴 CRÍTICA | `scans.py` línea 247 | Corregir nombre parámetro |
| 4 | OpenVAS mock mode + logging error | 🟠 ALTA | `openvas_worker.py`, `gvm/client.py` | Fix mock + logging extra |
| 5-6 | Scan types usando OpenVAS innecesariamente | 🟡 MEDIA | `scans.py` | Usar Nmap para service detection |
| 7 | Full scan mismo error que P3 | 🔴 CRÍTICA | `scans.py` línea 252 | Corregir nombre parámetro |
| 8 | Notificaciones mock | 🟡 MEDIA | `topbar.tsx` | Crear hook + API real |

---

## 🔧 Problema 1: Scan Status No Actualiza en Frontend

### Síntoma
- Discovery scan encuentra 17 hosts pero la card del scan no muestra "completado"
- Logs de worker muestran éxito pero frontend no se entera

### Causa Raíz
El `nmap_worker.py` actualiza status internamente pero **NO actualiza el campo `status` del Scan en la base de datos** cuando termina.

### Archivos a Modificar

#### `backend/app/workers/nmap_worker.py`

```python
# Agregar función helper para actualizar scan status en DB
async def update_scan_status_in_db(scan_id: str, status: str, results: dict = None):
    """Actualiza el status del scan en la base de datos."""
    from app.db.session import async_session
    from app.models.scan import Scan, ScanStatus
    
    async with async_session() as db:
        scan = await db.get(Scan, scan_id)
        if scan:
            scan.status = status
            if status == "completed":
                scan.completed_at = datetime.utcnow()
            if results:
                scan.results = results
            await db.commit()

# Modificar discovery_scan al final:
def discovery_scan(...):
    # ... código existente ...
    
    # AL FINAL, actualizar status en DB
    if scan_id:
        from app.db.session import sync_session
        with sync_session() as db:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.status = "completed"
                scan.completed_at = datetime.utcnow()
                scan.results = result
                db.commit()
    
    return result
```

#### Alternativa: Actualizar vía callback de Celery

```python
# En celery_app.py - agregar signal handler
from celery.signals import task_success, task_failure

@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Actualiza scan status cuando tarea termina exitosamente."""
    # Extraer scan_id del resultado si existe
    if isinstance(result, dict) and 'scan_id' in result:
        update_scan_in_db(result['scan_id'], 'completed', result)
```

### Logs a Agregar
En `scans/[id]/page.tsx` mostrar comando ejecutado:

```typescript
// En la página de detalle de scan, agregar:
{scanLogs && (
  <Card>
    <CardHeader>
      <CardTitle>Comando Ejecutado</CardTitle>
    </CardHeader>
    <CardContent>
      <code className="bg-muted p-2 rounded block">
        {scanLogs.command || `nmap -sn ${scan.targets.join(' ')}`}
      </code>
    </CardContent>
  </Card>
)}
```

---

## 🔧 Problema 2: Assets No Aparecen en Página

### Síntoma
- Dashboard muestra 273 assets
- Página `/assets` muestra menos (256 anteriores)

### Causa Raíz
1. El hook `useAssets()` usa un endpoint que tiene **paginación por defecto**
2. El endpoint `/api/v1/assets` tiene `limit=100` o similar
3. Dashboard usa `/api/v1/dashboard/stats` que cuenta todos

### Archivos a Modificar

#### `backend/app/api/v1/assets.py`

```python
# Verificar paginación del endpoint GET /assets
@router.get("")
async def get_assets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),  # ← Aumentar máximo o remover límite
    ...
):
```

#### `frontend/hooks/use-assets.ts`

```typescript
// Modificar para solicitar más assets o implementar paginación
export function useAssets(params?: { 
  type?: string; 
  criticality?: string; 
  status?: string;
  search?: string;
  page?: number;
  limit?: number;  // ← Agregar
}) {
  return useQuery({
    queryKey: ['assets', params],
    queryFn: () => api.getAssets({ ...params, limit: 1000 }), // ← Aumentar límite
  });
}
```

#### `frontend/lib/api.ts`

```typescript
// Agregar método getAssets si no existe
async getAssets(params?: {
  type?: string;
  criticality?: string;
  status?: string;
  search?: string;
  limit?: number;
  skip?: number;
}): Promise<Asset[]> {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.set('limit', params.limit.toString());
  if (params?.skip) queryParams.set('skip', params.skip.toString());
  // ... otros params
  
  return this.request<Asset[]>(`/assets?${queryParams.toString()}`);
}
```

---

## 🔧 Problema 3: Port Scan - Typo `targets` vs `target`

### Síntoma
- Error: `quick_scan() got an unexpected keyword argument 'tagets'` (o 'targets')
- El worker no recibe el scan porque el nombre del parámetro es incorrecto

### Causa Raíz
En `scans.py` línea 245-247:

```python
task = nmap_quick_scan_task.delay(
    scan_id=scan.id,
    targets=targets_str,  # ❌ INCORRECTO - worker espera 'target'
)
```

Pero `quick_scan` en `nmap_worker.py` línea 1086 define:

```python
def quick_scan(
    target: str,           # ← Espera 'target' (singular)
    organization_id: str,
    scan_id: Optional[str] = None,
)
```

### Solución

#### `backend/app/api/v1/scans.py` - Línea 244-248

```python
# ANTES (INCORRECTO):
elif scan_data.scan_type == ScanType.PORT_SCAN:
    task = nmap_quick_scan_task.delay(
        scan_id=scan.id,
        targets=targets_str,  # ❌
    )

# DESPUÉS (CORRECTO):
elif scan_data.scan_type == ScanType.PORT_SCAN:
    task = nmap_quick_scan_task.delay(
        target=targets_str,                           # ✅ Corregido
        organization_id=str(current_user.organization_id),  # ✅ Faltaba
        scan_id=str(scan.id),                         # ✅ Convertir a str
    )
```

---

## 🔧 Problema 4: OpenVAS Mock Mode + Logging Error

### Síntoma
```
WARNING: gvm-tools not installed, using mock mode
ERROR: KeyError("Attempt to overwrite 'message' in LogRecord")
```

### Causa Raíz
1. En modo mock, `create_task` devuelve un `task_id` falso
2. Luego `get_task_status(task_id)` intenta buscar ese task y falla con `GVMNotFoundError`
3. El error se logea con `logger.error(..., extra=e.to_dict())`
4. `e.to_dict()` contiene key `'message'` que conflictúa con LogRecord

### Solución

#### `backend/app/workers/openvas_worker.py` - Línea 195

```python
# ANTES:
except GVMError as e:
    logger.error(f"GVM error in scan {scan_id}: {e}", extra=e.to_dict())

# DESPUÉS:
except GVMError as e:
    error_dict = e.to_dict()
    # Evitar conflicto con LogRecord reserved keys
    error_dict.pop('message', None)
    error_dict.pop('msg', None)
    logger.error(f"GVM error in scan {scan_id}: {e}", extra={'gvm_error': error_dict})
```

#### `backend/app/integrations/gvm/client.py` - Mock Mode

```python
# En el modo mock, simular task real en memoria
class GVMClient:
    _mock_tasks = {}  # Almacenar tasks simulados
    
    async def create_task(self, ...):
        if self.mock_mode:
            task_id = str(uuid4())
            self._mock_tasks[task_id] = {
                'status': 'Running',
                'progress': 0,
                'is_done': False
            }
            return task_id
    
    async def get_task_status(self, task_id):
        if self.mock_mode:
            if task_id in self._mock_tasks:
                # Simular progreso
                task = self._mock_tasks[task_id]
                task['progress'] += 20
                if task['progress'] >= 100:
                    task['is_done'] = True
                    task['status'] = 'Done'
                return TaskStatus(**task)
            else:
                # Crear uno nuevo si no existe
                self._mock_tasks[task_id] = {...}
```

---

## 🔧 Problema 5-6: Scan Types - Usar Nmap Primero

### Situación Actual
- `SERVICE_SCAN` y `VULNERABILITY` usan OpenVAS
- OpenVAS no está instalado/configurado → mock mode → errores

### Propuesta de Flujo Mejorado

```
DISCOVERY  → Nmap -sn (ping scan)
PORT_SCAN  → Nmap -sV -F (quick ports + service detection)
SERVICE    → Nmap -sV -sC (full service detection) → NO OpenVAS
FULL       → Nmap -sV -sC -p- (all ports) → NO OpenVAS
VULNERABILITY → Nmap + Nuclei (si está instalado) → OpenVAS como fallback
```

### Implementación

#### `backend/app/api/v1/scans.py` - Línea 255-262

```python
# ANTES:
else:
    # Para vulnerability y otros, usar OpenVAS
    task = openvas_full_scan.delay(...)

# DESPUÉS:
elif scan_data.scan_type == ScanType.SERVICE_SCAN:
    # Usar Nmap para detección de servicios
    task = nmap_service_scan_task.delay(
        target=targets_str,
        organization_id=str(current_user.organization_id),
        scan_id=str(scan.id),
    )
elif scan_data.scan_type == ScanType.VULNERABILITY:
    # Usar Nuclei si está disponible, sino OpenVAS
    if nuclei_available():
        task = nuclei_scan_task.delay(
            target=targets_str,
            scan_id=str(scan.id),
        )
    else:
        # Fallback a OpenVAS (solo si está configurado)
        if openvas_available():
            task = openvas_full_scan.delay(...)
        else:
            raise HTTPException(
                status_code=400,
                detail="No vulnerability scanner available. Install Nuclei or configure OpenVAS."
            )
else:
    raise HTTPException(status_code=400, detail=f"Unsupported scan type: {scan_data.scan_type}")
```

---

## 🔧 Problema 7: Full Scan - Mismo Error que P3

### Síntoma
Similar al problema 3, el full scan también tiene el typo

### Solución

#### `backend/app/api/v1/scans.py` - Línea 250-254

```python
# ANTES:
elif scan_data.scan_type == ScanType.FULL:
    task = nmap_full_scan_task.delay(
        scan_id=scan.id,
        targets=targets_str,  # ❌
    )

# DESPUÉS:
elif scan_data.scan_type == ScanType.FULL:
    task = nmap_full_scan_task.delay(
        target=targets_str,                           # ✅
        organization_id=str(current_user.organization_id),  # ✅
        scan_id=str(scan.id),                         # ✅
    )
```

---

## 🔧 Problema 8: Notificaciones Mock

### Situación Actual
En `topbar.tsx` las notificaciones están hardcodeadas:

```tsx
<Badge>3</Badge>  // ← Hardcoded

<DropdownMenuItem>
  <span>Se detectó CVE-2024-1234 en servidor-prod-01</span>  // ← Hardcoded
  <span>hace 5 min</span>  // ← Hardcoded
</DropdownMenuItem>
```

### Solución Completa

#### 1. Crear modelo de Notification (Backend)

```python
# backend/app/models/notification.py
class Notification(Base):
    __tablename__ = "notifications"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    type: Mapped[str]  # 'vulnerability', 'scan_complete', 'asset_offline', etc.
    title: Mapped[str]
    message: Mapped[str]
    severity: Mapped[str] = mapped_column(default="info")
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]
    
    # Relaciones
    user: Mapped["User"] = relationship(back_populates="notifications")
```

#### 2. Crear API endpoint

```python
# backend/app/api/v1/notifications.py
@router.get("")
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    unread_only: bool = Query(False),
    limit: int = Query(10),
):
    """Obtener notificaciones del usuario."""
    query = select(Notification).where(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(limit)
    
    if unread_only:
        query = query.where(Notification.read == False)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/{id}/read")
async def mark_as_read(id: str, ...):
    """Marcar notificación como leída."""
    ...
```

#### 3. Crear hook y actualizar topbar (Frontend)

```typescript
// frontend/hooks/use-notifications.ts
export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.getNotifications({ limit: 10 }),
    refetchInterval: 30000, // Refrescar cada 30s
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () => api.getNotificationsCount(),
    refetchInterval: 30000,
  });
}
```

```tsx
// frontend/components/layout/topbar.tsx
const { data: notifications } = useNotifications();
const { data: unreadCount } = useUnreadCount();

<Badge>{unreadCount || 0}</Badge>

{notifications?.map(notif => (
  <DropdownMenuItem key={notif.id}>
    <span>{notif.title}</span>
    <span>{formatRelativeTime(notif.created_at)}</span>
  </DropdownMenuItem>
))}
```

---

## 📅 Plan de Implementación

### Día 18.5 - Correcciones Críticas (2-3 horas)

| Orden | Problema | Tiempo Est. | Prioridad |
|-------|----------|-------------|-----------|
| 1 | P3 + P7: Fix typo targets/target | 15 min | 🔴 CRÍTICA |
| 2 | P1: Scan status actualización | 30 min | 🔴 CRÍTICA |
| 3 | P2: Assets paginación | 20 min | 🔴 CRÍTICA |
| 4 | P4: OpenVAS logging fix | 20 min | 🟠 ALTA |
| 5 | P5-P6: Ajustar scan types | 30 min | 🟡 MEDIA |
| 6 | P8: Notificaciones (básico) | 1 hora | 🟡 MEDIA |

### Orden de Ejecución Recomendado

```
1. Fix P3 + P7 (targets → target) - INMEDIATO
   └── Probar port_scan y full_scan

2. Fix P1 (scan status) - INMEDIATO
   └── Agregar update_scan_status al final de workers
   └── Probar discovery con frontend

3. Fix P2 (assets) - INMEDIATO
   └── Verificar endpoint de assets
   └── Ajustar límite de paginación

4. Fix P4 (OpenVAS logging) - HOY
   └── Evitar key 'message' en extra dict
   └── Mejorar mock mode

5. Fix P5-P6 (scan types) - PUEDE ESPERAR
   └── Se puede hacer como parte del Día 20
   └── Documentar en FASE_03 como parte de Network Validation

6. Fix P8 (notificaciones) - PUEDE ESPERAR
   └── Se puede hacer en Día 25 (Dashboard Avanzado)
   └── Por ahora, ocultar el badge o poner "0"
```

---

## ✅ Checklist de Verificación

### Después de P3 + P7:
- [ ] `pnpm exec celery -A app.celery_app inspect registered` muestra tasks
- [ ] Crear PORT_SCAN → worker recibe tarea
- [ ] Crear FULL scan → worker recibe tarea

### Después de P1:
- [ ] Discovery scan → status cambia a "completed" en DB
- [ ] Frontend polling ve status "completed"
- [ ] Card de scan muestra resultados

### Después de P2:
- [ ] Página `/assets` muestra todos los assets
- [ ] Número coincide con Dashboard

### Después de P4:
- [ ] OpenVAS scan no causa KeyError en logs
- [ ] Mock mode funciona sin errores

---

## 🔗 Dependencias con Fase 3

| Problema | Impacto en Fase 3 | Resolución |
|----------|-------------------|------------|
| P1-P3, P7 | Bloquea TODO | Resolver ANTES de Día 19 |
| P4 | Bloquea Día 22-23 (OpenVAS/ZAP) | Resolver antes de Día 22 |
| P5-P6 | Afecta Día 20 (Network Scanning) | Integrar en Día 20 |
| P8 | Afecta Día 25 (Dashboard) | Integrar en Día 25 |

---

**Siguiente paso:** Implementar correcciones P3, P7, P1, P2 antes de continuar con Día 19.
