# =============================================================================
# NESTSECURE - Servicio de Correlación Service→CVE
# =============================================================================
"""
Servicio para correlacionar servicios detectados con CVEs del NVD.

Este servicio:
1. Construye CPEs desde servicios detectados por Nmap
2. Busca CVEs relacionados en cache local y NVD API
3. Crea vulnerabilidades automáticamente

Flujo típico:
1. Nmap detecta: Apache/2.4.49 en puerto 80
2. Se construye CPE: cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*
3. Se busca en NVD API por ese CPE
4. Se encuentran CVEs (ej: CVE-2021-41773, CVE-2021-42013)
5. Se crean Vulnerabilities vinculadas al servicio
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.asset import Asset
from app.models.cve_cache import CVECache
from app.models.scan import Scan
from app.models.service import Service
from app.models.vulnerability import (
    Vulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
)
from app.utils.cpe_utils import (
    build_cpe_from_service_info,
    build_cpe_search_query,
    get_cpe_confidence,
    parse_cpe,
)


logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# CONSTANTES
# =============================================================================

NVD_API_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFAULT_MAX_CVES = 20
RATE_LIMIT_WITH_KEY = 0.6  # segundos entre requests con API key
RATE_LIMIT_WITHOUT_KEY = 6.0  # segundos entre requests sin API key


# =============================================================================
# MAPEOS DE SEVERIDAD
# =============================================================================

CVSS_TO_SEVERITY: Dict[str, VulnerabilitySeverity] = {
    "CRITICAL": VulnerabilitySeverity.CRITICAL,
    "HIGH": VulnerabilitySeverity.HIGH,
    "MEDIUM": VulnerabilitySeverity.MEDIUM,
    "LOW": VulnerabilitySeverity.LOW,
    "NONE": VulnerabilitySeverity.INFO,
}


# =============================================================================
# CLASE PRINCIPAL
# =============================================================================

class CorrelationService:
    """
    Servicio para correlacionar servicios detectados con CVEs.
    
    Attributes:
        db: Sesión de base de datos async
        nvd_api_key: API key de NVD (opcional, mejora rate limits)
    """
    
    def __init__(
        self,
        db: AsyncSession,
        nvd_api_key: Optional[str] = None,
    ):
        self.db = db
        self.nvd_api_key = nvd_api_key or settings.NVD_API_KEY
    
    # -------------------------------------------------------------------------
    # Métodos públicos principales
    # -------------------------------------------------------------------------
    
    async def correlate_service(
        self,
        service: Service,
        scan_id: Optional[str] = None,
        auto_create_vuln: bool = True,
        max_cves: int = DEFAULT_MAX_CVES,
    ) -> Dict[str, Any]:
        """
        Correlaciona un servicio con CVEs del NVD.
        
        Flujo:
        1. Construir CPE desde el servicio
        2. Buscar CVEs en cache local
        3. Si no hay cache, buscar en NVD API
        4. Crear vulnerabilidades automáticamente
        
        Args:
            service: Servicio a correlacionar
            scan_id: ID del scan (para vincular vulnerabilidades)
            auto_create_vuln: Si True, crea Vulnerability automáticamente
            max_cves: Máximo de CVEs a procesar
        
        Returns:
            Dict con resultados:
            {
                'service_id': str,
                'cpe': str | None,
                'cpe_confidence': int,
                'cves_found': int,
                'vulnerabilities_created': int,
                'status': str,  # 'success', 'no_cpe', 'no_cves', 'error'
                'cves': List[str],  # IDs de CVEs encontrados
                'error': str | None,
            }
        """
        result = {
            "service_id": str(service.id),
            "cpe": None,
            "cpe_confidence": 0,
            "cves_found": 0,
            "vulnerabilities_created": 0,
            "status": "pending",
            "cves": [],
            "error": None,
        }
        
        logger.info(
            f"🔗 Correlating service: port={service.port}, "
            f"product={service.product}, version={service.version}"
        )
        
        try:
            # Paso 1: Construir CPE
            cpe = self._build_cpe(service)
            
            if not cpe:
                logger.warning(
                    f"⚠️ Could not build CPE for service {service.id}: "
                    f"{service.product} {service.version}"
                )
                result["status"] = "no_cpe"
                return result
            
            result["cpe"] = cpe
            result["cpe_confidence"] = get_cpe_confidence(
                "nmap_cpe" if service.cpe else "constructed",
                bool(service.version)
            )
            logger.info(f"📋 CPE: {cpe} (confidence: {result['cpe_confidence']})")
            
            # Paso 2: Buscar CVEs en cache local primero
            cves = await self._search_cves_in_cache(cpe)
            
            # Paso 3: Si no hay en cache, buscar en NVD
            if not cves:
                logger.info(f"🌐 Searching NVD for CPE: {cpe}")
                cves = await self._search_cves_in_nvd(cpe, max_results=max_cves)
                
                # Guardar en cache
                for cve_data in cves:
                    await self._save_cve_to_cache(cve_data)
            else:
                logger.info(f"💾 Found {len(cves)} CVEs in local cache")
            
            result["cves_found"] = len(cves)
            result["cves"] = [c["cve_id"] for c in cves[:10]]  # Top 10
            
            if not cves:
                result["status"] = "no_cves"
                return result
            
            # Paso 4: Crear vulnerabilidades
            if auto_create_vuln and cves:
                for cve_data in cves[:max_cves]:
                    vuln = await self._create_vulnerability_from_cve(
                        service=service,
                        cve=cve_data,
                        scan_id=scan_id,
                    )
                    if vuln:
                        result["vulnerabilities_created"] += 1
            
            result["status"] = "success"
            logger.info(
                f"✅ Correlation complete: {result['cves_found']} CVEs, "
                f"{result['vulnerabilities_created']} vulns created"
            )
            
        except Exception as e:
            logger.error(f"❌ Error correlating service {service.id}: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    async def correlate_scan_services(
        self,
        scan_id: str,
        auto_create: bool = True,
        max_cves_per_service: int = 10,
    ) -> Dict[str, Any]:
        """
        Correlaciona todos los servicios de un scan con CVEs.
        
        Args:
            scan_id: ID del scan
            auto_create: Si True, crea vulnerabilidades automáticamente
            max_cves_per_service: Máximo de CVEs por servicio
        
        Returns:
            Dict con resumen:
            {
                'scan_id': str,
                'services_processed': int,
                'services_with_cpe': int,
                'cves_found': int,
                'vulnerabilities_created': int,
                'status': str,
                'services': List[Dict],
            }
        """
        logger.info(f"🔗 Correlating all services for scan {scan_id}")
        
        result = {
            "scan_id": scan_id,
            "services_processed": 0,
            "services_with_cpe": 0,
            "cves_found": 0,
            "vulnerabilities_created": 0,
            "status": "pending",
            "services": [],
        }
        
        try:
            # Verificar scan existe
            scan = await self.db.get(Scan, scan_id)
            if not scan:
                raise ValueError(f"Scan {scan_id} not found")
            
            # Obtener servicios del scan (via assets)
            services = await self._get_scan_services(scan_id)
            
            logger.info(f"📡 Found {len(services)} services to correlate")
            
            for service in services:
                correlation = await self.correlate_service(
                    service=service,
                    scan_id=scan_id,
                    auto_create_vuln=auto_create,
                    max_cves=max_cves_per_service,
                )
                
                result["services_processed"] += 1
                if correlation["cpe"]:
                    result["services_with_cpe"] += 1
                result["cves_found"] += correlation["cves_found"]
                result["vulnerabilities_created"] += correlation["vulnerabilities_created"]
                result["services"].append(correlation)
            
            result["status"] = "success"
            logger.info(
                f"✅ Scan correlation complete: "
                f"{result['services_with_cpe']}/{result['services_processed']} with CPE, "
                f"{result['cves_found']} CVEs, {result['vulnerabilities_created']} vulns"
            )
            
        except Exception as e:
            logger.error(f"❌ Error correlating scan {scan_id}: {e}")
            result["status"] = "error"
        
        return result
    
    async def correlate_asset_services(
        self,
        asset_id: str,
        auto_create: bool = True,
    ) -> Dict[str, Any]:
        """
        Correlaciona todos los servicios de un asset.
        
        Args:
            asset_id: ID del asset
            auto_create: Si True, crea vulnerabilidades
        
        Returns:
            Dict con resultados
        """
        logger.info(f"🔗 Correlating services for asset {asset_id}")
        
        # Obtener asset
        asset = await self.db.get(Asset, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Obtener servicios del asset
        stmt = select(Service).where(Service.asset_id == asset_id)
        result = await self.db.execute(stmt)
        services = result.scalars().all()
        
        results = {
            "asset_id": asset_id,
            "services_processed": 0,
            "cves_found": 0,
            "vulnerabilities_created": 0,
            "services": [],
        }
        
        for service in services:
            correlation = await self.correlate_service(
                service=service,
                auto_create_vuln=auto_create,
            )
            results["services_processed"] += 1
            results["cves_found"] += correlation["cves_found"]
            results["vulnerabilities_created"] += correlation["vulnerabilities_created"]
            results["services"].append(correlation)
        
        return results
    
    # -------------------------------------------------------------------------
    # Métodos privados
    # -------------------------------------------------------------------------
    
    def _build_cpe(self, service: Service) -> Optional[str]:
        """Construye CPE desde un servicio."""
        return build_cpe_from_service_info(
            service_name=service.service_name,
            product=service.product,
            version=service.version,
            existing_cpe=service.cpe,
        )
    
    async def _get_scan_services(self, scan_id: str) -> List[Service]:
        """Obtiene todos los servicios relacionados con un scan."""
        # Los servicios están en assets, que están vinculados a scans
        # Necesitamos obtener assets del scan, luego sus servicios
        stmt = (
            select(Service)
            .join(Service.asset)
            .join(Asset.scans)
            .where(Scan.id == scan_id)
            .where(Service.product.isnot(None))  # Solo servicios con producto detectado
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _search_cves_in_cache(self, cpe: str) -> List[Dict[str, Any]]:
        """Busca CVEs en cache local por CPE."""
        parsed = parse_cpe(cpe)
        if not parsed:
            return []
        
        # Buscar en cve_cache por vendor/product
        # Usar affected_products si está disponible, o buscar por cpe_match
        stmt = select(CVECache).where(
            CVECache.cve_id.isnot(None)
        ).limit(50)
        
        result = await self.db.execute(stmt)
        cves = result.scalars().all()
        
        # Filtrar por vendor/product (simplificado)
        matching_cves = []
        for cve in cves:
            # Por ahora retornar vacío para forzar búsqueda en NVD
            # En producción, implementar matching más sofisticado
            pass
        
        return matching_cves
    
    async def _search_cves_in_nvd(
        self,
        cpe: str,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Busca CVEs en NVD API por CPE."""
        headers = {
            "User-Agent": "NestSecure/1.0 Vulnerability Scanner",
        }
        
        if self.nvd_api_key:
            headers["apiKey"] = self.nvd_api_key
        
        # Construir parámetros de búsqueda
        # NVD API espera cpeName en formato específico
        params = {
            "cpeName": cpe,
            "resultsPerPage": min(max_results, 100),
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    NVD_API_BASE_URL,
                    params=params,
                    headers=headers,
                    timeout=30.0,
                )
                
                if response.status_code == 404:
                    logger.debug(f"No CVEs found for CPE: {cpe}")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                vulnerabilities = data.get("vulnerabilities", [])
                logger.info(f"📦 NVD returned {len(vulnerabilities)} CVEs for {cpe}")
                
                return [
                    self._parse_nvd_cve(v)
                    for v in vulnerabilities
                ]
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"NVD API error: {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.error(f"NVD API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching NVD: {e}")
            return []
    
    def _parse_nvd_cve(self, cve_item: dict) -> Dict[str, Any]:
        """Parsea un CVE del formato NVD 2.0 API."""
        cve = cve_item.get("cve", {})
        cve_id = cve.get("id", "")
        
        # Descripción en inglés
        descriptions = cve.get("descriptions", [])
        description = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            "No description available"
        )
        
        # CVSS v3.1 (preferido) o v3.0
        metrics = cve.get("metrics", {})
        cvss_v31 = metrics.get("cvssMetricV31", [])
        cvss_v30 = metrics.get("cvssMetricV30", [])
        
        cvss_data = {}
        if cvss_v31:
            cvss_data = cvss_v31[0].get("cvssData", {})
        elif cvss_v30:
            cvss_data = cvss_v30[0].get("cvssData", {})
        
        # Fechas
        published = cve.get("published", "")
        last_modified = cve.get("lastModified", "")
        
        # Referencias
        references = [
            ref.get("url", "")
            for ref in cve.get("references", [])
        ]
        
        # CWE
        weaknesses = cve.get("weaknesses", [])
        cwe_id = None
        if weaknesses:
            for weakness in weaknesses:
                for desc in weakness.get("description", []):
                    if desc.get("lang") == "en":
                        cwe_val = desc.get("value", "")
                        if cwe_val.startswith("CWE-"):
                            cwe_id = cwe_val
                            break
        
        return {
            "cve_id": cve_id,
            "description": description[:4000],  # Limitar longitud
            "cvss_v3_score": cvss_data.get("baseScore"),
            "cvss_v3_vector": cvss_data.get("vectorString"),
            "cvss_v3_severity": cvss_data.get("baseSeverity"),
            "published_date": published,
            "last_modified_date": last_modified,
            "references": references[:10],  # Limitar
            "cwe_id": cwe_id,
            "exploit_available": False,  # TODO: Check EPSS/ExploitDB
            "in_cisa_kev": False,  # TODO: Check KEV
        }
    
    async def _save_cve_to_cache(self, cve_data: Dict[str, Any]) -> Optional[CVECache]:
        """Guarda un CVE en cache local."""
        cve_id = cve_data.get("cve_id")
        if not cve_id:
            return None
        
        # Verificar si ya existe
        existing = await self.db.get(CVECache, cve_id)
        if existing:
            return existing
        
        try:
            # Parsear fechas
            published = cve_data.get("published_date", "")
            last_modified = cve_data.get("last_modified_date", "")
            
            published_dt = datetime.now(timezone.utc)
            last_modified_dt = datetime.now(timezone.utc)
            
            if published:
                try:
                    published_dt = datetime.fromisoformat(
                        published.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass
            
            if last_modified:
                try:
                    last_modified_dt = datetime.fromisoformat(
                        last_modified.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass
            
            cve = CVECache(
                cve_id=cve_id,
                description=cve_data.get("description", ""),
                published_date=published_dt,
                last_modified_date=last_modified_dt,
                cvss_v3_score=cve_data.get("cvss_v3_score"),
                cvss_v3_vector=cve_data.get("cvss_v3_vector"),
                cvss_v3_severity=cve_data.get("cvss_v3_severity"),
                exploit_available=cve_data.get("exploit_available", False),
                in_cisa_kev=cve_data.get("in_cisa_kev", False),
            )
            
            self.db.add(cve)
            await self.db.commit()
            
            logger.debug(f"💾 Cached CVE: {cve_id}")
            return cve
            
        except Exception as e:
            logger.error(f"Error saving CVE {cve_id} to cache: {e}")
            await self.db.rollback()
            return None
    
    async def _create_vulnerability_from_cve(
        self,
        service: Service,
        cve: Dict[str, Any],
        scan_id: Optional[str] = None,
    ) -> Optional[Vulnerability]:
        """Crea una Vulnerability desde datos de CVE."""
        cve_id = cve.get("cve_id")
        if not cve_id:
            return None
        
        # Verificar si ya existe esta vuln para este servicio
        stmt = select(Vulnerability).where(
            and_(
                Vulnerability.service_id == service.id,
                Vulnerability.cve_id == cve_id,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.debug(f"Vulnerability {cve_id} already exists for service {service.id}")
            return None
        
        # Obtener asset para organization_id
        asset = await self.db.get(Asset, service.asset_id)
        if not asset:
            logger.error(f"Asset {service.asset_id} not found")
            return None
        
        # Mapear severidad
        cvss_severity = cve.get("cvss_v3_severity", "MEDIUM")
        severity = CVSS_TO_SEVERITY.get(
            cvss_severity.upper() if cvss_severity else "MEDIUM",
            VulnerabilitySeverity.MEDIUM
        )
        
        # Determinar scan_id
        if not scan_id:
            # Intentar obtener del asset
            if asset.scans:
                scan_id = str(asset.scans[0].id)
            else:
                # Crear un scan_id temporal (esto no debería pasar)
                logger.warning(f"No scan_id for vulnerability {cve_id}")
                return None
        
        try:
            vuln = Vulnerability(
                organization_id=asset.organization_id,
                asset_id=service.asset_id,
                service_id=service.id,
                scan_id=scan_id,
                cve_id=cve_id,
                name=f"{cve_id}: {service.product or 'Unknown Service'}",
                description=cve.get("description", f"Vulnerability {cve_id}"),
                host=asset.ip_address,
                port=service.port,
                severity=severity,
                status=VulnerabilityStatus.OPEN,
                cvss_score=cve.get("cvss_v3_score"),
                cvss_vector=cve.get("cvss_v3_vector"),
                cwe_id=cve.get("cwe_id"),
                references=cve.get("references", []),
                exploit_available=cve.get("exploit_available", False),
                detected_at=datetime.now(timezone.utc),
            )
            
            self.db.add(vuln)
            await self.db.commit()
            await self.db.refresh(vuln)
            
            logger.info(
                f"✅ Created vulnerability: {vuln.id} from {cve_id} "
                f"(severity: {severity.value})"
            )
            return vuln
            
        except Exception as e:
            logger.error(f"Error creating vulnerability from {cve_id}: {e}")
            await self.db.rollback()
            return None


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

async def correlate_service_quick(
    db: AsyncSession,
    service_id: str,
) -> Dict[str, Any]:
    """
    Correlación rápida de un servicio por ID.
    
    Args:
        db: Sesión de base de datos
        service_id: ID del servicio
    
    Returns:
        Resultados de correlación
    """
    service = await db.get(Service, service_id)
    if not service:
        raise ValueError(f"Service {service_id} not found")
    
    correlation_svc = CorrelationService(db)
    return await correlation_svc.correlate_service(service)


async def correlate_scan_quick(
    db: AsyncSession,
    scan_id: str,
) -> Dict[str, Any]:
    """
    Correlación rápida de todos los servicios de un scan.
    
    Args:
        db: Sesión de base de datos
        scan_id: ID del scan
    
    Returns:
        Resultados de correlación
    """
    correlation_svc = CorrelationService(db)
    return await correlation_svc.correlate_scan_services(scan_id)
