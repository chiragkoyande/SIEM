"""
Configuration settings for SentinelWatch SIEM.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sentinelwatch.db")
    
    # Business hours for detection (24-hour format)
    business_hours_start: int = 8  # 8 AM
    business_hours_end: int = 18  # 6 PM
    
    # Detection thresholds
    brute_force_threshold: int = 5  # Failed login attempts within time window
    brute_force_window_minutes: int = 10  # Time window for brute-force detection
    
    # IP Blacklist (comma-separated)
    ip_blacklist: str = os.getenv("IP_BLACKLIST", "10.0.0.100,192.168.1.200,172.16.0.50")
    
    # Geolocation settings
    maxmind_db_path: str = os.getenv("MAXMIND_DB_PATH", "")  # Optional GeoIP2 database path
    
    # Alert settings
    alert_retention_days: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()



