# =============================================================================
# NESTSECURE - API de OWASP ZAP
# =============================================================================
"""
Endpoints para escaneos de vulnerabilidades web con OWASP ZAP.

Endpoints:
- POST /zap/scan: Iniciar escaneo configurable
- GET /zap/scan/{task_id}: Obtener estado del escaneo
- GET /zap/scan/{task_id}/results: Obtener resultados
- GET /zap/profiles: Listar perfiles de escaneo
- POST /zap/quick: Escaneo rápido
- POST /zap/full: Escaneo completo
- POST /zap/api: Escaneo de API REST/GraphQL
- POST /zap/spa: Escaneo de Single Page Application
- GET /zap/alerts: Obtener alertas actuales
- GET /zap/version: Obtener versión y estado de ZAP
- POST /zap/clear: Limpiar sesión de ZAP
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from celery.result import AsyncResult

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.utils.logger import get_logger
from app.schemas.zap import (
    ZapScanRequest,
    ZapQuickScanRequest,
    ZapApiScanRequest,
    ZapSpaScanRequest,
    ZapScanResponse,
    ZapScanStatusResponse,
    ZapScanResultsResponse,
    ZapScanProgress,
    ZapProfileResponse,
    ZapProfilesListResponse,
    ZapAlertResponse,
    ZapAlertsSummary,
    ZapVersionResponse,
    ZapScanStatus,
    ZapScanMode,
    ZapAlertRisk,
    ZapAlertConfidence,
)
from app.workers.zap_worker import (
    zap_scan,
    zap_quick_scan,
    zap_full_scan,
    zap_api_scan,
    zap_spa_scan,
    zap_get_version,
    zap_get_alerts,
    zap_clear_session,
    zap_get_scan_policies,
)


logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _celery_status_to_zap_status(celery_status: str) -> ZapScanStatus:
    """Convertir estado de Celery a ZapScanStatus."""
    mapping = {
        "PENDING": ZapScanStatus.PENDING,
        "STARTED": ZapScanStatus.RUNNING,
        "PROGRESS": ZapScanStatus.RUNNING,
        "SUCCESS": ZapScanStatus.COMPLETED,
        "FAILURE": ZapScanStatus.FAILED,
        "REVOKED": ZapScanStatus.CANCELLED,
        "RETRY": ZapScanStatus.QUEUED,
    }
    return mapping.get(celery_status, ZapScanStatus.PENDING)


def _parse_progress(meta: dict) -> Optional[ZapScanProgress]:
    """Parsear progreso desde metadatos de Celery."""
    if not meta:
        return None
    
    return ZapScanProgress(
        phase=meta.get("phase", "unknown"),
        spider_progress=meta.get("spider_progress", 0),
        ajax_spider_progress=meta.get("ajax_spider_progress", 0),
        active_scan_progress=meta.get("active_scan_progress", 0),
        passive_scan_pending=meta.get("passive_scan_pending", 0),
        urls_found=meta.get("urls_found", 0),
        alerts_found=meta.get("alerts_found", 0),
        overall_progress=meta.get("overall_progress", 0),
        elapsed_seconds=meta.get("elapsed_seconds", 0),
    )


def _parse_alert_response(alert: dict) -> ZapAlertResponse:
    """Convertir alerta a response schema."""
    risk_value = alert.get("risk", "informational").lower()
    confidence_value = alert.get("confidence", "low").lower()
    
    # Mapear risk string a enum
    risk_mapping = {
        "informational": ZapAlertRisk.INFORMATIONAL,
        "low": ZapAlertRisk.LOW,
        "medium": ZapAlertRisk.MEDIUM,
        "high": ZapAlertRisk.HIGH,
    }
    
    # Mapear confidence string a enum
    confidence_mapping = {
        "false_positive": ZapAlertConfidence.FALSE_POSITIVE,
        "low": ZapAlertConfidence.LOW,
        "medium": ZapAlertConfidence.MEDIUM,
        "high": ZapAlertConfidence.HIGH,
        "confirmed": ZapAlertConfidence.CONFIRMED,
    }
    
    return ZapAlertResponse(
        id=str(alert.get("id", "")),
        name=alert.get("name", "Unknown"),
        risk=risk_mapping.get(risk_value, ZapAlertRisk.INFORMATIONAL),
        confidence=confidence_mapping.get(confidence_value, ZapAlertConfidence.LOW),
        url=alert.get("url", ""),
        method=alert.get("method", "GET"),
        param=alert.get("param"),
        attack=alert.get("attack"),
        evidence=alert.get("evidence"),
        description=alert.get("description", ""),
        solution=alert.get("solution", ""),
        reference=alert.get("reference"),
        cwe_id=alert.get("cwe_id"),
        wasc_id=alert.get("wasc_id"),
        owasp_top_10=alert.get("owasp_top_10"),
        plugin_id=alert.get("plugin_id", 0),
    )


# =============================================================================
# ENDPOINTS - SCAN LIFECYCLE
# =============================================================================

@router.post(
    "/scan",
    response_model=ZapScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar escaneo ZAP",
    description="Inicia un escaneo de vulnerabilidades web con OWASP ZAP."
)
async def start_zap_scan(
    request: ZapScanRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Iniciar un escaneo ZAP.
    
    Modos disponibles:
    - **quick**: Spider + Passive Scan (5 minutos)
    - **standard**: Spider + Passive + Active Scan (30 minutos)
    - **full**: Spider + Ajax Spider + Active Scan completo (1 hora)
    - **api**: Escaneo de API REST/GraphQL (30 minutos)
    - **passive**: Solo análisis pasivo (10 minutos)
    - **spa**: Single Page Application con Ajax Spider (40 minutos)
    """
    logger.info(
        f"Usuario {current_user.email} iniciando escaneo ZAP: "
        f"{request.target_url} (modo: {request.mode})"
    )
    
    # Validar URL
    if not request.target_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL debe comenzar con http:// o https://"
        )
    
    # Iniciar tarea Celery
    task = zap_scan.delay(
        target_url=request.target_url,
        mode=request.mode.value,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        asset_id=str(request.asset_id) if request.asset_id else None,
        include_patterns=request.include_patterns,
        exclude_patterns=request.exclude_patterns,
        timeout=request.timeout,
    )
    
    return ZapScanResponse(
        task_id=task.id,
        target_url=request.target_url,
        mode=request.mode,
        status=ZapScanStatus.PENDING,
        message="Escaneo ZAP iniciado correctamente",
    )


@router.get(
    "/scan/{task_id}",
    response_model=ZapScanStatusResponse,
    summary="Estado del escaneo",
    description="Obtiene el estado actual de un escaneo ZAP."
)
async def get_zap_scan_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Obtener estado de un escaneo ZAP."""
    result = AsyncResult(task_id)
    
    zap_status = _celery_status_to_zap_status(result.status)
    progress = None
    error = None
    started_at = None
    completed_at = None
    
    if result.status == "PROGRESS":
        progress = _parse_progress(result.info)
    elif result.status == "STARTED":
        progress = _parse_progress(result.info) if isinstance(result.info, dict) else None
    elif result.failed():
        error = str(result.result) if result.result else "Error desconocido"
    elif result.successful():
        data = result.result
        if isinstance(data, dict):
            if data.get("started_at"):
                started_at = datetime.fromisoformat(data["started_at"])
            if data.get("completed_at"):
                completed_at = datetime.fromisoformat(data["completed_at"])
    
    return ZapScanStatusResponse(
        task_id=task_id,
        status=zap_status,
        progress=progress,
        started_at=started_at,
        completed_at=completed_at,
        error=error,
    )


@router.get(
    "/scan/{task_id}/results",
    response_model=ZapScanResultsResponse,
    summary="Resultados del escaneo",
    description="Obtiene los resultados completos de un escaneo ZAP finalizado."
)
async def get_zap_scan_results(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Obtener resultados de un escaneo ZAP."""
    result = AsyncResult(task_id)
    
    if not result.ready():
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="El escaneo aún está en progreso"
        )
    
    if result.failed():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"El escaneo falló: {result.result}"
        )
    
    data = result.result
    
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Formato de resultado inválido"
        )
    
    # Parsear alertas
    alerts = [
        _parse_alert_response(a)
        for a in data.get("alerts", [])
    ]
    
    # Construir summary
    summary_data = data.get("alerts_summary", {})
    alerts_summary = ZapAlertsSummary(
        informational=summary_data.get("info", 0),
        low=summary_data.get("low", 0),
        medium=summary_data.get("medium", 0),
        high=summary_data.get("high", 0),
        total=summary_data.get("total", len(alerts)),
    )
    
    return ZapScanResultsResponse(
        task_id=task_id,
        target_url=data.get("target_url", ""),
        mode=ZapScanMode(data.get("mode", "standard")),
        status=ZapScanStatus.COMPLETED if data.get("success") else ZapScanStatus.FAILED,
        success=data.get("success", False),
        started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else datetime.now(timezone.utc),
        completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else datetime.now(timezone.utc),
        duration_seconds=data.get("duration_seconds", 0),
        urls_found=data.get("urls_found", 0),
        alerts_count=data.get("alerts_count", len(alerts)),
        alerts_summary=alerts_summary,
        alerts=alerts,
        errors=data.get("errors", []),
        spider_scan_id=data.get("spider_scan_id"),
        active_scan_id=data.get("active_scan_id"),
        context_name=data.get("context_name"),
    )


@router.delete(
    "/scan/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancelar escaneo",
    description="Cancela un escaneo ZAP en progreso."
)
async def cancel_zap_scan(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancelar un escaneo ZAP."""
    result = AsyncResult(task_id)
    
    if result.ready():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El escaneo ya finalizó"
        )
    
    result.revoke(terminate=True)
    logger.info(f"Escaneo ZAP {task_id} cancelado por {current_user.email}")


# =============================================================================
# ENDPOINTS - QUICK ACTIONS
# =============================================================================

@router.post(
    "/quick",
    response_model=ZapScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo rápido",
    description="Inicia un escaneo rápido (Spider + Passive Scan)."
)
async def start_quick_scan(
    request: ZapQuickScanRequest,
    current_user: User = Depends(get_current_user),
):
    """Escaneo rápido de 5 minutos."""
    if not request.target_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL debe comenzar con http:// o https://"
        )
    
    task = zap_quick_scan.delay(
        target_url=request.target_url,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        asset_id=str(request.asset_id) if request.asset_id else None,
    )
    
    return ZapScanResponse(
        task_id=task.id,
        target_url=request.target_url,
        mode=ZapScanMode.QUICK,
        status=ZapScanStatus.PENDING,
        message="Escaneo rápido ZAP iniciado",
    )


@router.post(
    "/full",
    response_model=ZapScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo completo",
    description="Inicia un escaneo completo (Spider + Ajax Spider + Active Scan)."
)
async def start_full_scan(
    request: ZapQuickScanRequest,
    current_user: User = Depends(get_current_user),
):
    """Escaneo completo de 1 hora."""
    if not request.target_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL debe comenzar con http:// o https://"
        )
    
    task = zap_full_scan.delay(
        target_url=request.target_url,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        asset_id=str(request.asset_id) if request.asset_id else None,
    )
    
    return ZapScanResponse(
        task_id=task.id,
        target_url=request.target_url,
        mode=ZapScanMode.FULL,
        status=ZapScanStatus.PENDING,
        message="Escaneo completo ZAP iniciado",
    )


@router.post(
    "/api",
    response_model=ZapScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo de API",
    description="Inicia un escaneo de API REST/GraphQL."
)
async def start_api_scan(
    request: ZapApiScanRequest,
    current_user: User = Depends(get_current_user),
):
    """Escaneo de API con soporte para OpenAPI."""
    if not request.target_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL debe comenzar con http:// o https://"
        )
    
    task = zap_api_scan.delay(
        target_url=request.target_url,
        openapi_url=request.openapi_url,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        asset_id=str(request.asset_id) if request.asset_id else None,
    )
    
    return ZapScanResponse(
        task_id=task.id,
        target_url=request.target_url,
        mode=ZapScanMode.API,
        status=ZapScanStatus.PENDING,
        message="Escaneo de API ZAP iniciado",
    )


@router.post(
    "/spa",
    response_model=ZapScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo de SPA",
    description="Inicia un escaneo de Single Page Application con Ajax Spider."
)
async def start_spa_scan(
    request: ZapSpaScanRequest,
    current_user: User = Depends(get_current_user),
):
    """Escaneo de SPA con Ajax Spider."""
    if not request.target_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL debe comenzar con http:// o https://"
        )
    
    task = zap_spa_scan.delay(
        target_url=request.target_url,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        asset_id=str(request.asset_id) if request.asset_id else None,
    )
    
    return ZapScanResponse(
        task_id=task.id,
        target_url=request.target_url,
        mode=ZapScanMode.SPA,
        status=ZapScanStatus.PENDING,
        message="Escaneo de SPA ZAP iniciado",
    )


# =============================================================================
# ENDPOINTS - CONFIGURATION
# =============================================================================

@router.get(
    "/profiles",
    response_model=ZapProfilesListResponse,
    summary="Perfiles de escaneo",
    description="Lista los perfiles de escaneo disponibles."
)
async def list_scan_profiles(
    current_user: User = Depends(get_current_user),
):
    """Listar perfiles de escaneo disponibles."""
    result = zap_get_scan_policies()
    policies = result.get("policies", [])
    
    profiles = [
        ZapProfileResponse(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            spider=p.get("spider", True),
            ajax_spider=p.get("ajax_spider", False),
            active_scan=p.get("active_scan", True),
            api_scan=p.get("api_scan", False),
            timeout=p.get("timeout", 1800),
        )
        for p in policies
    ]
    
    return ZapProfilesListResponse(
        profiles=profiles,
        total=len(profiles),
    )


@router.get(
    "/version",
    response_model=ZapVersionResponse,
    summary="Versión de ZAP",
    description="Obtiene la versión y estado de conexión con ZAP."
)
async def get_zap_version(
    current_user: User = Depends(get_current_user),
):
    """Obtener versión y estado de ZAP."""
    result = zap_get_version()
    
    return ZapVersionResponse(
        version=result.get("version", "unknown"),
        available=result.get("available", False),
        host=result.get("host", ""),
        port=result.get("port", 8080),
    )


# =============================================================================
# ENDPOINTS - ALERTS
# =============================================================================

@router.get(
    "/alerts",
    response_model=List[ZapAlertResponse],
    summary="Alertas actuales",
    description="Obtiene las alertas actuales en la sesión de ZAP."
)
async def get_current_alerts(
    base_url: Optional[str] = Query(None, description="Filtrar por URL base"),
    risk: Optional[int] = Query(None, ge=0, le=3, description="Filtrar por nivel de riesgo (0-3)"),
    start: int = Query(0, ge=0, description="Índice de inicio"),
    count: int = Query(100, ge=1, le=500, description="Número de alertas"),
    current_user: User = Depends(get_current_user),
):
    """Obtener alertas de la sesión actual de ZAP."""
    result = zap_get_alerts(
        base_url=base_url,
        risk_id=risk,
        start=start,
        count=count,
    )
    
    alerts = result.get("alerts", [])
    return [_parse_alert_response(a) for a in alerts]


@router.get(
    "/alerts/summary",
    response_model=ZapAlertsSummary,
    summary="Resumen de alertas",
    description="Obtiene un resumen de alertas por nivel de riesgo."
)
async def get_alerts_summary(
    base_url: Optional[str] = Query(None, description="Filtrar por URL base"),
    current_user: User = Depends(get_current_user),
):
    """Obtener resumen de alertas."""
    result = zap_get_alerts(base_url=base_url)
    summary = result.get("summary", {})
    
    # El summary de ZAP viene en formato diferente
    if isinstance(summary, dict) and "alertsSummary" in summary:
        summary_data = summary["alertsSummary"]
    else:
        summary_data = summary
    
    return ZapAlertsSummary(
        informational=summary_data.get("Informational", 0),
        low=summary_data.get("Low", 0),
        medium=summary_data.get("Medium", 0),
        high=summary_data.get("High", 0),
        total=result.get("total", 0),
    )


# =============================================================================
# ENDPOINTS - SESSION MANAGEMENT
# =============================================================================

@router.post(
    "/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Limpiar sesión",
    description="Limpia la sesión actual de ZAP (elimina todas las alertas y URLs)."
)
async def clear_zap_session(
    current_user: User = Depends(get_current_user),
):
    """Limpiar sesión de ZAP."""
    result = zap_clear_session()
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo limpiar la sesión de ZAP"
        )
    
    logger.info(f"Sesión ZAP limpiada por {current_user.email}")
