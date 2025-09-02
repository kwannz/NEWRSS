"""NEWRSS - Real-time Cryptocurrency News Aggregation Platform.

This module contains the main FastAPI application with security hardening,
WebSocket integration, and comprehensive monitoring capabilities.

The application provides:
- Real-time news aggregation from multiple RSS sources
- AI-powered news analysis and sentiment scoring
- WebSocket broadcasting for live updates
- Telegram bot integration for notifications
- Enterprise-grade security with OWASP Top 10 protection
- Comprehensive rate limiting and input validation
- Production-ready logging and monitoring

Typical usage example:
    uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload

Author: NEWRSS Development Team
Version: 1.0.0
"""

from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import socketio
from socketio import ASGIApp
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Core imports
from app.core.settings import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging, main_logger, database_logger, websocket_logger

# Security imports
from app.core.security_headers import SecurityHeadersMiddleware, security_monitoring_middleware
from app.core.rate_limiting import initialize_rate_limiter, limiter, custom_rate_limit_handler
from app.core.security import initialize_security
from app.core.input_validation import validate_request_size

# API routers
from app.api.news import router as news_router
from app.api.auth import router as auth_router
from app.api.sources import router as sources_router
from app.api.broadcast import router as broadcast_router
from app.api.exchange import router as exchange_router
from app.services.telegram_webhook import router as telegram_router

# Services
from app.services.broadcast_service import BroadcastService
from app.core.broadcast_utils import get_socketio_server

# Initialize logging before any other operations
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Manage application lifespan with proper startup and shutdown procedures.
    
    This function handles:
    - Security component initialization
    - Database setup and migration
    - Rate limiting configuration
    - Graceful resource cleanup on shutdown
    
    Args:
        app: The FastAPI application instance.
        
    Yields:
        None: Control to the application during its runtime.
        
    Raises:
        Exception: Any initialization errors are logged but don't prevent startup.
    """
    # Startup
    main_logger.info("Starting NEWRSS application with security hardening", env=settings.ENV)
    
    # Initialize security components
    try:
        await initialize_security()
        main_logger.info("Security components initialized")
    except Exception as e:
        main_logger.error(f"Failed to initialize security components: {e}")
    
    try:
        await initialize_rate_limiter()
        main_logger.info("Rate limiting initialized")
    except Exception as e:
        main_logger.error(f"Failed to initialize rate limiter: {e}")
    
    # Initialize database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    database_logger.info("Database tables created successfully")
    
    main_logger.info("Application startup completed successfully")
    yield
    
    # Shutdown
    main_logger.info("Starting application shutdown sequence")
    await engine.dispose()
    database_logger.info("Database connection closed")
    main_logger.info("Application shutdown completed")


# Create FastAPI app with enhanced security
app = FastAPI(
    title="NEWRSS API",
    description="Real-time cryptocurrency news aggregation platform with AI analysis",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
    # Security: Don't expose docs in production
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
    openapi_url="/openapi.json" if settings.ENV != "production" else None,
    contact={
        "name": "NEWRSS API Support",
        "email": "support@newrss.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Security Middleware Stack (order matters!)
# 1. Trusted Host middleware (outermost security layer)
if settings.ENV == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# 2. Security headers middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_csp=settings.CSP_ENABLED,
    enable_hsts=True
)

# 3. Security monitoring middleware
app.middleware("http")(security_monitoring_middleware)

# 4. Request size validation middleware
app.middleware("http")(validate_request_size)

# 5. CORS middleware (configured for security)
cors_origins = settings.CORS_ORIGINS
if settings.ENV == "production":
    # In production, be more restrictive
    cors_origins = [origin for origin in cors_origins if 'localhost' not in origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization", 
        "Content-Type", 
        "X-Requested-With",
        "X-API-Version"
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining", 
        "X-RateLimit-Reset"
    ]
)

# 6. Rate limiting
app.state.limiter = limiter


# Custom error handlers
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded exceptions with proper logging.
    
    Args:
        request: The incoming request that exceeded rate limits.
        exc: The rate limit exceeded exception.
        
    Returns:
        JSONResponse with appropriate error message and headers.
    """
    return await custom_rate_limit_handler(request, exc)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Enhanced HTTP exception handler with security logging.
    
    Provides comprehensive error handling with:
    - Security event logging for audit trails
    - Structured error responses
    - Additional security headers
    
    Args:
        request: The request that caused the exception.
        exc: The HTTP exception that was raised.
        
    Returns:
        JSONResponse with error details and security headers.
    """
    if exc.status_code >= 400:
        from app.core.security_headers import security_logger
        security_logger.log_security_event(
            "http_error",
            {
                "status_code": exc.status_code,
                "detail": exc.detail,
            },
            severity="low" if exc.status_code < 500 else "high",
            request=request
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "X-Error-Code": str(exc.status_code),
            "X-API-Version": "1.0"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler with comprehensive security logging.
    
    Handles all unhandled exceptions with:
    - Security event logging for audit
    - Detailed error logging for debugging
    - Sanitized error responses to prevent information leakage
    
    Args:
        request: The request that caused the exception.
        exc: The unhandled exception.
        
    Returns:
        JSONResponse with generic error message for security.
    """
    from app.core.security_headers import security_logger
    security_logger.log_security_event(
        "internal_error",
        {
            "error": str(exc),
            "error_type": type(exc).__name__,
        },
        severity="high",
        request=request
    )
    
    main_logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers={"X-Error-Code": "500"}
    )


# Include API routers with rate limiting
app.include_router(news_router)
app.include_router(sources_router)
app.include_router(broadcast_router)
app.include_router(exchange_router, prefix="/api/v1/exchange", tags=["exchange"])
app.include_router(telegram_router)
app.include_router(auth_router)

# Static files (with security considerations)
if settings.DEBUG:
    app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket setup
sio = get_socketio_server()
broadcast_service = BroadcastService()


# Health and monitoring endpoints
@app.get("/", response_model=Dict[str, str])
async def root() -> Dict[str, str] | FileResponse:
    """Root endpoint providing API information or static content.
    
    Returns:
        FileResponse: Static HTML file in debug mode.
        Dict[str, str]: API information in production mode.
    """
    if settings.DEBUG:
        return FileResponse("static/index.html")
    else:
        return {"message": "NEWRSS API", "version": "1.0.0", "status": "running"}


@app.get("/health", response_model=Dict[str, Any])
@limiter.limit("10/minute")  # Rate limit health checks
async def health(request: Request) -> Dict[str, Any]:
    """Enhanced health check endpoint with security status.
    
    Provides comprehensive health information including:
    - Application status and version
    - Environment configuration
    - Security features status
    
    Args:
        request: The incoming request (required for rate limiting).
        
    Returns:
        Dict containing health status and configuration information.
        
    Rate Limits:
        10 requests per minute per IP address.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENV,
        "security_headers_enabled": settings.SECURITY_HEADERS_ENABLED,
        "debug": settings.DEBUG
    }


@app.get("/security/status", response_model=Dict[str, Any])
@limiter.limit("5/minute")  # Very restrictive for security info
async def security_status(request: Request) -> Dict[str, Any]:
    """Security status endpoint with restricted access.
    
    Provides detailed security component status for debugging.
    Only available in non-production environments for security.
    
    Args:
        request: The incoming request (required for rate limiting).
        
    Returns:
        Dict containing security component status information.
        
    Raises:
        HTTPException: 404 error in production environment.
        
    Rate Limits:
        5 requests per minute per IP address.
    """
    if settings.ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )
    
    from app.core.rate_limiting import advanced_rate_limiter
    from app.core.security import token_blacklist
    
    return {
        "rate_limiter_connected": advanced_rate_limiter.redis_client is not None,
        "token_blacklist_connected": token_blacklist.redis_client is not None,
        "security_headers_enabled": settings.SECURITY_HEADERS_ENABLED,
        "csp_enabled": settings.CSP_ENABLED,
        "environment": settings.ENV
    }


# WebSocket event handlers with security
@sio.event
async def connect(sid: str, environ: Dict[str, Any]) -> Optional[bool]:
    """Handle WebSocket connection with security logging and rate limiting.
    
    Implements:
    - IP-based connection rate limiting
    - Security event logging
    - Connection validation
    
    Args:
        sid: Socket session identifier.
        environ: WSGI environment dictionary containing connection details.
        
    Returns:
        bool: False to reject connection, None/True to accept.
        
    Security Features:
        - IP-based rate limiting for WebSocket connections
        - Connection attempt logging for audit
        - Automatic disconnection for rate-limited clients
    """
    client_ip = environ.get('REMOTE_ADDR', 'unknown')
    websocket_logger.info(
        "WebSocket connection established", 
        socket_id=sid, 
        client_ip=client_ip
    )
    
    # Basic connection rate limiting could be added here
    from app.core.rate_limiting import advanced_rate_limiter, RateLimitType
    
    is_allowed, _ = await advanced_rate_limiter.check_rate_limit(client_ip, RateLimitType.WEBSOCKET)
    
    if not is_allowed:
        websocket_logger.warning("WebSocket connection rate limited", client_ip=client_ip)
        await sio.disconnect(sid)
        return False

    return None


@sio.event
async def disconnect(sid: str) -> None:
    """Handle WebSocket disconnection with logging.
    
    Args:
        sid: Socket session identifier for the disconnecting client.
    """
    websocket_logger.info("WebSocket connection closed", socket_id=sid)


# Import broadcast functions from utilities
from app.core.broadcast_utils import broadcast_news, broadcast_urgent

# Configure broadcast service with WebSocket functions
broadcast_service.set_websocket_broadcaster(broadcast_news, broadcast_urgent)

# Create ASGI app with WebSocket support
asgi_app = ASGIApp(sio, other_asgi_app=app)


# Log security configuration on startup
@app.on_event("startup")
async def log_security_config() -> None:
    """Log security configuration for audit purposes.
    
    Records comprehensive security settings including:
    - Environment and debug configuration
    - Security headers and policies status
    - Authentication and session settings
    - Network security configuration (sanitized for production)
    
    Security Note:
        Sensitive configuration values are redacted in production logs.
    """
    main_logger.info(
        "Security configuration loaded",
        environment=settings.ENV,
        debug_mode=settings.DEBUG,
        security_headers=settings.SECURITY_HEADERS_ENABLED,
        csp_enabled=settings.CSP_ENABLED,
        hsts_max_age=settings.HSTS_MAX_AGE,
        allowed_hosts=settings.ALLOWED_HOSTS if settings.ENV != "production" else ["[REDACTED]"],
        cors_origins=len(cors_origins),
        access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )