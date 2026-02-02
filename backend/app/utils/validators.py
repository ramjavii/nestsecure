# =============================================================================
# NESTSECURE - Validadores Personalizados
# =============================================================================
"""
Validadores personalizados para Pydantic y uso general.

Incluye:
- Validación de IPs y CIDRs
- Validación de puertos
- Validación de CPE y CVE
- Validadores de dominio/hostname
- Validadores de formato
"""

import re
from typing import Any, Callable, List, Optional, TypeVar, Union

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, PydanticCustomError, core_schema

from .constants import Patterns
from .helpers import (
    is_valid_cidr,
    is_valid_ip,
    is_valid_ipv4,
    is_valid_ipv6,
    is_valid_port,
    is_valid_port_range,
)


T = TypeVar("T")


# =============================================================================
# Validadores de Red
# =============================================================================
def validate_ipv4(value: str) -> str:
    """Valida y retorna dirección IPv4."""
    if not is_valid_ipv4(value):
        raise ValueError(f"'{value}' no es una dirección IPv4 válida")
    return value


def validate_ipv6(value: str) -> str:
    """Valida y retorna dirección IPv6."""
    if not is_valid_ipv6(value):
        raise ValueError(f"'{value}' no es una dirección IPv6 válida")
    return value


def validate_ip_address(value: str) -> str:
    """Valida y retorna dirección IP (v4 o v6)."""
    if not is_valid_ip(value):
        raise ValueError(f"'{value}' no es una dirección IP válida")
    return value


def validate_cidr(value: str) -> str:
    """Valida y retorna rango CIDR."""
    if not is_valid_cidr(value):
        raise ValueError(f"'{value}' no es un rango CIDR válido")
    return value


def validate_ip_or_cidr(value: str) -> str:
    """Valida IP individual o rango CIDR."""
    if not is_valid_ip(value) and not is_valid_cidr(value):
        raise ValueError(f"'{value}' no es una IP o CIDR válido")
    return value


def validate_port(value: Union[int, str]) -> int:
    """Valida y retorna puerto como entero."""
    if not is_valid_port(value):
        raise ValueError(f"'{value}' no es un puerto válido (1-65535)")
    return int(value)


def validate_port_range(value: str) -> str:
    """Valida rango de puertos (ej: '80-443' o '22')."""
    if not is_valid_port_range(value):
        raise ValueError(f"'{value}' no es un rango de puertos válido")
    return value


def validate_port_list(value: str) -> List[int]:
    """
    Valida y expande lista de puertos.
    Acepta: '22', '80,443', '20-25', '22,80-90,443'
    """
    ports = set()
    
    for part in value.replace(" ", "").split(","):
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                if not (is_valid_port(start) and is_valid_port(end) and start <= end):
                    raise ValueError(f"Rango inválido: {part}")
                ports.update(range(start, end + 1))
            except ValueError as e:
                raise ValueError(f"Formato de rango inválido: {part}") from e
        else:
            port = validate_port(part)
            ports.add(port)
    
    return sorted(ports)


def validate_mac_address(value: str) -> str:
    """Valida dirección MAC."""
    if not Patterns.MAC_ADDRESS.match(value):
        raise ValueError(f"'{value}' no es una dirección MAC válida")
    return value.upper()


# =============================================================================
# Validadores de Identificadores
# =============================================================================
def validate_hostname(value: str) -> str:
    """Valida nombre de host."""
    if not value:
        raise ValueError("El hostname no puede estar vacío")
    
    if len(value) > 253:
        raise ValueError("El hostname no puede exceder 253 caracteres")
    
    # Verificar cada parte del hostname
    parts = value.split(".")
    for part in parts:
        if not part:
            raise ValueError("El hostname tiene segmentos vacíos")
        if not Patterns.HOSTNAME.match(part):
            raise ValueError(f"Segmento de hostname inválido: '{part}'")
    
    return value.lower()


def validate_fqdn(value: str) -> str:
    """Valida nombre de dominio completo (FQDN)."""
    if not Patterns.FQDN.match(value):
        raise ValueError(f"'{value}' no es un FQDN válido")
    return value.lower()


def validate_slug(value: str) -> str:
    """Valida formato slug (letras minúsculas, números y guiones)."""
    if not Patterns.SLUG.match(value):
        raise ValueError(
            f"'{value}' no es un slug válido. "
            "Use solo letras minúsculas, números y guiones."
        )
    return value


def validate_uuid(value: str) -> str:
    """Valida formato UUID."""
    if not Patterns.UUID.match(value):
        raise ValueError(f"'{value}' no es un UUID válido")
    return value.lower()


# =============================================================================
# Validadores de Seguridad (CVE, CPE)
# =============================================================================
def validate_cve_id(value: str) -> str:
    """
    Valida identificador CVE.
    Formato: CVE-YYYY-NNNNN
    """
    value_upper = value.upper()
    if not Patterns.CVE_ID.match(value_upper):
        raise ValueError(
            f"'{value}' no es un ID de CVE válido. "
            "Formato esperado: CVE-YYYY-NNNNN"
        )
    return value_upper


def validate_cpe(value: str) -> str:
    """
    Valida formato CPE 2.3.
    Formato: cpe:2.3:part:vendor:product:version:...
    """
    if not value.startswith("cpe:2.3:"):
        raise ValueError("El CPE debe comenzar con 'cpe:2.3:'")
    
    # Validación básica de estructura
    parts = value.split(":")
    if len(parts) < 5:
        raise ValueError("El CPE tiene muy pocos componentes")
    
    # Part debe ser a, h, o, * o -
    part = parts[2]
    if part not in ("a", "h", "o", "*", "-"):
        raise ValueError(f"Parte de CPE inválida: '{part}'")
    
    return value.lower()


def validate_cvss_score(value: float) -> float:
    """Valida puntuación CVSS (0.0 - 10.0)."""
    if not 0.0 <= value <= 10.0:
        raise ValueError(f"CVSS debe estar entre 0.0 y 10.0, recibido: {value}")
    return round(value, 1)


# =============================================================================
# Validadores de Formato
# =============================================================================
def validate_not_empty(value: str, field_name: str = "campo") -> str:
    """Valida que el string no esté vacío."""
    if not value or not value.strip():
        raise ValueError(f"El {field_name} no puede estar vacío")
    return value.strip()


def validate_length(
    value: str,
    min_length: int = 0,
    max_length: int = 255,
    field_name: str = "campo"
) -> str:
    """Valida longitud de string."""
    length = len(value)
    if length < min_length:
        raise ValueError(
            f"El {field_name} debe tener al menos {min_length} caracteres"
        )
    if length > max_length:
        raise ValueError(
            f"El {field_name} no puede exceder {max_length} caracteres"
        )
    return value


def validate_regex(value: str, pattern: re.Pattern, message: str) -> str:
    """Valida string contra un patrón regex."""
    if not pattern.match(value):
        raise ValueError(message)
    return value


def validate_in_list(value: T, allowed: List[T], field_name: str = "valor") -> T:
    """Valida que el valor esté en una lista permitida."""
    if value not in allowed:
        raise ValueError(
            f"El {field_name} debe ser uno de: {', '.join(map(str, allowed))}"
        )
    return value


def validate_password_strength(password: str) -> str:
    """
    Valida fortaleza de contraseña.
    
    Requisitos:
    - Mínimo 8 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    - Al menos un caracter especial
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Mínimo 8 caracteres")
    if not re.search(r"[A-Z]", password):
        errors.append("Al menos una letra mayúscula")
    if not re.search(r"[a-z]", password):
        errors.append("Al menos una letra minúscula")
    if not re.search(r"\d", password):
        errors.append("Al menos un número")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Al menos un caracter especial")
    
    if errors:
        raise ValueError(
            f"La contraseña no cumple los requisitos: {'; '.join(errors)}"
        )
    
    return password


# =============================================================================
# Tipos Personalizados para Pydantic (Annotated Types)
# =============================================================================
class IPv4Address(str):
    """Tipo personalizado para IPv4 en Pydantic."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )
    
    @classmethod
    def _validate(cls, value: str) -> str:
        return validate_ipv4(value)


class IPv6Address(str):
    """Tipo personalizado para IPv6 en Pydantic."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )
    
    @classmethod
    def _validate(cls, value: str) -> str:
        return validate_ipv6(value)


class IPAddress(str):
    """Tipo personalizado para IP (v4 o v6) en Pydantic."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )
    
    @classmethod
    def _validate(cls, value: str) -> str:
        return validate_ip_address(value)


class CIDRNetwork(str):
    """Tipo personalizado para CIDR en Pydantic."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )
    
    @classmethod
    def _validate(cls, value: str) -> str:
        return validate_cidr(value)


class Port(int):
    """Tipo personalizado para puerto en Pydantic."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.int_schema(),
        )
    
    @classmethod
    def _validate(cls, value: int) -> int:
        return validate_port(value)


class CVEId(str):
    """Tipo personalizado para CVE ID en Pydantic."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )
    
    @classmethod
    def _validate(cls, value: str) -> str:
        return validate_cve_id(value)


class Slug(str):
    """Tipo personalizado para slug en Pydantic."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )
    
    @classmethod
    def _validate(cls, value: str) -> str:
        return validate_slug(value)


# =============================================================================
# Factory de Validadores
# =============================================================================
def create_length_validator(
    min_length: int = 0,
    max_length: int = 255,
    field_name: str = "campo"
) -> Callable[[str], str]:
    """Crea un validador de longitud configurable."""
    def validator(value: str) -> str:
        return validate_length(value, min_length, max_length, field_name)
    return validator


def create_regex_validator(
    pattern: Union[str, re.Pattern],
    message: str
) -> Callable[[str], str]:
    """Crea un validador regex configurable."""
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    
    def validator(value: str) -> str:
        return validate_regex(value, pattern, message)
    return validator


# =============================================================================
# Exportar
# =============================================================================
__all__ = [
    # Validadores de red
    "validate_ipv4",
    "validate_ipv6",
    "validate_ip_address",
    "validate_cidr",
    "validate_ip_or_cidr",
    "validate_port",
    "validate_port_range",
    "validate_port_list",
    "validate_mac_address",
    # Validadores de identificadores
    "validate_hostname",
    "validate_fqdn",
    "validate_slug",
    "validate_uuid",
    # Validadores de seguridad
    "validate_cve_id",
    "validate_cpe",
    "validate_cvss_score",
    # Validadores de formato
    "validate_not_empty",
    "validate_length",
    "validate_regex",
    "validate_in_list",
    "validate_password_strength",
    # Tipos Pydantic
    "IPv4Address",
    "IPv6Address",
    "IPAddress",
    "CIDRNetwork",
    "Port",
    "CVEId",
    "Slug",
    # Factories
    "create_length_validator",
    "create_regex_validator",
]
