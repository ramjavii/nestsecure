# =============================================================================
# NESTSECURE - Nuclei Scanner Client
# =============================================================================
"""
Cliente para ejecutar escaneos Nuclei.

Este módulo proporciona una interfaz de alto nivel para ejecutar
escaneos de vulnerabilidades con Nuclei.

Características:
- Ejecución de escaneos con perfiles predefinidos
- Modo mock para testing sin Nuclei instalado
- Actualización automática de templates
- Manejo de timeouts y errores
"""

import asyncio
import subprocess
import shutil
import os
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from .models import NucleiScanResult, NucleiFinding, Severity
from .profiles import (
    NucleiProfile,
    SCAN_PROFILES,
    DEFAULT_PROFILE,
    get_profile,
)
from .parser import NucleiParser
from .exceptions import (
    NucleiError,
    NucleiNotFoundError,
    NucleiTimeoutError,
    NucleiTargetError,
    NucleiExecutionError,
    NucleiTemplateError,
)


logger = logging.getLogger(__name__)


class NucleiScanner:
    """
    Cliente para ejecutar escaneos Nuclei.
    
    Proporciona una interfaz de alto nivel para ejecutar escaneos
    de vulnerabilidades con perfiles predefinidos o configuraciones
    personalizadas.
    
    Attributes:
        mock_mode: Si está en modo mock (no ejecuta Nuclei real)
        nuclei_path: Ruta al binario de Nuclei
        templates_path: Ruta a los templates
        default_timeout: Timeout por defecto en segundos
        
    Uso:
        # Modo normal
        scanner = NucleiScanner()
        result = await scanner.scan("https://example.com", profile="standard")
        
        # Modo mock para testing
        scanner = NucleiScanner(mock_mode=True)
        result = await scanner.scan("https://example.com")
    """
    
    def __init__(
        self,
        mock_mode: bool = False,
        nuclei_path: Optional[str] = None,
        templates_path: Optional[str] = None,
        default_timeout: int = 3600,
        work_dir: Optional[str] = None,
    ):
        """
        Inicializar cliente Nuclei.
        
        Args:
            mock_mode: Si usar modo mock
            nuclei_path: Ruta personalizada al binario de Nuclei
            templates_path: Ruta a templates personalizados
            default_timeout: Timeout por defecto en segundos
            work_dir: Directorio de trabajo para archivos temporales
        """
        self.mock_mode = mock_mode
        self.default_timeout = default_timeout
        self.work_dir = work_dir or tempfile.gettempdir()
        self.templates_path = templates_path
        
        if not mock_mode:
            self.nuclei_path = nuclei_path or self._find_nuclei()
            if not self.nuclei_path:
                raise NucleiNotFoundError()
        else:
            self.nuclei_path = "nuclei"
        
        self._parser = NucleiParser()
        
        logger.info(
            f"NucleiScanner initialized - mock_mode={mock_mode}, "
            f"nuclei_path={self.nuclei_path}"
        )
    
    def _find_nuclei(self) -> Optional[str]:
        """
        Encontrar el binario de Nuclei en el sistema.
        
        Returns:
            Ruta al binario o None si no se encuentra
        """
        # Usar shutil.which para encontrar en PATH
        nuclei_path = shutil.which("nuclei")
        if nuclei_path:
            return nuclei_path
        
        # Buscar en ubicaciones comunes
        common_paths = [
            "/usr/bin/nuclei",
            "/usr/local/bin/nuclei",
            "/opt/homebrew/bin/nuclei",
            os.path.expanduser("~/go/bin/nuclei"),
            os.path.expanduser("~/.local/bin/nuclei"),
        ]
        
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return None
    
    def get_version(self) -> str:
        """
        Obtener versión de Nuclei.
        
        Returns:
            String con la versión de Nuclei
        """
        if self.mock_mode:
            return "Nuclei v3.0.0 (Mock Mode)"
        
        try:
            result = subprocess.run(
                [self.nuclei_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            raise NucleiExecutionError("Timeout getting Nuclei version")
        except Exception as e:
            raise NucleiExecutionError(f"Failed to get Nuclei version: {str(e)}")
    
    async def update_templates(self) -> bool:
        """
        Actualizar templates de Nuclei.
        
        Returns:
            True si la actualización fue exitosa
        """
        if self.mock_mode:
            logger.info("Mock mode: skipping template update")
            return True
        
        logger.info("Updating Nuclei templates...")
        
        try:
            process = await asyncio.create_subprocess_exec(
                self.nuclei_path,
                "-update-templates",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300  # 5 minutos para actualización
            )
            
            if process.returncode == 0:
                logger.info("Templates updated successfully")
                return True
            else:
                logger.warning(f"Template update failed: {stderr.decode()}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Template update timed out")
            return False
        except Exception as e:
            logger.error(f"Template update error: {str(e)}")
            return False
    
    async def scan(
        self,
        target: str,
        profile: Optional[str] = None,
        tags: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        templates: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        callback: Optional[Callable[[NucleiFinding], None]] = None,
    ) -> NucleiScanResult:
        """
        Ejecutar escaneo Nuclei.
        
        Args:
            target: URL o IP a escanear
            profile: Nombre del perfil a usar
            tags: Tags específicos (override de profile)
            severities: Severidades específicas
            templates: Templates específicos
            timeout: Timeout en segundos
            callback: Función callback para cada finding
            
        Returns:
            NucleiScanResult con los resultados
            
        Raises:
            NucleiError: Para errores generales
            NucleiTimeoutError: Si excede el timeout
            NucleiTargetError: Si el target es inválido
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
        else:
            scan_profile = DEFAULT_PROFILE
        
        # Determinar timeout
        scan_timeout = timeout or self.default_timeout
        
        # Ejecutar escaneo
        if self.mock_mode:
            return self._generate_mock_result(target, scan_profile)
        
        return await self._execute_scan(
            target, scan_profile, tags, severities, templates,
            scan_timeout, callback
        )
    
    async def quick_scan(
        self,
        target: str,
        timeout: int = 600
    ) -> NucleiScanResult:
        """
        Escaneo rápido con perfil quick.
        
        Args:
            target: Target a escanear
            timeout: Timeout en segundos
            
        Returns:
            NucleiScanResult
        """
        return await self.scan(target, profile="quick", timeout=timeout)
    
    async def full_scan(
        self,
        target: str,
        timeout: int = 7200
    ) -> NucleiScanResult:
        """
        Escaneo completo con perfil full.
        
        Args:
            target: Target a escanear
            timeout: Timeout en segundos (default 2 horas)
            
        Returns:
            NucleiScanResult
        """
        return await self.scan(target, profile="full", timeout=timeout)
    
    async def cve_scan(
        self,
        target: str,
        timeout: int = 3600
    ) -> NucleiScanResult:
        """
        Escaneo enfocado en CVEs.
        
        Args:
            target: Target a escanear
            timeout: Timeout en segundos
            
        Returns:
            NucleiScanResult
        """
        return await self.scan(target, profile="cves", timeout=timeout)
    
    async def web_scan(
        self,
        target: str,
        timeout: int = 3600
    ) -> NucleiScanResult:
        """
        Escaneo de vulnerabilidades web.
        
        Args:
            target: Target a escanear
            timeout: Timeout en segundos
            
        Returns:
            NucleiScanResult
        """
        return await self.scan(target, profile="web", timeout=timeout)
    
    def _validate_target(self, target: str) -> None:
        """
        Validar target de escaneo.
        
        Args:
            target: Target a validar
            
        Raises:
            NucleiTargetError: Si el target es inválido
        """
        if not target or not target.strip():
            raise NucleiTargetError(target, "Target cannot be empty")
        
        target = target.strip()
        
        # Detectar caracteres peligrosos
        dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r']
        for char in dangerous_chars:
            if char in target:
                raise NucleiTargetError(
                    target,
                    f"Invalid character '{char}' in target"
                )
        
        # Verificar longitud
        if len(target) > 2048:
            raise NucleiTargetError(target, "Target URL too long")
    
    async def _execute_scan(
        self,
        target: str,
        profile: NucleiProfile,
        tags: Optional[List[str]],
        severities: Optional[List[str]],
        templates: Optional[List[str]],
        timeout: int,
        callback: Optional[Callable[[NucleiFinding], None]],
    ) -> NucleiScanResult:
        """
        Ejecutar escaneo Nuclei real.
        
        Args:
            target: Target a escanear
            profile: Perfil de escaneo
            tags: Tags override
            severities: Severidades override
            templates: Templates override
            timeout: Timeout en segundos
            callback: Callback por finding
            
        Returns:
            NucleiScanResult
        """
        # Crear archivo temporal para output
        output_file = os.path.join(
            self.work_dir,
            f"nuclei_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        
        # Construir comando
        cmd = [self.nuclei_path]
        cmd.extend(["-target", target])
        
        # Agregar argumentos del perfil
        cmd.extend(profile.get_arguments())
        
        # Override de tags si se especifican
        if tags:
            cmd.extend(["-tags", ",".join(tags)])
        
        # Override de severities si se especifican
        if severities:
            cmd.extend(["-severity", ",".join(severities)])
        
        # Templates específicos
        if templates:
            for t in templates:
                cmd.extend(["-t", t])
        
        # Templates path personalizado
        if self.templates_path:
            cmd.extend(["-t", self.templates_path])
        
        # Output a archivo
        cmd.extend(["-o", output_file])
        
        # Silenciar banners
        cmd.append("-silent")
        
        logger.info(f"Executing Nuclei scan: {' '.join(cmd)}")
        
        result = NucleiScanResult()
        result.start_time = datetime.now()
        result.targets = [target]
        
        try:
            # Ejecutar proceso
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
                raise NucleiTimeoutError(timeout, target)
            
            result.end_time = datetime.now()
            
            # Verificar resultado
            if process.returncode not in [0, 1]:  # 1 = findings found
                stderr_text = stderr.decode('utf-8', errors='replace')
                raise NucleiExecutionError(
                    f"Nuclei exited with code {process.returncode}: {stderr_text}",
                    exit_code=process.returncode,
                    stderr=stderr_text
                )
            
            # Parsear resultados
            if os.path.exists(output_file):
                parsed = self._parser.parse_file(output_file)
                result.findings = parsed.findings
                result.templates_used = parsed.templates_used
                result.matched_requests = len(result.findings)
            
            # Extraer estadísticas de stderr
            if stderr:
                stats = self._parser.extract_stats(stderr.decode('utf-8', errors='replace'))
                result.total_requests = stats.get("total_requests", 0)
                result.error_count = stats.get("errors", 0)
            
            # Ejecutar callbacks
            if callback and result.findings:
                for finding in result.findings:
                    try:
                        callback(finding)
                    except Exception as e:
                        logger.error(f"Callback error: {str(e)}")
            
            return result
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
    
    def _generate_mock_result(
        self,
        target: str,
        profile: NucleiProfile
    ) -> NucleiScanResult:
        """
        Generar resultado mock para testing.
        
        Args:
            target: Target del escaneo
            profile: Perfil usado
            
        Returns:
            NucleiScanResult con datos ficticios
        """
        from .models import NucleiTemplate, TemplateType
        
        logger.info(f"Generating mock Nuclei scan result for {target}")
        
        findings = []
        
        # Generar findings mock según severidades del perfil
        mock_findings_data = [
            {
                "template_id": "http-missing-security-headers",
                "name": "HTTP Missing Security Headers",
                "severity": Severity.INFO,
                "tags": ["misconfig", "generic"],
            },
            {
                "template_id": "ssl-dns-san",
                "name": "SSL Certificate - Subject Alternative Name",
                "severity": Severity.INFO,
                "tags": ["ssl", "tech"],
            },
            {
                "template_id": "wordpress-version",
                "name": "WordPress Version Detected",
                "severity": Severity.INFO,
                "tags": ["tech", "wordpress"],
            },
        ]
        
        # Agregar hallazgos de mayor severidad si el perfil los incluye
        if "high" in profile.severities or "critical" in profile.severities:
            mock_findings_data.extend([
                {
                    "template_id": "cve-2021-44228-log4j-rce",
                    "name": "Apache Log4j RCE (CVE-2021-44228)",
                    "severity": Severity.CRITICAL,
                    "tags": ["cve", "rce", "log4j"],
                    "cve": "CVE-2021-44228",
                    "cvss": 10.0,
                },
                {
                    "template_id": "http-sql-injection",
                    "name": "SQL Injection Detected",
                    "severity": Severity.HIGH,
                    "tags": ["sqli", "injection"],
                },
            ])
        
        for fd in mock_findings_data:
            if fd["severity"].value in profile.severities:
                template = NucleiTemplate(
                    id=fd["template_id"],
                    name=fd["name"],
                    author=["projectdiscovery"],
                    severity=fd["severity"],
                    tags=fd["tags"],
                    template_type=TemplateType.HTTP,
                    cve=fd.get("cve"),
                    cvss=fd.get("cvss"),
                )
                
                finding = NucleiFinding(
                    template=template,
                    host=target,
                    matched_at=f"{target}/vulnerable",
                    timestamp=datetime.now(),
                )
                findings.append(finding)
        
        return NucleiScanResult(
            findings=findings,
            targets=[target],
            templates_used=[f["template_id"] for f in mock_findings_data],
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_requests=100,
            matched_requests=len(findings),
        )


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

async def quick_scan(target: str, mock_mode: bool = False) -> NucleiScanResult:
    """
    Función de conveniencia para escaneo rápido.
    
    Args:
        target: Target a escanear
        mock_mode: Si usar modo mock
        
    Returns:
        NucleiScanResult
    """
    scanner = NucleiScanner(mock_mode=mock_mode)
    return await scanner.quick_scan(target)


async def full_scan(target: str, mock_mode: bool = False) -> NucleiScanResult:
    """
    Función de conveniencia para escaneo completo.
    
    Args:
        target: Target a escanear
        mock_mode: Si usar modo mock
        
    Returns:
        NucleiScanResult
    """
    scanner = NucleiScanner(mock_mode=mock_mode)
    return await scanner.full_scan(target)


def check_nuclei_installed() -> bool:
    """
    Verificar si Nuclei está instalado.
    
    Returns:
        True si Nuclei está disponible
    """
    try:
        scanner = NucleiScanner()
        return True
    except NucleiNotFoundError:
        return False
