"""
Twenty CRM specific schemas
"""
from typing import Optional, List, Dict, Any
from app.schemas.base import BaseSchema


class TwentyCRMName(BaseSchema):
    """Name structure for Twenty CRM"""
    firstName: str
    lastName: str


class TwentyCRMEmails(BaseSchema):
    """Email structure for Twenty CRM"""
    primaryEmail: str
    additionalEmails: Optional[List[str]] = None


class TwentyCRMLink(BaseSchema):
    """Link structure for Twenty CRM"""
    primaryLinkLabel: str = ""
    primaryLinkUrl: str = ""
    secondaryLinks: List[Dict[str, Any]] = []


class TwentyCRMPhones(BaseSchema):
    """Phone structure for Twenty CRM"""
    primaryPhoneNumber: str
    primaryPhoneCallingCode: Optional[str] = None
    primaryPhoneCountryCode: Optional[str] = None
    additionalPhones: List[Dict[str, Any]] = []


class TwentyCRMPersonCreate(BaseSchema):
    """Model for creating a person in Twenty CRM"""
    name: TwentyCRMName
    emails: TwentyCRMEmails
    linkedinLink: Optional[TwentyCRMLink] = None
    xLink: Optional[TwentyCRMLink] = None
    phones: Optional[TwentyCRMPhones] = None
    # Custom fields for additional lead information
    vehicletype: Optional[str] = None  # Vehicle type interest
    city: Optional[str] = None  # City location
    employmentlength: Optional[str] = None  # Employment length
    companyname: Optional[str] = None  # Company employed with


class TwentyCRMTaskCreate(BaseSchema):
    """Model for creating a task in Twenty CRM"""
    title: str
    status: str = "BACKLOG"
    assigneeId: Optional[str] = None  # Workspace member ID to assign the task to (not person ID)
    bodyV2: Optional[Dict[str, Any]] = None  # Task content with markdown only
    taskTargets: Optional[List[Dict[str, str]]] = None  # Array to link task to person/company/opportunity
    salesrep: Optional[str] = None  # Sales representative name