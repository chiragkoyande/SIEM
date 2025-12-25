"""
Helper utilities for SentinelWatch SIEM.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional


def generate_alert_id() -> str:
    """Generate unique alert ID (UUID)."""
    return str(uuid.uuid4())


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse various timestamp formats commonly found in logs.
    Supports ISO format, Unix timestamp, and common log formats.
    """
    if not timestamp_str:
        return None
    
    # Try ISO format
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    # Try Unix timestamp
    try:
        timestamp_float = float(timestamp_str)
        return datetime.fromtimestamp(timestamp_float)
    except (ValueError, OSError):
        pass
    
    # Try common log formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%b/%Y:%H:%M:%S",
        "%b %d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    return None


def is_business_hours(timestamp: datetime, start_hour: int = 8, end_hour: int = 18) -> bool:
    """
    Check if timestamp is within business hours.
    Only considers weekday (Monday-Friday).
    """
    if timestamp.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    hour = timestamp.hour
    return start_hour <= hour < end_hour



