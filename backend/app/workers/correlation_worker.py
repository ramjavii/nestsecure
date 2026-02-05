# =============================================================================
# NESTSECURE - Worker de Correlación CVE
# =============================================================================
"""
Worker de Celery para correlacionar servicios detectados con CVEs.

Tareas:
- correlate_scan_cves: Correlaciona todos los servicios de un scan
- correlate_service_cves: Correlaciona un servicio individual
- correlate_asset_cves: Correlaciona todos los servicios de un asset
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from celery import shared_task
from sqlalchemy import select, and_

from app.config import get_settings
from app.db.session import get_sync_db
from app.models.asset import Asset
from app.models.cve_cache import CVECache
from app.models.scan import Scan, ScanStatus
from app.models.service import Service
from app.models.vulnerability import (
    Vulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
)
from app.utils.cpe_utils import (
    build_cpe_from_service_info,
    get_cpe_confidence,
    parse_cpe,
)


logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# CONSTANTES
# =============================================================================

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_API_KEY = settings.NVD_API_KEY
RATE_LIMIT_DELAY = 0.6 if NVD_API_KEY else 6.0  # segundos entre requests


# Mapeo CVSS a severidad
CVSS_SEVERITY_MAP = {
    "CRITICAL": VulnerabilitySeverity.CRITICAL,
    "HIGH": VulnerabilitySeverity.HIGH,
    "MEDIUM": VulnerabilitySeverity.MEDIUM,
    "LOW": VulnerabilitySeverity.LOW,
    "NONE": VulnerabilitySeverity.INFO,
}


# =============================================================================
# TAREAS PRINCIPALES
# =============================================================================

@shared_task(
    bind=True,
    name="app.workers.correlation_worker.correlate_scan_cves",
    max_retries=2,
    default_retry_delay=60,
    rate_limit="1/m",  # Respetar rate limits de NVD
)
def correlate_scan_cves(
    self,
    scan_id: str,
    auto_create_vulns: bool = True,
    max_cves_per_service: int = 10,
) -> Dict[str, Any]:
    """
    Correlaciona todos los servicios de un scan con CVEs.
    
    Esta tarea se puede ejecutar automáticamente después de un scan
    de puertos o manualmente desde la UI.
    
    Args:
        scan_id: ID del scan a correlacionar
        auto_create_vulns: Si True, crea vulnerabilidades automáticamente
        max_cves_per_service: Máximo de CVEs por servicio
    
    Returns:
        Dict con resultados de correlación
    """
    logger.info(f"🔗 Starting CVE correlation for scan {scan_id}")
    
    result = {
        "scan_id": scan_id,
        "services_processed": 0,
        "services_with_cpe": 0,
        "cves_found": 0,
        "vulnerabilities_created": 0,
        "status": "pending",
        "errors": [],
    }
    
    db = get_sync_db()
    
    try:
        # Verificar scan existe
        scan = db.execute(
            select(Scan).where(Scan.id == scan_id)
        ).scalar_one_or_none()
        
        if not scan:
            result["status"] = "error"
            result["errors"].append(f"Scan {scan_id} not found")
            return result
        
        # Obtener servicios del scan (via assets)
        # Los assets están vinculados a scans via many-to-many
        services = db.execute(
            select(Service)
            .join(Service.asset)
            .join(Asset.scans)
            .where(Scan.id == scan_id)
            .where(Service.product.isnot(None))  # Solo con producto detectado
        ).scalars().all()
        
        logger.info(f"📡 Found {len(services)} services with product info")
        
        for service in services:
            service_result = _correlate_single_service(
                db=db,
                service=service,
                scan_id=scan_id,
                auto_create_vulns=auto_create_vulns,
                max_cves=max_cves_per_service,
            )
            
            result["services_processed"] += 1
            if service_result["cpe"]:
                result["services_with_cpe"] += 1
            result["cves_found"] += service_result.get("cves_found", 0)
            result["vulnerabilities_created"] += service_result.get("vulns_created", 0)
            
            if service_result.get("error"):
                result["errors"].append(service_result["error"])
        
        result["status"] = "success"
        
        logger.info(
            f"✅ Scan correlation complete: "
            f"{result['services_with_cpe']}/{result['services_processed']} with CPE, "
            f"{result['cves_found']} CVEs, {result['vulnerabilities_created']} vulns"
        )
        
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        logger.exception(f"Error correlating scan {scan_id}: {e}")
        raise self.retry(exc=e)
    
    finally:
        db.close()
    
    return result


@shared_task(
    bind=True,
    name="app.workers.correlation_worker.correlate_service_cves",
    max_retries=2,
    rate_limit="2/m",
)
def correlate_service_cves(
    self,
    service_id: str,
    scan_id: Optional[str] = None,
    auto_create_vulns: bool = True,
    max_cves: int = 10,
) -> Dict[str, Any]:
    """
    Correlaciona un servicio individual con CVEs.
    
    Args:
        service_id: ID del servicio
        scan_id: ID del scan (opcional, para vincular vulnerabilidades)
        auto_create_vulns: Si True, crea vulnerabilidades
        max_cves: Máximo de CVEs a procesar
    
    Returns:
        Dict con resultados
    """
    logger.info(f"🔗 Correlating service {service_id}")
    
    db = get_sync_db()
    
    try:
        service = db.execute(
            select(Service).where(Service.id == service_id)
        ).scalar_one_or_none()
        
        if not service:
            return {
                "service_id": service_id,
                "status": "error",
                "error": "Service not found",
            }
        
        result = _correlate_single_service(
            db=db,
            service=service,
            scan_id=scan_id,
            auto_create_vulns=auto_create_vulns,
            max_cves=max_cves,
        )
        
        return result
        
    except Exception as e:
        logger.exception(f"Error correlating service {service_id}: {e}")
        raise self.retry(exc=e)
    
    finally:
        db.close()


@shared_task(
    bind=True,
    name="app.workers.correlation_worker.correlate_asset_cves",
    max_retries=2,
    rate_limit="1/m",
)
def correlate_asset_cves(
    self,
    asset_id: str,
    auto_create_vulns: bool = True,
) -> Dict[str, Any]:
    """
    Correlaciona todos los servicios de un asset.
    
    Args:
        asset_id: ID del asset
        auto_create_vulns: Si True, crea vulnerabilidades
    
    Returns:
        Dict con resultados
    """
    logger.info(f"🔗 Correlating services for asset {asset_id}")
    
    result = {
        "asset_id": asset_id,
        "services_processed": 0,
        "cves_found": 0,
        "vulnerabilities_created": 0,
        "status": "pending",
        "errors": [],
    }
    
    db = get_sync_db()
    
    try:
        services = db.execute(
            select(Service)
            .where(Service.asset_id == asset_id)
            .where(Service.product.isnot(None))
        ).scalars().all()
        
        for service in services:
            service_result = _correlate_single_service(
                db=db,
                service=service,
                auto_create_vulns=auto_create_vulns,
            )
            
            result["services_processed"] += 1
            result["cves_found"] += service_result.get("cves_found", 0)
            result["vulnerabilities_created"] += service_result.get("vulns_created", 0)
        
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        logger.exception(f"Error correlating asset {asset_id}: {e}")
    
    finally:
        db.close()
    
    return result


# =============================================================================
# FUNCIONES INTERNAS
# =============================================================================

def _correlate_single_service(
    db,
    service: Service,
    scan_id: Optional[str] = None,
    auto_create_vulns: bool = True,
    max_cves: int = 10,
) -> Dict[str, Any]:
    """Correlaciona un servicio individual con CVEs."""
    result = {
        "service_id": str(service.id),
        "port": service.port,
        "product": service.product,
        "version": service.version,
        "cpe": None,
        "cpe_confidence": 0,
        "cves_found": 0,
        "vulns_created": 0,
        "status": "pending",
        "error": None,
    }
    
    try:
        # Construir CPE
        cpe = build_cpe_from_service_info(
            service_name=service.service_name,
            product=service.product,
            version=service.version,
            existing_cpe=service.cpe,
        )
        
        if not cpe:
            result["status"] = "no_cpe"
            return result
        
        result["cpe"] = cpe
        result["cpe_confidence"] = get_cpe_confidence(
            "nmap_cpe" if service.cpe else "constructed",
            bool(service.version)
        )
        
        logger.debug(f"CPE for {service.product}: {cpe}")
        
        # Buscar CVEs en NVD
        cves = _search_nvd_for_cpe(cpe, max_results=max_cves)
        result["cves_found"] = len(cves)
        
        if not cves:
            result["status"] = "no_cves"
            return result
        
        # Guardar en cache y crear vulnerabilidades
        if auto_create_vulns:
            for cve_data in cves:
                # Guardar en cache
                _save_cve_to_cache(db, cve_data)
                
                # Crear vulnerabilidad
                vuln = _create_vulnerability(
                    db=db,
                    service=service,
                    cve_data=cve_data,
                    scan_id=scan_id,
                )
                if vuln:
                    result["vulns_created"] += 1
        
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Error correlating service {service.id}: {e}")
    
    return result


def _search_nvd_for_cpe(cpe: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Busca CVEs en NVD API por CPE."""
    import time
    
    headers = {"User-Agent": "NestSecure/1.0 VulnScanner"}
    if NVD_API_KEY:
        headers["apiKey"] = NVD_API_KEY
    
    params = {
        "cpeName": cpe,
        "resultsPerPage": min(max_results, 100),
    }
    
    try:
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
        
        response = httpx.get(
            NVD_API_URL,
            params=params,
            headers=headers,
            timeout=30.0,
        )
        
        if response.status_code == 404:
            return []
        
        response.raise_for_status()
        data = response.json()
        
        vulnerabilities = data.get("vulnerabilities", [])
        logger.info(f"NVD returned {len(vulnerabilities)} CVEs for {cpe}")
        
        return [_parse_nvd_cve(v) for v in vulnerabilities]
        
    except httpx.HTTPStatusError as e:
        logger.warning(f"NVD API error: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Error searching NVD: {e}")
        return []


def _parse_nvd_cve(cve_item: dict) -> Dict[str, Any]:
    """Parsea CVE de formato NVD 2.0."""
    cve = cve_item.get("cve", {})
    cve_id = cve.get("id", "")
    
    # Descripción
    descriptions = cve.get("descriptions", [])
    description = next(
        (d["value"] for d in descriptions if d.get("lang") == "en"),
        "No description"
    )
    
    # CVSS v3
    metrics = cve.get("metrics", {})
    cvss_v31 = metrics.get("cvssMetricV31", [])
    cvss_v30 = metrics.get("cvssMetricV30", [])
    
    cvss_data = {}
    if cvss_v31:
        cvss_data = cvss_v31[0].get("cvssData", {})
    elif cvss_v30:
        cvss_data = cvss_v30[0].get("cvssData", {})
    
    # Referencias
    references = [
        ref.get("url", "")
        for ref in cve.get("references", [])[:10]
    ]
    
    # CWE
    cwe_id = None
    for weakness in cve.get("weaknesses", []):
        for desc in weakness.get("description", []):
            if desc.get("lang") == "en" and desc.get("value", "").startswith("CWE-"):
                cwe_id = desc.get("value")
                break
    
    return {
        "cve_id": cve_id,
        "description": description[:4000],
        "cvss_v3_score": cvss_data.get("baseScore"),
        "cvss_v3_vector": cvss_data.get("vectorString"),
        "cvss_v3_severity": cvss_data.get("baseSeverity"),
        "published": cve.get("published", ""),
        "last_modified": cve.get("lastModified", ""),
        "references": references,
        "cwe_id": cwe_id,
    }


def _save_cve_to_cache(db, cve_data: Dict[str, Any]) -> Optional[CVECache]:
    """Guarda CVE en cache local."""
    cve_id = cve_data.get("cve_id")
    if not cve_id:
        return None
    
    # Verificar si existe
    existing = db.execute(
        select(CVECache).where(CVECache.cve_id == cve_id)
    ).scalar_one_or_none()
    
    if existing:
        return existing
    
    try:
        # Parsear fechas
        now = datetime.now(timezone.utc)
        
        published = cve_data.get("published", "")
        last_modified = cve_data.get("last_modified", "")
        
        pub_dt = now
        mod_dt = now
        
        if published:
            try:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                pass
        
        if last_modified:
            try:
                mod_dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            except ValueError:
                pass
        
        cve = CVECache(
            cve_id=cve_id,
            description=cve_data.get("description", ""),
            published_date=pub_dt,
            last_modified_date=mod_dt,
            cvss_v3_score=cve_data.get("cvss_v3_score"),
            cvss_v3_vector=cve_data.get("cvss_v3_vector"),
            cvss_v3_severity=cve_data.get("cvss_v3_severity"),
        )
        
        db.add(cve)
        db.commit()
        
        return cve
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error caching CVE {cve_id}: {e}")
        return None


def _create_vulnerability(
    db,
    service: Service,
    cve_data: Dict[str, Any],
    scan_id: Optional[str] = None,
) -> Optional[Vulnerability]:
    """Crea una Vulnerability desde datos de CVE."""
    cve_id = cve_data.get("cve_id")
    if not cve_id:
        return None
    
    # Verificar si ya existe
    existing = db.execute(
        select(Vulnerability).where(
            and_(
                Vulnerability.service_id == service.id,
                Vulnerability.cve_id == cve_id,
            )
        )
    ).scalar_one_or_none()
    
    if existing:
        return None
    
    # Obtener asset
    asset = db.execute(
        select(Asset).where(Asset.id == service.asset_id)
    ).scalar_one_or_none()
    
    if not asset:
        return None
    
    # Obtener scan_id si no se proporcionó
    if not scan_id:
        # Intentar obtener del asset (primer scan asociado)
        if hasattr(asset, 'scans') and asset.scans:
            scan_id = str(asset.scans[0].id)
        else:
            logger.warning(f"No scan_id available for vulnerability {cve_id}")
            return None
    
    # Mapear severidad
    cvss_severity = cve_data.get("cvss_v3_severity", "MEDIUM")
    severity = CVSS_SEVERITY_MAP.get(
        cvss_severity.upper() if cvss_severity else "MEDIUM",
        VulnerabilitySeverity.MEDIUM
    )
    
    try:
        vuln = Vulnerability(
            organization_id=asset.organization_id,
            asset_id=service.asset_id,
            service_id=service.id,
            scan_id=scan_id,
            cve_id=cve_id,
            name=f"{cve_id}: {service.product or 'Service'}",
            description=cve_data.get("description", f"Vulnerability {cve_id}"),
            host=asset.ip_address,
            port=service.port,
            severity=severity,
            status=VulnerabilityStatus.OPEN,
            cvss_score=cve_data.get("cvss_v3_score"),
            cvss_vector=cve_data.get("cvss_v3_vector"),
            cwe_id=cve_data.get("cwe_id"),
            references=cve_data.get("references", []),
            detected_at=datetime.now(timezone.utc),
        )
        
        db.add(vuln)
        db.commit()
        
        logger.info(f"✅ Created vulnerability: {cve_id} for service {service.id}")
        return vuln
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating vulnerability {cve_id}: {e}")
        return None
