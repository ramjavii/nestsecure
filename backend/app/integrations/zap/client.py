# =============================================================================
# NESTSECURE - Cliente API de OWASP ZAP
# =============================================================================
"""
Cliente HTTP para comunicarse con la API REST de OWASP ZAP.

Proporciona métodos para:
- Core: Acciones básicas del sistema
- Spider: Descubrimiento de URLs
- Ajax Spider: Descubrimiento para SPAs
- Active Scan: Escaneo activo de vulnerabilidades
- Passive Scan: Análisis pasivo de tráfico
- Alerts: Gestión de alertas encontradas
- Context: Configuración de contextos de escaneo
"""

import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlencode

import httpx

from app.config import get_settings
from app.utils.logger import get_logger
from app.integrations.zap.config import (
    ZAP_DEFAULT_HOST,
    ZAP_DEFAULT_PORT,
    ZAP_DEFAULT_TIMEOUT,
    ZAP_API_VERSION,
)


logger = get_logger(__name__)


class ZapClientError(Exception):
    """Error genérico del cliente ZAP."""
    pass


class ZapConnectionError(ZapClientError):
    """Error de conexión con ZAP."""
    pass


class ZapApiError(ZapClientError):
    """Error de la API de ZAP."""
    pass


class ZapClient:
    """
    Cliente para la API REST de OWASP ZAP.
    
    Ejemplo de uso:
        async with ZapClient() as client:
            version = await client.get_version()
            print(f"ZAP version: {version}")
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        timeout: int = ZAP_DEFAULT_TIMEOUT,
    ):
        """
        Inicializar cliente ZAP.
        
        Args:
            host: Host donde está corriendo ZAP
            port: Puerto de la API de ZAP
            api_key: API key para autenticación (vacío si está deshabilitado)
            timeout: Timeout para requests en segundos
        """
        settings = get_settings()
        
        self.host = host or settings.ZAP_HOST or ZAP_DEFAULT_HOST
        self.port = port or settings.ZAP_PORT or ZAP_DEFAULT_PORT
        self.api_key = api_key if api_key is not None else settings.ZAP_API_KEY
        self.timeout = timeout
        
        self.base_url = f"http://{self.host}:{self.port}"
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "ZapClient":
        """Context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
    
    async def connect(self) -> None:
        """Establecer conexión con ZAP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=30.0),
            )
            logger.info(f"Conectado a ZAP en {self.base_url}")
    
    async def close(self) -> None:
        """Cerrar conexión con ZAP."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Desconectado de ZAP")
    
    async def _request(
        self,
        component: str,
        action_type: str,  # view, action, other
        action: str,
        params: Optional[Dict] = None,
    ) -> Any:
        """
        Hacer request a la API de ZAP.
        
        Args:
            component: Componente de la API (core, spider, ascan, etc.)
            action_type: Tipo de acción (view, action, other)
            action: Nombre de la acción
            params: Parámetros adicionales
        
        Returns:
            Respuesta JSON de la API
        """
        if not self._client:
            await self.connect()
        
        # Construir URL
        url = f"/{ZAP_API_VERSION}/{component}/{action_type}/{action}/"
        
        # Agregar API key si está configurada
        request_params = params.copy() if params else {}
        if self.api_key:
            request_params["apikey"] = self.api_key
        
        try:
            response = await self._client.get(url, params=request_params)
            response.raise_for_status()
            
            data = response.json()
            
            # Verificar errores en la respuesta
            if isinstance(data, dict) and "code" in data and data.get("code") == "illegal_argument":
                raise ZapApiError(f"Error de API: {data.get('message', 'Unknown error')}")
            
            return data
            
        except httpx.ConnectError as e:
            logger.error(f"Error de conexión con ZAP: {e}")
            raise ZapConnectionError(f"No se pudo conectar a ZAP en {self.base_url}: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP de ZAP: {e.response.status_code}")
            raise ZapApiError(f"Error HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error inesperado en request a ZAP: {e}")
            raise ZapClientError(f"Error inesperado: {e}")
    
    # =========================================================================
    # CORE API
    # =========================================================================
    
    async def get_version(self) -> str:
        """Obtener versión de ZAP."""
        result = await self._request("core", "view", "version")
        return result.get("version", "unknown")
    
    async def get_hosts(self) -> List[str]:
        """Obtener lista de hosts conocidos."""
        result = await self._request("core", "view", "hosts")
        return result.get("hosts", [])
    
    async def get_sites(self) -> List[str]:
        """Obtener lista de sitios conocidos."""
        result = await self._request("core", "view", "sites")
        return result.get("sites", [])
    
    async def get_urls(self, base_url: Optional[str] = None) -> List[str]:
        """Obtener URLs conocidas, opcionalmente filtradas por baseurl."""
        params = {}
        if base_url:
            params["baseurl"] = base_url
        result = await self._request("core", "view", "urls", params)
        return result.get("urls", [])
    
    async def new_session(self, name: Optional[str] = None, overwrite: bool = True) -> Dict:
        """Crear nueva sesión de ZAP."""
        params = {}
        if name:
            params["name"] = name
            params["overwrite"] = str(overwrite).lower()
        return await self._request("core", "action", "newSession", params)
    
    async def access_url(self, url: str, follow_redirects: bool = True) -> Dict:
        """Acceder a una URL para que ZAP la analice."""
        params = {
            "url": url,
            "followRedirects": str(follow_redirects).lower(),
        }
        return await self._request("core", "action", "accessUrl", params)
    
    async def shutdown(self) -> Dict:
        """Apagar ZAP."""
        return await self._request("core", "action", "shutdown")
    
    # =========================================================================
    # SPIDER API
    # =========================================================================
    
    async def spider_scan(
        self,
        url: str,
        max_children: int = 10,
        recurse: bool = True,
        context_name: Optional[str] = None,
        subtree_only: bool = True,
    ) -> str:
        """
        Iniciar escaneo spider.
        
        Returns:
            ID del escaneo spider
        """
        params = {
            "url": url,
            "maxChildren": str(max_children),
            "recurse": str(recurse).lower(),
            "subtreeOnly": str(subtree_only).lower(),
        }
        if context_name:
            params["contextName"] = context_name
        
        result = await self._request("spider", "action", "scan", params)
        return result.get("scan", "")
    
    async def spider_status(self, scan_id: str) -> int:
        """Obtener progreso del spider (0-100)."""
        result = await self._request("spider", "view", "status", {"scanId": scan_id})
        return int(result.get("status", 0))
    
    async def spider_stop(self, scan_id: str) -> Dict:
        """Detener escaneo spider."""
        return await self._request("spider", "action", "stop", {"scanId": scan_id})
    
    async def spider_results(self, scan_id: str) -> List[str]:
        """Obtener URLs encontradas por el spider."""
        result = await self._request("spider", "view", "results", {"scanId": scan_id})
        return result.get("results", [])
    
    async def spider_full_results(self, scan_id: str) -> Dict:
        """Obtener resultados completos del spider."""
        return await self._request("spider", "view", "fullResults", {"scanId": scan_id})
    
    # =========================================================================
    # AJAX SPIDER API
    # =========================================================================
    
    async def ajax_spider_scan(
        self,
        url: str,
        in_scope: bool = True,
        context_name: Optional[str] = None,
        subtree_only: bool = True,
    ) -> Dict:
        """Iniciar escaneo Ajax Spider."""
        params = {
            "url": url,
            "inScope": str(in_scope).lower(),
            "subtreeOnly": str(subtree_only).lower(),
        }
        if context_name:
            params["contextName"] = context_name
        
        return await self._request("ajaxSpider", "action", "scan", params)
    
    async def ajax_spider_status(self) -> str:
        """Obtener estado del Ajax Spider (running/stopped)."""
        result = await self._request("ajaxSpider", "view", "status")
        return result.get("status", "stopped")
    
    async def ajax_spider_stop(self) -> Dict:
        """Detener Ajax Spider."""
        return await self._request("ajaxSpider", "action", "stop")
    
    async def ajax_spider_results(
        self,
        start: int = 0,
        count: int = 100,
    ) -> List[Dict]:
        """Obtener resultados del Ajax Spider."""
        result = await self._request(
            "ajaxSpider", "view", "results",
            {"start": str(start), "count": str(count)}
        )
        return result.get("results", [])
    
    async def ajax_spider_number_of_results(self) -> int:
        """Obtener número de resultados del Ajax Spider."""
        result = await self._request("ajaxSpider", "view", "numberOfResults")
        return int(result.get("numberOfResults", 0))
    
    # =========================================================================
    # ACTIVE SCAN API
    # =========================================================================
    
    async def active_scan(
        self,
        url: str,
        recurse: bool = True,
        in_scope_only: bool = True,
        scan_policy_name: Optional[str] = None,
        method: Optional[str] = None,
        post_data: Optional[str] = None,
        context_id: Optional[str] = None,
    ) -> str:
        """
        Iniciar escaneo activo.
        
        Returns:
            ID del escaneo activo
        """
        params = {
            "url": url,
            "recurse": str(recurse).lower(),
            "inScopeOnly": str(in_scope_only).lower(),
        }
        if scan_policy_name:
            params["scanPolicyName"] = scan_policy_name
        if method:
            params["method"] = method
        if post_data:
            params["postData"] = post_data
        if context_id:
            params["contextId"] = context_id
        
        result = await self._request("ascan", "action", "scan", params)
        return result.get("scan", "")
    
    async def active_scan_status(self, scan_id: str) -> int:
        """Obtener progreso del escaneo activo (0-100)."""
        result = await self._request("ascan", "view", "status", {"scanId": scan_id})
        return int(result.get("status", 0))
    
    async def active_scan_stop(self, scan_id: str) -> Dict:
        """Detener escaneo activo."""
        return await self._request("ascan", "action", "stop", {"scanId": scan_id})
    
    async def active_scan_pause(self, scan_id: str) -> Dict:
        """Pausar escaneo activo."""
        return await self._request("ascan", "action", "pause", {"scanId": scan_id})
    
    async def active_scan_resume(self, scan_id: str) -> Dict:
        """Reanudar escaneo activo pausado."""
        return await self._request("ascan", "action", "resume", {"scanId": scan_id})
    
    async def active_scan_scans(self) -> List[Dict]:
        """Obtener lista de todos los escaneos activos."""
        result = await self._request("ascan", "view", "scans")
        return result.get("scans", [])
    
    # =========================================================================
    # PASSIVE SCAN API
    # =========================================================================
    
    async def passive_scan_records_to_scan(self) -> int:
        """Obtener número de registros pendientes de escaneo pasivo."""
        result = await self._request("pscan", "view", "recordsToScan")
        return int(result.get("recordsToScan", 0))
    
    async def passive_scan_enable_all_scanners(self) -> Dict:
        """Habilitar todos los escáneres pasivos."""
        return await self._request("pscan", "action", "enableAllScanners")
    
    async def passive_scan_disable_all_scanners(self) -> Dict:
        """Deshabilitar todos los escáneres pasivos."""
        return await self._request("pscan", "action", "disableAllScanners")
    
    async def passive_scan_set_enabled(self, enabled: bool) -> Dict:
        """Habilitar o deshabilitar escaneo pasivo."""
        return await self._request(
            "pscan", "action", "setEnabled",
            {"enabled": str(enabled).lower()}
        )
    
    # =========================================================================
    # ALERTS API
    # =========================================================================
    
    async def get_alerts(
        self,
        base_url: Optional[str] = None,
        start: int = 0,
        count: int = 100,
        risk_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Obtener alertas encontradas.
        
        Args:
            base_url: Filtrar por URL base
            start: Índice de inicio
            count: Número de alertas a obtener
            risk_id: Filtrar por nivel de riesgo (0-3)
        """
        params = {
            "start": str(start),
            "count": str(count),
        }
        if base_url:
            params["baseurl"] = base_url
        if risk_id is not None:
            params["riskId"] = str(risk_id)
        
        result = await self._request("alert", "view", "alerts", params)
        return result.get("alerts", [])
    
    async def get_alerts_count(
        self,
        base_url: Optional[str] = None,
        risk_id: Optional[str] = None,
    ) -> int:
        """Obtener número total de alertas."""
        params = {}
        if base_url:
            params["baseurl"] = base_url
        if risk_id is not None:
            params["riskId"] = str(risk_id)
        
        result = await self._request("alert", "view", "numberOfAlerts", params)
        return int(result.get("numberOfAlerts", 0))
    
    async def get_alerts_summary(self, base_url: Optional[str] = None) -> Dict:
        """Obtener resumen de alertas por nivel de riesgo."""
        params = {}
        if base_url:
            params["baseurl"] = base_url
        
        return await self._request("alert", "view", "alertsSummary", params)
    
    async def delete_all_alerts(self) -> Dict:
        """Eliminar todas las alertas."""
        return await self._request("alert", "action", "deleteAllAlerts")
    
    # =========================================================================
    # CONTEXT API
    # =========================================================================
    
    async def create_context(self, name: str) -> str:
        """Crear nuevo contexto. Retorna ID del contexto."""
        result = await self._request("context", "action", "newContext", {"contextName": name})
        return result.get("contextId", "")
    
    async def include_in_context(self, context_name: str, regex: str) -> Dict:
        """Incluir regex en contexto."""
        return await self._request(
            "context", "action", "includeInContext",
            {"contextName": context_name, "regex": regex}
        )
    
    async def exclude_from_context(self, context_name: str, regex: str) -> Dict:
        """Excluir regex de contexto."""
        return await self._request(
            "context", "action", "excludeFromContext",
            {"contextName": context_name, "regex": regex}
        )
    
    async def get_context(self, context_name: str) -> Dict:
        """Obtener detalles de un contexto."""
        return await self._request("context", "view", "context", {"contextName": context_name})
    
    async def list_contexts(self) -> List[str]:
        """Listar nombres de contextos."""
        result = await self._request("context", "view", "contextList")
        return result.get("contextList", "").split(",") if result.get("contextList") else []
    
    async def remove_context(self, context_name: str) -> Dict:
        """Eliminar un contexto."""
        return await self._request("context", "action", "removeContext", {"contextName": context_name})
    
    # =========================================================================
    # OPENAPI API
    # =========================================================================
    
    async def import_openapi(
        self,
        url: Optional[str] = None,
        file: Optional[str] = None,
        context_id: Optional[str] = None,
        target: Optional[str] = None,
    ) -> Dict:
        """Importar definición OpenAPI."""
        params = {}
        if url:
            params["url"] = url
        if file:
            params["file"] = file
        if context_id:
            params["contextId"] = context_id
        if target:
            params["target"] = target
        
        return await self._request("openapi", "action", "importUrl" if url else "importFile", params)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def wait_for_spider(
        self,
        scan_id: str,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None,
    ) -> int:
        """
        Esperar a que termine el spider.
        
        Returns:
            Porcentaje final (100 si completó)
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await self.spider_status(scan_id)
            logger.debug(f"Spider status: {status}%")
            
            if status >= 100:
                return status
            
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Spider timeout after {timeout}s")
                return status
            
            await asyncio.sleep(poll_interval)
    
    async def wait_for_ajax_spider(
        self,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Esperar a que termine el Ajax Spider.
        
        Returns:
            Estado final
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await self.ajax_spider_status()
            logger.debug(f"Ajax Spider status: {status}")
            
            if status == "stopped":
                return status
            
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Ajax Spider timeout after {timeout}s")
                await self.ajax_spider_stop()
                return "timeout"
            
            await asyncio.sleep(poll_interval)
    
    async def wait_for_active_scan(
        self,
        scan_id: str,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
    ) -> int:
        """
        Esperar a que termine el escaneo activo.
        
        Returns:
            Porcentaje final (100 si completó)
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await self.active_scan_status(scan_id)
            logger.debug(f"Active scan status: {status}%")
            
            if status >= 100:
                return status
            
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Active scan timeout after {timeout}s")
                await self.active_scan_stop(scan_id)
                return status
            
            await asyncio.sleep(poll_interval)
    
    async def wait_for_passive_scan(
        self,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Esperar a que termine el escaneo pasivo.
        
        Returns:
            True si completó, False si timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            records = await self.passive_scan_records_to_scan()
            logger.debug(f"Passive scan records to scan: {records}")
            
            if records == 0:
                return True
            
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Passive scan timeout after {timeout}s")
                return False
            
            await asyncio.sleep(poll_interval)
    
    async def is_available(self) -> bool:
        """Verificar si ZAP está disponible."""
        try:
            await self.get_version()
            return True
        except Exception:
            return False
