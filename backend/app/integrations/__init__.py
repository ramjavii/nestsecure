# =============================================================================
# NESTSECURE - Integraciones Externas
# =============================================================================
"""
Módulo de integraciones con sistemas externos.

Submódulos:
- gvm: Greenbone Vulnerability Manager (OpenVAS)
- nmap: Network Mapper Scanner
- nuclei: Project Discovery Nuclei Scanner
- nvd: National Vulnerability Database (futuro)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gvm import GVMClient
    from .nmap import NmapScanner
    from .nuclei import NucleiScanner

__all__ = [
    "GVMClient",
    "NmapScanner",
    "NucleiScanner",
]
