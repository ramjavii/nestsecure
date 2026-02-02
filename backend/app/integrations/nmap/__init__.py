# =============================================================================
# NESTSECURE - Nmap Integration Module
# =============================================================================
"""
Módulo de integración Nmap para NestSecure.

Este módulo proporciona una interfaz completa para ejecutar escaneos
Nmap y procesar sus resultados de forma tipada.

Componentes:
- NmapScanner: Cliente para ejecutar escaneos
- NmapParser: Parser de resultados XML
- Modelos: Dataclasses tipados para resultados
- Perfiles: Configuraciones predefinidas de escaneo
- Excepciones: Manejo de errores específicos

Uso básico:
    from app.integrations.nmap import NmapScanner, NmapScanResult
    
    scanner = NmapScanner()
    result = await scanner.scan("192.168.1.0/24", profile="standard")
    
    for host in result.hosts:
        print(f"{host.ip_address}: {len(host.open_ports)} open ports")
        for vuln in host.vulnerabilities:
            print(f"  - {vuln.title} ({vuln.severity})")

Modo Mock (testing):
    scanner = NmapScanner(mock_mode=True)
    result = await scanner.scan("192.168.1.1")  # Returns mock data
"""

# Cliente principal
from .client import (
    NmapScanner,
    quick_scan,
    full_scan,
    check_nmap_installed,
)

# Parser
from .parser import (
    NmapParser,
    parse_nmap_xml,
    parse_nmap_file,
)

# Modelos de datos
from .models import (
    NmapScanResult,
    NmapHost,
    NmapPort,
    NmapVulnerability,
    NmapOS,
    PortState,
    HostState,
)

# Perfiles de escaneo
from .profiles import (
    NmapProfile,
    ScanIntensity,
    SCAN_PROFILES,
    DEFAULT_PROFILE,
    QUICK_SCAN,
    DISCOVERY_SCAN,
    STANDARD_SCAN,
    FULL_SCAN,
    STEALTH_SCAN,
    AGGRESSIVE_SCAN,
    VULNERABILITY_SCAN,
    WEB_SCAN,
    DATABASE_SCAN,
    SMB_SCAN,
    UDP_SCAN,
    get_profile,
    get_all_profiles,
    get_profiles_by_category,
    create_custom_profile,
)

# Excepciones
from .exceptions import (
    NmapError,
    NmapNotFoundError,
    NmapTimeoutError,
    NmapPermissionError,
    NmapParseError,
    NmapTargetError,
    NmapExecutionError,
)


__all__ = [
    # Cliente
    "NmapScanner",
    "quick_scan",
    "full_scan",
    "check_nmap_installed",
    
    # Parser
    "NmapParser",
    "parse_nmap_xml",
    "parse_nmap_file",
    
    # Modelos
    "NmapScanResult",
    "NmapHost",
    "NmapPort",
    "NmapVulnerability",
    "NmapOS",
    "PortState",
    "HostState",
    
    # Perfiles
    "NmapProfile",
    "ScanIntensity",
    "SCAN_PROFILES",
    "DEFAULT_PROFILE",
    "QUICK_SCAN",
    "DISCOVERY_SCAN",
    "STANDARD_SCAN",
    "FULL_SCAN",
    "STEALTH_SCAN",
    "AGGRESSIVE_SCAN",
    "VULNERABILITY_SCAN",
    "WEB_SCAN",
    "DATABASE_SCAN",
    "SMB_SCAN",
    "UDP_SCAN",
    "get_profile",
    "get_all_profiles",
    "get_profiles_by_category",
    "create_custom_profile",
    
    # Excepciones
    "NmapError",
    "NmapNotFoundError",
    "NmapTimeoutError",
    "NmapPermissionError",
    "NmapParseError",
    "NmapTargetError",
    "NmapExecutionError",
]

__version__ = "1.0.0"
