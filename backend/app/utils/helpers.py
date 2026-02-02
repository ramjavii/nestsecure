# =============================================================================
# NESTSECURE - Funciones Helper
# =============================================================================
"""
Funciones utilitarias comunes para toda la aplicación.

Incluye:
- Generación de IDs únicos
- Formateo de datos
- Utilidades de red
- Sanitización de strings
- Operaciones con fechas
"""

import hashlib
import ipaddress
import re
import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from .constants import Patterns


# =============================================================================
# Generación de IDs y Tokens
# =============================================================================
def generate_uuid() -> UUID:
    """Genera un UUID v4 único."""
    return uuid4()


def generate_uuid_str() -> str:
    """Genera un UUID v4 como string."""
    return str(uuid4())


def generate_short_id(length: int = 8) -> str:
    """
    Genera un ID corto alfanumérico.
    
    Args:
        length: Longitud del ID (default: 8)
    
    Returns:
        ID alfanumérico en minúsculas
    """
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_token(length: int = 32) -> str:
    """
    Genera un token seguro para uso en URLs o APIs.
    
    Args:
        length: Longitud del token en bytes (default: 32)
    
    Returns:
        Token hexadecimal
    """
    return secrets.token_hex(length)


def generate_api_key() -> str:
    """
    Genera una API key con formato específico.
    
    Returns:
        API key en formato 'ns_xxxx_xxxxxxxxxxxx'
    """
    prefix = "ns"
    version = "live" if True else "test"  # TODO: usar config
    random_part = secrets.token_hex(16)
    return f"{prefix}_{version}_{random_part}"


# =============================================================================
# Hash y Checksums
# =============================================================================
def hash_string(value: str, algorithm: str = "sha256") -> str:
    """
    Genera hash de un string.
    
    Args:
        value: String a hashear
        algorithm: Algoritmo (md5, sha1, sha256, sha512)
    
    Returns:
        Hash hexadecimal
    """
    hasher = hashlib.new(algorithm)
    hasher.update(value.encode("utf-8"))
    return hasher.hexdigest()


def generate_checksum(data: bytes, algorithm: str = "sha256") -> str:
    """
    Genera checksum de datos binarios.
    
    Args:
        data: Datos binarios
        algorithm: Algoritmo de hash
    
    Returns:
        Checksum hexadecimal
    """
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


# =============================================================================
# Utilidades de Red
# =============================================================================
def is_valid_ipv4(ip: str) -> bool:
    """Valida si es una dirección IPv4 válida."""
    try:
        ipaddress.IPv4Address(ip)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def is_valid_ipv6(ip: str) -> bool:
    """Valida si es una dirección IPv6 válida."""
    try:
        ipaddress.IPv6Address(ip)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def is_valid_ip(ip: str) -> bool:
    """Valida si es una dirección IP válida (v4 o v6)."""
    return is_valid_ipv4(ip) or is_valid_ipv6(ip)


def is_valid_cidr(cidr: str) -> bool:
    """Valida si es un rango CIDR válido."""
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except (ValueError, TypeError):
        return False


def is_private_ip(ip: str) -> bool:
    """Verifica si es una IP privada."""
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private
    except ValueError:
        return False


def is_valid_port(port: Union[int, str]) -> bool:
    """Valida si es un puerto válido (1-65535)."""
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False


def is_valid_port_range(port_range: str) -> bool:
    """
    Valida un rango de puertos (ej: "80-443" o "22").
    
    Args:
        port_range: String con puerto o rango
    
    Returns:
        True si es válido
    """
    match = Patterns.PORT_RANGE.match(port_range)
    if not match:
        return False
    
    start = int(match.group(1))
    end = int(match.group(3)) if match.group(3) else start
    
    return (
        is_valid_port(start) and
        is_valid_port(end) and
        start <= end
    )


def expand_cidr(cidr: str, max_hosts: int = 256) -> List[str]:
    """
    Expande un rango CIDR a lista de IPs.
    
    Args:
        cidr: Rango CIDR (ej: "192.168.1.0/24")
        max_hosts: Máximo número de hosts a retornar
    
    Returns:
        Lista de direcciones IP
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        hosts = list(network.hosts())[:max_hosts]
        return [str(host) for host in hosts]
    except ValueError:
        return []


def expand_port_range(port_range: str) -> List[int]:
    """
    Expande un rango de puertos a lista.
    
    Args:
        port_range: Rango (ej: "80-443" o "22" o "80,443,8080")
    
    Returns:
        Lista de puertos
    """
    ports = set()
    
    for part in port_range.replace(" ", "").split(","):
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                ports.update(range(start, min(end + 1, 65536)))
            except ValueError:
                continue
        else:
            try:
                port = int(part)
                if is_valid_port(port):
                    ports.add(port)
            except ValueError:
                continue
    
    return sorted(ports)


def get_ip_version(ip: str) -> Optional[int]:
    """Retorna la versión de IP (4 o 6) o None si es inválida."""
    try:
        addr = ipaddress.ip_address(ip)
        return addr.version
    except ValueError:
        return None


# =============================================================================
# Sanitización de Strings
# =============================================================================
def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Sanitiza un string removiendo caracteres peligrosos.
    
    Args:
        value: String a sanitizar
        max_length: Longitud máxima
    
    Returns:
        String sanitizado
    """
    if not value:
        return ""
    
    # Remover caracteres de control
    cleaned = "".join(char for char in value if char.isprintable())
    
    # Truncar si es necesario
    return cleaned[:max_length].strip()


def slugify(value: str) -> str:
    """
    Convierte un string a slug (URL-friendly).
    
    Args:
        value: String a convertir
    
    Returns:
        Slug en formato 'palabra-palabra'
    """
    if not value:
        return ""
    
    # Convertir a minúsculas
    slug = value.lower()
    
    # Reemplazar espacios y caracteres especiales por guiones
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    
    # Remover guiones al inicio y final
    return slug.strip("-")


def truncate(value: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Trunca un string con sufijo.
    
    Args:
        value: String a truncar
        max_length: Longitud máxima (incluyendo sufijo)
        suffix: Sufijo a agregar si se trunca
    
    Returns:
        String truncado
    """
    if not value or len(value) <= max_length:
        return value
    
    return value[: max_length - len(suffix)] + suffix


def mask_string(
    value: str,
    visible_start: int = 4,
    visible_end: int = 4,
    mask_char: str = "*"
) -> str:
    """
    Enmascara un string manteniendo visible inicio y fin.
    
    Args:
        value: String a enmascarar
        visible_start: Caracteres visibles al inicio
        visible_end: Caracteres visibles al final
        mask_char: Caracter de máscara
    
    Returns:
        String enmascarado
    """
    if not value:
        return ""
    
    length = len(value)
    if length <= visible_start + visible_end:
        return mask_char * length
    
    start = value[:visible_start]
    end = value[-visible_end:] if visible_end > 0 else ""
    middle = mask_char * (length - visible_start - visible_end)
    
    return f"{start}{middle}{end}"


# =============================================================================
# Operaciones con Fechas
# =============================================================================
def utc_now() -> datetime:
    """Retorna datetime actual en UTC con timezone."""
    return datetime.now(timezone.utc)


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """
    Convierte timestamp Unix a datetime UTC.
    
    Args:
        timestamp: Unix timestamp (segundos)
    
    Returns:
        DateTime en UTC
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convierte datetime a timestamp Unix.
    
    Args:
        dt: DateTime (debe tener timezone)
    
    Returns:
        Unix timestamp
    """
    return int(dt.timestamp())


def format_duration(seconds: Union[int, float]) -> str:
    """
    Formatea segundos como duración legible.
    
    Args:
        seconds: Duración en segundos
    
    Returns:
        String formateado (ej: "2h 30m 15s")
    """
    seconds = int(seconds)
    
    if seconds < 0:
        return "0s"
    
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def time_ago(dt: datetime) -> str:
    """
    Formatea datetime como tiempo relativo.
    
    Args:
        dt: DateTime a formatear
    
    Returns:
        String relativo (ej: "hace 5 minutos")
    """
    now = utc_now()
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "hace unos segundos"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"hace {minutes} minuto{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"hace {hours} hora{'s' if hours != 1 else ''}"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"hace {days} día{'s' if days != 1 else ''}"
    else:
        weeks = int(seconds / 604800)
        return f"hace {weeks} semana{'s' if weeks != 1 else ''}"


# =============================================================================
# Conversiones y Formateo
# =============================================================================
def bytes_to_human(size: int) -> str:
    """
    Convierte bytes a formato legible.
    
    Args:
        size: Tamaño en bytes
    
    Returns:
        String formateado (ej: "1.5 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def safe_int(value: Any, default: int = 0) -> int:
    """Convierte a int de forma segura."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convierte a float de forma segura."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def flatten_dict(
    d: Dict[str, Any],
    parent_key: str = "",
    separator: str = "."
) -> Dict[str, Any]:
    """
    Aplana un diccionario anidado.
    
    Args:
        d: Diccionario a aplanar
        parent_key: Prefijo para las claves
        separator: Separador entre niveles
    
    Returns:
        Diccionario aplanado
    """
    items: List[tuple] = []
    for k, v in d.items():
        new_key = f"{parent_key}{separator}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, separator).items())
        else:
            items.append((new_key, v))
    return dict(items)


# =============================================================================
# Exportar funciones
# =============================================================================
__all__ = [
    # IDs y tokens
    "generate_uuid",
    "generate_uuid_str",
    "generate_short_id",
    "generate_token",
    "generate_api_key",
    # Hash
    "hash_string",
    "generate_checksum",
    # Red
    "is_valid_ipv4",
    "is_valid_ipv6",
    "is_valid_ip",
    "is_valid_cidr",
    "is_private_ip",
    "is_valid_port",
    "is_valid_port_range",
    "expand_cidr",
    "expand_port_range",
    "get_ip_version",
    # Strings
    "sanitize_string",
    "slugify",
    "truncate",
    "mask_string",
    # Fechas
    "utc_now",
    "timestamp_to_datetime",
    "datetime_to_timestamp",
    "format_duration",
    "time_ago",
    # Conversiones
    "bytes_to_human",
    "safe_int",
    "safe_float",
    "flatten_dict",
]
