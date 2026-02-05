# FASE 3 - CONTINUACIÓN

## (Continuación del Día 20)

#### 3. Integrar Validación en Nmap Worker

**Archivo:** `backend/app/workers/nmap_worker.py`

```python
# backend/app/workers/nmap_worker.py
from app.utils.network_utils import validate_scan_target, is_private_ip

@celery_app.task(bind=True, name="nmap.discovery_scan")
def discovery_scan(
    self,
    target: str,
    organization_id: str,
    scan_id: str | None = None,
) -> dict:
    """
    Escaneo de descubrimiento de hosts (ping scan).
    
    VALIDACIÓN: Solo permite targets en redes privadas (RFC 1918).
    
    Args:
        target: IP o CIDR a escanear (DEBE ser red privada)
        organization_id: ID de la organización
        scan_id: ID del scan (opcional)
    
    Returns:
        Dict con resultados del escaneo
    
    Raises:
        ValueError: Si el target no es válido o es público
    """
    logger.info(f"🚀 Iniciando discovery scan: {target} para org {organization_id}")
    
    # ✅ VALIDAR TARGET (NUEVO)
    try:
        validated_target, target_type = validate_scan_target(target)
        logger.info(f"✅ Target validado: {validated_target} (tipo: {target_type})")
    except HTTPException as e:
        error_msg = f"❌ Target rechazado: {target} - {e.detail}"
        logger.error(error_msg)
        raise ValueError(e.detail)
    
    # Actualizar scan status
    if scan_id:
        _update_scan_status(scan_id, "running", {"stage": "discovery", "target": validated_target})
    
    try:
        # Ejecutar Nmap discovery scan
        logger.info(f"🔍 Ejecutando Nmap discovery scan en {validated_target}")
        nmap_output = run_nmap(["-sn", validated_target])
        
        # Parsear resultados
        hosts_found = parse_discovery_xml(nmap_output)
        logger.info(f"📡 Hosts encontrados: {len(hosts_found)}")
        
        # ... resto del código existente ...
        
    except Exception as e:
        logger.error(f"❌ Error en discovery scan: {e}")
        if scan_id:
            _update_scan_status(scan_id, "failed", {"error": str(e)})
        raise
```

#### 4. Integrar Validación en API de Scans

**Archivo:** `backend/app/api/v1/scans.py`

```python
# backend/app/api/v1/scans.py
from app.utils.network_utils import validate_multiple_targets

@router.post("", response_model=ScanRead, status_code=201)
async def create_scan(
    scan_data: ScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActiveUser = Depends(get_current_active_user),
):
    """
    Crea un nuevo scan.
    
    VALIDACIÓN: Solo permite targets en redes privadas.
    
    Args:
        scan_data: Datos del scan
            - name: Nombre del scan
            - targets: Lista de IPs/CIDRs (DEBEN ser privados)
            - scan_type: Tipo de escaneo
        
    Returns:
        Scan creado
        
    Raises:
        HTTPException 400: Si algún target es público o inválido
    """
    # ✅ VALIDAR TODOS LOS TARGETS (NUEVO)
    try:
        validated_targets = validate_multiple_targets(scan_data.targets)
        logger.info(f"✅ Targets validados: {validated_targets}")
    except HTTPException as e:
        # Re-lanzar con el mismo error
        logger.error(f"❌ Validación fallida: {e.detail}")
        raise e
    
    # Crear scan con targets validados
    scan = Scan(
        name=scan_data.name,
        scan_type=scan_data.scan_type,
        targets=validated_targets,  # <-- Usar targets validados
        status=ScanStatus.PENDING,
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    
    # Lanzar worker
    trigger_scan_worker(scan.id, scan.scan_type, validated_targets)
    
    return scan
```

#### 5. Frontend: Validación Client-Side

**Archivo:** `frontend/components/scans/create-scan-dialog.tsx`

```typescript
// frontend/components/scans/create-scan-dialog.tsx

const PRIVATE_NETWORK_PATTERNS = [
  /^10\.\d{1,3}\.\d{1,3}\.\d{1,3}(\/\d{1,2})?$/,           // 10.x.x.x
  /^192\.168\.\d{1,3}\.\d{1,3}(\/\d{1,2})?$/,             // 192.168.x.x
  /^172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}(\/\d{1,2})?$/, // 172.16-31.x.x
  /^127\.\d{1,3}\.\d{1,3}\.\d{1,3}(\/\d{1,2})?$/,         // 127.x.x.x
];

function validateTarget(target: string): string | null {
  const trimmed = target.trim();
  
  if (!trimmed) {
    return 'Target cannot be empty';
  }
  
  // Check if matches any private network pattern
  const isPrivate = PRIVATE_NETWORK_PATTERNS.some(pattern => 
    pattern.test(trimmed)
  );
  
  if (!isPrivate) {
    return 'Only private network IPs are allowed (10.x.x.x, 192.168.x.x, 172.16-31.x.x)';
  }
  
  return null;
}

// En el formulario:
<Input
  name="targets"
  onChange={(e) => {
    const value = e.target.value;
    const error = validateTarget(value);
    setTargetError(error);
  }}
/>
{targetError && (
  <Alert variant="destructive">
    <AlertDescription>{targetError}</AlertDescription>
  </Alert>
)}
```

---

## 📅 DÍA 21: SERVICE-TO-CVE CORRELATION

### Objetivo
Implementar correlación automática entre servicios detectados por Nmap y CVEs en NVD.

### Flujo Completo

```
1. Nmap escanea puerto 80
2. Detecta: Apache/2.4.49
3. Construir CPE: cpe:/a:apache:http_server:2.4.49
4. Buscar en NVD API por CPE
5. Encontrar CVE-2021-41773 (Path Traversal - CVSS 7.5)
6. Crear Vulnerability vinculada automáticamente
7. Mostrar en UI
```

### Implementación

#### 1. CPE Utilities

**Archivo:** `backend/app/utils/cpe_utils.py`

```python
# backend/app/utils/cpe_utils.py
"""
CPE (Common Platform Enumeration) utilities.

Construye CPEs desde información de servicios para búsqueda en NVD.
"""
import re
from typing import Optional, Tuple

from app.models.service import Service


# Mapeo de nombres de servicio a vendors conocidos
VENDOR_MAP = {
    'apache': 'apache',
    'nginx': 'nginx',
    'openssh': 'openssh',
    'mysql': 'mysql',
    'mariadb': 'mariadb',
    'postgresql': 'postgresql',
    'redis': 'redis',
    'mongodb': 'mongodb',
    'tomcat': 'apache',
    'iis': 'microsoft',
    'ssh': 'openssh',
    'ftp': 'vsftpd',
}

# Mapeo de productos
PRODUCT_MAP = {
    'apache': 'http_server',
    'nginx': 'nginx',
    'openssh': 'openssh',
    'mysql': 'mysql',
    'mariadb': 'mariadb',
    'postgresql': 'postgresql',
    'redis': 'redis',
    'mongodb': 'mongodb',
    'tomcat': 'tomcat',
    'iis': 'iis',
}


def normalize_version(version: str) -> str:
    """
    Normaliza versión para CPE.
    
    Ejemplos:
        "2.4.49" → "2.4.49"
        "v2.4.49" → "2.4.49"
        "2.4" → "2.4"
    """
    # Remover prefijo 'v'
    version = version.strip().lower().lstrip('v')
    
    # Mantener solo números y puntos
    version = re.sub(r'[^0-9.]', '', version)
    
    return version


def extract_vendor_product(service_name: str, service_product: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae vendor y product desde nombre de servicio.
    
    Args:
        service_name: Nombre del servicio (ej: "http", "ssh")
        service_product: Producto detectado (ej: "Apache httpd")
    
    Returns:
        Tuple (vendor, product)
    
    Examples:
        >>> extract_vendor_product("http", "Apache httpd")
        ('apache', 'http_server')
        >>> extract_vendor_product("ssh", "OpenSSH")
        ('openssh', 'openssh')
    """
    if not service_product:
        return (None, None)
    
    product_lower = service_product.lower()
    
    # Buscar matches en VENDOR_MAP
    for key, vendor in VENDOR_MAP.items():
        if key in product_lower:
            product = PRODUCT_MAP.get(key, key)
            return (vendor, product)
    
    return (None, None)


def build_cpe_from_service(service: Service) -> Optional[str]:
    """
    Construye CPE desde un objeto Service.
    
    CPE Format: cpe:/a:vendor:product:version
    
    Args:
        service: Objeto Service con información detectada
    
    Returns:
        CPE string o None si no se puede construir
    
    Examples:
        >>> service = Service(service_name="http", product="Apache httpd", version="2.4.49")
        >>> build_cpe_from_service(service)
        'cpe:/a:apache:http_server:2.4.49'
    """
    if not service.version:
        return None
    
    vendor, product = extract_vendor_product(service.service_name, service.product)
    
    if not vendor or not product:
        return None
    
    version = normalize_version(service.version)
    
    # Format CPE 2.2
    cpe = f"cpe:/a:{vendor}:{product}:{version}"
    
    return cpe
```

#### 2. Service Correlation Service

**Archivo:** `backend/app/services/correlation_service.py`

```python
# backend/app/services/correlation_service.py
"""
Servicio de correlación Service→CVE.

Correlaciona servicios detectados con CVEs de NVD automáticamente.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.service import Service
from app.models.asset import Asset
from app.models.scan import Scan
from app.models.cve_cache import CVECache
from app.models.vulnerability import (
    Vulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
)
from app.utils.cpe_utils import build_cpe_from_service, extract_vendor_product


logger = logging.getLogger(__name__)
settings = get_settings()


class CorrelationService:
    """Servicio para correlacionar servicios con CVEs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.nvd_api_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self.nvd_api_key = settings.NVD_API_KEY
    
    async def correlate_service(
        self,
        service: Service,
        auto_create_vuln: bool = True,
        max_cves: int = 10,
    ) -> Dict[str, Any]:
        """
        Correlaciona un servicio con CVEs.
        
        Flujo:
        1. Construir CPE desde servicio
        2. Buscar en cache local
        3. Si no hay cache, buscar en NVD
        4. Crear vulnerabilidades automáticamente
        
        Args:
            service: Servicio a correlacionar
            auto_create_vuln: Si True, crea Vulnerability automáticamente
            max_cves: Máximo de CVEs a procesar
        
        Returns:
            Dict con resultados:
            {
                'service_id': str,
                'cpe': str,
                'cves_found': int,
                'vulnerabilities_created': int,
                'status': str,
                'cves': List[str],
            }
        """
        logger.info(
            f"🔗 Correlating service: {service.product} {service.version} "
            f"on port {service.port}"
        )
        
        # Paso 1: Construir CPE
        cpe = build_cpe_from_service(service)
        if not cpe:
            logger.warning(f"⚠️ Could not build CPE for service {service.id}")
            return {
                'service_id': str(service.id),
                'cpe': None,
                'cves_found': 0,
                'vulnerabilities_created': 0,
                'status': 'no_cpe',
            }
        
        logger.info(f"📋 CPE built: {cpe}")
        
        # Paso 2: Buscar en cache local primero
        cached_cves = await self._search_cves_in_cache(cpe)
        
        # Paso 3: Si no hay en cache, buscar en NVD
        if not cached_cves:
            logger.info(f"🌐 Searching NVD for {cpe}")
            nvd_cves = await self._search_cves_in_nvd(cpe, max_results=max_cves)
            
            # Guardar en cache
            for cve_data in nvd_cves:
                await self._save_cve_to_cache(cve_data)
            
            cached_cves = nvd_cves
        else:
            logger.info(f"💾 Found {len(cached_cves)} CVEs in cache")
        
        # Paso 4: Crear vulnerabilidades
        vulnerabilities_created = 0
        if auto_create_vuln and cached_cves:
            for cve in cached_cves[:max_cves]:
                vuln = await self._create_vulnerability_from_cve(service, cve)
                if vuln:
                    vulnerabilities_created += 1
        
        result = {
            'service_id': str(service.id),
            'cpe': cpe,
            'cves_found': len(cached_cves),
            'vulnerabilities_created': vulnerabilities_created,
            'status': 'success',
            'cves': [cve['cve_id'] for cve in cached_cves[:5]],  # Top 5
        }
        
        logger.info(f"✅ Correlation complete: {result}")
        return result
    
    async def correlate_scan_services(
        self,
        scan_id: str,
        auto_create: bool = True,
    ) -> Dict[str, Any]:
        """
        Correlaciona todos los servicios de un scan.
        
        Args:
            scan_id: ID del scan
            auto_create: Si True, crea vulnerabilidades automáticamente
        
        Returns:
            Dict con resumen:
            {
                'scan_id': str,
                'services_processed': int,
                'cves_found': int,
                'vulnerabilities_created': int,
                'services': List[Dict],
            }
        """
        logger.info(f"🔗 Correlating services for scan {scan_id}")
        
        # Obtener scan
        scan = await self.db.get(Scan, scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")
        
        # Obtener todos los servicios del scan
        # (servicios de assets que fueron creados por este scan)
        stmt = (
            select(Service)
            .join(Service.asset)
            .join(Asset.scans)
            .where(Scan.id == scan_id)
        )
        result = await self.db.execute(stmt)
        services = result.scalars().all()
        
        logger.info(f"📡 Found {len(services)} services to correlate")
        
        results = {
            'scan_id': scan_id,
            'services_processed': 0,
            'cves_found': 0,
            'vulnerabilities_created': 0,
            'services': [],
        }
        
        for service in services:
            correlation = await self.correlate_service(service, auto_create)
            results['services_processed'] += 1
            results['cves_found'] += correlation['cves_found']
            results['vulnerabilities_created'] += correlation['vulnerabilities_created']
            results['services'].append(correlation)
        
        logger.info(f"✅ Scan correlation complete: {results}")
        return results
    
    async def _search_cves_in_cache(self, cpe: str) -> List[Dict[str, Any]]:
        """Busca CVEs en cache local por CPE."""
        vendor, product = extract_vendor_product("", cpe.split(":")[-2] if ":" in cpe else "")
        if not vendor or not product:
            return []
        
        # Buscar en cache
        stmt = select(CVECache).where(
            CVECache.affected_products.op('@>')(
                [{'vendor': vendor, 'product': product}]
            )
        ).limit(20)
        
        result = await self.db.execute(stmt)
        cves = result.scalars().all()
        
        return [
            {
                'cve_id': cve.cve_id,
                'description': cve.description,
                'cvss_v3_score': cve.cvss_v3_score,
                'cvss_v3_severity': cve.cvss_v3_severity,
                'exploit_available': cve.exploit_available,
                'in_cisa_kev': cve.in_cisa_kev,
            }
            for cve in cves
        ]
    
    async def _search_cves_in_nvd(
        self,
        cpe: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Busca CVEs en NVD API por CPE."""
        headers = {"User-Agent": "NestSecure/1.0"}
        if self.nvd_api_key:
            headers["apiKey"] = self.nvd_api_key
        
        params = {
            "cpeName": cpe,
            "resultsPerPage": max_results,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.nvd_api_url,
                    params=params,
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                
                vulnerabilities = data.get("vulnerabilities", [])
                return [self._parse_nvd_cve(v) for v in vulnerabilities]
        except Exception as e:
            logger.error(f"❌ Error searching NVD: {e}")
            return []
    
    def _parse_nvd_cve(self, cve_item: dict) -> Dict[str, Any]:
        """Parsea CVE de formato NVD 2.0."""
        cve = cve_item.get("cve", {})
        cve_id = cve.get("id")
        
        # Descripción
        descriptions = cve.get("descriptions", [])
        description = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            "No description available"
        )
        
        # CVSS metrics
        metrics = cve.get("metrics", {})
        cvss_v3 = metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {})
        
        return {
            'cve_id': cve_id,
            'description': description,
            'cvss_v3_score': cvss_v3.get("baseScore"),
            'cvss_v3_severity': cvss_v3.get("baseSeverity"),
            'exploit_available': False,  # TODO: Check EPSS/KEV
            'in_cisa_kev': False,
        }
    
    async def _save_cve_to_cache(self, cve_data: Dict[str, Any]) -> CVECache:
        """Guarda CVE en cache local."""
        # Verificar si ya existe
        stmt = select(CVECache).where(CVECache.cve_id == cve_data['cve_id'])
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing
        
        cve = CVECache(
            cve_id=cve_data['cve_id'],
            description=cve_data['description'],
            cvss_v3_score=cve_data.get('cvss_v3_score'),
            cvss_v3_severity=cve_data.get('cvss_v3_severity'),
            exploit_available=cve_data.get('exploit_available', False),
            in_cisa_kev=cve_data.get('in_cisa_kev', False),
        )
        
        self.db.add(cve)
        await self.db.commit()
        return cve
    
    async def _create_vulnerability_from_cve(
        self,
        service: Service,
        cve: Dict[str, Any],
    ) -> Optional[Vulnerability]:
        """Crea una Vulnerability desde un CVE."""
        # Verificar si ya existe
        stmt = select(Vulnerability).where(
            Vulnerability.service_id == service.id,
            Vulnerability.cve_id == cve['cve_id'],
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.debug(f"Vulnerability already exists: {cve['cve_id']}")
            return None
        
        # Mapear severidad
        severity_map = {
            'CRITICAL': VulnerabilitySeverity.CRITICAL,
            'HIGH': VulnerabilitySeverity.HIGH,
            'MEDIUM': VulnerabilitySeverity.MEDIUM,
            'LOW': VulnerabilitySeverity.LOW,
            'NONE': VulnerabilitySeverity.INFO,
        }
        
        severity = severity_map.get(
            cve.get('cvss_v3_severity', 'MEDIUM'),
            VulnerabilitySeverity.MEDIUM
        )
        
        # Obtener asset
        asset = await self.db.get(Asset, service.asset_id)
        
        vuln = Vulnerability(
            name=f"{cve['cve_id']} in {service.product}",
            description=cve['description'],
            severity=severity,
            status=VulnerabilityStatus.OPEN,
            cve_id=cve['cve_id'],
            cvss_score=cve.get('cvss_v3_score'),
            asset_id=service.asset_id,
            service_id=service.id,
            exploit_available=cve.get('exploit_available', False),
            detected_at=datetime.now(timezone.utc),
            organization_id=asset.organization_id,
        )
        
        self.db.add(vuln)
        await self.db.commit()
        
        logger.info(f"✅ Created vulnerability: {vuln.id} from {cve['cve_id']}")
        return vuln
```

#### 3. API Endpoints

**Archivo:** `backend/app/api/v1/correlation.py`

```python
# backend/app/api/v1/correlation.py
"""API endpoints para correlación Service→CVE."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentActiveUser, get_db
from app.models.service import Service
from app.models.scan import Scan
from app.services.correlation_service import CorrelationService


router = APIRouter()


@router.post("/services/{service_id}/correlate")
async def correlate_service(
    service_id: str,
    auto_create_vuln: bool = True,
    max_cves: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActiveUser = Depends(),
) -> dict:
    """
    Correlaciona un servicio con CVEs de NVD.
    
    Busca CVEs relacionados y opcionalmente crea vulnerabilidades.
    """
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Verificar permisos
    asset = await db.get(Asset, service.asset_id)
    if asset.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Correlacionar
    correlation_svc = CorrelationService(db)
    result = await correlation_svc.correlate_service(
        service,
        auto_create_vuln=auto_create_vuln,
        max_cves=max_cves,
    )
    
    return result


@router.post("/scans/{scan_id}/correlate")
async def correlate_scan(
    scan_id: str,
    auto_create: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActiveUser = Depends(),
) -> dict:
    """
    Correlaciona todos los servicios de un scan con CVEs.
    """
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    correlation_svc = CorrelationService(db)
    result = await correlation_svc.correlate_scan_services(scan_id, auto_create)
    
    return result
```

#### 4. Integración en Nmap Worker

```python
# backend/app/workers/nmap_worker.py

@celery_app.task(bind=True, name="nmap.port_scan")
def port_scan(self, asset_id: str, scan_id: str | None = None):
    """Escaneo de puertos y servicios."""
    # ... escaneo con nmap ...
    
    # Al finalizar, si hay servicios detectados Y auto_correlate_cves=True
    if services_created > 0:
        scan = db.query(Scan).get(scan_id)
        if scan and scan.auto_correlate_cves:
            logger.info(f"🔗 Triggering auto CVE correlation for {services_created} services")
            from app.workers.correlation_worker import correlate_scan_task
            correlate_scan_task.delay(scan_id, auto_create=True)
    
    return result
```

**Checklist Completo Fase 3:**

### CVE Frontend (Día 18-19)
- [x] Día 18: Infrastructure completa
- [ ] Día 19: Páginas CVE search y detail

### Network Validation (Día 20)
- [ ] Network validator utils
- [ ] Tests unitarios (10+ tests)
- [ ] Integración en Nmap worker
- [ ] Integración en API
- [ ] Validación frontend
- [ ] Tests E2E

### Service→CVE Correlation (Día 21)
- [ ] CPE utilities
- [ ] Correlation service
- [ ] API endpoints
- [ ] Celery worker integration
- [ ] Frontend UI (botón correlación)
- [ ] Tests unitarios
- [ ] Tests integración

### Nuclei (Día 22)
- [ ] Dockerfile actualizado
- [ ] Templates descargados
- [ ] Worker validado
- [ ] Tests instalación
- [ ] Tests E2E scan real

### ZAP (Día 23)
- [ ] ZAP worker completo
- [ ] Container ZAP
- [ ] API endpoints
- [ ] Tests

### CRUD Completo (Día 24)
- [ ] Assets: bulk delete, export CSV, filtros avanzados
- [ ] Scans: schedule, clone, edit
- [ ] Tests CRUD

### Dashboard (Día 25)
- [ ] CVE Trends widget
- [ ] EPSS Risk widget
- [ ] KEV Alerts widget
- [ ] Scanner Status

### Testing (Día 26)
- [ ] Backend: 550+ tests
- [ ] Frontend: 100+ E2E tests
- [ ] Cobertura >90%

### Performance (Día 27)
- [ ] Índices BD optimizados
- [ ] Redis caching
- [ ] Rate limiting
- [ ] Audit logging
