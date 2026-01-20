"""
Base repository class for data access operations
"""
from sqlalchemy.orm import Session
from typing import Generic, TypeVar, Type, Optional, List
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class for database operations.
    Repositories handle direct database access and queries.
    """
    
    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model
    
    def find_by_id(self, id: int) -> Optional[ModelType]:
        """Find a record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def find_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Find all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def find_by(self, **filters) -> List[ModelType]:
        """Find records by filters"""
        return self.db.query(self.model).filter_by(**filters).all()
    
    def find_one_by(self, **filters) -> Optional[ModelType]:
        """Find a single record by filters"""
        return self.db.query(self.model).filter_by(**filters).first()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**kwargs)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update(self, db_obj: ModelType, **kwargs) -> ModelType:
        """Update an existing record"""
        for key, value in kwargs.items():
            setattr(db_obj, key, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, db_obj: ModelType) -> None:
        """Delete a record"""
        self.db.delete(db_obj)
        self.db.commit()
