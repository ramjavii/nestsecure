# =============================================================================
# NESTSECURE - PLAN DE ELIMINACIÓN DE MOCK DATA PARA PRODUCCIÓN
# =============================================================================
# Fecha: 4 de Febrero, 2026
# Objetivo: Preparar el sistema para lanzamiento a producción
# Tiempo Estimado: 4-6 horas de trabajo
# =============================================================================

## 📋 RESUMEN

Este plan detalla los pasos necesarios para eliminar todo el mock data del frontend
y preparar el sistema para producción.

---

## 🎯 ARCHIVOS A MODIFICAR

### Prioridad 1: CRÍTICO (Bloquea Producción)

| # | Archivo | Líneas | Descripción | Tiempo |
|---|---------|--------|-------------|--------|
| 1 | `frontend/app/(dashboard)/page.tsx` | 18-34 | mockStats en Dashboard | 15 min |
| 2 | `frontend/app/(dashboard)/scans/[id]/page.tsx` | 79-134 | mockVulns en Scan Detail | 30 min |
| 3 | `frontend/app/(dashboard)/assets/[id]/page.tsx` | 74-155 | mockVulnerabilities | 30 min |
| 4 | `frontend/app/(dashboard)/reports/page.tsx` | 64-100 | mockReports completo | 45 min |
| 5 | `frontend/components/dashboard/vuln-trend-chart.tsx` | 29+ | generateMockData() | 20 min |
| 6 | `frontend/components/dashboard/severity-pie-chart.tsx` | 38-44 | mock stats | 15 min |

### Prioridad 2: LIMPIEZA (Código muerto)

| # | Archivo | Descripción | Tiempo |
|---|---------|-------------|--------|
| 7 | `frontend/app/(dashboard)/assets/page.tsx` | Eliminar ENABLE_MOCK_DATA y mockAssets (ya disabled) | 10 min |
| 8 | `frontend/app/(dashboard)/scans/page.tsx` | Eliminar ENABLE_MOCK_DATA y mockScans (ya disabled) | 10 min |

---

## 📝 INSTRUCCIONES DETALLADAS

### 1. Dashboard Page (`page.tsx`)

**Ubicación:** `frontend/app/(dashboard)/page.tsx`

**Antes:**
```typescript
const mockStats = {
  assets: { total: 156, active: 142, inactive: 14 },
  scans: { running: 3, completed: 47 },
  vulnerabilities: { /* ... */ },
  risk_score: 72,
};

const displayStats = stats || mockStats;
```

**Después:**
```typescript
// Sin mock - usar skeleton loader cuando isLoading
// Mostrar valores 0 o N/A cuando no hay datos

const displayStats = stats || {
  assets: { total: 0, active: 0, inactive: 0 },
  scans: { running: 0, completed: 0 },
  vulnerabilities: { total: 0, critical: 0, high: 0, medium: 0, low: 0, info: 0, open: 0, fixed: 0 },
  risk_score: 0,
};
```

**O mejor - usar loading states:**
```typescript
if (statsLoading) {
  return <DashboardSkeleton />;
}

if (!stats) {
  return <EmptyDashboard />;
}
```

---

### 2. Scan Detail (`scans/[id]/page.tsx`)

**Ubicación:** `frontend/app/(dashboard)/scans/[id]/page.tsx`

**Antes (líneas 79-134):**
```typescript
const mockVulns: Partial<Vulnerability>[] = [
  { id: "v1", title: "SQL Injection...", severity: "critical", /* ... */ },
  // más mocks...
];

// En render:
{mockVulns.map((vuln) => (
  // ...
))}
```

**Después:**
```typescript
// Agregar hook para obtener vulnerabilidades del scan
const { data: scanVulns, isLoading: vulnsLoading } = useScanVulnerabilities(scanId);

// En render:
{vulnsLoading ? (
  <TableSkeleton />
) : scanVulns && scanVulns.length > 0 ? (
  scanVulns.map((vuln) => (
    // ...
  ))
) : (
  <EmptyState 
    icon={Shield}
    title="Sin vulnerabilidades"
    description="No se encontraron vulnerabilidades en este escaneo"
  />
)}
```

**Agregar hook (si no existe):**
```typescript
// frontend/hooks/use-scans.ts
export function useScanVulnerabilities(scanId: string) {
  return useQuery({
    queryKey: ['scan-vulnerabilities', scanId],
    queryFn: () => api.getScanVulnerabilities(scanId),
    enabled: !!scanId,
  });
}
```

---

### 3. Asset Detail (`assets/[id]/page.tsx`)

**Ubicación:** `frontend/app/(dashboard)/assets/[id]/page.tsx`

**Antes (líneas 74-155):**
```typescript
const mockVulnerabilities: Vulnerability[] = [/* ... */];
const displayVulns = vulnerabilities || mockVulnerabilities;
```

**Después:**
```typescript
// Eliminar mockVulnerabilities completamente

// En render:
{vulnsLoading ? (
  <TableSkeleton />
) : vulnerabilities && vulnerabilities.length > 0 ? (
  // mostrar vulnerabilidades
) : (
  <EmptyState 
    icon={Shield}
    title="Sin vulnerabilidades"
    description="No hay vulnerabilidades registradas para este asset"
  />
)}
```

---

### 4. Reports Page (`reports/page.tsx`)

**Ubicación:** `frontend/app/(dashboard)/reports/page.tsx`

**Opción A: Mostrar "Coming Soon"**
```typescript
export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Reportes"
        description="Genera y descarga reportes de seguridad"
      />

      <Card className="flex flex-col items-center justify-center py-16">
        <FileText className="h-16 w-16 text-muted-foreground mb-4" />
        <h2 className="text-2xl font-semibold mb-2">Próximamente</h2>
        <p className="text-muted-foreground text-center max-w-md">
          La generación de reportes estará disponible en una próxima actualización.
          Mientras tanto, puedes exportar datos desde las páginas de Assets y Vulnerabilidades.
        </p>
      </Card>
    </div>
  );
}
```

**Opción B: Implementar API de Reportes** (Requiere backend)
- Crear endpoints en backend: `POST /api/v1/reports`, `GET /api/v1/reports`
- Crear hooks en frontend: `useReports()`, `useCreateReport()`
- Conectar UI existente a la API

---

### 5. VulnTrendChart (`vuln-trend-chart.tsx`)

**Ubicación:** `frontend/components/dashboard/vuln-trend-chart.tsx`

**Antes:**
```typescript
const chartData = data || generateMockData();

function generateMockData() {
  // genera 30 días de datos falsos
}
```

**Después:**
```typescript
if (isLoading) {
  return <ChartSkeleton />;
}

if (!data || data.length === 0) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Vulnerabilidades - Últimos 30 días</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-center h-[300px]">
        <div className="text-center text-muted-foreground">
          <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No hay datos de tendencia disponibles</p>
        </div>
      </CardContent>
    </Card>
  );
}

// Usar data directamente sin fallback
return (
  <Card>
    {/* chart con data real */}
  </Card>
);
```

---

### 6. SeverityPieChart (`severity-pie-chart.tsx`)

**Ubicación:** `frontend/components/dashboard/severity-pie-chart.tsx`

**Antes:**
```typescript
const stats = data || {
  critical: 8,
  high: 23,
  medium: 45,
  low: 67,
  info: 12,
};
```

**Después:**
```typescript
if (isLoading) {
  return <ChartSkeleton />;
}

const stats = data;

if (!stats || Object.values(stats).every(v => v === 0)) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Distribución por Severidad</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-center h-[300px]">
        <div className="text-center text-muted-foreground">
          <PieChart className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No hay vulnerabilidades registradas</p>
        </div>
      </CardContent>
    </Card>
  );
}

// Continuar con chart usando stats real
```

---

### 7 & 8. Eliminar código muerto

**Assets Page (`assets/page.tsx`):**
```typescript
// ELIMINAR estas líneas (78-147):
const ENABLE_MOCK_DATA = false;
const mockAssets: Asset[] = ENABLE_MOCK_DATA ? [/* ... */] : [];

// CAMBIAR:
const data = assetsResponse?.items || (ENABLE_MOCK_DATA ? mockAssets : []);
// A:
const data = assetsResponse?.items || [];
```

**Scans Page (`scans/page.tsx`):**
```typescript
// ELIMINAR estas líneas (72-196):
const ENABLE_MOCK_DATA = false;
const mockScans: Scan[] = ENABLE_MOCK_DATA ? [/* ... */] : [];

// CAMBIAR:
const data = scansResponse?.items || (ENABLE_MOCK_DATA ? mockScans : []);
// A:
const data = scansResponse?.items || [];
```

---

## 🔧 CONFIGURACIÓN DE PRODUCCIÓN

### Variables de Entorno Backend (`.env.production`)

```env
# Environment
ENVIRONMENT=production
DEBUG=false

# Security - CAMBIAR ESTOS VALORES
JWT_SECRET_KEY=GENERAR_CLAVE_SEGURA_DE_64_CARACTERES
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database - CAMBIAR PASSWORD
DATABASE_URL=postgresql+asyncpg://nestsecure:CAMBIAR_PASSWORD_SEGURO@postgres:5432/nestsecure

# Redis
REDIS_URL=redis://redis:6379/0

# CORS - Ajustar al dominio real
CORS_ORIGINS=["https://tu-dominio.com"]

# GVM (OpenVAS)
GVM_HOST=gvm
GVM_PORT=9390
GVM_USERNAME=admin
GVM_PASSWORD=CAMBIAR_PASSWORD_GVM
```

### Variables de Entorno Frontend (`.env.production`)

```env
NODE_ENV=production

# API URLs - Ajustar al dominio real
NEXT_PUBLIC_API_URL=https://tu-dominio.com/api/v1
NEXT_PUBLIC_BROWSER_API_URL=https://tu-dominio.com/api/v1
```

---

## ✅ CHECKLIST DE EJECUCIÓN

### Día 1: Eliminación de Mocks (4h)

- [ ] 1.1 Dashboard page - Eliminar mockStats
- [ ] 1.2 Scan Detail - Eliminar mockVulns, agregar hook
- [ ] 1.3 Asset Detail - Eliminar mockVulnerabilities
- [ ] 1.4 Reports page - Implementar "Coming Soon" o API
- [ ] 1.5 VulnTrendChart - Eliminar generateMockData()
- [ ] 1.6 SeverityPieChart - Eliminar mock stats
- [ ] 1.7 Assets page - Limpiar código muerto
- [ ] 1.8 Scans page - Limpiar código muerto

### Día 2: Configuración y Deploy (2h)

- [ ] 2.1 Crear .env.production para backend
- [ ] 2.2 Crear .env.production para frontend
- [ ] 2.3 Generar JWT_SECRET_KEY seguro
- [ ] 2.4 Cambiar passwords por defecto
- [ ] 2.5 Configurar CORS para dominio real
- [ ] 2.6 Build de producción
- [ ] 2.7 Test end-to-end

### Post-Deploy (Opcional)

- [ ] 3.1 Configurar Nginx reverse proxy
- [ ] 3.2 Configurar SSL/TLS con Let's Encrypt
- [ ] 3.3 Configurar backup automático de DB
- [ ] 3.4 Configurar monitoreo

---

## 🚨 COMANDOS ÚTILES

```bash
# Generar JWT_SECRET_KEY seguro
openssl rand -hex 32

# Build de producción
docker compose -f docker-compose.prod.yml build

# Deploy
docker compose -f docker-compose.prod.yml up -d

# Ver logs
docker compose -f docker-compose.prod.yml logs -f

# Verificar salud
curl http://localhost:8000/api/v1/health
curl http://localhost:3000/api/health

# Ejecutar migraciones en producción
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## 📊 ESTIMACIÓN DE TIEMPO

| Tarea | Tiempo Estimado |
|-------|-----------------|
| Eliminar mocks Dashboard | 30 min |
| Eliminar mocks Scan/Asset Detail | 1 hora |
| Reports "Coming Soon" | 30 min |
| Limpiar Charts | 45 min |
| Limpiar código muerto | 30 min |
| Configuración producción | 1 hora |
| Testing | 1 hora |
| **TOTAL** | **5-6 horas** |

---

*Plan creado el 4 de Febrero, 2026*
*Estado: LISTO PARA EJECUTAR*
