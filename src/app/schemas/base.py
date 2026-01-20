"""
Base schema classes
"""
from pydantic import BaseModel as PydanticBaseModel
from datetime import datetime
from typing import Optional


class BaseSchema(PydanticBaseModel):
    """Base schema with common configuration"""
    
    class Config:
        from_attributes = True  # Allows ORM mode (formerly orm_mode)
        populate_by_name = True


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""
    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """Schema with ID field"""
    id: int


class BaseResponseSchema(TimestampSchema, IDSchema):
    """Base response schema with common fields"""
    pass
