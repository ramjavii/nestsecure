# =============================================================================
# NESTSECURE - Constantes del Sistema
# =============================================================================
"""
Constantes globales utilizadas en toda la aplicación.

Incluye:
- Códigos de error
- Límites de paginación
- Timeouts
- Regex patterns
- Configuraciones por defecto
"""

from enum import Enum, IntEnum
from typing import Final
import re


# =============================================================================
# Códigos de Error
# =============================================================================
class ErrorCode(str, Enum):
    """Códigos de error estandarizados para la API."""
    
    # Errores de autenticación (1xxx)
    AUTH_INVALID_CREDENTIALS = "AUTH_1001"
    AUTH_TOKEN_EXPIRED = "AUTH_1002"
    AUTH_TOKEN_INVALID = "AUTH_1003"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_1004"
    AUTH_ACCOUNT_DISABLED = "AUTH_1005"
    AUTH_ACCOUNT_LOCKED = "AUTH_1006"
    
    # Errores de validación (2xxx)
    VALIDATION_REQUIRED_FIELD = "VAL_2001"
    VALIDATION_INVALID_FORMAT = "VAL_2002"
    VALIDATION_OUT_OF_RANGE = "VAL_2003"
    VALIDATION_DUPLICATE = "VAL_2004"
    VALIDATION_INVALID_TYPE = "VAL_2005"
    
    # Errores de recursos (3xxx)
    RESOURCE_NOT_FOUND = "RES_3001"
    RESOURCE_ALREADY_EXISTS = "RES_3002"
    RESOURCE_DELETED = "RES_3003"
    RESOURCE_LOCKED = "RES_3004"
    
    # Errores de escaneo (4xxx)
    SCAN_FAILED = "SCAN_4001"
    SCAN_TIMEOUT = "SCAN_4002"
    SCAN_TARGET_UNREACHABLE = "SCAN_4003"
    SCAN_INVALID_TARGET = "SCAN_4004"
    SCAN_QUOTA_EXCEEDED = "SCAN_4005"
    
    # Errores de base de datos (5xxx)
    DB_CONNECTION_FAILED = "DB_5001"
    DB_QUERY_FAILED = "DB_5002"
    DB_TRANSACTION_FAILED = "DB_5003"
    DB_INTEGRITY_ERROR = "DB_5004"
    
    # Errores de servicios externos (6xxx)
    EXTERNAL_SERVICE_UNAVAILABLE = "EXT_6001"
    EXTERNAL_SERVICE_TIMEOUT = "EXT_6002"
    EXTERNAL_SERVICE_ERROR = "EXT_6003"
    
    # Errores internos (9xxx)
    INTERNAL_ERROR = "INT_9001"
    CONFIGURATION_ERROR = "INT_9002"
    NOT_IMPLEMENTED = "INT_9003"


# =============================================================================
# Límites de Paginación
# =============================================================================
class PaginationLimits:
    """Límites para paginación de resultados."""
    
    DEFAULT_PAGE: Final[int] = 1
    DEFAULT_PAGE_SIZE: Final[int] = 20
    MIN_PAGE_SIZE: Final[int] = 1
    MAX_PAGE_SIZE: Final[int] = 100
    
    # Límites específicos por recurso
    MAX_ASSETS_PER_PAGE: Final[int] = 100
    MAX_VULNERABILITIES_PER_PAGE: Final[int] = 200
    MAX_SCANS_PER_PAGE: Final[int] = 50
    MAX_USERS_PER_PAGE: Final[int] = 50


# =============================================================================
# Timeouts (en segundos)
# =============================================================================
class Timeouts:
    """Timeouts para diferentes operaciones."""
    
    # HTTP/API
    DEFAULT_REQUEST_TIMEOUT: Final[int] = 30
    FILE_UPLOAD_TIMEOUT: Final[int] = 120
    
    # Base de datos
    DB_QUERY_TIMEOUT: Final[int] = 30
    DB_CONNECTION_TIMEOUT: Final[int] = 10
    
    # Escaneo
    SCAN_NMAP_DEFAULT: Final[int] = 600  # 10 minutos
    SCAN_NMAP_QUICK: Final[int] = 120    # 2 minutos
    SCAN_NMAP_FULL: Final[int] = 3600    # 1 hora
    SCAN_OPENVAS: Final[int] = 7200      # 2 horas
    SCAN_NUCLEI: Final[int] = 1800       # 30 minutos
    SCAN_ZAP: Final[int] = 3600          # 1 hora
    
    # Celery tasks
    TASK_DEFAULT_TIMEOUT: Final[int] = 3600
    TASK_SOFT_TIMEOUT: Final[int] = 3300
    
    # Cache
    CACHE_SHORT: Final[int] = 60         # 1 minuto
    CACHE_MEDIUM: Final[int] = 300       # 5 minutos
    CACHE_LONG: Final[int] = 3600        # 1 hora
    CACHE_DAY: Final[int] = 86400        # 24 horas
    
    # JWT
    ACCESS_TOKEN_EXPIRE: Final[int] = 1800      # 30 minutos
    REFRESH_TOKEN_EXPIRE: Final[int] = 604800   # 7 días


# =============================================================================
# Rate Limits
# =============================================================================
class RateLimits:
    """Límites de rate limiting."""
    
    # Requests por minuto
    DEFAULT_RPM: Final[int] = 60
    AUTH_RPM: Final[int] = 10        # Login attempts
    SCAN_RPM: Final[int] = 5         # Scan requests
    API_RPM: Final[int] = 100        # General API
    
    # Requests por hora
    SCAN_RPH: Final[int] = 30        # Scans por hora
    REPORT_RPH: Final[int] = 20      # Reports por hora


# =============================================================================
# Severidades de Vulnerabilidad
# =============================================================================
class VulnerabilitySeverity(str, Enum):
    """Niveles de severidad de vulnerabilidades."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    
    @property
    def score_range(self) -> tuple[float, float]:
        """Rango de CVSS para esta severidad."""
        ranges = {
            "critical": (9.0, 10.0),
            "high": (7.0, 8.9),
            "medium": (4.0, 6.9),
            "low": (0.1, 3.9),
            "info": (0.0, 0.0),
        }
        return ranges[self.value]


# =============================================================================
# Estados de Escaneo
# =============================================================================
class ScanStatus(str, Enum):
    """Estados posibles de un escaneo."""
    
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


# =============================================================================
# Tipos de Escaneo
# =============================================================================
class ScanType(str, Enum):
    """Tipos de escaneo disponibles."""
    
    QUICK = "quick"           # Escaneo rápido (top ports)
    STANDARD = "standard"     # Escaneo estándar
    FULL = "full"             # Escaneo completo
    VULNERABILITY = "vuln"    # Solo vulnerabilidades
    DISCOVERY = "discovery"   # Descubrimiento de hosts
    CUSTOM = "custom"         # Configuración personalizada


# =============================================================================
# Tipos de Asset
# =============================================================================
class AssetType(str, Enum):
    """Tipos de activos."""
    
    SERVER = "server"
    WORKSTATION = "workstation"
    NETWORK_DEVICE = "network_device"
    IOT_DEVICE = "iot_device"
    CONTAINER = "container"
    CLOUD_INSTANCE = "cloud_instance"
    VIRTUAL_MACHINE = "virtual_machine"
    DATABASE = "database"
    WEB_APPLICATION = "web_application"
    API_ENDPOINT = "api_endpoint"
    OTHER = "other"


# =============================================================================
# Criticidad de Asset
# =============================================================================
class AssetCriticality(str, Enum):
    """Niveles de criticidad de activos."""
    
    CRITICAL = "critical"     # Sistemas core del negocio
    HIGH = "high"             # Sistemas importantes
    MEDIUM = "medium"         # Sistemas de soporte
    LOW = "low"               # Sistemas no críticos


# =============================================================================
# Roles de Usuario
# =============================================================================
class UserRole(str, Enum):
    """Roles de usuario en el sistema."""
    
    ADMIN = "admin"           # Administrador total
    OPERATOR = "operator"     # Operador de escaneos
    ANALYST = "analyst"       # Analista de seguridad
    VIEWER = "viewer"         # Solo lectura


# Jerarquía de roles (mayor número = más permisos)
ROLE_HIERARCHY: Final[dict[str, int]] = {
    UserRole.VIEWER.value: 1,
    UserRole.ANALYST.value: 2,
    UserRole.OPERATOR.value: 3,
    UserRole.ADMIN.value: 4,
}


# =============================================================================
# Regex Patterns
# =============================================================================
class Patterns:
    """Patrones regex para validación."""
    
    # Redes
    IPV4: Final[re.Pattern] = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    
    IPV6: Final[re.Pattern] = re.compile(
        r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|"
        r"^::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|"
        r"^(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}$"
    )
    
    CIDR_V4: Final[re.Pattern] = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(?:[0-9]|[1-2][0-9]|3[0-2])$"
    )
    
    MAC_ADDRESS: Final[re.Pattern] = re.compile(
        r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
    )
    
    PORT: Final[re.Pattern] = re.compile(
        r"^([1-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$"
    )
    
    PORT_RANGE: Final[re.Pattern] = re.compile(
        r"^(\d{1,5})(-(\d{1,5}))?$"
    )
    
    # Identificadores
    HOSTNAME: Final[re.Pattern] = re.compile(
        r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
    )
    
    FQDN: Final[re.Pattern] = re.compile(
        r"^(?=.{1,253}$)(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)*(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
    )
    
    CVE_ID: Final[re.Pattern] = re.compile(
        r"^CVE-\d{4}-\d{4,}$"
    )
    
    CPE: Final[re.Pattern] = re.compile(
        r"^cpe:2\.3:[aho\*\-](?::[^:]+){10}$"
    )
    
    # Slug/Identificadores
    SLUG: Final[re.Pattern] = re.compile(
        r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    
    UUID: Final[re.Pattern] = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE
    )


# =============================================================================
# Puertos Comunes
# =============================================================================
class CommonPorts:
    """Puertos comunes para escaneos."""
    
    # Top 20 puertos TCP
    TOP_20: Final[list[int]] = [
        21, 22, 23, 25, 53, 80, 110, 111, 135, 139,
        143, 443, 445, 993, 995, 1723, 3306, 3389, 5900, 8080
    ]
    
    # Top 100 puertos TCP
    TOP_100: Final[list[int]] = [
        7, 9, 13, 21, 22, 23, 25, 26, 37, 53, 79, 80, 81, 88, 106, 110, 111,
        113, 119, 135, 139, 143, 144, 179, 199, 389, 427, 443, 444, 445, 465,
        513, 514, 515, 543, 544, 548, 554, 587, 631, 646, 873, 990, 993, 995,
        1025, 1026, 1027, 1028, 1029, 1110, 1433, 1720, 1723, 1755, 1900, 2000,
        2001, 2049, 2121, 2717, 3000, 3128, 3306, 3389, 3986, 4899, 5000, 5009,
        5051, 5060, 5101, 5190, 5357, 5432, 5631, 5666, 5800, 5900, 6000, 6001,
        6646, 7070, 8000, 8008, 8009, 8080, 8081, 8443, 8888, 9100, 9999, 10000,
        32768, 49152, 49153, 49154, 49155, 49156, 49157
    ]
    
    # Puertos de servicios web
    WEB: Final[list[int]] = [80, 443, 8000, 8080, 8443, 8888, 3000, 5000]
    
    # Puertos de bases de datos
    DATABASE: Final[list[int]] = [1433, 1521, 3306, 5432, 6379, 27017, 9200]
    
    # Puertos de acceso remoto
    REMOTE_ACCESS: Final[list[int]] = [22, 23, 3389, 5900, 5901]


# =============================================================================
# HTTP Status Messages
# =============================================================================
HTTP_STATUS_MESSAGES: Final[dict[int, str]] = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


# =============================================================================
# Exportar todas las constantes
# =============================================================================
__all__ = [
    "ErrorCode",
    "PaginationLimits",
    "Timeouts",
    "RateLimits",
    "VulnerabilitySeverity",
    "ScanStatus",
    "ScanType",
    "AssetType",
    "AssetCriticality",
    "UserRole",
    "ROLE_HIERARCHY",
    "Patterns",
    "CommonPorts",
    "HTTP_STATUS_MESSAGES",
]
