# =============================================================================
# NESTSECURE - Utilidades para CPE (Common Platform Enumeration)
# =============================================================================
"""
Utilidades para trabajar con identificadores CPE 2.3.

CPE (Common Platform Enumeration) es un esquema de nombres estructurados
para sistemas de información, software y paquetes.

Formato CPE 2.3:
cpe:2.3:part:vendor:product:version:update:edition:language:sw_edition:target_sw:target_hw:other

Parts:
- 'a' = Application
- 'h' = Hardware
- 'o' = Operating System
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .constants import Patterns


# =============================================================================
# Dataclass para CPE
# =============================================================================
@dataclass
class CPE:
    """
    Representa un identificador CPE 2.3.
    
    Attributes:
        part: Tipo de sistema (a=app, h=hardware, o=os)
        vendor: Fabricante/vendor
        product: Nombre del producto
        version: Versión
        update: Actualización/patch
        edition: Edición
        language: Idioma
        sw_edition: Edición de software
        target_sw: Software objetivo
        target_hw: Hardware objetivo
        other: Otros atributos
    """
    part: str
    vendor: str
    product: str
    version: str = "*"
    update: str = "*"
    edition: str = "*"
    language: str = "*"
    sw_edition: str = "*"
    target_sw: str = "*"
    target_hw: str = "*"
    other: str = "*"
    
    @property
    def part_name(self) -> str:
        """Retorna el nombre legible del part."""
        parts = {
            "a": "Application",
            "h": "Hardware",
            "o": "Operating System",
            "*": "Any",
            "-": "Not Applicable",
        }
        return parts.get(self.part, "Unknown")
    
    def to_uri(self) -> str:
        """Convierte a formato URI CPE 2.3."""
        components = [
            "cpe", "2.3",
            self.part,
            self._escape(self.vendor),
            self._escape(self.product),
            self._escape(self.version),
            self._escape(self.update),
            self._escape(self.edition),
            self._escape(self.language),
            self._escape(self.sw_edition),
            self._escape(self.target_sw),
            self._escape(self.target_hw),
            self._escape(self.other),
        ]
        return ":".join(components)
    
    def to_dict(self) -> Dict[str, str]:
        """Convierte a diccionario."""
        return {
            "part": self.part,
            "part_name": self.part_name,
            "vendor": self.vendor,
            "product": self.product,
            "version": self.version,
            "update": self.update,
            "edition": self.edition,
            "language": self.language,
            "sw_edition": self.sw_edition,
            "target_sw": self.target_sw,
            "target_hw": self.target_hw,
            "other": self.other,
        }
    
    def matches(self, other: "CPE") -> bool:
        """
        Verifica si este CPE coincide con otro.
        Usa wildcards (*) para matches parciales.
        """
        for attr in ["part", "vendor", "product", "version"]:
            self_val = getattr(self, attr)
            other_val = getattr(other, attr)
            
            # Wildcard match
            if self_val == "*" or other_val == "*":
                continue
            
            # Not applicable
            if self_val == "-" or other_val == "-":
                if self_val != other_val:
                    return False
                continue
            
            # Exact match (case insensitive)
            if self_val.lower() != other_val.lower():
                return False
        
        return True
    
    @staticmethod
    def _escape(value: str) -> str:
        """Escapa caracteres especiales en componentes CPE."""
        if value in ("*", "-"):
            return value
        
        # Escapar caracteres especiales
        special = r'\:*?#'
        result = ""
        for char in value:
            if char in special:
                result += f"\\{char}"
            else:
                result += char
        return result
    
    @staticmethod
    def _unescape(value: str) -> str:
        """Desescapa caracteres en componentes CPE."""
        if value in ("*", "-"):
            return value
        
        result = ""
        i = 0
        while i < len(value):
            if value[i] == "\\" and i + 1 < len(value):
                result += value[i + 1]
                i += 2
            else:
                result += value[i]
                i += 1
        return result


# =============================================================================
# Funciones de Parsing
# =============================================================================
def parse_cpe(cpe_string: str) -> Optional[CPE]:
    """
    Parsea un string CPE 2.3 a objeto CPE.
    
    Args:
        cpe_string: String en formato CPE 2.3
    
    Returns:
        Objeto CPE o None si el formato es inválido
    
    Example:
        >>> cpe = parse_cpe("cpe:2.3:a:apache:http_server:2.4.51:*:*:*:*:*:*:*")
        >>> cpe.vendor
        'apache'
    """
    if not cpe_string or not cpe_string.startswith("cpe:2.3:"):
        return None
    
    # Dividir componentes
    parts = cpe_string.split(":")
    
    if len(parts) < 5:
        return None
    
    # Extraer componentes (con valores por defecto)
    def get_part(index: int, default: str = "*") -> str:
        if index < len(parts):
            val = parts[index]
            return CPE._unescape(val) if val else default
        return default
    
    try:
        return CPE(
            part=get_part(2),
            vendor=get_part(3),
            product=get_part(4),
            version=get_part(5),
            update=get_part(6),
            edition=get_part(7),
            language=get_part(8),
            sw_edition=get_part(9),
            target_sw=get_part(10),
            target_hw=get_part(11),
            other=get_part(12),
        )
    except Exception:
        return None


def is_valid_cpe(cpe_string: str) -> bool:
    """Verifica si un string es un CPE válido."""
    return parse_cpe(cpe_string) is not None


def create_cpe(
    part: str,
    vendor: str,
    product: str,
    version: str = "*",
    **kwargs
) -> CPE:
    """
    Crea un nuevo CPE.
    
    Args:
        part: 'a' (app), 'h' (hardware), 'o' (os)
        vendor: Nombre del vendor
        product: Nombre del producto
        version: Versión
        **kwargs: Otros componentes opcionales
    
    Returns:
        Objeto CPE
    """
    return CPE(
        part=part,
        vendor=vendor.lower().replace(" ", "_"),
        product=product.lower().replace(" ", "_"),
        version=version,
        **kwargs
    )


# =============================================================================
# Funciones de Búsqueda y Match
# =============================================================================
def cpe_matches_pattern(cpe: CPE, pattern: CPE) -> bool:
    """
    Verifica si un CPE coincide con un patrón.
    
    El patrón puede usar wildcards (*) para cualquier valor.
    
    Args:
        cpe: CPE a verificar
        pattern: Patrón CPE (puede tener wildcards)
    
    Returns:
        True si coincide
    """
    return pattern.matches(cpe)


def find_matching_cpes(
    cpe: CPE,
    cpe_list: List[str]
) -> List[str]:
    """
    Encuentra CPEs que coinciden con un patrón.
    
    Args:
        cpe: Patrón CPE a buscar
        cpe_list: Lista de strings CPE
    
    Returns:
        Lista de CPEs que coinciden
    """
    matches = []
    for cpe_str in cpe_list:
        parsed = parse_cpe(cpe_str)
        if parsed and cpe.matches(parsed):
            matches.append(cpe_str)
    return matches


def extract_vendor_product(cpe_string: str) -> Optional[Tuple[str, str]]:
    """
    Extrae vendor y producto de un CPE.
    
    Args:
        cpe_string: String CPE
    
    Returns:
        Tuple (vendor, product) o None
    """
    cpe = parse_cpe(cpe_string)
    if cpe:
        return (cpe.vendor, cpe.product)
    return None


def extract_version(cpe_string: str) -> Optional[str]:
    """
    Extrae la versión de un CPE.
    
    Args:
        cpe_string: String CPE
    
    Returns:
        Versión o None
    """
    cpe = parse_cpe(cpe_string)
    if cpe and cpe.version not in ("*", "-"):
        return cpe.version
    return None


# =============================================================================
# Funciones de Normalización
# =============================================================================
def normalize_cpe(cpe_string: str) -> Optional[str]:
    """
    Normaliza un CPE a formato estándar.
    
    Args:
        cpe_string: String CPE (puede ser mal formado)
    
    Returns:
        CPE normalizado o None si es inválido
    """
    cpe = parse_cpe(cpe_string)
    if cpe:
        return cpe.to_uri()
    return None


def cpe_to_human_readable(cpe_string: str) -> str:
    """
    Convierte un CPE a formato legible.
    
    Args:
        cpe_string: String CPE
    
    Returns:
        String legible (ej: "Apache HTTP Server 2.4.51")
    """
    cpe = parse_cpe(cpe_string)
    if not cpe:
        return cpe_string
    
    # Formatear vendor y product
    vendor = cpe.vendor.replace("_", " ").title()
    product = cpe.product.replace("_", " ").title()
    
    result = f"{vendor} {product}"
    
    if cpe.version not in ("*", "-"):
        result += f" {cpe.version}"
    
    return result


# =============================================================================
# Funciones para búsqueda en NVD
# =============================================================================
def build_cpe_search_query(
    vendor: Optional[str] = None,
    product: Optional[str] = None,
    version: Optional[str] = None,
    part: str = "a"
) -> str:
    """
    Construye un CPE para búsqueda en NVD.
    
    Args:
        vendor: Vendor a buscar
        product: Producto a buscar
        version: Versión a buscar
        part: Tipo (a, h, o)
    
    Returns:
        String CPE para búsqueda
    """
    cpe = CPE(
        part=part,
        vendor=vendor.lower().replace(" ", "_") if vendor else "*",
        product=product.lower().replace(" ", "_") if product else "*",
        version=version or "*",
    )
    return cpe.to_uri()


# =============================================================================
# Exportar
# =============================================================================
__all__ = [
    "CPE",
    "parse_cpe",
    "is_valid_cpe",
    "create_cpe",
    "cpe_matches_pattern",
    "find_matching_cpes",
    "extract_vendor_product",
    "extract_version",
    "normalize_cpe",
    "cpe_to_human_readable",
    "build_cpe_search_query",
]
