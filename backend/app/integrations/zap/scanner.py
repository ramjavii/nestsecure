# =============================================================================
# NESTSECURE - Escáner ZAP
# =============================================================================
"""
Orquestador de escaneos con OWASP ZAP.

Gestiona el flujo completo de escaneo:
1. Preparación (crear contexto, configurar scope)
2. Spider (descubrimiento de URLs)
3. Ajax Spider (para SPAs)
4. Active Scan (pruebas de vulnerabilidades)
5. Recolección de alertas
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Callable, Any

from app.utils.logger import get_logger
from app.integrations.zap.client import ZapClient, ZapClientError
from app.integrations.zap.config import (
    ZAP_SCAN_POLICIES,
    ZAP_SPIDER_CONFIG,
    ZAP_AJAX_SPIDER_CONFIG,
)


logger = get_logger(__name__)


class ZapScanMode(str, Enum):
    """Modos de escaneo disponibles."""
    QUICK = "quick"
    STANDARD = "standard"
    FULL = "full"
    API = "api"
    PASSIVE = "passive"
    SPA = "spa"
    SPIDER_ONLY = "spider_only"
    ACTIVE_ONLY = "active_only"


@dataclass
class ZapScanProgress:
    """Progreso actual del escaneo."""
    phase: str = "initializing"
    spider_progress: int = 0
    ajax_spider_progress: int = 0
    active_scan_progress: int = 0
    passive_scan_pending: int = 0
    urls_found: int = 0
    alerts_found: int = 0
    start_time: Optional[datetime] = None
    current_time: Optional[datetime] = None
    
    @property
    def overall_progress(self) -> int:
        """Calcular progreso general."""
        if self.phase == "completed":
            return 100
        if self.phase == "spider":
            return self.spider_progress // 4  # 0-25%
        if self.phase == "ajax_spider":
            return 25 + (self.ajax_spider_progress // 4)  # 25-50%
        if self.phase == "active_scan":
            return 50 + (self.active_scan_progress // 2)  # 50-100%
        if self.phase == "passive_scan":
            return 90  # Casi terminado
        return 0
    
    @property
    def elapsed_seconds(self) -> float:
        """Tiempo transcurrido en segundos."""
        if not self.start_time:
            return 0
        current = self.current_time or datetime.now(timezone.utc)
        return (current - self.start_time).total_seconds()


@dataclass
class ZapScanResult:
    """Resultado de un escaneo ZAP."""
    target_url: str
    mode: ZapScanMode
    success: bool
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    urls_found: int = 0
    alerts: List[Dict] = field(default_factory=list)
    alerts_summary: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    spider_scan_id: Optional[str] = None
    active_scan_id: Optional[str] = None
    context_name: Optional[str] = None


class ZapScanner:
    """
    Orquestador de escaneos OWASP ZAP.
    
    Ejemplo de uso:
        async with ZapClient() as client:
            scanner = ZapScanner(client)
            result = await scanner.scan("http://target.local", mode=ZapScanMode.FULL)
            print(f"Encontradas {len(result.alerts)} alertas")
    """
    
    def __init__(
        self,
        client: ZapClient,
        progress_callback: Optional[Callable[[ZapScanProgress], None]] = None,
    ):
        """
        Inicializar escáner.
        
        Args:
            client: Cliente ZAP conectado
            progress_callback: Callback para reportar progreso
        """
        self.client = client
        self.progress_callback = progress_callback
        self._progress = ZapScanProgress()
        self._cancelled = False
    
    def cancel(self) -> None:
        """Cancelar escaneo en curso."""
        self._cancelled = True
    
    def _update_progress(self, **kwargs) -> None:
        """Actualizar y reportar progreso."""
        for key, value in kwargs.items():
            if hasattr(self._progress, key):
                setattr(self._progress, key, value)
        
        self._progress.current_time = datetime.now(timezone.utc)
        
        if self.progress_callback:
            self.progress_callback(self._progress)
    
    async def scan(
        self,
        url: str,
        mode: ZapScanMode = ZapScanMode.STANDARD,
        context_name: Optional[str] = None,
        timeout: Optional[int] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> ZapScanResult:
        """
        Ejecutar escaneo completo.
        
        Args:
            url: URL objetivo a escanear
            mode: Modo de escaneo
            context_name: Nombre del contexto (se genera uno si no se provee)
            timeout: Timeout total en segundos
            include_patterns: Patrones regex a incluir en el contexto
            exclude_patterns: Patrones regex a excluir del contexto
        
        Returns:
            Resultado del escaneo con alertas encontradas
        """
        self._cancelled = False
        self._progress = ZapScanProgress()
        self._progress.start_time = datetime.now(timezone.utc)
        
        # Obtener configuración del modo
        policy = ZAP_SCAN_POLICIES.get(mode.value, ZAP_SCAN_POLICIES["standard"])
        timeout = timeout or policy.get("timeout", 1800)
        
        errors: List[str] = []
        spider_scan_id: Optional[str] = None
        active_scan_id: Optional[str] = None
        
        try:
            # Preparar contexto
            self._update_progress(phase="preparing")
            context_name = context_name or f"nestsecure_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                await self._setup_context(url, context_name, include_patterns, exclude_patterns)
            except Exception as e:
                logger.warning(f"No se pudo crear contexto: {e}. Continuando sin contexto.")
                context_name = None
            
            # Acceder a la URL inicial
            logger.info(f"Accediendo a URL inicial: {url}")
            await self.client.access_url(url)
            
            # Spider
            if policy.get("spider", True) and not self._cancelled:
                self._update_progress(phase="spider")
                spider_scan_id = await self._run_spider(url, context_name, timeout // 4)
            
            # Ajax Spider (para SPAs)
            if policy.get("ajax_spider", False) and not self._cancelled:
                self._update_progress(phase="ajax_spider")
                await self._run_ajax_spider(url, context_name, timeout // 4)
            
            # Esperar escaneo pasivo
            if not self._cancelled:
                self._update_progress(phase="passive_scan")
                await self._wait_passive_scan(timeout=60)
            
            # Active Scan
            if policy.get("active_scan", False) and not self._cancelled:
                self._update_progress(phase="active_scan")
                active_scan_id = await self._run_active_scan(
                    url, 
                    context_name, 
                    timeout // 2,
                    policy.get("policy"),
                )
            
            # Recolectar resultados
            self._update_progress(phase="collecting")
            urls = await self.client.get_urls(url)
            alerts = await self.client.get_alerts(base_url=url, count=1000)
            alerts_summary = await self.client.get_alerts_summary(url)
            
            self._update_progress(
                phase="completed",
                urls_found=len(urls),
                alerts_found=len(alerts),
            )
            
            end_time = datetime.now(timezone.utc)
            
            return ZapScanResult(
                target_url=url,
                mode=mode,
                success=True,
                start_time=self._progress.start_time,
                end_time=end_time,
                duration_seconds=(end_time - self._progress.start_time).total_seconds(),
                urls_found=len(urls),
                alerts=alerts,
                alerts_summary=alerts_summary,
                errors=errors,
                spider_scan_id=spider_scan_id,
                active_scan_id=active_scan_id,
                context_name=context_name,
            )
            
        except Exception as e:
            logger.error(f"Error en escaneo ZAP: {e}")
            errors.append(str(e))
            
            end_time = datetime.now(timezone.utc)
            
            # Intentar recolectar alertas incluso si hubo error
            try:
                alerts = await self.client.get_alerts(base_url=url, count=1000)
                alerts_summary = await self.client.get_alerts_summary(url)
            except:
                alerts = []
                alerts_summary = {}
            
            return ZapScanResult(
                target_url=url,
                mode=mode,
                success=False,
                start_time=self._progress.start_time,
                end_time=end_time,
                duration_seconds=(end_time - self._progress.start_time).total_seconds(),
                alerts=alerts,
                alerts_summary=alerts_summary,
                errors=errors,
                spider_scan_id=spider_scan_id,
                active_scan_id=active_scan_id,
                context_name=context_name,
            )
    
    async def _setup_context(
        self,
        url: str,
        context_name: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> str:
        """Configurar contexto de escaneo."""
        # Crear contexto
        context_id = await self.client.create_context(context_name)
        logger.info(f"Contexto creado: {context_name} (ID: {context_id})")
        
        # Incluir URL base
        # Escapar caracteres especiales de regex
        import re
        base_regex = re.escape(url) + ".*"
        await self.client.include_in_context(context_name, base_regex)
        
        # Patrones adicionales
        if include_patterns:
            for pattern in include_patterns:
                await self.client.include_in_context(context_name, pattern)
        
        if exclude_patterns:
            for pattern in exclude_patterns:
                await self.client.exclude_from_context(context_name, pattern)
        
        return context_id
    
    async def _run_spider(
        self,
        url: str,
        context_name: Optional[str],
        timeout: int,
    ) -> str:
        """Ejecutar spider."""
        logger.info(f"Iniciando spider en {url}")
        
        scan_id = await self.client.spider_scan(
            url=url,
            max_children=ZAP_SPIDER_CONFIG.get("max_children", 10),
            recurse=True,
            context_name=context_name,
            subtree_only=ZAP_SPIDER_CONFIG.get("subtree_only", True),
        )
        
        logger.info(f"Spider iniciado con ID: {scan_id}")
        
        # Esperar con actualizaciones de progreso
        start_time = asyncio.get_event_loop().time()
        
        while not self._cancelled:
            status = await self.client.spider_status(scan_id)
            self._update_progress(spider_progress=status)
            
            if status >= 100:
                break
            
            if (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Spider timeout después de {timeout}s")
                await self.client.spider_stop(scan_id)
                break
            
            await asyncio.sleep(2)
        
        # Obtener resultados
        results = await self.client.spider_results(scan_id)
        self._update_progress(urls_found=len(results))
        logger.info(f"Spider completado. URLs encontradas: {len(results)}")
        
        return scan_id
    
    async def _run_ajax_spider(
        self,
        url: str,
        context_name: Optional[str],
        timeout: int,
    ) -> None:
        """Ejecutar Ajax Spider."""
        logger.info(f"Iniciando Ajax Spider en {url}")
        
        await self.client.ajax_spider_scan(
            url=url,
            in_scope=True,
            context_name=context_name,
            subtree_only=True,
        )
        
        # Esperar con actualizaciones de progreso
        start_time = asyncio.get_event_loop().time()
        max_duration = ZAP_AJAX_SPIDER_CONFIG.get("max_duration", 10) * 60
        actual_timeout = min(timeout, max_duration)
        
        while not self._cancelled:
            status = await self.client.ajax_spider_status()
            num_results = await self.client.ajax_spider_number_of_results()
            
            # Calcular progreso estimado
            elapsed = asyncio.get_event_loop().time() - start_time
            progress = min(int((elapsed / actual_timeout) * 100), 99)
            self._update_progress(ajax_spider_progress=progress)
            
            if status == "stopped":
                break
            
            if elapsed > actual_timeout:
                logger.warning(f"Ajax Spider timeout después de {actual_timeout}s")
                await self.client.ajax_spider_stop()
                break
            
            await asyncio.sleep(5)
        
        num_results = await self.client.ajax_spider_number_of_results()
        logger.info(f"Ajax Spider completado. Resultados: {num_results}")
    
    async def _run_active_scan(
        self,
        url: str,
        context_name: Optional[str],
        timeout: int,
        policy_name: Optional[str] = None,
    ) -> str:
        """Ejecutar escaneo activo."""
        logger.info(f"Iniciando escaneo activo en {url}")
        
        scan_id = await self.client.active_scan(
            url=url,
            recurse=True,
            in_scope_only=True,
            scan_policy_name=policy_name,
        )
        
        logger.info(f"Escaneo activo iniciado con ID: {scan_id}")
        
        # Esperar con actualizaciones de progreso
        start_time = asyncio.get_event_loop().time()
        
        while not self._cancelled:
            status = await self.client.active_scan_status(scan_id)
            self._update_progress(active_scan_progress=status)
            
            # Actualizar conteo de alertas periódicamente
            try:
                alert_count = await self.client.get_alerts_count(url)
                self._update_progress(alerts_found=alert_count)
            except:
                pass
            
            if status >= 100:
                break
            
            if (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Escaneo activo timeout después de {timeout}s")
                await self.client.active_scan_stop(scan_id)
                break
            
            await asyncio.sleep(5)
        
        logger.info(f"Escaneo activo completado.")
        return scan_id
    
    async def _wait_passive_scan(self, timeout: int = 60) -> None:
        """Esperar a que termine el escaneo pasivo."""
        logger.info("Esperando escaneo pasivo...")
        
        start_time = asyncio.get_event_loop().time()
        
        while not self._cancelled:
            records = await self.client.passive_scan_records_to_scan()
            self._update_progress(passive_scan_pending=records)
            
            if records == 0:
                break
            
            if (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Passive scan timeout, {records} registros pendientes")
                break
            
            await asyncio.sleep(2)
        
        logger.info("Escaneo pasivo completado.")
    
    async def quick_scan(self, url: str) -> ZapScanResult:
        """Atajo para escaneo rápido."""
        return await self.scan(url, mode=ZapScanMode.QUICK)
    
    async def full_scan(self, url: str) -> ZapScanResult:
        """Atajo para escaneo completo."""
        return await self.scan(url, mode=ZapScanMode.FULL)
    
    async def api_scan(
        self,
        url: str,
        openapi_url: Optional[str] = None,
    ) -> ZapScanResult:
        """
        Escaneo de API.
        
        Args:
            url: URL base de la API
            openapi_url: URL de la especificación OpenAPI/Swagger
        """
        # Importar OpenAPI si está disponible
        if openapi_url:
            try:
                await self.client.import_openapi(url=openapi_url, target=url)
                logger.info(f"OpenAPI importado desde {openapi_url}")
            except Exception as e:
                logger.warning(f"No se pudo importar OpenAPI: {e}")
        
        return await self.scan(url, mode=ZapScanMode.API)
    
    async def spa_scan(self, url: str) -> ZapScanResult:
        """Atajo para escaneo de Single Page Application."""
        return await self.scan(url, mode=ZapScanMode.SPA)
