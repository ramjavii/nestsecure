# =============================================================================
# NESTSECURE - Modelo de CVE Cache
# =============================================================================
"""
Modelo SQLAlchemy para cache de CVEs desde NVD.

Este modelo almacena información de CVEs consultados desde el NVD (National
Vulnerability Database) para evitar consultas repetidas y proporcionar
información enriquecida a las vulnerabilidades detectadas.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, JSONB, StringArray


class CVECache(Base, TimestampMixin):
    """
    Modelo de CVE Cache.
    
    Cache local de información de CVEs desde NVD para evitar consultas
    repetidas a la API externa.
    
    Attributes:
        cve_id: Identificador único del CVE (ej: CVE-2024-1234)
        description: Descripción del CVE
        cvss_v3_score: Puntuación CVSS v3 (0.0-10.0)
        cvss_v3_vector: Vector CVSS v3
        published_date: Fecha de publicación del CVE
        in_cisa_kev: Indica si está en CISA KEV (Known Exploited Vulnerabilities)
    """
    
    __tablename__ = "cve_cache"
    
    # -------------------------------------------------------------------------
    # Identificador principal (CVE-YYYY-NNNN)
    # -------------------------------------------------------------------------
    cve_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        nullable=False,
    )
    
    # -------------------------------------------------------------------------
    # Información básica
    # -------------------------------------------------------------------------
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    published_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    last_modified_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    # -------------------------------------------------------------------------
    # CVSS v3
    # -------------------------------------------------------------------------
    cvss_v3_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    
    cvss_v3_vector: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    
    cvss_v3_severity: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # Métricas CVSS v3 desglosadas
    cvss_v3_attack_vector: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    cvss_v3_attack_complexity: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    cvss_v3_privileges_required: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    cvss_v3_user_interaction: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    cvss_v3_scope: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    cvss_v3_confidentiality_impact: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    cvss_v3_integrity_impact: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    cvss_v3_availability_impact: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # CVSS v2 (legacy, para CVEs antiguos)
    # -------------------------------------------------------------------------
    cvss_v2_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    
    cvss_v2_vector: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    
    cvss_v2_severity: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # CPEs afectados (Common Platform Enumeration)
    # -------------------------------------------------------------------------
    affected_cpes: Mapped[list[str]] = mapped_column(
        StringArray(),
        nullable=True,
        default=list,
    )
    
    # Productos y vendors afectados (extraídos de CPEs)
    affected_vendors: Mapped[list[str]] = mapped_column(
        StringArray(),
        nullable=True,
        default=list,
    )
    
    affected_products: Mapped[list[str]] = mapped_column(
        StringArray(),
        nullable=True,
        default=list,
    )
    
    # -------------------------------------------------------------------------
    # Información de exploits
    # -------------------------------------------------------------------------
    exploit_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    exploit_code_maturity: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # URLs de exploits conocidos
    exploit_urls: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # EPSS (Exploit Prediction Scoring System)
    # -------------------------------------------------------------------------
    epss_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    
    epss_percentile: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    
    epss_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # CISA KEV (Known Exploited Vulnerabilities)
    # -------------------------------------------------------------------------
    in_cisa_kev: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    
    cisa_date_added: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    cisa_due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    cisa_required_action: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    cisa_vulnerability_name: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # CWE (Common Weakness Enumeration)
    # -------------------------------------------------------------------------
    cwe_ids: Mapped[list[str]] = mapped_column(
        StringArray(),
        nullable=True,
        default=list,
    )
    
    # -------------------------------------------------------------------------
    # Referencias y parches
    # -------------------------------------------------------------------------
    references: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
    )
    
    patches: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
    )
    
    # -------------------------------------------------------------------------
    # Control de cache
    # -------------------------------------------------------------------------
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    
    sync_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="nvd",
    )
    
    # Número de veces que se ha consultado este CVE
    hit_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # -------------------------------------------------------------------------
    # Métodos de utilidad
    # -------------------------------------------------------------------------
    @property
    def severity(self) -> str:
        """Retorna la severidad basada en CVSS v3 o v2."""
        if self.cvss_v3_severity:
            return self.cvss_v3_severity.lower()
        if self.cvss_v2_severity:
            return self.cvss_v2_severity.lower()
        return "unknown"
    
    @property
    def cvss_score(self) -> Optional[float]:
        """Retorna el score CVSS (preferencia v3 sobre v2)."""
        return self.cvss_v3_score or self.cvss_v2_score
    
    @property
    def is_critical(self) -> bool:
        """Indica si el CVE es crítico (score >= 9.0)."""
        score = self.cvss_score
        return score is not None and score >= 9.0
    
    @property
    def is_exploited_in_wild(self) -> bool:
        """Indica si hay evidencia de explotación activa."""
        return self.in_cisa_kev or self.exploit_available
    
    def increment_hit_count(self) -> None:
        """Incrementa el contador de consultas."""
        self.hit_count += 1
    
    def update_from_nvd(self, nvd_data: dict) -> None:
        """
        Actualiza el CVE desde datos de NVD API.
        
        Args:
            nvd_data: Diccionario con datos del CVE desde NVD
        """
        cve = nvd_data.get("cve", {})
        
        # Descripción
        descriptions = cve.get("descriptions", [])
        for desc in descriptions:
            if desc.get("lang") == "en":
                self.description = desc.get("value", "")
                break
        
        # Fechas
        self.published_date = datetime.fromisoformat(
            cve.get("published", "").replace("Z", "+00:00")
        )
        self.last_modified_date = datetime.fromisoformat(
            cve.get("lastModified", "").replace("Z", "+00:00")
        )
        
        # CVSS v3
        metrics = cve.get("metrics", {})
        cvss_v3_list = metrics.get("cvssMetricV31", []) or metrics.get("cvssMetricV30", [])
        if cvss_v3_list:
            cvss_v3 = cvss_v3_list[0].get("cvssData", {})
            self.cvss_v3_score = cvss_v3.get("baseScore")
            self.cvss_v3_vector = cvss_v3.get("vectorString")
            self.cvss_v3_severity = cvss_v3.get("baseSeverity")
            self.cvss_v3_attack_vector = cvss_v3.get("attackVector")
            self.cvss_v3_attack_complexity = cvss_v3.get("attackComplexity")
            self.cvss_v3_privileges_required = cvss_v3.get("privilegesRequired")
            self.cvss_v3_user_interaction = cvss_v3.get("userInteraction")
            self.cvss_v3_scope = cvss_v3.get("scope")
            self.cvss_v3_confidentiality_impact = cvss_v3.get("confidentialityImpact")
            self.cvss_v3_integrity_impact = cvss_v3.get("integrityImpact")
            self.cvss_v3_availability_impact = cvss_v3.get("availabilityImpact")
        
        # CVSS v2
        cvss_v2_list = metrics.get("cvssMetricV2", [])
        if cvss_v2_list:
            cvss_v2 = cvss_v2_list[0].get("cvssData", {})
            self.cvss_v2_score = cvss_v2.get("baseScore")
            self.cvss_v2_vector = cvss_v2.get("vectorString")
            self.cvss_v2_severity = cvss_v2_list[0].get("baseSeverity")
        
        # CWE
        weaknesses = cve.get("weaknesses", [])
        cwe_ids = []
        for weakness in weaknesses:
            for desc in weakness.get("description", []):
                if desc.get("lang") == "en":
                    cwe_ids.append(desc.get("value", ""))
        self.cwe_ids = cwe_ids
        
        # Referencias
        refs = cve.get("references", [])
        self.references = {"urls": [ref.get("url") for ref in refs]}
        
        # Timestamp de sync
        self.last_synced_at = datetime.now(timezone.utc)
