# 🚀 PLAN DE 3 DÍAS - Backend Pendientes

> **Fecha de inicio**: 6 de febrero de 2026
> **Objetivo**: Implementar los endpoints de backend faltantes y conectarlos al frontend

---

## 📊 PENDIENTES IDENTIFICADOS

| Feature | Backend | Frontend | Prioridad |
|---------|---------|----------|-----------|
| **Reports** | ❌ No existe | ❌ Mock | Alta |
| **Timeline Asset** | ❌ No existe | ❌ Vacío | Media |
| **Notificaciones** | ❌ No existe | ❌ Mock | Media |

---

## 📅 DÍA 1: Sistema de Reports

### Objetivo
Crear endpoints de generación y descarga de reportes en backend, y conectarlos al frontend.

### Tareas Backend

#### 1.1 Crear modelo Report (1h)
**Archivo**: `backend/app/models/report.py`

- [ ] Modelo Report con campos: id, type, format, status, file_path, created_at, completed_at
- [ ] Enum ReportType: executive, technical, compliance, vulnerability
- [ ] Enum ReportFormat: pdf, xlsx, json
- [ ] Enum ReportStatus: pending, generating, completed, failed

#### 1.2 Crear schemas de Report (30min)
**Archivo**: `backend/app/schemas/report.py`

- [ ] ReportCreate, ReportRead, GenerateReportRequest

#### 1.3 Crear endpoints de Reports (2h)
**Archivo**: `backend/app/api/v1/reports.py`

- [ ] GET /reports - Listar reportes del usuario
- [ ] POST /reports/generate - Generar nuevo reporte
- [ ] GET /reports/{id} - Detalle de reporte
- [ ] GET /reports/{id}/download - Descargar archivo
- [ ] DELETE /reports/{id} - Eliminar reporte

#### 1.4 Crear servicio de generación (2h)
**Archivo**: `backend/app/services/report_generator.py`

- [ ] Generador PDF con datos de vulnerabilidades
- [ ] Generador Excel con tablas
- [ ] Generador JSON con export completo

### Tareas Frontend

#### 1.5 Crear hook useReports (1h)
**Archivo**: `frontend/hooks/use-reports.ts`

- [ ] useReports - Listar reportes
- [ ] useGenerateReport - Crear nuevo
- [ ] useDownloadReport - Descargar

#### 1.6 Añadir API methods (30min)
**Archivo**: `frontend/lib/api.ts`

- [ ] getReports, generateReport, downloadReport, deleteReport

#### 1.7 Conectar página Reports (1h)
**Archivo**: `frontend/app/(dashboard)/reports/page.tsx`

- [ ] Reemplazar mocks con datos reales
- [ ] Implementar generación real
- [ ] Implementar descarga

### Entregables Día 1
- ✅ Backend: Modelo, schemas, endpoints de Reports
- ✅ Backend: Generación de PDF/Excel/JSON
- ✅ Frontend: Hook y API conectados
- ✅ Frontend: Página Reports funcional

---

## 📅 DÍA 2: Timeline de Assets

### Objetivo
Crear endpoint de timeline por asset y conectarlo al frontend.

### Tareas Backend

#### 2.1 Crear modelo ActivityLog (1h)
**Archivo**: `backend/app/models/activity.py`

- [ ] Modelo ActivityLog: id, asset_id, event_type, description, metadata, created_at
- [ ] Enum EventType: created, scanned, vuln_detected, status_changed, correlated

#### 2.2 Registrar eventos automáticamente (2h)
- [ ] Hook en creación de asset
- [ ] Hook en finalización de scan
- [ ] Hook en detección de vulnerabilidad
- [ ] Hook en correlación CVE

#### 2.3 Crear endpoint timeline (1h)
**Archivo**: `backend/app/api/v1/assets.py`

- [ ] GET /assets/{id}/timeline - Timeline de eventos del asset

### Tareas Frontend

#### 2.4 Crear hook useAssetTimeline (30min)
**Archivo**: `frontend/hooks/use-assets.ts`

- [ ] useAssetTimeline(assetId) - Obtener timeline

#### 2.5 Añadir API method (15min)
**Archivo**: `frontend/lib/api.ts`

- [ ] getAssetTimeline(assetId)

#### 2.6 Implementar UI Timeline (2h)
**Archivo**: `frontend/app/(dashboard)/assets/[id]/page.tsx`

- [ ] Componente Timeline con eventos
- [ ] Iconos por tipo de evento
- [ ] Fechas relativas

### Entregables Día 2
- ✅ Backend: Modelo ActivityLog
- ✅ Backend: Registro automático de eventos
- ✅ Backend: Endpoint timeline
- ✅ Frontend: Timeline visual en Asset Detail

---

## 📅 DÍA 3: Sistema de Notificaciones

### Objetivo
Crear sistema de preferencias de notificaciones y conectarlo.

### Tareas Backend

#### 3.1 Añadir campos a User (30min)
**Archivo**: `backend/app/models/user.py`

- [ ] Añadir campo notification_settings (JSON)

#### 3.2 Crear endpoints notificaciones (1h)
**Archivo**: `backend/app/api/v1/users.py`

- [ ] GET /users/me/notifications - Obtener preferencias
- [ ] PUT /users/me/notifications - Actualizar preferencias

#### 3.3 Crear servicio de notificaciones (2h)
**Archivo**: `backend/app/services/notifications.py`

- [ ] Envío de email para vulnerabilidades críticas
- [ ] Digest diario/semanal

### Tareas Frontend

#### 3.4 Actualizar hook useSettings (30min)
**Archivo**: `frontend/hooks/use-settings.ts`

- [ ] useNotificationSettings
- [ ] useUpdateNotificationSettings

#### 3.5 Conectar tab Notificaciones (1h)
**Archivo**: `frontend/app/(dashboard)/settings/page.tsx`

- [ ] Reemplazar mock con API real
- [ ] Guardar preferencias

### Tareas Extra

#### 3.6 Testing de integración (2h)
- [ ] Probar flujo completo de Reports
- [ ] Probar Timeline en assets
- [ ] Probar guardado de notificaciones

#### 3.7 Documentación final (1h)
- [ ] Actualizar README
- [ ] Actualizar documentación de API

### Entregables Día 3
- ✅ Backend: Preferencias de notificaciones
- ✅ Backend: Servicio de emails
- ✅ Frontend: Settings conectado completamente
- ✅ Testing y documentación

---

## ⏱️ Estimación de Tiempo

| Día | Backend | Frontend | Total |
|-----|---------|----------|-------|
| 1 | 5.5h | 2.5h | 8h |
| 2 | 4h | 2.75h | 6.75h |
| 3 | 3.5h | 1.5h + 3h extra | 8h |

---

## 🎯 Criterios de Éxito

Al finalizar los 3 días:

1. ✅ Reports generan PDF/Excel/JSON reales
2. ✅ Timeline muestra eventos reales por asset
3. ✅ Notificaciones se guardan en backend
4. ✅ 0 datos mock en toda la aplicación
5. ✅ Documentación actualizada
