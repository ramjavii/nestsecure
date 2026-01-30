# =============================================================================
# NESTSECURE - Dashboard API
# =============================================================================
"""
Endpoints de Dashboard para estadísticas y resúmenes.

Incluye:
- GET /stats: Estadísticas generales de la organización
- GET /recent-assets: Assets descubiertos recientemente
- GET /recent-scans: Últimos escaneos
- GET /vulnerability-summary: Resumen de vulnerabilidades
- GET /risk-overview: Visión general de riesgos
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentActiveUser
from app.db.session import get_db
from app.models.asset import Asset, AssetCriticality, AssetStatus
from app.models.service import Service, ServiceState
from app.schemas.asset import AssetRead

router = APIRouter()


# =============================================================================
# Stats Endpoint
# =============================================================================
@router.get(
    "/stats",
    summary="Estadísticas generales",
    description="Obtiene estadísticas generales del dashboard",
)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
) -> dict[str, Any]:
    """
    Estadísticas generales del dashboard.
    
    Returns:
        - Total de assets y desglose por estado
        - Total de servicios y desglose por estado
        - Conteo de vulnerabilidades por severidad
        - Risk score promedio
        - Tendencias (últimos 7 días)
    """
    org_id = current_user.organization_id
    
    # -------------------------------------------------------------------------
    # Assets Stats
    # -------------------------------------------------------------------------
    assets_query = select(
        func.count(Asset.id).label("total"),
        func.count(case((Asset.status == AssetStatus.ACTIVE.value, 1))).label("active"),
        func.count(case((Asset.status == AssetStatus.INACTIVE.value, 1))).label("inactive"),
        func.count(case((Asset.status == AssetStatus.MAINTENANCE.value, 1))).label("maintenance"),
        func.count(case((Asset.is_reachable == True, 1))).label("reachable"),
        func.avg(Asset.risk_score).label("avg_risk_score"),
    ).where(Asset.organization_id == org_id)
    
    assets_result = await db.execute(assets_query)
    assets_row = assets_result.one()
    
    # Assets por criticidad
    criticality_query = select(
        Asset.criticality,
        func.count(Asset.id).label("count"),
    ).where(Asset.organization_id == org_id).group_by(Asset.criticality)
    
    criticality_result = await db.execute(criticality_query)
    criticality_counts = {row.criticality: row.count for row in criticality_result.all()}
    
    # -------------------------------------------------------------------------
    # Services Stats
    # -------------------------------------------------------------------------
    services_query = select(
        func.count(Service.id).label("total"),
        func.count(case((Service.state == ServiceState.OPEN.value, 1))).label("open"),
        func.count(case((Service.state == ServiceState.CLOSED.value, 1))).label("closed"),
        func.count(case((Service.state == ServiceState.FILTERED.value, 1))).label("filtered"),
        func.count(case((Service.ssl_enabled == True, 1))).label("with_ssl"),
    ).join(Asset).where(Asset.organization_id == org_id)
    
    services_result = await db.execute(services_query)
    services_row = services_result.one()
    
    # -------------------------------------------------------------------------
    # Vulnerabilities Summary
    # -------------------------------------------------------------------------
    vuln_query = select(
        func.sum(Asset.vuln_critical_count).label("critical"),
        func.sum(Asset.vuln_high_count).label("high"),
        func.sum(Asset.vuln_medium_count).label("medium"),
        func.sum(Asset.vuln_low_count).label("low"),
    ).where(Asset.organization_id == org_id)
    
    vuln_result = await db.execute(vuln_query)
    vuln_row = vuln_result.one()
    
    # -------------------------------------------------------------------------
    # Recent Activity (últimos 7 días)
    # -------------------------------------------------------------------------
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    new_assets_query = select(func.count(Asset.id)).where(
        and_(
            Asset.organization_id == org_id,
            Asset.first_seen >= week_ago,
        )
    )
    new_assets_result = await db.execute(new_assets_query)
    new_assets = new_assets_result.scalar() or 0
    
    scanned_assets_query = select(func.count(Asset.id)).where(
        and_(
            Asset.organization_id == org_id,
            Asset.last_scanned >= week_ago,
        )
    )
    scanned_assets_result = await db.execute(scanned_assets_query)
    scanned_assets = scanned_assets_result.scalar() or 0
    
    return {
        "assets": {
            "total": assets_row.total or 0,
            "active": assets_row.active or 0,
            "inactive": assets_row.inactive or 0,
            "maintenance": assets_row.maintenance or 0,
            "reachable": assets_row.reachable or 0,
            "by_criticality": {
                "critical": criticality_counts.get(AssetCriticality.CRITICAL.value, 0),
                "high": criticality_counts.get(AssetCriticality.HIGH.value, 0),
                "medium": criticality_counts.get(AssetCriticality.MEDIUM.value, 0),
                "low": criticality_counts.get(AssetCriticality.LOW.value, 0),
            },
        },
        "services": {
            "total": services_row.total or 0,
            "open": services_row.open or 0,
            "closed": services_row.closed or 0,
            "filtered": services_row.filtered or 0,
            "with_ssl": services_row.with_ssl or 0,
        },
        "vulnerabilities": {
            "critical": int(vuln_row.critical or 0),
            "high": int(vuln_row.high or 0),
            "medium": int(vuln_row.medium or 0),
            "low": int(vuln_row.low or 0),
            "total": int((vuln_row.critical or 0) + (vuln_row.high or 0) + 
                        (vuln_row.medium or 0) + (vuln_row.low or 0)),
        },
        "risk": {
            "average_score": round(float(assets_row.avg_risk_score or 0), 2),
            "assets_at_risk": criticality_counts.get(AssetCriticality.CRITICAL.value, 0) +
                             criticality_counts.get(AssetCriticality.HIGH.value, 0),
        },
        "activity": {
            "new_assets_7d": new_assets,
            "scanned_assets_7d": scanned_assets,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Recent Assets
# =============================================================================
@router.get(
    "/recent-assets",
    response_model=list[AssetRead],
    summary="Assets recientes",
    description="Obtiene los assets descubiertos más recientemente",
)
async def get_recent_assets(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    limit: int = Query(default=10, ge=1, le=50, description="Número de assets"),
    days: int = Query(default=7, ge=1, le=30, description="Días hacia atrás"),
) -> list[AssetRead]:
    """
    Assets descubiertos recientemente.
    
    Ordenados por first_seen descendente.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    stmt = (
        select(Asset)
        .where(
            and_(
                Asset.organization_id == current_user.organization_id,
                Asset.first_seen >= cutoff,
            )
        )
        .order_by(Asset.first_seen.desc())
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    assets = result.scalars().all()
    
    return [AssetRead.model_validate(a) for a in assets]


# =============================================================================
# Top Risky Assets
# =============================================================================
@router.get(
    "/top-risky-assets",
    response_model=list[AssetRead],
    summary="Assets más riesgosos",
    description="Obtiene los assets con mayor puntuación de riesgo",
)
async def get_top_risky_assets(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    limit: int = Query(default=10, ge=1, le=50, description="Número de assets"),
) -> list[AssetRead]:
    """
    Assets con mayor riesgo.
    
    Ordenados por risk_score descendente.
    """
    stmt = (
        select(Asset)
        .where(Asset.organization_id == current_user.organization_id)
        .order_by(Asset.risk_score.desc())
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    assets = result.scalars().all()
    
    return [AssetRead.model_validate(a) for a in assets]


# =============================================================================
# Ports Distribution
# =============================================================================
@router.get(
    "/ports-distribution",
    summary="Distribución de puertos",
    description="Obtiene la distribución de puertos abiertos más comunes",
)
async def get_ports_distribution(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    limit: int = Query(default=15, ge=1, le=50, description="Número de puertos"),
) -> list[dict[str, Any]]:
    """
    Distribución de puertos abiertos.
    
    Útil para gráficos de barras en el dashboard.
    """
    stmt = (
        select(
            Service.port,
            Service.service_name,
            func.count(Service.id).label("count"),
        )
        .join(Asset)
        .where(
            and_(
                Asset.organization_id == current_user.organization_id,
                Service.state == ServiceState.OPEN.value,
            )
        )
        .group_by(Service.port, Service.service_name)
        .order_by(func.count(Service.id).desc())
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "port": row.port,
            "service_name": row.service_name or "unknown",
            "count": row.count,
        }
        for row in rows
    ]


# =============================================================================
# Asset Timeline
# =============================================================================
@router.get(
    "/asset-timeline",
    summary="Timeline de assets",
    description="Obtiene el número de assets descubiertos por día",
)
async def get_asset_timeline(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
    days: int = Query(default=30, ge=7, le=90, description="Días de historia"),
) -> list[dict[str, Any]]:
    """
    Timeline de descubrimiento de assets.
    
    Útil para gráficos de línea en el dashboard.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Agrupar por fecha
    stmt = (
        select(
            func.date(Asset.first_seen).label("date"),
            func.count(Asset.id).label("count"),
        )
        .where(
            and_(
                Asset.organization_id == current_user.organization_id,
                Asset.first_seen >= cutoff,
            )
        )
        .group_by(func.date(Asset.first_seen))
        .order_by(func.date(Asset.first_seen).asc())
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "date": str(row.date),
            "count": row.count,
        }
        for row in rows
    ]


# =============================================================================
# Vulnerability Trend
# =============================================================================
@router.get(
    "/vulnerability-trend",
    summary="Tendencia de vulnerabilidades",
    description="Obtiene la tendencia de vulnerabilidades por severidad",
)
async def get_vulnerability_trend(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentActiveUser,
) -> dict[str, Any]:
    """
    Tendencia de vulnerabilidades por severidad.
    
    Muestra el total actual y el cambio respecto a la semana anterior.
    """
    org_id = current_user.organization_id
    
    # Totales actuales
    current_query = select(
        func.sum(Asset.vuln_critical_count).label("critical"),
        func.sum(Asset.vuln_high_count).label("high"),
        func.sum(Asset.vuln_medium_count).label("medium"),
        func.sum(Asset.vuln_low_count).label("low"),
    ).where(Asset.organization_id == org_id)
    
    current_result = await db.execute(current_query)
    current = current_result.one()
    
    return {
        "current": {
            "critical": int(current.critical or 0),
            "high": int(current.high or 0),
            "medium": int(current.medium or 0),
            "low": int(current.low or 0),
        },
        "severity_distribution": [
            {"severity": "critical", "count": int(current.critical or 0), "color": "#dc2626"},
            {"severity": "high", "count": int(current.high or 0), "color": "#ea580c"},
            {"severity": "medium", "count": int(current.medium or 0), "color": "#ca8a04"},
            {"severity": "low", "count": int(current.low or 0), "color": "#16a34a"},
        ],
    }
