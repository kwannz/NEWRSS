"""
Security headers middleware for comprehensive protection against web attacks
"""
from typing import Dict, Optional, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.settings import settings
from app.core.logging import main_logger

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add comprehensive security headers to all responses
    """
    
    def __init__(self, app, enable_csp: bool = True, enable_hsts: bool = True):
        super().__init__(app)
        self.enable_csp = enable_csp and settings.CSP_ENABLED
        self.enable_hsts = enable_hsts
        
        # Content Security Policy configuration
        self.csp_directives = {
            "default-src": ["'self'"],
            "script-src": [
                "'self'", 
                "'unsafe-inline'",  # Required for some inline scripts, consider removing
                "cdn.socket.io",
                "https:",
            ],
            "style-src": [
                "'self'", 
                "'unsafe-inline'",  # Required for inline styles
                "fonts.googleapis.com",
                "https:",
            ],
            "font-src": [
                "'self'",
                "fonts.gstatic.com",
                "data:",
            ],
            "img-src": [
                "'self'",
                "data:",
                "https:",
                "blob:",
            ],
            "connect-src": [
                "'self'",
                "wss:",
                "ws:",
                "https://api.openai.com",  # For AI features
                "https://api.telegram.org",  # For Telegram integration
            ],
            "frame-src": ["'none'"],
            "object-src": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "upgrade-insecure-requests": [],
            "block-all-mixed-content": [],
        }
        
        # Security headers configuration
        self.security_headers = {
            # XSS Protection
            "X-XSS-Protection": "1; mode=block",
            
            # Content Type Sniffing Protection
            "X-Content-Type-Options": "nosniff",
            
            # Clickjacking Protection
            "X-Frame-Options": "DENY",
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Download Options (IE)
            "X-Download-Options": "noopen",
            
            # Cross-Origin Policies
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "cross-origin",
            
            # Feature Policy / Permissions Policy
            "Permissions-Policy": self._build_permissions_policy(),
            
            # Remove server information
            "Server": "NEWRSS-API",
            
            # Cache Control for sensitive endpoints
            # Will be overridden per endpoint as needed
        }
    
    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy header value"""
        policies = [
            "camera=()",
            "microphone=()",
            "geolocation=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
            "ambient-light-sensor=()",
            "autoplay=(self)",
            "encrypted-media=(self)",
            "fullscreen=(self)",
            "picture-in-picture=()",
        ]
        return ", ".join(policies)
    
    def _build_csp_header(self, request: Request) -> str:
        """Build Content Security Policy header value"""
        directives = []
        
        # Add nonce for dynamic scripts if needed
        # nonce = secrets.token_urlsafe(16)
        # request.state.csp_nonce = nonce
        
        for directive, sources in self.csp_directives.items():
            if sources:
                directive_value = f"{directive} {' '.join(sources)}"
            else:
                directive_value = directive
            directives.append(directive_value)
        
        return "; ".join(directives)
    
    def _build_hsts_header(self) -> str:
        """Build HTTP Strict Transport Security header"""
        return f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains; preload"
    
    def _should_add_hsts(self, request: Request) -> bool:
        """Determine if HSTS header should be added"""
        # Only add HSTS for HTTPS requests in production
        return (
            self.enable_hsts and 
            (request.url.scheme == "https" or settings.ENV == "production")
        )
    
    def _get_cache_control_for_path(self, path: str) -> Optional[str]:
        """Get appropriate cache control header for different paths"""
        # Security-sensitive endpoints should not be cached
        security_paths = ["/auth/", "/api/users/", "/api/admin/"]
        if any(security_path in path for security_path in security_paths):
            return "no-cache, no-store, must-revalidate, private"
        
        # API endpoints - short cache
        if path.startswith("/api/"):
            return "public, max-age=60"
        
        # Static assets - longer cache
        if path.startswith("/static/"):
            return "public, max-age=86400"
        
        # Default - short cache
        return "public, max-age=300"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers to response"""
        
        # Log security-relevant request info
        if settings.ENV != "dev":
            main_logger.debug(
                "Security headers processing request",
                method=request.method,
                path=request.url.path,
                user_agent=request.headers.get("user-agent", "")[:100],
                x_forwarded_for=request.headers.get("x-forwarded-for", ""),
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add security headers only if enabled in settings
        if not settings.SECURITY_HEADERS_ENABLED:
            return response
        
        # Add standard security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Add Content Security Policy
        if self.enable_csp:
            csp_header = self._build_csp_header(request)
            response.headers["Content-Security-Policy"] = csp_header
            # Also add report-only header for monitoring
            # response.headers["Content-Security-Policy-Report-Only"] = csp_header
        
        # Add HSTS header for HTTPS
        if self._should_add_hsts(request):
            response.headers["Strict-Transport-Security"] = self._build_hsts_header()
        
        # Add appropriate cache control
        cache_control = self._get_cache_control_for_path(request.url.path)
        if cache_control:
            response.headers["Cache-Control"] = cache_control
        
        # Add security-related headers based on response type
        if response.headers.get("content-type", "").startswith("application/json"):
            # For API responses, add additional security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-API-Version"] = "1.0"
        
        # Remove potentially sensitive server headers
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]
        
        return response

class SecurityEventLogger:
    """
    Logger for security events and suspicious activities
    """
    
    @staticmethod
    def log_suspicious_request(request: Request, reason: str, severity: str = "medium"):
        """Log suspicious request activity"""
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        user_agent = request.headers.get("user-agent", "unknown")
        
        main_logger.warning(
            f"Suspicious request detected",
            reason=reason,
            severity=severity,
            client_ip=client_ip,
            user_agent=user_agent[:200],  # Truncate long user agents
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
        )
    
    @staticmethod
    def log_authentication_failure(username: str, request: Request, reason: str):
        """Log authentication failure with context"""
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        
        main_logger.warning(
            f"Authentication failure",
            username=username,
            reason=reason,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent", "unknown")[:200],
            timestamp=request.state.request_start_time if hasattr(request.state, 'request_start_time') else None,
        )
    
    @staticmethod
    def log_rate_limit_violation(identifier: str, endpoint: str, limit_type: str):
        """Log rate limit violations"""
        main_logger.warning(
            f"Rate limit violation",
            identifier=identifier[:8] + "..." if len(identifier) > 8 else identifier,
            endpoint=endpoint,
            limit_type=limit_type,
        )
    
    @staticmethod
    def log_input_validation_failure(field: str, value: str, reason: str, request: Request):
        """Log input validation failures"""
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        
        main_logger.warning(
            f"Input validation failure",
            field=field,
            value=value[:100] if len(value) > 100 else value,  # Truncate long values
            reason=reason,
            client_ip=client_ip,
            path=request.url.path,
        )
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict, severity: str = "medium", request: Optional[Request] = None):
        """Log general security events"""
        log_data = {
            "event_type": event_type,
            "severity": severity,
            **details
        }
        
        if request:
            log_data.update({
                "client_ip": request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown"),
                "user_agent": request.headers.get("user-agent", "unknown")[:200],
                "path": request.url.path,
                "method": request.method,
            })
        
        main_logger.warning(f"Security event: {event_type}", **log_data)

# Security monitoring functions
def detect_suspicious_patterns(request: Request) -> List[str]:
    """
    Detect suspicious patterns in requests
    
    Returns:
        List of detected suspicious patterns
    """
    suspicious_patterns = []
    
    # Check for SQL injection patterns in query parameters
    query_string = str(request.query_params).lower()
    sql_patterns = [
        'union', 'select', 'insert', 'delete', 'drop', 'exec',
        '\'', '"', '--', '/*', '*/', ';'
    ]
    
    for pattern in sql_patterns:
        if pattern in query_string:
            suspicious_patterns.append(f"SQL injection pattern: {pattern}")
    
    # Check for XSS patterns
    xss_patterns = ['<script', 'javascript:', 'on', 'expression(']
    for pattern in xss_patterns:
        if pattern in query_string:
            suspicious_patterns.append(f"XSS pattern: {pattern}")
    
    # Check for directory traversal
    if '..' in request.url.path or '~' in request.url.path:
        suspicious_patterns.append("Directory traversal attempt")
    
    # Check for suspicious user agents
    user_agent = request.headers.get("user-agent", "").lower()
    suspicious_agents = ['sqlmap', 'nmap', 'nikto', 'dirbuster', 'gobuster', 'burp']
    
    for agent in suspicious_agents:
        if agent in user_agent:
            suspicious_patterns.append(f"Suspicious user agent: {agent}")
    
    # Check for excessive headers (potential DoS)
    if len(request.headers) > 50:
        suspicious_patterns.append("Excessive headers count")
    
    # Check for suspicious referers
    referer = request.headers.get("referer", "").lower()
    if referer and any(suspicious in referer for suspicious in ['malware', 'phishing', 'spam']):
        suspicious_patterns.append("Suspicious referer")
    
    return suspicious_patterns

async def security_monitoring_middleware(request: Request, call_next):
    """
    Middleware for security monitoring and threat detection
    """
    import time
    start_time = time.time()
    request.state.request_start_time = start_time
    
    # Detect suspicious patterns
    suspicious_patterns = detect_suspicious_patterns(request)
    
    if suspicious_patterns:
        SecurityEventLogger.log_suspicious_request(
            request, 
            f"Multiple suspicious patterns: {', '.join(suspicious_patterns)}", 
            severity="high"
        )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log slow requests (potential DoS)
        request_duration = time.time() - start_time
        if request_duration > 5.0:  # 5 seconds threshold
            SecurityEventLogger.log_security_event(
                "slow_request",
                {
                    "duration": request_duration,
                    "endpoint": request.url.path,
                    "method": request.method
                },
                severity="medium",
                request=request
            )
        
        return response
        
    except Exception as e:
        # Log any exceptions that might indicate attacks
        SecurityEventLogger.log_security_event(
            "request_exception",
            {
                "error": str(e),
                "error_type": type(e).__name__,
            },
            severity="high",
            request=request
        )
        raise

# Global security event logger instance
security_logger = SecurityEventLogger()