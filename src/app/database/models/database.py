"""
Database models for PostgreSQL tables.
Add your SQLAlchemy models here.
"""
from sqlalchemy import Column, String, Text, Boolean, Date, Numeric
from app.database.models.base import BaseModel


class Lead(BaseModel):
    """
    Lead model representing leads from the database.
    Maps to the 'leads' table in PostgreSQL.
    """
    __tablename__ = "leads"
    
    # Lead Identification
    lead_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    
    # Address Information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    country_code = Column(String(10), nullable=True)  # e.g., "ON" for Ontario
    
    # Vehicle Information
    vehicle_type = Column(String(50), nullable=True, index=True)
    
    # Financial Information
    current_credit = Column(String(100), nullable=True)
    
    # Employment Information
    employment_status = Column(String(50), nullable=True, index=True)
    job_title = Column(String(100), nullable=True)
    company_name = Column(String(200), nullable=True)
    monthly_salary_min = Column(Numeric(10, 2), nullable=True)
    monthly_salary_max = Column(Numeric(10, 2), nullable=True)
    employment_length = Column(String(50), nullable=True)
    length_at_company = Column(String(50), nullable=True)
    
    # Residency Information
    length_at_home_address = Column(String(50), nullable=True)
