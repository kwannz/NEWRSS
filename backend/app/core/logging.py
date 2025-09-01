"""
Production-ready structured logging configuration for NEWRSS.

This module provides structured JSON logging using structlog for better
observability, monitoring, and debugging in production environments.
"""

import logging
import sys
from typing import Any, Dict, Optional
import structlog
from pythonjsonlogger import jsonlogger
from app.core.settings import settings


def configure_logging(
    level: str = "INFO",
    enable_json: bool = True,
    enable_colors: bool = False
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Use JSON formatter for structured logs
        enable_colors: Enable colored output for development
    """
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # Processors for structlog
    processors = [
        # Add context
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Add service metadata
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]
    
    # Choose renderer based on environment
    if enable_json:
        processors.append(structlog.processors.JSONRenderer())
    elif enable_colors and sys.stderr.isatty():
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Configure JSON formatter for standard library loggers
    if enable_json:
        json_formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
        
        # Apply to root logger
        root_logger = logging.getLogger()
        if root_logger.handlers:
            for handler in root_logger.handlers:
                handler.setFormatter(json_formatter)


def get_logger(name: str, **context: Any) -> structlog.BoundLogger:
    """
    Get a configured logger with optional context.
    
    Args:
        name: Logger name (usually __name__)
        **context: Additional context to bind to logger
        
    Returns:
        Configured structured logger
    """
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


# Application-specific loggers with context
def get_service_logger(service_name: str, **context: Any) -> structlog.BoundLogger:
    """Get logger for service layer with service context."""
    return get_logger(f"newrss.service.{service_name}", service=service_name, **context)


def get_task_logger(task_name: str, **context: Any) -> structlog.BoundLogger:
    """Get logger for task/background job with task context."""
    return get_logger(f"newrss.task.{task_name}", task=task_name, **context)


def get_api_logger(endpoint: str, **context: Any) -> structlog.BoundLogger:
    """Get logger for API endpoints with request context."""
    return get_logger(f"newrss.api.{endpoint}", endpoint=endpoint, **context)


def setup_logging() -> None:
    """
    Initialize logging configuration based on environment settings.
    
    This should be called once during application startup.
    """
    # Determine configuration based on environment
    if settings.ENV == "dev":
        configure_logging(
            level="DEBUG",
            enable_json=False,
            enable_colors=True
        )
    elif settings.ENV == "test":
        configure_logging(
            level="WARNING",
            enable_json=False,
            enable_colors=False
        )
    else:  # production
        configure_logging(
            level="INFO",
            enable_json=True,
            enable_colors=False
        )


# Pre-configured loggers for common use cases
main_logger = get_logger("newrss.main")
database_logger = get_logger("newrss.database")
websocket_logger = get_logger("newrss.websocket")