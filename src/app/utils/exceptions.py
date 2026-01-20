"""
Custom exception classes
"""
from fastapi import HTTPException, status


class CRMAPIError(HTTPException):
    """Exception raised when CRM API call fails"""
    def __init__(self, detail: str, status_code: int = status.HTTP_502_BAD_GATEWAY):
        super().__init__(status_code=status_code, detail=detail)


class DatabaseError(HTTPException):
    """Exception raised for database errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)


class ValidationError(HTTPException):
    """Exception raised for validation errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY):
        super().__init__(status_code=status_code, detail=detail)
