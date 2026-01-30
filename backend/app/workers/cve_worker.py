# =============================================================================
# NESTSECURE - CVE Worker
# =============================================================================
"""
Worker para sincronización de CVEs desde NVD (National Vulnerability Database).

Características:
- Sincronización incremental por fecha
- Sincronización de CVEs específicos
- Caché local en PostgreSQL
- Rate limiting automático para la API de NVD
- Enriquecimiento con datos de EPSS y CISA KEV
"""

import logging
from datetime import datetime, timedelta
from time import sleep
from typing import Any

import httpx
from celery import states

from app.core.config import get_settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Constants
# =============================================================================
NVD_API_URL = settings.NVD_API_URL
NVD_API_KEY = settings.NVD_API_KEY
EPSS_API_URL = "https://api.first.org/data/v1/epss"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

# Rate limiting: 5 requests per 30 seconds without API key, 50 with key
RATE_LIMIT_DELAY = 0.6 if NVD_API_KEY else 6.0
BATCH_SIZE = 100  # CVEs per request


# =============================================================================
# Helper Functions
# =============================================================================
def get_http_client() -> httpx.Client:
    """Crea un cliente HTTP configurado para NVD API."""
    headers = {
        "User-Agent": "NestSecure/1.0 (vulnerability-scanner)",
    }
    if NVD_API_KEY:
        headers["apiKey"] = NVD_API_KEY
    
    return httpx.Client(
        headers=headers,
        timeout=30.0,
        follow_redirects=True,
    )


def parse_nvd_cve(cve_item: dict) -> dict:
    """
    Parsea un CVE del formato NVD API 2.0 a nuestro formato.
    
    Args:
        cve_item: Item de CVE de la API de NVD
    
    Returns:
        dict con datos normalizados del CVE
    """
    cve = cve_item.get("cve", {})
    cve_id = cve.get("id", "")
    
    # Descripción (preferir inglés)
    description = ""
    descriptions = cve.get("descriptions", [])
    for desc in descriptions:
        if desc.get("lang") == "en":
            description = desc.get("value", "")
            break
    if not description and descriptions:
        description = descriptions[0].get("value", "")
    
    # CVSS v3.1 o v3.0
    cvss_v3_score = None
    cvss_v3_vector = None
    cvss_v3_severity = None
    
    metrics = cve.get("metrics", {})
    cvss_v31 = metrics.get("cvssMetricV31", [])
    cvss_v30 = metrics.get("cvssMetricV30", [])
    
    cvss_data = None
    if cvss_v31:
        cvss_data = cvss_v31[0].get("cvssData", {})
    elif cvss_v30:
        cvss_data = cvss_v30[0].get("cvssData", {})
    
    if cvss_data:
        cvss_v3_score = cvss_data.get("baseScore")
        cvss_v3_vector = cvss_data.get("vectorString")
        cvss_v3_severity = cvss_data.get("baseSeverity")
    
    # CVSS v2 (para CVEs antiguos)
    cvss_v2_score = None
    cvss_v2_vector = None
    
    cvss_v2_list = metrics.get("cvssMetricV2", [])
    if cvss_v2_list:
        cvss_v2_data = cvss_v2_list[0].get("cvssData", {})
        cvss_v2_score = cvss_v2_data.get("baseScore")
        cvss_v2_vector = cvss_v2_data.get("vectorString")
    
    # CWE
    cwe_ids = []
    weaknesses = cve.get("weaknesses", [])
    for weakness in weaknesses:
        for desc in weakness.get("description", []):
            if desc.get("lang") == "en":
                value = desc.get("value", "")
                if value.startswith("CWE-"):
                    cwe_ids.append(value)
    
    # Referencias
    references = []
    for ref in cve.get("references", []):
        url = ref.get("url", "")
        if url:
            references.append({
                "url": url,
                "source": ref.get("source", ""),
                "tags": ref.get("tags", []),
            })
    
    # CPE (productos afectados)
    affected_products = []
    configurations = cve.get("configurations", [])
    for config in configurations:
        for node in config.get("nodes", []):
            for cpe_match in node.get("cpeMatch", []):
                if cpe_match.get("vulnerable"):
                    affected_products.append({
                        "cpe": cpe_match.get("criteria", ""),
                        "version_start": cpe_match.get("versionStartIncluding"),
                        "version_end": cpe_match.get("versionEndIncluding"),
                    })
    
    # Fechas
    published_date = cve.get("published")
    last_modified_date = cve.get("lastModified")
    
    return {
        "cve_id": cve_id,
        "description": description,
        "cvss_v3_score": cvss_v3_score,
        "cvss_v3_vector": cvss_v3_vector,
        "cvss_v3_severity": cvss_v3_severity,
        "cvss_v2_score": cvss_v2_score,
        "cvss_v2_vector": cvss_v2_vector,
        "cwe_ids": cwe_ids,
        "references": references,
        "affected_products": affected_products,
        "published_date": published_date,
        "last_modified_date": last_modified_date,
    }


# =============================================================================
# CVE Sync Task
# =============================================================================
@celery_app.task(
    bind=True,
    name="cve.sync_cves",
    max_retries=3,
    default_retry_delay=60,
)
def sync_cves(self, days_back: int = 7, full_sync: bool = False) -> dict:
    """
    Sincroniza CVEs desde NVD API.
    
    Args:
        days_back: Días hacia atrás para sincronizar (default: 7)
        full_sync: Si True, sincroniza todos los CVEs (¡puede tardar horas!)
    
    Returns:
        dict con estadísticas de sincronización
    """
    from app.db.session import get_sync_session
    from app.models.cve_cache import CVECache
    
    logger.info(f"Starting CVE sync: days_back={days_back}, full_sync={full_sync}")
    
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "cves_fetched": 0,
        "cves_created": 0,
        "cves_updated": 0,
        "errors": [],
    }
    
    try:
        # Calcular fechas
        end_date = datetime.utcnow()
        if full_sync:
            # Para full sync, empezamos desde 1999 (primeros CVEs)
            start_date = datetime(1999, 1, 1)
        else:
            start_date = end_date - timedelta(days=days_back)
        
        # Formato de fecha para NVD API
        pub_start = start_date.strftime("%Y-%m-%dT00:00:00.000")
        pub_end = end_date.strftime("%Y-%m-%dT23:59:59.999")
        
        client = get_http_client()
        start_index = 0
        total_results = None
        
        with get_sync_session() as session:
            while True:
                # Construir URL con parámetros
                params = {
                    "lastModStartDate": pub_start,
                    "lastModEndDate": pub_end,
                    "startIndex": start_index,
                    "resultsPerPage": BATCH_SIZE,
                }
                
                # Update task state
                self.update_state(
                    state=states.STARTED,
                    meta={
                        "status": "fetching",
                        "start_index": start_index,
                        "total": total_results,
                        "fetched": stats["cves_fetched"],
                    }
                )
                
                # Hacer request
                try:
                    response = client.get(NVD_API_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPError as e:
                    logger.error(f"HTTP error fetching CVEs: {e}")
                    stats["errors"].append(f"HTTP error at index {start_index}: {str(e)}")
                    # Retry después de delay
                    sleep(RATE_LIMIT_DELAY * 2)
                    continue
                
                # Parsear resultados
                if total_results is None:
                    total_results = data.get("totalResults", 0)
                    logger.info(f"Total CVEs to sync: {total_results}")
                
                vulnerabilities = data.get("vulnerabilities", [])
                
                if not vulnerabilities:
                    break
                
                # Procesar cada CVE
                for vuln_item in vulnerabilities:
                    try:
                        cve_data = parse_nvd_cve(vuln_item)
                        cve_id = cve_data["cve_id"]
                        
                        # Buscar si ya existe
                        existing = session.query(CVECache).filter(
                            CVECache.cve_id == cve_id
                        ).first()
                        
                        if existing:
                            # Actualizar
                            existing.description = cve_data["description"]
                            existing.cvss_v3_score = cve_data["cvss_v3_score"]
                            existing.cvss_v3_vector = cve_data["cvss_v3_vector"]
                            existing.cvss_v2_score = cve_data["cvss_v2_score"]
                            existing.cvss_v2_vector = cve_data["cvss_v2_vector"]
                            existing.cwe_ids = cve_data["cwe_ids"]
                            existing.references = cve_data["references"]
                            existing.affected_products = cve_data["affected_products"]
                            existing.last_modified_date = datetime.fromisoformat(
                                cve_data["last_modified_date"].replace("Z", "+00:00")
                            ) if cve_data["last_modified_date"] else None
                            stats["cves_updated"] += 1
                        else:
                            # Crear nuevo
                            new_cve = CVECache(
                                cve_id=cve_id,
                                description=cve_data["description"],
                                cvss_v3_score=cve_data["cvss_v3_score"],
                                cvss_v3_vector=cve_data["cvss_v3_vector"],
                                cvss_v2_score=cve_data["cvss_v2_score"],
                                cvss_v2_vector=cve_data["cvss_v2_vector"],
                                cwe_ids=cve_data["cwe_ids"],
                                references=cve_data["references"],
                                affected_products=cve_data["affected_products"],
                                published_date=datetime.fromisoformat(
                                    cve_data["published_date"].replace("Z", "+00:00")
                                ) if cve_data["published_date"] else None,
                                last_modified_date=datetime.fromisoformat(
                                    cve_data["last_modified_date"].replace("Z", "+00:00")
                                ) if cve_data["last_modified_date"] else None,
                            )
                            session.add(new_cve)
                            stats["cves_created"] += 1
                        
                        stats["cves_fetched"] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing CVE: {e}")
                        stats["errors"].append(f"Error processing CVE: {str(e)}")
                
                # Commit batch
                session.commit()
                
                # Check if we're done
                start_index += len(vulnerabilities)
                if start_index >= total_results:
                    break
                
                # Rate limiting
                sleep(RATE_LIMIT_DELAY)
        
        stats["completed_at"] = datetime.utcnow().isoformat()
        stats["status"] = "completed"
        
        logger.info(f"CVE sync completed: {stats}")
        return stats
        
    except Exception as e:
        logger.exception(f"CVE sync failed: {e}")
        stats["status"] = "failed"
        stats["error"] = str(e)
        raise self.retry(exc=e)


# =============================================================================
# CVE Lookup Task
# =============================================================================
@celery_app.task(
    bind=True,
    name="cve.lookup_cve",
    max_retries=3,
    default_retry_delay=30,
)
def lookup_cve(self, cve_id: str) -> dict:
    """
    Busca información de un CVE específico en NVD y lo guarda en caché.
    
    Args:
        cve_id: ID del CVE (ej: CVE-2024-1234)
    
    Returns:
        dict con información del CVE
    """
    from app.db.session import get_sync_session
    from app.models.cve_cache import CVECache
    
    logger.info(f"Looking up CVE: {cve_id}")
    
    # Normalizar formato
    cve_id = cve_id.upper()
    if not cve_id.startswith("CVE-"):
        cve_id = f"CVE-{cve_id}"
    
    # Verificar caché primero
    with get_sync_session() as session:
        cached = session.query(CVECache).filter(
            CVECache.cve_id == cve_id
        ).first()
        
        if cached:
            # Check if cache is fresh (less than 24 hours old)
            cache_age = datetime.utcnow() - cached.updated_at
            if cache_age < timedelta(hours=24):
                cached.increment_hit_count()
                session.commit()
                return {
                    "status": "cached",
                    "cve_id": cached.cve_id,
                    "description": cached.description,
                    "cvss_v3_score": cached.cvss_v3_score,
                    "cvss_v3_vector": cached.cvss_v3_vector,
                    "cvss_v2_score": cached.cvss_v2_score,
                    "cvss_v2_vector": cached.cvss_v2_vector,
                    "published_date": cached.published_date.isoformat() if cached.published_date else None,
                }
    
    # Fetch from NVD
    client = get_http_client()
    
    try:
        params = {"cveId": cve_id}
        response = client.get(NVD_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        vulnerabilities = data.get("vulnerabilities", [])
        
        if not vulnerabilities:
            return {
                "status": "not_found",
                "cve_id": cve_id,
            }
        
        # Parse and save
        cve_data = parse_nvd_cve(vulnerabilities[0])
        
        with get_sync_session() as session:
            existing = session.query(CVECache).filter(
                CVECache.cve_id == cve_id
            ).first()
            
            if existing:
                # Update existing
                existing.description = cve_data["description"]
                existing.cvss_v3_score = cve_data["cvss_v3_score"]
                existing.cvss_v3_vector = cve_data["cvss_v3_vector"]
                existing.cvss_v2_score = cve_data["cvss_v2_score"]
                existing.cvss_v2_vector = cve_data["cvss_v2_vector"]
                existing.cwe_ids = cve_data["cwe_ids"]
                existing.references = cve_data["references"]
                existing.affected_products = cve_data["affected_products"]
                existing.increment_hit_count()
            else:
                # Create new
                new_cve = CVECache(
                    cve_id=cve_id,
                    description=cve_data["description"],
                    cvss_v3_score=cve_data["cvss_v3_score"],
                    cvss_v3_vector=cve_data["cvss_v3_vector"],
                    cvss_v2_score=cve_data["cvss_v2_score"],
                    cvss_v2_vector=cve_data["cvss_v2_vector"],
                    cwe_ids=cve_data["cwe_ids"],
                    references=cve_data["references"],
                    affected_products=cve_data["affected_products"],
                    published_date=datetime.fromisoformat(
                        cve_data["published_date"].replace("Z", "+00:00")
                    ) if cve_data["published_date"] else None,
                    last_modified_date=datetime.fromisoformat(
                        cve_data["last_modified_date"].replace("Z", "+00:00")
                    ) if cve_data["last_modified_date"] else None,
                )
                session.add(new_cve)
            
            session.commit()
        
        return {
            "status": "fetched",
            **cve_data,
        }
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error looking up CVE {cve_id}: {e}")
        raise self.retry(exc=e)


# =============================================================================
# EPSS Enrichment Task
# =============================================================================
@celery_app.task(
    bind=True,
    name="cve.enrich_epss",
)
def enrich_epss(self, cve_ids: list[str]) -> dict:
    """
    Enriquece CVEs con datos de EPSS (Exploit Prediction Scoring System).
    
    EPSS proporciona una probabilidad de que un CVE sea explotado
    en los próximos 30 días.
    
    Args:
        cve_ids: Lista de IDs de CVEs para enriquecer
    
    Returns:
        dict con estadísticas de enriquecimiento
    """
    from app.db.session import get_sync_session
    from app.models.cve_cache import CVECache
    
    logger.info(f"Enriching {len(cve_ids)} CVEs with EPSS data")
    
    stats = {
        "total": len(cve_ids),
        "enriched": 0,
        "errors": [],
    }
    
    # EPSS API acepta hasta 30 CVEs por request
    batch_size = 30
    
    client = httpx.Client(timeout=30.0)
    
    for i in range(0, len(cve_ids), batch_size):
        batch = cve_ids[i:i + batch_size]
        cve_param = ",".join(batch)
        
        try:
            response = client.get(f"{EPSS_API_URL}?cve={cve_param}")
            response.raise_for_status()
            data = response.json()
            
            epss_data = {item["cve"]: item for item in data.get("data", [])}
            
            with get_sync_session() as session:
                for cve_id in batch:
                    if cve_id in epss_data:
                        epss_info = epss_data[cve_id]
                        
                        cve = session.query(CVECache).filter(
                            CVECache.cve_id == cve_id
                        ).first()
                        
                        if cve:
                            cve.epss_score = float(epss_info.get("epss", 0))
                            cve.epss_percentile = float(epss_info.get("percentile", 0))
                            stats["enriched"] += 1
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Error fetching EPSS data: {e}")
            stats["errors"].append(str(e))
        
        # Small delay between batches
        sleep(0.5)
    
    logger.info(f"EPSS enrichment completed: {stats}")
    return stats


# =============================================================================
# CISA KEV Sync Task
# =============================================================================
@celery_app.task(
    bind=True,
    name="cve.sync_cisa_kev",
)
def sync_cisa_kev(self) -> dict:
    """
    Sincroniza la lista de CISA Known Exploited Vulnerabilities (KEV).
    
    KEV es una lista de CVEs que están siendo activamente explotados
    y que requieren remediación prioritaria.
    
    Returns:
        dict con estadísticas de sincronización
    """
    from app.db.session import get_sync_session
    from app.models.cve_cache import CVECache
    
    logger.info("Syncing CISA KEV catalog")
    
    stats = {
        "total_kev": 0,
        "updated": 0,
        "not_in_cache": 0,
        "errors": [],
    }
    
    client = httpx.Client(timeout=60.0)
    
    try:
        response = client.get(CISA_KEV_URL)
        response.raise_for_status()
        data = response.json()
        
        vulnerabilities = data.get("vulnerabilities", [])
        stats["total_kev"] = len(vulnerabilities)
        
        logger.info(f"Found {stats['total_kev']} CVEs in CISA KEV catalog")
        
        with get_sync_session() as session:
            for vuln in vulnerabilities:
                cve_id = vuln.get("cveID")
                
                if not cve_id:
                    continue
                
                cve = session.query(CVECache).filter(
                    CVECache.cve_id == cve_id
                ).first()
                
                if cve:
                    cve.cisa_kev = True
                    cve.cisa_kev_date_added = vuln.get("dateAdded")
                    cve.cisa_kev_due_date = vuln.get("dueDate")
                    cve.exploit_available = True
                    stats["updated"] += 1
                else:
                    stats["not_in_cache"] += 1
            
            session.commit()
        
    except Exception as e:
        logger.error(f"Error syncing CISA KEV: {e}")
        stats["errors"].append(str(e))
    
    logger.info(f"CISA KEV sync completed: {stats}")
    return stats


# =============================================================================
# Scheduled Tasks
# =============================================================================
@celery_app.task(name="cve.daily_sync")
def daily_sync():
    """Tarea programada para sincronización diaria de CVEs."""
    # Sync last 7 days of CVEs
    sync_cves.delay(days_back=7)
    
    # Sync CISA KEV
    sync_cisa_kev.delay()
    
    return {"status": "scheduled"}
