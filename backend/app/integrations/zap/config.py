# =============================================================================
# NESTSECURE - Configuración ZAP
# =============================================================================
"""
Configuración y constantes para la integración con OWASP ZAP.
"""

from typing import Dict, Final


# =============================================================================
# CONFIGURACIÓN DE CONEXIÓN
# =============================================================================

ZAP_DEFAULT_HOST: Final[str] = "zap"
ZAP_DEFAULT_PORT: Final[int] = 8080
ZAP_DEFAULT_TIMEOUT: Final[int] = 3600  # 1 hora
ZAP_API_VERSION: Final[str] = "JSON"


# =============================================================================
# POLÍTICAS DE ESCANEO
# =============================================================================

class ZapScanPolicy:
    """Políticas predefinidas de escaneo."""
    DEFAULT = "Default Policy"
    LIGHT = "Light"
    MEDIUM = "Medium"
    HIGH = "High"
    INSANE = "Insane"


ZAP_SCAN_POLICIES: Dict[str, Dict] = {
    "quick": {
        "name": "Quick Scan",
        "description": "Escaneo rápido - Spider + pasivo solamente",
        "spider": True,
        "ajax_spider": False,
        "active_scan": False,
        "timeout": 300,  # 5 minutos
    },
    "standard": {
        "name": "Standard Scan",
        "description": "Escaneo estándar - Spider + pasivo + activo básico",
        "spider": True,
        "ajax_spider": False,
        "active_scan": True,
        "policy": ZapScanPolicy.MEDIUM,
        "timeout": 1800,  # 30 minutos
    },
    "full": {
        "name": "Full Scan",
        "description": "Escaneo completo - Spider + Ajax Spider + activo completo",
        "spider": True,
        "ajax_spider": True,
        "active_scan": True,
        "policy": ZapScanPolicy.HIGH,
        "timeout": 3600,  # 1 hora
    },
    "api": {
        "name": "API Scan",
        "description": "Escaneo de API REST/GraphQL",
        "spider": False,
        "ajax_spider": False,
        "active_scan": True,
        "api_scan": True,
        "policy": ZapScanPolicy.DEFAULT,
        "timeout": 1800,  # 30 minutos
    },
    "passive": {
        "name": "Passive Only",
        "description": "Solo análisis pasivo - sin ataques activos",
        "spider": True,
        "ajax_spider": False,
        "active_scan": False,
        "timeout": 600,  # 10 minutos
    },
    "spa": {
        "name": "SPA Scan",
        "description": "Escaneo para Single Page Applications",
        "spider": True,
        "ajax_spider": True,
        "active_scan": True,
        "policy": ZapScanPolicy.MEDIUM,
        "timeout": 2400,  # 40 minutos
    },
}


# =============================================================================
# MAPEO DE RIESGOS DE ALERTAS
# =============================================================================

# Risk levels de ZAP
ZAP_ALERT_RISKS: Dict[int, str] = {
    0: "INFORMATIONAL",
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
}

# Confidence levels de ZAP
ZAP_ALERT_CONFIDENCES: Dict[int, str] = {
    0: "FALSE_POSITIVE",
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
    4: "CONFIRMED",
}


# =============================================================================
# MAPEO A SEVERIDADES DE NESTSECURE
# =============================================================================

ZAP_RISK_TO_SEVERITY: Dict[int, str] = {
    0: "info",
    1: "low",
    2: "medium",
    3: "high",
}

# CWE a CVE mapping para alertas comunes de ZAP
ZAP_CWE_MAPPING: Dict[int, Dict] = {
    79: {"name": "Cross-site Scripting (XSS)", "owasp_top_10": "A03:2021"},
    89: {"name": "SQL Injection", "owasp_top_10": "A03:2021"},
    78: {"name": "OS Command Injection", "owasp_top_10": "A03:2021"},
    22: {"name": "Path Traversal", "owasp_top_10": "A01:2021"},
    352: {"name": "Cross-Site Request Forgery (CSRF)", "owasp_top_10": "A01:2021"},
    601: {"name": "Open Redirect", "owasp_top_10": "A01:2021"},
    611: {"name": "XML External Entity (XXE)", "owasp_top_10": "A05:2021"},
    918: {"name": "Server-Side Request Forgery (SSRF)", "owasp_top_10": "A10:2021"},
    200: {"name": "Information Exposure", "owasp_top_10": "A01:2021"},
    209: {"name": "Information Exposure Through Error Messages", "owasp_top_10": "A01:2021"},
    311: {"name": "Missing Encryption", "owasp_top_10": "A02:2021"},
    319: {"name": "Cleartext Transmission", "owasp_top_10": "A02:2021"},
    326: {"name": "Weak Cryptography", "owasp_top_10": "A02:2021"},
    502: {"name": "Deserialization of Untrusted Data", "owasp_top_10": "A08:2021"},
    614: {"name": "Sensitive Cookie Without Secure Flag", "owasp_top_10": "A05:2021"},
    693: {"name": "Protection Mechanism Failure", "owasp_top_10": "A05:2021"},
    1021: {"name": "Improper Restriction of Rendered UI Layers", "owasp_top_10": "A05:2021"},
}


# =============================================================================
# REGLAS DE ESCANEO ACTIVO POR CATEGORÍA
# =============================================================================

ZAP_ACTIVE_SCAN_RULES: Dict[str, list] = {
    "injection": [
        40012,  # Cross Site Scripting (Reflected)
        40014,  # Cross Site Scripting (Persistent)
        40016,  # Cross Site Scripting (Persistent) - Prime
        40017,  # Cross Site Scripting (Persistent) - Spider
        40018,  # SQL Injection
        40019,  # SQL Injection - MySQL
        40020,  # SQL Injection - Hypersonic SQL
        40021,  # SQL Injection - Oracle
        40022,  # SQL Injection - PostgreSQL
        40024,  # SQL Injection - SQLite
        40026,  # Cross Site Scripting (DOM Based)
        90018,  # Advanced SQL Injection
        90020,  # Remote OS Command Injection
    ],
    "authentication": [
        10010,  # Cookie No HttpOnly Flag
        10011,  # Cookie Without Secure Flag
        10017,  # Cross-Domain JavaScript Source File Inclusion
        10023,  # Information Disclosure - Debug Error Messages
        10024,  # Information Disclosure - Sensitive Information in URL
        10025,  # Information Disclosure - Sensitive Information in HTTP Referrer Header
        10027,  # Information Disclosure - Suspicious Comments
    ],
    "configuration": [
        10015,  # Incomplete or No Cache-control and Pragma HTTP Header Set
        10016,  # Web Browser XSS Protection Not Enabled
        10020,  # X-Frame-Options Header Not Set
        10021,  # X-Content-Type-Options Header Missing
        10035,  # Strict-Transport-Security Header Not Set
        10036,  # Server Leaks Version Information via "Server" HTTP Response Header
        10037,  # Server Leaks Information via "X-Powered-By" HTTP Response Header
        10038,  # Content Security Policy (CSP) Header Not Set
        10039,  # X-Backend-Server Header Information Leak
        10040,  # Secure Pages Include Mixed Content
        10041,  # HTTP to HTTPS Insecure Transition in Form Post
        10054,  # Cookie Without SameSite Attribute
        10055,  # CSP Scanner
        10063,  # Permissions Policy Header Not Set
        10098,  # Cross-Domain Misconfiguration
    ],
    "file_inclusion": [
        6,      # Path Traversal
        7,      # Remote File Inclusion
        40003,  # CRLF Injection
        40009,  # Server Side Include
        40032,  # .htaccess Information Leak
        40034,  # .env Information Leak
    ],
}


# =============================================================================
# CONFIGURACIÓN DE SPIDER
# =============================================================================

ZAP_SPIDER_CONFIG: Dict[str, any] = {
    "max_depth": 5,
    "max_children": 10,
    "thread_count": 5,
    "subtree_only": True,
    "parse_comments": True,
    "parse_robots_txt": True,
    "parse_sitemap_xml": True,
    "handle_odata_params": True,
}


# =============================================================================
# CONFIGURACIÓN DE AJAX SPIDER
# =============================================================================

ZAP_AJAX_SPIDER_CONFIG: Dict[str, any] = {
    "browser": "firefox-headless",
    "max_duration": 10,  # minutos
    "max_crawl_depth": 5,
    "number_of_browsers": 2,
    "random_inputs": True,
    "event_wait_time": 1000,  # ms
    "reload_wait_time": 1000,  # ms
}
