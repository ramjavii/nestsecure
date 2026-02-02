# =============================================================================
# NESTSECURE - DÍA 8-9: INTEGRACIÓN OPENVAS
# =============================================================================
# Fecha Planeada: 2026-02-04/05
# Duración Estimada: 2 días
# Dependencias: Día 7 completado, Docker funcionando
# =============================================================================

## 📋 RESUMEN EJECUTIVO

El Día 8-9 marca el inicio de la **Fase 2: Scanners**. Integraremos OpenVAS (GVM - Greenbone Vulnerability Management) como nuestro escáner de vulnerabilidades empresarial principal.

### 🎯 Objetivos Principales

1. **Configurar OpenVAS en Docker** - Container GVM funcionando
2. **Implementar GVM Client** - Comunicación con GVM via gvm-tools
3. **Worker OpenVAS para Celery** - Tareas asíncronas de escaneo
4. **API de Scans** - Endpoints para iniciar/monitorear escaneos
5. **Parser de Resultados** - Convertir reportes GVM a nuestro modelo

---

## 🏗️ ARQUITECTURA PROPUESTA

```
┌─────────────────────────────────────────────────────────────────────┐
│                           NESTSECURE                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend                                                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Dashboard → Scans → Results → Reports                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  Backend API                                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  /api/v1/scans     - CRUD de escaneos                         │  │
│  │  /api/v1/targets   - Gestión de targets GVM                   │  │
│  │  /api/v1/results   - Resultados de escaneos                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  Celery Workers                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  openvas_worker.py                                             │  │
│  │  ├── create_target()     - Crear target en GVM                │  │
│  │  ├── start_scan()        - Iniciar escaneo                    │  │
│  │  ├── check_scan_status() - Monitorear progreso                │  │
│  │  ├── get_scan_results()  - Obtener resultados                 │  │
│  │  └── parse_report()      - Parsear a nuestro modelo           │  │
│  └───────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  GVM Client                                                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  app/integrations/gvm/                                         │  │
│  │  ├── client.py       - GVM API client (gvm-tools)             │  │
│  │  ├── models.py       - Dataclasses GVM                        │  │
│  │  ├── parser.py       - Parse XML reports                      │  │
│  │  └── exceptions.py   - Excepciones específicas                │  │
│  └───────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  Docker                                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  greenbone/openvas-scanner (GVM 22.x)                        │    │
│  │  ├── ospd-openvas (Port 9390)                                │    │
│  │  ├── gvmd (Manager)                                          │    │
│  │  └── postgresql (internal)                                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 ENTREGABLES POR DÍA

### DÍA 8: Setup GVM + Client Básico

#### 8.1 Docker GVM Setup
- [ ] Agregar servicio GVM a docker-compose.dev.yml
- [ ] Configurar volúmenes para persistencia
- [ ] Script de inicialización (crear usuario admin)
- [ ] Health check para GVM
- [ ] Documentar tiempos de inicialización (~10-15 min primera vez)

#### 8.2 GVM Client
- [ ] `app/integrations/gvm/__init__.py`
- [ ] `app/integrations/gvm/client.py` - GVMClient class
- [ ] `app/integrations/gvm/models.py` - Dataclasses
- [ ] `app/integrations/gvm/exceptions.py` - Excepciones
- [ ] Tests unitarios del client (mocked)

#### 8.3 Modelos de Datos
- [ ] `app/models/scan.py` - Modelo Scan actualizado
- [ ] `app/models/scan_result.py` - Resultados individuales
- [ ] Migración Alembic
- [ ] Tests de modelos

### DÍA 9: Worker + API + Parser

#### 9.1 OpenVAS Worker
- [ ] `app/workers/openvas_worker.py` - Worker completo
- [ ] Tareas: create_target, start_scan, check_status, get_results
- [ ] Cola dedicada "openvas"
- [ ] Rate limiting y timeouts

#### 9.2 API Endpoints
- [ ] `app/api/v1/scans.py` - Endpoints de escaneo
- [ ] `app/schemas/scan.py` - Schemas actualizados
- [ ] Tests de API

#### 9.3 Parser de Resultados
- [ ] `app/integrations/gvm/parser.py` - Parser XML → Modelo
- [ ] Mapeo de severidades GVM → nuestras severidades
- [ ] Extracción de CVEs
- [ ] Tests del parser

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
backend/
├── app/
│   ├── integrations/
│   │   ├── __init__.py
│   │   └── gvm/
│   │       ├── __init__.py
│   │       ├── client.py           # GVMClient class
│   │       ├── models.py           # GVMTarget, GVMScan, GVMResult
│   │       ├── parser.py           # XMLParser → Models
│   │       └── exceptions.py       # GVMError, GVMConnectionError...
│   │
│   ├── models/
│   │   └── scan.py                 # Actualizar con campos GVM
│   │
│   ├── schemas/
│   │   └── scan.py                 # ScanCreate, ScanResponse...
│   │
│   ├── workers/
│   │   └── openvas_worker.py       # Reemplazar placeholder
│   │
│   ├── api/v1/
│   │   └── scans.py                # Nuevo archivo
│   │
│   └── tests/
│       ├── test_integrations/
│       │   └── test_gvm_client.py  # Tests del client
│       ├── test_workers/
│       │   └── test_openvas_worker.py # Tests del worker
│       └── test_api/
│           └── test_scans.py       # Tests de API
│
├── docker/
│   └── gvm/
│       ├── docker-compose.gvm.yml  # Compose específico GVM
│       └── init-gvm.sh             # Script inicialización
│
└── alembic/versions/
    └── xxx_add_scan_gvm_fields.py  # Nueva migración
```

---

## 🔧 IMPLEMENTACIÓN DETALLADA

### 1. Docker Compose - GVM Service

```yaml
# docker-compose.dev.yml - Agregar:
services:
  gvm:
    image: greenbone/openvas-scanner:stable
    container_name: nestsecure-gvm
    hostname: gvm
    ports:
      - "9390:9390"   # gvmd socket
      - "9392:9392"   # HTTPS API
    volumes:
      - gvm_data:/var/lib/gvm
      - gvm_certs:/var/lib/gvm/CA
      - openvas_plugins:/var/lib/openvas/plugins
    environment:
      - GVM_ADMIN_PASSWORD=${GVM_PASSWORD:-admin}
      - COMMUNITY_NVT_RSYNC_ENABLED=true
    healthcheck:
      test: ["CMD", "gvm-cli", "--gmp-username", "admin", "--gmp-password", "admin", "socket", "--socketpath", "/run/gvm/gvmd.sock", "--xml", "<get_version/>"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 300s  # GVM tarda en iniciar
    restart: unless-stopped
    networks:
      - nestsecure-network

volumes:
  gvm_data:
  gvm_certs:
  openvas_plugins:
```

### 2. GVM Client

```python
# app/integrations/gvm/client.py
"""
Cliente GVM (Greenbone Vulnerability Manager).

Wrapper sobre gvm-tools para comunicación con OpenVAS.
"""
from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID
import asyncio
from functools import lru_cache

from gvm.connections import UnixSocketConnection, TLSConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform

from app.config import get_settings
from app.utils.logger import get_logger
from .models import GVMTarget, GVMScan, GVMTask, GVMReport
from .exceptions import (
    GVMConnectionError,
    GVMAuthenticationError,
    GVMTimeoutError,
    GVMScanError
)

logger = get_logger(__name__)


class GVMClient:
    """
    Cliente para interactuar con GVM/OpenVAS.
    
    Soporta conexión via Unix Socket (local) o TLS (remoto).
    
    Usage:
        async with GVMClient() as client:
            targets = await client.get_targets()
            scan_id = await client.start_scan(target_id)
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        socket_path: Optional[str] = None,
        timeout: int = 300
    ):
        settings = get_settings()
        
        self.host = host or settings.GVM_HOST
        self.port = port or settings.GVM_PORT
        self.username = username or settings.GVM_USERNAME
        self.password = password or settings.GVM_PASSWORD
        self.socket_path = socket_path or "/run/gvm/gvmd.sock"
        self.timeout = timeout or settings.GVM_TIMEOUT
        
        self._connection = None
        self._gmp = None
        self._authenticated = False
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self) -> None:
        """Establecer conexión con GVM."""
        try:
            # Intentar Unix Socket primero (más rápido)
            if self._try_socket_connection():
                return
            
            # Fallback a TLS
            self._connection = TLSConnection(
                hostname=self.host,
                port=self.port,
                timeout=self.timeout
            )
            self._gmp = Gmp(connection=self._connection, transform=EtreeTransform())
            
            # Autenticar
            response = self._gmp.authenticate(self.username, self.password)
            if response.get("status") != "200":
                raise GVMAuthenticationError(f"Auth failed: {response}")
            
            self._authenticated = True
            logger.info(f"Connected to GVM at {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"GVM connection error: {e}")
            raise GVMConnectionError(f"Cannot connect to GVM: {e}")
    
    def _try_socket_connection(self) -> bool:
        """Intentar conexión via Unix Socket."""
        try:
            self._connection = UnixSocketConnection(path=self.socket_path)
            self._gmp = Gmp(connection=self._connection, transform=EtreeTransform())
            self._gmp.authenticate(self.username, self.password)
            self._authenticated = True
            logger.info(f"Connected to GVM via socket: {self.socket_path}")
            return True
        except Exception:
            return False
    
    async def disconnect(self) -> None:
        """Cerrar conexión con GVM."""
        if self._connection:
            self._connection.disconnect()
            self._authenticated = False
            logger.info("Disconnected from GVM")
    
    # =========================================================================
    # TARGETS
    # =========================================================================
    
    async def get_targets(self, filter_string: Optional[str] = None) -> List[GVMTarget]:
        """Obtener lista de targets configurados."""
        self._ensure_authenticated()
        
        response = self._gmp.get_targets(filter_string=filter_string)
        targets = []
        
        for target in response.findall('.//target'):
            targets.append(GVMTarget(
                id=target.get('id'),
                name=target.find('name').text,
                hosts=target.find('hosts').text,
                port_list_id=target.find('port_list').get('id') if target.find('port_list') is not None else None,
                comment=target.find('comment').text if target.find('comment') is not None else None
            ))
        
        return targets
    
    async def create_target(
        self,
        name: str,
        hosts: str,
        port_list_id: Optional[str] = None,
        comment: Optional[str] = None
    ) -> str:
        """
        Crear un target en GVM.
        
        Args:
            name: Nombre del target
            hosts: IPs o rangos (ej: "192.168.1.0/24" o "192.168.1.1,192.168.1.2")
            port_list_id: ID del port list a usar (default: All IANA)
            comment: Comentario opcional
        
        Returns:
            ID del target creado
        """
        self._ensure_authenticated()
        
        # Port list por defecto: All IANA assigned TCP
        if not port_list_id:
            port_list_id = "33d0cd82-57c6-11e1-8ed1-406186ea4fc5"
        
        response = self._gmp.create_target(
            name=name,
            hosts=[hosts],
            port_list_id=port_list_id,
            comment=comment or f"Created by NestSecure"
        )
        
        target_id = response.get('id')
        if not target_id:
            raise GVMScanError(f"Failed to create target: {response}")
        
        logger.info(f"Created GVM target: {target_id} for hosts: {hosts}")
        return target_id
    
    async def delete_target(self, target_id: str) -> bool:
        """Eliminar un target."""
        self._ensure_authenticated()
        response = self._gmp.delete_target(target_id=target_id)
        return response.get('status') == '200'
    
    # =========================================================================
    # SCANS / TASKS
    # =========================================================================
    
    async def get_scan_configs(self) -> List[dict]:
        """Obtener configuraciones de escaneo disponibles."""
        self._ensure_authenticated()
        
        response = self._gmp.get_scan_configs()
        configs = []
        
        for config in response.findall('.//config'):
            configs.append({
                'id': config.get('id'),
                'name': config.find('name').text,
                'type': config.find('type').text if config.find('type') is not None else 'unknown'
            })
        
        return configs
    
    async def create_task(
        self,
        name: str,
        target_id: str,
        config_id: Optional[str] = None,
        scanner_id: Optional[str] = None,
        comment: Optional[str] = None
    ) -> str:
        """
        Crear una tarea (task) de escaneo.
        
        Args:
            name: Nombre de la tarea
            target_id: ID del target a escanear
            config_id: ID de configuración (default: Full and fast)
            scanner_id: ID del scanner (default: OpenVAS Default)
            comment: Comentario opcional
        
        Returns:
            ID de la tarea creada
        """
        self._ensure_authenticated()
        
        # Scan config por defecto: Full and fast
        if not config_id:
            config_id = "daba56c8-73ec-11df-a475-002264764cea"
        
        # Scanner por defecto: OpenVAS Default
        if not scanner_id:
            scanner_id = "08b69003-5fc2-4037-a479-93b440211c73"
        
        response = self._gmp.create_task(
            name=name,
            config_id=config_id,
            target_id=target_id,
            scanner_id=scanner_id,
            comment=comment or f"NestSecure scan"
        )
        
        task_id = response.get('id')
        if not task_id:
            raise GVMScanError(f"Failed to create task: {response}")
        
        logger.info(f"Created GVM task: {task_id}")
        return task_id
    
    async def start_task(self, task_id: str) -> str:
        """
        Iniciar una tarea de escaneo.
        
        Returns:
            ID del reporte generado
        """
        self._ensure_authenticated()
        
        response = self._gmp.start_task(task_id=task_id)
        report_id = response.find('.//report_id')
        
        if report_id is None:
            raise GVMScanError(f"Failed to start task: {response}")
        
        report_id = report_id.text
        logger.info(f"Started task {task_id}, report: {report_id}")
        return report_id
    
    async def get_task_status(self, task_id: str) -> GVMTask:
        """Obtener estado de una tarea."""
        self._ensure_authenticated()
        
        response = self._gmp.get_task(task_id=task_id)
        task = response.find('.//task')
        
        if task is None:
            raise GVMScanError(f"Task not found: {task_id}")
        
        status = task.find('status').text if task.find('status') is not None else 'Unknown'
        progress = task.find('progress').text if task.find('progress') is not None else '0'
        
        return GVMTask(
            id=task.get('id'),
            name=task.find('name').text,
            status=status,
            progress=int(progress) if progress.isdigit() else 0,
            target_id=task.find('target').get('id') if task.find('target') is not None else None,
            last_report_id=task.find('.//last_report/report').get('id') if task.find('.//last_report/report') is not None else None
        )
    
    async def stop_task(self, task_id: str) -> bool:
        """Detener una tarea en ejecución."""
        self._ensure_authenticated()
        response = self._gmp.stop_task(task_id=task_id)
        return response.get('status') == '200'
    
    async def delete_task(self, task_id: str) -> bool:
        """Eliminar una tarea."""
        self._ensure_authenticated()
        response = self._gmp.delete_task(task_id=task_id)
        return response.get('status') == '200'
    
    # =========================================================================
    # REPORTS
    # =========================================================================
    
    async def get_report(
        self,
        report_id: str,
        report_format: str = "xml"
    ) -> GVMReport:
        """
        Obtener reporte de escaneo.
        
        Args:
            report_id: ID del reporte
            report_format: Formato (xml, pdf, html, csv)
        
        Returns:
            GVMReport con resultados parseados
        """
        self._ensure_authenticated()
        
        response = self._gmp.get_report(
            report_id=report_id,
            report_format_id=self._get_format_id(report_format),
            ignore_pagination=True,
            details=True
        )
        
        # Parsear el reporte
        from .parser import GVMParser
        parser = GVMParser()
        return parser.parse_report(response, report_id)
    
    def _get_format_id(self, format_name: str) -> str:
        """Obtener ID del formato de reporte."""
        formats = {
            "xml": "a994b278-1f62-11e1-96ac-406186ea4fc5",
            "pdf": "c402cc3e-b531-11e1-9163-406186ea4fc5",
            "html": "6c248850-1f62-11e1-b082-406186ea4fc5",
            "csv": "c1645568-627a-11e3-a660-406186ea4fc5"
        }
        return formats.get(format_name.lower(), formats["xml"])
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _ensure_authenticated(self) -> None:
        """Verificar que estamos autenticados."""
        if not self._authenticated:
            raise GVMConnectionError("Not authenticated. Call connect() first.")
    
    async def get_version(self) -> str:
        """Obtener versión de GVM."""
        self._ensure_authenticated()
        response = self._gmp.get_version()
        return response.find('.//version').text if response.find('.//version') is not None else "unknown"
    
    async def health_check(self) -> dict:
        """Verificar estado de GVM."""
        try:
            version = await self.get_version()
            return {
                "status": "healthy",
                "version": version,
                "connected": self._authenticated
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }


# Singleton para reutilizar conexión
@lru_cache()
def get_gvm_client() -> GVMClient:
    """Obtener instancia singleton del cliente GVM."""
    return GVMClient()
```

### 3. GVM Models

```python
# app/integrations/gvm/models.py
"""
Modelos de datos para GVM/OpenVAS.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class GVMSeverity(Enum):
    """Severidades de GVM mapeadas a CVSS."""
    LOG = "log"           # 0.0
    LOW = "low"           # 0.1 - 3.9
    MEDIUM = "medium"     # 4.0 - 6.9
    HIGH = "high"         # 7.0 - 8.9
    CRITICAL = "critical" # 9.0 - 10.0
    
    @classmethod
    def from_cvss(cls, cvss: float) -> "GVMSeverity":
        """Convertir CVSS score a severidad."""
        if cvss <= 0:
            return cls.LOG
        elif cvss < 4.0:
            return cls.LOW
        elif cvss < 7.0:
            return cls.MEDIUM
        elif cvss < 9.0:
            return cls.HIGH
        else:
            return cls.CRITICAL


class GVMTaskStatus(Enum):
    """Estados posibles de una tarea GVM."""
    NEW = "New"
    REQUESTED = "Requested"
    RUNNING = "Running"
    PAUSE_REQUESTED = "Pause Requested"
    PAUSED = "Paused"
    RESUME_REQUESTED = "Resume Requested"
    STOP_REQUESTED = "Stop Requested"
    STOPPED = "Stopped"
    DONE = "Done"
    DELETE_REQUESTED = "Delete Requested"
    ULTIMATE_DELETE_REQUESTED = "Ultimate Delete Requested"


@dataclass
class GVMTarget:
    """Target de escaneo en GVM."""
    id: str
    name: str
    hosts: str
    port_list_id: Optional[str] = None
    comment: Optional[str] = None
    creation_time: Optional[datetime] = None


@dataclass
class GVMTask:
    """Tarea de escaneo en GVM."""
    id: str
    name: str
    status: str
    progress: int = 0
    target_id: Optional[str] = None
    config_id: Optional[str] = None
    last_report_id: Optional[str] = None
    creation_time: Optional[datetime] = None
    
    @property
    def is_running(self) -> bool:
        return self.status in ["Running", "Requested"]
    
    @property
    def is_done(self) -> bool:
        return self.status == "Done"


@dataclass
class GVMVulnerability:
    """Vulnerabilidad individual encontrada."""
    id: str
    name: str
    host: str
    port: Optional[str] = None
    severity: float = 0.0
    severity_class: GVMSeverity = GVMSeverity.LOG
    cvss_base: Optional[float] = None
    description: Optional[str] = None
    solution: Optional[str] = None
    cve_ids: List[str] = field(default_factory=list)
    threat: Optional[str] = None
    family: Optional[str] = None
    qod: int = 0  # Quality of Detection
    refs: List[str] = field(default_factory=list)


@dataclass
class GVMHostResult:
    """Resultados para un host específico."""
    ip: str
    hostname: Optional[str] = None
    os: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    vulnerabilities: List[GVMVulnerability] = field(default_factory=list)
    
    @property
    def total_vulns(self) -> int:
        return len(self.vulnerabilities)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.severity_class == GVMSeverity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.severity_class == GVMSeverity.HIGH)


@dataclass
class GVMReport:
    """Reporte completo de escaneo GVM."""
    id: str
    task_id: str
    scan_start: Optional[datetime] = None
    scan_end: Optional[datetime] = None
    hosts: List[GVMHostResult] = field(default_factory=list)
    
    # Contadores
    host_count: int = 0
    vuln_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    log_count: int = 0
    
    def calculate_stats(self) -> None:
        """Calcular estadísticas del reporte."""
        self.host_count = len(self.hosts)
        self.vuln_count = sum(h.total_vulns for h in self.hosts)
        
        for host in self.hosts:
            for vuln in host.vulnerabilities:
                match vuln.severity_class:
                    case GVMSeverity.CRITICAL:
                        self.critical_count += 1
                    case GVMSeverity.HIGH:
                        self.high_count += 1
                    case GVMSeverity.MEDIUM:
                        self.medium_count += 1
                    case GVMSeverity.LOW:
                        self.low_count += 1
                    case GVMSeverity.LOG:
                        self.log_count += 1
```

### 4. OpenVAS Worker

```python
# app/workers/openvas_worker.py
"""
Celery Worker para OpenVAS/GVM.

Maneja tareas asíncronas de escaneo de vulnerabilidades.
"""
import asyncio
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from celery import current_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.db.session import async_session_maker
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.vulnerability import Vulnerability
from app.integrations.gvm.client import GVMClient
from app.integrations.gvm.models import GVMSeverity
from app.integrations.gvm.exceptions import GVMError
from app.utils.logger import get_logger
from app.core.metrics import (
    SCAN_DURATION_SECONDS,
    SCANS_IN_PROGRESS,
    VULNERABILITIES_FOUND_TOTAL
)

logger = get_logger(__name__)


# =============================================================================
# TAREAS PRINCIPALES
# =============================================================================

@celery_app.task(
    bind=True,
    name="openvas.full_scan",
    queue="openvas",
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=7200,  # 2 horas
    time_limit=7500
)
def openvas_full_scan(
    self,
    scan_id: str,
    targets: str,
    config_id: Optional[str] = None,
    organization_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ejecutar escaneo completo de OpenVAS.
    
    Este es el punto de entrada principal que orquesta:
    1. Crear target en GVM
    2. Crear y ejecutar tarea
    3. Monitorear progreso
    4. Obtener y parsear resultados
    5. Guardar en base de datos
    
    Args:
        scan_id: ID del scan en nuestra DB
        targets: IPs o rangos a escanear
        config_id: Config de GVM (default: Full and fast)
        organization_id: ID de la organización
    
    Returns:
        Resumen del escaneo
    """
    return asyncio.get_event_loop().run_until_complete(
        _async_full_scan(self, scan_id, targets, config_id, organization_id)
    )


async def _async_full_scan(
    task,
    scan_id: str,
    targets: str,
    config_id: Optional[str],
    organization_id: Optional[str]
) -> Dict[str, Any]:
    """Implementación async del full scan."""
    
    start_time = datetime.utcnow()
    SCANS_IN_PROGRESS.labels(scanner="openvas").inc()
    
    async with async_session_maker() as db:
        # Actualizar estado a RUNNING
        scan = await _update_scan_status(db, scan_id, ScanStatus.RUNNING)
        
        try:
            async with GVMClient() as gvm:
                # 1. Crear target
                logger.info(f"Creating GVM target for scan {scan_id}")
                target_id = await gvm.create_target(
                    name=f"NestSecure-{scan_id[:8]}",
                    hosts=targets,
                    comment=f"Scan ID: {scan_id}"
                )
                
                # 2. Crear y ejecutar task
                logger.info(f"Creating GVM task for target {target_id}")
                task_id = await gvm.create_task(
                    name=f"Scan-{scan_id[:8]}",
                    target_id=target_id,
                    config_id=config_id
                )
                
                report_id = await gvm.start_task(task_id)
                
                # Guardar IDs de GVM
                scan.external_id = task_id
                scan.metadata = {
                    "gvm_target_id": target_id,
                    "gvm_task_id": task_id,
                    "gvm_report_id": report_id
                }
                await db.commit()
                
                # 3. Monitorear progreso
                logger.info(f"Monitoring scan progress for task {task_id}")
                while True:
                    task_status = await gvm.get_task_status(task_id)
                    
                    # Actualizar progreso
                    scan.progress = task_status.progress
                    task.update_state(
                        state='PROGRESS',
                        meta={'progress': task_status.progress, 'status': task_status.status}
                    )
                    await db.commit()
                    
                    if task_status.is_done:
                        break
                    
                    if task_status.status in ["Stopped", "Stop Requested"]:
                        raise GVMError(f"Scan stopped: {task_status.status}")
                    
                    await asyncio.sleep(30)  # Poll cada 30 segundos
                
                # 4. Obtener y parsear resultados
                logger.info(f"Getting report {report_id}")
                report = await gvm.get_report(report_id)
                
                # 5. Guardar vulnerabilidades en DB
                vuln_count = await _save_vulnerabilities(
                    db, scan, report, organization_id
                )
                
                # 6. Marcar como completado
                scan.status = ScanStatus.COMPLETED
                scan.progress = 100
                scan.completed_at = datetime.utcnow()
                scan.results_count = vuln_count
                await db.commit()
                
                # 7. Cleanup en GVM (opcional)
                try:
                    await gvm.delete_task(task_id)
                    await gvm.delete_target(target_id)
                except Exception as e:
                    logger.warning(f"Cleanup failed: {e}")
                
                # Métricas
                duration = (datetime.utcnow() - start_time).total_seconds()
                SCAN_DURATION_SECONDS.labels(scanner="openvas", status="success").observe(duration)
                VULNERABILITIES_FOUND_TOTAL.labels(
                    scanner="openvas",
                    severity="total"
                ).inc(vuln_count)
                
                return {
                    "scan_id": scan_id,
                    "status": "completed",
                    "hosts_scanned": report.host_count,
                    "vulnerabilities_found": vuln_count,
                    "critical": report.critical_count,
                    "high": report.high_count,
                    "medium": report.medium_count,
                    "low": report.low_count,
                    "duration_seconds": duration
                }
                
        except GVMError as e:
            logger.error(f"GVM error in scan {scan_id}: {e}")
            await _update_scan_status(db, scan_id, ScanStatus.FAILED, str(e))
            SCAN_DURATION_SECONDS.labels(scanner="openvas", status="error").observe(
                (datetime.utcnow() - start_time).total_seconds()
            )
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in scan {scan_id}: {e}")
            await _update_scan_status(db, scan_id, ScanStatus.FAILED, str(e))
            raise
        
        finally:
            SCANS_IN_PROGRESS.labels(scanner="openvas").dec()


@celery_app.task(
    bind=True,
    name="openvas.check_status",
    queue="openvas"
)
def openvas_check_status(self, scan_id: str) -> Dict[str, Any]:
    """Verificar estado de un escaneo en curso."""
    return asyncio.get_event_loop().run_until_complete(
        _async_check_status(scan_id)
    )


async def _async_check_status(scan_id: str) -> Dict[str, Any]:
    """Implementación async de check_status."""
    async with async_session_maker() as db:
        scan = await db.get(Scan, UUID(scan_id))
        if not scan:
            return {"error": "Scan not found"}
        
        if not scan.external_id:
            return {
                "scan_id": scan_id,
                "status": scan.status.value,
                "progress": scan.progress
            }
        
        try:
            async with GVMClient() as gvm:
                task_status = await gvm.get_task_status(scan.external_id)
                
                return {
                    "scan_id": scan_id,
                    "status": scan.status.value,
                    "gvm_status": task_status.status,
                    "progress": task_status.progress,
                    "is_running": task_status.is_running,
                    "is_done": task_status.is_done
                }
        except GVMError as e:
            return {
                "scan_id": scan_id,
                "status": scan.status.value,
                "error": str(e)
            }


@celery_app.task(
    name="openvas.stop_scan",
    queue="openvas"
)
def openvas_stop_scan(scan_id: str) -> Dict[str, Any]:
    """Detener un escaneo en curso."""
    return asyncio.get_event_loop().run_until_complete(
        _async_stop_scan(scan_id)
    )


async def _async_stop_scan(scan_id: str) -> Dict[str, Any]:
    """Implementación async de stop_scan."""
    async with async_session_maker() as db:
        scan = await db.get(Scan, UUID(scan_id))
        if not scan or not scan.external_id:
            return {"error": "Scan not found or not started"}
        
        try:
            async with GVMClient() as gvm:
                await gvm.stop_task(scan.external_id)
                scan.status = ScanStatus.CANCELLED
                await db.commit()
                
                return {
                    "scan_id": scan_id,
                    "status": "cancelled"
                }
        except GVMError as e:
            return {"error": str(e)}


# =============================================================================
# HELPERS
# =============================================================================

async def _update_scan_status(
    db: AsyncSession,
    scan_id: str,
    status: ScanStatus,
    error_message: Optional[str] = None
) -> Scan:
    """Actualizar estado de un scan en la DB."""
    scan = await db.get(Scan, UUID(scan_id))
    if scan:
        scan.status = status
        if error_message:
            scan.error_message = error_message
        if status == ScanStatus.FAILED:
            scan.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(scan)
    return scan


async def _save_vulnerabilities(
    db: AsyncSession,
    scan: Scan,
    report,
    organization_id: Optional[str]
) -> int:
    """Guardar vulnerabilidades del reporte en la DB."""
    count = 0
    
    for host_result in report.hosts:
        # Buscar asset por IP
        asset = await _find_or_create_asset(db, host_result.ip, organization_id)
        
        for gvm_vuln in host_result.vulnerabilities:
            vuln = Vulnerability(
                organization_id=UUID(organization_id) if organization_id else scan.organization_id,
                asset_id=asset.id if asset else None,
                scan_id=scan.id,
                title=gvm_vuln.name,
                description=gvm_vuln.description,
                severity=_map_severity(gvm_vuln.severity_class),
                cvss_score=gvm_vuln.cvss_base,
                cve_ids=gvm_vuln.cve_ids,
                solution=gvm_vuln.solution,
                affected_host=host_result.ip,
                affected_port=gvm_vuln.port,
                scanner="openvas",
                raw_output={"gvm_id": gvm_vuln.id, "family": gvm_vuln.family}
            )
            db.add(vuln)
            count += 1
    
    await db.commit()
    logger.info(f"Saved {count} vulnerabilities for scan {scan.id}")
    return count


def _map_severity(gvm_severity: GVMSeverity) -> str:
    """Mapear severidad GVM a nuestro enum."""
    mapping = {
        GVMSeverity.CRITICAL: "critical",
        GVMSeverity.HIGH: "high",
        GVMSeverity.MEDIUM: "medium",
        GVMSeverity.LOW: "low",
        GVMSeverity.LOG: "info"
    }
    return mapping.get(gvm_severity, "info")


async def _find_or_create_asset(db: AsyncSession, ip: str, org_id: Optional[str]):
    """Buscar asset por IP o crear uno temporal."""
    from app.models.asset import Asset
    
    stmt = select(Asset).where(Asset.ip_address == ip)
    if org_id:
        stmt = stmt.where(Asset.organization_id == UUID(org_id))
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

---

## 🧪 TESTS ESTIMADOS

### Tests del GVM Client
- `test_gvm_connect_success` - Conexión exitosa
- `test_gvm_connect_failure` - Error de conexión
- `test_gvm_authenticate` - Autenticación
- `test_create_target` - Crear target
- `test_create_task` - Crear tarea
- `test_start_task` - Iniciar escaneo
- `test_get_task_status` - Obtener estado
- `test_get_report` - Obtener reporte
- `test_parse_report` - Parsear XML

**Total: ~15 tests**

### Tests del Worker
- `test_full_scan_success` - Escaneo completo
- `test_full_scan_gvm_error` - Error de GVM
- `test_check_status` - Verificar estado
- `test_stop_scan` - Detener escaneo
- `test_save_vulnerabilities` - Guardar resultados

**Total: ~10 tests**

### Tests de API
- `test_create_scan` - Crear escaneo
- `test_list_scans` - Listar escaneos
- `test_get_scan` - Obtener escaneo
- `test_get_scan_results` - Resultados
- `test_cancel_scan` - Cancelar
- `test_scan_permissions` - Permisos

**Total: ~15 tests**

### Tests del Parser
- `test_parse_vulnerabilities` - Parsear vulnerabilidades
- `test_severity_mapping` - Mapeo de severidades
- `test_cve_extraction` - Extraer CVEs

**Total: ~10 tests**

---

## 📊 MÉTRICAS DE ÉXITO

### Día 8
- [ ] GVM corriendo en Docker
- [ ] GVMClient conectando y autenticando
- [ ] Crear targets y tareas
- [ ] ~15 tests pasando

### Día 9
- [ ] Worker OpenVAS funcional
- [ ] API de scans implementada
- [ ] Parser de reportes funcionando
- [ ] Vulnerabilidades guardándose en DB
- [ ] ~50 tests totales nuevos
- [ ] Health check de GVM integrado

---

## ⚠️ NOTAS IMPORTANTES

### Tiempo de Inicialización de GVM
GVM tarda **10-20 minutos** en inicializar la primera vez mientras:
- Descarga NVTs (~70,000 plugins)
- Crea base de datos interna
- Genera certificados

### Recursos de Sistema
GVM es intensivo en recursos:
- **RAM:** Mínimo 4GB, recomendado 8GB
- **Disco:** ~10GB para NVTs y DB
- **CPU:** Escaneos son CPU-intensivos

### Configuraciones de Escaneo Recomendadas
| Config | Duración | Uso |
|--------|----------|-----|
| Discovery | 5-15 min | Descubrimiento rápido |
| Host Discovery | 5-10 min | Solo hosts vivos |
| Full and fast | 30-60 min | Balance velocidad/cobertura |
| Full and deep | 2-4 horas | Escaneo exhaustivo |

### Port Lists Predefinidas
| ID | Nombre | Puertos |
|----|--------|---------|
| 33d0cd82... | All IANA TCP | 1-65535 TCP |
| 730ef368... | All IANA TCP+UDP | TCP + UDP |
| 4a4717fe... | All TCP | Todos TCP |
| eca4f8ce... | Web | 80, 443, 8080... |

---

## 🔗 DEPENDENCIAS

### Python Packages
```txt
# requirements.txt - agregar:
gvm-tools>=24.1.0
python-gvm>=24.1.0
lxml>=5.0.0
```

### Docker
- greenbone/openvas-scanner:stable (GVM 22.x)
- Aproximadamente 2GB de imagen

---

## 📝 CHECKLIST FINAL

### Pre-Implementación
- [ ] Verificar RAM disponible (mínimo 8GB total)
- [ ] Verificar espacio en disco (10GB+ libre)
- [ ] Docker funcionando correctamente
- [ ] Tests del Día 7 pasando

### Día 8
- [ ] docker-compose.dev.yml actualizado con GVM
- [ ] GVM inicializado y saludable
- [ ] app/integrations/gvm/client.py implementado
- [ ] app/integrations/gvm/models.py implementado
- [ ] Tests básicos del client pasando

### Día 9
- [ ] Worker openvas_worker.py implementado
- [ ] API scans.py implementada
- [ ] Parser de reportes funcional
- [ ] Integración con métricas Prometheus
- [ ] Todos los tests pasando
- [ ] Documentación actualizada

---

**Siguiente paso:** Día 10-11 - Nuclei Integration
