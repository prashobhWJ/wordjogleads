"""
Database models module
"""
from app.database.models.base import Base
from app.database.models.database import Lead  # Import all models here

__all__ = ["Base", "Lead"]
