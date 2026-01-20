"""
General helper functions
"""
from typing import Any, Dict, Optional
from datetime import datetime


def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO string"""
    return dt.isoformat() if dt else None


def safe_get(data: Dict[str, Any], *keys, default: Any = None) -> Any:
    """
    Safely get nested dictionary values.
    
    Args:
        data: Dictionary to search
        *keys: Keys to traverse
        default: Default value if key not found
    
    Returns:
        Value or default
    """
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default


def remove_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from dictionary"""
    return {k: v for k, v in data.items() if v is not None}
