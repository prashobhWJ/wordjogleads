"""
API-specific dependencies for v1 endpoints
"""
from typing import Optional
from fastapi import Header, HTTPException, status


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key from request header.
    Customize this based on your authentication requirements.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    # Add your API key validation logic here
    return x_api_key
