"""
Example usage of the Rich logger

This file demonstrates how to use the shared Rich logger throughout the application.
"""

from app.utils.logging import get_logger, app_logger

# Example 1: Get a module-specific logger
logger = get_logger(__name__)

# Example 2: Use the shared application logger
# app_logger is already available and ready to use

def example_function():
    """Example function showing different log levels"""
    
    # Module-specific logger
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Using Rich markup for colored output
    logger.info("[bold green]Success![/bold green] Operation completed")
    logger.warning("[yellow]Warning:[/yellow] This is a warning")
    logger.error("[bold red]Error:[/bold red] Something went wrong")
    
    # Application-wide logger
    app_logger.info("[cyan]Application action:[/cyan] User logged in")
    app_logger.info("[green]✅ Record created successfully[/green]")
    app_logger.error("[red]❌ Failed to process request[/red]")


# Rich markup examples:
# [bold] - Bold text
# [italic] - Italic text
# [underline] - Underlined text
# [red] - Red text
# [green] - Green text
# [yellow] - Yellow text
# [blue] - Blue text
# [cyan] - Cyan text
# [magenta] - Magenta text
# [white] - White text
# [dim] - Dim text
# Combinations: [bold red], [italic green], etc.
