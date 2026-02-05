# =============================================================================
# NESTSECURE - Network Validation Utilities
# =============================================================================
"""
Network validation utilities.

Validates scan targets to ensure they are within private networks only (RFC 1918).

RFC 1918 defines the following private address ranges:
- 10.0.0.0/8 (Class A): 10.0.0.0 - 10.255.255.255
- 172.16.0.0/12 (Class B): 172.16.0.0 - 172.31.255.255
- 192.168.0.0/16 (Class C): 192.168.0.0 - 192.168.255.255

Additional private ranges:
- 127.0.0.0/8 (Loopback): 127.0.0.0 - 127.255.255.255
- 169.254.0.0/16 (Link-local): 169.254.0.0 - 169.254.255.255

SECURITY: This module is CRITICAL for preventing scans to external networks.
"""

import ipaddress
import logging
import re
from typing import List, Tuple, Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# =============================================================================
# Private IP Ranges (RFC 1918 + Additional)
# =============================================================================

PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),        # Clase A: 10.0.0.0 - 10.255.255.255
    ipaddress.ip_network('172.16.0.0/12'),     # Clase B: 172.16.0.0 - 172.31.255.255
    ipaddress.ip_network('192.168.0.0/16'),    # Clase C: 192.168.0.0 - 192.168.255.255
    ipaddress.ip_network('127.0.0.0/8'),       # Localhost: 127.0.0.1 - 127.255.255.255
    ipaddress.ip_network('169.254.0.0/16'),    # Link-local: 169.254.0.0 - 169.254.255.255
]

# Ranges for display/documentation purposes
PRIVATE_RANGES_DESCRIPTION = """
Allowed IP ranges (RFC 1918):
  • 10.0.0.0 - 10.255.255.255 (10.0.0.0/8)
  • 172.16.0.0 - 172.31.255.255 (172.16.0.0/12)
  • 192.168.0.0 - 192.168.255.255 (192.168.0.0/16)
  • 127.0.0.0 - 127.255.255.255 (localhost)
"""


# =============================================================================
# Core Validation Functions
# =============================================================================

def is_private_ip(ip: str) -> bool:
    """
    Verifica si una dirección IP es privada según RFC 1918.
    
    Args:
        ip: Dirección IP en formato string (ej: '192.168.1.1')
    
    Returns:
        True si es IP privada, False si es pública
    
    Examples:
        >>> is_private_ip('192.168.1.1')
        True
        >>> is_private_ip('8.8.8.8')
        False
        >>> is_private_ip('10.0.0.1')
        True
        >>> is_private_ip('172.16.0.1')
        True
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        # IP inválida
        return False


def is_private_network(cidr: str) -> bool:
    """
    Verifica si una red CIDR es completamente privada.
    
    Args:
        cidr: Red en formato CIDR (ej: '192.168.1.0/24')
    
    Returns:
        True si TODA la red es privada
    
    Examples:
        >>> is_private_network('192.168.1.0/24')
        True
        >>> is_private_network('10.0.0.0/8')
        True
        >>> is_private_network('8.8.8.0/24')
        False
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        # Verificar que toda la red esté dentro de rangos privados
        return any(
            network.subnet_of(private_range) 
            for private_range in PRIVATE_IP_RANGES
        )
    except ValueError:
        # CIDR inválido
        return False


def is_valid_ip(ip: str) -> bool:
    """
    Verifica si una string es una IP válida (v4 o v6).
    
    Args:
        ip: String a verificar
    
    Returns:
        True si es una IP válida
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_cidr(cidr: str) -> bool:
    """
    Verifica si una string es un CIDR válido.
    
    Args:
        cidr: String a verificar
    
    Returns:
        True si es un CIDR válido
    """
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except ValueError:
        return False


# =============================================================================
# Main Validation Function
# =============================================================================

def validate_scan_target(target: str) -> Tuple[str, str]:
    """
    Valida y normaliza un target de escaneo.
    
    Solo permite:
    - IPs privadas individuales (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    - Redes privadas en CIDR (192.168.1.0/24, 10.0.0.0/8, etc.)
    
    NO permite:
    - IPs públicas
    - Redes públicas
    - Hostnames (por seguridad, podría resolver a IP pública)
    
    Args:
        target: IP, CIDR o hostname
    
    Returns:
        Tuple de (target_normalizado, tipo)
        tipo: 'ip' | 'cidr'
    
    Raises:
        HTTPException 400: Si el target no es válido o es público
    
    Examples:
        >>> validate_scan_target('192.168.1.1')
        ('192.168.1.1', 'ip')
        >>> validate_scan_target('192.168.1.0/24')
        ('192.168.1.0/24', 'cidr')
        >>> validate_scan_target('8.8.8.8')
        HTTPException: Public IP addresses are not allowed
    """
    target = target.strip()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target cannot be empty."
        )
    
    # Caso 1: CIDR notation (192.168.1.0/24)
    if '/' in target:
        # Validar formato CIDR
        if not is_valid_cidr(target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CIDR format: '{target}'. Expected format: x.x.x.x/xx"
            )
        
        if not is_private_network(target):
            logger.warning(
                f"SECURITY: Rejected public network scan attempt: {target}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Public networks are not allowed for scanning. "
                    f"Target '{target}' is outside private networks. "
                    f"Only private networks (10.x, 172.16-31.x, 192.168.x) are permitted."
                )
            )
        
        # Normalizar CIDR (remover host bits si es necesario)
        normalized = str(ipaddress.ip_network(target, strict=False))
        return (normalized, 'cidr')
    
    # Caso 2: Single IP
    if is_valid_ip(target):
        if not is_private_ip(target):
            logger.warning(
                f"SECURITY: Rejected public IP scan attempt: {target}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Public IP address '{target}' is not allowed for scanning. "
                    f"Only private IPs (10.x, 172.16-31.x, 192.168.x) are permitted."
                )
            )
        return (target, 'ip')
    
    # Caso 3: Hostname (no permitido por seguridad)
    # Ejemplo: google.com podría resolver a IP pública
    logger.warning(
        f"SECURITY: Rejected hostname scan attempt: {target}"
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Hostnames are not supported for security reasons. "
            f"Please use IP addresses or CIDR notation only. "
            f"Received: '{target}'"
        )
    )


def validate_multiple_targets(targets: List[str]) -> List[Tuple[str, str]]:
    """
    Valida múltiples targets.
    
    Args:
        targets: Lista de IPs o CIDRs
    
    Returns:
        Lista de tuples (target_normalizado, tipo)
    
    Raises:
        HTTPException: Si algún target no es válido
    """
    if not targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one target is required."
        )
    
    validated = []
    for i, target in enumerate(targets):
        try:
            normalized, target_type = validate_scan_target(target)
            validated.append((normalized, target_type))
        except HTTPException as e:
            # Re-raise con contexto adicional
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Target #{i+1} ('{target}'): {e.detail}"
            )
    
    return validated


def validate_targets_list(targets: List[str]) -> List[str]:
    """
    Valida múltiples targets y retorna solo los targets normalizados.
    
    Args:
        targets: Lista de IPs o CIDRs
    
    Returns:
        Lista de targets normalizados (solo strings)
    """
    validated = validate_multiple_targets(targets)
    return [t[0] for t in validated]


# =============================================================================
# Network Information Functions
# =============================================================================

def get_network_info(cidr: str) -> dict:
    """
    Obtiene información detallada sobre una red CIDR.
    
    Args:
        cidr: Red en formato CIDR
    
    Returns:
        Dict con información de la red:
        - network: Dirección de red
        - netmask: Máscara de red
        - broadcast: Dirección de broadcast
        - num_hosts: Número de hosts disponibles
        - first_host: Primera IP de host
        - last_host: Última IP de host
        - prefix_length: Longitud del prefijo CIDR
        - is_private: Si es red privada
    
    Examples:
        >>> get_network_info('192.168.1.0/24')
        {
            'network': '192.168.1.0',
            'netmask': '255.255.255.0',
            'broadcast': '192.168.1.255',
            'num_hosts': 254,
            'first_host': '192.168.1.1',
            'last_host': '192.168.1.254',
            'prefix_length': 24,
            'is_private': True
        }
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError as e:
        raise ValueError(f"Invalid CIDR: {cidr}. Error: {e}")
    
    # Calcular hosts usables (excluir network y broadcast)
    num_hosts = network.num_addresses - 2 if network.num_addresses > 2 else 0
    
    # Calcular first_host y last_host
    if num_hosts > 0:
        first_host = str(network.network_address + 1)
        last_host = str(network.broadcast_address - 1)
    else:
        first_host = None
        last_host = None
    
    return {
        'network': str(network.network_address),
        'netmask': str(network.netmask),
        'broadcast': str(network.broadcast_address),
        'num_hosts': num_hosts,
        'first_host': first_host,
        'last_host': last_host,
        'prefix_length': network.prefixlen,
        'is_private': is_private_network(cidr),
        'version': network.version,  # 4 o 6
    }


def get_ip_info(ip: str) -> dict:
    """
    Obtiene información sobre una IP individual.
    
    Args:
        ip: Dirección IP
    
    Returns:
        Dict con información de la IP
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError as e:
        raise ValueError(f"Invalid IP: {ip}. Error: {e}")
    
    return {
        'ip': str(ip_obj),
        'version': ip_obj.version,
        'is_private': is_private_ip(ip),
        'is_loopback': ip_obj.is_loopback,
        'is_link_local': ip_obj.is_link_local,
        'is_multicast': ip_obj.is_multicast,
        'is_reserved': ip_obj.is_reserved,
    }


# =============================================================================
# Utility Functions
# =============================================================================

def expand_cidr_to_ips(cidr: str, limit: int = 256) -> List[str]:
    """
    Expande un CIDR a lista de IPs individuales.
    
    ADVERTENCIA: Usar con precaución, puede generar muchas IPs.
    
    Args:
        cidr: Red en formato CIDR
        limit: Límite máximo de IPs a retornar (default: 256)
    
    Returns:
        Lista de IPs en la red (excluyendo network y broadcast)
    
    Raises:
        ValueError: Si el CIDR es inválido o tiene demasiadas IPs
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError as e:
        raise ValueError(f"Invalid CIDR: {cidr}")
    
    # Verificar límite
    num_hosts = network.num_addresses - 2
    if num_hosts > limit:
        raise ValueError(
            f"Network {cidr} has {num_hosts} hosts, exceeds limit of {limit}. "
            f"Use a smaller network (e.g., /24) or increase limit."
        )
    
    # Generar IPs (excluyendo network y broadcast)
    hosts = list(network.hosts())[:limit]
    return [str(ip) for ip in hosts]


def get_common_ports() -> List[int]:
    """
    Retorna lista de puertos comunes para escaneo rápido.
    """
    return [
        21,    # FTP
        22,    # SSH
        23,    # Telnet
        25,    # SMTP
        53,    # DNS
        80,    # HTTP
        110,   # POP3
        135,   # MSRPC
        139,   # NetBIOS
        143,   # IMAP
        443,   # HTTPS
        445,   # SMB
        993,   # IMAPS
        995,   # POP3S
        1433,  # MSSQL
        1521,  # Oracle
        3306,  # MySQL
        3389,  # RDP
        5432,  # PostgreSQL
        5900,  # VNC
        6379,  # Redis
        8080,  # HTTP Alt
        8443,  # HTTPS Alt
        27017, # MongoDB
    ]


# =============================================================================
# Schema Validation (for API)
# =============================================================================

class NetworkValidationError(Exception):
    """Exception para errores de validación de red."""
    
    def __init__(self, message: str, target: str = None):
        self.message = message
        self.target = target
        super().__init__(self.message)


def validate_target_for_scan(target: str) -> dict:
    """
    Valida un target y retorna información detallada para API.
    
    Args:
        target: IP o CIDR a validar
    
    Returns:
        Dict con:
        - valid: bool
        - target: target normalizado
        - type: 'ip' | 'cidr'
        - info: información adicional
        - error: mensaje de error si no es válido
    """
    try:
        normalized, target_type = validate_scan_target(target)
        
        if target_type == 'cidr':
            info = get_network_info(normalized)
        else:
            info = get_ip_info(normalized)
        
        return {
            'valid': True,
            'target': normalized,
            'type': target_type,
            'info': info,
            'error': None,
        }
    
    except HTTPException as e:
        return {
            'valid': False,
            'target': target,
            'type': None,
            'info': None,
            'error': e.detail,
        }
    except Exception as e:
        return {
            'valid': False,
            'target': target,
            'type': None,
            'info': None,
            'error': str(e),
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core validation
    'is_private_ip',
    'is_private_network',
    'is_valid_ip',
    'is_valid_cidr',
    'validate_scan_target',
    'validate_multiple_targets',
    'validate_targets_list',
    
    # Info functions
    'get_network_info',
    'get_ip_info',
    
    # Utilities
    'expand_cidr_to_ips',
    'get_common_ports',
    
    # API helpers
    'validate_target_for_scan',
    'NetworkValidationError',
    
    # Constants
    'PRIVATE_IP_RANGES',
    'PRIVATE_RANGES_DESCRIPTION',
]
