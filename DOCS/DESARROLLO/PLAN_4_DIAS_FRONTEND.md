# 🚀 PLAN DE 4 DÍAS - Completar Integración Frontend

> **Fecha de creación**: $(date)
> **Objetivo**: Conectar todas las APIs disponibles con el frontend, eliminar datos mock, y completar componentes vacíos.

---

## 📊 ANÁLISIS PREVIO: Estado Actual del Frontend

### ✅ APIs Disponibles en `lib/api.ts` (1,080 líneas)
| Categoría | Métodos | Estado en UI |
|-----------|---------|--------------|
| **Auth** | login, register, logout, getProfile | ✅ Conectado |
| **Dashboard** | getDashboardStats, getRecentScans, getVulnerabilityTrend | ✅ Conectado |
| **Assets** | CRUD + getServices, getVulnerabilities, getScans | ⚠️ Parcial - Tab Scans vacío |
| **Scans** | CRUD + getResults, getHosts, getLogs | ✅ Conectado en detalle |
| **Vulnerabilities** | CRUD + updateStatus | ✅ Conectado |
| **CVE** | search, lookup, stats, sync, trending, KEV, exploitable | ✅ Conectado |
| **Correlation** | correlateService, correlateScan, correlateAsset, getServiceCPE | ⚠️ Hook existe, componente existe, NO integrado |
| **Nuclei** | startScan, getStatus, getResults, getProfiles, quickScan, cveScan, webScan | ⚠️ Hook existe, componente existe, NO integrado |
| **ZAP** | startScan, getStatus, getResults, quickScan, fullScan, apiScan, spaScan, getProfiles | ⚠️ Hook existe, componente existe, NO integrado |
| **Network** | validateTarget, validateMultiple, getNetworkInfo, getPrivateRanges | ✅ Usado en ScanFormModal |
| **Reports** | ❌ NO EXISTE EN API.TS | ❌ Página usa MOCK |
| **Settings/Profile** | update, changePassword | ⚠️ Página usa MOCK |

### 🔴 Páginas con Datos MOCK
1. **`/reports`** - Completamente mock, sin llamadas API
2. **`/settings`** - Todas las acciones (guardar perfil, cambiar contraseña, notificaciones) son mock
3. **Dashboard top-vulns-table** - Tiene datos mock como fallback

### 🟡 Componentes NO Integrados
1. **`NucleiScanButton`** (486 líneas) - COMPLETO pero no usado en ninguna página
2. **`ZapScanButton`** (435 líneas) - COMPLETO pero no usado en ninguna página
3. **`CorrelateButton`** (339 líneas) - COMPLETO pero no usado en ninguna página
4. **`ZapAlertsTable`** - Existe pero no usado
5. **`ZapScanHistory`** - Existe pero no usado

### 🟡 Tabs/Secciones Vacías
1. **Assets [id]** - Tab "Historial de Scans" muestra EmptyState sin llamar API
2. **Assets [id]** - Tab "Timeline" sin implementar
3. **Scans [id]** - Falta botón para correlacionar servicios
4. **Assets [id]** - Falta botón para escanear con Nuclei/ZAP

---

## 📅 DÍA 1: Integración de Escaneos Avanzados (Nuclei + ZAP)

### Objetivo
Integrar los componentes `NucleiScanButton` y `ZapScanButton` en las páginas correspondientes para que los usuarios puedan ejecutar escaneos de vulnerabilidades web.

### Tareas

#### 1.1 Integrar NucleiScanButton en Assets Detail (2h)
**Archivo**: `frontend/app/(dashboard)/assets/[id]/page.tsx`

- [ ] Importar `NucleiScanButton` de `@/components/nuclei/nuclei-scan-button`
- [ ] Añadir botón en el header junto a "Editar" y "Eliminar"
- [ ] Pasar `target={displayAsset.ip_address}` y `assetId={id}`
- [ ] Añadir callback `onComplete` para refrescar vulnerabilidades

```tsx
import { NucleiScanButton } from '@/components/nuclei/nuclei-scan-button';

// En el header:
<NucleiScanButton 
  target={displayAsset.ip_address}
  assetId={id}
  variant="outline"
/>
```

#### 1.2 Integrar ZapScanButton en Assets Detail (2h)
**Archivo**: `frontend/app/(dashboard)/assets/[id]/page.tsx`

- [ ] Importar `ZapScanButton` de `@/components/zap/zap-scan-button`
- [ ] Añadir junto al NucleiScanButton
- [ ] Configurar con hostname si existe, o IP si no

```tsx
import { ZapScanButton } from '@/components/zap/zap-scan-button';

// En el header:
<ZapScanButton 
  defaultUrl={displayAsset.hostname ? `http://${displayAsset.hostname}` : `http://${displayAsset.ip_address}`}
  assetId={id}
/>
```

#### 1.3 Crear página/modal de resultados Nuclei (3h)
**Nuevo archivo**: `frontend/app/(dashboard)/scans/nuclei/[taskId]/page.tsx`

- [ ] Crear página de detalle de scan Nuclei
- [ ] Usar `useNucleiScanStatus` y `useNucleiScanResults`
- [ ] Mostrar progreso en tiempo real
- [ ] Tabla de findings con severidad
- [ ] Exportar resultados

#### 1.4 Crear página/modal de resultados ZAP (3h)
**Nuevo archivo**: `frontend/app/(dashboard)/scans/zap/[taskId]/page.tsx`

- [ ] Crear página de detalle de scan ZAP
- [ ] Usar `useZapScanStatus` y `useZapScanResults`
- [ ] Integrar `ZapAlertsTable` existente
- [ ] Mostrar progreso por fases (spider, active, passive)
- [ ] Tabla de alerts con risk level

#### 1.5 Añadir enlaces en Scans list (1h)
**Archivo**: `frontend/app/(dashboard)/scans/page.tsx`

- [ ] Detectar si un scan tiene resultados Nuclei/ZAP asociados
- [ ] Mostrar badges indicando tipo de scan
- [ ] Links a páginas de detalle correspondientes

### Entregables Día 1
- ✅ NucleiScanButton funcional desde Asset Detail
- ✅ ZapScanButton funcional desde Asset Detail
- ✅ Página de resultados Nuclei con tabla de findings
- ✅ Página de resultados ZAP con alerts
- ✅ Usuario puede ejecutar scans de vulnerabilidades web desde cualquier asset

---

## 📅 DÍA 2: Integración de Correlation + Asset Scans History

### Objetivo
Conectar el sistema de correlación CVE y completar el historial de scans en assets.

### Tareas

#### 2.1 Integrar CorrelateButton en Scan Detail (2h)
**Archivo**: `frontend/app/(dashboard)/scans/[id]/page.tsx`

- [ ] Importar `CorrelateButton` de `@/components/correlation/correlate-button`
- [ ] Añadir botón en header "Correlacionar con CVEs"
- [ ] Configurar tipo `scan` con `resourceId={id}`
- [ ] Mostrar toast con resultados

```tsx
import { CorrelateButton } from '@/components/correlation/correlate-button';

// En acciones:
<CorrelateButton 
  type="scan"
  resourceId={id}
  resourceName={scan.name}
  onComplete={(result) => {
    toast({ title: `${result.vulnerabilities_created} vulnerabilidades creadas` });
    refetchResults();
  }}
/>
```

#### 2.2 Integrar CorrelateButton en Asset Detail (2h)
**Archivo**: `frontend/app/(dashboard)/assets/[id]/page.tsx`

- [ ] Añadir `CorrelateButton` con tipo `asset`
- [ ] Añadir en cada servicio individual también (tipo `service`)
- [ ] Refrescar vulnerabilidades después de correlación

#### 2.3 Completar Tab "Historial de Scans" en Asset Detail (3h)
**Archivo**: `frontend/app/(dashboard)/assets/[id]/page.tsx`

- [ ] Ya existe hook `useAssetScans(id)` pero NO se llama
- [ ] Importar y usar `useAssetScans`
- [ ] Reemplazar EmptyState por tabla real
- [ ] Mostrar: nombre scan, tipo, fecha, estado, # vulnerabilidades

```tsx
const { data: scansHistory } = useAssetScans(id);
const displayScans = scansHistory || [];

// En TabsContent value="scans":
{displayScans.length === 0 ? (
  <EmptyState ... />
) : (
  <Table>
    {displayScans.map((scan) => (...))}
  </Table>
)}
```

#### 2.4 Añadir CorrelateButton por servicio (2h)
**Archivo**: `frontend/app/(dashboard)/scans/[id]/page.tsx` (HostRow component)

- [ ] En la vista expandida de servicios, añadir botón de correlación por servicio
- [ ] Usar tipo `service` con `resourceId={service.id}`

#### 2.5 Crear indicador de CVEs correlacionados (1h)
**Archivo**: `frontend/components/shared/cve-indicator.tsx`

- [ ] Nuevo componente que muestra si un servicio tiene CVEs correlacionados
- [ ] Badge con contador de CVEs
- [ ] Tooltip con lista de CVE IDs

### Entregables Día 2
- ✅ Correlación de scans completos con un click
- ✅ Correlación de assets completos
- ✅ Correlación de servicios individuales
- ✅ Historial de scans funcional en Asset Detail
- ✅ Indicadores visuales de CVEs correlacionados

---

## 📅 DÍA 3: Reports y Settings (Eliminar Mocks)

### Objetivo
Eliminar todos los datos mock de Reports y Settings, conectando con APIs reales.

### Tareas

#### 3.1 Crear hook useReports (1h)
**Nuevo archivo**: `frontend/hooks/use-reports.ts`

```tsx
export function useReports(params?: { type?: string; format?: string }) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => api.getReports(params),
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateReportPayload) => api.generateReport(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: (reportId: string) => api.downloadReport(reportId),
  });
}
```

#### 3.2 Añadir APIs de Reports en api.ts (1h)
**Archivo**: `frontend/lib/api.ts`

```tsx
// Reports
async getReports(params?: { type?: string; format?: string }): Promise<Report[]> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.append('type', params.type);
  if (params?.format) searchParams.append('format', params.format);
  return this.request<Report[]>(`/reports?${searchParams}`);
}

async generateReport(payload: GenerateReportPayload): Promise<Report> {
  return this.request<Report>('/reports/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

async downloadReport(reportId: string): Promise<Blob> {
  const response = await fetch(`${this.baseUrl}/reports/${reportId}/download`, {
    headers: this.getHeaders(),
  });
  return response.blob();
}
```

#### 3.3 Conectar página Reports con API (3h)
**Archivo**: `frontend/app/(dashboard)/reports/page.tsx`

- [ ] Importar `useReports` y `useGenerateReport`
- [ ] Reemplazar mock data con datos reales
- [ ] Implementar `handleGenerateReport` real
- [ ] Añadir descarga de reportes
- [ ] Mostrar lista de reportes históricos

#### 3.4 Crear hook useSettings (1h)
**Nuevo archivo**: `frontend/hooks/use-settings.ts`

```tsx
export function useUpdateProfile() {
  return useMutation({
    mutationFn: (payload: UpdateProfilePayload) => api.updateProfile(payload),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (payload: ChangePasswordPayload) => api.changePassword(payload),
  });
}

export function useNotificationSettings() {
  return useQuery({
    queryKey: ['settings', 'notifications'],
    queryFn: () => api.getNotificationSettings(),
  });
}

export function useUpdateNotificationSettings() {
  return useMutation({
    mutationFn: (payload) => api.updateNotificationSettings(payload),
  });
}
```

#### 3.5 Añadir APIs de Settings en api.ts (1h)
**Archivo**: `frontend/lib/api.ts`

```tsx
// Settings
async updateProfile(payload: UpdateProfilePayload): Promise<User> {
  return this.request<User>('/users/me', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

async changePassword(payload: ChangePasswordPayload): Promise<void> {
  return this.request<void>('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

async getNotificationSettings(): Promise<NotificationSettings> {
  return this.request<NotificationSettings>('/users/me/notifications');
}

async updateNotificationSettings(payload: NotificationSettings): Promise<void> {
  return this.request<void>('/users/me/notifications', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
```

#### 3.6 Conectar Settings con APIs reales (2h)
**Archivo**: `frontend/app/(dashboard)/settings/page.tsx`

- [ ] Importar hooks de settings
- [ ] Reemplazar `setTimeout` por llamadas reales
- [ ] Manejar errores apropiadamente
- [ ] Actualizar auth store después de cambios de perfil

### Entregables Día 3
- ✅ Página Reports completamente funcional
- ✅ Generación real de reportes PDF/Excel/JSON
- ✅ Historial de reportes generados
- ✅ Perfil de usuario editable con API real
- ✅ Cambio de contraseña funcional
- ✅ Configuración de notificaciones persistente

---

## 📅 DÍA 4: Polish, Timeline, y Validación Final

### Objetivo
Completar features pendientes menores, implementar timeline, y validar toda la integración.

### Tareas

#### 4.1 Implementar Timeline en Asset Detail (2h)
**Archivo**: `frontend/app/(dashboard)/assets/[id]/page.tsx`

- [ ] Crear hook `useAssetTimeline(id)` 
- [ ] Añadir API endpoint `getAssetTimeline` en api.ts
- [ ] Implementar UI de timeline con eventos:
  - Creación del asset
  - Scans ejecutados
  - Vulnerabilidades detectadas
  - Cambios de estado
  - Correlaciones realizadas

#### 4.2 Eliminar datos mock de top-vulns-table (1h)
**Archivo**: `frontend/components/dashboard/top-vulns-table.tsx`

- [ ] Remover el fallback de mock data
- [ ] Usar solo `vulnerabilities` prop
- [ ] Mejorar loading state

#### 4.3 Añadir validación de red en formularios de scan (1h)
**Archivo**: `frontend/components/scans/scan-form-modal.tsx`

- [ ] Asegurar que `useValidateTarget` está siendo usado
- [ ] Mostrar feedback visual de validación
- [ ] Bloquear submit si hay IPs públicas (para seguridad)

#### 4.4 Crear página de Nuclei/ZAP settings (2h)
**Nuevo archivo**: `frontend/app/(dashboard)/settings/scanners/page.tsx`

- [ ] Mostrar estado de Nuclei (versión, templates)
- [ ] Mostrar estado de ZAP (versión, disponibilidad)
- [ ] Configuración de perfiles por defecto
- [ ] Botón para actualizar templates de Nuclei

#### 4.5 Testing de integración completa (2h)
Validar manualmente:

- [ ] Login → Dashboard muestra datos reales
- [ ] Assets → Lista con datos reales
- [ ] Asset Detail → Services, Vulnerabilities, Scans History
- [ ] Asset Detail → Botones Nuclei/ZAP funcionan
- [ ] Scan Detail → Hosts, Results, Logs, Correlación
- [ ] Vulnerabilities → Lista y detalle
- [ ] CVE → Búsqueda funcional
- [ ] Reports → Generar y descargar
- [ ] Settings → Guardar cambios

#### 4.6 Documentar cambios (1h)
- [ ] Actualizar README con nuevas features
- [ ] Actualizar ESTADO_PROYECTO_COMPLETO.md
- [ ] Crear CHANGELOG con todo lo implementado

### Entregables Día 4
- ✅ Timeline funcional en Asset Detail
- ✅ Sin datos mock en ninguna parte
- ✅ Página de configuración de scanners
- ✅ Validación completa de toda la integración
- ✅ Documentación actualizada

---

## 📝 Resumen de Archivos a Crear/Modificar

### Archivos Nuevos
1. `frontend/app/(dashboard)/scans/nuclei/[taskId]/page.tsx`
2. `frontend/app/(dashboard)/scans/zap/[taskId]/page.tsx`
3. `frontend/hooks/use-reports.ts`
4. `frontend/hooks/use-settings.ts`
5. `frontend/hooks/use-timeline.ts`
6. `frontend/components/shared/cve-indicator.tsx`
7. `frontend/app/(dashboard)/settings/scanners/page.tsx`

### Archivos a Modificar
1. `frontend/app/(dashboard)/assets/[id]/page.tsx` - +Nuclei, +ZAP, +Correlate, +Scans History, +Timeline
2. `frontend/app/(dashboard)/scans/[id]/page.tsx` - +Correlate button
3. `frontend/app/(dashboard)/scans/page.tsx` - +badges tipo scan
4. `frontend/app/(dashboard)/reports/page.tsx` - Eliminar mocks
5. `frontend/app/(dashboard)/settings/page.tsx` - Eliminar mocks
6. `frontend/lib/api.ts` - +Reports APIs, +Settings APIs, +Timeline API
7. `frontend/components/dashboard/top-vulns-table.tsx` - Eliminar mocks

### Tipos a Añadir en `types/index.ts`
```typescript
export interface Report {
  id: string;
  type: 'executive' | 'technical' | 'compliance' | 'vulnerability';
  format: 'pdf' | 'xlsx' | 'json';
  status: 'pending' | 'generating' | 'completed' | 'failed';
  created_at: string;
  completed_at: string | null;
  download_url: string | null;
  size_bytes: number | null;
}

export interface GenerateReportPayload {
  type: string;
  format: string;
  date_range: string;
  filters?: Record<string, unknown>;
}

export interface TimelineEvent {
  id: string;
  event_type: 'created' | 'scanned' | 'vuln_detected' | 'status_changed' | 'correlated';
  description: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface NotificationSettings {
  email_critical: boolean;
  email_high: boolean;
  email_medium: boolean;
  email_scan_complete: boolean;
  push_enabled: boolean;
  daily_digest: boolean;
  weekly_report: boolean;
}
```

---

## ⏱️ Estimación de Tiempo por Día

| Día | Tareas Principales | Horas Estimadas |
|-----|-------------------|-----------------|
| **Día 1** | Nuclei + ZAP integration | 11h |
| **Día 2** | Correlation + Asset Scans | 10h |
| **Día 3** | Reports + Settings | 9h |
| **Día 4** | Timeline + Polish + Testing | 9h |
| **Total** | | **39h** |

---

## 🎯 Criterios de Éxito

Al finalizar los 4 días:

1. ✅ **0 datos mock** en toda la aplicación
2. ✅ **Todos los componentes** (Nuclei, ZAP, Correlate) integrados
3. ✅ **Todas las APIs** en api.ts tienen uso en el frontend
4. ✅ **Todas las tabs** muestran datos reales
5. ✅ **Reports** generan y descargan archivos reales
6. ✅ **Settings** persisten cambios en backend
7. ✅ **Usuario** puede ejecutar workflow completo:
   - Crear asset → Escanear → Ver servicios → Correlacionar CVEs → Generar reporte

---

## 🚨 Dependencias Backend

Verificar que estos endpoints existan en backend:

| Endpoint | Router | Estado |
|----------|--------|--------|
| `GET /assets/{id}/scans` | assets.py | ✅ Verificar |
| `POST /reports/generate` | ❓ | ⚠️ Puede no existir |
| `GET /reports` | ❓ | ⚠️ Puede no existir |
| `GET /reports/{id}/download` | ❓ | ⚠️ Puede no existir |
| `PUT /users/me` | users.py | ✅ Verificar |
| `POST /auth/change-password` | auth.py | ✅ Verificar |
| `GET /users/me/notifications` | ❓ | ⚠️ Puede no existir |
| `GET /assets/{id}/timeline` | ❓ | ⚠️ Puede no existir |

**NOTA**: Si algún endpoint no existe, se documentará pero se implementará un stub o se marcará para Fase 2.
