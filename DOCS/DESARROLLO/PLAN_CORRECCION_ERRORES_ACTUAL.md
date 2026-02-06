# Plan de Corrección de Errores - NESTSECURE

## Análisis de Errores

### 🔴 Categoría 1: Errores FALSOS POSITIVOS (NO requieren corrección)

#### 1.1 Errores en `scripts/init-db.sql`
**Causa**: VS Code tiene configurado un linter de SQL Server (MSSQL) pero el archivo es PostgreSQL.
- `CREATE EXTENSION IF NOT EXISTS` es sintaxis válida de PostgreSQL
- `DO $$ ... $$` bloques anónimos son válidos en PostgreSQL
- `RAISE NOTICE` es válido en PostgreSQL

**Solución**: Estos NO son errores reales. Para eliminar los warnings:
- Opción A: Ignorar (recomendado - no afectan funcionamiento)
- Opción B: Agregar comentario `-- sql-dialect: postgresql` al inicio
- Opción C: Configurar VS Code para usar PostgreSQL en lugar de MSSQL

#### 1.2 Warnings de Python en `reports.py`
**Causa**: Las librerías `openpyxl` y `reportlab` no están instaladas en el entorno virtual actual.
- Son imports dinámicos dentro de try/except
- Se usan solo cuando se genera el reporte

**Solución**: No es error de código. Solo ejecutar:
```bash
pip install reportlab openpyxl
```

---

### 🟡 Categoría 2: Warnings de Tailwind CSS (Baja prioridad)

Son sugerencias de Tailwind v4 para usar "clases canónicas" más cortas:
- `w-[140px]` → `w-35`
- `max-w-[300px]` → `max-w-75`
- `h-[300px]` → `h-75`
- `flex-shrink-0` → `shrink-0`

**Solución**: Opcional. Estas clases funcionan correctamente. Solo son sugerencias estéticas.

---

### 🔴 Categoría 3: Errores TypeScript REALES (Requieren corrección)

#### 3.1 Error: Módulo `@/components/shared/loading-spinner` no encontrado
**Archivo**: `frontend/app/(dashboard)/reports/page.tsx` línea 31
**Causa**: El componente `LoadingSpinner` no existe en la carpeta `shared`
**Componentes existentes en shared**:
- `loading-skeleton.tsx` ✅ existe
- `loading-spinner.tsx` ❌ NO existe

**Solución**: 
- Opción A: Crear el componente `loading-spinner.tsx`
- Opción B: Usar `loading-skeleton.tsx` que ya existe

#### 3.2 Error: Módulos ZAP no encontrados en index.ts
**Archivo**: `frontend/components/zap/index.ts` líneas 8-9
**Causa**: El export usa llaves `{ }` pero los archivos exportan `default`
**Archivos existentes**:
- `zap-alerts-table.tsx` ✅
- `zap-scan-history.tsx` ✅

**Problema**: Los exports nombrados vs default no coinciden
**Solución**: Verificar cómo exportan los componentes y ajustar el index.ts

#### 3.3 Error: Tipo ScanType incompatible
**Archivo**: `frontend/components/scans/scan-form-modal.tsx` línea 148
**Causa**: El schema Zod incluye `service_scan` pero el tipo `CreateScanPayload` no lo incluye
**Código actual**:
```typescript
scan_type: z.enum(['discovery', 'port_scan', 'service_scan', 'vulnerability', 'full'])
```
**Tipo CreateScanPayload** probablemente tiene:
```typescript
scan_type: 'discovery' | 'port_scan' | 'vulnerability' | 'full'
```

**Solución**: Sincronizar el tipo `ScanType` en `types/index.ts` para incluir `service_scan`

---

## Plan de Ejecución Paso a Paso

### Paso 1: Crear `loading-spinner.tsx`
```
Archivo: frontend/components/shared/loading-spinner.tsx
Acción: Crear componente simple de spinner
```

### Paso 2: Corregir exports de ZAP
```
Archivo: frontend/components/zap/index.ts
Acción: Verificar y corregir exports nombrados
```

### Paso 3: Sincronizar tipo ScanType
```
Archivo: frontend/types/index.ts
Acción: Agregar 'service_scan' al tipo ScanType
```

### Paso 4: Verificar CreateScanPayload
```
Archivo: frontend/types/index.ts
Acción: Verificar que CreateScanPayload use ScanType
```

---

## Resumen de Acciones

| # | Archivo | Acción | Prioridad |
|---|---------|--------|-----------|
| 1 | `components/shared/loading-spinner.tsx` | Crear | 🔴 Alta |
| 2 | `components/zap/index.ts` | Corregir exports | 🔴 Alta |
| 3 | `types/index.ts` | Agregar service_scan a ScanType | 🔴 Alta |
| 4 | `scripts/init-db.sql` | Ignorar (falso positivo) | ⚪ N/A |
| 5 | Warnings CSS | Opcional - estéticos | 🟡 Baja |
| 6 | Warnings Python | pip install libs | 🟡 Baja |

---

## Tiempo Estimado
- Correcciones críticas: ~10 minutos
- Verificación: ~5 minutos
- Total: ~15 minutos
