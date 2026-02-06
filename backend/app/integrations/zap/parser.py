# =============================================================================
# NESTSECURE - Parser de Alertas ZAP
# =============================================================================
"""
Parser para convertir alertas de ZAP a vulnerabilidades de NESTSECURE.

Mapea alertas ZAP a:
- Severidad NESTSECURE
- CWE/CVE cuando están disponibles
- OWASP Top 10
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from app.models.vulnerability import VulnerabilitySeverity
from app.utils.logger import get_logger
from app.integrations.zap.config import (
    ZAP_ALERT_RISKS,
    ZAP_ALERT_CONFIDENCES,
    ZAP_RISK_TO_SEVERITY,
    ZAP_CWE_MAPPING,
)


logger = get_logger(__name__)


@dataclass
class ParsedZapAlert:
    """Alerta ZAP parseada."""
    # Identificación
    alert_id: str
    plugin_id: int
    name: str
    
    # Ubicación
    url: str
    method: str
    param: Optional[str]
    attack: Optional[str]
    evidence: Optional[str]
    
    # Clasificación
    risk: int  # 0-3
    risk_name: str
    confidence: int  # 0-4
    confidence_name: str
    severity: VulnerabilitySeverity
    
    # Detalles
    description: str
    solution: str
    reference: str
    other_info: Optional[str]
    
    # Clasificación estándar
    cwe_id: Optional[int]
    wasc_id: Optional[int]
    owasp_top_10: Optional[str]
    
    # Metadatos
    tags: Dict
    source: str = "zap"


class ZapAlertParser:
    """
    Parser de alertas ZAP a formato NESTSECURE.
    
    Ejemplo:
        parser = ZapAlertParser()
        parsed = parser.parse_alert(zap_alert)
        vulnerability = parser.to_vulnerability_create(parsed, asset_id, scan_id)
    """
    
    def __init__(self):
        """Inicializar parser."""
        self.cwe_mapping = ZAP_CWE_MAPPING
    
    def parse_alert(self, alert: Dict) -> ParsedZapAlert:
        """
        Parsear una alerta ZAP.
        
        Args:
            alert: Dict con datos de alerta de ZAP API
        
        Returns:
            Alerta parseada
        """
        risk = int(alert.get("risk", 0))
        confidence = int(alert.get("confidence", 0))
        
        # Extraer CWE ID
        cwe_id = None
        cwe_string = alert.get("cweid", "")
        if cwe_string:
            try:
                cwe_id = int(cwe_string)
            except (ValueError, TypeError):
                pass
        
        # Extraer WASC ID
        wasc_id = None
        wasc_string = alert.get("wascid", "")
        if wasc_string:
            try:
                wasc_id = int(wasc_string)
            except (ValueError, TypeError):
                pass
        
        # Obtener OWASP Top 10 del CWE mapping
        owasp_top_10 = None
        if cwe_id and cwe_id in self.cwe_mapping:
            owasp_top_10 = self.cwe_mapping[cwe_id].get("owasp_top_10")
        
        # Mapear severidad
        severity = self._map_severity(risk, confidence)
        
        # Extraer tags
        tags = {}
        if alert.get("tags"):
            tags = alert["tags"]
        
        return ParsedZapAlert(
            alert_id=alert.get("id", str(alert.get("pluginId", ""))),
            plugin_id=int(alert.get("pluginId", 0)),
            name=alert.get("name", alert.get("alert", "Unknown Alert")),
            url=alert.get("url", ""),
            method=alert.get("method", "GET"),
            param=alert.get("param") or None,
            attack=alert.get("attack") or None,
            evidence=alert.get("evidence") or None,
            risk=risk,
            risk_name=ZAP_ALERT_RISKS.get(risk, "UNKNOWN"),
            confidence=confidence,
            confidence_name=ZAP_ALERT_CONFIDENCES.get(confidence, "UNKNOWN"),
            severity=severity,
            description=alert.get("description", ""),
            solution=alert.get("solution", ""),
            reference=alert.get("reference", ""),
            other_info=alert.get("otherinfo") or None,
            cwe_id=cwe_id,
            wasc_id=wasc_id,
            owasp_top_10=owasp_top_10,
            tags=tags,
        )
    
    def parse_alerts(self, alerts: List[Dict]) -> List[ParsedZapAlert]:
        """Parsear múltiples alertas."""
        parsed = []
        for alert in alerts:
            try:
                parsed.append(self.parse_alert(alert))
            except Exception as e:
                logger.warning(f"Error parseando alerta ZAP: {e}")
        return parsed
    
    def _map_severity(self, risk: int, confidence: int) -> VulnerabilitySeverity:
        """
        Mapear riesgo y confianza a severidad NESTSECURE.
        
        Args:
            risk: Nivel de riesgo ZAP (0-3)
            confidence: Nivel de confianza ZAP (0-4)
        
        Returns:
            Severidad de NESTSECURE
        """
        # Si la confianza es muy baja, reducir severidad
        if confidence == 0:  # False positive
            return VulnerabilitySeverity.INFO
        
        severity_name = ZAP_RISK_TO_SEVERITY.get(risk, "info")
        
        # Ajustar si confianza es baja
        if confidence == 1 and severity_name in ("high", "critical"):
            severity_name = "medium"
        
        return VulnerabilitySeverity(severity_name)
    
    def to_vulnerability_create(
        self,
        parsed: ParsedZapAlert,
        asset_id: UUID,
        scan_id: UUID,
        organization_id: UUID,
    ) -> Dict:
        """
        Convertir alerta parseada a dict para crear Vulnerability.
        
        Args:
            parsed: Alerta parseada
            asset_id: ID del asset
            scan_id: ID del scan
            organization_id: ID de la organización
        
        Returns:
            Dict con campos para VulnerabilityCreate
        """
        # Construir título
        title = parsed.name
        if parsed.param:
            title = f"{title} (param: {parsed.param})"
        
        # Construir descripción completa
        description_parts = [parsed.description]
        if parsed.attack:
            description_parts.append(f"\n**Attack:** {parsed.attack}")
        if parsed.evidence:
            description_parts.append(f"\n**Evidence:** {parsed.evidence[:500]}")
        if parsed.other_info:
            description_parts.append(f"\n**Additional Info:** {parsed.other_info[:500]}")
        
        description = "\n".join(description_parts)
        
        # Construir referencias
        references = []
        if parsed.reference:
            # ZAP puede devolver múltiples referencias separadas por newline
            for ref in parsed.reference.split("\n"):
                ref = ref.strip()
                if ref and ref.startswith("http"):
                    references.append(ref)
        
        if parsed.cwe_id:
            references.append(f"https://cwe.mitre.org/data/definitions/{parsed.cwe_id}.html")
        
        if parsed.wasc_id:
            references.append(f"http://projects.webappsec.org/w/page/{parsed.wasc_id}")
        
        # Construir CVE ID si está disponible en tags o nombre
        cve_id = None
        if "CVE" in parsed.name.upper():
            import re
            cve_match = re.search(r'CVE-\d{4}-\d+', parsed.name.upper())
            if cve_match:
                cve_id = cve_match.group(0)
        
        return {
            "name": title[:255],  # Limitar longitud
            "description": description[:4000],  # Limitar longitud
            "severity": parsed.severity,
            "status": "OPEN",
            "cve_id": cve_id,
            "host": parsed.url,
            "port": self._extract_port(parsed.url),
            "asset_id": asset_id,
            "scan_id": scan_id,
            "organization_id": organization_id,
            "source": "zap",
            "remediation": parsed.solution[:2000] if parsed.solution else None,
            "references": references[:10],  # Limitar referencias
            "raw_data": {
                "zap_alert_id": parsed.alert_id,
                "zap_plugin_id": parsed.plugin_id,
                "method": parsed.method,
                "param": parsed.param,
                "attack": parsed.attack,
                "evidence": parsed.evidence[:200] if parsed.evidence else None,
                "risk": parsed.risk,
                "confidence": parsed.confidence,
                "cwe_id": parsed.cwe_id,
                "wasc_id": parsed.wasc_id,
                "owasp_top_10": parsed.owasp_top_10,
            },
        }
    
    def _extract_port(self, url: str) -> Optional[int]:
        """Extraer puerto de una URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.port:
                return parsed.port
            if parsed.scheme == "https":
                return 443
            if parsed.scheme == "http":
                return 80
        except:
            pass
        return None
    
    def group_alerts_by_type(self, alerts: List[ParsedZapAlert]) -> Dict[str, List[ParsedZapAlert]]:
        """
        Agrupar alertas por tipo/nombre.
        
        Útil para reducir duplicados cuando el mismo problema
        aparece en múltiples URLs.
        """
        groups: Dict[str, List[ParsedZapAlert]] = {}
        for alert in alerts:
            key = f"{alert.plugin_id}:{alert.name}"
            if key not in groups:
                groups[key] = []
            groups[key].append(alert)
        return groups
    
    def deduplicate_alerts(
        self,
        alerts: List[ParsedZapAlert],
        keep_highest_confidence: bool = True,
    ) -> List[ParsedZapAlert]:
        """
        Deduplicar alertas similares.
        
        Args:
            alerts: Lista de alertas
            keep_highest_confidence: Si True, mantiene la alerta con mayor confianza
        
        Returns:
            Lista de alertas deduplicadas
        """
        groups = self.group_alerts_by_type(alerts)
        deduplicated = []
        
        for group in groups.values():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                if keep_highest_confidence:
                    # Ordenar por confianza descendente, luego por riesgo descendente
                    sorted_group = sorted(
                        group,
                        key=lambda a: (a.confidence, a.risk),
                        reverse=True
                    )
                    deduplicated.append(sorted_group[0])
                else:
                    deduplicated.append(group[0])
        
        return deduplicated
    
    def get_severity_summary(self, alerts: List[ParsedZapAlert]) -> Dict[str, int]:
        """Obtener resumen de severidades."""
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
            "total": len(alerts),
        }
        
        for alert in alerts:
            severity_name = alert.severity.value.lower()
            if severity_name in summary:
                summary[severity_name] += 1
        
        return summary
