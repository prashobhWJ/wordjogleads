"""
Database session management
"""
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional

from app.database.connection import DatabasePool
from app.database.models.base import Base


# Session factory - will be initialized after pool is ready
SessionLocal: Optional[sessionmaker] = None


def init_session_factory() -> None:
    """
    Initialize the session factory with the database engine.
    Should be called after DatabasePool.initialize()
    Sets the schema search path for all connections.
    """
    global SessionLocal
    if SessionLocal is None:
        from app.core.config import settings
        engine = DatabasePool.get_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Set schema search path for all new connections
        if settings.database.schema and settings.database.schema != "public":
            from sqlalchemy import event
            @event.listens_for(engine, "connect")
            def set_search_path(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute(f"SET search_path TO {settings.database.schema}, public")
                cursor.close()


def init_db() -> None:
    """
    Initialize database tables.
    Call this to create all tables defined in models.
    """
    engine = DatabasePool.get_engine()
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """
    Get a new database session from the pool.
    Use this for manual session management outside of FastAPI dependencies.
    
    Returns:
        Session: Database session
        
    Raises:
        RuntimeError: If session factory is not initialized
    """
    if SessionLocal is None:
        init_session_factory()
    
    if SessionLocal is None:
        raise RuntimeError("Session factory not initialized. Call DatabasePool.initialize() first.")
    
    return SessionLocal()
