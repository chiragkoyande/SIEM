"""
Log ingestion service for SentinelWatch SIEM.
Handles ingestion via REST API and file uploads.
"""

from typing import List, Dict
from sqlalchemy.orm import Session
from tempfile import NamedTemporaryFile
import os

from backend.app.models.database import LogEntry
from backend.app.parsing.log_parser import log_parser
from backend.app.detection.rules import detection_engine
from backend.app.alerting.alert_manager import alert_manager


class IngestionService:
    """
    Service for ingesting logs from various sources.
    Handles parsing, normalization, storage, and detection.
    """
    
    def ingest_logs_from_text(
        self,
        log_lines: List[str],
        source_file: str = None,
        db: Session = None
    ) -> Dict:
        """
        Ingest logs from text lines.
        
        Args:
            log_lines: List of log line strings
            source_file: Optional source file name
            db: Database session
            
        Returns:
            Dict with ingestion statistics
        """
        parsed_entries = []
        alerts_generated = 0
        
        for line in log_lines:
            if not line.strip():
                continue
            
            # Parse log line
            log_entry = log_parser.parse_line(line, source_file)
            if not log_entry:
                continue
            
            # Store in database
            db.add(log_entry)
            db.flush()  # Flush to get ID
            
            # Run detection rules
            detected_alerts = detection_engine.analyze(log_entry, db)
            
            # Create alerts
            for alert_data in detected_alerts:
                alert_manager.create_alert(
                    rule_name=alert_data["rule_name"],
                    severity=alert_data["severity"],
                    description=alert_data["description"],
                    context=alert_data["context"],
                    db=db,
                    log_entry=log_entry
                )
                alerts_generated += 1
            
            parsed_entries.append(log_entry)
        
        # Commit all entries
        db.commit()
        
        return {
            "ingested": len(parsed_entries),
            "alerts_generated": alerts_generated
        }
    
    def ingest_logs_from_file(
        self,
        file_path: str,
        db: Session
    ) -> Dict:
        """
        Ingest logs from uploaded file.
        
        Args:
            file_path: Path to log file
            db: Database session
            
        Returns:
            Dict with ingestion statistics
        """
        source_file = os.path.basename(file_path)
        parsed_entries = log_parser.parse_file(file_path)
        alerts_generated = 0
        
        for log_entry in parsed_entries:
            # Store in database
            db.add(log_entry)
            db.flush()
            
            # Run detection rules
            detected_alerts = detection_engine.analyze(log_entry, db)
            
            # Create alerts
            for alert_data in detected_alerts:
                alert_manager.create_alert(
                    rule_name=alert_data["rule_name"],
                    severity=alert_data["severity"],
                    description=alert_data["description"],
                    context=alert_data["context"],
                    db=db,
                    log_entry=log_entry
                )
                alerts_generated += 1
        
        # Commit all entries
        db.commit()
        
        return {
            "ingested": len(parsed_entries),
            "alerts_generated": alerts_generated,
            "source_file": source_file
        }
    
    def ingest_single_log(
        self,
        log_data: Dict,
        db: Session
    ) -> Dict:
        """
        Ingest a single log entry from API.
        
        Args:
            log_data: Dict with log fields (timestamp, source_ip, username, event_type, status)
            db: Database session
            
        Returns:
            Dict with ingestion result
        """
        from datetime import datetime
        from backend.app.utils.helpers import parse_timestamp
        from backend.app.utils.geolocation import geolocation_service
        
        # Parse timestamp
        timestamp = log_data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = parse_timestamp(timestamp)
        if not timestamp or not isinstance(timestamp, datetime):
            timestamp = datetime.utcnow()
        
        # Get geolocation
        source_ip = log_data.get("source_ip", "")
        location_data = None
        if source_ip:
            location_data = geolocation_service.get_location(source_ip)
        
        # Create log entry
        log_entry = LogEntry(
            timestamp=timestamp,
            source_ip=source_ip,
            username=log_data.get("username", ""),
            event_type=log_data.get("event_type", "authentication"),
            status=log_data.get("status", "unknown"),
            raw_log=log_data.get("raw_log", ""),
            country_code=location_data.get("country_code") if location_data else None,
            latitude=location_data.get("latitude") if location_data else None,
            longitude=location_data.get("longitude") if location_data else None
        )
        
        # Store in database
        db.add(log_entry)
        db.flush()
        
        # Run detection rules
        detected_alerts = detection_engine.analyze(log_entry, db)
        alerts_generated = len(detected_alerts)
        
        # Create alerts
        for alert_data in detected_alerts:
            alert_manager.create_alert(
                rule_name=alert_data["rule_name"],
                severity=alert_data["severity"],
                description=alert_data["description"],
                context=alert_data["context"],
                db=db,
                log_entry=log_entry
            )
        
        # Commit
        db.commit()
        
        return {
            "ingested": 1,
            "alerts_generated": alerts_generated,
            "log_entry_id": log_entry.id
        }


# Global ingestion service instance
ingestion_service = IngestionService()

