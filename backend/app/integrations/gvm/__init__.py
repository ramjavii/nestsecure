# =============================================================================
# NESTSECURE - GVM (Greenbone Vulnerability Manager) Integration
# =============================================================================
"""
Integración con OpenVAS/GVM para escaneo de vulnerabilidades.

Este módulo proporciona:
- GVMClient: Cliente para comunicación con GVM
- GVMParser: Parser de reportes XML
- Modelos de datos GVM
- Excepciones específicas

Uso básico:
    from app.integrations.gvm import GVMClient
    
    async with GVMClient() as client:
        targets = await client.get_targets()
        task_id = await client.create_task(name="Scan", target_id=target_id)
        await client.start_task(task_id)
"""

from .client import GVMClient, get_gvm_client
from .models import (
    GVMSeverity,
    GVMTaskStatus,
    GVMTarget,
    GVMTask,
    GVMVulnerability,
    GVMHostResult,
    GVMReport,
    GVMScanConfig,
    GVMPortList,
)
from .parser import GVMParser
from .exceptions import (
    GVMError,
    GVMConnectionError,
    GVMAuthenticationError,
    GVMTimeoutError,
    GVMScanError,
    GVMNotFoundError,
    GVMConfigurationError,
)

__all__ = [
    # Client
    "GVMClient",
    "get_gvm_client",
    # Parser
    "GVMParser",
    # Models
    "GVMSeverity",
    "GVMTaskStatus",
    "GVMTarget",
    "GVMTask",
    "GVMVulnerability",
    "GVMHostResult",
    "GVMReport",
    "GVMScanConfig",
    "GVMPortList",
    # Exceptions
    "GVMError",
    "GVMConnectionError",
    "GVMAuthenticationError",
    "GVMTimeoutError",
    "GVMScanError",
    "GVMNotFoundError",
    "GVMConfigurationError",
]
