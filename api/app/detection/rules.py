"""
Detection rules engine for SentinelWatch SIEM.
Implements rule-based detection using regex and correlation logic.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from backend.app.models.database import LogEntry, Alert
from backend.config.config import settings
from backend.app.utils.helpers import is_business_hours
from backend.app.utils.geolocation import geolocation_service


class DetectionRule:
    """
    Base class for detection rules.
    All rules inherit from this class and implement the check() method.
    """
    
    def __init__(self, rule_name: str, severity: str, description: str):
        self.rule_name = rule_name
        self.severity = severity
        self.description = description
    
    def check(self, log_entry: LogEntry, db: Session) -> Optional[Dict]:
        """
        Check if log entry triggers this rule.
        
        Args:
            log_entry: LogEntry to check
            db: Database session for correlation queries
            
        Returns:
            Dict with alert details if triggered, None otherwise
        """
        raise NotImplementedError("Subclasses must implement check() method")


class BruteForceDetectionRule(DetectionRule):
    """
    Detects brute-force login attempts.
    Triggers when multiple failed login attempts occur from same IP within time window.
    """
    
    def __init__(self):
        super().__init__(
            rule_name="brute_force_login",
            severity="High",
            description="Multiple failed login attempts detected from same IP address"
        )
    
    def check(self, log_entry: LogEntry, db: Session) -> Optional[Dict]:
        """Check for brute-force pattern."""
        # Only check failed login attempts
        if log_entry.status != "failed" or log_entry.event_type != "login":
            return None
        
        if not log_entry.source_ip:
            return None
        
        # Count failed attempts from this IP in the time window
        time_window_start = log_entry.timestamp - timedelta(minutes=settings.brute_force_window_minutes)
        
        failed_count = db.query(func.count(LogEntry.id)).filter(
            and_(
                LogEntry.source_ip == log_entry.source_ip,
                LogEntry.status == "failed",
                LogEntry.event_type == "login",
                LogEntry.timestamp >= time_window_start,
                LogEntry.timestamp <= log_entry.timestamp
            )
        ).scalar()
        
        if failed_count >= settings.brute_force_threshold:
            # Check if alert already exists for this IP in recent time
            recent_alert = db.query(Alert).filter(
                and_(
                    Alert.rule_name == self.rule_name,
                    Alert.source_ip == log_entry.source_ip,
                    Alert.triggered_at >= time_window_start,
                    Alert.resolved == False
                )
            ).first()
            
            if not recent_alert:
                return {
                    "description": f"Brute-force login attempt detected from {log_entry.source_ip}. "
                                 f"{failed_count} failed attempts in {settings.brute_force_window_minutes} minutes.",
                    "context": {
                        "source_ip": log_entry.source_ip,
                        "failed_attempts": failed_count,
                        "time_window_minutes": settings.brute_force_window_minutes,
                        "affected_users": [log_entry.username] if log_entry.username else []
                    }
                }
        
        return None


class ImpossibleTravelDetectionRule(DetectionRule):
    """
    Detects impossible travel based on IP geolocation.
    Triggers when user logs in from two geographically distant locations within short time.
    """
    
    def __init__(self):
        super().__init__(
            rule_name="impossible_travel",
            severity="Critical",
            description="User logged in from geographically distant locations in short time"
        )
        self.max_travel_time_hours = 1  # Maximum realistic travel time
        self.min_distance_km = 1000  # Minimum distance to trigger (km)
    
    def check(self, log_entry: LogEntry, db: Session) -> Optional[Dict]:
        """Check for impossible travel pattern."""
        # Only check successful logins
        if log_entry.status != "success" or log_entry.event_type != "login":
            return None
        
        if not log_entry.username or not log_entry.source_ip:
            return None
        
        # Get geolocation for current login
        current_location = geolocation_service.get_location(log_entry.source_ip)
        if not current_location or not current_location.get('latitude'):
            return None
        
        # Find previous successful login from this user
        time_window_start = log_entry.timestamp - timedelta(hours=self.max_travel_time_hours)
        
        previous_login = db.query(LogEntry).filter(
            and_(
                LogEntry.username == log_entry.username,
                LogEntry.status == "success",
                LogEntry.event_type == "login",
                LogEntry.timestamp >= time_window_start,
                LogEntry.timestamp < log_entry.timestamp,
                LogEntry.source_ip != log_entry.source_ip,
                LogEntry.latitude.isnot(None)
            )
        ).order_by(LogEntry.timestamp.desc()).first()
        
        if previous_login and previous_login.latitude and previous_login.longitude:
            # Calculate distance
            distance = geolocation_service.calculate_distance(
                previous_login.latitude,
                previous_login.longitude,
                current_location['latitude'],
                current_location['longitude']
            )
            
            # Calculate time difference
            time_diff = log_entry.timestamp - previous_login.timestamp
            hours_diff = time_diff.total_seconds() / 3600
            
            # Check if travel is physically impossible
            # Assume maximum realistic travel speed: 800 km/h (commercial aircraft)
            max_realistic_speed = 800  # km/h
            min_required_hours = distance / max_realistic_speed
            
            if distance >= self.min_distance_km and hours_diff < min_required_hours:
                # Check if alert already exists
                recent_alert = db.query(Alert).filter(
                    and_(
                        Alert.rule_name == self.rule_name,
                        Alert.username == log_entry.username,
                        Alert.triggered_at >= time_window_start,
                        Alert.resolved == False
                    )
                ).first()
                
                if not recent_alert:
                    return {
                        "description": f"Impossible travel detected for user {log_entry.username}. "
                                     f"Login from {previous_login.source_ip} ({previous_login.country_code}) "
                                     f"to {log_entry.source_ip} ({current_location.get('country_code')}) "
                                     f"covering {distance:.0f} km in {hours_diff:.2f} hours.",
                        "context": {
                            "username": log_entry.username,
                            "previous_ip": previous_login.source_ip,
                            "previous_location": f"{previous_login.country_code} ({previous_login.latitude}, {previous_login.longitude})",
                            "current_ip": log_entry.source_ip,
                            "current_location": f"{current_location.get('country_code')} ({current_location['latitude']}, {current_location['longitude']})",
                            "distance_km": round(distance, 2),
                            "time_hours": round(hours_diff, 2),
                            "previous_timestamp": previous_login.timestamp.isoformat()
                        }
                    }
        
        return None


class BusinessHoursDetectionRule(DetectionRule):
    """
    Detects logins outside business hours.
    Triggers when successful login occurs outside configured business hours.
    """
    
    def __init__(self):
        super().__init__(
            rule_name="login_outside_business_hours",
            severity="Medium",
            description="Login detected outside normal business hours"
        )
    
    def check(self, log_entry: LogEntry, db: Session) -> Optional[Dict]:
        """Check if login is outside business hours."""
        # Only check successful logins
        if log_entry.status != "success" or log_entry.event_type != "login":
            return None
        
        # Check if outside business hours
        if is_business_hours(log_entry.timestamp, settings.business_hours_start, settings.business_hours_end):
            return None
        
        # Suppress alert if it's a weekend (handled by is_business_hours, but double-check)
        if log_entry.timestamp.weekday() >= 5:
            return None
        
        # Check for recent alert to avoid spam
        time_window_start = log_entry.timestamp - timedelta(hours=1)
        recent_alert = db.query(Alert).filter(
            and_(
                Alert.rule_name == self.rule_name,
                Alert.username == log_entry.username,
                Alert.source_ip == log_entry.source_ip,
                Alert.triggered_at >= time_window_start,
                Alert.resolved == False
            )
        ).first()
        
        if not recent_alert:
            hour = log_entry.timestamp.hour
            return {
                "description": f"Login outside business hours detected for user {log_entry.username} "
                             f"from {log_entry.source_ip} at {log_entry.timestamp.strftime('%H:%M')} "
                             f"(Business hours: {settings.business_hours_start}:00 - {settings.business_hours_end}:00).",
                "context": {
                    "username": log_entry.username,
                    "source_ip": log_entry.source_ip,
                    "login_time": log_entry.timestamp.isoformat(),
                    "business_hours": f"{settings.business_hours_start}:00 - {settings.business_hours_end}:00",
                    "day_of_week": log_entry.timestamp.strftime("%A")
                }
            }
        
        return None


class PrivilegeEscalationDetectionRule(DetectionRule):
    """
    Detects privilege escalation attempts.
    Triggers on events indicating privilege changes or admin access.
    """
    
    def __init__(self):
        super().__init__(
            rule_name="privilege_escalation",
            severity="High",
            description="Privilege escalation or admin access attempt detected"
        )
        
        # Keywords indicating privilege escalation
        self.escalation_keywords = [
            'sudo', 'su', 'admin', 'root', 'elevate', 'privilege',
            'runas', 'impersonate', 'escalate'
        ]
    
    def check(self, log_entry: LogEntry, db: Session) -> Optional[Dict]:
        """Check for privilege escalation patterns."""
        # Check event type
        if log_entry.event_type in ['privilege_escalation', 'admin_access', 'sudo', 'su']:
            return {
                "description": f"Privilege escalation attempt detected for user {log_entry.username} "
                             f"from {log_entry.source_ip}",
                "context": {
                    "username": log_entry.username,
                    "source_ip": log_entry.source_ip,
                    "event_type": log_entry.event_type,
                    "status": log_entry.status,
                    "raw_log": log_entry.raw_log[:500] if log_entry.raw_log else None
                }
            }
        
        # Check raw log for keywords
        if log_entry.raw_log:
            log_lower = log_entry.raw_log.lower()
            for keyword in self.escalation_keywords:
                if keyword in log_lower:
                    # Check for recent alert
                    time_window_start = log_entry.timestamp - timedelta(minutes=30)
                    recent_alert = db.query(Alert).filter(
                        and_(
                            Alert.rule_name == self.rule_name,
                            Alert.username == log_entry.username,
                            Alert.triggered_at >= time_window_start,
                            Alert.resolved == False
                        )
                    ).first()
                    
                    if not recent_alert:
                        return {
                            "description": f"Potential privilege escalation detected for user {log_entry.username} "
                                         f"from {log_entry.source_ip}. Keyword: {keyword}",
                            "context": {
                                "username": log_entry.username,
                                "source_ip": log_entry.source_ip,
                                "keyword": keyword,
                                "event_type": log_entry.event_type,
                                "status": log_entry.status,
                                "raw_log": log_entry.raw_log[:500]
                            }
                        }
        
        return None


class BlacklistIPDetectionRule(DetectionRule):
    """
    Detects activity from blacklisted IP addresses.
    Uses static blacklist from configuration.
    """
    
    def __init__(self):
        super().__init__(
            rule_name="blacklisted_ip",
            severity="Critical",
            description="Activity detected from blacklisted IP address"
        )
        # Parse blacklist from settings
        self.blacklist = set(
            ip.strip() for ip in settings.ip_blacklist.split(',') if ip.strip()
        )
    
    def check(self, log_entry: LogEntry, db: Session) -> Optional[Dict]:
        """Check if IP is in blacklist."""
        if not log_entry.source_ip:
            return None
        
        if log_entry.source_ip in self.blacklist:
            # Check for recent alert to avoid spam
            time_window_start = log_entry.timestamp - timedelta(hours=1)
            recent_alert = db.query(Alert).filter(
                and_(
                    Alert.rule_name == self.rule_name,
                    Alert.source_ip == log_entry.source_ip,
                    Alert.triggered_at >= time_window_start,
                    Alert.resolved == False
                )
            ).first()
            
            if not recent_alert:
                return {
                    "description": f"Activity detected from blacklisted IP address: {log_entry.source_ip}",
                    "context": {
                        "source_ip": log_entry.source_ip,
                        "username": log_entry.username,
                        "event_type": log_entry.event_type,
                        "status": log_entry.status,
                        "country_code": log_entry.country_code,
                        "raw_log": log_entry.raw_log[:500] if log_entry.raw_log else None
                    }
                }
        
        return None


class DetectionEngine:
    """
    Main detection engine that runs all detection rules.
    """
    
    def __init__(self):
        self.rules = [
            BruteForceDetectionRule(),
            ImpossibleTravelDetectionRule(),
            BusinessHoursDetectionRule(),
            PrivilegeEscalationDetectionRule(),
            BlacklistIPDetectionRule()
        ]
    
    def analyze(self, log_entry: LogEntry, db: Session) -> List[Dict]:
        """
        Analyze log entry against all detection rules.
        
        Args:
            log_entry: LogEntry to analyze
            db: Database session
            
        Returns:
            List of alert dictionaries (one per triggered rule)
        """
        alerts = []
        
        for rule in self.rules:
            try:
                result = rule.check(log_entry, db)
                if result:
                    alerts.append({
                        "rule_name": rule.rule_name,
                        "severity": rule.severity,
                        "description": result["description"],
                        "context": result.get("context", {})
                    })
            except Exception as e:
                print(f"Error executing rule {rule.rule_name}: {e}")
                continue
        
        return alerts


# Global detection engine instance
detection_engine = DetectionEngine()



