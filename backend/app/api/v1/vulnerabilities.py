# =============================================================================
# NESTSECURE - Endpoints de Vulnerabilidades
# =============================================================================
"""
Endpoints CRUD para gestión de vulnerabilidades.

Incluye:
- GET /: Listar vulnerabilidades con filtros avanzados
- GET /{id}: Obtener vulnerabilidad con detalles
- POST /: Crear vulnerabilidad (para scanners)
- PATCH /{id}: Actualizar estado/asignación
- DELETE /{id}: Eliminar vulnerabilidad
- GET /stats: Estadísticas de vulnerabilidades
- POST /{id}/comment: Añadir comentario
- PATCH /bulk: Actualización masiva de vulnerabilidades
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentActiveUser, require_role
from app.db.session import get_db
from app.models.asset import Asset
from app.models.cve_cache import CVECache
from app.models.scan import Scan
from app.models.service import Service
from app.models.user import User, UserRole
from app.models.vulnerability import (
    Vulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
)
from app.models.vulnerability_comment import VulnerabilityComment
from app.schemas.common import DeleteResponse, MessageResponse, PaginatedResponse
from app.schemas.vulnerability import (
    VulnerabilityBulkUpdate,
    VulnerabilityCreate,
    VulnerabilityFilter,
    VulnerabilityRead,
    VulnerabilityReadMinimal,
    VulnerabilityReadWithAsset,
    VulnerabilityReadWithDetails,
    VulnerabilityStats,
    VulnerabilityUpdate,
)

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def get_vulnerability_or_404(
    db: AsyncSession,
    vuln_id: str,
    organization_id: str,
    include_relations: bool = False,
) -> Vulnerability:
    """
    Obtiene una vulnerabilidad por ID o lanza 404.
    
    Args:
        db: Sesión de base de datos
        vuln_id: ID de la vulnerabilidad
        organization_id: ID de la organización del usuario
        include_relations: Si incluir relaciones (asset, service, scan, comments)
    
    Returns:
        Vulnerabilidad encontrada
    
    Raises:
        HTTPException 404: Si no existe o no pertenece a la organización
    """
    stmt = select(Vulnerability).where(
        and_(
            Vulnerability.id == vuln_id,
            Vulnerability.organization_id == organization_id,
        )
    )
    
    if include_relations:
        stmt = stmt.options(
            selectinload(Vulnerability.asset),
            selectinload(Vulnerability.service),
            selectinload(Vulnerability.scan),
            selectinload(Vulnerability.cve),
            selectinload(Vulnerability.assigned_to),
            selectinload(Vulnerability.comments).selectinload(VulnerabilityComment.user),
        )
    
    result = await db.execute(stmt)
    vuln = result.scalar_one_or_none()
    
    if vuln is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerabilidad no encontrada",
        )
    
    return vuln


# =============================================================================
# List Vulnerabilities
# =============================================================================
@router.get(
    "",
    response_model=PaginatedResponse[VulnerabilityRead],
    summary="Listar vulnerabilidades",
    description="Lista todas las vulnerabilidades de mi organización con filtros avanzados",
)
async def list_vulnerabilities(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items por página"),
    search: str | None = Query(default=None, description="Buscar por título o CVE"),
    severity: str | None = Query(default=None, description="Filtrar por severidad"),
    status_filter: str | None = Query(default=None, alias="status", description="Filtrar por estado"),
    asset_id: str | None = Query(default=None, description="Filtrar por asset"),
    service_id: str | None = Query(default=None, description="Filtrar por servicio"),
    scan_id: str | None = Query(default=None, description="Filtrar por escaneo"),
    cve_id: str | None = Query(default=None, description="Filtrar por CVE ID"),
    assigned_to_id: str | None = Query(default=None, description="Filtrar por asignado"),
    exploit_available: bool | None = Query(default=None, description="Con exploit disponible"),
    is_false_positive: bool | None = Query(default=None, description="Es falso positivo"),
    min_cvss: float | None = Query(default=None, ge=0, le=10, description="CVSS mínimo"),
    max_cvss: float | None = Query(default=None, ge=0, le=10, description="CVSS máximo"),
    min_risk_score: float | None = Query(default=None, ge=0, le=100, description="Risk score mínimo"),
    order_by: str = Query(default="risk_score", description="Campo para ordenar"),
    order_desc: bool = Query(default=True, description="Orden descendente"),
):
    """
    Lista vulnerabilidades con filtros avanzados.
    
    Filtros disponibles:
    - search: Busca en título y CVE ID (ILIKE)
    - severity: critical, high, medium, low, informational
    - status: open, confirmed, in_progress, resolved, accepted, false_positive
    - asset_id: Filtrar por asset específico
    - service_id: Filtrar por servicio específico
    - scan_id: Filtrar por escaneo específico
    - cve_id: Filtrar por CVE ID exacto
    - assigned_to_id: Filtrar por usuario asignado
    - exploit_available: true = solo con exploit disponible
    - is_false_positive: true/false
    - min_cvss, max_cvss: Rango de CVSS
    - min_risk_score: Risk score mínimo
    
    Ordenamiento:
    - order_by: risk_score (default), cvss_score, severity, created_at, title
    - order_desc: true (default) para descendente
    """
    # Base query - solo vulnerabilidades de mi organización
    stmt = select(Vulnerability).where(
        Vulnerability.organization_id == current_user.organization_id
    )
    
    # Aplicar filtros
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Vulnerability.name.ilike(search_pattern),
                Vulnerability.cve_id.ilike(search_pattern),
            )
        )
    
    if severity:
        if severity not in {s.value for s in VulnerabilitySeverity}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Severidad inválida: {severity}",
            )
        stmt = stmt.where(Vulnerability.severity == severity)
    
    if status_filter:
        if status_filter not in {s.value for s in VulnerabilityStatus}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {status_filter}",
            )
        stmt = stmt.where(Vulnerability.status == status_filter)
    
    if asset_id:
        stmt = stmt.where(Vulnerability.asset_id == asset_id)
    
    if service_id:
        stmt = stmt.where(Vulnerability.service_id == service_id)
    
    if scan_id:
        stmt = stmt.where(Vulnerability.scan_id == scan_id)
    
    if cve_id:
        stmt = stmt.where(Vulnerability.cve_id == cve_id)
    
    if assigned_to_id:
        stmt = stmt.where(Vulnerability.assigned_to_id == assigned_to_id)
    
    if exploit_available is not None:
        stmt = stmt.where(Vulnerability.exploit_available == exploit_available)
    
    if is_false_positive is not None:
        stmt = stmt.where(Vulnerability.is_false_positive == is_false_positive)
    
    if min_cvss is not None:
        stmt = stmt.where(Vulnerability.cvss_score >= min_cvss)
    
    if max_cvss is not None:
        stmt = stmt.where(Vulnerability.cvss_score <= max_cvss)
    
    if min_risk_score is not None:
        stmt = stmt.where(Vulnerability.risk_score >= min_risk_score)
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Ordenamiento
    order_columns = {
        "risk_score": Vulnerability.risk_score,
        "cvss_score": Vulnerability.cvss_score,
        "severity": Vulnerability.severity,
        "created_at": Vulnerability.created_at,
        "name": Vulnerability.name,
        "first_detected_at": Vulnerability.first_detected_at,
        "last_detected_at": Vulnerability.last_detected_at,
    }
    order_column = order_columns.get(order_by, Vulnerability.risk_score)
    
    if order_desc:
        stmt = stmt.order_by(order_column.desc().nullslast())
    else:
        stmt = stmt.order_by(order_column.asc().nullsfirst())
    
    # Paginación
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    # Include asset for display
    stmt = stmt.options(selectinload(Vulnerability.asset))
    
    result = await db.execute(stmt)
    vulns = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[VulnerabilityRead.model_validate(v) for v in vulns],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Get Vulnerability Details
# =============================================================================
@router.get(
    "/{vuln_id}",
    response_model=VulnerabilityReadWithDetails,
    summary="Obtener vulnerabilidad",
    description="Obtiene una vulnerabilidad con todos sus detalles",
)
async def get_vulnerability(
    vuln_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene una vulnerabilidad con:
    - Datos completos de la vulnerabilidad
    - Asset relacionado
    - Servicio relacionado (si aplica)
    - Información del escaneo
    - Datos del CVE (si está en cache)
    - Comentarios con usuarios
    """
    vuln = await get_vulnerability_or_404(
        db, vuln_id, current_user.organization_id, include_relations=True
    )
    
    # Construir respuesta con relaciones serializadas
    response_dict = {
        "id": vuln.id,
        "organization_id": vuln.organization_id,
        "asset_id": vuln.asset_id,
        "scan_id": vuln.scan_id,
        "service_id": vuln.service_id,
        "cve_id": vuln.cve_id,
        "name": vuln.name,
        "description": vuln.description,
        "severity": vuln.severity,
        "cvss_score": vuln.cvss_score,
        "cvss_vector": vuln.cvss_vector,
        "status": vuln.status,
        "solution": vuln.solution,
        "references": vuln.references,
        "cwe_id": vuln.cwe_id,
        "cwe_name": vuln.cwe_name,
        "risk_score": vuln.risk_score,
        "risk_factors": vuln.risk_factors,
        "exploit_available": vuln.exploit_available,
        "exploit_maturity": vuln.exploit_maturity,
        "in_the_wild": vuln.in_the_wild,
        "assigned_to_id": vuln.assigned_to_id,
        "due_date": vuln.due_date,
        "resolution_notes": vuln.resolution_notes,
        "resolved_at": vuln.resolved_at,
        "resolved_by_id": vuln.resolved_by_id,
        "first_detected_at": vuln.first_detected_at,
        "last_detected_at": vuln.last_detected_at,
        "times_detected": vuln.times_detected,
        "scanner_name": vuln.scanner_name,
        "created_at": vuln.created_at,
        "updated_at": vuln.updated_at,
        "asset": None,
        "service": None,
        "scan": None,
    }
    
    # Agregar asset si existe
    if vuln.asset:
        response_dict["asset"] = {
            "id": vuln.asset.id,
            "ip_address": vuln.asset.ip_address,
            "hostname": vuln.asset.hostname,
            "asset_type": vuln.asset.asset_type,
            "criticality": vuln.asset.criticality,
        }
    
    # Agregar service si existe
    if vuln.service:
        response_dict["service"] = {
            "id": vuln.service.id,
            "port": vuln.service.port,
            "protocol": vuln.service.protocol,
            "name": vuln.service.name,
            "version": vuln.service.version,
        }
    
    # Agregar scan si existe
    if vuln.scan:
        response_dict["scan"] = {
            "id": vuln.scan.id,
            "name": vuln.scan.name,
            "scan_type": vuln.scan.scan_type,
            "status": vuln.scan.status,
        }
    
    return VulnerabilityReadWithDetails.model_validate(response_dict)


# =============================================================================
# Create Vulnerability
# =============================================================================
@router.post(
    "",
    response_model=VulnerabilityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear vulnerabilidad",
    description="Crea una nueva vulnerabilidad (usado por scanners)",
    dependencies=[Depends(require_role(UserRole.OPERATOR))],
)
async def create_vulnerability(
    vuln_in: VulnerabilityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Crea una nueva vulnerabilidad.
    
    Usado principalmente por scanners para reportar hallazgos.
    
    - Verifica que el asset pertenezca a la organización
    - Si se proporciona service_id, verifica que pertenezca al asset
    - Si se proporciona cve_id, intenta enriquecer con datos del cache
    - Calcula risk_score basado en CVSS y criticidad del asset
    """
    organization_id = current_user.organization_id
    
    # Verificar que el asset existe y pertenece a la organización
    asset_stmt = select(Asset).where(
        and_(
            Asset.id == vuln_in.asset_id,
            Asset.organization_id == organization_id,
        )
    )
    asset_result = await db.execute(asset_stmt)
    asset = asset_result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset no encontrado",
        )
    
    # Verificar servicio si se proporciona
    if vuln_in.service_id:
        service_stmt = select(Service).where(
            and_(
                Service.id == vuln_in.service_id,
                Service.asset_id == vuln_in.asset_id,
            )
        )
        service_result = await db.execute(service_stmt)
        service = service_result.scalar_one_or_none()
        
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servicio no encontrado o no pertenece al asset",
            )
    
    # Buscar CVE en cache si se proporciona
    cve_data = None
    if vuln_in.cve_id:
        cve_stmt = select(CVECache).where(CVECache.cve_id == vuln_in.cve_id)
        cve_result = await db.execute(cve_stmt)
        cve_data = cve_result.scalar_one_or_none()
    
    # Crear vulnerabilidad
    vuln = Vulnerability(
        organization_id=organization_id,
        asset_id=vuln_in.asset_id,
        service_id=vuln_in.service_id,
        scan_id=vuln_in.scan_id,
        cve_id=vuln_in.cve_id,
        name=vuln_in.name,
        description=vuln_in.description,
        severity=vuln_in.severity,
        cvss_score=vuln_in.cvss_score,
        cvss_vector=vuln_in.cvss_vector,
        solution=vuln_in.solution,
        references=vuln_in.references or [],
        evidence=vuln_in.evidence,
        cwe_id=vuln_in.cwe_id,
        cwe_name=vuln_in.cwe_name,
        exploit_available=vuln_in.exploit_available or False,
        exploit_maturity=vuln_in.exploit_maturity,
        in_the_wild=vuln_in.in_the_wild or False,
        scanner_name=vuln_in.scanner_name,
        scanner_plugin_id=vuln_in.scanner_plugin_id,
        raw_output=vuln_in.raw_output,
        status=VulnerabilityStatus.OPEN.value,
        first_detected_at=datetime.utcnow(),
        last_detected_at=datetime.utcnow(),
        times_detected=1,
    )
    
    # Enriquecer con datos del CVE si está disponible
    if cve_data:
        vuln.enrich_from_cve(cve_data)
    
    # Calcular risk_score básico (CVSS * factor de criticidad del asset)
    criticality_multipliers = {
        "critical": 1.0,
        "high": 0.9,
        "medium": 0.7,
        "low": 0.5,
    }
    multiplier = criticality_multipliers.get(asset.criticality, 0.7)
    base_score = vuln.cvss_score or 5.0
    vuln.risk_score = min(100, base_score * 10 * multiplier)
    
    db.add(vuln)
    await db.commit()
    await db.refresh(vuln)
    
    # Actualizar contadores en el asset
    await update_asset_vuln_counts(db, vuln_in.asset_id)
    
    return VulnerabilityRead.model_validate(vuln)


async def update_asset_vuln_counts(db: AsyncSession, asset_id: str) -> None:
    """Actualiza los contadores de vulnerabilidades en un asset."""
    # Contar vulnerabilidades activas por severidad
    counts = {}
    for severity in ["critical", "high", "medium", "low"]:
        count_stmt = select(func.count()).select_from(Vulnerability).where(
            and_(
                Vulnerability.asset_id == asset_id,
                Vulnerability.severity == severity,
                Vulnerability.status.notin_(["fixed", "false_positive", "accepted_risk"]),
            )
        )
        result = await db.execute(count_stmt)
        counts[severity] = result.scalar() or 0
    
    # Actualizar asset
    update_stmt = select(Asset).where(Asset.id == asset_id)
    asset_result = await db.execute(update_stmt)
    asset = asset_result.scalar_one_or_none()
    
    if asset:
        asset.vuln_critical_count = counts["critical"]
        asset.vuln_high_count = counts["high"]
        asset.vuln_medium_count = counts["medium"]
        asset.vuln_low_count = counts["low"]
        
        # Recalcular risk_score del asset
        asset.risk_score = (
            counts["critical"] * 40 +
            counts["high"] * 20 +
            counts["medium"] * 5 +
            counts["low"] * 1
        )
        asset.risk_score = min(100.0, asset.risk_score)
        
        await db.commit()


# =============================================================================
# Update Vulnerability
# =============================================================================
@router.patch(
    "/{vuln_id}",
    response_model=VulnerabilityRead,
    summary="Actualizar vulnerabilidad",
    description="Actualiza el estado o asignación de una vulnerabilidad",
    dependencies=[Depends(require_role(UserRole.OPERATOR))],
)
async def update_vulnerability(
    vuln_id: str,
    vuln_in: VulnerabilityUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Actualiza una vulnerabilidad.
    
    Operaciones comunes:
    - Cambiar estado (open -> in_progress -> resolved)
    - Marcar como falso positivo
    - Asignar a un usuario
    - Actualizar solución o notas
    """
    vuln = await get_vulnerability_or_404(
        db, vuln_id, current_user.organization_id
    )
    
    update_data = vuln_in.model_dump(exclude_unset=True)
    
    # Manejar cambios de estado especiales
    if "status" in update_data:
        new_status = update_data["status"]
        
        if new_status == VulnerabilityStatus.FIXED.value:
            vuln.resolved_at = datetime.utcnow()
            vuln.resolved_by_id = current_user.id
        elif new_status == VulnerabilityStatus.FALSE_POSITIVE.value:
            vuln.resolved_at = datetime.utcnow()
            vuln.resolved_by_id = current_user.id
    
    # Validar assigned_to_id si se proporciona
    if "assigned_to_id" in update_data and update_data["assigned_to_id"]:
        user_stmt = select(User).where(
            and_(
                User.id == update_data["assigned_to_id"],
                User.organization_id == current_user.organization_id,
            )
        )
        user_result = await db.execute(user_stmt)
        assigned_user = user_result.scalar_one_or_none()
        
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario asignado no encontrado",
            )
    
    # Aplicar cambios
    for field, value in update_data.items():
        setattr(vuln, field, value)
    
    await db.commit()
    await db.refresh(vuln)
    
    # Actualizar contadores si cambió el estado
    if "status" in update_data:
        await update_asset_vuln_counts(db, vuln.asset_id)
    
    return VulnerabilityRead.model_validate(vuln)


# =============================================================================
# Delete Vulnerability
# =============================================================================
@router.delete(
    "/{vuln_id}",
    response_model=DeleteResponse,
    summary="Eliminar vulnerabilidad",
    description="Elimina una vulnerabilidad (solo admins)",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_vulnerability(
    vuln_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Elimina una vulnerabilidad permanentemente.
    
    Solo disponible para administradores.
    Se recomienda marcar como falso positivo en lugar de eliminar.
    """
    vuln = await get_vulnerability_or_404(
        db, vuln_id, current_user.organization_id
    )
    
    asset_id = vuln.asset_id
    deleted_id = vuln.id
    
    await db.delete(vuln)
    await db.commit()
    
    # Actualizar contadores del asset
    await update_asset_vuln_counts(db, asset_id)
    
    return DeleteResponse(
        message="Vulnerabilidad eliminada correctamente",
        deleted_id=deleted_id
    )


# =============================================================================
# Vulnerability Statistics
# =============================================================================
@router.get(
    "/stats/summary",
    response_model=VulnerabilityStats,
    summary="Estadísticas de vulnerabilidades",
    description="Obtiene estadísticas agregadas de vulnerabilidades",
)
async def get_vulnerability_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Obtiene estadísticas de vulnerabilidades:
    - Total por severidad
    - Total por estado
    - Conteo con exploit disponible
    - Promedio de CVSS
    - Top CVEs más frecuentes
    """
    org_id = current_user.organization_id
    
    # Conteo por severidad
    severity_counts = {}
    for severity in VulnerabilitySeverity:
        count_stmt = select(func.count()).select_from(Vulnerability).where(
            and_(
                Vulnerability.organization_id == org_id,
                Vulnerability.severity == severity.value,
            )
        )
        result = await db.execute(count_stmt)
        severity_counts[severity.value] = result.scalar() or 0
    
    # Conteo por estado
    status_counts = {}
    for st in VulnerabilityStatus:
        count_stmt = select(func.count()).select_from(Vulnerability).where(
            and_(
                Vulnerability.organization_id == org_id,
                Vulnerability.status == st.value,
            )
        )
        result = await db.execute(count_stmt)
        status_counts[st.value] = result.scalar() or 0
    
    # Total
    total_stmt = select(func.count()).select_from(Vulnerability).where(
        Vulnerability.organization_id == org_id
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0
    
    # Con exploit
    exploit_stmt = select(func.count()).select_from(Vulnerability).where(
        and_(
            Vulnerability.organization_id == org_id,
            Vulnerability.exploit_available == True,
        )
    )
    exploit_result = await db.execute(exploit_stmt)
    with_exploit = exploit_result.scalar() or 0
    
    # Promedio CVSS
    avg_stmt = select(func.avg(Vulnerability.cvss_score)).where(
        and_(
            Vulnerability.organization_id == org_id,
            Vulnerability.cvss_score.isnot(None),
        )
    )
    avg_result = await db.execute(avg_stmt)
    avg_cvss = avg_result.scalar() or 0.0
    
    # Vulnerabilidades abiertas (no resueltas ni falso positivo)
    open_stmt = select(func.count()).select_from(Vulnerability).where(
        and_(
            Vulnerability.organization_id == org_id,
            Vulnerability.status.notin_(["fixed", "false_positive", "accepted_risk"]),
        )
    )
    open_result = await db.execute(open_stmt)
    open_count = open_result.scalar() or 0
    
    return VulnerabilityStats(
        total=total,
        by_severity=severity_counts,
        by_status=status_counts,
        with_exploit=with_exploit,
        average_cvss=round(float(avg_cvss), 2),
        open_count=open_count,
        resolved_count=status_counts.get("fixed", 0),
        false_positive_count=status_counts.get("false_positive", 0),
    )


# =============================================================================
# Add Comment
# =============================================================================
@router.post(
    "/{vuln_id}/comments",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Añadir comentario",
    description="Añade un comentario a una vulnerabilidad",
)
async def add_comment(
    vuln_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    content: str = Query(..., min_length=1, max_length=5000, description="Contenido del comentario"),
    comment_type: str = Query(default="note", description="Tipo: note, investigation, resolution"),
):
    """
    Añade un comentario a una vulnerabilidad.
    
    Tipos de comentario:
    - note: Nota general
    - investigation: Hallazgos de investigación
    - resolution: Detalles de resolución
    """
    vuln = await get_vulnerability_or_404(
        db, vuln_id, current_user.organization_id
    )
    
    comment = VulnerabilityComment(
        vulnerability_id=vuln.id,
        user_id=current_user.id,
        content=content,
        comment_type=comment_type,
    )
    
    db.add(comment)
    await db.commit()
    
    return MessageResponse(message="Comentario añadido correctamente")


# =============================================================================
# Bulk Update
# =============================================================================
@router.patch(
    "/bulk/update",
    response_model=MessageResponse,
    summary="Actualización masiva",
    description="Actualiza múltiples vulnerabilidades a la vez",
    dependencies=[Depends(require_role(UserRole.OPERATOR))],
)
async def bulk_update_vulnerabilities(
    bulk_update: VulnerabilityBulkUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
):
    """
    Actualiza múltiples vulnerabilidades.
    
    Útil para:
    - Cambiar estado de varias a la vez
    - Asignar múltiples vulnerabilidades a un usuario
    - Marcar múltiples como falso positivo
    """
    org_id = current_user.organization_id
    
    # Verificar que todas las vulnerabilidades existen y pertenecen a la org
    stmt = select(Vulnerability).where(
        and_(
            Vulnerability.id.in_(bulk_update.vulnerability_ids),
            Vulnerability.organization_id == org_id,
        )
    )
    result = await db.execute(stmt)
    vulns = result.scalars().all()
    
    if len(vulns) != len(bulk_update.vulnerability_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Una o más vulnerabilidades no encontradas",
        )
    
    # Validar assigned_to_id si se proporciona
    if bulk_update.assigned_to_id:
        user_stmt = select(User).where(
            and_(
                User.id == bulk_update.assigned_to_id,
                User.organization_id == org_id,
            )
        )
        user_result = await db.execute(user_stmt)
        if not user_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario asignado no encontrado",
            )
    
    # Aplicar cambios
    affected_assets = set()
    for vuln in vulns:
        if bulk_update.status:
            vuln.status = bulk_update.status
            if bulk_update.status in ["fixed", "false_positive", "accepted_risk"]:
                vuln.resolved_at = datetime.utcnow()
                vuln.resolved_by_id = current_user.id
        
        if bulk_update.assigned_to_id:
            vuln.assigned_to_id = bulk_update.assigned_to_id
        
        affected_assets.add(vuln.asset_id)
    
    await db.commit()
    
    # Actualizar contadores de assets afectados
    for asset_id in affected_assets:
        await update_asset_vuln_counts(db, asset_id)
    
    return MessageResponse(
        message=f"{len(vulns)} vulnerabilidades actualizadas correctamente"
    )
