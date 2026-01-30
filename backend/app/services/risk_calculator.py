# =============================================================================
# NESTSECURE - Risk Calculator Service
# =============================================================================
"""
Servicio para calcular scores de riesgo de vulnerabilidades y assets.

El cálculo de riesgo considera múltiples factores:
- CVSS base score
- Criticidad del asset
- Disponibilidad de exploits
- Presencia en CISA KEV
- EPSS (probabilidad de explotación)
- Antigüedad de la vulnerabilidad
- Estado de la vulnerabilidad

Fórmula base:
    risk_score = base_score * asset_multiplier * exploit_multiplier * age_factor * epss_factor

Donde:
- base_score: CVSS v3 (o v2 si no hay v3) normalizado a 0-100
- asset_multiplier: Factor basado en criticidad del asset (0.5 - 1.2)
- exploit_multiplier: Factor basado en disponibilidad de exploit (1.0 - 1.5)
- age_factor: Factor basado en antigüedad (0.8 - 1.1)
- epss_factor: Factor basado en probabilidad de explotación (1.0 - 1.3)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# =============================================================================
# Risk Calculation Constants
# =============================================================================
# Asset criticality multipliers
ASSET_CRITICALITY_MULTIPLIERS = {
    "critical": 1.2,
    "high": 1.0,
    "medium": 0.8,
    "low": 0.5,
}

# Exploit availability multipliers
EXPLOIT_MULTIPLIERS = {
    "no_exploit": 1.0,
    "poc": 1.15,  # Proof of concept
    "functional": 1.3,  # Functional exploit
    "weaponized": 1.5,  # Weaponized / in the wild
}

# CISA KEV multiplier (actively exploited)
CISA_KEV_MULTIPLIER = 1.4

# Age factors (how old is the vulnerability)
AGE_FACTORS = {
    "less_than_30_days": 1.1,  # New vulnerabilities are higher risk
    "30_to_90_days": 1.0,
    "90_to_180_days": 0.95,
    "180_to_365_days": 0.9,
    "more_than_365_days": 0.85,
}

# EPSS thresholds
EPSS_THRESHOLDS = {
    "very_high": (0.5, 1.3),   # > 50% probability
    "high": (0.25, 1.2),       # 25-50%
    "medium": (0.1, 1.1),      # 10-25%
    "low": (0.0, 1.0),         # < 10%
}


# =============================================================================
# Risk Calculator Class
# =============================================================================
class RiskCalculator:
    """
    Calculador de riesgos para vulnerabilidades y assets.
    
    Proporciona métodos para calcular scores de riesgo individuales
    y agregados, considerando múltiples factores de riesgo.
    """
    
    @staticmethod
    def calculate_vulnerability_risk(
        cvss_score: Optional[float],
        asset_criticality: str = "medium",
        exploit_available: bool = False,
        exploit_maturity: Optional[str] = None,
        in_cisa_kev: bool = False,
        epss_score: Optional[float] = None,
        first_seen: Optional[datetime] = None,
    ) -> dict:
        """
        Calcula el score de riesgo de una vulnerabilidad.
        
        Args:
            cvss_score: Puntuación CVSS (0-10)
            asset_criticality: Criticidad del asset (critical, high, medium, low)
            exploit_available: Si hay exploit conocido
            exploit_maturity: Madurez del exploit (poc, functional, weaponized)
            in_cisa_kev: Si está en la lista CISA KEV
            epss_score: Probabilidad EPSS (0-1)
            first_seen: Fecha de primera detección
        
        Returns:
            dict con risk_score y risk_factors
        """
        # Base score (normalizado a 0-100)
        base_score = (cvss_score or 5.0) * 10
        
        # Asset criticality multiplier
        asset_mult = ASSET_CRITICALITY_MULTIPLIERS.get(
            asset_criticality.lower(), 0.8
        )
        
        # Exploit multiplier
        if in_cisa_kev:
            exploit_mult = CISA_KEV_MULTIPLIER
        elif exploit_available:
            if exploit_maturity:
                exploit_mult = EXPLOIT_MULTIPLIERS.get(
                    exploit_maturity.lower(), 
                    EXPLOIT_MULTIPLIERS["poc"]
                )
            else:
                exploit_mult = EXPLOIT_MULTIPLIERS["poc"]
        else:
            exploit_mult = EXPLOIT_MULTIPLIERS["no_exploit"]
        
        # Age factor
        age_factor = 1.0
        if first_seen:
            age_days = (datetime.utcnow() - first_seen).days
            if age_days < 30:
                age_factor = AGE_FACTORS["less_than_30_days"]
            elif age_days < 90:
                age_factor = AGE_FACTORS["30_to_90_days"]
            elif age_days < 180:
                age_factor = AGE_FACTORS["90_to_180_days"]
            elif age_days < 365:
                age_factor = AGE_FACTORS["180_to_365_days"]
            else:
                age_factor = AGE_FACTORS["more_than_365_days"]
        
        # EPSS factor
        epss_factor = 1.0
        if epss_score is not None:
            for level, (threshold, factor) in EPSS_THRESHOLDS.items():
                if epss_score >= threshold:
                    epss_factor = factor
                    break
        
        # Calculate final score
        raw_score = base_score * asset_mult * exploit_mult * age_factor * epss_factor
        
        # Cap at 100
        risk_score = min(100.0, raw_score)
        
        # Build risk factors explanation
        risk_factors = {
            "base_cvss": cvss_score,
            "base_score": base_score,
            "asset_criticality": asset_criticality,
            "asset_multiplier": asset_mult,
            "exploit_available": exploit_available,
            "exploit_maturity": exploit_maturity,
            "exploit_multiplier": exploit_mult,
            "in_cisa_kev": in_cisa_kev,
            "age_factor": age_factor,
            "epss_score": epss_score,
            "epss_factor": epss_factor,
            "raw_score": raw_score,
        }
        
        return {
            "risk_score": round(risk_score, 2),
            "risk_factors": risk_factors,
        }
    
    @staticmethod
    def calculate_asset_risk(
        vuln_counts: dict,
        asset_criticality: str = "medium",
    ) -> dict:
        """
        Calcula el score de riesgo agregado de un asset.
        
        Args:
            vuln_counts: Dict con conteo por severidad
                {critical: 2, high: 5, medium: 10, low: 3}
            asset_criticality: Criticidad del asset
        
        Returns:
            dict con risk_score y risk_breakdown
        """
        # Weighted scores per severity
        severity_weights = {
            "critical": 40,
            "high": 20,
            "medium": 5,
            "low": 1,
        }
        
        # Calculate weighted sum
        weighted_sum = 0
        for severity, count in vuln_counts.items():
            weight = severity_weights.get(severity.lower(), 1)
            weighted_sum += count * weight
        
        # Apply asset criticality
        asset_mult = ASSET_CRITICALITY_MULTIPLIERS.get(
            asset_criticality.lower(), 0.8
        )
        
        raw_score = weighted_sum * asset_mult
        
        # Cap at 100
        risk_score = min(100.0, raw_score)
        
        risk_breakdown = {
            "vuln_counts": vuln_counts,
            "severity_weights": severity_weights,
            "weighted_sum": weighted_sum,
            "asset_criticality": asset_criticality,
            "asset_multiplier": asset_mult,
        }
        
        return {
            "risk_score": round(risk_score, 2),
            "risk_breakdown": risk_breakdown,
        }
    
    @staticmethod
    def get_risk_level(risk_score: float) -> str:
        """
        Convierte un risk score numérico a un nivel categórico.
        
        Args:
            risk_score: Score de 0 a 100
        
        Returns:
            str: critical, high, medium, low, o info
        """
        if risk_score >= 90:
            return "critical"
        elif risk_score >= 70:
            return "high"
        elif risk_score >= 40:
            return "medium"
        elif risk_score >= 10:
            return "low"
        else:
            return "info"
    
    @staticmethod
    def get_priority_score(
        risk_score: float,
        sla_days_remaining: Optional[int] = None,
        is_assigned: bool = False,
    ) -> float:
        """
        Calcula un score de priorización para ordenar vulnerabilidades.
        
        Considera:
        - Risk score base
        - Días restantes de SLA (urgencia)
        - Si está asignada (menor prioridad)
        
        Args:
            risk_score: Score de riesgo base
            sla_days_remaining: Días hasta vencimiento de SLA
            is_assigned: Si ya está asignada a alguien
        
        Returns:
            float: Score de prioridad (mayor = más urgente)
        """
        priority = risk_score
        
        # SLA urgency boost
        if sla_days_remaining is not None:
            if sla_days_remaining <= 0:
                priority *= 1.5  # Overdue!
            elif sla_days_remaining <= 3:
                priority *= 1.3
            elif sla_days_remaining <= 7:
                priority *= 1.15
        
        # Slightly lower priority if already assigned
        if is_assigned:
            priority *= 0.95
        
        return round(priority, 2)


# =============================================================================
# Batch Risk Calculator
# =============================================================================
class BatchRiskCalculator:
    """
    Calculador de riesgos para procesamiento en lote.
    
    Útil para recalcular scores de todas las vulnerabilidades
    de un asset o una organización.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.calculator = RiskCalculator()
    
    async def recalculate_vulnerability_risks(
        self,
        organization_id: str,
        asset_id: Optional[str] = None,
    ) -> dict:
        """
        Recalcula los scores de riesgo de vulnerabilidades.
        
        Args:
            organization_id: ID de la organización
            asset_id: ID del asset (opcional, si no se pasa, procesa todos)
        
        Returns:
            dict con estadísticas del procesamiento
        """
        from app.models.vulnerability import Vulnerability
        from app.models.asset import Asset
        from app.models.cve_cache import CVECache
        
        stats = {
            "processed": 0,
            "updated": 0,
            "errors": 0,
        }
        
        # Build query
        stmt = select(Vulnerability).where(
            Vulnerability.organization_id == organization_id
        )
        
        if asset_id:
            stmt = stmt.where(Vulnerability.asset_id == asset_id)
        
        result = await self.db.execute(stmt)
        vulnerabilities = result.scalars().all()
        
        for vuln in vulnerabilities:
            try:
                # Get asset criticality
                asset_stmt = select(Asset).where(Asset.id == vuln.asset_id)
                asset_result = await self.db.execute(asset_stmt)
                asset = asset_result.scalar_one_or_none()
                
                asset_criticality = asset.criticality if asset else "medium"
                
                # Get CVE data if available
                in_cisa_kev = False
                epss_score = None
                
                if vuln.cve_id:
                    cve_stmt = select(CVECache).where(
                        CVECache.cve_id == vuln.cve_id
                    )
                    cve_result = await self.db.execute(cve_stmt)
                    cve = cve_result.scalar_one_or_none()
                    
                    if cve:
                        in_cisa_kev = cve.cisa_kev or False
                        epss_score = cve.epss_score
                
                # Calculate risk
                risk_data = self.calculator.calculate_vulnerability_risk(
                    cvss_score=vuln.cvss_score,
                    asset_criticality=asset_criticality,
                    exploit_available=vuln.exploit_available,
                    exploit_maturity=vuln.exploit_maturity,
                    in_cisa_kev=in_cisa_kev,
                    epss_score=epss_score,
                    first_seen=vuln.first_detected_at,
                )
                
                # Update vulnerability
                vuln.risk_score = risk_data["risk_score"]
                vuln.risk_factors = risk_data["risk_factors"]
                
                stats["updated"] += 1
                
            except Exception as e:
                logger.error(f"Error calculating risk for vuln {vuln.id}: {e}")
                stats["errors"] += 1
            
            stats["processed"] += 1
        
        await self.db.commit()
        
        return stats
    
    async def recalculate_asset_risks(
        self,
        organization_id: str,
    ) -> dict:
        """
        Recalcula los scores de riesgo de todos los assets.
        
        Args:
            organization_id: ID de la organización
        
        Returns:
            dict con estadísticas del procesamiento
        """
        from app.models.asset import Asset
        from app.models.vulnerability import Vulnerability, VulnerabilityStatus
        from sqlalchemy import func
        
        stats = {
            "processed": 0,
            "updated": 0,
        }
        
        # Get all assets
        asset_stmt = select(Asset).where(
            Asset.organization_id == organization_id
        )
        asset_result = await self.db.execute(asset_stmt)
        assets = asset_result.scalars().all()
        
        for asset in assets:
            # Count active vulnerabilities by severity
            active_statuses = [
                VulnerabilityStatus.OPEN.value,
                VulnerabilityStatus.ACKNOWLEDGED.value,
                VulnerabilityStatus.IN_PROGRESS.value,
            ]
            
            vuln_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }
            
            for severity in vuln_counts.keys():
                count_stmt = select(func.count()).select_from(Vulnerability).where(
                    and_(
                        Vulnerability.asset_id == asset.id,
                        Vulnerability.severity == severity,
                        Vulnerability.status.in_(active_statuses),
                    )
                )
                count_result = await self.db.execute(count_stmt)
                vuln_counts[severity] = count_result.scalar() or 0
            
            # Calculate asset risk
            risk_data = self.calculator.calculate_asset_risk(
                vuln_counts=vuln_counts,
                asset_criticality=asset.criticality,
            )
            
            # Update asset
            asset.risk_score = risk_data["risk_score"]
            asset.vuln_critical_count = vuln_counts["critical"]
            asset.vuln_high_count = vuln_counts["high"]
            asset.vuln_medium_count = vuln_counts["medium"]
            asset.vuln_low_count = vuln_counts["low"]
            
            stats["processed"] += 1
            stats["updated"] += 1
        
        await self.db.commit()
        
        return stats


# =============================================================================
# Celery Tasks for Risk Calculation
# =============================================================================
def create_risk_calculation_tasks():
    """
    Crea tareas de Celery para cálculo de riesgos.
    
    Debe ser llamado después de que celery_app esté configurado.
    """
    from app.workers.celery_app import celery_app
    
    @celery_app.task(name="risk.recalculate_organization")
    def recalculate_organization_risks(organization_id: str) -> dict:
        """
        Recalcula todos los scores de riesgo de una organización.
        
        Args:
            organization_id: ID de la organización
        
        Returns:
            dict con estadísticas
        """
        from app.db.session import get_sync_session
        from app.models.asset import Asset
        from app.models.vulnerability import Vulnerability
        
        logger.info(f"Recalculating risks for organization {organization_id}")
        
        calculator = RiskCalculator()
        stats = {
            "vulnerabilities_processed": 0,
            "assets_processed": 0,
        }
        
        with get_sync_session() as session:
            # Process vulnerabilities
            vulns = session.query(Vulnerability).filter(
                Vulnerability.organization_id == organization_id
            ).all()
            
            for vuln in vulns:
                asset = session.query(Asset).filter(
                    Asset.id == vuln.asset_id
                ).first()
                
                risk_data = calculator.calculate_vulnerability_risk(
                    cvss_score=vuln.cvss_score,
                    asset_criticality=asset.criticality if asset else "medium",
                    exploit_available=vuln.exploit_available,
                    exploit_maturity=vuln.exploit_maturity,
                    first_seen=vuln.first_detected_at,
                )
                
                vuln.risk_score = risk_data["risk_score"]
                vuln.risk_factors = risk_data["risk_factors"]
                stats["vulnerabilities_processed"] += 1
            
            # Process assets
            assets = session.query(Asset).filter(
                Asset.organization_id == organization_id
            ).all()
            
            for asset in assets:
                vuln_counts = {
                    "critical": asset.vuln_critical_count,
                    "high": asset.vuln_high_count,
                    "medium": asset.vuln_medium_count,
                    "low": asset.vuln_low_count,
                }
                
                risk_data = calculator.calculate_asset_risk(
                    vuln_counts=vuln_counts,
                    asset_criticality=asset.criticality,
                )
                
                asset.risk_score = risk_data["risk_score"]
                stats["assets_processed"] += 1
            
            session.commit()
        
        logger.info(f"Risk recalculation completed: {stats}")
        return stats
    
    return {
        "recalculate_organization_risks": recalculate_organization_risks,
    }
