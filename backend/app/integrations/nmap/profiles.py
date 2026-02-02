# =============================================================================
# NESTSECURE - Nmap Scan Profiles
# =============================================================================
"""
Perfiles de escaneo Nmap predefinidos para diferentes casos de uso.

Cada perfil define argumentos optimizados para un escenario específico.
Los perfiles se pueden personalizar o extender según necesidades.

Perfiles disponibles:
- quick: Escaneo rápido de puertos comunes
- discovery: Descubrimiento de hosts en red
- standard: Escaneo balanceado con detección de versiones
- full: Escaneo completo de 65535 puertos
- stealth: Escaneo sigiloso (SYN scan)
- aggressive: Escaneo agresivo con todas las features
- vulnerability: Escaneo con scripts de vulnerabilidades
- web: Enfocado en servicios web (80, 443, 8080, etc.)
- database: Enfocado en bases de datos (3306, 5432, etc.)
- smb: Enfocado en servicios Windows/SMB
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ScanIntensity(Enum):
    """
    Niveles de intensidad de escaneo.
    
    Afecta la velocidad y el ruido del escaneo.
    """
    PARANOID = 0   # Muy lento, mínimo ruido
    SNEAKY = 1     # Lento, bajo ruido
    POLITE = 2     # Moderado, respeta recursos
    NORMAL = 3     # Default
    AGGRESSIVE = 4  # Rápido, más recursos
    INSANE = 5     # Muy rápido, máximo ruido


@dataclass
class NmapProfile:
    """
    Perfil de escaneo Nmap.
    
    Attributes:
        name: Nombre único del perfil
        display_name: Nombre para mostrar en UI
        description: Descripción del perfil
        arguments: Lista de argumentos Nmap
        ports: Especificación de puertos (--top-ports, -p, etc.)
        estimated_time_per_host: Tiempo estimado por host en segundos
        intensity: Nivel de intensidad
        requires_root: Si requiere privilegios de root
        scripts: Scripts NSE a ejecutar
        timing: Timing template (-T0 a -T5)
    """
    name: str
    display_name: str
    description: str
    arguments: List[str]
    ports: Optional[str] = None
    estimated_time_per_host: int = 60  # segundos
    intensity: ScanIntensity = ScanIntensity.NORMAL
    requires_root: bool = False
    scripts: List[str] = field(default_factory=list)
    timing: int = 3  # -T3 por default
    categories: List[str] = field(default_factory=list)
    
    def get_arguments_string(self) -> str:
        """Obtener argumentos como string."""
        return " ".join(self.arguments)
    
    def get_full_command(self, target: str, output_file: Optional[str] = None) -> List[str]:
        """
        Generar comando completo de Nmap.
        
        Args:
            target: IP o rango a escanear
            output_file: Archivo de salida XML (opcional)
            
        Returns:
            Lista de argumentos para subprocess
        """
        cmd = ["nmap"]
        cmd.extend(self.arguments)
        
        # Agregar timing si no está en arguments
        if not any(arg.startswith("-T") for arg in self.arguments):
            cmd.append(f"-T{self.timing}")
        
        # Agregar output XML si se especifica
        if output_file:
            cmd.extend(["-oX", output_file])
        
        # Target al final
        cmd.append(target)
        
        return cmd
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "estimated_time_per_host": self.estimated_time_per_host,
            "intensity": self.intensity.name,
            "requires_root": self.requires_root,
            "categories": self.categories,
        }


# =============================================================================
# PERFILES PREDEFINIDOS
# =============================================================================

QUICK_SCAN = NmapProfile(
    name="quick",
    display_name="Escaneo Rápido",
    description="Escaneo rápido de los 100 puertos más comunes. Ideal para reconocimiento inicial.",
    arguments=[
        "-sS",           # SYN scan (stealth)
        "-sV",           # Version detection
        "--top-ports", "100",  # Top 100 puertos
        "-O",            # OS detection
        "--version-light",  # Version detection ligera
    ],
    estimated_time_per_host=30,
    intensity=ScanIntensity.AGGRESSIVE,
    requires_root=True,
    timing=4,
    categories=["reconnaissance", "quick"],
)

DISCOVERY_SCAN = NmapProfile(
    name="discovery",
    display_name="Descubrimiento de Hosts",
    description="Descubre hosts activos en la red sin escanear puertos. Muy rápido.",
    arguments=[
        "-sn",           # No port scan (ping scan)
        "-PE",           # ICMP echo request
        "-PP",           # ICMP timestamp request
        "-PM",           # ICMP netmask request
        "-PS22,80,443",  # TCP SYN to common ports
        "-PA80,443",     # TCP ACK
        "-PU53",         # UDP to DNS
    ],
    estimated_time_per_host=5,
    intensity=ScanIntensity.AGGRESSIVE,
    requires_root=True,
    timing=4,
    categories=["reconnaissance", "discovery"],
)

STANDARD_SCAN = NmapProfile(
    name="standard",
    display_name="Escaneo Estándar",
    description="Escaneo balanceado con detección de versiones y OS. Recomendado para uso general.",
    arguments=[
        "-sS",           # SYN scan
        "-sV",           # Version detection
        "-sC",           # Default scripts
        "-O",            # OS detection
        "--top-ports", "1000",  # Top 1000 puertos
    ],
    estimated_time_per_host=120,
    intensity=ScanIntensity.NORMAL,
    requires_root=True,
    timing=3,
    categories=["general", "recommended"],
)

FULL_SCAN = NmapProfile(
    name="full",
    display_name="Escaneo Completo",
    description="Escaneo de todos los 65535 puertos TCP. Muy exhaustivo pero lento.",
    arguments=[
        "-sS",           # SYN scan
        "-sV",           # Version detection
        "-sC",           # Default scripts
        "-O",            # OS detection
        "-p-",           # All ports (1-65535)
        "--version-all",  # Try all probes
    ],
    estimated_time_per_host=600,
    intensity=ScanIntensity.NORMAL,
    requires_root=True,
    timing=3,
    categories=["thorough", "full"],
)

STEALTH_SCAN = NmapProfile(
    name="stealth",
    display_name="Escaneo Sigiloso",
    description="Escaneo lento y sigiloso para evitar detección por IDS/IPS.",
    arguments=[
        "-sS",           # SYN scan (no completa conexiones)
        "-sV",           # Version detection
        "--version-light",  # Minimal version probes
        "--top-ports", "500",
        "-f",            # Fragment packets
        "--data-length", "24",  # Add random data
    ],
    estimated_time_per_host=300,
    intensity=ScanIntensity.SNEAKY,
    requires_root=True,
    timing=1,  # Paranoid timing
    categories=["stealth", "evasion"],
)

AGGRESSIVE_SCAN = NmapProfile(
    name="aggressive",
    display_name="Escaneo Agresivo",
    description="Escaneo rápido y agresivo con todas las características. Genera mucho ruido.",
    arguments=[
        "-sS",           # SYN scan
        "-sV",           # Version detection
        "-sC",           # Default scripts
        "-O",            # OS detection
        "-A",            # Aggressive (enables -O, -sV, -sC, --traceroute)
        "--top-ports", "1000",
        "--version-all",  # All version probes
        "--osscan-guess",  # Guess OS
    ],
    estimated_time_per_host=180,
    intensity=ScanIntensity.AGGRESSIVE,
    requires_root=True,
    timing=4,
    categories=["aggressive", "thorough"],
)

VULNERABILITY_SCAN = NmapProfile(
    name="vulnerability",
    display_name="Escaneo de Vulnerabilidades",
    description="Ejecuta scripts de detección de vulnerabilidades (vuln, exploit, auth).",
    arguments=[
        "-sS",           # SYN scan
        "-sV",           # Version detection
        "--top-ports", "1000",
        "--script", "vuln,exploit,auth",  # Vulnerability scripts
    ],
    scripts=[
        "vuln",          # Vulnerability detection
        "exploit",       # Exploit detection
        "auth",          # Auth bypass detection
    ],
    estimated_time_per_host=600,
    intensity=ScanIntensity.NORMAL,
    requires_root=True,
    timing=3,
    categories=["vulnerability", "security"],
)

WEB_SCAN = NmapProfile(
    name="web",
    display_name="Escaneo Web",
    description="Enfocado en servicios web HTTP/HTTPS con scripts específicos.",
    arguments=[
        "-sS",           # SYN scan
        "-sV",           # Version detection
        "-p", "80,443,8080,8443,8000,8008,8888,3000,3001,5000,5001,9000,9443",
        "--script", "http-vuln*,http-enum,http-headers,http-methods,http-title,ssl-cert,ssl-enum-ciphers",
    ],
    scripts=[
        "http-vuln*",
        "http-enum",
        "http-headers",
        "http-methods",
        "http-title",
        "ssl-cert",
        "ssl-enum-ciphers",
    ],
    estimated_time_per_host=180,
    intensity=ScanIntensity.NORMAL,
    requires_root=True,
    timing=3,
    categories=["web", "http", "ssl"],
)

DATABASE_SCAN = NmapProfile(
    name="database",
    display_name="Escaneo de Bases de Datos",
    description="Enfocado en servicios de bases de datos con scripts específicos.",
    arguments=[
        "-sS",           # SYN scan
        "-sV",           # Version detection
        "-p", "1433,1434,3306,5432,5433,27017,27018,6379,9200,9300,11211,1521,1830",
        "--script", "mysql*,ms-sql*,pgsql*,mongodb*,redis*,oracle*",
    ],
    scripts=[
        "mysql*",
        "ms-sql*",
        "pgsql*",
        "mongodb*",
        "redis*",
        "oracle*",
    ],
    estimated_time_per_host=180,
    intensity=ScanIntensity.NORMAL,
    requires_root=True,
    timing=3,
    categories=["database", "data"],
)

SMB_SCAN = NmapProfile(
    name="smb",
    display_name="Escaneo SMB/Windows",
    description="Enfocado en servicios Windows (SMB, NetBIOS, RPC).",
    arguments=[
        "-sS",           # SYN scan
        "-sV",           # Version detection
        "-sU",           # UDP scan
        "-p", "T:135,139,445,1433,3389,5985,5986,U:137,138",
        "--script", "smb-vuln*,smb-enum*,smb2-vuln*,ms-sql*,rdp-*",
    ],
    scripts=[
        "smb-vuln*",
        "smb-enum*",
        "smb2-vuln*",
        "ms-sql*",
        "rdp-*",
    ],
    estimated_time_per_host=240,
    intensity=ScanIntensity.NORMAL,
    requires_root=True,
    timing=3,
    categories=["smb", "windows", "network"],
)

UDP_SCAN = NmapProfile(
    name="udp",
    display_name="Escaneo UDP",
    description="Escaneo de puertos UDP comunes. Lento pero necesario para servicios como DNS, SNMP.",
    arguments=[
        "-sU",           # UDP scan
        "-sV",           # Version detection
        "--top-ports", "100",
        "--version-intensity", "0",  # Light version detection
    ],
    estimated_time_per_host=300,
    intensity=ScanIntensity.POLITE,
    requires_root=True,
    timing=3,
    categories=["udp", "thorough"],
)


# =============================================================================
# REGISTRO DE PERFILES
# =============================================================================

SCAN_PROFILES: Dict[str, NmapProfile] = {
    "quick": QUICK_SCAN,
    "discovery": DISCOVERY_SCAN,
    "standard": STANDARD_SCAN,
    "full": FULL_SCAN,
    "stealth": STEALTH_SCAN,
    "aggressive": AGGRESSIVE_SCAN,
    "vulnerability": VULNERABILITY_SCAN,
    "web": WEB_SCAN,
    "database": DATABASE_SCAN,
    "smb": SMB_SCAN,
    "udp": UDP_SCAN,
}

# Alias para compatibilidad
DEFAULT_PROFILE = STANDARD_SCAN


def get_profile(name: str) -> Optional[NmapProfile]:
    """
    Obtener un perfil por nombre.
    
    Args:
        name: Nombre del perfil
        
    Returns:
        NmapProfile o None si no existe
    """
    return SCAN_PROFILES.get(name.lower())


def get_all_profiles() -> List[NmapProfile]:
    """
    Obtener todos los perfiles disponibles.
    
    Returns:
        Lista de perfiles
    """
    return list(SCAN_PROFILES.values())


def get_profiles_by_category(category: str) -> List[NmapProfile]:
    """
    Obtener perfiles por categoría.
    
    Args:
        category: Categoría a filtrar
        
    Returns:
        Lista de perfiles que pertenecen a la categoría
    """
    return [p for p in SCAN_PROFILES.values() if category.lower() in p.categories]


def create_custom_profile(
    name: str,
    display_name: str,
    description: str,
    arguments: List[str],
    **kwargs
) -> NmapProfile:
    """
    Crear un perfil personalizado.
    
    Args:
        name: Nombre único
        display_name: Nombre para mostrar
        description: Descripción
        arguments: Lista de argumentos Nmap
        **kwargs: Otros atributos opcionales
        
    Returns:
        NmapProfile personalizado
    """
    return NmapProfile(
        name=name,
        display_name=display_name,
        description=description,
        arguments=arguments,
        **kwargs
    )
