# =============================================================================
# NESTSECURE - FASE 3: PLAN DE IMPLEMENTACIÓN COMPLETO
# =============================================================================
# Fecha Inicio: 2026-02-05 (Post Día 17)
# Duración Estimada: 10-12 días de desarrollo
# Objetivo: Sistema completo funcional con CVE correlation y network scanning
# =============================================================================

## 📋 ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estado Actual](#estado-actual-post-fase-2)
3. [Arquitectura Completa](#arquitectura-fase-3)
4. [Día 18: CVE Infrastructure ✅](#día-18-cve-infrastructure-completado)
5. [Día 19: CVE Frontend Pages](#día-19-cve-frontend-pages)
6. [Día 20: Network Scanning & Validation](#día-20-network-scanning--validation)
7. [Día 21: Service-to-CVE Correlation](#día-21-service-to-cve-correlation)
8. [Día 22: Nuclei Installation & Integration](#día-22-nuclei-installation--integration)
9. [Día 23: ZAP Worker Implementation](#día-23-zap-worker-implementation)
10. [Día 24: Asset & Scan CRUD Completion](#día-24-asset--scan-crud-completion)
11. [Día 25: Dashboard Avanzado](#día-25-dashboard-avanzado)
12. [Día 26: Testing Suite](#día-26-testing-suite)
13. [Día 27: Performance & Security](#día-27-performance--security)
14. [Checklist Final](#checklist-final)

---

## 📊 RESUMEN EJECUTIVO

### Objetivos de la Fase 3

La Fase 3 transforma NESTSECURE en un sistema completo de gestión de vulnerabilidades con capacidades enterprise-grade.

**Componentes Clave:**
- ✅ **CVE Infrastructure** - Types, API, Hooks, Components (DÍA 18 COMPLETADO)
- 🔍 **CVE Search Frontend** - Interfaz completa de búsqueda y detalle de CVEs
- 🌐 **Network Scanning** - Validación y restricción **SOLO A RED LOCAL**
- 🔗 **Service→CVE Correlation** - Búsqueda automática de CVEs por servicios/puertos detectados
- 🛠️ **Nuclei Integration** - Scanner de vulnerabilidades instalado y funcional
- 🕷️ **ZAP Integration** - Scanner de aplicaciones web completo
- 📊 **Dashboard Completo** - Todas las métricas y widgets funcionales
- ✅ **Testing Suite** - Tests unitarios, integración y E2E completos

### Métricas Objetivo

| Métrica | Estado Actual | Objetivo Fase 3 |
|---------|---------------|-----------------|
| Frontend Pages | 12 | 16+ |
| CVE Frontend | Tipos/Hooks | Search + Detail pages |
| Workers Funcionales | 2 (Nmap, CVE) | 4 (+ Nuclei, ZAP) |
| Tests Backend | 400+ | 550+ |
| Tests Frontend E2E | ~50 | ~100 |
| Cobertura | ~85% | >90% |
| **Network Validation** | ❌ No | ✅ Solo red local |
| **Service→CVE Correlation** | ❌ No | ✅ Automático |
| CRUD Completo | Parcial | 100% |

---

## 🎯 ESTADO ACTUAL (POST FASE 2)

### ✅ Componentes Implementados

| Componente | Estado | Tests | Líneas | Notas |
|------------|--------|-------|--------|-------|
| FastAPI Backend | ✅ | 400+ | ~15K | 80+ endpoints |
| PostgreSQL + TimescaleDB | ✅ | - | - | Multi-tenant |
| Redis + Celery | ✅ | - | - | Async tasks |
| Auth JWT | ✅ | 16 | ~1.5K | Access + Refresh tokens |
| **Nmap Worker** | ✅ | - | 1312 | Discovery + Port scan |
| **CVE Worker** | ✅ | - | ~800 | Sync NVD, lookup, EPSS |
| **CVE Frontend (Día 18)** | ✅ | - | ~1200 | Types, API, Hooks, Components |
| **Nuclei Worker** | ⚠️ | - | ~600 | Código listo, NO instalado |
| **ZAP Worker** | ❌ | - | ~150 | Solo placeholder |
| Frontend React | ✅ | ~50 E2E | ~10K | Dashboard, Assets, Scans, Vulns |
| **CVE Pages** | ❌ | - | - | Pendiente (Día 19) |
| **Network Validation** | ❌ | - | - | Sin restricción a red local |
| **Service→CVE Correlation** | ❌ | - | - | No implementado |

### 🔴 Gaps Críticos Identificados

#### 1. Network Scanning sin Validación ⚠️ CRÍTICO
- ❌ Actualmente acepta **CUALQUIER** IP/CIDR
- ❌ Puede escanear: `8.8.8.8`, `1.1.1.1`, IPs públicas
- ❌ **RIESGO DE SEGURIDAD**: Escaneo fuera de red local

**Solución (Día 20):**
- Validador que solo permite: `192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`
- Validación backend + frontend
- Tests de seguridad

#### 2. CVE Pages Faltantes
- ❌ `/cve` - Búsqueda de CVEs no existe
- ❌ `/cve/[id]` - Detalle de CVE no existe
- ❌ No hay navegación en sidebar

**Solución (Día 19):**
- Página completa de búsqueda con filtros
- Página de detalle con tabs (Info, References, Affected Products)
- Agregar link en sidebar

#### 3. Correlación Automática ⚠️ CRÍTICO
- ❌ Servicios detectados **NO se buscan en NVD**
- ❌ No hay vinculación automática Service→CVE
- ❌ Proceso manual e ineficiente

**Ejemplo del problema:**
```
Nmap detecta: Apache/2.4.49 en puerto 80
❌ NO busca automáticamente CVE-2021-41773 (Path Traversal crítico)
❌ Usuario debe buscar manualmente
```

**Solución (Día 21):**
```python
# Flujo automático:
1. Nmap detecta: Apache/2.4.49
2. Construir CPE: cpe:/a:apache:http_server:2.4.49
3. Buscar en NVD por CPE
4. Encontrar: CVE-2021-41773, CVE-2021-42013
5. Crear Vulnerability automáticamente
6. Mostrar en UI
```

#### 4. CRUD Incompleto
- ❌ Assets sin bulk operations (delete, export)
- ❌ Assets sin filtros avanzados (por tags, risk score, etc.)
- ❌ Scans sin edición/reprogramación
- ❌ Scans sin clonación
- ❌ Sin schedule de scans recurrentes

#### 5. Testing Gaps
- ❌ Sin tests para network validation
- ❌ Sin tests de correlación Service→CVE
- ❌ Coverage < 90%
- ❌ Sin load testing

---

## 🏗️ ARQUITECTURA FASE 3

### Diagrama Completo del Sistema

```
┌────────────────────────────────────────────────────────────────────────┐
│                        NESTSECURE - FASE 3 COMPLETA                     │
├────────────────────────────────────────────────────────────────────────┤
│  FRONTEND (Next.js 16 + TypeScript + TanStack Query v5)                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Pages:                                                            │  │
│  │ • /dashboard     - Main dashboard con stats                       │  │
│  │ • /assets        - CRUD completo + filtros + bulk ops + export    │  │
│  │ • /scans         - CRUD + schedule + clone + history              │  │
│  │ • /vulnerabilities - Lista + detalle + remediation                │  │
│  │ • /cve (NEW)     - Búsqueda CVE con filtros avanzados             │  │
│  │ • /cve/[id] (NEW) - Detalle CVE con tabs y referencias            │  │
│  │ • /reports       - Generación y descarga de reportes              │  │
│  │ • /settings      - Configuración del sistema                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Components:                                                        │  │
│  │ • Network Validation - Valida IPs privadas antes de escanear      │  │
│  │ • CVE Search Form - Búsqueda avanzada con múltiples filtros       │  │
│  │ • Service CVE Badge - Muestra CVEs vinculados a servicios         │  │
│  │ • Correlation Button - Trigger manual de correlación              │  │
│  │ • Auto-Correlation Toggle - Activar/desactivar correlación auto   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│  BACKEND API (FastAPI + SQLAlchemy + Pydantic)                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ New Services:                                                      │  │
│  │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐  │  │
│  │ │ Network Validator│ │ Correlation Svc  │ │ CVE Enrichment   │  │  │
│  │ │ - Private IPs    │ │ - Service→CPE    │ │ - NVD Lookup     │  │  │
│  │ │ - CIDR Check     │ │ - CPE→CVE Search │ │ - EPSS Scores    │  │  │
│  │ │ - Whitelist      │ │ - Auto-linking   │ │ - KEV Check      │  │  │
│  │ │ - RFC 1918       │ │ - Bulk Correlate │ │ - Cache Results  │  │  │
│  │ └──────────────────┘ └──────────────────┘ └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ New Endpoints:                                                     │  │
│  │ • POST /api/v1/network/validate - Validar target de escaneo       │  │
│  │ • POST /api/v1/correlation/services/{id}/correlate - Correlate 1  │  │
│  │ • POST /api/v1/correlation/scans/{id}/correlate - Correlate all   │  │
│  │ • POST /api/v1/scans/{id}/schedule - Schedule scan con cron       │  │
│  │ • POST /api/v1/assets/bulk/delete - Bulk delete assets            │  │
│  │ • GET  /api/v1/assets/export/csv - Export assets CSV              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│  WORKERS (Celery + Redis)                                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Nmap Worker (✅ FUNCIONAL + MEJORAS)                              │  │
│  │ ├─ discovery_scan(target) → VALIDA red local → scan              │  │
│  │ ├─ port_scan(asset_id) → find_services() → CORRELATE_CVE()       │  │
│  │ └─ service_scan(asset_id) → enrich() → link_cves()               │  │
│  │                                                                    │  │
│  │ CVE Worker (✅ FUNCIONAL)                                          │  │
│  │ ├─ sync_cves(days_back=30) → NVD API → Cache local               │  │
│  │ ├─ lookup_cve(cve_id) → Cache first → NVD fallback               │  │
│  │ ├─ lookup_multiple(cve_ids[]) → Batch lookup                     │  │
│  │ └─ get_epss_scores(cve_ids[]) → FIRST.org API                    │  │
│  │                                                                    │  │
│  │ Correlation Worker (🆕 NEW)                                       │  │
│  │ ├─ correlate_service(service_id) → CPE → NVD → Vuln              │  │
│  │ ├─ correlate_scan(scan_id) → All services → Batch                │  │
│  │ └─ auto_correlate_on_scan_complete(scan_id) → Trigger auto       │  │
│  │                                                                    │  │
│  │ Nuclei Worker (⚠️ CÓDIGO LISTO, INSTALACIÓN PENDIENTE)           │  │
│  │ ├─ nuclei_scan(target, templates[]) → Execute → Parse            │  │
│  │ ├─ update_templates() → Download latest                          │  │
│  │ └─ parse_results() → Extract CVEs → Link to vulns                │  │
│  │                                                                    │  │
│  │ ZAP Worker (❌ PENDIENTE IMPLEMENTACIÓN)                          │  │
│  │ ├─ spider_scan(url) → Discover endpoints                         │  │
│  │ ├─ active_scan(url) → Test vulnerabilities                       │  │
│  │ ├─ passive_scan(url) → Analyze responses                         │  │
│  │ └─ parse_alerts() → Map to OWASP Top 10 → Link CVEs              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│  DATABASE (PostgreSQL 15 + TimescaleDB)                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Tables & Relationships:                                            │  │
│  │                                                                    │  │
│  │ Assets ─┬─ Services ─┬─ service_cve_correlation (NEW)             │  │
│  │         │            │         │                                   │  │
│  │         │            │         └──→ CVE Cache                      │  │
│  │         │            │                                             │  │
│  │         │            └──────────────→ Vulnerabilities               │  │
│  │         │                                  │                       │  │
│  │         │                                  ├─ cve_id (FK)          │  │
│  │         │                                  ├─ service_id (FK)      │  │
│  │         │                                  └─ auto_created (bool)  │  │
│  │         │                                                          │  │
│  │         └────────────────────────────→ Scans                       │  │
│  │                                            │                       │  │
│  │                                            ├─ auto_correlate_cves  │  │
│  │                                            └─ cron_schedule        │  │
│  │                                                                    │  │
│  │ CVE Cache ─┬─ affected_products (JSON)                            │  │
│  │            ├─ cvss_v3_score                                       │  │
│  │            ├─ epss_score (NEW)                                    │  │
│  │            ├─ in_cisa_kev                                         │  │
│  │            └─ last_fetched_at                                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│  EXTERNAL INTEGRATIONS                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ • NVD API - CVE data (rate limited: 5 req/30s without key)        │  │
│  │ • FIRST.org EPSS API - Exploit prediction scores                  │  │
│  │ • CISA KEV - Known Exploited Vulnerabilities catalog              │  │
│  │ • CVE.org MITRE - Additional CVE references                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### Flujo de Correlación Service→CVE (NUEVO)

```
┌────────────────────────────────────────────────────────────────────────┐
│ FLUJO: SCAN → SERVICE DETECTION → CVE CORRELATION                      │
└────────────────────────────────────────────────────────────────────────┘

1. SCAN INICIADO
   │
   ├─ User crea scan: POST /api/v1/scans
   │  Target: "192.168.1.0/24" (✅ Validado como red privada)
   │  auto_correlate_cves: true
   │
   └─> Celery Task: nmap.discovery_scan.delay()

2. DISCOVERY SCAN
   │
   ├─ Nmap: nmap -sn 192.168.1.0/24
   │
   ├─ Hosts found: 
   │  • 192.168.1.1 (Router)
   │  • 192.168.1.10 (Server)
   │  • 192.168.1.20 (Workstation)
   │
   └─> Create Assets en DB

3. PORT SCAN (Auto-trigger)
   │
   ├─ Nmap: nmap -sV -sC 192.168.1.10
   │
   ├─ Services detected:
   │  • Port 22: OpenSSH 7.4
   │  • Port 80: Apache httpd 2.4.49  ← VULNERABLE!
   │  • Port 443: OpenSSL 1.1.1
   │
   └─> Create Services en DB

4. AUTO CVE CORRELATION (Si auto_correlate_cves=true)
   │
   ├─ Para cada servicio detectado:
   │
   ├─ Service: Apache httpd 2.4.49
   │  │
   │  ├─ Step 1: Build CPE
   │  │  └─> cpe:/a:apache:http_server:2.4.49
   │  │
   │  ├─ Step 2: Search en Cache Local
   │  │  └─> No encontrado → Query NVD
   │  │
   │  ├─ Step 3: NVD API Request
   │  │  GET https://services.nvd.nist.gov/rest/json/cves/2.0
   │  │  ?cpeName=cpe:/a:apache:http_server:2.4.49
   │  │
   │  ├─ Step 4: CVEs Encontrados
   │  │  • CVE-2021-41773 (CVSS 7.5) - Path Traversal
   │  │  • CVE-2021-42013 (CVSS 9.8) - Path Traversal + RCE
   │  │
   │  ├─ Step 5: Save to CVE Cache
   │  │  INSERT INTO cve_cache ...
   │  │
   │  └─ Step 6: Create Vulnerabilities
   │     INSERT INTO vulnerabilities (
   │       name: "CVE-2021-41773 in Apache httpd",
   │       severity: CRITICAL,
   │       cve_id: "CVE-2021-41773",
   │       service_id: {service.id},
   │       asset_id: {asset.id},
   │       auto_created: true
   │     )
   │
   └─> Correlación completa

5. RESULTADO FINAL
   │
   ├─ Asset: 192.168.1.10
   │  ├─ Services: 3 (SSH, HTTP, HTTPS)
   │  ├─ Vulnerabilities: 2 (Ambos CVEs de Apache)
   │  └─ Risk Score: 9.8 (CRÍTICO)
   │
   └─> UI actualizada en tiempo real (websocket)
```

---

## ✅ DÍA 18: CVE INFRASTRUCTURE (COMPLETADO)

### Estado: ✅ COMPLETADO

**Fecha:** 2026-02-05  
**Tiempo:** ~6 horas  
**Archivos Creados:** 7  
**Líneas de Código:** ~1,200

### Implementado

#### 1. Tipos TypeScript (12 tipos)
- ✅ `CVE` - Tipo completo de CVE
- ✅ `CVEMinimal` - Vista resumida para listas
- ✅ `CVESearchParams` - Parámetros de búsqueda
- ✅ `CVEStats` - Estadísticas globales
- ✅ `CVESeverity` - Enum de severidades
- ✅ `CVEReference` - Referencias externas
- ✅ `AffectedProduct` - Productos afectados
- ✅ `CVESyncRequest` - Request de sincronización
- ✅ `CVESyncStatus` - Estado de sincronización
- ✅ `CVELookupRequest` - Request de lookup
- ✅ `CVELookupResponse` - Response de lookup
- ✅ `PaginatedResponse<CVE>` - Respuesta paginada

**Archivo:** [types/index.ts](../../frontend/types/index.ts)

#### 2. API Client (10 métodos)
- ✅ `searchCVEs(params)` - Búsqueda con filtros
- ✅ `getCVE(cveId)` - Obtener CVE individual
- ✅ `lookupCVEs(cveIds[])` - Lookup múltiple
- ✅ `getCVEStats()` - Estadísticas globales
- ✅ `syncCVEs(request)` - Sincronizar con NVD
- ✅ `getCVESyncStatus()` - Estado de sincronización
- ✅ `getVulnerabilityCVE(vulnId)` - CVE de vulnerabilidad
- ✅ `getTrendingCVEs()` - CVEs trending
- ✅ `getKEVCVEs()` - CISA KEV catalog
- ✅ `getExploitableCVEs()` - CVEs con exploit disponible

**Archivo:** [lib/api.ts](../../frontend/lib/api.ts)

#### 3. React Query Hooks (12 hooks)
- ✅ `useCVESearch(params)` - Hook de búsqueda
- ✅ `useCVESearchInfinite(params)` - Infinite scroll
- ✅ `useCVE(cveId)` - Hook individual
- ✅ `useCVEStats()` - Hook de stats
- ✅ `useCVESyncStatus()` - Estado sync
- ✅ `useSyncCVEs()` - Mutation sync
- ✅ `useCVELookup()` - Mutation lookup
- ✅ `useTrendingCVEs()` - Trending
- ✅ `useKEVCVEs()` - KEV catalog
- ✅ `useExploitableCVEs()` - Exploitable
- ✅ `usePrefetchCVE(cveId)` - Prefetch
- ✅ `useInvalidateCVEs()` - Invalidate cache

**Archivo:** [hooks/use-cve.ts](../../frontend/hooks/use-cve.ts)

#### 4. Componentes UI (5 componentes)
- ✅ `CVSSBadge` - Badge de score CVSS
- ✅ `SeverityBadge` - Badge de severidad
- ✅ `CVSSScore` - Score detallado
- ✅ `CVECard` - Tarjeta completa
- ✅ `CVECardMinimal` - Tarjeta resumida
- ✅ `CVELink` - Link a CVE detail
- ✅ `CVEStatsCard` - Tarjeta de estadísticas
- ✅ `CVESearchForm` - Formulario de búsqueda avanzada
- ✅ `CVEDetails` - Vista completa con tabs

**Archivos:**
- [components/cve/cvss-badge.tsx](../../frontend/components/cve/cvss-badge.tsx)
- [components/cve/cve-card.tsx](../../frontend/components/cve/cve-card.tsx)
- [components/cve/cve-search-form.tsx](../../frontend/components/cve/cve-search-form.tsx)
- [components/cve/cve-details.tsx](../../frontend/components/cve/cve-details.tsx)
- [components/cve/index.ts](../../frontend/components/cve/index.ts)

### Validación

```bash
# TypeScript validation
✅ npx tsc --noEmit → 0 errors

# Dependencies check
✅ Slider component exists
✅ All shadcn/ui components available
✅ TanStack Query v5 configured
```

### Documentación

Ver: [DIA_18_COMPLETADO.md](./DIA_18_COMPLETADO.md)

---

## 📅 DÍA 19: CVE FRONTEND PAGES

### Objetivo
Crear páginas completas de búsqueda y detalle de CVEs en el frontend, integrando todos los componentes del Día 18.

### Estado: ⏳ PENDIENTE

### Implementación Detallada

#### 1. Página de Búsqueda CVE

**Archivo:** `frontend/app/(dashboard)/cve/page.tsx`

**Características:**
- Formulario de búsqueda avanzada con múltiples filtros
- Tarjetas de estadísticas globales (Total, con Exploits, KEV, Last Sync)
- Lista de resultados paginada
- Infinite scroll opcional
- Loading states y error handling
- Empty states

**Código Completo:**

```typescript
// frontend/app/(dashboard)/cve/page.tsx
'use client';

import { useState } from 'react';
import { useCVESearch, useCVEStats } from '@/hooks/use-cve';
import {
  CVESearchForm,
  CVECardMinimal,
  CVEStatsCard,
} from '@/components/cve';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Database, Shield, Bug, AlertTriangle } from 'lucide-react';
import type { CVESearchParams } from '@/types';

export default function CVESearchPage() {
  const [searchParams, setSearchParams] = useState<CVESearchParams>({
    page: 1,
    page_size: 20,
  });

  const { cves, total, page, pages, isLoading, error } = useCVESearch(searchParams);
  const { stats, isLoading: statsLoading } = useCVEStats();

  const handleSearch = (params: CVESearchParams) => {
    setSearchParams({ ...params, page: 1, page_size: 20 });
  };

  const handlePageChange = (newPage: number) => {
    setSearchParams(prev => ({ ...prev, page: newPage }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">CVE Database</h1>
        <p className="text-muted-foreground mt-2">
          Search and explore Common Vulnerabilities and Exposures (CVEs) from the National Vulnerability Database
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsLoading ? (
          <>
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </>
        ) : stats ? (
          <>
            <CVEStatsCard
              title="Total CVEs"
              value={stats.total_cves.toLocaleString()}
              icon={<Database className="h-4 w-4 text-muted-foreground" />}
              description={stats.avg_cvss ? `Avg CVSS: ${stats.avg_cvss.toFixed(1)}` : 'No data'}
            />
            <CVEStatsCard
              title="With Exploits"
              value={stats.with_exploits.toLocaleString()}
              icon={<Bug className="h-4 w-4 text-red-500" />}
              description={`${((stats.with_exploits / stats.total_cves) * 100).toFixed(1)}% of total`}
              variant="destructive"
            />
            <CVEStatsCard
              title="In CISA KEV"
              value={stats.in_kev.toLocaleString()}
              icon={<AlertTriangle className="h-4 w-4 text-orange-500" />}
              description="Known Exploited Vulnerabilities"
              variant="warning"
            />
            <CVEStatsCard
              title="Last Sync"
              value={stats.last_sync ? new Date(stats.last_sync).toLocaleDateString() : 'Never'}
              icon={<Shield className="h-4 w-4 text-green-500" />}
              description={`Status: ${stats.sync_status || 'Unknown'}`}
            />
          </>
        ) : null}
      </div>

      {/* Search Form */}
      <Card className="p-6">
        <CVESearchForm onSearch={handleSearch} isLoading={isLoading} />
      </Card>

      {/* Results */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            {total > 0 ? `Results (${total.toLocaleString()} found)` : 'Results'}
          </h2>
          {total > 0 && (
            <p className="text-sm text-muted-foreground">
              Page {page} of {pages}
            </p>
          )}
        </div>

        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>
              Error loading CVEs: {error.message}
            </AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="space-y-2">
            {[...Array(10)].map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : cves.length > 0 ? (
          <>
            <div className="space-y-2">
              {cves.map(cve => (
                <CVECardMinimal 
                  key={cve.cve_id} 
                  cve={cve}
                  data-test="cve-card"
                />
              ))}
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <p className="text-sm text-muted-foreground">
                  Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, total)} of {total}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <div className="flex items-center gap-1">
                    {/* Page numbers */}
                    {Array.from({ length: Math.min(5, pages) }, (_, i) => {
                      const pageNum = page - 2 + i;
                      if (pageNum < 1 || pageNum > pages) return null;
                      return (
                        <Button
                          key={pageNum}
                          variant={pageNum === page ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => handlePageChange(pageNum)}
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page === pages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          <Card className="p-12 text-center">
            <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No CVEs found</h3>
            <p className="text-muted-foreground">
              Try adjusting your search filters or search terms
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
```

#### 2. Página de Detalle CVE

**Archivo:** `frontend/app/(dashboard)/cve/[id]/page.tsx`

**Características:**
- Vista completa de CVE con tabs
- Información CVSS detallada
- Referencias externas
- Productos afectados
- Timeline de publicación
- Links a NVD, MITRE, CISA KEV

**Código Completo:**

```typescript
// frontend/app/(dashboard)/cve/[id]/page.tsx
'use client';

import { use } from 'react';
import { useCVE } from '@/hooks/use-cve';
import { CVEDetails } from '@/components/cve';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function CVEDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const cveId = decodeURIComponent(id);
  
  const { cve, isLoading, error } = useCVE(cveId);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" asChild>
          <Link href="/cve">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to CVE Search
          </Link>
        </Button>
        <Alert variant="destructive">
          <AlertDescription>
            Error loading CVE: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!cve) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" asChild>
          <Link href="/cve">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to CVE Search
          </Link>
        </Button>
        <Alert>
          <AlertDescription>
            CVE not found: {cveId}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" asChild>
        <Link href="/cve">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to CVE Search
        </Link>
      </Button>

      <CVEDetails cve={cve} />
    </div>
  );
}
```

#### 3. Actualizar Sidebar Navigation

**Archivo:** `frontend/components/layout/sidebar.tsx` (o similar)

```typescript
import { Database } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Assets', href: '/assets', icon: ServerIcon },
  { name: 'Scans', href: '/scans', icon: ScanIcon },
  { name: 'Vulnerabilities', href: '/vulnerabilities', icon: BugIcon },
  { 
    name: 'CVE Database', 
    href: '/cve', 
    icon: Database,
    badge: 'New',
  }, // 🆕 NEW
  { name: 'Reports', href: '/reports', icon: FileTextIcon },
  { name: 'Settings', href: '/settings', icon: SettingsIcon },
];
```

### Tests E2E

**Archivo:** `frontend/tests/e2e/cve.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('CVE Search Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/cve');
  });

  test('should display CVE search page with header and stats', async ({ page }) => {
    // Header
    await expect(page.locator('h1')).toContainText('CVE Database');
    
    // Stats cards
    await expect(page.locator('text=Total CVEs')).toBeVisible();
    await expect(page.locator('text=With Exploits')).toBeVisible();
    await expect(page.locator('text=In CISA KEV')).toBeVisible();
    await expect(page.locator('text=Last Sync')).toBeVisible();
    
    // Search form
    await expect(page.locator('[placeholder*="Search"]')).toBeVisible();
  });

  test('should search CVEs by keyword', async ({ page }) => {
    const searchInput = page.locator('[placeholder*="Search CVE"]');
    await searchInput.fill('apache');
    
    await page.locator('button:has-text("Search")').click();
    
    await page.waitForTimeout(1000);
    
    // Should show results or empty state
    const hasResults = await page.locator('[data-test="cve-card"]').count() > 0;
    const hasEmpty = await page.locator('text=No CVEs found').isVisible();
    
    expect(hasResults || hasEmpty).toBeTruthy();
  });

  test('should filter by severity', async ({ page }) => {
    // Open filters
    await page.locator('button:has-text("Filters")').click();
    
    // Select CRITICAL severity
    await page.locator('[data-test="severity-select"]').click();
    await page.locator('[data-test="severity-critical"]').click();
    
    // Apply filters
    await page.locator('button:has-text("Apply")').click();
    
    await page.waitForTimeout(1000);
  });

  test('should filter by CVSS score range', async ({ page }) => {
    await page.locator('button:has-text("Filters")').click();
    
    // Set min CVSS
    const minSlider = page.locator('[data-test="cvss-min-slider"]');
    await minSlider.fill('7.0');
    
    // Set max CVSS
    const maxSlider = page.locator('[data-test="cvss-max-slider"]');
    await maxSlider.fill('10.0');
    
    await page.locator('button:has-text("Apply")').click();
    
    await page.waitForTimeout(1000);
  });

  test('should filter exploitable CVEs only', async ({ page }) => {
    await page.locator('button:has-text("Filters")').click();
    
    await page.locator('[data-test="has-exploit-checkbox"]').check();
    
    await page.locator('button:has-text("Apply")').click();
    
    await page.waitForTimeout(1000);
  });

  test('should navigate to CVE detail page', async ({ page }) => {
    // Wait for results to load
    await page.waitForSelector('[data-test="cve-card"]', { timeout: 5000 });
    
    const firstCVE = page.locator('[data-test="cve-card"]').first();
    if (await firstCVE.count() > 0) {
      await firstCVE.click();
      
      // Should navigate to detail page
      await expect(page).toHaveURL(/\/cve\/CVE-\d{4}-\d+/);
      await expect(page.locator('h1')).toContainText('CVE-');
    }
  });

  test('should paginate results', async ({ page }) => {
    // Search for common term to get many results
    const searchInput = page.locator('[placeholder*="Search CVE"]');
    await searchInput.fill('remote');
    await page.locator('button:has-text("Search")').click();
    
    await page.waitForTimeout(1000);
    
    // Check if pagination exists
    const nextButton = page.locator('button:has-text("Next")');
    if (await nextButton.isEnabled()) {
      await nextButton.click();
      await page.waitForTimeout(500);
      
      // Should be on page 2
      await expect(page.locator('text=Page 2')).toBeVisible();
    }
  });
});

test.describe('CVE Detail Page', () => {
  test('should display CVE details for known CVE', async ({ page }) => {
    // Navigate to Log4Shell (famous CVE)
    await page.goto('/cve/CVE-2021-44228');
    
    // Header with CVE ID
    await expect(page.locator('h1')).toContainText('CVE-2021-44228');
    
    // Tabs
    await expect(page.locator('[role="tablist"]')).toBeVisible();
    await expect(page.locator('button[role="tab"]:has-text("Overview")')).toBeVisible();
    await expect(page.locator('button[role="tab"]:has-text("References")')).toBeVisible();
    await expect(page.locator('button[role="tab"]:has-text("Affected Products")')).toBeVisible();
  });

  test('should show CVSS score and severity', async ({ page }) => {
    await page.goto('/cve/CVE-2021-44228');
    
    // CVSS score should be visible
    await expect(page.locator('text=/CVSS.*10.0|9.8|9.0/')).toBeVisible();
    
    // Severity badge
    await expect(page.locator('text=CRITICAL')).toBeVisible();
  });

  test('should display external links', async ({ page }) => {
    await page.goto('/cve/CVE-2021-44228');
    
    // External links
    await expect(page.locator('a:has-text("NVD")')).toBeVisible();
    await expect(page.locator('a:has-text("MITRE")')).toBeVisible();
    
    // Links should have correct hrefs
    const nvdLink = page.locator('a:has-text("NVD")');
    await expect(nvdLink).toHaveAttribute('href', /nvd.nist.gov/);
  });

  test('should switch between tabs', async ({ page }) => {
    await page.goto('/cve/CVE-2021-44228');
    
    // Click References tab
    await page.locator('button[role="tab"]:has-text("References")').click();
    await expect(page.locator('[role="tabpanel"]')).toContainText(/Reference|URL|Source/i);
    
    // Click Affected Products tab
    await page.locator('button[role="tab"]:has-text("Affected Products")').click();
    await expect(page.locator('[role="tabpanel"]')).toContainText(/Product|Vendor|Version/i);
  });

  test('should handle non-existent CVE gracefully', async ({ page }) => {
    await page.goto('/cve/CVE-9999-99999');
    
    await expect(page.locator('text=CVE not found')).toBeVisible();
    await expect(page.locator('a:has-text("Back to CVE Search")')).toBeVisible();
  });

  test('should show back button to CVE search', async ({ page }) => {
    await page.goto('/cve/CVE-2021-44228');
    
    const backButton = page.locator('a:has-text("Back to CVE Search")');
    await expect(backButton).toBeVisible();
    
    await backButton.click();
    await expect(page).toHaveURL('/cve');
  });
});
```

### Checklist Día 19

- [ ] Crear `app/(dashboard)/cve/page.tsx`
- [ ] Crear `app/(dashboard)/cve/[id]/page.tsx`
- [ ] Actualizar sidebar navigation
- [ ] Agregar tests E2E (`tests/e2e/cve.spec.ts`)
- [ ] Ejecutar tests: `pnpm test:e2e cve`
- [ ] Validar TypeScript: `pnpm type-check`
- [ ] Validar UI en desarrollo
- [ ] Documentar en `DIA_19_COMPLETADO.md`

---

## 📅 DÍA 20: NETWORK SCANNING & VALIDATION

### Objetivo
Implementar validación de red para restringir escaneos **SOLO A REDES LOCALES PRIVADAS** (RFC 1918).

### Estado: ⏳ PENDIENTE

### Problema Actual ⚠️ CRÍTICO

```python
# backend/app/workers/nmap_worker.py (LÍNEA ~100)
@celery_app.task
def discovery_scan(target: str, organization_id: str):
    # ❌ PROBLEMA: Acepta CUALQUIER IP/CIDR
    # ❌ Puede escanear: 8.8.8.8, 1.1.1.1, IPs públicas
    # ❌ RIESGO: Escaneo fuera de la red local
    nmap_output = run_nmap(["-sn", target])
```

**Ejemplos de targets peligrosos que actualmente se permiten:**
- ❌ `8.8.8.8` (Google DNS)
- ❌ `1.1.1.1` (Cloudflare DNS)
- ❌ `151.101.0.0/16` (Fastly CDN)
- ❌ Cualquier IP pública

### Solución: Network Validator

#### 1. Crear Utilidad de Validación

**Archivo:** `backend/app/utils/network_utils.py`

```python
# backend/app/utils/network_utils.py
"""
Network validation utilities.

Validates scan targets to ensure they are within private networks only (RFC 1918).
"""
import ipaddress
import re
from typing import List, Tuple, Optional

from fastapi import HTTPException, status


# Rangos de IPs privadas según RFC 1918
# https://datatracker.ietf.org/doc/html/rfc1918
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),        # Clase A: 10.0.0.0 - 10.255.255.255
    ipaddress.ip_network('172.16.0.0/12'),     # Clase B: 172.16.0.0 - 172.31.255.255
    ipaddress.ip_network('192.168.0.0/16'),    # Clase C: 192.168.0.0 - 192.168.255.255
    ipaddress.ip_network('127.0.0.0/8'),       # Localhost: 127.0.0.1 - 127.255.255.255
    ipaddress.ip_network('169.254.0.0/16'),    # Link-local: 169.254.0.0 - 169.254.255.255
]


def is_private_ip(ip: str) -> bool:
    """
    Verifica si una dirección IP es privada según RFC 1918.
    
    Args:
        ip: Dirección IP en formato string (ej: '192.168.1.1')
    
    Returns:
        True si es IP privada, False si es pública
    
    Examples:
        >>> is_private_ip('192.168.1.1')
        True
        >>> is_private_ip('8.8.8.8')
        False
        >>> is_private_ip('10.0.0.1')
        True
        >>> is_private_ip('172.16.0.1')
        True
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        # IP inválida
        return False


def is_private_network(cidr: str) -> bool:
    """
    Verifica si una red CIDR es completamente privada.
    
    Args:
        cidr: Red en formato CIDR (ej: '192.168.1.0/24')
    
    Returns:
        True si TODA la red es privada
    
    Examples:
        >>> is_private_network('192.168.1.0/24')
        True
        >>> is_private_network('10.0.0.0/8')
        True
        >>> is_private_network('8.8.8.0/24')
        False
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        # Verificar que toda la red esté dentro de rangos privados
        return any(network.subnet_of(private_range) 
                  for private_range in PRIVATE_IP_RANGES)
    except ValueError:
        # CIDR inválido
        return False


def validate_scan_target(target: str) -> Tuple[str, str]:
    """
    Valida y normaliza un target de escaneo.
    
    Solo permite:
    - IPs privadas individuales (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    - Redes privadas en CIDR (192.168.1.0/24, 10.0.0.0/8, etc.)
    
    NO permite:
    - IPs públicas
    - Redes públicas
    - Hostnames (por seguridad, podría resolver a IP pública)
    
    Args:
        target: IP, CIDR o hostname
    
    Returns:
        Tuple de (target_normalizado, tipo)
        tipo: 'ip' | 'cidr'
    
    Raises:
        HTTPException 400: Si el target no es válido o es público
    
    Examples:
        >>> validate_scan_target('192.168.1.1')
        ('192.168.1.1', 'ip')
        >>> validate_scan_target('192.168.1.0/24')
        ('192.168.1.0/24', 'cidr')
        >>> validate_scan_target('8.8.8.8')
        HTTPException: Public IP addresses are not allowed
    """
    target = target.strip()
    
    # Caso 1: CIDR notation (192.168.1.0/24)
    if '/' in target:
        if not is_private_network(target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Public networks are not allowed for scanning. "
                    f"Target '{target}' is outside private networks. "
                    f"Only private networks (10.x, 172.16-31.x, 192.168.x) are permitted."
                )
            )
        return (target, 'cidr')
    
    # Caso 2: Single IP
    try:
        ip_obj = ipaddress.ip_address(target)
        if not is_private_ip(target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Public IP address '{target}' is not allowed for scanning. "
                    f"Only private IPs (10.x, 172.16-31.x, 192.168.x) are permitted."
                )
            )
        return (target, 'ip')
    except ValueError:
        pass
    
    # Caso 3: Hostname (no permitido por seguridad)
    # Ejemplo: google.com podría resolver a IP pública
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Hostnames are not supported for security reasons. "
            f"Please use IP addresses or CIDR notation only."
        )
    )


def validate_multiple_targets(targets: List[str]) -> List[str]:
    """
    Valida múltiples targets.
    
    Args:
        targets: Lista de IPs o CIDRs
    
    Returns:
        Lista de targets validados y normalizados
    
    Raises:
        HTTPException: Si algún target no es válido
    """
    validated = []
    for i, target in enumerate(targets):
        try:
            normalized, _ = validate_scan_target(target)
            validated.append(normalized)
        except HTTPException as e:
            # Re-raise con contexto adicional
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Target #{i+1} invalid: {e.detail}"
            )
    return validated


def get_network_info(cidr: str) -> dict:
    """
    Obtiene información detallada sobre una red CIDR.
    
    Args:
        cidr: Red en formato CIDR
    
    Returns:
        Dict con información de la red:
        - network: Dirección de red
        - netmask: Máscara de red
        - broadcast: Dirección de broadcast
        - num_hosts: Número de hosts disponibles
        - first_host: Primera IP de host
        - last_host: Última IP de host
        - prefix_length: Longitud del prefijo CIDR
    
    Examples:
        >>> get_network_info('192.168.1.0/24')
        {
            'network': '192.168.1.0',
            'netmask': '255.255.255.0',
            'broadcast': '192.168.1.255',
            'num_hosts': 254,
            'first_host': '192.168.1.1',
            'last_host': '192.168.1.254',
            'prefix_length': 24
        }
    """
    network = ipaddress.ip_network(cidr, strict=False)
    
    # Calcular hosts usables (excluir network y broadcast)
    num_hosts = network.num_addresses - 2 if network.num_addresses > 2 else 0
    
    return {
        'network': str(network.network_address),
        'netmask': str(network.netmask),
        'broadcast': str(network.broadcast_address),
        'num_hosts': num_hosts,
        'first_host': str(network.network_address + 1) if num_hosts > 0 else None,
        'last_host': str(network.broadcast_address - 1) if num_hosts > 0 else None,
        'prefix_length': network.prefixlen,
        'is_private': is_private_network(cidr),
    }


# ============================================================================
# Whitelist opcional (para casos excepcionales)
# ============================================================================

def is_whitelisted(target: str, whitelist: Optional[List[str]] = None) -> bool:
    """
    Verifica si un target está en whitelist (opcional).
    
    Permite excepciones controladas para casos específicos.
    
    Args:
        target: IP o CIDR a verificar
        whitelist: Lista de targets permitidos
    
    Returns:
        True si está en whitelist
    """
    if not whitelist:
        return False
    
    return target in whitelist
```

#### 2. Tests Unitarios para Network Validator

**Archivo:** `backend/app/tests/test_utils/test_network_utils.py`

```python
# backend/app/tests/test_utils/test_network_utils.py
import pytest
from fastapi import HTTPException

from app.utils.network_utils import (
    is_private_ip,
    is_private_network,
    validate_scan_target,
    validate_multiple_targets,
    get_network_info,
)


class TestIsPrivateIP:
    """Tests para verificación de IPs privadas."""
    
    def test_class_a_private_ips(self):
        """IPs Clase A privadas (10.x.x.x)."""
        assert is_private_ip('10.0.0.1')
        assert is_private_ip('10.255.255.254')
        assert is_private_ip('10.1.2.3')
    
    def test_class_b_private_ips(self):
        """IPs Clase B privadas (172.16-31.x.x)."""
        assert is_private_ip('172.16.0.1')
        assert is_private_ip('172.31.255.254')
        assert is_private_ip('172.20.1.1')
    
    def test_class_c_private_ips(self):
        """IPs Clase C privadas (192.168.x.x)."""
        assert is_private_ip('192.168.1.1')
        assert is_private_ip('192.168.255.254')
        assert is_private_ip('192.168.0.1')
    
    def test_localhost(self):
        """Localhost IPs (127.x.x.x)."""
        assert is_private_ip('127.0.0.1')
        assert is_private_ip('127.255.255.254')
    
    def test_link_local(self):
        """Link-local IPs (169.254.x.x)."""
        assert is_private_ip('169.254.1.1')
        assert is_private_ip('169.254.255.254')
    
    def test_public_ips(self):
        """IPs públicas deberían retornar False."""
        assert not is_private_ip('8.8.8.8')          # Google DNS
        assert not is_private_ip('1.1.1.1')          # Cloudflare DNS
        assert not is_private_ip('208.67.222.222')   # OpenDNS
        assert not is_private_ip('151.101.1.140')    # Fastly
        assert not is_private_ip('93.184.216.34')    # example.com
    
    def test_invalid_ips(self):
        """IPs inválidas deberían retornar False."""
        assert not is_private_ip('invalid')
        assert not is_private_ip('999.999.999.999')
        assert not is_private_ip('192.168.1')
        assert not is_private_ip('192.168.1.1.1')


class TestIsPrivateNetwork:
    """Tests para verificación de redes privadas."""
    
    def test_class_a_networks(self):
        """Redes Clase A privadas."""
        assert is_private_network('10.0.0.0/8')
        assert is_private_network('10.1.0.0/16')
        assert is_private_network('10.1.1.0/24')
    
    def test_class_b_networks(self):
        """Redes Clase B privadas."""
        assert is_private_network('172.16.0.0/12')
        assert is_private_network('172.20.0.0/16')
        assert is_private_network('172.31.0.0/24')
    
    def test_class_c_networks(self):
        """Redes Clase C privadas."""
        assert is_private_network('192.168.0.0/16')
        assert is_private_network('192.168.1.0/24')
        assert is_private_network('192.168.100.0/24')
    
    def test_public_networks(self):
        """Redes públicas deberían retornar False."""
        assert not is_private_network('8.8.8.0/24')
        assert not is_private_network('1.1.1.0/24')
        assert not is_private_network('151.101.0.0/16')
    
    def test_invalid_cidrs(self):
        """CIDRs inválidos deberían retornar False."""
        assert not is_private_network('invalid')
        assert not is_private_network('192.168.1.1/99')
        assert not is_private_network('192.168.1.0')  # Sin /xx


class TestValidateScanTarget:
    """Tests para validación de targets de escaneo."""
    
    def test_valid_private_ip_class_a(self):
        """IPs Clase A válidas."""
        target, tipo = validate_scan_target('10.0.0.1')
        assert target == '10.0.0.1'
        assert tipo == 'ip'
    
    def test_valid_private_ip_class_b(self):
        """IPs Clase B válidas."""
        target, tipo = validate_scan_target('172.16.0.1')
        assert target == '172.16.0.1'
        assert tipo == 'ip'
    
    def test_valid_private_ip_class_c(self):
        """IPs Clase C válidas."""
        target, tipo = validate_scan_target('192.168.1.1')
        assert target == '192.168.1.1'
        assert tipo == 'ip'
    
    def test_valid_private_cidr(self):
        """Redes privadas válidas en CIDR."""
        target, tipo = validate_scan_target('192.168.1.0/24')
        assert target == '192.168.1.0/24'
        assert tipo == 'cidr'
        
        target, tipo = validate_scan_target('10.0.0.0/8')
        assert target == '10.0.0.0/8'
        assert tipo == 'cidr'
    
    def test_public_ip_rejected(self):
        """IPs públicas deberían ser rechazadas con error 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('8.8.8.8')
        
        assert exc_info.value.status_code == 400
        assert 'Public IP address' in exc_info.value.detail
        assert '8.8.8.8' in exc_info.value.detail
    
    def test_public_network_rejected(self):
        """Redes públicas deberían ser rechazadas."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('8.8.8.0/24')
        
        assert exc_info.value.status_code == 400
        assert 'Public networks' in exc_info.value.detail
    
    def test_hostname_rejected(self):
        """Hostnames deberían ser rechazados."""
        with pytest.raises(HTTPException) as exc_info:
            validate_scan_target('google.com')
        
        assert exc_info.value.status_code == 400
        assert 'Hostnames are not supported' in exc_info.value.detail
        
        with pytest.raises(HTTPException):
            validate_scan_target('example.com')
    
    def test_invalid_format_rejected(self):
        """Formatos inválidos deberían ser rechazados."""
        with pytest.raises(HTTPException):
            validate_scan_target('invalid-ip')
        
        with pytest.raises(HTTPException):
            validate_scan_target('999.999.999.999')
    
    def test_strips_whitespace(self):
        """Debería eliminar espacios en blanco."""
        target, tipo = validate_scan_target('  192.168.1.1  ')
        assert target == '192.168.1.1'
        assert tipo == 'ip'


class TestValidateMultipleTargets:
    """Tests para validación de múltiples targets."""
    
    def test_all_valid_targets(self):
        """Múltiples targets válidos deberían pasar."""
        targets = ['192.168.1.1', '10.0.0.0/8', '172.16.0.1']
        validated = validate_multiple_targets(targets)
        
        assert len(validated) == 3
        assert validated == ['192.168.1.1', '10.0.0.0/8', '172.16.0.1']
    
    def test_mixed_valid_invalid_first_invalid(self):
        """Si el primero falla, debería lanzar error."""
        targets = ['8.8.8.8', '192.168.1.1']
        
        with pytest.raises(HTTPException) as exc_info:
            validate_multiple_targets(targets)
        
        assert 'Target #1' in exc_info.value.detail
    
    def test_mixed_valid_invalid_second_invalid(self):
        """Si el segundo falla, debería indicar cuál."""
        targets = ['192.168.1.1', '8.8.8.8']
        
        with pytest.raises(HTTPException) as exc_info:
            validate_multiple_targets(targets)
        
        assert 'Target #2' in exc_info.value.detail
    
    def test_empty_list(self):
        """Lista vacía debería retornar lista vacía."""
        validated = validate_multiple_targets([])
        assert validated == []


class TestGetNetworkInfo:
    """Tests para obtener información de red."""
    
    def test_slash_24_network(self):
        """Red /24 (254 hosts)."""
        info = get_network_info('192.168.1.0/24')
        
        assert info['network'] == '192.168.1.0'
        assert info['netmask'] == '255.255.255.0'
        assert info['broadcast'] == '192.168.1.255'
        assert info['num_hosts'] == 254
        assert info['first_host'] == '192.168.1.1'
        assert info['last_host'] == '192.168.1.254'
        assert info['prefix_length'] == 24
        assert info['is_private'] is True
    
    def test_slash_16_network(self):
        """Red /16 (65,534 hosts)."""
        info = get_network_info('192.168.0.0/16')
        
        assert info['network'] == '192.168.0.0'
        assert info['num_hosts'] == 65534
        assert info['prefix_length'] == 16
    
    def test_slash_8_network(self):
        """Red /8 (~16 millones de hosts)."""
        info = get_network_info('10.0.0.0/8')
        
        assert info['network'] == '10.0.0.0'
        assert info['prefix_length'] == 8
        assert info['num_hosts'] == 16777214
    
    def test_slash_30_network(self):
        """Red /30 (2 hosts - típico punto a punto)."""
        info = get_network_info('192.168.1.0/30')
        
        assert info['num_hosts'] == 2
        assert info['first_host'] == '192.168.1.1'
        assert info['last_host'] == '192.168.1.2'
    
    def test_slash_31_network(self):
        """Red /31 (sin broadcast - RFC 3021)."""
        info = get_network_info('192.168.1.0/31')
        
        assert info['num_hosts'] == 0  # Sin hosts usables en implementación estándar


class TestSecurityScenarios:
    """Tests de escenarios de seguridad."""
    
    def test_blocks_scanning_google_dns(self):
        """Debería bloquear escaneo a Google DNS (8.8.8.8)."""
        with pytest.raises(HTTPException):
            validate_scan_target('8.8.8.8')
    
    def test_blocks_scanning_cloudflare_dns(self):
        """Debería bloquear escaneo a Cloudflare DNS (1.1.1.1)."""
        with pytest.raises(HTTPException):
            validate_scan_target('1.1.1.1')
    
    def test_blocks_scanning_external_networks(self):
        """Debería bloquear escaneo a redes externas."""
        with pytest.raises(HTTPException):
            validate_scan_target('151.101.0.0/16')  # Fastly CDN
    
    def test_allows_scanning_local_router(self):
        """Debería permitir escaneo a router local."""
        target, _ = validate_scan_target('192.168.1.1')
        assert target == '192.168.1.1'
    
    def test_allows_scanning_local_network(self):
        """Debería permitir escaneo a toda la red local."""
        target, _ = validate_scan_target('192.168.1.0/24')
        assert target == '192.168.1.0/24'
```

Ver continuación en el mensaje siguiente debido al límite de longitud...

