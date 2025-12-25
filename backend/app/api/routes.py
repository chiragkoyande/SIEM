"""
FastAPI routes for SentinelWatch SIEM.
Provides REST API endpoints for log ingestion and dashboard data.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
import csv
import io
import json

from backend.app.models.database import get_db, LogEntry, Alert
from backend.app.ingestion.ingestion_service import ingestion_service
from backend.app.alerting.alert_manager import alert_manager

router = APIRouter()


# Pydantic models for request/response
class LogEntryRequest(BaseModel):
    """Request model for single log entry."""
    timestamp: Optional[str] = None
    source_ip: str
    username: Optional[str] = None
    event_type: str = "authentication"
    status: str
    raw_log: Optional[str] = None


class LogBulkRequest(BaseModel):
    """Request model for bulk log ingestion."""
    logs: List[LogEntryRequest]


class AlertResponse(BaseModel):
    """Response model for alerts."""
    alert_id: str
    rule_name: str
    severity: str
    description: str
    context: Optional[dict]
    source_ip: Optional[str]
    username: Optional[str]
    triggered_at: datetime
    acknowledged: bool
    resolved: bool
    
    class Config:
        from_attributes = True


class DashboardStatsResponse(BaseModel):
    """Response model for dashboard statistics."""
    total_logs: int
    alerts_by_severity: dict
    recent_alerts: List[AlertResponse]
    total_alerts: int


@router.post("/api/logs/single")
async def ingest_single_log(
    log_data: LogEntryRequest,
    db: Session = Depends(get_db)
):
    """
    Ingest a single log entry via REST API.
    """
    try:
        result = ingestion_service.ingest_single_log(
            log_data.dict(),
            db
        )
        return JSONResponse(content={
            "status": "success",
            "message": "Log ingested successfully",
            "data": result
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/logs/bulk")
async def ingest_bulk_logs(
    log_data: LogBulkRequest,
    db: Session = Depends(get_db)
):
    """
    Ingest multiple log entries via REST API.
    """
    try:
        log_lines = []
        for log in log_data.logs:
            # Convert log to string format
            log_line = f"{log.timestamp or datetime.utcnow().isoformat()} {log.source_ip} {log.username or 'unknown'} {log.event_type} {log.status}"
            if log.raw_log:
                log_line += f" {log.raw_log}"
            log_lines.append(log_line)
        
        result = ingestion_service.ingest_logs_from_text(log_lines, db=db)
        return JSONResponse(content={
            "status": "success",
            "message": f"{result['ingested']} logs ingested successfully",
            "data": result
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/logs/upload")
async def upload_log_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and ingest a log file.
    """
    try:
        # Save uploaded file temporarily
        with NamedTemporaryFile(delete=False, suffix=".log") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Ingest logs from file
            result = ingestion_service.ingest_logs_from_file(temp_path, db)
            return JSONResponse(content={
                "status": "success",
                "message": f"File uploaded and processed successfully",
                "data": result
            })
        finally:
            # Clean up temporary file
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    severity: Optional[str] = None,
    limit: int = 50
):
    """
    Get dashboard statistics including total logs, alerts by severity, and recent alerts.
    """
    try:
        # Total logs count
        total_logs = db.query(func.count(LogEntry.id)).scalar()
        
        # Alert statistics
        alerts_by_severity = alert_manager.get_alert_statistics(db)
        
        # Recent alerts (unresolved)
        recent_alerts = alert_manager.get_alerts(
            db,
            severity=severity,
            resolved=False,
            limit=limit
        )
        
        # Convert alerts to response format
        recent_alerts_response = []
        for alert in recent_alerts:
            context = None
            if alert.context:
                try:
                    context = json.loads(alert.context)
                except:
                    context = {}
            
            recent_alerts_response.append(AlertResponse(
                alert_id=alert.alert_id,
                rule_name=alert.rule_name,
                severity=alert.severity,
                description=alert.description,
                context=context,
                source_ip=alert.source_ip,
                username=alert.username,
                triggered_at=alert.triggered_at,
                acknowledged=alert.acknowledged,
                resolved=alert.resolved
            ))
        
        return DashboardStatsResponse(
            total_logs=total_logs,
            alerts_by_severity=alerts_by_severity,
            recent_alerts=recent_alerts_response,
            total_alerts=alerts_by_severity["total"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/alerts")
async def get_alerts(
    db: Session = Depends(get_db),
    severity: Optional[str] = None,
    rule_name: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get alerts with filtering options.
    """
    try:
        alerts = alert_manager.get_alerts(
            db,
            severity=severity,
            rule_name=rule_name,
            resolved=resolved,
            limit=limit,
            offset=offset
        )
        
        alerts_response = []
        for alert in alerts:
            context = None
            if alert.context:
                try:
                    context = json.loads(alert.context)
                except:
                    context = {}
            
            alerts_response.append(AlertResponse(
                alert_id=alert.alert_id,
                rule_name=alert.rule_name,
                severity=alert.severity,
                description=alert.description,
                context=context,
                source_ip=alert.source_ip,
                username=alert.username,
                triggered_at=alert.triggered_at,
                acknowledged=alert.acknowledged,
                resolved=alert.resolved
            ))
        
        return {"alerts": alerts_response, "count": len(alerts_response)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/alerts/export")
async def export_alerts(
    db: Session = Depends(get_db),
    severity: Optional[str] = None,
    rule_name: Optional[str] = None,
    resolved: Optional[bool] = None,
    format: str = Query("csv", regex="^(csv|json)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Export alerts to CSV or JSON format.
    Useful for SOC reporting and analysis.
    """
    try:
        # Parse date filters
        start_datetime = None
        end_datetime = None
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Build query with date filters
        query = db.query(Alert)
        if severity:
            query = query.filter(Alert.severity == severity)
        if rule_name:
            query = query.filter(Alert.rule_name == rule_name)
        if resolved is not None:
            query = query.filter(Alert.resolved == resolved)
        if start_datetime:
            query = query.filter(Alert.triggered_at >= start_datetime)
        if end_datetime:
            query = query.filter(Alert.triggered_at <= end_datetime)
        
        alerts = query.order_by(Alert.triggered_at.desc()).all()
        
        if format == "csv":
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Alert ID", "Rule Name", "Severity", "Description", 
                "Source IP", "Username", "Triggered At", "Acknowledged", "Resolved"
            ])
            
            for alert in alerts:
                writer.writerow([
                    alert.alert_id,
                    alert.rule_name,
                    alert.severity,
                    alert.description,
                    alert.source_ip or "",
                    alert.username or "",
                    alert.triggered_at.isoformat(),
                    alert.acknowledged,
                    alert.resolved
                ])
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=alerts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        
        else:  # JSON
            alerts_data = []
            for alert in alerts:
                context = None
                if alert.context:
                    try:
                        context = json.loads(alert.context)
                    except:
                        context = {}
                
                alerts_data.append({
                    "alert_id": alert.alert_id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity,
                    "description": alert.description,
                    "context": context,
                    "source_ip": alert.source_ip,
                    "username": alert.username,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "acknowledged": alert.acknowledged,
                    "resolved": alert.resolved
                })
            
            return Response(
                content=json.dumps(alerts_data, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=alerts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/alerts/{alert_id}")
async def get_alert_detail(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific alert."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    context = None
    if alert.context:
        try:
            context = json.loads(alert.context)
        except:
            context = {}
    
    # Get related log entry if exists
    log_entry = None
    if alert.log_entry_id:
        log_entry = db.query(LogEntry).filter(LogEntry.id == alert.log_entry_id).first()
    
    return {
        "alert_id": alert.alert_id,
        "rule_name": alert.rule_name,
        "severity": alert.severity,
        "description": alert.description,
        "context": context,
        "source_ip": alert.source_ip,
        "username": alert.username,
        "triggered_at": alert.triggered_at.isoformat(),
        "acknowledged": alert.acknowledged,
        "acknowledged_by": alert.acknowledged_by,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "resolved": alert.resolved,
        "resolved_by": alert.resolved_by,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "notes": alert.notes,
        "log_entry": {
            "id": log_entry.id,
            "timestamp": log_entry.timestamp.isoformat(),
            "raw_log": log_entry.raw_log,
            "country_code": log_entry.country_code
        } if log_entry else None
    }


@router.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    analyst: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Acknowledge an alert."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.acknowledged = True
    alert.acknowledged_by = analyst or "System"
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    
    return {"status": "success", "message": "Alert acknowledged"}


@router.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    analyst: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Resolve an alert."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.resolved = True
    alert.acknowledged = True
    alert.resolved_by = analyst or "System"
    alert.resolved_at = datetime.utcnow()
    if not alert.acknowledged_at:
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = analyst or "System"
    db.commit()
    
    return {"status": "success", "message": "Alert resolved"}


@router.put("/api/alerts/{alert_id}/notes")
async def update_alert_notes(
    alert_id: str,
    notes: str = Query(...),
    db: Session = Depends(get_db)
):
    """Add or update notes for an alert."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.notes = notes
    db.commit()
    
    return {"status": "success", "message": "Notes updated"}


@router.get("/api/logs")
async def search_logs(
    db: Session = Depends(get_db),
    source_ip: Optional[str] = None,
    username: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Search and filter log entries.
    Essential for SOC investigation workflows.
    """
    try:
        query = db.query(LogEntry)
        
        # Apply filters
        if source_ip:
            query = query.filter(LogEntry.source_ip == source_ip)
        if username:
            query = query.filter(LogEntry.username == username)
        if event_type:
            query = query.filter(LogEntry.event_type == event_type)
        if status:
            query = query.filter(LogEntry.status == status)
        
        # Date range filter
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(LogEntry.timestamp >= start_datetime)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(LogEntry.timestamp <= end_datetime)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        logs = query.order_by(LogEntry.timestamp.desc()).offset(offset).limit(limit).all()
        
        logs_data = []
        for log in logs:
            logs_data.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "source_ip": log.source_ip,
                "username": log.username,
                "event_type": log.event_type,
                "status": log.status,
                "country_code": log.country_code,
                "raw_log": log.raw_log,
                "source_file": log.source_file
            })
        
        return {
            "logs": logs_data,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/logs/{log_id}")
async def get_log_detail(
    log_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific log entry."""
    log = db.query(LogEntry).filter(LogEntry.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    
    return {
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "source_ip": log.source_ip,
        "username": log.username,
        "event_type": log.event_type,
        "status": log.status,
        "country_code": log.country_code,
        "latitude": log.latitude,
        "longitude": log.longitude,
        "raw_log": log.raw_log,
        "source_file": log.source_file,
        "created_at": log.created_at.isoformat()
    }
