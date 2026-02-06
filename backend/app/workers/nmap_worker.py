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
- execute_scan_task: Tarea principal que orquesta scans y actualiza DB
"""

import logging
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import SessionLocal
from app.models.asset import Asset, AssetStatus
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.service import Service, ServiceProtocol, ServiceState
from app.models.vulnerability import Vulnerability, VulnerabilitySeverity
from app.utils.network_utils import is_private_ip, is_private_network

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


def update_scan_status_in_db(
    scan_id: str,
    status: str,
    results: dict = None,
    error_message: str = None,
) -> None:
    """
    Actualiza el status de un scan en la base de datos.
    
    Además de actualizar el status, guarda los assets y servicios
    encontrados en las tablas correspondientes.
    
    Args:
        scan_id: ID del scan a actualizar
        status: Nuevo status ('completed', 'failed', 'running', etc.)
        results: Resultados del scan (opcional)
        error_message: Mensaje de error si falló (opcional)
    """
    db = get_sync_db()
    try:
        scan = db.execute(
            select(Scan).where(Scan.id == scan_id)
        ).scalar_one_or_none()
        
        if scan:
            scan.status = status
            now = datetime.now(timezone.utc)
            
            if status == "completed":
                scan.completed_at = now
                # Calcular duración si hay started_at
                if scan.started_at:
                    duration = (now - scan.started_at).total_seconds()
                    scan.duration_seconds = int(duration)
            
            if status == "running" and not scan.started_at:
                scan.started_at = now
            
            if results:
                scan.results = results
                
                # Actualizar contadores del scan
                services_found = results.get("services_found", 0) or len(results.get("services", []))
                hosts_found = results.get("hosts_found", 0)
                vulns_found = results.get("vulnerabilities_found", 0) or len(results.get("vulnerabilities", []))
                
                if services_found > 0:
                    scan.total_services_found = services_found
                if hosts_found > 0:
                    scan.total_hosts_up = hosts_found
                    scan.total_hosts_scanned = hosts_found
                if vulns_found > 0:
                    scan.total_vulnerabilities = vulns_found
                
                # Guardar duración del escaneo si está en los resultados
                nmap_duration = results.get("duration_seconds")
                if nmap_duration and status == "completed":
                    scan.duration_seconds = int(nmap_duration)
                
                # Guardar servicios en la BD si hay
                services = results.get("services", [])
                if services and scan.organization_id:
                    _save_services_from_results(db, scan, services, now)
                
                # Guardar vulnerabilidades en la BD si hay
                vulnerabilities = results.get("vulnerabilities", [])
                if vulnerabilities and scan.organization_id:
                    _save_vulnerabilities_from_results(db, scan, vulnerabilities, now)
            
            if error_message:
                scan.error_message = error_message
            
            db.commit()
            logger.info(f"Scan {scan_id} status updated to '{status}'")
        else:
            logger.warning(f"Scan {scan_id} not found in DB")
    except Exception as e:
        logger.error(f"Error updating scan {scan_id} status: {e}")
        db.rollback()
    finally:
        db.close()


def _save_services_from_results(db, scan, services: list, now: datetime) -> None:
    """
    Guarda los servicios encontrados en la BD.
    
    Crea o actualiza Assets y Services basándose en los resultados del scan.
    """
    for svc in services:
        try:
            port = svc.get("port")
            if not port:
                continue
                
            # Obtener o crear asset basado en el target del scan
            target_ip = scan.targets[0] if scan.targets else None
            if not target_ip:
                continue
            
            # Buscar asset existente
            asset = db.execute(
                select(Asset).where(
                    Asset.organization_id == scan.organization_id,
                    Asset.ip_address == target_ip,
                )
            ).scalar_one_or_none()
            
            if not asset:
                # Crear nuevo asset
                asset = Asset(
                    organization_id=scan.organization_id,
                    ip_address=target_ip,
                    hostname=svc.get("hostname"),
                    status=AssetStatus.ACTIVE.value,
                    is_reachable=True,
                    first_seen=now,
                    last_seen=now,
                    last_scanned=now,
                    risk_score=0.0,
                )
                db.add(asset)
                db.flush()  # Para obtener el ID
            else:
                asset.last_seen = now
                asset.last_scanned = now
                asset.is_reachable = True
            
            # Buscar servicio existente
            existing_svc = db.execute(
                select(Service).where(
                    Service.asset_id == asset.id,
                    Service.port == port,
                    Service.protocol == svc.get("protocol", "tcp"),
                )
            ).scalar_one_or_none()
            
            if not existing_svc:
                # Crear nuevo servicio
                new_service = Service(
                    asset_id=asset.id,
                    port=port,
                    protocol=svc.get("protocol", "tcp"),
                    state=ServiceState.OPEN.value,
                    service_name=svc.get("service_name") or svc.get("name"),
                    product=svc.get("product"),
                    version=svc.get("version"),
                    cpe=svc.get("cpe"),
                    banner=svc.get("banner"),
                    detection_method="nmap",
                    confidence=90,
                )
                db.add(new_service)
            else:
                # Actualizar servicio existente
                existing_svc.state = ServiceState.OPEN.value
                existing_svc.service_name = svc.get("service_name") or svc.get("name") or existing_svc.service_name
                existing_svc.product = svc.get("product") or existing_svc.product
                existing_svc.version = svc.get("version") or existing_svc.version
                
        except Exception as e:
            logger.warning(f"Error saving service {svc}: {e}")
            continue


def parse_vulners_output(script_output: str) -> list[dict]:
    """
    Parsea la salida del script vulners de nmap para extraer CVEs.
    
    La salida de vulners tiene formato:
      CVE-2023-38408	9.8	https://vulners.com/cve/CVE-2023-38408
      CVE-2020-15778	7.8	https://vulners.com/cve/CVE-2020-15778
    
    Args:
        script_output: Output del script vulners
        
    Returns:
        Lista de dicts con cve_id, cvss_score, url
    """
    import re
    
    vulnerabilities = []
    
    # Patrón para CVE con CVSS score
    cve_pattern = re.compile(
        r'(CVE-\d{4}-\d+)\s+(\d+\.?\d*)',
        re.IGNORECASE
    )
    
    for match in cve_pattern.finditer(script_output):
        cve_id = match.group(1).upper()
        try:
            cvss_score = float(match.group(2))
        except ValueError:
            cvss_score = 0.0
        
        # Determinar severidad basada en CVSS
        if cvss_score >= 9.0:
            severity = VulnerabilitySeverity.CRITICAL.value
        elif cvss_score >= 7.0:
            severity = VulnerabilitySeverity.HIGH.value
        elif cvss_score >= 4.0:
            severity = VulnerabilitySeverity.MEDIUM.value
        elif cvss_score > 0:
            severity = VulnerabilitySeverity.LOW.value
        else:
            severity = VulnerabilitySeverity.INFO.value
        
        vulnerabilities.append({
            "cve_id": cve_id,
            "cvss_score": cvss_score,
            "severity": severity,
            "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
        })
    
    return vulnerabilities


def _save_vulnerabilities_from_results(
    db, 
    scan, 
    vulnerabilities: list, 
    now: datetime
) -> int:
    """
    Guarda las vulnerabilidades encontradas en la BD.
    
    Args:
        db: Sesión de BD
        scan: Objeto Scan
        vulnerabilities: Lista de vulnerabilidades a guardar
        now: Timestamp actual
        
    Returns:
        Número de vulnerabilidades guardadas
    """
    saved_count = 0
    
    for vuln in vulnerabilities:
        try:
            # Obtener asset asociado
            target_ip = scan.targets[0] if scan.targets else None
            if not target_ip:
                continue
            
            asset = db.execute(
                select(Asset).where(
                    Asset.organization_id == scan.organization_id,
                    Asset.ip_address == target_ip,
                )
            ).scalar_one_or_none()
            
            if not asset:
                logger.warning(f"No asset found for {target_ip}")
                continue
            
            cve_id = vuln.get("cve_id")
            port = vuln.get("port")
            service_name = vuln.get("service", "Unknown Service")
            
            # Buscar service_id si tenemos puerto
            service_id = None
            if port:
                service = db.execute(
                    select(Service).where(
                        Service.asset_id == asset.id,
                        Service.port == port,
                    )
                ).scalar_one_or_none()
                if service:
                    service_id = service.id
            
            # Verificar si ya existe esta vulnerabilidad para este scan/asset
            existing = db.execute(
                select(Vulnerability).where(
                    Vulnerability.scan_id == scan.id,
                    Vulnerability.asset_id == asset.id,
                    Vulnerability.cve_id == cve_id,
                )
            ).scalar_one_or_none()
            
            if existing:
                continue
            
            # Crear nueva vulnerabilidad
            new_vuln = Vulnerability(
                organization_id=scan.organization_id,
                asset_id=asset.id,
                service_id=service_id,
                scan_id=scan.id,
                cve_id=cve_id,
                name=f"{cve_id} - {service_name}",
                description=vuln.get("description", f"Vulnerabilidad {cve_id} detectada por nmap vulners script"),
                severity=vuln.get("severity", VulnerabilitySeverity.MEDIUM.value),
                cvss_score=vuln.get("cvss_score"),
                status="open",
                host=str(asset.ip_address),
                port=port,
                references=[vuln.get("url")] if vuln.get("url") else [],
            )
            db.add(new_vuln)
            saved_count += 1
            
        except Exception as e:
            logger.warning(f"Error saving vulnerability {vuln}: {e}")
            continue
    
    if saved_count > 0:
        logger.info(f"Saved {saved_count} vulnerabilities for scan {scan.id}")
    
    return saved_count


def validate_target_security(target: str) -> bool:
    """
    Valida que un target sea seguro para escanear (solo redes privadas).
    
    SEGURIDAD: Esta es una segunda capa de validación después del API.
    Previene escaneos a IPs públicas incluso si el API fue bypaseado.
    
    Args:
        target: IP o CIDR a validar
    
    Returns:
        True si el target es seguro (red privada)
    
    Logs:
        WARNING si se detecta intento de escaneo a IP pública
    """
    target = target.strip()
    
    # Si es CIDR
    if '/' in target:
        if not is_private_network(target):
            logger.warning(
                f"SECURITY: Blocked scan to public network: {target}"
            )
            return False
        return True
    
    # Si es IP individual
    if not is_private_ip(target):
        logger.warning(
            f"SECURITY: Blocked scan to public IP: {target}"
        )
        return False
    
    return True


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


def parse_nmap_duration(xml_output: str) -> Optional[float]:
    """
    Extrae la duración del escaneo del XML de nmap.
    
    El XML contiene: <finished time="..." timestr="..." elapsed="123.45"/>
    
    Args:
        xml_output: Salida XML de nmap
    
    Returns:
        Duración en segundos o None si no se puede parsear
    """
    try:
        root = ET.fromstring(xml_output)
        finished = root.find(".//finished")
        if finished is not None:
            elapsed = finished.get("elapsed")
            if elapsed:
                return float(elapsed)
    except (ET.ParseError, ValueError) as e:
        logger.warning(f"Could not parse nmap duration: {e}")
    return None


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
            
            # Scripts (para banners, vulners, etc.)
            service_data["scripts"] = []
            for script in port.findall("script"):
                script_id = script.get("id")
                script_output = script.get("output", "")
                
                if script_id == "banner":
                    service_data["banner"] = script_output[:1000]  # Limitar banner
                
                # Guardar todos los scripts para análisis de vulnerabilidades
                service_data["scripts"].append({
                    "id": script_id,
                    "output": script_output[:2000],  # Limitar output
                })
            
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
    scan_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Descubrimiento de hosts en una red.
    
    Ejecuta un ping scan (-sn) para encontrar hosts activos.
    SEGURIDAD: Solo permite escaneos a redes privadas (RFC 1918).
    
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
    
    # SEGURIDAD: Validar que el target sea una red privada
    # Esto es una segunda capa de protección después del API
    for single_target in target.split(","):
        if not validate_target_security(single_target.strip()):
            error_msg = f"Security: Target '{single_target}' is not a private network"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            if scan_id:
                update_scan_status_in_db(scan_id, ScanStatus.FAILED.value, error_message=error_msg)
            return result
    
    try:
        # Ejecutar Nmap discovery
        xml_output = run_nmap(["-sn", target])
        
        # Parsear resultados
        hosts = parse_discovery_xml(xml_output)
        result["hosts_found"] = len(hosts)
        
        # Parsear duración del escaneo
        duration = parse_nmap_duration(xml_output)
        if duration:
            result["duration_seconds"] = duration
        
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
        
        # Actualizar status del scan en DB
        if scan_id:
            update_scan_status_in_db(scan_id, "completed", results=result)
        
    except subprocess.TimeoutExpired:
        result["errors"].append(f"Timeout escaneando {target}")
        logger.error(f"Timeout en discovery scan: {target}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=f"Timeout escaneando {target}")
        raise self.retry(exc=Exception("Nmap timeout"))
    
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Error en Nmap: {e.stderr}")
        logger.error(f"Error en Nmap: {e}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=str(e))
        raise
    
    except Exception as e:
        result["errors"].append(str(e))
        logger.exception(f"Error en discovery scan: {e}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=str(e))
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


# =============================================================================
# Execute Scan Task - Tarea Principal con Actualización de DB
# =============================================================================
@shared_task(
    bind=True,
    name="app.workers.nmap_worker.execute_scan_task",
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=3300,  # 55 minutos
    time_limit=3600,  # 60 minutos hard limit
)
def execute_scan_task(
    self,
    scan_id: str,
    scan_type: str,
    targets: list[str],
    organization_id: str,
    port_range: Optional[str] = None,
    engine_config: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Tarea principal de escaneo que actualiza el estado en DB.
    
    Esta tarea:
    1. Marca el scan como RUNNING
    2. Ejecuta el escaneo según el tipo
    3. Actualiza progreso durante la ejecución
    4. Marca como COMPLETED o FAILED al terminar
    
    Args:
        scan_id: ID del scan en base de datos
        scan_type: Tipo de escaneo (discovery, port_scan, full, etc.)
        targets: Lista de IPs/CIDRs a escanear
        organization_id: ID de la organización
        port_range: Rango de puertos opcional
        engine_config: Configuración adicional del engine
    
    Returns:
        dict con resultados del escaneo
    """
    logger.info(f"Iniciando execute_scan_task: scan_id={scan_id}, type={scan_type}")
    
    db = get_sync_db()
    result: dict[str, Any] = {
        "scan_id": scan_id,
        "scan_type": scan_type,
        "targets": targets,
        "hosts_found": 0,
        "hosts_scanned": 0,
        "services_found": 0,
        "vulnerabilities_found": 0,
        "errors": [],
        "success": False,
    }
    
    try:
        # Obtener scan de la base de datos
        scan = db.execute(
            select(Scan).where(Scan.id == scan_id)
        ).scalar_one_or_none()
        
        if not scan:
            logger.error(f"Scan {scan_id} no encontrado")
            result["errors"].append(f"Scan {scan_id} no encontrado")
            return result
        
        # Verificar que no está cancelado
        if scan.status == ScanStatus.CANCELLED.value:
            logger.info(f"Scan {scan_id} fue cancelado, abortando")
            result["errors"].append("Scan cancelado")
            return result
        
        # =====================================================================
        # FASE 1: Marcar como RUNNING
        # =====================================================================
        scan.start()
        scan.add_log(f"Iniciando escaneo tipo '{scan_type}'", "info")
        scan.update_progress(5, "Iniciando")
        db.commit()
        
        total_targets = len(targets)
        processed_targets = 0
        
        # =====================================================================
        # FASE 2: Ejecutar escaneo según tipo
        # =====================================================================
        if scan_type == ScanType.DISCOVERY.value:
            # Discovery scan - encontrar hosts activos
            scan.update_progress(10, "Descubriendo hosts")
            scan.add_log(f"Escaneando {total_targets} targets", "info")
            db.commit()
            
            all_hosts = []
            for i, target in enumerate(targets):
                try:
                    # Verificar si fue cancelado
                    db.refresh(scan)
                    if scan.status == ScanStatus.CANCELLED.value:
                        logger.info(f"Scan {scan_id} cancelado durante ejecución")
                        result["errors"].append("Scan cancelado durante ejecución")
                        return result
                    
                    scan.update_progress(
                        10 + int((i / total_targets) * 80),
                        f"Escaneando {target}"
                    )
                    db.commit()
                    
                    # Ejecutar nmap discovery
                    xml_output = run_nmap(["-sn", target])
                    hosts = parse_discovery_xml(xml_output)
                    
                    # Guardar hosts encontrados como assets
                    now = datetime.now(timezone.utc)
                    for host_data in hosts:
                        ip = host_data.get("ip_address")
                        if not ip:
                            continue
                        
                        # Buscar asset existente
                        existing = db.execute(
                            select(Asset).where(
                                Asset.organization_id == organization_id,
                                Asset.ip_address == ip,
                            )
                        ).scalar_one_or_none()
                        
                        if existing:
                            existing.last_seen = now
                            existing.last_scanned = now
                            existing.is_reachable = True
                            if host_data.get("hostname") and not existing.hostname:
                                existing.hostname = host_data["hostname"]
                        else:
                            new_asset = Asset(
                                organization_id=organization_id,
                                ip_address=ip,
                                hostname=host_data.get("hostname"),
                                mac_address=host_data.get("mac_address"),
                                status=AssetStatus.ACTIVE.value,
                                is_reachable=True,
                                first_seen=now,
                                last_seen=now,
                                last_scanned=now,
                                risk_score=0.0,
                            )
                            db.add(new_asset)
                            result["hosts_found"] += 1
                        
                        all_hosts.append(host_data)
                    
                    db.commit()
                    processed_targets += 1
                    
                except subprocess.TimeoutExpired:
                    error_msg = f"Timeout escaneando {target}"
                    result["errors"].append(error_msg)
                    scan.add_log(error_msg, "warning")
                    db.commit()
                    
                except subprocess.CalledProcessError as e:
                    error_msg = f"Error Nmap en {target}: {e.stderr}"
                    result["errors"].append(error_msg)
                    scan.add_log(error_msg, "error")
                    db.commit()
            
            result["hosts_scanned"] = len(all_hosts)
            result["hosts"] = all_hosts  # Guardar lista de hosts para el endpoint
            scan.total_hosts_scanned = total_targets
            scan.total_hosts_up = len(all_hosts)
            
        elif scan_type in [ScanType.PORT_SCAN.value, ScanType.SERVICE_SCAN.value]:
            # Port scan - escanear puertos en targets específicos
            scan.update_progress(10, "Escaneando puertos")
            scan.add_log(f"Escaneando puertos en {total_targets} targets", "info")
            db.commit()
            
            all_services = []
            for i, target in enumerate(targets):
                try:
                    db.refresh(scan)
                    if scan.status == ScanStatus.CANCELLED.value:
                        result["errors"].append("Scan cancelado durante ejecución")
                        return result
                    
                    scan.update_progress(
                        10 + int((i / total_targets) * 80),
                        f"Escaneando {target}"
                    )
                    db.commit()
                    
                    # Preparar argumentos de nmap
                    nmap_args = ["-sV", "-sC"]
                    if port_range:
                        nmap_args.extend(["-p", port_range])
                    else:
                        nmap_args.append("-F")  # Top 100 ports
                    nmap_args.append(target)
                    
                    xml_output = run_nmap(nmap_args)
                    scan_data = parse_port_scan_xml(xml_output)
                    
                    # Buscar o crear asset
                    ip = scan_data["host_info"].get("ip_address") or target
                    asset = db.execute(
                        select(Asset).where(
                            Asset.organization_id == organization_id,
                            Asset.ip_address == ip,
                        )
                    ).scalar_one_or_none()
                    
                    if not asset:
                        asset = Asset(
                            organization_id=organization_id,
                            ip_address=ip,
                            hostname=scan_data["host_info"].get("hostname"),
                            status=AssetStatus.ACTIVE.value,
                            is_reachable=True,
                            first_seen=datetime.now(timezone.utc),
                            last_seen=datetime.now(timezone.utc),
                        )
                        db.add(asset)
                        db.flush()
                    
                    # Actualizar asset con OS detection
                    if scan_data["host_info"].get("os_match"):
                        asset.operating_system = scan_data["host_info"]["os_match"]
                    asset.last_scanned = datetime.now(timezone.utc)
                    asset.last_seen = datetime.now(timezone.utc)
                    
                    # Guardar servicios
                    for svc_data in scan_data["services"]:
                        port = svc_data["port"]
                        protocol = svc_data["protocol"]
                        
                        existing_svc = db.execute(
                            select(Service).where(
                                Service.asset_id == asset.id,
                                Service.port == port,
                                Service.protocol == protocol,
                            )
                        ).scalar_one_or_none()
                        
                        state_map = {
                            "open": ServiceState.OPEN.value,
                            "closed": ServiceState.CLOSED.value,
                            "filtered": ServiceState.FILTERED.value,
                        }
                        state = state_map.get(svc_data["state"], ServiceState.UNKNOWN.value)
                        
                        if existing_svc:
                            existing_svc.state = state
                            existing_svc.service_name = svc_data.get("service_name")
                            existing_svc.product = svc_data.get("product")
                            existing_svc.version = svc_data.get("version")
                        else:
                            new_service = Service(
                                asset_id=asset.id,
                                port=port,
                                protocol=protocol,
                                state=state,
                                service_name=svc_data.get("service_name"),
                                product=svc_data.get("product"),
                                version=svc_data.get("version"),
                                detection_method="nmap",
                            )
                            db.add(new_service)
                        
                        all_services.append(svc_data)
                    
                    db.commit()
                    processed_targets += 1
                    result["hosts_scanned"] += 1
                    
                except subprocess.TimeoutExpired:
                    error_msg = f"Timeout escaneando {target}"
                    result["errors"].append(error_msg)
                    scan.add_log(error_msg, "warning")
                    db.commit()
                    
                except Exception as e:
                    error_msg = f"Error en {target}: {str(e)}"
                    result["errors"].append(error_msg)
                    scan.add_log(error_msg, "error")
                    db.commit()
            
            result["services_found"] = len(all_services)
            scan.total_services_found = len(all_services)
            scan.total_hosts_scanned = processed_targets
            
        elif scan_type == ScanType.FULL.value:
            # Full scan - discovery + port scan completo
            scan.update_progress(5, "Fase 1: Discovery")
            scan.add_log("Iniciando escaneo completo (discovery + ports)", "info")
            db.commit()
            
            # Fase 1: Discovery
            discovered_hosts = []
            for i, target in enumerate(targets):
                try:
                    db.refresh(scan)
                    if scan.status == ScanStatus.CANCELLED.value:
                        return result
                    
                    scan.update_progress(5 + int((i / total_targets) * 30), f"Discovery: {target}")
                    db.commit()
                    
                    xml_output = run_nmap(["-sn", target])
                    hosts = parse_discovery_xml(xml_output)
                    
                    for host_data in hosts:
                        ip = host_data.get("ip_address")
                        if ip:
                            discovered_hosts.append(ip)
                            
                except Exception as e:
                    result["errors"].append(f"Discovery error {target}: {str(e)}")
            
            result["hosts_found"] = len(discovered_hosts)
            scan.total_hosts_up = len(discovered_hosts)
            scan.add_log(f"Discovery completado: {len(discovered_hosts)} hosts", "info")
            db.commit()
            
            # Fase 2: Port scan de cada host descubierto
            scan.update_progress(40, "Fase 2: Port Scan")
            db.commit()
            
            total_discovered = len(discovered_hosts)
            all_services = []
            
            for i, ip in enumerate(discovered_hosts):
                try:
                    db.refresh(scan)
                    if scan.status == ScanStatus.CANCELLED.value:
                        return result
                    
                    scan.update_progress(
                        40 + int((i / max(total_discovered, 1)) * 55),
                        f"Port scan: {ip}"
                    )
                    db.commit()
                    
                    nmap_args = ["-sV", "-sC"]
                    if port_range:
                        nmap_args.extend(["-p", port_range])
                    else:
                        nmap_args.append("--top-ports=1000")
                    nmap_args.append(ip)
                    
                    xml_output = run_nmap(nmap_args, timeout=600)  # 10 min por host
                    scan_data = parse_port_scan_xml(xml_output)
                    
                    # Guardar asset
                    asset = db.execute(
                        select(Asset).where(
                            Asset.organization_id == organization_id,
                            Asset.ip_address == ip,
                        )
                    ).scalar_one_or_none()
                    
                    if not asset:
                        asset = Asset(
                            organization_id=organization_id,
                            ip_address=ip,
                            status=AssetStatus.ACTIVE.value,
                            is_reachable=True,
                            first_seen=datetime.now(timezone.utc),
                            last_seen=datetime.now(timezone.utc),
                        )
                        db.add(asset)
                        db.flush()
                    
                    if scan_data["host_info"].get("os_match"):
                        asset.operating_system = scan_data["host_info"]["os_match"]
                    if scan_data["host_info"].get("hostname"):
                        asset.hostname = scan_data["host_info"]["hostname"]
                    asset.last_scanned = datetime.now(timezone.utc)
                    
                    # Guardar servicios
                    for svc_data in scan_data["services"]:
                        existing_svc = db.execute(
                            select(Service).where(
                                Service.asset_id == asset.id,
                                Service.port == svc_data["port"],
                                Service.protocol == svc_data["protocol"],
                            )
                        ).scalar_one_or_none()
                        
                        if not existing_svc:
                            new_service = Service(
                                asset_id=asset.id,
                                port=svc_data["port"],
                                protocol=svc_data["protocol"],
                                state=svc_data.get("state", "open"),
                                service_name=svc_data.get("service_name"),
                                product=svc_data.get("product"),
                                version=svc_data.get("version"),
                                detection_method="nmap",
                            )
                            db.add(new_service)
                        
                        all_services.append(svc_data)
                    
                    db.commit()
                    result["hosts_scanned"] += 1
                    
                except SoftTimeLimitExceeded:
                    scan.add_log(f"Soft time limit alcanzado en {ip}", "warning")
                    db.commit()
                    break
                    
                except Exception as e:
                    result["errors"].append(f"Port scan error {ip}: {str(e)}")
            
            result["services_found"] = len(all_services)
            scan.total_services_found = len(all_services)
            scan.total_hosts_scanned = result["hosts_scanned"]
        
        # =====================================================================
        # FASE 3: Marcar como completado
        # =====================================================================
        db.refresh(scan)
        if scan.status != ScanStatus.CANCELLED.value:
            scan.complete()
            scan.add_log(
                f"Escaneo completado: {result['hosts_scanned']} hosts, "
                f"{result['services_found']} servicios",
                "info"
            )
            result["success"] = True
        
        db.commit()
        
        logger.info(
            f"Scan {scan_id} completado: "
            f"hosts={result['hosts_scanned']}, services={result['services_found']}"
        )
        
    except SoftTimeLimitExceeded:
        logger.warning(f"Soft time limit excedido para scan {scan_id}")
        try:
            scan = db.execute(select(Scan).where(Scan.id == scan_id)).scalar_one_or_none()
            if scan:
                scan.fail("Tiempo límite excedido")
                scan.add_log("Escaneo detenido: tiempo límite excedido", "error")
                db.commit()
        except Exception:
            pass
        result["errors"].append("Tiempo límite excedido")
        
    except Exception as e:
        logger.exception(f"Error en execute_scan_task: {e}")
        result["errors"].append(str(e))
        
        try:
            scan = db.execute(select(Scan).where(Scan.id == scan_id)).scalar_one_or_none()
            if scan and scan.status not in [ScanStatus.COMPLETED.value, ScanStatus.CANCELLED.value]:
                scan.fail(str(e))
                scan.add_log(f"Error: {str(e)}", "error")
                db.commit()
        except Exception:
            pass
        
        raise self.retry(exc=e)
        
    finally:
        db.close()
    
    return result


# =============================================================================
# Quick Access Tasks - Wrappers convenientes
# =============================================================================

@shared_task(
    name="app.workers.nmap_worker.quick_scan",
    soft_time_limit=300,
    time_limit=360,
)
def quick_scan(
    target: str,
    organization_id: str,
    scan_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Escaneo rápido de Nmap - Top 100 puertos.
    
    Usa el perfil 'quick' para escanear rápidamente los puertos más comunes.
    Ideal para validaciones iniciales.
    SEGURIDAD: Solo permite escaneos a redes privadas (RFC 1918).
    
    Args:
        target: IP o hostname a escanear
        organization_id: ID de la organización
        scan_id: ID del scan en DB (opcional)
    
    Returns:
        dict con resultados del escaneo
    """
    logger.info(f"Quick scan iniciado - target={target}")
    
    result = {
        "scan_type": "quick",
        "target": target,
        "organization_id": organization_id,
        "services": [],
        "host_info": {},
        "errors": [],
    }
    
    # SEGURIDAD: Validar que el target sea una red privada
    for single_target in target.split(","):
        if not validate_target_security(single_target.strip()):
            error_msg = f"Security: Target '{single_target}' is not a private network"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            if scan_id:
                update_scan_status_in_db(scan_id, ScanStatus.FAILED.value, error_message=error_msg)
            return result
    
    try:
        # Ejecutar nmap con perfil rápido
        xml_output = run_nmap(["-sV", "-F", "--version-light", target], timeout=240)
        
        # Parsear resultados
        scan_data = parse_port_scan_xml(xml_output)
        result["services"] = scan_data["services"]
        result["host_info"] = scan_data["host_info"]
        result["services_found"] = len(scan_data["services"])
        
        # Parsear duración del escaneo
        duration = parse_nmap_duration(xml_output)
        if duration:
            result["duration_seconds"] = duration
        
        result["success"] = True
        
        logger.info(f"Quick scan completado - {len(scan_data['services'])} servicios")
        
        # Actualizar status del scan en DB
        if scan_id:
            update_scan_status_in_db(scan_id, "completed", results=result)
        
    except subprocess.TimeoutExpired:
        result["errors"].append(f"Timeout escaneando {target}")
        logger.error(f"Timeout en quick scan: {target}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=f"Timeout escaneando {target}")
        
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Nmap error: {e.stderr}")
        logger.error(f"Nmap error en quick scan: {e}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=str(e))
        
    except Exception as e:
        result["errors"].append(str(e))
        logger.exception(f"Error en quick scan: {e}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=str(e))
    
    return result


@shared_task(
    name="app.workers.nmap_worker.full_scan",
    soft_time_limit=3600,
    time_limit=3900,
)
def full_scan(
    target: str,
    organization_id: str,
    scan_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Escaneo completo de Nmap - Todos los 65535 puertos.
    
    Usa el perfil 'full' para escanear todos los puertos TCP.
    ADVERTENCIA: Puede tardar más de 1 hora.
    SEGURIDAD: Solo permite escaneos a redes privadas (RFC 1918).
    
    Args:
        target: IP o hostname a escanear
        organization_id: ID de la organización
        scan_id: ID del scan en DB (opcional)
    
    Returns:
        dict con resultados del escaneo
    """
    logger.info(f"Full scan iniciado - target={target}")
    
    result = {
        "scan_type": "full",
        "target": target,
        "organization_id": organization_id,
        "services": [],
        "host_info": {},
        "errors": [],
    }
    
    # SEGURIDAD: Validar que el target sea una red privada
    for single_target in target.split(","):
        if not validate_target_security(single_target.strip()):
            error_msg = f"Security: Target '{single_target}' is not a private network"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            if scan_id:
                update_scan_status_in_db(scan_id, ScanStatus.FAILED.value, error_message=error_msg)
            return result
    
    try:
        # Ejecutar nmap con perfil completo
        xml_output = run_nmap([
            "-sV", "-sC", "-p-", 
            "--max-retries", "2",
            "--min-rate", "1000",
            target
        ], timeout=3500)
        
        # Parsear resultados
        scan_data = parse_port_scan_xml(xml_output)
        result["services"] = scan_data["services"]
        result["host_info"] = scan_data["host_info"]
        result["services_found"] = len(scan_data["services"])
        
        # Parsear duración del escaneo
        duration = parse_nmap_duration(xml_output)
        if duration:
            result["duration_seconds"] = duration
        
        result["success"] = True
        
        logger.info(f"Full scan completado - {len(scan_data['services'])} servicios")
        
        # Actualizar status del scan en DB
        if scan_id:
            update_scan_status_in_db(scan_id, "completed", results=result)
        
    except subprocess.TimeoutExpired:
        result["errors"].append(f"Timeout escaneando {target}")
        logger.error(f"Timeout en full scan: {target}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=f"Timeout escaneando {target}")
        
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Nmap error: {e.stderr}")
        logger.error(f"Nmap error en full scan: {e}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=str(e))
        
    except Exception as e:
        result["errors"].append(str(e))
        logger.exception(f"Error en full scan: {e}")
        if scan_id:
            update_scan_status_in_db(scan_id, "failed", error_message=str(e))
    
    return result


@shared_task(
    name="app.workers.nmap_worker.vulnerability_scan",
    soft_time_limit=1800,
    time_limit=2100,
)
def vulnerability_scan(
    target: str,
    organization_id: str,
    scan_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Escaneo de vulnerabilidades con Nmap NSE scripts.
    
    Usa scripts de detección de vulnerabilidades de Nmap.
    Incluye: vuln, vulners, exploit, auth checks.
    SEGURIDAD: Solo permite escaneos a redes privadas (RFC 1918).
    
    Args:
        target: IP o hostname a escanear
        organization_id: ID de la organización
        scan_id: ID del scan en DB (opcional)
    
    Returns:
        dict con resultados del escaneo y vulnerabilidades
    """
    logger.info(f"Vulnerability scan iniciado - target={target}")
    
    result = {
        "scan_type": "vulnerability",
        "target": target,
        "organization_id": organization_id,
        "services": [],
        "vulnerabilities": [],
        "host_info": {},
        "errors": [],
    }
    
    # SEGURIDAD: Validar que el target sea una red privada
    for single_target in target.split(","):
        if not validate_target_security(single_target.strip()):
            error_msg = f"Security: Target '{single_target}' is not a private network"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            if scan_id:
                update_scan_status_in_db(scan_id, ScanStatus.FAILED.value, error_message=error_msg)
            return result
    
    try:
        # Ejecutar nmap con scripts de vulnerabilidades (incluyendo vulners)
        xml_output = run_nmap([
            "-sV", "-sC",
            "--script", "vuln,vulners,exploit,auth",
            "-Pn",  # Skip host discovery
            target
        ], timeout=1700)
        
        # Parsear resultados
        scan_data = parse_port_scan_xml(xml_output)
        result["services"] = scan_data["services"]
        result["host_info"] = scan_data["host_info"]
        result["services_found"] = len(scan_data["services"])
        
        # Extraer vulnerabilidades de los scripts
        for service in scan_data["services"]:
            scripts = service.get("scripts", [])
            for script in scripts:
                script_id = script.get("id", "").lower()
                script_output = script.get("output", "")
                
                # Parsear script vulners para extraer CVEs
                if script_id == "vulners":
                    cves = parse_vulners_output(script_output)
                    for cve in cves:
                        cve["port"] = service["port"]
                        cve["service"] = service.get("service_name", "unknown")
                        cve["script_id"] = script_id
                        cve["description"] = f"{cve['cve_id']} detectado en {service.get('service_name', 'servicio')} puerto {service['port']}"
                        result["vulnerabilities"].append(cve)
                
                # Otros scripts de vulnerabilidades
                elif "vuln" in script_id:
                    result["vulnerabilities"].append({
                        "port": service["port"],
                        "service": service.get("service_name", "unknown"),
                        "script_id": script_id,
                        "output": script_output[:500],
                        "severity": VulnerabilitySeverity.MEDIUM.value,
                        "description": f"Vulnerabilidad detectada por script {script_id}",
                    })
        
        result["vulnerabilities_found"] = len(result["vulnerabilities"])
        
        # Parsear duración del escaneo
        duration = parse_nmap_duration(xml_output)
        if duration:
            result["duration_seconds"] = duration
        
        result["success"] = True
        
        # Actualizar estado del scan en DB con resultados (incluyendo vulnerabilidades)
        if scan_id:
            update_scan_status_in_db(scan_id, ScanStatus.COMPLETED.value, results=result)
        
        logger.info(
            f"Vulnerability scan completado - "
            f"{len(scan_data['services'])} servicios, "
            f"{len(result['vulnerabilities'])} vulns"
        )
        
    except subprocess.TimeoutExpired:
        result["errors"].append(f"Timeout escaneando {target}")
        logger.error(f"Timeout en vulnerability scan: {target}")
        if scan_id:
            update_scan_status_in_db(scan_id, ScanStatus.FAILED.value, error_message=f"Timeout escaneando {target}")
        
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Nmap error: {e.stderr}")
        logger.error(f"Nmap error en vulnerability scan: {e}")
        if scan_id:
            update_scan_status_in_db(scan_id, ScanStatus.FAILED.value, error_message=f"Nmap error: {e.stderr}")
        
    except Exception as e:
        result["errors"].append(str(e))
        logger.exception(f"Error en vulnerability scan: {e}")
        if scan_id:
            update_scan_status_in_db(scan_id, ScanStatus.FAILED.value, error_message=str(e))
    
    return result


# =============================================================================
# Export
# =============================================================================
__all__ = [
    "discovery_scan",
    "port_scan",
    "scan_network",
    "execute_scan_task",
    "quick_scan",
    "full_scan",
    "vulnerability_scan",
]
