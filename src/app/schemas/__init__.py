"""
Pydantic schemas for request/response validation
"""
from app.schemas.base import (
    BaseSchema,
    TimestampSchema,
    IDSchema,
    BaseResponseSchema
)
from app.schemas.twenty_crm import (
    TwentyCRMName,
    TwentyCRMEmails,
    TwentyCRMLink,
    TwentyCRMPhones,
    TwentyCRMPersonCreate,
    TwentyCRMTaskCreate
)
from app.schemas.leads import (
    LeadBase,
    LeadSummary,
    LeadDetail,
    LeadListResponse,
    LeadSyncResponse,
    SalesAgentMatchResponse
)

__all__ = [
    # Base schemas
    "BaseSchema",
    "TimestampSchema",
    "IDSchema",
    "BaseResponseSchema",
    # Twenty CRM schemas
    "TwentyCRMName",
    "TwentyCRMEmails",
    "TwentyCRMLink",
    "TwentyCRMPhones",
    "TwentyCRMPersonCreate",
    "TwentyCRMTaskCreate",
    # Lead schemas
    "LeadBase",
    "LeadSummary",
    "LeadDetail",
    "LeadListResponse",
    "LeadSyncResponse",
    "SalesAgentMatchResponse",
]