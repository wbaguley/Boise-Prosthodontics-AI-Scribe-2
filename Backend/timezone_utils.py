"""
Timezone utility functions for handling datetime operations with configurable timezone support
"""

from datetime import datetime, timezone
import pytz
from typing import Optional, Union
import logging

def get_system_timezone():
    """Get the configured system timezone"""
    try:
        from database import get_system_config
        tz_name = get_system_config('timezone', 'America/Denver')  # Default to Mountain Time
        return pytz.timezone(tz_name)
    except Exception as e:
        logging.warning(f"Error getting system timezone: {e}. Using default America/Denver")
        return pytz.timezone('America/Denver')

def get_system_datetime_format():
    """Get the configured datetime format string"""
    try:
        from database import get_system_config
        return get_system_config('datetime_format', '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.warning(f"Error getting datetime format: {e}. Using default format")
        return '%Y-%m-%d %H:%M:%S'

def get_system_date_format():
    """Get the configured date format string"""
    try:
        from database import get_system_config
        return get_system_config('date_format', '%Y-%m-%d')
    except Exception as e:
        logging.warning(f"Error getting date format: {e}. Using default format")
        return '%Y-%m-%d'

def get_system_time_format():
    """Get the configured time format string"""
    try:
        from database import get_system_config
        return get_system_config('time_format', '%H:%M:%S')
    except Exception as e:
        logging.warning(f"Error getting time format: {e}. Using default format")
        return '%H:%M:%S'

def now_in_system_timezone() -> datetime:
    """Get current datetime in the configured system timezone"""
    system_tz = get_system_timezone()
    return datetime.now(system_tz)

def utc_to_system_timezone(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to system timezone"""
    if utc_dt.tzinfo is None:
        # Assume it's UTC if no timezone info
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
    elif utc_dt.tzinfo != pytz.UTC:
        # Convert to UTC first if it's in a different timezone
        utc_dt = utc_dt.astimezone(pytz.UTC)
    
    system_tz = get_system_timezone()
    return utc_dt.astimezone(system_tz)

def system_timezone_to_utc(system_dt: datetime) -> datetime:
    """Convert system timezone datetime to UTC"""
    system_tz = get_system_timezone()
    
    if system_dt.tzinfo is None:
        # Assume it's in system timezone if no timezone info
        system_dt = system_tz.localize(system_dt)
    
    return system_dt.astimezone(pytz.UTC)

def format_datetime_for_display(dt: datetime, include_timezone: bool = False) -> str:
    """Format datetime for display using system configuration"""
    if dt is None:
        return "N/A"
    
    # Convert to system timezone if needed
    if dt.tzinfo is not None:
        dt = utc_to_system_timezone(dt)
    
    format_str = get_system_datetime_format()
    
    if include_timezone:
        system_tz = get_system_timezone()
        formatted = dt.strftime(format_str)
        return f"{formatted} {system_tz.zone}"
    
    return dt.strftime(format_str)

def format_date_for_display(dt: datetime) -> str:
    """Format date for display using system configuration"""
    if dt is None:
        return "N/A"
    
    # Convert to system timezone if needed
    if dt.tzinfo is not None:
        dt = utc_to_system_timezone(dt)
    
    format_str = get_system_date_format()
    return dt.strftime(format_str)

def format_time_for_display(dt: datetime) -> str:
    """Format time for display using system configuration"""
    if dt is None:
        return "N/A"
    
    # Convert to system timezone if needed
    if dt.tzinfo is not None:
        dt = utc_to_system_timezone(dt)
    
    format_str = get_system_time_format()
    return dt.strftime(format_str)

def parse_date_string(date_str: str, date_format: Optional[str] = None) -> Optional[datetime]:
    """Parse date string using system or provided format"""
    if not date_str:
        return None
    
    if date_format is None:
        date_format = get_system_date_format()
    
    try:
        return datetime.strptime(date_str, date_format)
    except ValueError as e:
        logging.error(f"Error parsing date '{date_str}' with format '{date_format}': {e}")
        return None

def parse_datetime_string(datetime_str: str, datetime_format: Optional[str] = None) -> Optional[datetime]:
    """Parse datetime string using system or provided format"""
    if not datetime_str:
        return None
    
    if datetime_format is None:
        datetime_format = get_system_datetime_format()
    
    try:
        return datetime.strptime(datetime_str, datetime_format)
    except ValueError as e:
        logging.error(f"Error parsing datetime '{datetime_str}' with format '{datetime_format}': {e}")
        return None

def get_session_id_with_timezone() -> str:
    """Generate session ID with current system timezone datetime"""
    now = now_in_system_timezone()
    return now.strftime("%Y%m%d_%H%M%S")

def get_available_timezones() -> list:
    """Get list of commonly used timezones for configuration"""
    common_timezones = [
        'America/New_York',      # Eastern Time
        'America/Chicago',       # Central Time
        'America/Denver',        # Mountain Time
        'America/Phoenix',       # Arizona Time (no DST)
        'America/Los_Angeles',   # Pacific Time
        'America/Anchorage',     # Alaska Time
        'Pacific/Honolulu',      # Hawaii Time
        'UTC',                   # Universal Time
    ]
    
    return [
        {
            'name': tz_name,
            'display_name': tz_name.replace('_', ' ').replace('/', ' / '),
            'current_time': datetime.now(pytz.timezone(tz_name)).strftime('%H:%M')
        }
        for tz_name in common_timezones
    ]

def validate_timezone(tz_name: str) -> bool:
    """Validate if timezone name is valid"""
    try:
        pytz.timezone(tz_name)
        return True
    except pytz.UnknownTimeZoneError:
        return False

# Backwards compatibility functions to replace datetime.now() usage
def get_current_datetime() -> datetime:
    """Get current datetime in system timezone - use instead of datetime.now()"""
    return now_in_system_timezone()

def get_current_utc_datetime() -> datetime:
    """Get current UTC datetime - for database storage"""
    return datetime.now(pytz.UTC)

def format_for_soap_note(dt: Optional[datetime] = None) -> str:
    """Format datetime for SOAP note display"""
    if dt is None:
        dt = now_in_system_timezone()
    
    # Use a readable format for medical notes
    return dt.strftime("%B %d, %Y at %I:%M %p")

def format_for_email_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime for email timestamps"""
    if dt is None:
        dt = now_in_system_timezone()
    
    return dt.strftime("%A, %B %d, %Y at %I:%M %p")