# =============================================================================
# NESTSECURE - API de Scans
# =============================================================================
"""
Endpoints para gestión de escaneos de seguridad.

Endpoints:
- POST /scans: Crear y ejecutar nuevo scan
- GET /scans: Listar scans de la organización
- GET /scans/{id}: Obtener detalle de scan
- GET /scans/{id}/status: Obtener estado del scan
- GET /scans/{id}/results: Obtener resultados
- POST /scans/{id}/stop: Detener scan en ejecución
- DELETE /scans/{id}: Eliminar scan
- GET /scans/nmap/profiles: Listar perfiles Nmap disponibles
- POST /scans/nmap/quick: Escaneo rápido con Nmap
- POST /scans/nmap/full: Escaneo completo con Nmap
- POST /scans/nmap/vulnerability: Escaneo de vulnerabilidades con Nmap
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, Integer, cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.vulnerability import Vulnerability
from app.models.asset import Asset
from app.models.service import Service
from app.utils.logger import get_logger
from app.utils.network_utils import validate_targets_list
from app.workers.openvas_worker import openvas_full_scan, openvas_stop_scan, openvas_check_status
from app.integrations.nmap import get_all_profiles as get_nmap_profiles, SCAN_PROFILES as NMAP_PROFILES
from app.workers.nmap_worker import (
    discovery_scan as nmap_discovery_task,
    quick_scan as nmap_quick_scan_task,
    full_scan as nmap_full_scan_task,
    vulnerability_scan as nmap_vuln_scan_task,
)

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class ScanCreate(BaseModel):
    """Schema para crear un scan."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scan_type: ScanType = ScanType.VULNERABILITY
    targets: List[str] = Field(..., min_items=1)
    excluded_targets: Optional[List[str]] = None
    port_range: Optional[str] = None


class ScanResponse(BaseModel):
    """Schema de respuesta de scan."""
    id: str
    name: str
    description: Optional[str]
    scan_type: str
    targets: List[str]
    status: str
    progress: int
    current_phase: Optional[str]
    
    total_hosts_scanned: int
    total_hosts_up: int
    total_services_found: int
    total_vulnerabilities: int
    vuln_critical: int
    vuln_high: int
    vuln_medium: int
    vuln_low: int
    
    celery_task_id: Optional[str]
    gvm_target_id: Optional[str]
    gvm_task_id: Optional[str]
    gvm_report_id: Optional[str]
    
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    error_message: Optional[str]
    
    results: Optional[dict] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanListResponse(BaseModel):
    """Respuesta paginada de scans."""
    items: List[ScanResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ScanStatusResponse(BaseModel):
    """Estado actual del scan."""
    id: str
    status: str
    progress: int
    current_phase: Optional[str]
    gvm_progress: Optional[int]
    is_running: bool
    is_done: bool
    error_message: Optional[str]


class VulnerabilitySummary(BaseModel):
    """Resumen de vulnerabilidad."""
    id: str
    name: str
    severity: str  # Severity level as string (critical, high, medium, low, info)
    cvss_score: Optional[float] = None  # Numeric CVSS score
    severity_class: str
    host: Optional[str] = None
    port: Optional[int] = None
    cve_ids: List[str] = []


class ScanResultsResponse(BaseModel):
    """Resultados del scan."""
    scan_id: str
    status: str
    summary: dict
    vulnerabilities: List[VulnerabilitySummary]
    total_vulnerabilities: int


# Schemas para hosts del scan
class ScanServiceSummary(BaseModel):
    """Resumen de servicio detectado."""
    id: str
    port: int
    protocol: str
    service_name: Optional[str]
    version: Optional[str]
    state: str


class ScanHostSummary(BaseModel):
    """Resumen de host encontrado en el scan."""
    id: str
    ip_address: str
    hostname: Optional[str]
    operating_system: Optional[str]
    status: str
    services_count: int
    vulnerabilities_count: int
    vuln_critical: int
    vuln_high: int
    services: List[ScanServiceSummary]


class ScanHostsResponse(BaseModel):
    """Response con hosts del scan."""
    scan_id: str
    total_hosts: int
    hosts: List[ScanHostSummary]


# Schemas para logs del scan
class ScanLogEntry(BaseModel):
    """Entrada de log del scan."""
    timestamp: str
    level: str
    message: str


class ScanLogsResponse(BaseModel):
    """Response con logs del scan."""
    scan_id: str
    status: str
    current_phase: Optional[str]
    logs: List[ScanLogEntry]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear y ejecutar nuevo scan",
)
async def create_scan(
    scan_data: ScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crear un nuevo scan de seguridad y ejecutarlo.
    
    El scan se encola en Celery y comienza a ejecutarse inmediatamente.
    Usa polling en GET /scans/{id}/status para monitorear el progreso.
    
    NOTA: Solo se permiten escaneos a redes privadas (RFC 1918):
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
    """
    # Validar que todos los targets sean IPs/redes privadas
    # Esto previene escaneos a IPs públicas por seguridad
    validated_targets = validate_targets_list(scan_data.targets)
    
    # Crear registro del scan con targets validados
    scan = Scan(
        id=str(uuid4()).replace("-", ""),
        organization_id=current_user.organization_id,
        name=scan_data.name,
        description=scan_data.description,
        scan_type=scan_data.scan_type.value,
        targets=validated_targets,  # Usar targets validados
        excluded_targets=scan_data.excluded_targets or [],
        port_range=scan_data.port_range,
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    
    logger.info(f"Created scan {scan.id} for targets {scan_data.targets}")
    
    # Encolar tarea de Celery según el tipo de scan
    try:
        targets_str = ",".join(scan_data.targets)
        
        # Seleccionar worker según tipo de scan
        if scan_data.scan_type == ScanType.DISCOVERY:
            # Usar Nmap para descubrimiento de hosts
            task = nmap_discovery_task.delay(
                target=targets_str,
                organization_id=str(current_user.organization_id),
                scan_id=str(scan.id),
            )
        elif scan_data.scan_type == ScanType.PORT_SCAN:
            # Usar Nmap para escaneo de puertos
            task = nmap_quick_scan_task.delay(
                target=targets_str,
                organization_id=str(current_user.organization_id),
                scan_id=str(scan.id),
            )
        elif scan_data.scan_type == ScanType.FULL:
            # Usar Nmap para escaneo completo
            task = nmap_full_scan_task.delay(
                target=targets_str,
                organization_id=str(current_user.organization_id),
                scan_id=str(scan.id),
            )
        elif scan_data.scan_type == ScanType.SERVICE_SCAN:
            # Usar Nmap con detección de servicios (-sV)
            task = nmap_quick_scan_task.delay(
                target=targets_str,
                organization_id=str(current_user.organization_id),
                scan_id=str(scan.id),
            )
        elif scan_data.scan_type == ScanType.VULNERABILITY:
            # Usar Nmap con scripts de vulnerabilidades
            task = nmap_vuln_scan_task.delay(
                target=targets_str,
                organization_id=str(current_user.organization_id),
                scan_id=str(scan.id),
            )
        else:
            # Fallback para tipos desconocidos, usar discovery
            task = nmap_discovery_task.delay(
                target=targets_str,
                organization_id=str(current_user.organization_id),
                scan_id=str(scan.id),
            )
        
        # Guardar ID de tarea Celery
        scan.celery_task_id = task.id
        scan.status = ScanStatus.QUEUED.value
        await db.commit()
        await db.refresh(scan)
        
        logger.info(f"Scan {scan.id} queued with Celery task {task.id}")
        
    except Exception as e:
        logger.error(f"Failed to queue scan {scan.id}: {e}")
        scan.status = ScanStatus.FAILED.value
        scan.error_message = f"Failed to queue: {str(e)}"
        await db.commit()
        await db.refresh(scan)
    
    return scan


@router.get(
    "",
    response_model=ScanListResponse,
    summary="Listar scans",
)
async def list_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[ScanStatus] = Query(None, alias="status"),
    scan_type_filter: Optional[ScanType] = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar todos los scans de la organización."""
    # Query base
    query = select(Scan).where(Scan.organization_id == current_user.organization_id)
    count_query = select(func.count(Scan.id)).where(Scan.organization_id == current_user.organization_id)
    
    # Filtros
    if status_filter:
        query = query.where(Scan.status == status_filter.value)
        count_query = count_query.where(Scan.status == status_filter.value)
    
    if scan_type_filter:
        query = query.where(Scan.scan_type == scan_type_filter.value)
        count_query = count_query.where(Scan.scan_type == scan_type_filter.value)
    
    # Total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginación
    offset = (page - 1) * page_size
    query = query.order_by(desc(Scan.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    scans = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size
    
    return ScanListResponse(
        items=[ScanResponse.model_validate(s) for s in scans],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{scan_id}",
    response_model=ScanResponse,
    summary="Obtener detalle de scan",
)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener detalle completo de un scan."""
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return scan


@router.get(
    "/{scan_id}/status",
    response_model=ScanStatusResponse,
    summary="Obtener estado del scan",
)
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estado actual del scan.
    
    Usa este endpoint para polling durante la ejecución del scan.
    """
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Si hay un task de GVM activo, consultar estado real
    gvm_progress = None
    if scan.gvm_task_id and scan.status == ScanStatus.RUNNING.value:
        try:
            gvm_status = openvas_check_status.delay(scan.gvm_task_id).get(timeout=10)
            gvm_progress = gvm_status.get("progress")
        except Exception:
            pass  # Si falla, usar datos locales
    
    is_running = scan.status in [ScanStatus.RUNNING.value, ScanStatus.QUEUED.value]
    is_done = scan.status in [ScanStatus.COMPLETED.value, ScanStatus.FAILED.value, ScanStatus.CANCELLED.value]
    
    return ScanStatusResponse(
        id=scan.id,
        status=scan.status,
        progress=scan.progress,
        current_phase=scan.current_phase,
        gvm_progress=gvm_progress,
        is_running=is_running,
        is_done=is_done,
        error_message=scan.error_message,
    )


@router.get(
    "/{scan_id}/results",
    response_model=ScanResultsResponse,
    summary="Obtener resultados del scan",
)
async def get_scan_results(
    scan_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    min_severity: Optional[float] = Query(None, ge=0, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener vulnerabilidades encontradas en el scan."""
    # Verificar scan existe
    scan_query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    scan_result = await db.execute(scan_query)
    scan = scan_result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Query vulnerabilidades
    vuln_query = select(Vulnerability).where(Vulnerability.scan_id == scan_id)
    count_query = select(func.count(Vulnerability.id)).where(Vulnerability.scan_id == scan_id)
    
    if min_severity is not None:
        vuln_query = vuln_query.where(Vulnerability.severity >= min_severity)
        count_query = count_query.where(Vulnerability.severity >= min_severity)
    
    # Total
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginación
    offset = (page - 1) * page_size
    vuln_query = vuln_query.order_by(desc(Vulnerability.severity)).offset(offset).limit(page_size)
    
    vuln_result = await db.execute(vuln_query)
    vulns = vuln_result.scalars().all()
    
    vulnerabilities = [
        VulnerabilitySummary(
            id=v.id,
            name=v.name,
            severity=v.severity,
            cvss_score=v.cvss_score,
            severity_class=v.severity_class,
            host=v.host,
            port=v.port,
            cve_ids=v.cve_ids or [],
        )
        for v in vulns
    ]
    
    summary = {
        "total": scan.total_vulnerabilities,
        "critical": scan.vuln_critical,
        "high": scan.vuln_high,
        "medium": scan.vuln_medium,
        "low": scan.vuln_low,
        "info": scan.vuln_info,
        "hosts_scanned": scan.total_hosts_scanned,
        "hosts_up": scan.total_hosts_up,
    }
    
    return ScanResultsResponse(
        scan_id=scan.id,
        status=scan.status,
        summary=summary,
        vulnerabilities=vulnerabilities,
        total_vulnerabilities=total,
    )


@router.get(
    "/{scan_id}/hosts",
    response_model=ScanHostsResponse,
    summary="Obtener hosts descubiertos en el scan",
)
async def get_scan_hosts(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener lista de hosts/assets descubiertos o escaneados.
    
    Incluye servicios detectados y conteo de vulnerabilidades por host.
    """
    # Verificar scan existe
    scan_query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    scan_result = await db.execute(scan_query)
    scan = scan_result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    hosts = []
    
    # Obtener assets basándose en los targets del scan
    # Los targets pueden ser IPs individuales o rangos CIDR
    if scan.targets:
        for target in scan.targets:
            # Buscar asset por IP
            asset_query = select(Asset).where(
                Asset.organization_id == current_user.organization_id,
                Asset.ip_address == target,
            )
            asset_result = await db.execute(asset_query)
            asset = asset_result.scalar_one_or_none()
            
            if asset:
                # Contar vulnerabilidades por asset en este scan
                vuln_count_query = select(
                    func.count(Vulnerability.id),
                    func.sum(func.cast(Vulnerability.severity == 'critical', Integer)),
                    func.sum(func.cast(Vulnerability.severity == 'high', Integer)),
                ).where(
                    Vulnerability.scan_id == scan_id,
                    Vulnerability.asset_id == asset.id,
                )
                counts = await db.execute(vuln_count_query)
                row = counts.first()
                vuln_total = row[0] if row else 0
                vuln_crit = row[1] if row else 0
                vuln_high = row[2] if row else 0
                
                # Obtener servicios del asset
                service_query = select(Service).where(Service.asset_id == asset.id)
                service_result = await db.execute(service_query)
                services = service_result.scalars().all()
                
                service_summaries = [
                    ScanServiceSummary(
                        id=s.id,
                        port=s.port,
                        protocol=s.protocol,
                        service_name=s.service_name,
                        version=s.version,
                        state=s.state,
                    )
                    for s in services
                ]
                
                hosts.append(ScanHostSummary(
                    id=asset.id,
                    ip_address=str(asset.ip_address),
                    hostname=asset.hostname,
                    operating_system=asset.operating_system,
                    status=asset.status,
                    services_count=len(services),
                    vulnerabilities_count=vuln_total or 0,
                    vuln_critical=vuln_crit or 0,
                    vuln_high=vuln_high or 0,
                    services=service_summaries,
                ))
    
    # También incluir hosts de scan.results si existe
    if scan.results and isinstance(scan.results, dict):
        results_services = scan.results.get("services", [])
        results_hosts = scan.results.get("hosts", [])
        
        # Si no encontramos assets en DB pero hay hosts en results, usar esos
        if not hosts and results_hosts:
            for i, host_data in enumerate(results_hosts):
                ip = host_data.get("ip_address", "")
                hosts.append(ScanHostSummary(
                    id=f"temp-{i}",  # ID temporal para hosts no persistidos
                    ip_address=ip,
                    hostname=host_data.get("hostname"),
                    operating_system=None,
                    status="active",
                    services_count=0,
                    vulnerabilities_count=0,
                    vuln_critical=0,
                    vuln_high=0,
                    services=[],
                ))
        
        # Si no hay hosts pero hay servicios, crear hosts desde servicios
        if not hosts and results_services:
            # Agrupar servicios por IP
            services_by_host: dict = {}
            for svc in results_services:
                host_ip = svc.get("host") or svc.get("ip_address") or (scan.targets[0] if scan.targets else "unknown")
                if host_ip not in services_by_host:
                    services_by_host[host_ip] = []
                services_by_host[host_ip].append(svc)
            
            for i, (host_ip, svcs) in enumerate(services_by_host.items()):
                service_summaries = [
                    ScanServiceSummary(
                        id=f"temp-svc-{i}-{j}",
                        port=s.get("port", 0),
                        protocol=s.get("protocol", "tcp"),
                        service_name=s.get("service_name") or s.get("name"),
                        version=s.get("version"),
                        state=s.get("state", "open"),
                    )
                    for j, s in enumerate(svcs)
                ]
                
                hosts.append(ScanHostSummary(
                    id=f"temp-host-{i}",
                    ip_address=str(host_ip),
                    hostname=None,
                    operating_system=None,
                    status="active",
                    services_count=len(svcs),
                    vulnerabilities_count=0,
                    vuln_critical=0,
                    vuln_high=0,
                    services=service_summaries,
                ))
            
            # Actualizar total_services_found si es diferente
            if scan.total_services_found != len(results_services):
                scan.total_services_found = len(results_services)
                await db.commit()
    
    return ScanHostsResponse(
        scan_id=scan.id,
        total_hosts=len(hosts),
        hosts=hosts,
    )


@router.get(
    "/{scan_id}/logs",
    response_model=ScanLogsResponse,
    summary="Obtener logs del scan",
)
async def get_scan_logs(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener historial de logs/eventos del scan.
    
    Útil para monitorear el progreso y depurar problemas.
    """
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Convertir logs a formato de respuesta
    log_entries = []
    if scan.logs:
        for log in scan.logs:
            log_entries.append(ScanLogEntry(
                timestamp=log.get("timestamp", ""),
                level=log.get("level", "info"),
                message=log.get("message", ""),
            ))
    
    # Si no hay logs, generar logs básicos del estado
    if not log_entries:
        if scan.created_at:
            log_entries.append(ScanLogEntry(
                timestamp=scan.created_at.isoformat() if hasattr(scan.created_at, 'isoformat') else str(scan.created_at),
                level="info",
                message=f"Scan '{scan.name}' creado con targets: {', '.join(scan.targets)}",
            ))
        if scan.started_at:
            log_entries.append(ScanLogEntry(
                timestamp=scan.started_at.isoformat() if hasattr(scan.started_at, 'isoformat') else str(scan.started_at),
                level="info",
                message=f"Escaneo iniciado - Tipo: {scan.scan_type}",
            ))
        if scan.status == ScanStatus.COMPLETED.value and scan.completed_at:
            log_entries.append(ScanLogEntry(
                timestamp=scan.completed_at.isoformat() if hasattr(scan.completed_at, 'isoformat') else str(scan.completed_at),
                level="success",
                message=f"Escaneo completado - {scan.total_vulnerabilities} vulnerabilidades encontradas",
            ))
        if scan.status == ScanStatus.FAILED.value:
            log_entries.append(ScanLogEntry(
                timestamp=scan.completed_at.isoformat() if scan.completed_at and hasattr(scan.completed_at, 'isoformat') else str(scan.updated_at),
                level="error",
                message=f"Error: {scan.error_message or 'Error desconocido'}",
            ))
    
    return ScanLogsResponse(
        scan_id=scan.id,
        status=scan.status,
        current_phase=scan.current_phase,
        logs=log_entries,
    )


@router.post(
    "/{scan_id}/stop",
    response_model=ScanStatusResponse,
    summary="Detener scan en ejecución",
)
async def stop_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detener un scan que está en ejecución."""
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan.status not in [ScanStatus.RUNNING.value, ScanStatus.QUEUED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot stop scan in status: {scan.status}"
        )
    
    # Detener en GVM si hay task activo
    if scan.gvm_task_id:
        try:
            openvas_stop_scan.delay(scan.gvm_task_id)
        except Exception as e:
            logger.warning(f"Failed to stop GVM task: {e}")
    
    # Actualizar estado local
    scan.cancel()
    await db.commit()
    await db.refresh(scan)
    
    logger.info(f"Scan {scan_id} stopped by user {current_user.id}")
    
    return ScanStatusResponse(
        id=scan.id,
        status=scan.status,
        progress=scan.progress,
        current_phase=scan.current_phase,
        gvm_progress=None,
        is_running=False,
        is_done=True,
        error_message=None,
    )


@router.delete(
    "/{scan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar scan",
)
async def delete_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Eliminar un scan y todas sus vulnerabilidades asociadas.
    
    No se puede eliminar un scan en ejecución (debe detenerse primero).
    """
    query = select(Scan).where(
        Scan.id == scan_id,
        Scan.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan.status in [ScanStatus.RUNNING.value, ScanStatus.QUEUED.value]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete running scan. Stop it first."
        )
    
    await db.delete(scan)
    await db.commit()
    
    logger.info(f"Scan {scan_id} deleted by user {current_user.id}")


# =============================================================================
# NMAP ENDPOINTS - Perfiles y escaneos rápidos
# =============================================================================

class NmapProfileResponse(BaseModel):
    """Perfil de escaneo Nmap."""
    name: str = Field(..., description="Identificador del perfil")
    display_name: str = Field(..., description="Nombre para mostrar")
    description: str = Field(..., description="Descripción del perfil")
    arguments: List[str] = Field(default_factory=list, description="Argumentos de Nmap")
    intensity: str = Field(default="normal", description="Intensidad del escaneo")
    estimated_duration: Optional[str] = Field(default=None, description="Duración estimada")
    ports: Optional[str] = Field(default=None, description="Puertos a escanear")


class NmapScanRequest(BaseModel):
    """Request para escaneo Nmap."""
    target: str = Field(..., min_length=1, max_length=2048)
    scan_name: Optional[str] = Field(default=None, max_length=255)


class NmapScanResponse(BaseModel):
    """Response de escaneo Nmap."""
    task_id: str
    scan_id: Optional[str] = None
    status: str
    target: str
    profile: str
    message: Optional[str] = None


@router.get(
    "/nmap/profiles",
    response_model=List[NmapProfileResponse],
    summary="Listar perfiles Nmap",
    description="Obtener lista de perfiles de escaneo Nmap disponibles."
)
async def list_nmap_profiles(
    current_user: User = Depends(get_current_user),
):
    """
    Listar perfiles de escaneo Nmap disponibles.
    
    Cada perfil tiene diferentes configuraciones:
    - **quick**: Top 100 puertos (~2 min)
    - **standard**: Top 1000 puertos (~5 min)
    - **full**: Todos los puertos (~30+ min)
    - **stealth**: Escaneo sigiloso
    - **vulnerability**: Con scripts de vulnerabilidades
    """
    profiles = get_nmap_profiles()
    
    profile_responses = []
    for profile in profiles:
        profile_dict = profile.to_dict()
        profile_responses.append(NmapProfileResponse(
            name=profile_dict.get("name", "unknown"),
            display_name=profile_dict.get("display_name", profile_dict.get("name", "Unknown").title()),
            description=profile_dict.get("description", ""),
            arguments=profile_dict.get("arguments", []),
            intensity=profile_dict.get("intensity", "normal"),
            estimated_duration=profile_dict.get("estimated_duration"),
            ports=profile_dict.get("ports"),
        ))
    
    return profile_responses


@router.post(
    "/nmap/quick",
    response_model=NmapScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo rápido Nmap",
    description="Escaneo rápido de los top 100 puertos (~2 minutos)."
)
async def nmap_quick_scan(
    request: NmapScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Escaneo rápido con Nmap.
    
    Escanea los 100 puertos más comunes con detección de servicios básica.
    Ideal para validaciones rápidas.
    """
    logger.info(f"Starting quick Nmap scan - target={request.target}")
    
    # Crear registro en DB
    scan_id = str(uuid4()).replace("-", "")
    scan = Scan(
        id=scan_id,
        organization_id=current_user.organization_id,
        name=request.scan_name or f"Quick Nmap Scan - {request.target}",
        description="Quick scan of top 100 ports",
        scan_type=ScanType.PORT_SCAN.value,
        targets=[request.target],
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    
    # Encolar tarea
    task = nmap_quick_scan_task.delay(
        target=request.target,
        organization_id=str(current_user.organization_id),
        scan_id=scan_id,
    )
    
    scan.celery_task_id = task.id
    await db.commit()
    
    return NmapScanResponse(
        task_id=task.id,
        scan_id=scan_id,
        status="queued",
        target=request.target,
        profile="quick",
        message="Quick scan queued successfully"
    )


@router.post(
    "/nmap/full",
    response_model=NmapScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo completo Nmap",
    description="Escaneo de todos los 65535 puertos (puede tardar +30 min)."
)
async def nmap_full_scan(
    request: NmapScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Escaneo completo con Nmap.
    
    Escanea todos los 65535 puertos TCP con detección de servicios.
    ADVERTENCIA: Puede tardar más de 30 minutos.
    """
    logger.info(f"Starting full Nmap scan - target={request.target}")
    
    scan_id = str(uuid4()).replace("-", "")
    scan = Scan(
        id=scan_id,
        organization_id=current_user.organization_id,
        name=request.scan_name or f"Full Nmap Scan - {request.target}",
        description="Full scan of all 65535 ports",
        scan_type=ScanType.FULL.value,
        targets=[request.target],
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    
    task = nmap_full_scan_task.delay(
        target=request.target,
        organization_id=str(current_user.organization_id),
        scan_id=scan_id,
    )
    
    scan.celery_task_id = task.id
    await db.commit()
    
    return NmapScanResponse(
        task_id=task.id,
        scan_id=scan_id,
        status="queued",
        target=request.target,
        profile="full",
        message="Full scan queued successfully. This may take 30+ minutes."
    )


@router.post(
    "/nmap/vulnerability",
    response_model=NmapScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Escaneo de vulnerabilidades Nmap",
    description="Escaneo con scripts NSE de detección de vulnerabilidades."
)
async def nmap_vulnerability_scan(
    request: NmapScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Escaneo de vulnerabilidades con Nmap.
    
    Usa scripts NSE de la categoría 'vuln' para detectar vulnerabilidades conocidas.
    Incluye checks de autenticación, exploits y malware.
    """
    logger.info(f"Starting vulnerability Nmap scan - target={request.target}")
    
    scan_id = str(uuid4()).replace("-", "")
    scan = Scan(
        id=scan_id,
        organization_id=current_user.organization_id,
        name=request.scan_name or f"Vulnerability Nmap Scan - {request.target}",
        description="Vulnerability scan using NSE scripts",
        scan_type=ScanType.VULNERABILITY.value,
        targets=[request.target],
        status=ScanStatus.QUEUED.value,
        created_by_id=current_user.id,
    )
    
    db.add(scan)
    await db.commit()
    
    task = nmap_vuln_scan_task.delay(
        target=request.target,
        organization_id=str(current_user.organization_id),
        scan_id=scan_id,
    )
    
    scan.celery_task_id = task.id
    await db.commit()
    
    return NmapScanResponse(
        task_id=task.id,
        scan_id=scan_id,
        status="queued",
        target=request.target,
        profile="vulnerability",
        message="Vulnerability scan queued successfully"
    )
