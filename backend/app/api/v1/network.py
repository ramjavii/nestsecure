# =============================================================================
# NESTSECURE - API de Network Utilities
# =============================================================================
"""
Endpoints para validación y utilidades de red.

Endpoints:
- POST /network/validate: Validar un target de escaneo
- POST /network/validate-multiple: Validar múltiples targets
- GET /network/info/{cidr}: Obtener información de una red CIDR
- GET /network/private-ranges: Obtener rangos de IPs privadas permitidos
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.utils.network_utils import (
    validate_target_for_scan,
    validate_scan_target,
    validate_targets_list,
    get_network_info,
    get_ip_info,
    PRIVATE_RANGES_DESCRIPTION,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class TargetValidationRequest(BaseModel):
    """Request para validar un target."""
    target: str = Field(..., min_length=1, description="IP o CIDR a validar")


class MultipleTargetsRequest(BaseModel):
    """Request para validar múltiples targets."""
    targets: List[str] = Field(..., min_items=1, description="Lista de IPs o CIDRs")


class TargetValidationResponse(BaseModel):
    """Response de validación de target."""
    valid: bool
    target: str
    type: Optional[str] = None  # 'ip' | 'cidr' | None
    error: Optional[str] = None
    info: Optional[dict] = None


class MultipleValidationResponse(BaseModel):
    """Response de validación de múltiples targets."""
    valid: bool
    targets: List[TargetValidationResponse]
    total: int
    valid_count: int
    invalid_count: int


class NetworkInfoResponse(BaseModel):
    """Response con información de red."""
    network: str
    netmask: str
    broadcast: str
    num_hosts: int
    first_host: Optional[str]
    last_host: Optional[str]
    prefix_length: int
    is_private: bool
    version: int


class PrivateRangesResponse(BaseModel):
    """Response con rangos de IPs privadas."""
    description: str
    ranges: List[dict]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/validate",
    response_model=TargetValidationResponse,
    summary="Validar un target de escaneo",
)
async def validate_target(request: TargetValidationRequest):
    """
    Valida si un target (IP o CIDR) es válido para escanear.
    
    Solo se permiten redes privadas según RFC 1918:
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
    
    Returns:
        TargetValidationResponse con valid=True/False y detalles
    """
    result = validate_target_for_scan(request.target)
    return TargetValidationResponse(**result)


@router.post(
    "/validate-multiple",
    response_model=MultipleValidationResponse,
    summary="Validar múltiples targets",
)
async def validate_multiple_targets(request: MultipleTargetsRequest):
    """
    Valida múltiples targets (IPs o CIDRs) en una sola llamada.
    
    Útil para validar antes de crear un scan con múltiples objetivos.
    
    Returns:
        MultipleValidationResponse con resultados individuales y resumen
    """
    results = []
    valid_count = 0
    invalid_count = 0
    
    for target in request.targets:
        validation = validate_target_for_scan(target)
        results.append(TargetValidationResponse(**validation))
        
        if validation['valid']:
            valid_count += 1
        else:
            invalid_count += 1
    
    all_valid = invalid_count == 0
    
    return MultipleValidationResponse(
        valid=all_valid,
        targets=results,
        total=len(request.targets),
        valid_count=valid_count,
        invalid_count=invalid_count,
    )


@router.get(
    "/info/{cidr:path}",
    response_model=NetworkInfoResponse,
    summary="Obtener información de una red CIDR",
)
async def get_cidr_info(cidr: str):
    """
    Obtiene información detallada sobre una red CIDR.
    
    Incluye: dirección de red, máscara, broadcast, número de hosts, etc.
    
    Args:
        cidr: Red en formato CIDR (ej: 192.168.1.0/24)
    
    Returns:
        NetworkInfoResponse con información detallada
    """
    try:
        info = get_network_info(cidr)
        return NetworkInfoResponse(**info)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/private-ranges",
    response_model=PrivateRangesResponse,
    summary="Obtener rangos de IPs privadas permitidos",
)
async def get_private_ranges():
    """
    Retorna la lista de rangos de IPs privadas permitidos para escaneo.
    
    Estos rangos están definidos según RFC 1918.
    """
    return PrivateRangesResponse(
        description=PRIVATE_RANGES_DESCRIPTION,
        ranges=[
            {
                "name": "Class A Private",
                "cidr": "10.0.0.0/8",
                "range": "10.0.0.0 - 10.255.255.255",
                "hosts": 16777214,
            },
            {
                "name": "Class B Private",
                "cidr": "172.16.0.0/12",
                "range": "172.16.0.0 - 172.31.255.255",
                "hosts": 1048574,
            },
            {
                "name": "Class C Private",
                "cidr": "192.168.0.0/16",
                "range": "192.168.0.0 - 192.168.255.255",
                "hosts": 65534,
            },
            {
                "name": "Loopback",
                "cidr": "127.0.0.0/8",
                "range": "127.0.0.0 - 127.255.255.255",
                "hosts": 16777214,
            },
            {
                "name": "Link-local",
                "cidr": "169.254.0.0/16",
                "range": "169.254.0.0 - 169.254.255.255",
                "hosts": 65534,
            },
        ]
    )


@router.get(
    "/check-ip/{ip}",
    summary="Verificar si una IP es privada",
)
async def check_ip(ip: str):
    """
    Verifica si una IP específica es privada o pública.
    
    Args:
        ip: Dirección IP a verificar
    
    Returns:
        Información sobre la IP
    """
    try:
        info = get_ip_info(ip)
        return {
            "ip": ip,
            "is_private": info["is_private"],
            "can_scan": info["is_private"],
            "details": info,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid IP address: {ip}"
        )
