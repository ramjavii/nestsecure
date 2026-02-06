# =============================================================================
# NESTSECURE - API de Vulnerabilidades
# =============================================================================
"""
Endpoints para gestión de vulnerabilidades.

Incluye:
- GET /vulnerabilities: Listar vulnerabilidades
- GET /vulnerabilities/{id}: Obtener detalle de vulnerabilidad
- PUT /vulnerabilities/{id}: Actualizar vulnerabilidad
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, get_db
from app.models.asset import Asset
from app.models.service import Service
from app.models.user import User
from app.models.vulnerability import Vulnerability, VulnerabilityStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================
class VulnerabilityResponse(BaseModel):
    """Respuesta de vulnerabilidad."""
    id: str
    name: str
    description: str
    severity: str
    status: str
    cvss_score: Optional[float]
    cvss_vector: Optional[str]
    cve_id: Optional[str]
    cwe_id: Optional[str]
    host: Optional[str]
    port: Optional[int]
    solution: Optional[str]
    references: List[str]
    exploit_available: bool
    asset_id: str
    scan_id: str
    first_detected_at: str
    last_detected_at: str
    
    class Config:
        from_attributes = True


class VulnerabilityListResponse(BaseModel):
    """Respuesta de lista de vulnerabilidades."""
    items: List[VulnerabilityResponse]
    total: int
    page: int
    pages: int


class VulnerabilityUpdate(BaseModel):
    """Payload para actualizar vulnerabilidad."""
    status: Optional[str] = None
    assigned_to_id: Optional[str] = None
    resolution_notes: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================
@router.get(
    "",
    response_model=List[VulnerabilityResponse],
    summary="Listar vulnerabilidades",
)
async def list_vulnerabilities(
    severity: Optional[str] = Query(None, description="Filtrar por severidad"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    search: Optional[str] = Query(None, description="Buscar por nombre o CVE"),
    sort_by: Optional[str] = Query("cvss_score", description="Campo para ordenar"),
    sort_order: Optional[str] = Query("desc", description="Orden: asc o desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    deduplicate: bool = Query(True, description="Deduplicar vulnerabilidades por nombre"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar vulnerabilidades de la organización.
    
    Soporta filtros por severidad, estado y búsqueda por texto.
    Por defecto deduplica las vulnerabilidades por nombre.
    """
    # Base query - get all to deduplicate first
    query = select(Vulnerability).where(
        Vulnerability.organization_id == current_user.organization_id
    )
    
    # Filtros
    if severity:
        query = query.where(Vulnerability.severity == severity)
    
    if status:
        query = query.where(Vulnerability.status == status)
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Vulnerability.name.ilike(search_filter)) |
            (Vulnerability.cve_id.ilike(search_filter)) |
            (Vulnerability.description.ilike(search_filter))
        )
    
    # Ordenamiento
    order_column = getattr(Vulnerability, sort_by, Vulnerability.cvss_score)
    if sort_order == "asc":
        query = query.order_by(order_column, Vulnerability.created_at.desc())
    else:
        query = query.order_by(desc(order_column), Vulnerability.created_at.desc())
    
    # Ejecutar
    result = await db.execute(query)
    vulns = result.scalars().all()
    
    if deduplicate:
        # Deduplicar por nombre, quedándose con la más reciente
        seen_names = {}
        unique_vulns = []
        for v in vulns:
            if v.name not in seen_names:
                seen_names[v.name] = True
                unique_vulns.append(v)
        vulns = unique_vulns
    
    total = len(vulns)
    
    # Paginación después de deduplicar
    offset = (page - 1) * page_size
    vulns = vulns[offset:offset + page_size]
    
    return [
        VulnerabilityResponse(
            id=v.id,
            name=v.name,
            description=v.description or "",
            severity=v.severity,
            status=v.status,
            cvss_score=v.cvss_score,
            cvss_vector=v.cvss_vector,
            cve_id=v.cve_id,
            cwe_id=v.cwe_id,
            host=v.host,
            port=v.port,
            solution=v.solution,
            references=v.references or [],
            exploit_available=v.exploit_available,
            asset_id=v.asset_id,
            scan_id=v.scan_id,
            first_detected_at=v.first_detected_at.isoformat() if v.first_detected_at else "",
            last_detected_at=v.last_detected_at.isoformat() if v.last_detected_at else "",
        )
        for v in vulns
    ]


@router.get(
    "/{vuln_id}",
    response_model=VulnerabilityResponse,
    summary="Obtener vulnerabilidad",
)
async def get_vulnerability(
    vuln_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener detalle de una vulnerabilidad."""
    query = select(Vulnerability).where(
        Vulnerability.id == vuln_id,
        Vulnerability.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    vuln = result.scalar_one_or_none()
    
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    return VulnerabilityResponse(
        id=vuln.id,
        name=vuln.name,
        description=vuln.description or "",
        severity=vuln.severity,
        status=vuln.status,
        cvss_score=vuln.cvss_score,
        cvss_vector=vuln.cvss_vector,
        cve_id=vuln.cve_id,
        cwe_id=vuln.cwe_id,
        host=vuln.host,
        port=vuln.port,
        solution=vuln.solution,
        references=vuln.references or [],
        exploit_available=vuln.exploit_available,
        asset_id=vuln.asset_id,
        scan_id=vuln.scan_id,
        first_detected_at=vuln.first_detected_at.isoformat() if vuln.first_detected_at else "",
        last_detected_at=vuln.last_detected_at.isoformat() if vuln.last_detected_at else "",
    )


@router.put(
    "/{vuln_id}",
    response_model=VulnerabilityResponse,
    summary="Actualizar vulnerabilidad",
)
async def update_vulnerability(
    vuln_id: str,
    payload: VulnerabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar estado o asignación de una vulnerabilidad."""
    query = select(Vulnerability).where(
        Vulnerability.id == vuln_id,
        Vulnerability.organization_id == current_user.organization_id,
    )
    result = await db.execute(query)
    vuln = result.scalar_one_or_none()
    
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    if payload.status:
        vuln.status = payload.status
    
    if payload.assigned_to_id:
        vuln.assigned_to_id = payload.assigned_to_id
    
    if payload.resolution_notes:
        vuln.resolution_notes = payload.resolution_notes
    
    await db.commit()
    await db.refresh(vuln)
    
    return VulnerabilityResponse(
        id=vuln.id,
        name=vuln.name,
        description=vuln.description or "",
        severity=vuln.severity,
        status=vuln.status,
        cvss_score=vuln.cvss_score,
        cvss_vector=vuln.cvss_vector,
        cve_id=vuln.cve_id,
        cwe_id=vuln.cwe_id,
        host=vuln.host,
        port=vuln.port,
        solution=vuln.solution,
        references=vuln.references or [],
        exploit_available=vuln.exploit_available,
        asset_id=vuln.asset_id,
        scan_id=vuln.scan_id,
        first_detected_at=vuln.first_detected_at.isoformat() if vuln.first_detected_at else "",
        last_detected_at=vuln.last_detected_at.isoformat() if vuln.last_detected_at else "",
    )
