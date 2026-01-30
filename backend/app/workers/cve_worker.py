# =============================================================================
# NESTSECURE - CVE Worker (Placeholder)
# =============================================================================
"""
Worker para sincronización de CVEs desde NVD.
TODO: Implementar en Día 5.
"""

from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="cve.sync_cves")
def sync_cves(self, days_back: int = 7):
    """
    Sincroniza CVEs desde NVD API.
    
    Args:
        days_back: Días hacia atrás para sincronizar
    
    Returns:
        dict con estadísticas de sincronización
    """
    # TODO: Implementar
    return {
        "status": "not_implemented",
        "message": "CVE sync will be implemented in Day 5"
    }


@celery_app.task(bind=True, name="cve.lookup_cve")
def lookup_cve(self, cve_id: str):
    """
    Busca información de un CVE específico.
    
    Args:
        cve_id: ID del CVE (ej: CVE-2024-1234)
    
    Returns:
        dict con información del CVE
    """
    # TODO: Implementar
    return {
        "status": "not_implemented",
        "cve_id": cve_id
    }