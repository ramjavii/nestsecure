# =============================================================================
# NESTSECURE - GVM XML Parser
# =============================================================================
"""
Parser para reportes XML de GVM/OpenVAS.

Convierte la respuesta XML de GVM a nuestros modelos de datos.
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from xml.etree import ElementTree as ET

from .models import (
    GVMSeverity,
    GVMTarget,
    GVMTask,
    GVMTaskStatus,
    GVMVulnerability,
    GVMHostResult,
    GVMReport,
    GVMScanConfig,
    GVMPortList,
)
from .exceptions import GVMError

# Regex para extraer CVEs
CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)


class GVMParser:
    """
    Parser para respuestas XML de GVM.
    
    Convierte elementos XML a dataclasses tipados.
    
    Usage:
        parser = GVMParser()
        report = parser.parse_report(xml_element, report_id)
        targets = parser.parse_targets(xml_element)
    """
    
    def __init__(self, include_log_level: bool = False):
        """
        Inicializar parser.
        
        Args:
            include_log_level: Si True, incluye vulnerabilidades de nivel "Log"
        """
        self.include_log_level = include_log_level
    
    # =========================================================================
    # TARGETS
    # =========================================================================
    
    def parse_targets(self, xml: Union[ET.Element, str]) -> List[GVMTarget]:
        """
        Parsear lista de targets.
        
        Args:
            xml: Elemento XML o string XML
        
        Returns:
            Lista de GVMTarget
        """
        root = self._ensure_element(xml)
        targets = []
        
        for target in root.findall(".//target"):
            targets.append(self._parse_target(target))
        
        return targets
    
    def _parse_target(self, element: ET.Element) -> GVMTarget:
        """Parsear un elemento target."""
        port_list = element.find("port_list")
        
        return GVMTarget(
            id=element.get("id", ""),
            name=self._get_text(element, "name"),
            hosts=self._get_text(element, "hosts"),
            port_list_id=port_list.get("id") if port_list is not None else None,
            port_list_name=self._get_text(port_list, "name") if port_list is not None else None,
            comment=self._get_text(element, "comment"),
            creation_time=self._parse_datetime(self._get_text(element, "creation_time")),
            modification_time=self._parse_datetime(self._get_text(element, "modification_time")),
            exclude_hosts=self._get_text(element, "exclude_hosts"),
            alive_test=self._get_text(element, "alive_tests") or "Scan Config Default",
        )
    
    # =========================================================================
    # TASKS
    # =========================================================================
    
    def parse_tasks(self, xml: Union[ET.Element, str]) -> List[GVMTask]:
        """
        Parsear lista de tasks.
        
        Args:
            xml: Elemento XML o string XML
        
        Returns:
            Lista de GVMTask
        """
        root = self._ensure_element(xml)
        tasks = []
        
        for task in root.findall(".//task"):
            tasks.append(self._parse_task(task))
        
        return tasks
    
    def parse_task(self, xml: Union[ET.Element, str]) -> GVMTask:
        """
        Parsear una task individual.
        
        Args:
            xml: Elemento XML o string XML
        
        Returns:
            GVMTask
        """
        root = self._ensure_element(xml)
        task = root.find(".//task")
        
        if task is None:
            raise GVMError("No task found in XML")
        
        return self._parse_task(task)
    
    def _parse_task(self, element: ET.Element) -> GVMTask:
        """Parsear un elemento task."""
        target = element.find("target")
        config = element.find("config")
        scanner = element.find("scanner")
        last_report = element.find(".//last_report/report")
        
        # Progress puede estar en diferentes lugares
        progress = self._get_text(element, "progress") or "0"
        if not progress.isdigit():
            progress = "0"
        
        return GVMTask(
            id=element.get("id", ""),
            name=self._get_text(element, "name"),
            status=self._get_text(element, "status") or "New",
            progress=int(progress),
            target_id=target.get("id") if target is not None else None,
            target_name=self._get_text(target, "name") if target is not None else None,
            config_id=config.get("id") if config is not None else None,
            config_name=self._get_text(config, "name") if config is not None else None,
            scanner_id=scanner.get("id") if scanner is not None else None,
            scanner_name=self._get_text(scanner, "name") if scanner is not None else None,
            last_report_id=last_report.get("id") if last_report is not None else None,
            creation_time=self._parse_datetime(self._get_text(element, "creation_time")),
            modification_time=self._parse_datetime(self._get_text(element, "modification_time")),
            comment=self._get_text(element, "comment"),
        )
    
    # =========================================================================
    # REPORTS
    # =========================================================================
    
    def parse_report(
        self,
        xml: Union[ET.Element, str],
        report_id: str
    ) -> GVMReport:
        """
        Parsear un reporte completo.
        
        Args:
            xml: Elemento XML o string XML
            report_id: ID del reporte
        
        Returns:
            GVMReport con todos los resultados
        """
        root = self._ensure_element(xml)
        
        # Buscar el elemento report
        report_elem = root.find(".//report")
        if report_elem is None:
            report_elem = root
        
        # Info del task
        task = report_elem.find(".//task")
        task_id = task.get("id") if task is not None else ""
        task_name = self._get_text(task, "name") if task is not None else None
        
        # Tiempos
        scan_start = self._parse_datetime(self._get_text(report_elem, ".//scan_start"))
        scan_end = self._parse_datetime(self._get_text(report_elem, ".//scan_end"))
        
        # Parsear resultados agrupados por host
        hosts_dict: Dict[str, GVMHostResult] = {}
        
        for result in report_elem.findall(".//results/result"):
            vuln = self._parse_vulnerability(result)
            
            # Filtrar log level si no se incluye
            if not self.include_log_level and vuln.severity_class == GVMSeverity.LOG:
                continue
            
            # Agrupar por host
            if vuln.host not in hosts_dict:
                hosts_dict[vuln.host] = GVMHostResult(ip=vuln.host)
            
            hosts_dict[vuln.host].vulnerabilities.append(vuln)
            
            # Agregar puerto si es único
            if vuln.port and vuln.port not in hosts_dict[vuln.host].ports:
                hosts_dict[vuln.host].ports.append(vuln.port)
        
        # Parsear info de hosts (OS, hostname, etc.)
        for host_elem in report_elem.findall(".//host"):
            ip = self._get_text(host_elem, "ip") or host_elem.text
            if ip and ip in hosts_dict:
                host_result = hosts_dict[ip]
                
                # Buscar hostname
                for detail in host_elem.findall(".//detail"):
                    name = self._get_text(detail, "name")
                    value = self._get_text(detail, "value")
                    
                    if name == "hostname":
                        host_result.hostname = value
                    elif name == "best_os_txt":
                        host_result.os = value
                    elif name == "best_os_cpe":
                        host_result.os_cpe = value
                
                # Tiempos del host
                host_start = host_elem.find("start")
                host_end = host_elem.find("end")
                if host_start is not None:
                    host_result.start_time = self._parse_datetime(host_start.text)
                if host_end is not None:
                    host_result.end_time = self._parse_datetime(host_end.text)
        
        # Crear reporte
        report = GVMReport(
            id=report_id,
            task_id=task_id,
            task_name=task_name,
            scan_start=scan_start,
            scan_end=scan_end,
            hosts=list(hosts_dict.values()),
            scan_run_status=self._get_text(report_elem, ".//scan_run_status"),
        )
        
        # Calcular estadísticas
        report.calculate_stats()
        
        return report
    
    def _parse_vulnerability(self, element: ET.Element) -> GVMVulnerability:
        """Parsear un elemento result a GVMVulnerability."""
        # Host
        host_elem = element.find("host")
        host = self._get_text(host_elem, None) if host_elem is not None else ""
        if host_elem is not None and not host:
            host = host_elem.text or ""
        
        # Extraer asset hostname si existe
        asset = host_elem.find("asset") if host_elem is not None else None
        hostname = asset.get("name") if asset is not None else None
        
        # Port
        port = self._get_text(element, "port")
        
        # NVT info
        nvt = element.find("nvt")
        nvt_oid = nvt.get("oid") if nvt is not None else None
        
        # Severity
        severity_str = self._get_text(element, "severity") or "0.0"
        try:
            severity = float(severity_str)
        except ValueError:
            severity = 0.0
        
        # Threat
        threat = self._get_text(element, "threat") or "Log"
        
        # CVEs
        cve_ids = self._extract_cves(element)
        
        # Description y solution
        description = self._get_text(nvt, "tags") if nvt is not None else None
        description = self._parse_tags(description)
        
        solution = None
        solution_type = None
        summary = None
        insight = None
        impact = None
        affected = None
        detection = None
        
        if nvt is not None:
            # Parsear tags de NVT
            tags_text = self._get_text(nvt, "tags")
            if tags_text:
                tags = self._parse_nvt_tags(tags_text)
                summary = tags.get("summary")
                solution = tags.get("solution")
                solution_type = tags.get("solution_type")
                insight = tags.get("insight")
                impact = tags.get("impact")
                affected = tags.get("affected")
                detection = tags.get("vuldetect")
        
        # QoD
        qod = element.find("qod")
        qod_value = 0
        qod_type = None
        if qod is not None:
            qod_value_str = self._get_text(qod, "value") or "0"
            try:
                qod_value = int(qod_value_str)
            except ValueError:
                pass
            qod_type = self._get_text(qod, "type")
        
        # Referencias
        xrefs = []
        if nvt is not None:
            refs = nvt.find("refs")
            if refs is not None:
                for ref in refs.findall("ref"):
                    ref_type = ref.get("type", "")
                    ref_id = ref.get("id", "")
                    if ref_type and ref_id:
                        xrefs.append(f"{ref_type}:{ref_id}")
        
        # Family
        family = self._get_text(nvt, "family") if nvt is not None else None
        
        return GVMVulnerability(
            id=element.get("id", ""),
            name=self._get_text(element, "name") or self._get_text(nvt, "name") or "Unknown",
            host=host,
            port=port,
            severity=severity,
            severity_class=GVMSeverity.from_cvss(severity),
            cvss_base=severity if severity > 0 else None,
            description=description or summary,
            summary=summary,
            solution=solution,
            solution_type=solution_type,
            insight=insight,
            impact=impact,
            affected=affected,
            detection=detection,
            cve_ids=cve_ids,
            xrefs=xrefs,
            threat=threat,
            family=family,
            nvt_oid=nvt_oid,
            qod=qod_value,
            qod_type=qod_type,
        )
    
    # =========================================================================
    # CONFIGS Y PORT LISTS
    # =========================================================================
    
    def parse_scan_configs(self, xml: Union[ET.Element, str]) -> List[GVMScanConfig]:
        """Parsear lista de configuraciones de escaneo."""
        root = self._ensure_element(xml)
        configs = []
        
        for config in root.findall(".//config"):
            configs.append(GVMScanConfig(
                id=config.get("id", ""),
                name=self._get_text(config, "name"),
                type=self._get_text(config, "type") or "0",
                family_count=self._get_int(config, "family_count"),
                nvt_count=self._get_int(config, "nvt_count"),
                comment=self._get_text(config, "comment"),
            ))
        
        return configs
    
    def parse_port_lists(self, xml: Union[ET.Element, str]) -> List[GVMPortList]:
        """Parsear lista de port lists."""
        root = self._ensure_element(xml)
        port_lists = []
        
        for pl in root.findall(".//port_list"):
            port_lists.append(GVMPortList(
                id=pl.get("id", ""),
                name=self._get_text(pl, "name"),
                port_count=self._get_int(pl, "port_count"),
                comment=self._get_text(pl, "comment"),
            ))
        
        return port_lists
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _ensure_element(self, xml: Union[ET.Element, str]) -> ET.Element:
        """Asegurar que tenemos un Element."""
        if isinstance(xml, str):
            return ET.fromstring(xml)
        return xml
    
    def _get_text(
        self,
        element: Optional[ET.Element],
        path: Optional[str] = None
    ) -> Optional[str]:
        """Obtener texto de un elemento o subelemento."""
        if element is None:
            return None
        
        if path:
            sub = element.find(path)
            if sub is not None:
                return sub.text
            return None
        
        return element.text
    
    def _get_int(
        self,
        element: Optional[ET.Element],
        path: str,
        default: int = 0
    ) -> int:
        """Obtener entero de un elemento."""
        text = self._get_text(element, path)
        if text and text.isdigit():
            return int(text)
        return default
    
    def _parse_datetime(self, text: Optional[str]) -> Optional[datetime]:
        """Parsear datetime de GVM."""
        if not text:
            return None
        
        # Formatos comunes de GVM
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%a %b %d %H:%M:%S %Y",
            "%Y-%m-%dT%H:%M:%S.%fZ",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(text.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _extract_cves(self, element: ET.Element) -> List[str]:
        """Extraer CVEs de un resultado."""
        cves = set()
        
        # Buscar en refs/ref con type="cve"
        nvt = element.find("nvt")
        if nvt is not None:
            refs = nvt.find("refs")
            if refs is not None:
                for ref in refs.findall("ref"):
                    if ref.get("type", "").lower() == "cve":
                        cve_id = ref.get("id", "")
                        if cve_id:
                            cves.add(cve_id.upper())
        
        # Buscar en texto con regex
        text = ET.tostring(element, encoding="unicode", method="text")
        found = CVE_PATTERN.findall(text)
        for cve in found:
            cves.add(cve.upper())
        
        return sorted(list(cves))
    
    def _parse_tags(self, tags_text: Optional[str]) -> Optional[str]:
        """Parsear tags y extraer descripción."""
        if not tags_text:
            return None
        
        # Los tags tienen formato: key=value|key2=value2|...
        parts = tags_text.split("|")
        for part in parts:
            if part.startswith("summary="):
                return part[8:]
        
        return tags_text
    
    def _parse_nvt_tags(self, tags_text: str) -> Dict[str, str]:
        """Parsear todos los tags de un NVT."""
        result = {}
        
        if not tags_text:
            return result
        
        # Formato: key=value|key2=value2|...
        parts = tags_text.split("|")
        for part in parts:
            if "=" in part:
                key, _, value = part.partition("=")
                result[key.strip()] = value.strip()
        
        return result
