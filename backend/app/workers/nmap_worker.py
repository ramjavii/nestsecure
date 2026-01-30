# =============================================================================
# NESTSECURE - Nmap Worker
# =============================================================================
"""
Worker de Celery para tareas de escaneo con Nmap.

Incluye:
- discovery_scan: Descubrimiento de hosts en una red
- port_scan: Escaneo de puertos y servicios en un asset
- quick_scan: Escaneo rápido de top 100 puertos
- full_scan: Escaneo completo de todos los puertos
"""

import logging
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Optional

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import SessionLocal
from app.models.asset import Asset, AssetStatus
from app.models.service import Service, ServiceProtocol, ServiceState

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Helper Functions
# =============================================================================
def get_sync_db() -> Session:
    """
    Obtiene una sesión síncrona de base de datos.
    Celery workers usan conexiones síncronas.
    """
    return SessionLocal()


def run_nmap(args: list[str], timeout: int | None = None) -> str:
    """
    Ejecuta Nmap con los argumentos dados.
    
    Args:
        args: Lista de argumentos para nmap
        timeout: Timeout en segundos (default: settings.NMAP_TIMEOUT)
    
    Returns:
        Salida XML de Nmap
    
    Raises:
        subprocess.TimeoutExpired: Si el escaneo excede el timeout
        subprocess.CalledProcessError: Si nmap falla
    """
    if timeout is None:
        timeout = settings.NMAP_TIMEOUT
    
    cmd = [settings.NMAP_PATH, "-oX", "-"] + args
    
    logger.info(f"Ejecutando Nmap: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    
    if result.returncode != 0 and "host seems down" not in result.stderr.lower():
        logger.error(f"Nmap stderr: {result.stderr}")
        raise subprocess.CalledProcessError(
            result.returncode,
            cmd,
            result.stdout,
            result.stderr,
        )
    
    return result.stdout


def parse_discovery_xml(xml_output: str) -> list[dict[str, Any]]:
    """
    Parsea la salida XML de un discovery scan (-sn).
    
    Args:
        xml_output: Salida XML de nmap
    
    Returns:
        Lista de hosts encontrados con IP, hostname, MAC
    """
    hosts = []
    
    try:
        root = ET.fromstring(xml_output)
    except ET.ParseError as e:
        logger.error(f"Error parseando XML: {e}")
        return hosts
    
    for host in root.findall(".//host"):
        status = host.find("status")
        if status is None or status.get("state") != "up":
            continue
        
        host_data: dict[str, Any] = {
            "ip_address": None,
            "hostname": None,
            "mac_address": None,
            "vendor": None,
        }
        
        # Direcciones
        for addr in host.findall("address"):
            addr_type = addr.get("addrtype")
            if addr_type == "ipv4" or addr_type == "ipv6":
                host_data["ip_address"] = addr.get("addr")
            elif addr_type == "mac":
                host_data["mac_address"] = addr.get("addr")
                host_data["vendor"] = addr.get("vendor")
        
        # Hostname
        hostnames = host.find("hostnames")
        if hostnames is not None:
            hostname_elem = hostnames.find("hostname")
            if hostname_elem is not None:
                host_data["hostname"] = hostname_elem.get("name")
        
        if host_data["ip_address"]:
            hosts.append(host_data)
    
    return hosts


def parse_port_scan_xml(xml_output: str) -> dict[str, Any]:
    """
    Parsea la salida XML de un port scan (-sV).
    
    Args:
        xml_output: Salida XML de nmap
    
    Returns:
        Dict con información del host y servicios detectados
    """
    result: dict[str, Any] = {
        "host_info": {
            "ip_address": None,
            "hostname": None,
            "mac_address": None,
            "os_match": None,
            "os_accuracy": 0,
        },
        "services": [],
    }
    
    try:
        root = ET.fromstring(xml_output)
    except ET.ParseError as e:
        logger.error(f"Error parseando XML: {e}")
        return result
    
    host = root.find(".//host")
    if host is None:
        return result
    
    # Información del host
    for addr in host.findall("address"):
        addr_type = addr.get("addrtype")
        if addr_type == "ipv4" or addr_type == "ipv6":
            result["host_info"]["ip_address"] = addr.get("addr")
        elif addr_type == "mac":
            result["host_info"]["mac_address"] = addr.get("addr")
    
    # Hostname
    hostnames = host.find("hostnames")
    if hostnames is not None:
        hostname_elem = hostnames.find("hostname")
        if hostname_elem is not None:
            result["host_info"]["hostname"] = hostname_elem.get("name")
    
    # OS Detection
    os_elem = host.find("os")
    if os_elem is not None:
        os_match = os_elem.find("osmatch")
        if os_match is not None:
            result["host_info"]["os_match"] = os_match.get("name")
            result["host_info"]["os_accuracy"] = int(os_match.get("accuracy", 0))
    
    # Puertos y servicios
    ports = host.find("ports")
    if ports is not None:
        for port in ports.findall("port"):
            port_id = port.get("portid")
            protocol = port.get("protocol", "tcp")
            
            state_elem = port.find("state")
            state = state_elem.get("state", "unknown") if state_elem is not None else "unknown"
            
            service_elem = port.find("service")
            service_data: dict[str, Any] = {
                "port": int(port_id) if port_id else 0,
                "protocol": protocol,
                "state": state,
                "service_name": None,
                "product": None,
                "version": None,
                "cpe": None,
                "banner": None,
                "ssl_enabled": False,
            }
            
            if service_elem is not None:
                service_data["service_name"] = service_elem.get("name")
                service_data["product"] = service_elem.get("product")
                service_data["version"] = service_elem.get("version")
                
                # Detectar SSL
                tunnel = service_elem.get("tunnel")
                if tunnel == "ssl":
                    service_data["ssl_enabled"] = True
                
                # CPE
                cpe_elem = service_elem.find("cpe")
                if cpe_elem is not None:
                    service_data["cpe"] = cpe_elem.text
            
            # Scripts (para banners, etc.)
            for script in port.findall("script"):
                script_id = script.get("id")
                if script_id == "banner":
                    service_data["banner"] = script.get("output", "")[:1000]  # Limitar banner
            
            if service_data["port"] > 0:
                result["services"].append(service_data)
    
    return result


# =============================================================================
# Celery Tasks
# =============================================================================
@shared_task(
    bind=True,
    name="app.workers.nmap_worker.discovery_scan",
    max_retries=3,
    default_retry_delay=60,
    rate_limit="5/m",
)
def discovery_scan(
    self,
    target: str,
    organization_id: str,
) -> dict[str, Any]:
    """
    Descubrimiento de hosts en una red.
    
    Ejecuta un ping scan (-sn) para encontrar hosts activos.
    
    Args:
        target: Target a escanear (ej: "192.168.1.0/24", "10.0.0.1-10")
        organization_id: ID de la organización
    
    Returns:
        dict con hosts encontrados y estadísticas
    """
    logger.info(f"Iniciando discovery scan: {target} para org {organization_id}")
    
    result = {
        "target": target,
        "organization_id": organization_id,
        "hosts_found": 0,
        "hosts_created": 0,
        "hosts_updated": 0,
        "hosts": [],
        "errors": [],
    }
    
    try:
        # Ejecutar Nmap discovery
        xml_output = run_nmap(["-sn", target])
        
        # Parsear resultados
        hosts = parse_discovery_xml(xml_output)
        result["hosts_found"] = len(hosts)
        
        # Guardar en base de datos
        db = get_sync_db()
        try:
            now = datetime.now(timezone.utc)
            
            for host_data in hosts:
                ip = host_data["ip_address"]
                if not ip:
                    continue
                
                # Buscar asset existente
                stmt = select(Asset).where(
                    Asset.organization_id == organization_id,
                    Asset.ip_address == ip,
                )
                existing = db.execute(stmt).scalar_one_or_none()
                
                if existing:
                    # Actualizar asset existente
                    existing.last_seen = now
                    existing.is_reachable = True
                    if host_data.get("hostname") and not existing.hostname:
                        existing.hostname = host_data["hostname"]
                    if host_data.get("mac_address") and not existing.mac_address:
                        existing.mac_address = host_data["mac_address"]
                    result["hosts_updated"] += 1
                else:
                    # Crear nuevo asset
                    asset = Asset(
                        organization_id=organization_id,
                        ip_address=ip,
                        hostname=host_data.get("hostname"),
                        mac_address=host_data.get("mac_address"),
                        status=AssetStatus.ACTIVE.value,
                        is_reachable=True,
                        first_seen=now,
                        last_seen=now,
                        risk_score=0.0,
                        vuln_critical_count=0,
                        vuln_high_count=0,
                        vuln_medium_count=0,
                        vuln_low_count=0,
                    )
                    db.add(asset)
                    result["hosts_created"] += 1
                
                result["hosts"].append(host_data)
            
            db.commit()
            
        finally:
            db.close()
        
        logger.info(
            f"Discovery completado: {result['hosts_found']} encontrados, "
            f"{result['hosts_created']} creados, {result['hosts_updated']} actualizados"
        )
        
    except subprocess.TimeoutExpired:
        result["errors"].append(f"Timeout escaneando {target}")
        logger.error(f"Timeout en discovery scan: {target}")
        raise self.retry(exc=Exception("Nmap timeout"))
    
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Error en Nmap: {e.stderr}")
        logger.error(f"Error en Nmap: {e}")
        raise
    
    except Exception as e:
        result["errors"].append(str(e))
        logger.exception(f"Error en discovery scan: {e}")
        raise
    
    return result


@shared_task(
    bind=True,
    name="app.workers.nmap_worker.port_scan",
    max_retries=2,
    default_retry_delay=120,
    rate_limit="3/m",
)
def port_scan(
    self,
    asset_id: str,
    scan_type: str = "quick",
) -> dict[str, Any]:
    """
    Escaneo de puertos y servicios en un asset.
    
    Args:
        asset_id: ID del asset a escanear
        scan_type: Tipo de escaneo (quick, full, top1000)
    
    Returns:
        dict con servicios encontrados y estadísticas
    """
    logger.info(f"Iniciando port scan: {asset_id}, tipo: {scan_type}")
    
    result = {
        "asset_id": asset_id,
        "scan_type": scan_type,
        "services_found": 0,
        "services_created": 0,
        "services_updated": 0,
        "services": [],
        "os_detected": None,
        "errors": [],
    }
    
    db = get_sync_db()
    try:
        # Obtener asset
        asset = db.execute(
            select(Asset).where(Asset.id == asset_id)
        ).scalar_one_or_none()
        
        if not asset:
            result["errors"].append(f"Asset {asset_id} no encontrado")
            return result
        
        ip_address = asset.ip_address
        
        # Configurar argumentos según tipo de escaneo
        nmap_args = ["-sV", "-sC"]  # Service detection + default scripts
        
        if scan_type == "quick":
            nmap_args.append("-F")  # Top 100 ports
        elif scan_type == "full":
            nmap_args.extend(["-p-", "--max-retries", "2"])  # All ports
        elif scan_type == "top1000":
            nmap_args.append("--top-ports=1000")
        
        nmap_args.append(ip_address)
        
        # Ejecutar Nmap
        xml_output = run_nmap(nmap_args)
        
        # Parsear resultados
        scan_data = parse_port_scan_xml(xml_output)
        
        # Actualizar asset con OS detection
        if scan_data["host_info"]["os_match"]:
            asset.operating_system = scan_data["host_info"]["os_match"]
            result["os_detected"] = scan_data["host_info"]["os_match"]
        
        if scan_data["host_info"]["hostname"] and not asset.hostname:
            asset.hostname = scan_data["host_info"]["hostname"]
        
        now = datetime.now(timezone.utc)
        asset.last_scanned = now
        asset.last_seen = now
        asset.is_reachable = True
        
        # Procesar servicios
        for svc_data in scan_data["services"]:
            port = svc_data["port"]
            protocol = svc_data["protocol"]
            
            # Buscar servicio existente
            existing_svc = db.execute(
                select(Service).where(
                    Service.asset_id == asset_id,
                    Service.port == port,
                    Service.protocol == protocol,
                )
            ).scalar_one_or_none()
            
            # Mapear estado
            state_map = {
                "open": ServiceState.OPEN.value,
                "closed": ServiceState.CLOSED.value,
                "filtered": ServiceState.FILTERED.value,
            }
            state = state_map.get(svc_data["state"], ServiceState.UNKNOWN.value)
            
            if existing_svc:
                # Actualizar servicio existente
                existing_svc.state = state
                existing_svc.service_name = svc_data["service_name"]
                existing_svc.product = svc_data["product"]
                existing_svc.version = svc_data["version"]
                existing_svc.cpe = svc_data["cpe"]
                existing_svc.banner = svc_data["banner"]
                existing_svc.ssl_enabled = svc_data["ssl_enabled"]
                existing_svc.detection_method = "nmap"
                result["services_updated"] += 1
            else:
                # Crear nuevo servicio
                service = Service(
                    asset_id=asset_id,
                    port=port,
                    protocol=protocol,
                    state=state,
                    service_name=svc_data["service_name"],
                    product=svc_data["product"],
                    version=svc_data["version"],
                    cpe=svc_data["cpe"],
                    banner=svc_data["banner"],
                    ssl_enabled=svc_data["ssl_enabled"],
                    detection_method="nmap",
                    confidence=90,
                )
                db.add(service)
                result["services_created"] += 1
            
            result["services"].append(svc_data)
        
        result["services_found"] = len(scan_data["services"])
        
        db.commit()
        
        logger.info(
            f"Port scan completado para {ip_address}: "
            f"{result['services_found']} servicios, "
            f"{result['services_created']} creados, {result['services_updated']} actualizados"
        )
        
    except subprocess.TimeoutExpired:
        result["errors"].append(f"Timeout escaneando asset {asset_id}")
        logger.error(f"Timeout en port scan: {asset_id}")
        raise self.retry(exc=Exception("Nmap timeout"))
    
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Error en Nmap: {e.stderr}")
        logger.error(f"Error en Nmap: {e}")
        raise
    
    except Exception as e:
        result["errors"].append(str(e))
        logger.exception(f"Error en port scan: {e}")
        raise
    
    finally:
        db.close()
    
    return result


@shared_task(
    bind=True,
    name="app.workers.nmap_worker.scan_network",
    max_retries=1,
)
def scan_network(
    self,
    target: str,
    organization_id: str,
    scan_type: str = "quick",
) -> dict[str, Any]:
    """
    Escaneo completo de red: discovery + port scan de cada host.
    
    Esta tarea es un orquestador que:
    1. Ejecuta discovery_scan para encontrar hosts
    2. Crea tareas port_scan para cada host encontrado
    
    Args:
        target: Target de red (ej: "192.168.1.0/24")
        organization_id: ID de la organización
        scan_type: Tipo de escaneo de puertos
    
    Returns:
        dict con resultados del discovery y IDs de tareas de port scan
    """
    logger.info(f"Iniciando scan completo de red: {target}")
    
    result = {
        "target": target,
        "organization_id": organization_id,
        "discovery_result": None,
        "port_scan_tasks": [],
    }
    
    try:
        # Paso 1: Discovery
        discovery_result = discovery_scan(target, organization_id)
        result["discovery_result"] = discovery_result
        
        # Paso 2: Port scan de cada host encontrado
        db = get_sync_db()
        try:
            for host in discovery_result.get("hosts", []):
                ip = host.get("ip_address")
                if not ip:
                    continue
                
                # Obtener el asset_id
                asset = db.execute(
                    select(Asset).where(
                        Asset.organization_id == organization_id,
                        Asset.ip_address == ip,
                    )
                ).scalar_one_or_none()
                
                if asset:
                    # Encolar port scan
                    task = port_scan.delay(asset.id, scan_type)
                    result["port_scan_tasks"].append({
                        "asset_id": asset.id,
                        "ip_address": ip,
                        "task_id": task.id,
                    })
        finally:
            db.close()
        
        logger.info(
            f"Scan de red completado: {len(result['port_scan_tasks'])} port scans encolados"
        )
        
    except Exception as e:
        logger.exception(f"Error en scan_network: {e}")
        raise
    
    return result
