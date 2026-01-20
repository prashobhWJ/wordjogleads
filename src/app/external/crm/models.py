"""
Pydantic models for CRM API requests and responses
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class CRMRecordCreate(BaseModel):
    """Base model for creating CRM records"""
    pass


class CRMRecordResponse(BaseModel):
    """Base model for CRM API responses"""
    id: Optional[str] = None
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class CRMContactCreate(CRMRecordCreate):
    """Model for creating a contact in CRM"""
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    additional_fields: Optional[Dict[str, Any]] = None


class CRMLeadCreate(CRMRecordCreate):
    """Model for creating a lead in CRM"""
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    additional_fields: Optional[Dict[str, Any]] = None
