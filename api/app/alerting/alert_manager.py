"""
Alert management system for SentinelWatch SIEM.
Handles creation and storage of structured alerts.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.models.database import Alert, LogEntry
from backend.app.utils.helpers import generate_alert_id


class AlertManager:
    """
    Manages alert creation and storage.
    Creates structured alerts with unique IDs, severity levels, and context.
    """
    
    def create_alert(
        self,
        rule_name: str,
        severity: str,
        description: str,
        context: Dict,
        db: Session,
        log_entry: Optional[LogEntry] = None,
        source_ip: Optional[str] = None,
        username: Optional[str] = None
    ) -> Alert:
        """
        Create and store a new alert.
        
        Args:
            rule_name: Name of the detection rule that triggered
            severity: Alert severity (Low, Medium, High, Critical)
            description: Human-readable alert description
            context: Additional context data (dict)
            db: Database session
            log_entry: Optional related log entry
            source_ip: Source IP address
            username: Username associated with alert
            
        Returns:
            Created Alert object
        """
        # Extract IP and username from log_entry if not provided
        if log_entry:
            source_ip = source_ip or log_entry.source_ip
            username = username or log_entry.username
            log_entry_id = log_entry.id
        else:
            log_entry_id = None
        
        # Create alert
        alert = Alert(
            alert_id=generate_alert_id(),
            rule_name=rule_name,
            severity=severity,
            description=description,
            context=json.dumps(context) if context else None,
            source_ip=source_ip,
            username=username,
            log_entry_id=log_entry_id,
            triggered_at=datetime.utcnow(),
            acknowledged=False,
            resolved=False
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        return alert
    
    def get_alerts(
        self,
        db: Session,
        severity: Optional[str] = None,
        rule_name: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        """
        Retrieve alerts with optional filtering.
        
        Args:
            db: Database session
            severity: Filter by severity
            rule_name: Filter by rule name
            resolved: Filter by resolved status
            limit: Maximum number of alerts to return
            offset: Offset for pagination
            
        Returns:
            List of Alert objects
        """
        query = db.query(Alert)
        
        if severity:
            query = query.filter(Alert.severity == severity)
        if rule_name:
            query = query.filter(Alert.rule_name == rule_name)
        if resolved is not None:
            query = query.filter(Alert.resolved == resolved)
        
        return query.order_by(Alert.triggered_at.desc()).offset(offset).limit(limit).all()
    
    def get_alert_statistics(self, db: Session) -> Dict[str, int]:
        """
        Get alert statistics by severity.
        
        Returns:
            Dict with severity counts
        """
        stats = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
            "total": 0
        }
        
        # Count by severity (only unresolved)
        from sqlalchemy import func
        results = db.query(
            Alert.severity,
            func.count(Alert.id).label('count')
        ).filter(
            Alert.resolved == False
        ).group_by(Alert.severity).all()
        
        for severity, count in results:
            if severity in stats:
                stats[severity] = count
                stats["total"] += count
        
        return stats
    
    def acknowledge_alert(self, alert_id: str, db: Session, analyst: str = None) -> Optional[Alert]:
        """Acknowledge an alert."""
        from datetime import datetime
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = analyst or "System"
            alert.acknowledged_at = datetime.utcnow()
            db.commit()
            db.refresh(alert)
        return alert
    
    def resolve_alert(self, alert_id: str, db: Session, analyst: str = None) -> Optional[Alert]:
        """Resolve an alert."""
        from datetime import datetime
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if alert:
            alert.resolved = True
            alert.acknowledged = True
            alert.resolved_by = analyst or "System"
            alert.resolved_at = datetime.utcnow()
            if not alert.acknowledged_at:
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = analyst or "System"
            db.commit()
            db.refresh(alert)
        return alert


# Global alert manager instance
alert_manager = AlertManager()



