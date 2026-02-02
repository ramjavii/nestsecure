# =============================================================================
# NESTSECURE - Nuclei Integration Module
# =============================================================================
"""
Módulo de integración Nuclei para NestSecure.

Este módulo proporciona una interfaz completa para ejecutar escaneos
de vulnerabilidades con Nuclei y procesar sus resultados.

Componentes:
- NucleiScanner: Cliente para ejecutar escaneos
- NucleiParser: Parser de resultados JSON Lines
- Modelos: Dataclasses tipados para resultados
- Perfiles: Configuraciones predefinidas de escaneo
- Excepciones: Manejo de errores específicos

Uso básico:
    from app.integrations.nuclei import NucleiScanner, NucleiScanResult
    
    scanner = NucleiScanner()
    result = await scanner.scan("https://example.com", profile="standard")
    
    print(f"Found {result.total_findings} vulnerabilities:")
    for finding in result.findings:
        print(f"  [{finding.severity.value}] {finding.title}")
        if finding.cve:
            print(f"    CVE: {finding.cve}")

Modo Mock (testing):
    scanner = NucleiScanner(mock_mode=True)
    result = await scanner.scan("https://example.com")  # Returns mock data
"""

# Cliente principal
from .client import (
    NucleiScanner,
    quick_scan,
    full_scan,
    check_nuclei_installed,
)

# Parser
from .parser import (
    NucleiParser,
    parse_nuclei_output,
    parse_nuclei_file,
)

# Modelos de datos
from .models import (
    NucleiScanResult,
    NucleiFinding,
    NucleiTemplate,
    NucleiMatcher,
    Severity,
    TemplateType,
)

# Perfiles de escaneo
from .profiles import (
    NucleiProfile,
    ScanSpeed,
    SCAN_PROFILES,
    DEFAULT_PROFILE,
    QUICK_SCAN,
    STANDARD_SCAN,
    FULL_SCAN,
    CVE_SCAN,
    WEB_SCAN,
    MISCONFIG_SCAN,
    EXPOSURE_SCAN,
    TAKEOVER_SCAN,
    NETWORK_SCAN,
    TECH_DETECT_SCAN,
    get_profile,
    get_all_profiles,
    create_custom_profile,
)

# Excepciones
from .exceptions import (
    NucleiError,
    NucleiNotFoundError,
    NucleiTimeoutError,
    NucleiTemplateError,
    NucleiParseError,
    NucleiTargetError,
    NucleiExecutionError,
    NucleiRateLimitError,
)


__all__ = [
    # Cliente
    "NucleiScanner",
    "quick_scan",
    "full_scan",
    "check_nuclei_installed",
    
    # Parser
    "NucleiParser",
    "parse_nuclei_output",
    "parse_nuclei_file",
    
    # Modelos
    "NucleiScanResult",
    "NucleiFinding",
    "NucleiTemplate",
    "NucleiMatcher",
    "Severity",
    "TemplateType",
    
    # Perfiles
    "NucleiProfile",
    "ScanSpeed",
    "SCAN_PROFILES",
    "DEFAULT_PROFILE",
    "QUICK_SCAN",
    "STANDARD_SCAN",
    "FULL_SCAN",
    "CVE_SCAN",
    "WEB_SCAN",
    "MISCONFIG_SCAN",
    "EXPOSURE_SCAN",
    "TAKEOVER_SCAN",
    "NETWORK_SCAN",
    "TECH_DETECT_SCAN",
    "get_profile",
    "get_all_profiles",
    "create_custom_profile",
    
    # Excepciones
    "NucleiError",
    "NucleiNotFoundError",
    "NucleiTimeoutError",
    "NucleiTemplateError",
    "NucleiParseError",
    "NucleiTargetError",
    "NucleiExecutionError",
    "NucleiRateLimitError",
]

__version__ = "1.0.0"
