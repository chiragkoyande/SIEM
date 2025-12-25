"""
Log parsing and normalization module.
Converts various log formats into common schema.
"""

import re
from datetime import datetime
from typing import Optional, Dict, List
from backend.app.models.database import LogEntry
from backend.app.utils.helpers import parse_timestamp
from backend.app.utils.geolocation import geolocation_service


class LogParser:
    """
    Parser for authentication and system logs.
    Normalizes logs into common schema: timestamp, source IP, username, event type, status.
    """
    
    # Regex patterns for common log formats
    PATTERNS = {
        # Apache/Nginx access log format
        'apache_access': re.compile(
            r'(?P<ip>\S+) .*? \[(?P<timestamp>.*?)\] .*?"\w+ (?P<path>\S+)'
        ),
        # SSH authentication log
        'ssh_auth': re.compile(
            r'(?P<timestamp>\w+ \d+ \d+:\d+:\d+) .*? (?P<event>Accepted|Failed) .*? (?P<source_ip>\d+\.\d+\.\d+\.\d+) .*? user (?P<username>\S+)'
        ),
        # Generic authentication log
        'auth_log': re.compile(
            r'(?P<timestamp>[\d\-:T.]+).*?(?P<source_ip>\d+\.\d+\.\d+\.\d+).*?user[:\s]+(?P<username>\S+).*?(?P<status>success|failed|denied|accepted|rejected)',
            re.IGNORECASE
        ),
        # Windows Event Log style
        'windows_event': re.compile(
            r'(?P<timestamp>[\d\-:T.]+).*?Source IP[:\s]+(?P<source_ip>\d+\.\d+\.\d+\.\d+).*?User[:\s]+(?P<username>\S+).*?Status[:\s]+(?P<status>\w+)',
            re.IGNORECASE
        ),
        # JSON format logs
        'json_log': re.compile(
            r'\{.*?"timestamp"[:\s]+"(?P<timestamp>[^"]+)".*?"ip"[:\s]+"(?P<source_ip>[^"]+)".*?"user"[:\s]+"(?P<username>[^"]+)".*?"status"[:\s]+"(?P<status>[^"]+)".*?\}',
            re.IGNORECASE | re.DOTALL
        ),
        # Custom format: timestamp IP username event status
        'simple_log': re.compile(
            r'(?P<timestamp>[\d\-:T.]+)\s+(?P<source_ip>\d+\.\d+\.\d+\.\d+)\s+(?P<username>\S+)\s+(?P<event_type>\w+)\s+(?P<status>\w+)'
        )
    }
    
    def parse_line(self, log_line: str, source_file: str = None) -> Optional[LogEntry]:
        """
        Parse a single log line into normalized LogEntry.
        
        Args:
            log_line: Raw log line to parse
            source_file: Optional source file name
            
        Returns:
            LogEntry object or None if parsing fails
        """
        log_line = log_line.strip()
        if not log_line:
            return None
        
        parsed_data = self._extract_fields(log_line)
        if not parsed_data:
            return None
        
        # Parse timestamp
        timestamp = parsed_data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = parse_timestamp(timestamp)
        if not timestamp or not isinstance(timestamp, datetime):
            timestamp = datetime.utcnow()
        
        # Extract fields with defaults
        source_ip = parsed_data.get('source_ip', '')
        username = parsed_data.get('username', '')
        event_type = parsed_data.get('event_type', parsed_data.get('event', 'authentication'))
        status = parsed_data.get('status', 'unknown')
        
        # Get geolocation for IP
        location_data = None
        country_code = None
        latitude = None
        longitude = None
        
        if source_ip:
            location_data = geolocation_service.get_location(source_ip)
            if location_data:
                country_code = location_data.get('country_code')
                latitude = location_data.get('latitude')
                longitude = location_data.get('longitude')
        
        # Create LogEntry
        log_entry = LogEntry(
            timestamp=timestamp,
            source_ip=source_ip,
            username=username,
            event_type=event_type.lower(),
            status=status.lower(),
            raw_log=log_line,
            source_file=source_file,
            country_code=country_code,
            latitude=latitude,
            longitude=longitude
        )
        
        return log_entry
    
    def _extract_fields(self, log_line: str) -> Optional[Dict[str, str]]:
        """
        Extract fields from log line using regex patterns.
        Returns dict with extracted fields.
        """
        # Try each pattern
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.search(log_line)
            if match:
                data = match.groupdict()
                
                # Normalize event type based on pattern
                if 'event' in data and 'event_type' not in data:
                    event_value = data['event'].lower()
                    if event_value in ['accepted', 'success']:
                        data['status'] = 'success'
                        data['event_type'] = 'login'
                    elif event_value in ['failed', 'denied', 'rejected']:
                        data['status'] = 'failed'
                        data['event_type'] = 'login'
                    else:
                        data['event_type'] = event_value
                
                return data
        
        # Fallback: try to extract IP address and basic info
        ip_match = re.search(r'\b(\d+\.\d+\.\d+\.\d+)\b', log_line)
        if ip_match:
            return {
                'source_ip': ip_match.group(1),
                'timestamp': datetime.utcnow().isoformat(),
                'username': '',
                'event_type': 'unknown',
                'status': 'unknown'
            }
        
        return None
    
    def parse_file(self, file_path: str) -> List[LogEntry]:
        """
        Parse entire log file.
        
        Args:
            file_path: Path to log file
            
        Returns:
            List of LogEntry objects
        """
        entries = []
        source_file = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        entry = self.parse_line(line, source_file)
                        if entry:
                            entries.append(entry)
                    except Exception as e:
                        print(f"Error parsing line {line_num}: {e}")
                        continue
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
        
        return entries


# Global parser instance
log_parser = LogParser()



