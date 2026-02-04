# =============================================================================
# NESTSECURE - API de Nuclei
# =============================================================================
"""
Endpoints para escaneos de vulnerabilidades con Nuclei.

Endpoints:
- POST /nuclei/scan: Iniciar escaneo con perfil configurable
- GET /nuclei/scan/{task_id}: Obtener estado del escaneo
- GET /nuclei/scan/{task_id}/results: Obtener resultados
- GET /nuclei/profiles: Listar perfiles disponibles
- POST /nuclei/quick: Escaneo rápido de vulnerabilidades críticas
- POST /nuclei/cve: Escaneo enfocado en CVEs
- POST /nuclei/web: Escaneo de vulnerabilidades web
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from celery.result import AsyncResult
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.vulnerability import Vulnerability, VulnerabilitySeverity
from app.utils.logger import get_logger
from app.schemas.nuclei import (
    NucleiScanRequest,
    NucleiQuickScanRequest,
    NucleiCVEScanRequest,
    NucleiWebScanRequest,
    NucleiScanResponse,
    NucleiScanStatusResponse,
    NucleiScanResultsResponse,
    NucleiProfileResponse,
    NucleiProfilesListResponse,
    NucleiFindingResponse,
    NucleiSeveritySummary,
    NucleiScanStatus,
    NucleiSeverity,
    NucleiScanListResponse,
    NucleiScanListItem,
)
from app.workers.nuclei_worker import (
    nuclei_scan,
    nuclei_quick_scan,
    nuclei_cve_scan,
    nuclei_web_scan,
    nuclei_get_available_profiles,
)
from app.integrations.nuclei import (
    SCAN_PROFILES,
    get_all_profiles,
)


logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _celery_status_to_nuclei_status(celery_status: str) -> NucleiScanStatus:
    """Convertir estado de Celery a NucleiScanStatus."""
    mapping = {
        "PENDING": NucleiScanStatus.PENDING,
        "STARTED": NucleiScanStatus.RUNNING,
        "SUCCESS": NucleiScanStatus.COMPLETED,
        "FAILURE": NucleiScanStatus.FAILED,
        "REVOKED": NucleiScanStatus.CANCELLED,
        "RETRY": NucleiScanStatus.QUEUED,
    }
    return mapping.get(celery_status, NucleiScanStatus.PENDING)


def _build_severity_summary(findings: List[dict]) -> NucleiSeveritySummary:
    """Construir resumen de severidades desde findings."""
    summary = NucleiSeveritySummary()
    for finding in findings:
        severity = finding.get("severity", "info").lower()
        if severity == "critical":
            summary.critical += 1
        elif severity == "high":
            summary.high += 1
        elif severity == "medium":
            summary.medium += 1
        elif severity == "low":
            summary.low += 1
        else:
            summary.info += 1
    summary.total = len(findings)
    return summary


def _convert_finding_to_response(finding: dict) -> NucleiFindingResponse:
    """Convertir finding dict a response schema."""
    timestamp = None
    if finding.get("timestamp"):
        try:
            if isinstance(finding["timestamp"], str):
                timestamp = datetime.fromisoformat(finding["timestamp"].replace("Z", "+00:00"))
            else:
                timestamp = finding["timestamp"]
        except:
            pass
    
    return NucleiFindingResponse(
        template_id=finding.get("template_id", "unknown"),
        template_name=finding.get("template_name", finding.get("template_id", "Unknown")),
        severity=NucleiSeverity(finding.get("severity", "info").lower()),
        host=finding.get("host", ""),
        matched_at=finding.get("matched_at", ""),
        ip=finding.get("ip"),
        timestamp=timestamp,
        cve=finding.get("cve"),
        cvss=finding.get("cvss"),
        cwe_id=finding.get("cwe_id"),
        description=finding.get("description"),
        references=finding.get("references"),
        extracted=finding.get("extracted"),
        matcher_name=finding.get("matcher_name"),
    )


# =============================================================================
# ENDPOINTS - SCAN LIFECYCLE
# =============================================================================

@router.post(
    "/scan",
    response_model=NucleiScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar escaneo Nuclei",
    description="Inicia un escaneo de vulnerabilidades con Nuclei usando el perfil especificado."
)
async def start_nuclei_scan(
    request: NucleiScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Iniciar un escaneo Nuclei.
    
    El escaneo se encola en Celery y se ejecuta de forma asíncrona.
    Usa el endpoint GET /nuclei/scan/{task_id} para monitorear el progreso.
    
    Perfiles disponibles:
    - **quick**: Escaneo rápido (~5 min), solo vulnerabilidades críticas
    - **standard**: Escaneo balanceado (~30 min), mayoría de templates
    - **full**: Escaneo completo (~2+ horas), todos los templates
    - **cves**: Enfocado en detección de CVEs conocidos
    - **web**: Vulnerabilidades web (XSS, SQLi, SSRF, etc.)
    """
    logger.info(
        f"Starting Nuclei scan - user={current_user.id}, target={request.target}, profile={request.profile}"
    )
    
    # Crear registro en DB (opcional, para tracking)
    scan_id = str(uuid4()).replace("-", "")
    scan = Scan(
        id=scan_id,
        organization_id=current_user.organization_id,
        name=request.scan_name or f"Nuclei Scan - {request.target}",
        description=f"Nuclei vulnerability scan using {request.profile} profile",
        scan_type=ScanType.VULNERABILITY.value,
        targets=[request.target],
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    
    # Encolar tarea en Celery
    try:
        severities = [s.value for s in request.severities] if request.severities else None
        
        task = nuclei_scan.delay(
            target=request.target,
            profile=request.profile,
            scan_id=scan_id,
            timeout=request.timeout,
            tags=request.tags,
            severities=severities,
        )
        
        # Actualizar scan con task_id
        scan.celery_task_id = task.id
        await db.commit()
        
        logger.info(f"Nuclei scan queued - task_id={task.id}, scan_id={scan_id}")
        
        return NucleiScanResponse(
            task_id=task.id,
            scan_id=scan_id,
            status=NucleiScanStatus.QUEUED,
            target=request.target,
            profile=request.profile,
            message=f"Scan queued successfully with profile '{request.profile}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to queue Nuclei scan: {e}")
        scan.status = ScanStatus.FAILED.value
        scan.error_message = str(e)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue scan: {str(e)}"
        )


@router.get(
    "/scan/{task_id}",
    response_model=NucleiScanStatusResponse,
    summary="Obtener estado del escaneo",
    description="Obtener el estado actual de un escaneo Nuclei por su task_id."
)
async def get_nuclei_scan_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estado de un escaneo Nuclei.
    
    Estados posibles:
    - **pending**: Esperando ser procesado
    - **queued**: En cola de Celery
    - **running**: Ejecutándose
    - **completed**: Completado exitosamente
    - **failed**: Falló
    - **cancelled**: Cancelado
    - **timeout**: Excedió tiempo límite
    """
    # Consultar estado de Celery
    task_result = AsyncResult(task_id)
    celery_status = task_result.status
    
    # Buscar scan en DB por celery_task_id
    query = select(Scan).where(
        Scan.celery_task_id == task_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    scan_id = scan.id if scan else None
    target = scan.targets[0] if scan and scan.targets else "unknown"
    profile = "standard"
    
    # Determinar estado
    nuclei_status = _celery_status_to_nuclei_status(celery_status)
    
    response = NucleiScanStatusResponse(
        task_id=task_id,
        scan_id=scan_id,
        status=nuclei_status,
        target=target,
        profile=profile,
    )
    
    # Si completado, agregar resumen
    if task_result.ready() and task_result.successful():
        task_data = task_result.result
        if isinstance(task_data, dict):
            if task_data.get("status") == "completed":
                response.status = NucleiScanStatus.COMPLETED
                
                findings = task_data.get("findings", [])
                response.summary = _build_severity_summary(findings)
                response.total_findings = len(findings)
                response.unique_cves = task_data.get("unique_cves", [])
                
                # Timing
                if task_data.get("start_time"):
                    try:
                        response.started_at = datetime.fromisoformat(
                            task_data["start_time"].replace("Z", "+00:00")
                        )
                    except:
                        pass
                if task_data.get("end_time"):
                    try:
                        response.completed_at = datetime.fromisoformat(
                            task_data["end_time"].replace("Z", "+00:00")
                        )
                    except:
                        pass
                
            elif task_data.get("status") == "timeout":
                response.status = NucleiScanStatus.TIMEOUT
                response.error_message = task_data.get("error")
                
            elif task_data.get("status") == "error":
                response.status = NucleiScanStatus.FAILED
                response.error_message = task_data.get("error")
    
    elif task_result.failed():
        response.status = NucleiScanStatus.FAILED
        response.error_message = str(task_result.result) if task_result.result else "Unknown error"
    
    return response


@router.get(
    "/scan/{task_id}/results",
    response_model=NucleiScanResultsResponse,
    summary="Obtener resultados del escaneo",
    description="Obtener los resultados completos de un escaneo Nuclei."
)
async def get_nuclei_scan_results(
    task_id: str,
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(50, ge=1, le=200, description="Items por página"),
    severity: Optional[NucleiSeverity] = Query(None, description="Filtrar por severidad"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener resultados de un escaneo Nuclei.
    
    Solo disponible cuando el escaneo está completado.
    Soporta paginación y filtrado por severidad.
    """
    # Consultar resultado de Celery
    task_result = AsyncResult(task_id)
    
    if not task_result.ready():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scan is not completed yet. Check status first."
        )
    
    if task_result.failed():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scan failed: {str(task_result.result)}"
        )
    
    task_data = task_result.result
    if not isinstance(task_data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid scan result format"
        )
    
    if task_data.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scan status: {task_data.get('status', 'unknown')}"
        )
    
    # Obtener findings
    findings = task_data.get("findings", [])
    
    # Filtrar por severidad si se especifica
    if severity:
        findings = [f for f in findings if f.get("severity", "").lower() == severity.value]
    
    # Paginación
    total = len(findings)
    total_pages = (total + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_findings = findings[start_idx:end_idx]
    
    # Buscar scan en DB
    query = select(Scan).where(
        Scan.celery_task_id == task_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    return NucleiScanResultsResponse(
        task_id=task_id,
        scan_id=scan.id if scan else None,
        status=NucleiScanStatus.COMPLETED,
        target=task_data.get("targets", ["unknown"])[0] if task_data.get("targets") else "unknown",
        profile=task_data.get("profile"),
        started_at=datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00")) 
            if task_data.get("start_time") else None,
        completed_at=datetime.fromisoformat(task_data["end_time"].replace("Z", "+00:00"))
            if task_data.get("end_time") else None,
        summary=_build_severity_summary(task_data.get("findings", [])),
        findings=[_convert_finding_to_response(f) for f in paginated_findings],
        total_findings=total,
        unique_cves=task_data.get("unique_cves", []),
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# ENDPOINTS - QUICK SCANS
# =============================================================================

@router.post(
    "/quick",
    response_model=NucleiScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo rápido",
    description="Escaneo rápido de vulnerabilidades críticas (~5 minutos)."
)
async def quick_nuclei_scan(
    request: NucleiQuickScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Escaneo rápido Nuclei.
    
    Usa el perfil 'quick' que solo busca vulnerabilidades críticas y de alto impacto.
    Ideal para validaciones rápidas.
    """
    logger.info(f"Starting quick Nuclei scan - target={request.target}")
    
    # Crear registro en DB
    scan_id = str(uuid4()).replace("-", "")
    scan = Scan(
        id=scan_id,
        organization_id=current_user.organization_id,
        name=request.scan_name or f"Quick Nuclei Scan - {request.target}",
        description="Quick scan for critical vulnerabilities",
        scan_type=ScanType.VULNERABILITY.value,
        targets=[request.target],
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    
    # Encolar
    task = nuclei_quick_scan.delay(target=request.target, scan_id=scan_id)
    
    scan.celery_task_id = task.id
    await db.commit()
    
    return NucleiScanResponse(
        task_id=task.id,
        scan_id=scan_id,
        status=NucleiScanStatus.QUEUED,
        target=request.target,
        profile="quick",
        message="Quick scan queued successfully"
    )


@router.post(
    "/cve",
    response_model=NucleiScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo de CVEs",
    description="Escaneo enfocado en detección de CVEs conocidos."
)
async def cve_nuclei_scan(
    request: NucleiCVEScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Escaneo de CVEs con Nuclei.
    
    Usa templates específicos para detección de CVEs conocidos.
    Incluye CVEs de alto impacto como Log4Shell, ProxyShell, etc.
    """
    logger.info(f"Starting CVE Nuclei scan - target={request.target}")
    
    scan_id = str(uuid4()).replace("-", "")
    scan = Scan(
        id=scan_id,
        organization_id=current_user.organization_id,
        name=request.scan_name or f"CVE Nuclei Scan - {request.target}",
        description="CVE-focused vulnerability scan",
        scan_type=ScanType.VULNERABILITY.value,
        targets=[request.target],
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    
    task = nuclei_cve_scan.delay(target=request.target, scan_id=scan_id)
    
    scan.celery_task_id = task.id
    await db.commit()
    
    return NucleiScanResponse(
        task_id=task.id,
        scan_id=scan_id,
        status=NucleiScanStatus.QUEUED,
        target=request.target,
        profile="cves",
        message="CVE scan queued successfully"
    )


@router.post(
    "/web",
    response_model=NucleiScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo web",
    description="Escaneo de vulnerabilidades web (XSS, SQLi, SSRF, etc.)."
)
async def web_nuclei_scan(
    request: NucleiWebScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Escaneo web con Nuclei.
    
    Enfocado en vulnerabilidades web:
    - XSS (Cross-Site Scripting)
    - SQL Injection
    - SSRF (Server-Side Request Forgery)
    - File Inclusion
    - Open Redirect
    - Y más...
    """
    logger.info(f"Starting web Nuclei scan - target={request.target}")
    
    scan_id = str(uuid4()).replace("-", "")
    scan = Scan(
        id=scan_id,
        organization_id=current_user.organization_id,
        name=request.scan_name or f"Web Nuclei Scan - {request.target}",
        description="Web vulnerability scan",
        scan_type=ScanType.VULNERABILITY.value,
        targets=[request.target],
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    
    task = nuclei_web_scan.delay(target=request.target, scan_id=scan_id)
    
    scan.celery_task_id = task.id
    await db.commit()
    
    return NucleiScanResponse(
        task_id=task.id,
        scan_id=scan_id,
        status=NucleiScanStatus.QUEUED,
        target=request.target,
        profile="web",
        message="Web scan queued successfully"
    )


# =============================================================================
# ENDPOINTS - PROFILES
# =============================================================================

@router.get(
    "/profiles",
    response_model=NucleiProfilesListResponse,
    summary="Listar perfiles de escaneo",
    description="Obtener lista de perfiles de escaneo Nuclei disponibles."
)
async def list_nuclei_profiles(
    current_user: User = Depends(get_current_user),
):
    """
    Listar perfiles de escaneo Nuclei disponibles.
    
    Cada perfil tiene diferentes configuraciones de:
    - Templates incluidos
    - Severidades
    - Velocidad
    - Tiempo estimado
    """
    profiles = get_all_profiles()
    
    profile_responses = []
    for profile in profiles:
        profile_dict = profile.to_dict()
        profile_responses.append(NucleiProfileResponse(
            name=profile_dict.get("name", "unknown"),
            display_name=profile_dict.get("display_name", profile_dict.get("name", "Unknown")),
            description=profile_dict.get("description", ""),
            tags=profile_dict.get("tags", []),
            severities=profile_dict.get("severities", []),
            template_types=profile_dict.get("template_types", []),
            speed=profile_dict.get("speed", "normal"),
            estimated_duration=profile_dict.get("estimated_duration"),
            recommended_for=profile_dict.get("recommended_for"),
        ))
    
    return NucleiProfilesListResponse(
        profiles=profile_responses,
        total=len(profile_responses),
        default_profile="standard"
    )


@router.get(
    "/profiles/{profile_name}",
    response_model=NucleiProfileResponse,
    summary="Obtener perfil específico",
    description="Obtener detalles de un perfil de escaneo específico."
)
async def get_nuclei_profile(
    profile_name: str,
    current_user: User = Depends(get_current_user),
):
    """Obtener información de un perfil específico."""
    if profile_name not in SCAN_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_name}' not found. Available: {list(SCAN_PROFILES.keys())}"
        )
    
    profile = SCAN_PROFILES[profile_name]
    profile_dict = profile.to_dict()
    
    return NucleiProfileResponse(
        name=profile_dict.get("name", profile_name),
        display_name=profile_dict.get("display_name", profile_name.title()),
        description=profile_dict.get("description", ""),
        tags=profile_dict.get("tags", []),
        severities=profile_dict.get("severities", []),
        template_types=profile_dict.get("template_types", []),
        speed=profile_dict.get("speed", "normal"),
        estimated_duration=profile_dict.get("estimated_duration"),
        recommended_for=profile_dict.get("recommended_for"),
    )


# =============================================================================
# ENDPOINTS - SCAN HISTORY (Bonus)
# =============================================================================

@router.get(
    "/scans",
    response_model=NucleiScanListResponse,
    summary="Listar historial de escaneos",
    description="Listar escaneos Nuclei realizados por la organización."
)
async def list_nuclei_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[NucleiScanStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar historial de escaneos Nuclei.
    
    Muestra escaneos realizados por la organización con paginación.
    """
    # Query base - solo scans de tipo vulnerabilidad con descripción de Nuclei
    query = select(Scan).where(
        Scan.organization_id == current_user.organization_id,
        Scan.description.ilike("%nuclei%"),
    )
    
    count_query = select(func.count(Scan.id)).where(
        Scan.organization_id == current_user.organization_id,
        Scan.description.ilike("%nuclei%"),
    )
    
    # Filtro por estado
    if status_filter:
        status_value = status_filter.value
        query = query.where(Scan.status == status_value)
        count_query = count_query.where(Scan.status == status_value)
    
    # Total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginación
    offset = (page - 1) * page_size
    query = query.order_by(desc(Scan.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    scans = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size
    
    items = []
    for scan in scans:
        items.append(NucleiScanListItem(
            task_id=scan.celery_task_id or "",
            scan_id=scan.id,
            target=scan.targets[0] if scan.targets else "unknown",
            profile="standard",  # Could be extracted from description
            status=NucleiScanStatus(scan.status) if scan.status in [s.value for s in NucleiScanStatus] else NucleiScanStatus.PENDING,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            total_findings=scan.total_vulnerabilities or 0,
            critical_count=scan.vuln_critical or 0,
            high_count=scan.vuln_high or 0,
        ))
    
    return NucleiScanListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
