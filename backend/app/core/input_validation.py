"""
Advanced input validation and sanitization system for security hardening
"""
import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator, Field
import bleach
from app.core.settings import settings
from app.core.logging import main_logger

class ValidationError(Exception):
    """Custom validation error"""
    pass

class InputSanitizer:
    """
    Advanced input sanitization to prevent XSS, injection attacks, and malicious content
    """
    
    # Allowed HTML tags for rich content (very restrictive)
    ALLOWED_TAGS = [
        'b', 'i', 'u', 'strong', 'em', 'p', 'br', 'span'
    ]
    
    # Allowed attributes for HTML tags
    ALLOWED_ATTRIBUTES = {
        '*': ['class'],
        'span': ['style']
    }
    
    # Allowed CSS properties (very limited)
    ALLOWED_STYLES = ['color', 'font-weight', 'text-decoration']
    
    @staticmethod
    def sanitize_html(content: str, allow_html: bool = False) -> str:
        """
        Sanitize HTML content to prevent XSS attacks
        
        Args:
            content: Raw content to sanitize
            allow_html: Whether to allow safe HTML tags
            
        Returns:
            Sanitized content
        """
        if not content:
            return ""
        
        if allow_html:
            # Use bleach for advanced HTML sanitization
            sanitized = bleach.clean(
                content,
                tags=InputSanitizer.ALLOWED_TAGS,
                attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
                styles=InputSanitizer.ALLOWED_STYLES,
                strip=True
            )
        else:
            # Strip all HTML and escape remaining content
            sanitized = bleach.clean(content, tags=[], strip=True)
            sanitized = html.escape(sanitized)
        
        return sanitized
    
    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        Sanitize and validate URLs to prevent malicious redirects
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL
            
        Raises:
            ValidationError: If URL is invalid or malicious
        """
        if not url:
            return ""
        
        # Basic URL validation
        url = url.strip()
        
        # Check for suspicious protocols
        suspicious_protocols = ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:']
        if any(url.lower().startswith(protocol) for protocol in suspicious_protocols):
            raise ValidationError(f"Suspicious URL protocol detected")
        
        # Ensure URL starts with http or https
        if not url.lower().startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Parse and validate URL structure
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.netloc:
                raise ValidationError("Invalid URL structure")
        except Exception:
            raise ValidationError("Invalid URL format")
        
        # Additional security checks
        if '..' in parsed.path or parsed.netloc.startswith('.'):
            raise ValidationError("Potentially malicious URL detected")
        
        return url
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Safe filename
        """
        if not filename:
            return ""
        
        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', '..', '~', '$', '&', '|', ';', '`', '<', '>', '"', "'"]
        sanitized = filename
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
        
        # Limit length
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """
        Sanitize search queries to prevent SQL injection and other attacks
        
        Args:
            query: Search query to sanitize
            
        Returns:
            Sanitized query
        """
        if not query:
            return ""
        
        # Remove SQL injection patterns
        sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
            r'(--|/\*|\*/)',
            r'(\bOR\b.*\=.*\=|\bAND\b.*\=.*\=)',
            r'(\bor\b.*\=.*\=|\band\b.*\=.*\=)'
        ]
        
        sanitized = query
        for pattern in sql_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validate and normalize email address
        
        Args:
            email: Email to validate
            
        Returns:
            Normalized email
            
        Raises:
            ValidationError: If email is invalid
        """
        if not email:
            raise ValidationError("Email is required")
        
        email = email.strip().lower()
        
        # Basic email regex (RFC 5322 compliant)
        email_pattern = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")
        
        # Additional security checks
        if len(email) > 254:  # RFC limit
            raise ValidationError("Email too long")
        
        local_part, domain = email.rsplit('@', 1)
        if len(local_part) > 64:  # RFC limit for local part
            raise ValidationError("Email local part too long")
        
        # Check for suspicious patterns
        suspicious_patterns = ['..', '..@', '@.', '@@']
        if any(pattern in email for pattern in suspicious_patterns):
            raise ValidationError("Suspicious email pattern detected")
        
        return email
    
    @staticmethod
    def validate_username(username: str) -> str:
        """
        Validate and normalize username
        
        Args:
            username: Username to validate
            
        Returns:
            Normalized username
            
        Raises:
            ValidationError: If username is invalid
        """
        if not username:
            raise ValidationError("Username is required")
        
        username = username.strip().lower()
        
        # Username validation rules
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters")
        
        if len(username) > 30:
            raise ValidationError("Username must be less than 30 characters")
        
        # Allow only alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValidationError("Username can only contain letters, numbers, hyphens, and underscores")
        
        # Prevent usernames that look like system accounts
        reserved_names = [
            'admin', 'administrator', 'root', 'system', 'api', 'www', 'mail', 
            'ftp', 'ssh', 'http', 'https', 'test', 'guest', 'anonymous'
        ]
        
        if username in reserved_names:
            raise ValidationError("Username is reserved")
        
        return username

# Base models with enhanced validation

class SecureBaseModel(BaseModel):
    """
    Base model with security-focused validation
    """
    
    class Config:
        # Validate all fields
        validate_all = True
        # Forbid extra fields
        extra = 'forbid'
        # Use enum values
        use_enum_values = True
        # Validate assignment
        validate_assignment = True
        # Strip whitespace
        anystr_strip_whitespace = True
        # Limit string length globally
        max_anystr_length = 10000

class PaginationModel(BaseModel):
    """Secure pagination model"""
    page: int = Field(default=1, ge=1, le=10000, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")
    
    @validator('page')
    def validate_page(cls, v):
        if v > 10000:  # Prevent excessive pagination
            raise ValueError('Page number too high')
        return v
    
    @validator('size')
    def validate_size(cls, v):
        if v > 100:  # Prevent excessive page sizes
            raise ValueError('Page size too large')
        return v

class SearchQueryModel(BaseModel):
    """Secure search query model"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    
    @validator('query')
    def sanitize_query(cls, v):
        return InputSanitizer.sanitize_search_query(v)

# Request size validation middleware
async def validate_request_size(request, call_next):
    """
    Middleware to validate request size and prevent DoS attacks
    """
    content_length = request.headers.get('content-length')
    
    if content_length:
        content_length = int(content_length)
        if content_length > settings.MAX_REQUEST_SIZE:
            main_logger.warning(
                f"Request size too large",
                size=content_length,
                limit=settings.MAX_REQUEST_SIZE,
                client_ip=request.client.host if request.client else "unknown"
            )
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
    
    response = await call_next(request)
    return response

# Content-Type validation
def validate_content_type(allowed_types: List[str]):
    """
    Decorator to validate request content type
    
    Args:
        allowed_types: List of allowed content types
    """
    def decorator(func):
        async def wrapper(request, *args, **kwargs):
            content_type = request.headers.get('content-type', '').lower()
            
            # Remove charset and other parameters
            content_type = content_type.split(';')[0].strip()
            
            if content_type not in allowed_types:
                main_logger.warning(
                    f"Invalid content type",
                    received=content_type,
                    allowed=allowed_types,
                    endpoint=request.url.path
                )
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported content type. Allowed: {', '.join(allowed_types)}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator