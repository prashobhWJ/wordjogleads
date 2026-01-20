"""
Base service class for common service functionality
"""
from sqlalchemy.orm import Session
from typing import Generic, TypeVar, Type, Optional, List
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseService(Generic[ModelType]):
    """
    Base service class with common CRUD operations.
    Services should inherit from this for standard database operations.
    """
    
    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model
    
    def get(self, id: int) -> Optional[ModelType]:
        """Get a single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**kwargs)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Update an existing record"""
        db_obj = self.get(id)
        if not db_obj:
            return None
        for key, value in kwargs.items():
            setattr(db_obj, key, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: int) -> bool:
        """Delete a record"""
        db_obj = self.get(id)
        if not db_obj:
            return False
        self.db.delete(db_obj)
        self.db.commit()
        return True
