"""
PostgreSQL Connection Pool Manager
Uses SQLAlchemy for connection pooling
"""
from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import Pool
from typing import Optional
from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DatabasePool:
    """
    PostgreSQL connection pool manager using SQLAlchemy.
    Manages a single shared connection pool for all database operations.
    """
    
    _engine: Optional[Engine] = None
    _pool: Optional[Pool] = None
    _initialized: bool = False
    
    @classmethod
    def initialize(cls) -> None:
        """
        Initialize the database connection pool.
        Should be called at application startup.
        """
        if cls._initialized:
            logger.warning("Database pool already initialized")
            return
        
        try:
            # Get pool configuration from settings
            pool_config = settings.database.pool
            pool_size = pool_config.size
            max_overflow = pool_config.max_overflow
            pool_timeout = pool_config.timeout
            pool_recycle = pool_config.recycle
            
            cls._engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,  # Recycle connections after 1 hour
                echo=pool_config.echo,
                connect_args={
                    "options": f"-csearch_path={settings.database.schema}"
                } if settings.database.schema else {},
            )
            
            cls._pool = cls._engine.pool
            cls._initialized = True
            
            logger.info(
                f"[green]Database pool initialized:[/green] "
                f"[cyan]size={pool_size}[/cyan], [cyan]max_overflow={max_overflow}[/cyan], "
                f"[cyan]timeout={pool_timeout}s[/cyan], [cyan]recycle={pool_recycle}s[/cyan]"
            )
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @classmethod
    def get_engine(cls) -> Engine:
        """
        Get the database engine.
        Initializes the pool if not already initialized.
        
        Returns:
            Engine: SQLAlchemy engine instance
            
        Raises:
            RuntimeError: If pool is not initialized
        """
        if not cls._initialized:
            cls.initialize()
        
        if cls._engine is None:
            raise RuntimeError("Database pool not initialized")
        
        return cls._engine
    
    @classmethod
    def get_pool(cls) -> Pool:
        """
        Get the connection pool.
        
        Returns:
            Pool: SQLAlchemy connection pool instance
            
        Raises:
            RuntimeError: If pool is not initialized
        """
        if not cls._initialized:
            cls.initialize()
        
        if cls._pool is None:
            raise RuntimeError("Database pool not initialized")
        
        return cls._pool
    
    @classmethod
    def close(cls) -> None:
        """
        Close the database connection pool.
        Should be called at application shutdown.
        """
        if cls._engine is not None:
            try:
                cls._engine.dispose()
                logger.info("[green]Database pool closed successfully[/green]")
            except Exception as e:
                logger.error(f"Error closing database pool: {e}")
            finally:
                cls._engine = None
                cls._pool = None
                cls._initialized = False
    
    @classmethod
    def get_pool_status(cls) -> dict:
        """
        Get the current status of the connection pool.
        
        Returns:
            dict: Pool status information
        """
        if not cls._initialized or cls._pool is None:
            return {
                "initialized": False,
                "size": 0,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
            }
        
        return {
            "initialized": True,
            "size": cls._pool.size(),
            "checked_in": cls._pool.checkedin(),
            "checked_out": cls._pool.checkedout(),
            "overflow": cls._pool.overflow(),
        }


# Convenience accessor for backward compatibility
def get_engine() -> Engine:
    """Get the database engine (backward compatibility)"""
    return DatabasePool.get_engine()
