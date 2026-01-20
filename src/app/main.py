"""
FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.database.connection import DatabasePool
from app.database.session import init_session_factory
from app.utils.logging import get_logger, app_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.
    Initializes database pool on startup and closes it on shutdown.
    """
    # Startup
    app_logger.info("🚀 [bold green]Initializing application...[/bold green]")
    try:
        app_logger.info("📊 [cyan]Initializing database connection pool...[/cyan]")
        DatabasePool.initialize()
        init_session_factory()
        app_logger.info("✅ [bold green]Application initialized successfully[/bold green]")
    except Exception as e:
        app_logger.error(f"❌ [bold red]Failed to initialize application:[/bold red] {e}")
        raise
    
    yield
    
    # Shutdown
    app_logger.info("🛑 [yellow]Shutting down application...[/yellow]")
    try:
        app_logger.info("📊 [cyan]Closing database connection pool...[/cyan]")
        DatabasePool.close()
        app_logger.info("✅ [bold green]Application shut down successfully[/bold green]")
    except Exception as e:
        app_logger.error(f"❌ [bold red]Error during application shutdown:[/bold red] {e}")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description=settings.description,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
if settings.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.backend_cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "API is running", "version": settings.version}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        pool_status = DatabasePool.get_pool_status()
        return {
            "status": "healthy",
            "database": {
                "pool_initialized": pool_status["initialized"],
                "pool_size": pool_status["size"],
                "connections_checked_out": pool_status["checked_out"],
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
