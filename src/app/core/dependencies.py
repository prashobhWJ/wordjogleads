"""
Shared dependencies for FastAPI routes
"""
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_session


def get_db() -> Generator:
    """
    Database session dependency.
    Yields a database session from the pool and ensures it's closed after use.
    """
    db = get_session()
    try:
        yield db
    finally:
        db.close()
