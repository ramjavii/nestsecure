# =============================================================================
# NESTSECURE - API de Correlación Service→CVE
# =============================================================================
"""
Endpoints para correlacionar servicios detectados con CVEs del NVD.

Endpoints:
- POST /correlation/services/{service_id}/correlate - Correlacionar un servicio
- POST /correlation/scans/{scan_id}/correlate - Correlacionar servicios de un scan
- POST /correlation/assets/{asset_id}/correlate - Correlacionar servicios de un asset
- GET /correlation/cpe/{service_id} - Obtener CPE de un servicio
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.asset import Asset
from app.models.scan import Scan
from app.models.service import Service
from app.models.user import User
from app.services.correlation_service import CorrelationService
from app.utils.cpe_utils import build_cpe_from_service_info


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/correlation", tags=["Correlation"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ServiceCorrelationRequest(BaseModel):
    """Request para correlacionar un servicio."""
    auto_create_vuln: bool = Field(
        default=True,
        description="Crear vulnerabilidades automáticamente"
    )
    max_cves: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Máximo de CVEs a procesar"
    )


class CorrelationResult(BaseModel):
    """Resultado de correlación de un servicio."""
    service_id: str
    cpe: Optional[str] = None
    cpe_confidence: int = 0
    cves_found: int = 0
    vulnerabilities_created: int = 0
    status: str
    cves: list[str] = []
    error: Optional[str] = None


class ScanCorrelationResult(BaseModel):
    """Resultado de correlación de un scan."""
    scan_id: str
    services_processed: int = 0
    services_with_cpe: int = 0
    cves_found: int = 0
    vulnerabilities_created: int = 0
    status: str
    services: list[CorrelationResult] = []


class AssetCorrelationResult(BaseModel):
    """Resultado de correlación de un asset."""
    asset_id: str
    services_processed: int = 0
    cves_found: int = 0
    vulnerabilities_created: int = 0
    services: list[CorrelationResult] = []


class CPEInfo(BaseModel):
    """Información de CPE de un servicio."""
    service_id: str
    port: int
    protocol: str
    service_name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    cpe: Optional[str] = None
    cpe_source: str  # "nmap_detected", "constructed", "none"
    confidence: int = 0


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/services/{service_id}/correlate",
    response_model=CorrelationResult,
    summary="Correlacionar un servicio con CVEs",
    description="""
    Busca CVEs relacionados con un servicio detectado.
    
    El proceso:
    1. Construye un CPE desde la información del servicio (producto, versión)
    2. Busca CVEs en cache local
    3. Si no hay cache, busca en NVD API
    4. Opcionalmente crea vulnerabilidades automáticamente
    
    **Ejemplo**: Apache/2.4.49 → CVE-2021-41773 (Path Traversal)
    """,
)
async def correlate_service(
    service_id: str,
    request: ServiceCorrelationRequest = ServiceCorrelationRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CorrelationResult:
    """Correlaciona un servicio con CVEs del NVD."""
    # Obtener servicio
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio {service_id} no encontrado"
        )
    
    # Verificar permisos (via asset -> organization)
    asset = await db.get(Asset, service.asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset del servicio no encontrado"
        )
    
    if asset.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para este servicio"
        )
    
    # Correlacionar
    logger.info(
        f"Correlating service {service_id} by user {current_user.email}"
    )
    
    correlation_svc = CorrelationService(db)
    result = await correlation_svc.correlate_service(
        service=service,
        auto_create_vuln=request.auto_create_vuln,
        max_cves=request.max_cves,
    )
    
    return CorrelationResult(**result)


@router.post(
    "/scans/{scan_id}/correlate",
    response_model=ScanCorrelationResult,
    summary="Correlacionar todos los servicios de un scan",
    description="""
    Correlaciona todos los servicios detectados en un scan con CVEs.
    
    Útil después de completar un scan de puertos/servicios para
    identificar vulnerabilidades conocidas automáticamente.
    """,
)
async def correlate_scan(
    scan_id: str,
    auto_create: bool = Query(
        default=True,
        description="Crear vulnerabilidades automáticamente"
    ),
    max_cves_per_service: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Máximo de CVEs por servicio"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ScanCorrelationResult:
    """Correlaciona servicios de un scan."""
    # Verificar scan
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} no encontrado"
        )
    
    if scan.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para este scan"
        )
    
    logger.info(
        f"Correlating scan {scan_id} by user {current_user.email}"
    )
    
    correlation_svc = CorrelationService(db)
    result = await correlation_svc.correlate_scan_services(
        scan_id=scan_id,
        auto_create=auto_create,
        max_cves_per_service=max_cves_per_service,
    )
    
    return ScanCorrelationResult(
        scan_id=result["scan_id"],
        services_processed=result["services_processed"],
        services_with_cpe=result["services_with_cpe"],
        cves_found=result["cves_found"],
        vulnerabilities_created=result["vulnerabilities_created"],
        status=result["status"],
        services=[CorrelationResult(**s) for s in result["services"]],
    )


@router.post(
    "/assets/{asset_id}/correlate",
    response_model=AssetCorrelationResult,
    summary="Correlacionar servicios de un asset",
    description="Correlaciona todos los servicios de un asset con CVEs.",
)
async def correlate_asset(
    asset_id: str,
    auto_create: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AssetCorrelationResult:
    """Correlaciona servicios de un asset."""
    # Verificar asset
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset_id} no encontrado"
        )
    
    if asset.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para este asset"
        )
    
    logger.info(
        f"Correlating asset {asset_id} by user {current_user.email}"
    )
    
    correlation_svc = CorrelationService(db)
    result = await correlation_svc.correlate_asset_services(
        asset_id=asset_id,
        auto_create=auto_create,
    )
    
    return AssetCorrelationResult(
        asset_id=result["asset_id"],
        services_processed=result["services_processed"],
        cves_found=result["cves_found"],
        vulnerabilities_created=result["vulnerabilities_created"],
        services=[CorrelationResult(**s) for s in result["services"]],
    )


@router.get(
    "/cpe/{service_id}",
    response_model=CPEInfo,
    summary="Obtener CPE de un servicio",
    description="""
    Obtiene el CPE (Common Platform Enumeration) de un servicio.
    
    Si Nmap detectó un CPE, lo retorna. Si no, intenta construirlo
    desde el producto y versión detectados.
    """,
)
async def get_service_cpe(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CPEInfo:
    """Obtiene CPE de un servicio."""
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio {service_id} no encontrado"
        )
    
    # Verificar permisos
    asset = await db.get(Asset, service.asset_id)
    if not asset or asset.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para este servicio"
        )
    
    # Determinar CPE
    cpe = None
    cpe_source = "none"
    confidence = 0
    
    if service.cpe:
        cpe = service.cpe
        cpe_source = "nmap_detected"
        confidence = 95
    else:
        # Intentar construir
        constructed = build_cpe_from_service_info(
            service_name=service.service_name,
            product=service.product,
            version=service.version,
        )
        if constructed:
            cpe = constructed
            cpe_source = "constructed"
            confidence = 75 if service.version else 50
    
    return CPEInfo(
        service_id=str(service.id),
        port=service.port,
        protocol=service.protocol,
        service_name=service.service_name,
        product=service.product,
        version=service.version,
        cpe=cpe,
        cpe_source=cpe_source,
        confidence=confidence,
    )


@router.get(
    "/stats",
    summary="Estadísticas de correlación",
    description="Obtiene estadísticas de correlación para la organización.",
)
async def get_correlation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Estadísticas de correlación."""
    # TODO: Implementar estadísticas
    # - Total de servicios con CPE
    # - Total de CVEs encontrados
    # - Distribución por severidad
    # - Servicios más vulnerables
    
    return {
        "total_services": 0,
        "services_with_cpe": 0,
        "total_cves_correlated": 0,
        "vulnerabilities_from_correlation": 0,
        "top_affected_products": [],
    }
