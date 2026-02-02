# =============================================================================
# NESTSECURE - Módulo de Workers
# =============================================================================
"""
Workers de Celery para tareas asíncronas.

Workers implementados:
- nmap_worker: Escaneo de red con Nmap
- cve_worker: Enriquecimiento CVE desde NVD
- report_worker: Generación de reportes
- cleanup_worker: Limpieza de datos antiguos

Workers pendientes (Fase 2):
- openvas_worker: Escaneo de vulnerabilidades con OpenVAS
- nuclei_worker: Escaneo con templates Nuclei
- zap_worker: Escaneo web con OWASP ZAP
"""

from .celery_app import celery_app

__all__ = ["celery_app"]
