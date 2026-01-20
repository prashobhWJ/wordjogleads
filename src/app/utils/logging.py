"""
Rich logging utility for beautiful, colored terminal output
"""
import logging
import sys
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install as install_traceback
from app.core.config import settings

# Install rich traceback handler for better error display
install_traceback(show_locals=True)

# Create a shared console instance
_console = Console()


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with Rich formatting and colors.
    All loggers share the same RichHandler for consistent output.
    
    Args:
        name: Logger name (typically __name__)
        level: Optional log level override (defaults to settings.log_level)
    
    Returns:
        Configured logger instance with RichHandler
    """
    logger = logging.getLogger(name)
    
    # Set log level
    log_level = level.upper() if level else settings.log_level.upper()
    logger.setLevel(getattr(logging, log_level))
    
    # Avoid adding multiple handlers
    if not logger.handlers:
        # Create RichHandler with beautiful formatting
        handler = RichHandler(
            console=_console,
            show_time=True,
            show_path=True,
            show_level=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,  # Enable rich markup in log messages
            log_time_format="[%Y-%m-%d %H:%M:%S]",
        )
        
        # Set formatter (RichHandler has its own formatting, but we can customize)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(message)s",
                datefmt="[%Y-%m-%d %H:%M:%S]"
            )
        )
        
        logger.addHandler(handler)
    
    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False
    
    return logger


def get_shared_logger() -> logging.Logger:
    """
    Get a shared application logger for general application-wide logging.
    Use this for logging actions that don't belong to a specific module.
    
    Returns:
        Shared logger instance
    """
    return get_logger("app")


# Create a shared application logger instance
app_logger = get_shared_logger()
