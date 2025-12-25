"""
IP Geolocation utilities for impossible travel detection.
Uses GeoIP2 database if available, falls back to free API services.
"""

import geoip2.database
import geoip2.errors
import requests
import os
from typing import Optional, Dict, Tuple
from backend.config.config import settings


class GeolocationService:
    """
    Service for IP geolocation.
    Handles both MaxMind GeoIP2 database and API fallback.
    """
    
    def __init__(self):
        self.geoip_reader = None
        if settings.maxmind_db_path and os.path.exists(settings.maxmind_db_path):
            try:
                self.geoip_reader = geoip2.database.Reader(settings.maxmind_db_path)
            except Exception as e:
                print(f"Warning: Could not load GeoIP2 database: {e}")
    
    def get_location(self, ip_address: str) -> Optional[Dict[str, any]]:
        """
        Get geolocation for an IP address.
        
        Returns:
            Dict with keys: country_code, latitude, longitude, city, country_name
            None if location cannot be determined
        """
        # Skip private IP ranges
        if self._is_private_ip(ip_address):
            return None
        
        # Try MaxMind database first
        if self.geoip_reader:
            try:
                response = self.geoip_reader.city(ip_address)
                return {
                    "country_code": response.country.iso_code,
                    "latitude": response.location.latitude,
                    "longitude": response.location.longitude,
                    "city": response.city.name,
                    "country_name": response.country.name
                }
            except (geoip2.errors.AddressNotFoundError, ValueError):
                pass
        
        # Fallback to free API (ip-api.com)
        try:
            response = requests.get(
                f"http://ip-api.com/json/{ip_address}",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return {
                        "country_code": data.get("countryCode"),
                        "latitude": data.get("lat"),
                        "longitude": data.get("lon"),
                        "city": data.get("city"),
                        "country_name": data.get("country")
                    }
        except Exception:
            pass
        
        return None
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.
        Returns distance in kilometers.
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in kilometers
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP address is in private range."""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        try:
            first_octet = int(parts[0])
            second_octet = int(parts[1])
            
            # Private IP ranges
            if first_octet == 10:
                return True
            if first_octet == 172 and 16 <= second_octet <= 31:
                return True
            if first_octet == 192 and second_octet == 168:
                return True
            if first_octet == 127:
                return True
            
            return False
        except ValueError:
            return False
    
    def __del__(self):
        """Cleanup GeoIP reader."""
        if self.geoip_reader:
            self.geoip_reader.close()


# Global instance
geolocation_service = GeolocationService()



