"""
Lead API request and response schemas
"""
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from app.schemas.base import BaseSchema, BaseResponseSchema, IDSchema


class LeadBase(BaseSchema):
    """Base lead schema with common fields"""
    lead_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class LeadSummary(LeadBase, IDSchema):
    """Summary schema for lead list responses"""
    city: Optional[str] = None
    state_province: Optional[str] = None
    employment_status: Optional[str] = None
    company_name: Optional[str] = None
    created_at: Optional[datetime] = None


class LeadDetail(LeadBase, BaseResponseSchema):
    """Detailed lead schema for single lead responses"""
    date_of_birth: Optional[date] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    vehicle_type: Optional[str] = None
    current_credit: Optional[str] = None
    employment_status: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    monthly_salary_min: Optional[Decimal] = None
    monthly_salary_max: Optional[Decimal] = None
    employment_length: Optional[str] = None
    length_at_company: Optional[str] = None
    length_at_home_address: Optional[str] = None


class LeadListResponse(BaseSchema):
    """Response schema for lead list endpoint"""
    total: int
    skip: int
    limit: int
    leads: List[LeadSummary]


class LeadSyncResponse(BaseSchema):
    """Response schema for lead sync operations"""
    message: str
    lead_id: Optional[str] = None
    crm_response: Optional[dict] = None
    results: Optional[dict] = None


class SalesAgentMatchResponse(BaseSchema):
    """Response schema for sales agent matching"""
    message: str
    lead_id: str
    selected_agent_id: Optional[str] = None
    selected_agent_name: Optional[str] = None
    confidence_score: Optional[int] = None
    reasoning: Optional[str] = None
    alternative_agents: Optional[List[dict]] = None
    match_result: Optional[dict] = None
