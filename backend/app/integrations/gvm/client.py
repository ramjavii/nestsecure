# =============================================================================
# NESTSECURE - GVM Client
# =============================================================================
"""
Cliente GVM (Greenbone Vulnerability Manager).

Proporciona una interfaz de alto nivel para comunicación con OpenVAS/GVM.

Este cliente puede operar de dos formas:
1. **Modo Real**: Conecta con un servidor GVM real via socket/TLS
2. **Modo Mock**: Para testing y desarrollo sin GVM

Usage:
    # Modo real (producción)
    async with GVMClient() as client:
        targets = await client.get_targets()
        task_id = await client.create_task(name="Scan", target_id=target_id)
        await client.start_task(task_id)
    
    # Modo mock (testing)
    client = GVMClient(mock_mode=True)
    await client.connect()
"""

import asyncio
from datetime import datetime
from functools import lru_cache
from typing import Optional, List, Dict, Any
from xml.etree import ElementTree as ET

from app.config import get_settings
from app.utils.logger import get_logger

from .models import (
    GVMTarget,
    GVMTask,
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
)

logger = get_logger(__name__)


class GVMClient:
    """
    Cliente para interactuar con GVM/OpenVAS.
    
    Soporta:
    - Conexión via Unix Socket (local) o TLS (remoto)
    - Gestión de targets y tasks
    - Ejecución y monitoreo de escaneos
    - Obtención y parseo de reportes
    
    Attributes:
        host: Host del servidor GVM
        port: Puerto del servidor GVM  
        username: Usuario de autenticación
        password: Contraseña de autenticación
        timeout: Timeout para operaciones (segundos)
        mock_mode: Si True, opera sin conexión real
    """
    
    # Configuraciones predefinidas de GVM
    SCAN_CONFIG_DISCOVERY = "8715c877-47a0-438d-98a3-27c7a6ab2196"
    SCAN_CONFIG_HOST_DISCOVERY = "2d3f051c-55ba-11e3-bf43-406186ea4fc5"
    SCAN_CONFIG_FULL_AND_FAST = "daba56c8-73ec-11df-a475-002264764cea"
    SCAN_CONFIG_FULL_AND_DEEP = "708f25c4-7489-11df-8094-002264764cea"
    
    # Port lists predefinidas
    PORT_LIST_ALL_IANA_TCP = "33d0cd82-57c6-11e1-8ed1-406186ea4fc5"
    PORT_LIST_ALL_TCP_NMAP_1000 = "96a3c78c-2a97-11e5-9d86-406186ea4fc5"
    
    # Scanner por defecto
    SCANNER_OPENVAS_DEFAULT = "08b69003-5fc2-4037-a479-93b440211c73"
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        socket_path: Optional[str] = None,
        timeout: Optional[int] = None,
        mock_mode: bool = False,
    ):
        """
        Inicializar cliente GVM.
        
        Args:
            host: Host del servidor GVM (default: de config)
            port: Puerto del servidor (default: 9390)
            username: Usuario GVM (default: de config)
            password: Contraseña GVM (default: de config)
            socket_path: Path al Unix socket (alternativa a host/port)
            timeout: Timeout en segundos (default: 300)
            mock_mode: Si True, no conecta realmente (para testing)
        """
        settings = get_settings()
        
        self.host = host or settings.GVM_HOST
        self.port = port or settings.GVM_PORT
        self.username = username or settings.GVM_USERNAME
        self.password = password or settings.GVM_PASSWORD
        self.socket_path = socket_path or "/run/gvmd/gvmd.sock"
        self.timeout = timeout or settings.GVM_TIMEOUT
        self.mock_mode = mock_mode
        
        self._connection = None
        self._gmp = None
        self._authenticated = False
        self._parser = GVMParser()
        self._version: Optional[str] = None
    
    # =========================================================================
    # CONTEXT MANAGER
    # =========================================================================
    
    async def __aenter__(self) -> "GVMClient":
        """Entrar al context manager."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Salir del context manager."""
        await self.disconnect()
    
    # =========================================================================
    # CONEXIÓN
    # =========================================================================
    
    async def connect(self) -> None:
        """
        Establecer conexión con GVM.
        
        Intenta primero Unix Socket, luego TLS.
        
        Raises:
            GVMConnectionError: Si no puede conectar
            GVMAuthenticationError: Si falla autenticación
        """
        if self.mock_mode:
            self._authenticated = True
            self._version = "22.4.0 (mock)"
            logger.info("GVM client in mock mode")
            return
        
        try:
            # Importar gvm-tools (puede no estar disponible)
            try:
                from gvm.connections import UnixSocketConnection, TLSConnection
                from gvm.protocols.gmp import Gmp
                from gvm.transforms import EtreeTransform
            except ImportError:
                logger.warning("gvm-tools not installed, using mock mode")
                self.mock_mode = True
                self._authenticated = True
                self._version = "mock (gvm-tools not installed)"
                return
            
            # Intentar Unix Socket primero (más rápido si es local)
            socket_connected = await self._try_socket_connection(
                UnixSocketConnection, Gmp, EtreeTransform
            )
            
            if not socket_connected:
                # Intentar TLS
                await self._try_tls_connection(
                    TLSConnection, Gmp, EtreeTransform
                )
            
            logger.info(
                f"Connected to GVM v{self._version}",
                extra={"host": self.host, "authenticated": self._authenticated}
            )
            
        except GVMConnectionError:
            raise
        except GVMAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"GVM connection error: {e}")
            raise GVMConnectionError(
                f"Cannot connect to GVM: {e}",
                host=self.host,
                port=self.port,
            )
    
    async def _try_socket_connection(
        self, UnixSocketConnection, Gmp, EtreeTransform
    ) -> bool:
        """Intentar conexión via Unix Socket."""
        try:
            self._connection = UnixSocketConnection(path=self.socket_path)
            self._gmp = Gmp(connection=self._connection, transform=EtreeTransform())
            
            # Autenticar
            response = self._gmp.authenticate(self.username, self.password)
            if self._check_response(response):
                self._authenticated = True
                self._version = self._get_version_sync()
                logger.info(f"Connected to GVM via socket: {self.socket_path}")
                return True
            
        except Exception as e:
            logger.debug(f"Socket connection failed: {e}")
            self._connection = None
            self._gmp = None
        
        return False
    
    async def _try_tls_connection(
        self, TLSConnection, Gmp, EtreeTransform
    ) -> None:
        """Intentar conexión via TLS."""
        try:
            self._connection = TLSConnection(
                hostname=self.host,
                port=self.port,
                timeout=self.timeout,
            )
            self._gmp = Gmp(connection=self._connection, transform=EtreeTransform())
            
            # Autenticar
            response = self._gmp.authenticate(self.username, self.password)
            if not self._check_response(response):
                raise GVMAuthenticationError(
                    "Authentication failed",
                    username=self.username,
                )
            
            self._authenticated = True
            self._version = self._get_version_sync()
            logger.info(f"Connected to GVM via TLS: {self.host}:{self.port}")
            
        except GVMAuthenticationError:
            raise
        except Exception as e:
            raise GVMConnectionError(
                f"TLS connection failed: {e}",
                host=self.host,
                port=self.port,
            )
    
    async def disconnect(self) -> None:
        """Cerrar conexión con GVM."""
        if self._connection and not self.mock_mode:
            try:
                self._connection.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")
        
        self._connection = None
        self._gmp = None
        self._authenticated = False
        logger.info("Disconnected from GVM")
    
    def _ensure_connected(self) -> None:
        """Verificar que estamos conectados."""
        if not self._authenticated:
            raise GVMConnectionError("Not connected. Call connect() first.")
    
    def _check_response(self, response: ET.Element) -> bool:
        """Verificar que una respuesta es exitosa."""
        status = response.get("status", "")
        return status.startswith("2")  # 200, 201, etc.
    
    def _get_version_sync(self) -> str:
        """Obtener versión de GVM (síncrono)."""
        if self.mock_mode:
            return "22.4.0 (mock)"
        
        try:
            response = self._gmp.get_version()
            version = response.find(".//version")
            return version.text if version is not None else "unknown"
        except Exception:
            return "unknown"
    
    # =========================================================================
    # TARGETS
    # =========================================================================
    
    async def get_targets(
        self,
        filter_string: Optional[str] = None
    ) -> List[GVMTarget]:
        """
        Obtener lista de targets configurados.
        
        Args:
            filter_string: Filtro GMP (ej: "name~test")
        
        Returns:
            Lista de GVMTarget
        """
        self._ensure_connected()
        
        if self.mock_mode:
            return []
        
        response = self._gmp.get_targets(filter_string=filter_string)
        return self._parser.parse_targets(response)
    
    async def get_target(self, target_id: str) -> GVMTarget:
        """
        Obtener un target específico.
        
        Args:
            target_id: ID del target
        
        Returns:
            GVMTarget
        
        Raises:
            GVMNotFoundError: Si el target no existe
        """
        self._ensure_connected()
        
        if self.mock_mode:
            raise GVMNotFoundError(
                f"Target not found: {target_id}",
                resource_type="target",
                resource_id=target_id,
            )
        
        response = self._gmp.get_target(target_id=target_id)
        targets = self._parser.parse_targets(response)
        
        if not targets:
            raise GVMNotFoundError(
                f"Target not found: {target_id}",
                resource_type="target",
                resource_id=target_id,
            )
        
        return targets[0]
    
    async def create_target(
        self,
        name: str,
        hosts: str,
        port_list_id: Optional[str] = None,
        comment: Optional[str] = None,
        exclude_hosts: Optional[str] = None,
    ) -> str:
        """
        Crear un target en GVM.
        
        Args:
            name: Nombre del target
            hosts: IPs o rangos (ej: "192.168.1.0/24" o "192.168.1.1,192.168.1.2")
            port_list_id: ID del port list (default: All IANA TCP)
            comment: Comentario opcional
            exclude_hosts: Hosts a excluir del escaneo
        
        Returns:
            ID del target creado
        
        Raises:
            GVMScanError: Si falla la creación
        """
        self._ensure_connected()
        
        if self.mock_mode:
            import uuid
            return str(uuid.uuid4())
        
        # Port list por defecto
        if not port_list_id:
            port_list_id = self.PORT_LIST_ALL_IANA_TCP
        
        try:
            response = self._gmp.create_target(
                name=name,
                hosts=[hosts],
                port_list_id=port_list_id,
                comment=comment or f"Created by NestSecure at {datetime.utcnow().isoformat()}",
                exclude_hosts=[exclude_hosts] if exclude_hosts else None,
            )
            
            target_id = response.get("id")
            if not target_id:
                status_text = response.get("status_text", "Unknown error")
                raise GVMScanError(f"Failed to create target: {status_text}")
            
            logger.info(f"Created GVM target: {target_id}", extra={"hosts": hosts})
            return target_id
            
        except GVMScanError:
            raise
        except Exception as e:
            raise GVMScanError(f"Failed to create target: {e}")
    
    async def delete_target(self, target_id: str, ultimate: bool = False) -> bool:
        """
        Eliminar un target.
        
        Args:
            target_id: ID del target
            ultimate: Si True, elimina permanentemente
        
        Returns:
            True si se eliminó correctamente
        """
        self._ensure_connected()
        
        if self.mock_mode:
            return True
        
        try:
            response = self._gmp.delete_target(target_id=target_id, ultimate=ultimate)
            return self._check_response(response)
        except Exception as e:
            logger.warning(f"Failed to delete target {target_id}: {e}")
            return False
    
    # =========================================================================
    # TASKS
    # =========================================================================
    
    async def get_tasks(
        self,
        filter_string: Optional[str] = None
    ) -> List[GVMTask]:
        """
        Obtener lista de tasks.
        
        Args:
            filter_string: Filtro GMP
        
        Returns:
            Lista de GVMTask
        """
        self._ensure_connected()
        
        if self.mock_mode:
            return []
        
        response = self._gmp.get_tasks(filter_string=filter_string)
        return self._parser.parse_tasks(response)
    
    async def get_task(self, task_id: str) -> GVMTask:
        """
        Obtener una task específica.
        
        Args:
            task_id: ID de la task
        
        Returns:
            GVMTask
        
        Raises:
            GVMNotFoundError: Si la task no existe
        """
        self._ensure_connected()
        
        if self.mock_mode:
            raise GVMNotFoundError(
                f"Task not found: {task_id}",
                resource_type="task",
                resource_id=task_id,
            )
        
        response = self._gmp.get_task(task_id=task_id)
        return self._parser.parse_task(response)
    
    async def create_task(
        self,
        name: str,
        target_id: str,
        config_id: Optional[str] = None,
        scanner_id: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        """
        Crear una tarea de escaneo.
        
        Args:
            name: Nombre de la tarea
            target_id: ID del target a escanear
            config_id: ID de configuración (default: Full and fast)
            scanner_id: ID del scanner (default: OpenVAS Default)
            comment: Comentario opcional
        
        Returns:
            ID de la tarea creada
        
        Raises:
            GVMScanError: Si falla la creación
        """
        self._ensure_connected()
        
        if self.mock_mode:
            import uuid
            return str(uuid.uuid4())
        
        # Valores por defecto
        if not config_id:
            config_id = self.SCAN_CONFIG_FULL_AND_FAST
        if not scanner_id:
            scanner_id = self.SCANNER_OPENVAS_DEFAULT
        
        try:
            response = self._gmp.create_task(
                name=name,
                config_id=config_id,
                target_id=target_id,
                scanner_id=scanner_id,
                comment=comment or f"NestSecure scan at {datetime.utcnow().isoformat()}",
            )
            
            task_id = response.get("id")
            if not task_id:
                status_text = response.get("status_text", "Unknown error")
                raise GVMScanError(f"Failed to create task: {status_text}")
            
            logger.info(f"Created GVM task: {task_id}", extra={"target_id": target_id})
            return task_id
            
        except GVMScanError:
            raise
        except Exception as e:
            raise GVMScanError(f"Failed to create task: {e}")
    
    async def start_task(self, task_id: str) -> str:
        """
        Iniciar una tarea de escaneo.
        
        Args:
            task_id: ID de la tarea
        
        Returns:
            ID del reporte generado
        
        Raises:
            GVMScanError: Si falla el inicio
        """
        self._ensure_connected()
        
        if self.mock_mode:
            import uuid
            return str(uuid.uuid4())
        
        try:
            response = self._gmp.start_task(task_id=task_id)
            
            report_id_elem = response.find(".//report_id")
            if report_id_elem is None or not report_id_elem.text:
                status_text = response.get("status_text", "Unknown error")
                raise GVMScanError(f"Failed to start task: {status_text}")
            
            report_id = report_id_elem.text
            logger.info(f"Started task {task_id}, report: {report_id}")
            return report_id
            
        except GVMScanError:
            raise
        except Exception as e:
            raise GVMScanError(f"Failed to start task: {e}", task_id=task_id)
    
    async def stop_task(self, task_id: str) -> bool:
        """
        Detener una tarea en ejecución.
        
        Args:
            task_id: ID de la tarea
        
        Returns:
            True si se detuvo correctamente
        """
        self._ensure_connected()
        
        if self.mock_mode:
            return True
        
        try:
            response = self._gmp.stop_task(task_id=task_id)
            success = self._check_response(response)
            
            if success:
                logger.info(f"Stopped task: {task_id}")
            
            return success
        except Exception as e:
            logger.warning(f"Failed to stop task {task_id}: {e}")
            return False
    
    async def delete_task(self, task_id: str, ultimate: bool = False) -> bool:
        """
        Eliminar una tarea.
        
        Args:
            task_id: ID de la tarea
            ultimate: Si True, elimina permanentemente
        
        Returns:
            True si se eliminó correctamente
        """
        self._ensure_connected()
        
        if self.mock_mode:
            return True
        
        try:
            response = self._gmp.delete_task(task_id=task_id, ultimate=ultimate)
            return self._check_response(response)
        except Exception as e:
            logger.warning(f"Failed to delete task {task_id}: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> GVMTask:
        """
        Obtener estado actual de una tarea.
        
        Alias de get_task() para claridad semántica.
        
        Args:
            task_id: ID de la tarea
        
        Returns:
            GVMTask con estado actual
        """
        return await self.get_task(task_id)
    
    # =========================================================================
    # REPORTS
    # =========================================================================
    
    async def get_report(
        self,
        report_id: str,
        include_log_level: bool = False,
    ) -> GVMReport:
        """
        Obtener reporte de escaneo.
        
        Args:
            report_id: ID del reporte
            include_log_level: Si True, incluye resultados de nivel "Log"
        
        Returns:
            GVMReport con resultados parseados
        
        Raises:
            GVMNotFoundError: Si el reporte no existe
        """
        self._ensure_connected()
        
        if self.mock_mode:
            # Retornar reporte vacío en mock mode
            return GVMReport(
                id=report_id,
                task_id="mock-task",
                task_name="Mock Scan",
                scan_start=datetime.utcnow(),
                scan_end=datetime.utcnow(),
                hosts=[],
            )
        
        try:
            # Obtener reporte con detalles
            response = self._gmp.get_report(
                report_id=report_id,
                ignore_pagination=True,
                details=True,
            )
            
            # Configurar parser
            self._parser.include_log_level = include_log_level
            
            # Parsear
            report = self._parser.parse_report(response, report_id)
            
            logger.info(
                f"Retrieved report {report_id}",
                extra={
                    "hosts": report.host_count,
                    "vulns": report.vuln_count,
                }
            )
            
            return report
            
        except GVMError:
            raise
        except Exception as e:
            raise GVMError(f"Failed to get report: {e}")
    
    # =========================================================================
    # SCAN CONFIGS Y PORT LISTS
    # =========================================================================
    
    async def get_scan_configs(self) -> List[GVMScanConfig]:
        """
        Obtener configuraciones de escaneo disponibles.
        
        Returns:
            Lista de GVMScanConfig
        """
        self._ensure_connected()
        
        if self.mock_mode:
            return [
                GVMScanConfig(
                    id=self.SCAN_CONFIG_FULL_AND_FAST,
                    name="Full and fast",
                    type="0",
                ),
                GVMScanConfig(
                    id=self.SCAN_CONFIG_DISCOVERY,
                    name="Discovery",
                    type="0",
                ),
            ]
        
        response = self._gmp.get_scan_configs()
        return self._parser.parse_scan_configs(response)
    
    async def get_port_lists(self) -> List[GVMPortList]:
        """
        Obtener listas de puertos disponibles.
        
        Returns:
            Lista de GVMPortList
        """
        self._ensure_connected()
        
        if self.mock_mode:
            return [
                GVMPortList(
                    id=self.PORT_LIST_ALL_IANA_TCP,
                    name="All IANA assigned TCP",
                    port_count=65535,
                ),
            ]
        
        response = self._gmp.get_port_lists()
        return self._parser.parse_port_lists(response)
    
    # =========================================================================
    # HEALTH Y UTILIDADES
    # =========================================================================
    
    async def get_version(self) -> str:
        """
        Obtener versión de GVM.
        
        Returns:
            String con versión
        """
        self._ensure_connected()
        return self._version or "unknown"
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Verificar estado de GVM.
        
        Returns:
            Dict con estado de salud
        """
        try:
            if not self._authenticated:
                await self.connect()
            
            version = await self.get_version()
            
            return {
                "status": "healthy",
                "version": version,
                "connected": self._authenticated,
                "mock_mode": self.mock_mode,
                "host": self.host,
                "port": self.port,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False,
                "mock_mode": self.mock_mode,
            }
    
    # =========================================================================
    # OPERACIONES DE ALTO NIVEL
    # =========================================================================
    
    async def quick_scan(
        self,
        hosts: str,
        name: Optional[str] = None,
        config_id: Optional[str] = None,
        wait_for_completion: bool = False,
        poll_interval: int = 30,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Ejecutar un escaneo rápido.
        
        Crea target, task, inicia escaneo y opcionalmente espera.
        
        Args:
            hosts: IPs o rangos a escanear
            name: Nombre del escaneo (autogenerado si no se especifica)
            config_id: Config de escaneo (default: Full and fast)
            wait_for_completion: Si True, espera a que termine
            poll_interval: Segundos entre checks de estado
            timeout: Timeout máximo en segundos
        
        Returns:
            Dict con IDs y estado del escaneo
        """
        self._ensure_connected()
        
        # Generar nombre si no se especifica
        if not name:
            name = f"NestSecure-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Crear target
        target_id = await self.create_target(
            name=f"{name}-target",
            hosts=hosts,
        )
        
        try:
            # Crear task
            task_id = await self.create_task(
                name=name,
                target_id=target_id,
                config_id=config_id,
            )
            
            # Iniciar escaneo
            report_id = await self.start_task(task_id)
            
            result = {
                "name": name,
                "target_id": target_id,
                "task_id": task_id,
                "report_id": report_id,
                "status": "started",
                "hosts": hosts,
            }
            
            # Esperar si se solicita
            if wait_for_completion:
                timeout = timeout or self.timeout
                start_time = datetime.utcnow()
                
                while True:
                    task = await self.get_task_status(task_id)
                    result["status"] = task.status
                    result["progress"] = task.progress
                    
                    if task.is_done:
                        # Obtener reporte
                        report = await self.get_report(report_id)
                        result["report"] = report.get_summary()
                        result["status"] = "completed"
                        break
                    
                    # Check timeout
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed > timeout:
                        result["status"] = "timeout"
                        break
                    
                    await asyncio.sleep(poll_interval)
            
            return result
            
        except Exception as e:
            # Cleanup en caso de error
            try:
                await self.delete_target(target_id)
            except Exception:
                pass
            raise


# =============================================================================
# SINGLETON
# =============================================================================

_gvm_client: Optional[GVMClient] = None


def get_gvm_client(mock_mode: bool = False) -> GVMClient:
    """
    Obtener instancia del cliente GVM.
    
    Args:
        mock_mode: Si True, retorna cliente en modo mock
    
    Returns:
        GVMClient instance
    """
    global _gvm_client
    
    if _gvm_client is None or _gvm_client.mock_mode != mock_mode:
        _gvm_client = GVMClient(mock_mode=mock_mode)
    
    return _gvm_client


def reset_gvm_client() -> None:
    """Resetear el cliente GVM (útil para testing)."""
    global _gvm_client
    _gvm_client = None
