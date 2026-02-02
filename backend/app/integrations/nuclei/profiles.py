# =============================================================================
# NESTSECURE - Nuclei Scan Profiles
# =============================================================================
"""
Perfiles de escaneo Nuclei predefinidos para diferentes casos de uso.

Cada perfil define templates y configuraciones optimizadas
para un escenario específico de escaneo.

Perfiles disponibles:
- quick: Escaneo rápido con templates críticos
- standard: Escaneo balanceado
- full: Escaneo exhaustivo con todos los templates
- cves: Enfocado en CVEs conocidos
- web: Vulnerabilidades web comunes (XSS, SQLi, etc.)
- misconfig: Misconfigurations
- exposures: Exposiciones de datos sensibles
- takeovers: Subdomain takeovers
- network: Vulnerabilidades de red
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ScanSpeed(Enum):
    """
    Velocidades de escaneo.
    
    Afecta rate limiting y concurrencia.
    """
    SLOW = "slow"         # Rate limit conservative
    NORMAL = "normal"     # Default
    FAST = "fast"         # Aggressive but reasonable
    INSANE = "insane"     # Maximum speed


@dataclass
class NucleiProfile:
    """
    Perfil de escaneo Nuclei.
    
    Attributes:
        name: Nombre único del perfil
        display_name: Nombre para mostrar en UI
        description: Descripción del perfil
        tags: Tags de templates a incluir
        exclude_tags: Tags de templates a excluir
        severities: Severidades a incluir
        templates: Templates específicos a usar
        exclude_templates: Templates a excluir
        rate_limit: Requests por segundo
        concurrency: Templates concurrentes
        bulk_size: Hosts por batch
        timeout: Timeout por request en segundos
        retries: Reintentos por request
        estimated_time_per_target: Tiempo estimado por target
        speed: Velocidad del escaneo
    """
    name: str
    display_name: str
    description: str
    tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)
    severities: List[str] = field(default_factory=lambda: ["critical", "high", "medium", "low", "info"])
    templates: List[str] = field(default_factory=list)
    exclude_templates: List[str] = field(default_factory=list)
    rate_limit: int = 150
    concurrency: int = 25
    bulk_size: int = 25
    timeout: int = 10
    retries: int = 2
    estimated_time_per_target: int = 60
    speed: ScanSpeed = ScanSpeed.NORMAL
    
    def get_arguments(self) -> List[str]:
        """
        Generar argumentos de línea de comandos para Nuclei.
        
        Returns:
            Lista de argumentos
        """
        args = []
        
        # Tags
        if self.tags:
            args.extend(["-tags", ",".join(self.tags)])
        
        # Exclude tags
        if self.exclude_tags:
            args.extend(["-exclude-tags", ",".join(self.exclude_tags)])
        
        # Severities
        if self.severities and len(self.severities) < 5:
            args.extend(["-severity", ",".join(self.severities)])
        
        # Specific templates
        if self.templates:
            for t in self.templates:
                args.extend(["-t", t])
        
        # Exclude templates
        if self.exclude_templates:
            for t in self.exclude_templates:
                args.extend(["-exclude", t])
        
        # Rate limiting
        args.extend(["-rate-limit", str(self.rate_limit)])
        
        # Concurrency
        args.extend(["-c", str(self.concurrency)])
        args.extend(["-bulk-size", str(self.bulk_size)])
        
        # Timeout y retries
        args.extend(["-timeout", str(self.timeout)])
        args.extend(["-retries", str(self.retries)])
        
        # JSON output
        args.append("-json")
        
        return args
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "tags": self.tags,
            "severities": self.severities,
            "estimated_time_per_target": self.estimated_time_per_target,
            "speed": self.speed.value,
        }


# =============================================================================
# PERFILES PREDEFINIDOS
# =============================================================================

QUICK_SCAN = NucleiProfile(
    name="quick",
    display_name="Escaneo Rápido",
    description="Escaneo rápido enfocado en vulnerabilidades críticas y altas.",
    tags=["cve", "rce", "sqli", "ssrf", "lfi"],
    severities=["critical", "high"],
    rate_limit=200,
    concurrency=50,
    bulk_size=50,
    timeout=5,
    retries=1,
    estimated_time_per_target=30,
    speed=ScanSpeed.FAST,
)

STANDARD_SCAN = NucleiProfile(
    name="standard",
    display_name="Escaneo Estándar",
    description="Escaneo balanceado con los templates más relevantes.",
    tags=["cve", "vuln", "exposure", "misconfig", "tech"],
    exclude_tags=["dos", "fuzz", "intrusive"],
    severities=["critical", "high", "medium"],
    rate_limit=150,
    concurrency=25,
    bulk_size=25,
    timeout=10,
    retries=2,
    estimated_time_per_target=120,
    speed=ScanSpeed.NORMAL,
)

FULL_SCAN = NucleiProfile(
    name="full",
    display_name="Escaneo Completo",
    description="Escaneo exhaustivo con todos los templates disponibles.",
    tags=[],  # Sin filtro de tags = todos
    exclude_tags=["dos", "intrusive"],  # Excluir solo DoS
    severities=["critical", "high", "medium", "low", "info"],
    rate_limit=100,
    concurrency=20,
    bulk_size=20,
    timeout=15,
    retries=3,
    estimated_time_per_target=600,
    speed=ScanSpeed.SLOW,
)

CVE_SCAN = NucleiProfile(
    name="cves",
    display_name="Escaneo de CVEs",
    description="Enfocado en detectar CVEs conocidos.",
    tags=["cve"],
    severities=["critical", "high", "medium"],
    rate_limit=150,
    concurrency=30,
    bulk_size=30,
    timeout=10,
    retries=2,
    estimated_time_per_target=180,
    speed=ScanSpeed.NORMAL,
)

WEB_SCAN = NucleiProfile(
    name="web",
    display_name="Escaneo Web",
    description="Vulnerabilidades web comunes (XSS, SQLi, SSRF, etc.).",
    tags=["xss", "sqli", "ssrf", "lfi", "rfi", "redirect", "injection"],
    severities=["critical", "high", "medium"],
    rate_limit=100,
    concurrency=20,
    bulk_size=20,
    timeout=10,
    retries=2,
    estimated_time_per_target=180,
    speed=ScanSpeed.NORMAL,
)

MISCONFIG_SCAN = NucleiProfile(
    name="misconfig",
    display_name="Misconfiguraciones",
    description="Detectar configuraciones incorrectas y defaults.",
    tags=["misconfig", "default-login", "config"],
    severities=["critical", "high", "medium", "low"],
    rate_limit=150,
    concurrency=30,
    bulk_size=30,
    timeout=8,
    retries=2,
    estimated_time_per_target=90,
    speed=ScanSpeed.NORMAL,
)

EXPOSURE_SCAN = NucleiProfile(
    name="exposures",
    display_name="Exposiciones",
    description="Detectar datos sensibles expuestos.",
    tags=["exposure", "token", "api-key", "secret", "leak"],
    severities=["critical", "high", "medium", "low", "info"],
    rate_limit=150,
    concurrency=30,
    bulk_size=30,
    timeout=8,
    retries=2,
    estimated_time_per_target=90,
    speed=ScanSpeed.NORMAL,
)

TAKEOVER_SCAN = NucleiProfile(
    name="takeover",
    display_name="Subdomain Takeover",
    description="Detectar posibilidades de subdomain takeover.",
    tags=["takeover"],
    severities=["critical", "high", "medium"],
    rate_limit=200,
    concurrency=50,
    bulk_size=50,
    timeout=10,
    retries=2,
    estimated_time_per_target=30,
    speed=ScanSpeed.FAST,
)

NETWORK_SCAN = NucleiProfile(
    name="network",
    display_name="Escaneo de Red",
    description="Vulnerabilidades de servicios de red.",
    tags=["network", "ssh", "ftp", "rdp", "smb", "telnet"],
    severities=["critical", "high", "medium"],
    rate_limit=100,
    concurrency=20,
    bulk_size=20,
    timeout=15,
    retries=3,
    estimated_time_per_target=120,
    speed=ScanSpeed.NORMAL,
)

TECH_DETECT_SCAN = NucleiProfile(
    name="tech-detect",
    display_name="Detección de Tecnologías",
    description="Identificar tecnologías y frameworks utilizados.",
    tags=["tech", "detect", "fingerprint"],
    severities=["info"],
    rate_limit=200,
    concurrency=50,
    bulk_size=50,
    timeout=5,
    retries=1,
    estimated_time_per_target=20,
    speed=ScanSpeed.FAST,
)


# =============================================================================
# REGISTRO DE PERFILES
# =============================================================================

SCAN_PROFILES: Dict[str, NucleiProfile] = {
    "quick": QUICK_SCAN,
    "standard": STANDARD_SCAN,
    "full": FULL_SCAN,
    "cves": CVE_SCAN,
    "web": WEB_SCAN,
    "misconfig": MISCONFIG_SCAN,
    "exposures": EXPOSURE_SCAN,
    "takeover": TAKEOVER_SCAN,
    "network": NETWORK_SCAN,
    "tech-detect": TECH_DETECT_SCAN,
}

DEFAULT_PROFILE = STANDARD_SCAN


def get_profile(name: str) -> Optional[NucleiProfile]:
    """
    Obtener un perfil por nombre.
    
    Args:
        name: Nombre del perfil
        
    Returns:
        NucleiProfile o None si no existe
    """
    return SCAN_PROFILES.get(name.lower())


def get_all_profiles() -> List[NucleiProfile]:
    """
    Obtener todos los perfiles disponibles.
    
    Returns:
        Lista de perfiles
    """
    return list(SCAN_PROFILES.values())


def create_custom_profile(
    name: str,
    display_name: str,
    description: str,
    **kwargs
) -> NucleiProfile:
    """
    Crear un perfil personalizado.
    
    Args:
        name: Nombre único
        display_name: Nombre para mostrar
        description: Descripción
        **kwargs: Otros atributos opcionales
        
    Returns:
        NucleiProfile personalizado
    """
    return NucleiProfile(
        name=name,
        display_name=display_name,
        description=description,
        **kwargs
    )
