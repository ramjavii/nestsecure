# =============================================================================
# NESTSECURE - Integraciones Externas
# =============================================================================
"""
Módulo de integraciones con sistemas externos.

Submódulos:
- gvm: Greenbone Vulnerability Manager (OpenVAS)
- nvd: National Vulnerability Database (futuro)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gvm import GVMClient

__all__ = ["GVMClient"]
