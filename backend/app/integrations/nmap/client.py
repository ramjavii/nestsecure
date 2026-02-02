# =============================================================================
# NESTSECURE - Nmap Scanner Client
# =============================================================================
"""
Cliente para ejecutar escaneos Nmap.

Este módulo proporciona una interfaz de alto nivel para ejecutar
escaneos Nmap y obtener resultados tipados.

Características:
- Ejecución de escaneos con perfiles predefinidos
- Modo mock para testing sin Nmap instalado
- Manejo de timeouts y errores
- Verificación de permisos
"""

import asyncio
import subprocess
import shutil
import os
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Callable

from .models import NmapScanResult, NmapHost, HostState
from .profiles import (
    NmapProfile,
    SCAN_PROFILES,
    DEFAULT_PROFILE,
    get_profile,
)
from .parser import NmapParser
from .exceptions import (
    NmapError,
    NmapNotFoundError,
    NmapTimeoutError,
    NmapPermissionError,
    NmapExecutionError,
    NmapTargetError,
)


logger = logging.getLogger(__name__)


class NmapScanner:
    """
    Cliente para ejecutar escaneos Nmap.
    
    Proporciona una interfaz de alto nivel para ejecutar escaneos
    con perfiles predefinidos o argumentos personalizados.
    
    Attributes:
        mock_mode: Si está en modo mock (no ejecuta Nmap real)
        nmap_path: Ruta al binario de Nmap
        default_timeout: Timeout por defecto en segundos
        
    Uso:
        # Modo normal
        scanner = NmapScanner()
        result = await scanner.scan("192.168.1.0/24", profile="standard")
        
        # Modo mock para testing
        scanner = NmapScanner(mock_mode=True)
        result = await scanner.scan("192.168.1.1")  # Retorna datos mock
    """
    
    def __init__(
        self,
        mock_mode: bool = False,
        nmap_path: Optional[str] = None,
        default_timeout: int = 3600,
        work_dir: Optional[str] = None,
    ):
        """
        Inicializar cliente Nmap.
        
        Args:
            mock_mode: Si usar modo mock (no ejecuta Nmap real)
            nmap_path: Ruta personalizada al binario de Nmap
            default_timeout: Timeout por defecto en segundos (1 hora)
            work_dir: Directorio de trabajo para archivos temporales
        """
        self.mock_mode = mock_mode
        self.default_timeout = default_timeout
        self.work_dir = work_dir or tempfile.gettempdir()
        
        if not mock_mode:
            self.nmap_path = nmap_path or self._find_nmap()
            if not self.nmap_path:
                raise NmapNotFoundError()
        else:
            self.nmap_path = "nmap"  # Dummy para mock
        
        self._parser = NmapParser()
        
        logger.info(
            f"NmapScanner initialized - mock_mode={mock_mode}, "
            f"nmap_path={self.nmap_path}"
        )
    
    def _find_nmap(self) -> Optional[str]:
        """
        Encontrar el binario de Nmap en el sistema.
        
        Returns:
            Ruta al binario o None si no se encuentra
        """
        # Usar shutil.which para encontrar en PATH
        nmap_path = shutil.which("nmap")
        if nmap_path:
            return nmap_path
        
        # Buscar en ubicaciones comunes
        common_paths = [
            "/usr/bin/nmap",
            "/usr/local/bin/nmap",
            "/opt/homebrew/bin/nmap",  # macOS con Homebrew
            "/snap/bin/nmap",
            "C:\\Program Files (x86)\\Nmap\\nmap.exe",
            "C:\\Program Files\\Nmap\\nmap.exe",
        ]
        
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return None
    
    def check_root_privileges(self) -> bool:
        """
        Verificar si tenemos privilegios de root/admin.
        
        Returns:
            True si tenemos privilegios elevados
        """
        if os.name == 'nt':  # Windows
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                return False
        else:  # Unix/Linux/macOS
            return os.geteuid() == 0
    
    def get_version(self) -> str:
        """
        Obtener versión de Nmap.
        
        Returns:
            String con la versión de Nmap
            
        Raises:
            NmapExecutionError: Si falla al obtener versión
        """
        if self.mock_mode:
            return "Nmap 7.94 (Mock Mode)"
        
        try:
            result = subprocess.run(
                [self.nmap_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Primera línea contiene la versión
            return result.stdout.strip().split('\n')[0]
        except subprocess.TimeoutExpired:
            raise NmapExecutionError("Timeout getting Nmap version")
        except Exception as e:
            raise NmapExecutionError(f"Failed to get Nmap version: {str(e)}")
    
    async def scan(
        self,
        target: str,
        profile: Optional[str] = None,
        arguments: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        callback: Optional[Callable[[str], None]] = None,
    ) -> NmapScanResult:
        """
        Ejecutar escaneo Nmap.
        
        Args:
            target: IP, rango CIDR o hostname a escanear
            profile: Nombre del perfil a usar (opcional)
            arguments: Argumentos personalizados (override de profile)
            timeout: Timeout en segundos (opcional)
            callback: Función callback para progress updates
            
        Returns:
            NmapScanResult con los resultados del escaneo
            
        Raises:
            NmapError: Para errores generales
            NmapTimeoutError: Si excede el timeout
            NmapPermissionError: Si faltan permisos
            NmapTargetError: Si el target es inválido
        """
        # Validar target
        self._validate_target(target)
        
        # Obtener perfil
        scan_profile = None
        if profile:
            scan_profile = get_profile(profile)
            if not scan_profile:
                logger.warning(f"Profile '{profile}' not found, using default")
                scan_profile = DEFAULT_PROFILE
        
        # Determinar argumentos
        if arguments:
            scan_args = arguments
        elif scan_profile:
            scan_args = scan_profile.arguments.copy()
        else:
            scan_args = DEFAULT_PROFILE.arguments.copy()
        
        # Determinar timeout
        scan_timeout = timeout or self.default_timeout
        
        # Verificar permisos si es necesario
        if scan_profile and scan_profile.requires_root:
            if not self.check_root_privileges():
                logger.warning(
                    f"Profile '{profile}' requires root privileges, "
                    "some features may not work"
                )
        
        # Ejecutar escaneo
        if self.mock_mode:
            return self._generate_mock_result(target, scan_profile)
        
        return await self._execute_scan(
            target, scan_args, scan_timeout, callback
        )
    
    async def quick_scan(self, target: str, timeout: int = 300) -> NmapScanResult:
        """
        Escaneo rápido con perfil quick.
        
        Args:
            target: Target a escanear
            timeout: Timeout en segundos (default 5 min)
            
        Returns:
            NmapScanResult
        """
        return await self.scan(target, profile="quick", timeout=timeout)
    
    async def full_scan(self, target: str, timeout: int = 3600) -> NmapScanResult:
        """
        Escaneo completo con perfil full.
        
        Args:
            target: Target a escanear
            timeout: Timeout en segundos (default 1 hora)
            
        Returns:
            NmapScanResult
        """
        return await self.scan(target, profile="full", timeout=timeout)
    
    async def vulnerability_scan(
        self,
        target: str,
        timeout: int = 3600
    ) -> NmapScanResult:
        """
        Escaneo de vulnerabilidades con perfil vulnerability.
        
        Args:
            target: Target a escanear
            timeout: Timeout en segundos
            
        Returns:
            NmapScanResult
        """
        return await self.scan(target, profile="vulnerability", timeout=timeout)
    
    async def discovery_scan(
        self,
        network: str,
        timeout: int = 600
    ) -> NmapScanResult:
        """
        Descubrimiento de hosts en red.
        
        Args:
            network: Red CIDR a escanear
            timeout: Timeout en segundos
            
        Returns:
            NmapScanResult
        """
        return await self.scan(network, profile="discovery", timeout=timeout)
    
    def _validate_target(self, target: str) -> None:
        """
        Validar target de escaneo.
        
        Args:
            target: Target a validar
            
        Raises:
            NmapTargetError: Si el target es inválido
        """
        if not target or not target.strip():
            raise NmapTargetError(target, "Target cannot be empty")
        
        # Limpiar target
        target = target.strip()
        
        # Detectar caracteres peligrosos (inyección de comandos)
        dangerous_chars = [';', '|', '&', '$', '`', '>', '<', '\n', '\r']
        for char in dangerous_chars:
            if char in target:
                raise NmapTargetError(
                    target,
                    f"Invalid character '{char}' in target"
                )
        
        # Verificar que no sea muy largo
        if len(target) > 256:
            raise NmapTargetError(target, "Target too long (max 256 chars)")
    
    async def _execute_scan(
        self,
        target: str,
        arguments: List[str],
        timeout: int,
        callback: Optional[Callable[[str], None]] = None,
    ) -> NmapScanResult:
        """
        Ejecutar escaneo Nmap real.
        
        Args:
            target: Target a escanear
            arguments: Argumentos de Nmap
            timeout: Timeout en segundos
            callback: Callback para progress
            
        Returns:
            NmapScanResult
        """
        # Crear archivo temporal para output XML
        xml_output = os.path.join(
            self.work_dir,
            f"nmap_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        )
        
        # Construir comando
        cmd = [self.nmap_path]
        cmd.extend(arguments)
        cmd.extend(["-oX", xml_output])
        cmd.append(target)
        
        logger.info(f"Executing Nmap scan: {' '.join(cmd)}")
        
        if callback:
            callback(f"Starting scan: {' '.join(cmd)}")
        
        try:
            # Ejecutar proceso asíncrono
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise NmapTimeoutError(timeout, target)
            
            # Verificar resultado
            if process.returncode != 0:
                stderr_text = stderr.decode('utf-8', errors='replace')
                
                # Detectar errores comunes
                if 'requires root' in stderr_text.lower():
                    raise NmapPermissionError(
                        "This scan requires root privileges"
                    )
                elif 'failed to resolve' in stderr_text.lower():
                    raise NmapTargetError(target, "Failed to resolve hostname")
                else:
                    raise NmapExecutionError(
                        f"Nmap exited with code {process.returncode}: {stderr_text}"
                    )
            
            # Parsear resultados
            if not os.path.exists(xml_output):
                raise NmapExecutionError("XML output file was not created")
            
            result = self._parser.parse_file(xml_output)
            
            if callback:
                callback(f"Scan completed: {result.hosts_up} hosts up")
            
            return result
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(xml_output):
                try:
                    os.remove(xml_output)
                except:
                    pass
    
    def _generate_mock_result(
        self,
        target: str,
        profile: Optional[NmapProfile] = None
    ) -> NmapScanResult:
        """
        Generar resultado mock para testing.
        
        Args:
            target: Target del escaneo
            profile: Perfil usado
            
        Returns:
            NmapScanResult con datos ficticios
        """
        from .models import NmapPort, NmapVulnerability, NmapOS, PortState
        
        logger.info(f"Generating mock scan result for {target}")
        
        # Determinar IPs mock según target
        if '/' in target:  # CIDR
            mock_ips = [f"192.168.1.{i}" for i in range(1, 6)]
        else:
            mock_ips = [target]
        
        hosts = []
        for ip in mock_ips:
            # Crear puertos mock
            ports = [
                NmapPort(
                    port=22,
                    protocol="tcp",
                    state=PortState.OPEN,
                    service_name="ssh",
                    product="OpenSSH",
                    version="8.9",
                ),
                NmapPort(
                    port=80,
                    protocol="tcp",
                    state=PortState.OPEN,
                    service_name="http",
                    product="nginx",
                    version="1.18.0",
                ),
                NmapPort(
                    port=443,
                    protocol="tcp",
                    state=PortState.OPEN,
                    service_name="https",
                    product="nginx",
                    version="1.18.0",
                    ssl_enabled=True,
                ),
            ]
            
            # Crear vulnerabilidades mock si es perfil de vulnerabilidades
            vulnerabilities = []
            if profile and 'vuln' in profile.name.lower():
                vulnerabilities = [
                    NmapVulnerability(
                        script_id="http-vuln-cve2021-41773",
                        title="Apache HTTP Server Path Traversal",
                        state="VULNERABLE",
                        cvss=7.5,
                        cves=["CVE-2021-41773"],
                        port=80,
                        protocol="tcp",
                    ),
                    NmapVulnerability(
                        script_id="ssl-heartbleed",
                        title="OpenSSL Heartbleed Vulnerability",
                        state="NOT VULNERABLE",
                        cvss=None,
                        cves=["CVE-2014-0160"],
                        port=443,
                        protocol="tcp",
                    ),
                ]
            
            host = NmapHost(
                ip_address=ip,
                state=HostState.UP,
                hostname=f"host-{ip.split('.')[-1]}.local",
                os=NmapOS(
                    name="Linux 5.x",
                    accuracy=95,
                    family="Linux",
                    generation="5.x",
                ),
                ports=ports,
                vulnerabilities=vulnerabilities,
            )
            hosts.append(host)
        
        return NmapScanResult(
            hosts=hosts,
            scan_type=profile.name if profile else "mock",
            arguments=" ".join(profile.arguments) if profile else "--mock",
            start_time=datetime.now(),
            end_time=datetime.now(),
            elapsed_seconds=5.0,
            hosts_up=len(hosts),
            hosts_down=0,
            hosts_total=len(hosts),
            scanner_version="Nmap 7.94 (Mock Mode)",
        )


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

async def quick_scan(target: str, mock_mode: bool = False) -> NmapScanResult:
    """
    Función de conveniencia para escaneo rápido.
    
    Args:
        target: Target a escanear
        mock_mode: Si usar modo mock
        
    Returns:
        NmapScanResult
    """
    scanner = NmapScanner(mock_mode=mock_mode)
    return await scanner.quick_scan(target)


async def full_scan(target: str, mock_mode: bool = False) -> NmapScanResult:
    """
    Función de conveniencia para escaneo completo.
    
    Args:
        target: Target a escanear
        mock_mode: Si usar modo mock
        
    Returns:
        NmapScanResult
    """
    scanner = NmapScanner(mock_mode=mock_mode)
    return await scanner.full_scan(target)


def check_nmap_installed() -> bool:
    """
    Verificar si Nmap está instalado.
    
    Returns:
        True si Nmap está disponible
    """
    try:
        scanner = NmapScanner()
        return True
    except NmapNotFoundError:
        return False
