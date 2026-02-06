# =============================================================================
# NESTSECURE - API de Reports
# =============================================================================
"""
Endpoints para gestión de reportes.

Incluye:
- GET /reports: Listar reportes
- POST /reports/generate: Generar nuevo reporte
- GET /reports/{id}: Obtener detalle de reporte
- GET /reports/{id}/download: Descargar reporte
- DELETE /reports/{id}: Eliminar reporte
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentActiveUser, get_db
from app.models.report import Report, ReportFormat, ReportStatus, ReportType
from app.schemas.report import (
    GenerateReportRequest,
    GenerateReportResponse,
    ReportListResponse,
    ReportRead,
    ReportSummary,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================
async def get_report_or_404(
    db: AsyncSession,
    report_id: str,
    organization_id: str,
) -> Report:
    """
    Obtiene un reporte por ID o lanza 404.
    """
    stmt = select(Report).where(
        Report.id == report_id,
        Report.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Reporte no encontrado",
        )
    
    return report


# =============================================================================
# Report Generation Service (inline para simplicidad)
# =============================================================================
async def generate_report_task(
    report_id: str,
    organization_id: str,
):
    """
    Tarea de background para generar el reporte.
    Crea su propia sesión de base de datos para evitar problemas con sesiones cerradas.
    """
    from app.models.vulnerability import Vulnerability
    from app.models.asset import Asset
    from app.models.scan import Scan
    from app.db.session import get_session_maker
    import json
    
    # Crear nueva sesión para la tarea de background
    session_factory = await get_session_maker()
    async with session_factory() as db:
        # Obtener reporte
        stmt = select(Report).where(Report.id == report_id)
        result = await db.execute(stmt)
        report = result.scalar_one_or_none()
        
        if not report:
            logger.error(f"Report {report_id} not found for generation")
            return
        
        try:
            report.mark_generating()
            await db.commit()
            
            # Preparar datos según tipo de reporte
            data = {}
            
            # Para ejecutivo, cargar TODO
            if report.report_type == ReportType.EXECUTIVE.value:
                # Vulnerabilidades
                vuln_stmt = select(Vulnerability).where(
                    Vulnerability.organization_id == organization_id
                ).order_by(desc(Vulnerability.cvss_score))
                
                vuln_result = await db.execute(vuln_stmt)
                vulns = vuln_result.scalars().all()
                
                data["vulnerabilities"] = [
                    {
                        "id": str(v.id),
                        "name": v.name,
                        "severity": v.severity,
                        "status": v.status,
                        "cvss_score": v.cvss_score,
                        "cve_id": v.cve_id,
                        "asset_id": str(v.asset_id),
                        "description": v.description,
                    }
                    for v in vulns
                ]
                
                data["stats"] = {
                    "total": len(vulns),
                    "critical": sum(1 for v in vulns if v.severity == "critical"),
                    "high": sum(1 for v in vulns if v.severity == "high"),
                    "medium": sum(1 for v in vulns if v.severity == "medium"),
                    "low": sum(1 for v in vulns if v.severity == "low"),
                    "open": sum(1 for v in vulns if v.status == "open"),
                    "fixed": sum(1 for v in vulns if v.status == "fixed"),
                }
                
                # Assets
                asset_stmt = select(Asset).where(
                    Asset.organization_id == organization_id
                )
                asset_result = await db.execute(asset_stmt)
                assets = asset_result.scalars().all()
                
                data["assets"] = [
                    {
                        "id": str(a.id),
                        "ip_address": a.ip_address,
                        "hostname": a.hostname,
                        "asset_type": a.asset_type,
                        "criticality": a.criticality,
                        "status": a.status,
                    }
                    for a in assets
                ]
                
                data["asset_stats"] = {
                    "total": len(assets),
                }
                
                # Scans
                scan_stmt = select(Scan).where(
                    Scan.organization_id == organization_id
                ).order_by(desc(Scan.created_at)).limit(100)
                
                scan_result = await db.execute(scan_stmt)
                scans = scan_result.scalars().all()
                
                data["scans"] = [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "scan_type": s.scan_type,
                        "status": s.status,
                        "hosts_discovered": s.hosts_discovered,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in scans
                ]
            
            elif report.report_type in [ReportType.VULNERABILITY.value, ReportType.TECHNICAL.value]:
                # Obtener vulnerabilidades
                vuln_stmt = select(Vulnerability).where(
                    Vulnerability.organization_id == organization_id
                ).order_by(desc(Vulnerability.cvss_score))
                
                vuln_result = await db.execute(vuln_stmt)
                vulns = vuln_result.scalars().all()
                
                data["vulnerabilities"] = [
                    {
                        "id": str(v.id),
                        "name": v.name,
                        "severity": v.severity,
                        "status": v.status,
                        "cvss_score": v.cvss_score,
                        "cve_id": v.cve_id,
                        "asset_id": str(v.asset_id),
                        "description": v.description,
                    }
                    for v in vulns
                ]
                
                # Estadísticas
                data["stats"] = {
                    "total": len(vulns),
                    "critical": sum(1 for v in vulns if v.severity == "critical"),
                    "high": sum(1 for v in vulns if v.severity == "high"),
                    "medium": sum(1 for v in vulns if v.severity == "medium"),
                    "low": sum(1 for v in vulns if v.severity == "low"),
                    "open": sum(1 for v in vulns if v.status == "open"),
                    "fixed": sum(1 for v in vulns if v.status == "fixed"),
                }
            
            elif report.report_type == ReportType.ASSET_INVENTORY.value:
                # Obtener assets
                asset_stmt = select(Asset).where(
                    Asset.organization_id == organization_id
                )
                asset_result = await db.execute(asset_stmt)
                assets = asset_result.scalars().all()
                
                data["assets"] = [
                    {
                        "id": str(a.id),
                        "ip_address": a.ip_address,
                        "hostname": a.hostname,
                        "asset_type": a.asset_type,
                        "criticality": a.criticality,
                        "status": a.status,
                    }
                    for a in assets
                ]
                
                data["asset_stats"] = {
                    "total": len(assets),
                }
            
            elif report.report_type == ReportType.SCAN_SUMMARY.value:
                # Obtener scans
                scan_stmt = select(Scan).where(
                    Scan.organization_id == organization_id
                ).order_by(desc(Scan.created_at)).limit(100)
                
                scan_result = await db.execute(scan_stmt)
                scans = scan_result.scalars().all()
                
                data["scans"] = [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "scan_type": s.scan_type,
                        "status": s.status,
                        "hosts_discovered": s.hosts_discovered,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in scans
                ]
            
            # Generar archivo
            reports_dir = "/tmp/nestsecure_reports"
            os.makedirs(reports_dir, exist_ok=True)
            
            file_ext = report.format
            filename = f"{report.id}.{file_ext}"
            file_path = os.path.join(reports_dir, filename)
            
            if report.format == ReportFormat.JSON.value:
                # Generar JSON
                with open(file_path, "w") as f:
                    json.dump({
                        "report": {
                            "id": str(report.id),
                            "name": report.name,
                            "type": report.report_type,
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                        },
                        "data": data,
                    }, f, indent=2, default=str)
            
            elif report.format == ReportFormat.CSV.value:
                # Generar CSV simple de vulnerabilidades
                import csv
                with open(file_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Name", "Severity", "Status", "CVSS", "CVE"])
                    for v in data.get("vulnerabilities", []):
                        writer.writerow([
                            v["id"], v["name"], v["severity"], 
                            v["status"], v["cvss_score"], v["cve_id"]
                        ])
            
            elif report.format == ReportFormat.XLSX.value:
                # Generar Excel básico con openpyxl si está disponible
                try:
                    from openpyxl import Workbook
                    wb = Workbook()
                    ws = wb.active
                    ws.title = "Vulnerabilities"
                    
                    # Headers
                    headers = ["ID", "Name", "Severity", "Status", "CVSS", "CVE", "Description"]
                    ws.append(headers)
                    
                    # Datos
                    for v in data.get("vulnerabilities", []):
                        ws.append([
                            v["id"], v["name"], v["severity"],
                            v["status"], v["cvss_score"], v["cve_id"],
                            v.get("description", "")[:100]
                        ])
                    
                    wb.save(file_path)
                except ImportError:
                    # Fallback a JSON si no hay openpyxl
                    file_path = file_path.replace(".xlsx", ".json")
                    with open(file_path, "w") as f:
                        json.dump(data, f, indent=2, default=str)
            
            elif report.format == ReportFormat.PDF.value:
                # Generar PDF básico con reportlab si está disponible
                try:
                    from reportlab.lib.pagesizes import letter
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                    from reportlab.lib.styles import getSampleStyleSheet
                    from reportlab.lib import colors
                    
                    doc = SimpleDocTemplate(file_path, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    # Título
                    story.append(Paragraph(f"<b>{report.name}</b>", styles["Title"]))
                    story.append(Spacer(1, 12))
                    story.append(Paragraph(f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
                    story.append(Spacer(1, 24))
                    
                    # Estadísticas
                    if "stats" in data:
                        stats = data["stats"]
                        story.append(Paragraph("<b>Resumen de Vulnerabilidades</b>", styles["Heading2"]))
                        story.append(Spacer(1, 12))
                        
                        stats_data = [
                            ["Total", "Críticas", "Altas", "Medias", "Bajas"],
                            [stats["total"], stats["critical"], stats["high"], stats["medium"], stats["low"]]
                        ]
                        t = Table(stats_data)
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        story.append(t)
                        story.append(Spacer(1, 24))
                    
                    # Assets para reporte ejecutivo
                    if "assets" in data and data["assets"]:
                        story.append(Paragraph("<b>Inventario de Assets</b>", styles["Heading2"]))
                        story.append(Spacer(1, 12))
                        story.append(Paragraph(f"Total de assets: {len(data['assets'])}", styles["Normal"]))
                        story.append(Spacer(1, 12))
                    
                    # Lista de vulnerabilidades (top 20)
                    if "vulnerabilities" in data and data["vulnerabilities"]:
                        story.append(Paragraph("<b>Top Vulnerabilidades</b>", styles["Heading2"]))
                        story.append(Spacer(1, 12))
                        
                        vuln_data = [["Nombre", "Severidad", "CVSS", "CVE"]]
                        for v in data["vulnerabilities"][:20]:
                            vuln_data.append([
                                v["name"][:40] + "..." if len(v["name"]) > 40 else v["name"],
                                v["severity"].upper(),
                                str(v["cvss_score"] or "-"),
                                v["cve_id"] or "-"
                            ])
                        
                        t = Table(vuln_data, colWidths=[200, 80, 60, 100])
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                        ]))
                        story.append(t)
                    
                    doc.build(story)
                    
                except ImportError:
                    # Fallback a JSON si no hay reportlab
                    file_path = file_path.replace(".pdf", ".json")
                    with open(file_path, "w") as f:
                        json.dump(data, f, indent=2, default=str)
            
            # Obtener tamaño del archivo
            file_size = os.path.getsize(file_path)
            
            # Marcar como completado
            report.mark_completed(file_path, file_size)
            await db.commit()
            
            logger.info(f"Report {report_id} generated successfully: {file_path}")
            
        except Exception as e:
            logger.error(f"Error generating report {report_id}: {e}")
            report.mark_failed(str(e))
            await db.commit()


# =============================================================================
# Endpoints
# =============================================================================
@router.get(
    "",
    response_model=ReportListResponse,
    summary="Listar reportes",
)
async def list_reports(
    report_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActiveUser = None,
):
    """
    Listar reportes de la organización.
    """
    # Base query
    query = select(Report).where(
        Report.organization_id == current_user.organization_id
    )
    
    # Filtros
    if report_type:
        query = query.where(Report.report_type == report_type)
    if status:
        query = query.where(Report.status == status)
    
    # Ordenar por más reciente
    query = query.order_by(desc(Report.created_at))
    
    # Contar total
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginar
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return ReportListResponse(
        reports=[
            ReportSummary(
                id=str(r.id),
                name=r.name,
                report_type=r.report_type,
                format=r.format,
                status=r.status,
                created_at=r.created_at,
                completed_at=r.completed_at,
                is_downloadable=r.is_downloadable,
            )
            for r in reports
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/generate",
    response_model=GenerateReportResponse,
    summary="Generar nuevo reporte",
)
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActiveUser = None,
):
    """
    Solicita la generación de un nuevo reporte.
    
    El reporte se genera en background y su estado puede consultarse
    con GET /reports/{id}.
    """
    # Validar tipo y formato
    valid_types = [t.value for t in ReportType]
    if request.report_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Valores permitidos: {valid_types}"
        )
    
    valid_formats = [f.value for f in ReportFormat]
    if request.format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido. Valores permitidos: {valid_formats}"
        )
    
    # Crear registro de reporte
    report = Report(
        id=str(uuid4()),
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        name=request.name,
        report_type=request.report_type,
        format=request.format,
        description=request.description,
        status=ReportStatus.PENDING.value,
        parameters={
            "date_from": request.date_from.isoformat() if request.date_from else None,
            "date_to": request.date_to.isoformat() if request.date_to else None,
            "severity_filter": request.severity_filter,
            "status_filter": request.status_filter,
            "asset_ids": request.asset_ids,
        },
    )
    
    db.add(report)
    await db.commit()
    await db.refresh(report)
    
    # Ejecutar generación en background
    # Nota: En producción usaríamos Celery, pero para simplicidad usamos BackgroundTasks
    background_tasks.add_task(
        generate_report_task,
        str(report.id),
        current_user.organization_id,
    )
    
    return GenerateReportResponse(
        id=str(report.id),
        status=report.status,
        message=f"Reporte '{request.name}' en cola de generación",
    )


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    summary="Obtener detalle de reporte",
)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActiveUser = None,
):
    """
    Obtiene el detalle de un reporte.
    """
    report = await get_report_or_404(db, report_id, current_user.organization_id)
    
    return ReportRead(
        id=str(report.id),
        name=report.name,
        report_type=report.report_type,
        format=report.format,
        status=report.status,
        description=report.description,
        file_size=report.file_size,
        parameters=report.parameters,
        error_message=report.error_message,
        completed_at=report.completed_at,
        created_by_id=str(report.created_by_id) if report.created_by_id else None,
        is_downloadable=report.is_downloadable,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get(
    "/{report_id}/download",
    summary="Descargar reporte",
)
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActiveUser = None,
):
    """
    Descarga el archivo del reporte.
    """
    report = await get_report_or_404(db, report_id, current_user.organization_id)
    
    if not report.is_downloadable:
        raise HTTPException(
            status_code=400,
            detail="El reporte no está disponible para descarga"
        )
    
    if not os.path.exists(report.file_path):
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado"
        )
    
    # Determinar media type
    media_types = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
        "csv": "text/csv",
    }
    media_type = media_types.get(report.format, "application/octet-stream")
    
    # Nombre del archivo para descarga
    safe_name = report.name.replace(" ", "_").replace("/", "_")
    filename = f"{safe_name}.{report.format}"
    
    return FileResponse(
        path=report.file_path,
        media_type=media_type,
        filename=filename,
    )


@router.delete(
    "/{report_id}",
    summary="Eliminar reporte",
)
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActiveUser = None,
):
    """
    Elimina un reporte y su archivo asociado.
    """
    report = await get_report_or_404(db, report_id, current_user.organization_id)
    
    # Eliminar archivo si existe
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except OSError:
            pass
    
    # Eliminar registro
    await db.delete(report)
    await db.commit()
    
    return {"message": "Reporte eliminado", "deleted_id": report_id}
