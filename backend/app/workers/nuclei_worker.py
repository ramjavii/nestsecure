# =============================================================================
# NESTSECURE - Worker de Nuclei
# =============================================================================
"""
Worker de Celery para integración con Nuclei.

Este módulo proporciona tareas asíncronas para ejecutar escaneos
de vulnerabilidades con Nuclei.

Tareas disponibles:
- nuclei_scan: Escaneo con perfil específico
- nuclei_quick_scan: Escaneo rápido de vulnerabilidades críticas
- nuclei_cve_scan: Escaneo enfocado en CVEs
- nuclei_web_scan: Escaneo de vulnerabilidades web
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.models.vulnerability import Vulnerability, VulnerabilitySeverity, VulnerabilityStatus
from app.models.scan import Scan, ScanStatus
from app.integrations.nuclei import (
    NucleiScanner,
    NucleiScanResult,
    NucleiFinding,
    get_profile,
    SCAN_PROFILES,
    NucleiError,
    NucleiTimeoutError,
    NucleiNotFoundError,
)


logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

def _should_use_mock() -> bool:
    """Determinar si usar modo mock."""
    if getattr(settings, "NUCLEI_MOCK_MODE", False):
        return True
    
    try:
        from app.integrations.nuclei import check_nuclei_installed
        return not check_nuclei_installed()
    except:
        return True


MOCK_MODE = _should_use_mock()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _run_async(coro):
    """Ejecutar coroutine en contexto síncrono de Celery."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _convert_finding_to_dict(finding: NucleiFinding) -> Dict[str, Any]:
    """Convertir NucleiFinding a diccionario."""
    return {
        "template_id": finding.template.id,
        "template_name": finding.template.name,
        "severity": finding.severity.value,
        "host": finding.host,
        "matched_at": finding.matched_at,
        "ip": finding.ip,
        "timestamp": finding.timestamp.isoformat() if finding.timestamp else None,
        "cve": finding.cve,
        "cvss": finding.cvss,
        "description": finding.template.description,
        "references": finding.template.reference,
        "tags": finding.template.tags,
        "extracted": finding.extracted,
    }


def _convert_result_to_dict(result: NucleiScanResult) -> Dict[str, Any]:
    """Convertir NucleiScanResult a diccionario."""
    return {
        "summary": result.get_summary(),
        "targets": result.targets,
        "templates_used": result.templates_used,
        "start_time": result.start_time.isoformat() if result.start_time else None,
        "end_time": result.end_time.isoformat() if result.end_time else None,
        "total_requests": result.total_requests,
        "findings": [_convert_finding_to_dict(f) for f in result.findings],
        "severity_counts": {
            "critical": result.critical_count,
            "high": result.high_count,
            "medium": result.medium_count,
            "low": result.low_count,
            "info": result.info_count,
        },
        "unique_cves": result.unique_cves,
    }


def _get_sync_db() -> Session:
    """Obtener sesión síncrona de base de datos para Celery."""
    return SessionLocal()


def _severity_to_db(severity: str) -> str:
    """Convertir severidad de Nuclei a severidad de DB."""
    mapping = {
        "critical": VulnerabilitySeverity.CRITICAL.value,
        "high": VulnerabilitySeverity.HIGH.value,
        "medium": VulnerabilitySeverity.MEDIUM.value,
        "low": VulnerabilitySeverity.LOW.value,
        "info": VulnerabilitySeverity.INFO.value,
    }
    return mapping.get(severity.lower(), VulnerabilitySeverity.MEDIUM.value)


def _persist_findings(
    scan_id: str,
    findings: List[Dict[str, Any]],
    organization_id: Optional[str] = None,
) -> Dict[str, int]:
    """
    Persistir findings de Nuclei en la base de datos.
    
    Args:
        scan_id: ID del scan
        findings: Lista de findings como dicts
        organization_id: ID de la organización
    
    Returns:
        dict con conteo de vulnerabilidades creadas
    """
    db = _get_sync_db()
    stats = {
        "created": 0,
        "skipped": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    }
    
    try:
        # Obtener scan para extraer organization_id y asset_id si no se provee
        scan = db.execute(
            select(Scan).where(Scan.id == scan_id)
        ).scalar_one_or_none()
        
        if not scan:
            logger.warning(f"Scan {scan_id} not found, skipping persistence")
            return stats
        
        org_id = organization_id or scan.organization_id
        
        # Necesitamos un asset para asociar las vulnerabilidades
        # Intentar obtener o crear un asset temporal basado en el target
        from app.models.asset import Asset
        
        target = scan.targets[0] if scan.targets else "unknown"
        
        # Buscar asset existente por IP o hostname
        asset = db.execute(
            select(Asset).where(
                Asset.organization_id == org_id,
                (Asset.ip_address == target) | (Asset.hostname == target)
            )
        ).scalar_one_or_none()
        
        if not asset:
            # Crear asset temporal para las vulnerabilidades
            asset = Asset(
                id=str(uuid4()).replace("-", ""),
                organization_id=org_id,
                ip_address=target if "." in target else None,
                hostname=target if "." not in target else None,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                is_reachable=True,
            )
            db.add(asset)
            db.flush()
        
        now = datetime.now(timezone.utc)
        
        for finding in findings:
            severity = finding.get("severity", "info").lower()
            template_id = finding.get("template_id", "unknown")
            
            # Verificar si ya existe esta vulnerabilidad
            existing = db.execute(
                select(Vulnerability).where(
                    Vulnerability.scan_id == scan_id,
                    Vulnerability.scanner_plugin_id == template_id,
                    Vulnerability.host == finding.get("host", "")[:500],
                )
            ).scalar_one_or_none()
            
            if existing:
                # Actualizar última detección
                existing.last_detected_at = now
                existing.times_detected += 1
                stats["skipped"] += 1
                continue
            
            # Crear nueva vulnerabilidad
            description = finding.get("description") or f"Detected by Nuclei template: {template_id}"
            
            vuln = Vulnerability(
                id=str(uuid4()).replace("-", ""),
                organization_id=org_id,
                asset_id=asset.id,
                scan_id=scan_id,
                name=finding.get("template_name", template_id)[:500],
                description=description[:2000] if description else "",
                severity=_severity_to_db(severity),
                status=VulnerabilityStatus.OPEN.value,
                host=finding.get("host", "")[:500],
                cve_id=finding.get("cve"),
                cvss_score=finding.get("cvss"),
                references=finding.get("references", []),
                scanner_name="nuclei",
                scanner_plugin_id=template_id,
                raw_output=finding,
                first_detected_at=now,
                last_detected_at=now,
            )
            
            db.add(vuln)
            stats["created"] += 1
            stats[severity] = stats.get(severity, 0) + 1
        
        # Actualizar conteos en el scan
        scan.total_vulnerabilities = stats["created"] + stats["skipped"]
        scan.vuln_critical = stats["critical"]
        scan.vuln_high = stats["high"]
        scan.vuln_medium = stats["medium"]
        scan.vuln_low = stats["low"]
        scan.vuln_info = stats.get("info", 0)
        
        db.commit()
        
        logger.info(
            f"Persisted {stats['created']} vulnerabilities for scan {scan_id} "
            f"(skipped {stats['skipped']} duplicates)"
        )
        
    except Exception as e:
        logger.exception(f"Error persisting findings: {e}")
        db.rollback()
        
    finally:
        db.close()
    
    return stats


# =============================================================================
# CELERY TASKS
# =============================================================================

@shared_task(
    bind=True,
    name="nuclei.scan",
    max_retries=2,
    soft_time_limit=7200,
    time_limit=7500,
)
def nuclei_scan(
    self,
    target: str,
    profile: str = "standard",
    scan_id: Optional[str] = None,
    timeout: int = 3600,
    tags: Optional[List[str]] = None,
    severities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Ejecutar escaneo Nuclei con perfil específico."""
    task_id = self.request.id
    logger.info(f"Starting Nuclei scan - task_id={task_id}, target={target}")
    
    try:
        scanner = NucleiScanner(mock_mode=MOCK_MODE)
        
        async def run_scan():
            return await scanner.scan(
                target=target,
                profile=profile,
                timeout=timeout,
                tags=tags,
                severities=severities,
            )
        
        result = _run_async(run_scan())
        result_dict = _convert_result_to_dict(result)
        result_dict.update({
            "task_id": task_id,
            "scan_id": scan_id,
            "profile": profile,
            "status": "completed",
        })
        
        # Persistir findings en la base de datos
        if scan_id and result_dict.get("findings"):
            persist_stats = _persist_findings(scan_id, result_dict["findings"])
            result_dict["persist_stats"] = persist_stats
        
        logger.info(f"Nuclei scan completed - findings={result.total_findings}")
        return result_dict
        
    except NucleiTimeoutError as e:
        logger.error(f"Nuclei scan timeout: {str(e)}")
        return {"task_id": task_id, "status": "timeout", "error": str(e)}
        
    except NucleiError as e:
        logger.error(f"Nuclei error: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        return {"task_id": task_id, "status": "error", "error": str(e)}
        
    except Exception as e:
        logger.exception(f"Unexpected error in Nuclei scan")
        return {"task_id": task_id, "status": "error", "error": str(e)}


@shared_task(name="nuclei.quick_scan", soft_time_limit=900, time_limit=1000)
def nuclei_quick_scan(target: str, scan_id: Optional[str] = None) -> Dict[str, Any]:
    """Escaneo rápido de vulnerabilidades críticas."""
    return nuclei_scan.apply(
        args=[target],
        kwargs={"profile": "quick", "scan_id": scan_id, "timeout": 600}
    ).get()


@shared_task(name="nuclei.cve_scan", soft_time_limit=3600, time_limit=3900)
def nuclei_cve_scan(target: str, scan_id: Optional[str] = None) -> Dict[str, Any]:
    """Escaneo enfocado en CVEs."""
    return nuclei_scan.apply(
        args=[target],
        kwargs={"profile": "cves", "scan_id": scan_id, "timeout": 3000}
    ).get()


@shared_task(name="nuclei.web_scan", soft_time_limit=3600, time_limit=3900)
def nuclei_web_scan(target: str, scan_id: Optional[str] = None) -> Dict[str, Any]:
    """Escaneo de vulnerabilidades web."""
    return nuclei_scan.apply(
        args=[target],
        kwargs={"profile": "web", "scan_id": scan_id, "timeout": 3000}
    ).get()


@shared_task(name="nuclei.update_templates", soft_time_limit=600, time_limit=660)
def nuclei_update_templates() -> Dict[str, Any]:
    """Actualizar templates de Nuclei."""
    logger.info("Updating Nuclei templates...")
    
    try:
        if MOCK_MODE:
            return {"status": "skipped", "reason": "mock_mode"}
        
        scanner = NucleiScanner(mock_mode=False)
        
        async def run_update():
            return await scanner.update_templates()
        
        success = _run_async(run_update())
        return {"status": "success" if success else "failed"}
            
    except Exception as e:
        logger.error(f"Error updating templates: {str(e)}")
        return {"status": "error", "error": str(e)}


@shared_task(name="nuclei.get_available_profiles")
def nuclei_get_available_profiles() -> List[Dict[str, Any]]:
    """Obtener lista de perfiles disponibles."""
    return [profile.to_dict() for profile in SCAN_PROFILES.values()]


__all__ = [
    "nuclei_scan",
    "nuclei_quick_scan",
    "nuclei_cve_scan",
    "nuclei_web_scan",
    "nuclei_update_templates",
    "nuclei_get_available_profiles",
]
