# =============================================================================
# NESTSECURE - Integración OWASP ZAP
# =============================================================================
"""
Integración con OWASP ZAP (Zed Attack Proxy) para escaneos DAST.

Este módulo proporciona:
- Cliente API para comunicarse con ZAP
- Configuración de contextos y políticas de escaneo
- Modos de escaneo: Spider, Ajax Spider, Active Scan, Passive Scan, API Scan
- Parseo de alertas y mapeo a vulnerabilidades

Componentes:
- ZapClient: Cliente para la API de ZAP
- ZapScanner: Orquestador de escaneos
- ZapAlertParser: Parser de alertas a vulnerabilidades

Uso:
    from app.integrations.zap import ZapClient, ZapScanner
    
    # Crear cliente
    client = ZapClient(host="zap", port=8080)
    
    # Verificar conexión
    version = await client.get_version()
    
    # Iniciar escaneo
    scanner = ZapScanner(client)
    results = await scanner.full_scan("http://target.local")
"""

from app.integrations.zap.client import ZapClient
from app.integrations.zap.scanner import ZapScanner, ZapScanMode
from app.integrations.zap.parser import ZapAlertParser
from app.integrations.zap.config import (
    ZAP_DEFAULT_HOST,
    ZAP_DEFAULT_PORT,
    ZAP_SCAN_POLICIES,
    ZAP_ALERT_RISKS,
    ZAP_ALERT_CONFIDENCES,
)

__all__ = [
    "ZapClient",
    "ZapScanner",
    "ZapScanMode",
    "ZapAlertParser",
    "ZAP_DEFAULT_HOST",
    "ZAP_DEFAULT_PORT",
    "ZAP_SCAN_POLICIES",
    "ZAP_ALERT_RISKS",
    "ZAP_ALERT_CONFIDENCES",
]
