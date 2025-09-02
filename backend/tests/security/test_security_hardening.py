"""
Comprehensive security hardening tests for NEWRSS Phase 3
Tests all implemented security features and validates enterprise-grade security
"""
import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from httpx import AsyncClient
import redis.asyncio as aioredis

from app.core.settings import Settings
from app.core.security import (
    TokenBlacklist, create_access_token, verify_token, logout_token,
    validate_password_strength, initialize_security
)
from app.core.rate_limiting import (
    AdvancedRateLimiter, RateLimitType, initialize_rate_limiter
)
from app.core.input_validation import (
    InputSanitizer, ValidationError, SecureBaseModel
)
from app.core.security_headers import (
    SecurityHeadersMiddleware, detect_suspicious_patterns, SecurityEventLogger
)
from app.main import asgi_app

class TestProductionSecurityConfiguration:
    """Test production security configuration enforcement"""
    
    def test_production_secret_key_validation(self):
        """Test that production requires proper SECRET_KEY"""
        with pytest.raises(ValueError, match="SECRET_KEY must be changed"):
            Settings(
                ENV="production",
                SECRET_KEY="dev-secret-key-change-in-production"
            )
    
    def test_production_database_validation(self):
        """Test that production rejects SQLite"""
        with pytest.raises(ValueError, match="SQLite is not recommended"):
            Settings(
                ENV="production", 
                SECRET_KEY="very-secure-production-key-32-chars-long",
                DATABASE_URL="sqlite+aiosqlite:///./prod.db"
            )
    
    def test_production_cors_validation(self):
        """Test that production removes localhost from CORS"""
        settings = Settings(
            ENV="production",
            SECRET_KEY="very-secure-production-key-32-chars-long", 
            DATABASE_URL="postgresql://user:pass@localhost/db",
            CORS_ORIGINS=[
                "http://localhost:3000",
                "https://api.example.com",
                "https://app.example.com"
            ]
        )
        
        # Should remove localhost origins
        assert "http://localhost:3000" not in settings.CORS_ORIGINS
        assert "https://api.example.com" in settings.CORS_ORIGINS
    
    def test_debug_disabled_in_production(self):
        """Test that DEBUG is automatically disabled in production"""
        settings = Settings(
            ENV="production",
            SECRET_KEY="very-secure-production-key-32-chars-long",
            DATABASE_URL="postgresql://user:pass@localhost/db",
            DEBUG=True  # Should be overridden
        )
        
        assert settings.DEBUG is False

class TestJWTSecurityHardening:
    """Test JWT security enhancements"""
    
    @pytest.fixture
    def token_blacklist(self):
        """Create token blacklist instance for testing"""
        blacklist = TokenBlacklist()
        # Mock Redis for testing
        blacklist.redis_client = Mock()
        return blacklist
    
    @pytest.mark.asyncio
    async def test_token_blacklisting(self, token_blacklist):
        """Test token blacklisting functionality"""
        token = "test_token"
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Mock Redis operations
        token_blacklist.redis_client.setex.return_value = None
        token_blacklist.redis_client.get.return_value = "blacklisted"
        
        # Test blacklisting
        success = await token_blacklist.blacklist_token(token, expires_at)
        assert success is True
        
        # Test checking blacklist
        is_blacklisted = await token_blacklist.is_token_blacklisted(token)
        assert is_blacklisted is True
    
    def test_enhanced_token_creation(self):
        """Test enhanced JWT token creation with security claims"""
        token_data = create_access_token({"sub": "testuser"})
        
        assert "access_token" in token_data
        assert "expires_at" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"
        assert isinstance(token_data["expires_at"], datetime)
    
    @pytest.mark.asyncio
    async def test_token_verification_with_blacklist(self):
        """Test token verification includes blacklist checking"""
        token_data = create_access_token({"sub": "testuser"})
        token = token_data["access_token"]
        
        # Mock blacklist to return not blacklisted
        with patch('app.core.security.token_blacklist') as mock_blacklist:
            mock_blacklist.is_token_blacklisted.return_value = False
            
            payload = await verify_token(token)
            assert payload is not None
            assert payload["sub"] == "testuser"
            assert payload["type"] == "access"
    
    @pytest.mark.asyncio
    async def test_blacklisted_token_rejection(self):
        """Test that blacklisted tokens are rejected"""
        token_data = create_access_token({"sub": "testuser"})
        token = token_data["access_token"]
        
        # Mock blacklist to return blacklisted
        with patch('app.core.security.token_blacklist') as mock_blacklist:
            mock_blacklist.is_token_blacklisted.return_value = True
            
            payload = await verify_token(token)
            assert payload is None
    
    def test_password_strength_validation(self):
        """Test password strength validation"""
        # Weak passwords should fail
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "PASSWORD",
            "12345678",
            "Passw0rd"  # Missing special char
        ]
        
        for password in weak_passwords:
            is_valid, _ = validate_password_strength(password)
            assert is_valid is False
        
        # Strong password should pass
        is_valid, error = validate_password_strength("SecureP@ssw0rd123!")
        assert is_valid is True
        assert error == ""

class TestRateLimiting:
    """Test advanced rate limiting system"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance for testing"""
        limiter = AdvancedRateLimiter()
        # Mock Redis for testing
        limiter.redis_client = Mock()
        return limiter
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, rate_limiter):
        """Test rate limit enforcement"""
        identifier = "192.168.1.100"
        limit_type = RateLimitType.GENERAL_API
        
        # Mock Redis pipeline operations
        mock_pipe = Mock()
        mock_pipe.execute.return_value = [None, 5, None, None]  # 5 requests made
        rate_limiter.redis_client.pipeline.return_value = mock_pipe
        rate_limiter.redis_client.exists.return_value = False  # Not blocked
        
        is_allowed, info = await rate_limiter.check_rate_limit(identifier, limit_type)
        
        assert is_allowed is True
        assert info["requests_made"] == 5
        assert "limit" in info
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limiter):
        """Test rate limit exceeded handling"""
        identifier = "192.168.1.100"
        limit_type = RateLimitType.AUTHENTICATION
        
        # Mock Redis to return exceeded requests
        mock_pipe = Mock()
        mock_pipe.execute.return_value = [None, 15, None, None]  # 15 requests (over limit)
        rate_limiter.redis_client.pipeline.return_value = mock_pipe
        rate_limiter.redis_client.exists.return_value = False
        rate_limiter.redis_client.setex.return_value = None
        
        is_allowed, info = await rate_limiter.check_rate_limit(identifier, limit_type)
        
        assert is_allowed is False
        assert "error" in info
        assert info["error"] == "Rate limit exceeded"
    
    @pytest.mark.asyncio
    async def test_ip_blocking(self, rate_limiter):
        """Test IP blocking for severe violations"""
        identifier = "192.168.1.100"
        limit_type = RateLimitType.AUTHENTICATION
        
        # Mock Redis to return blocked status
        rate_limiter.redis_client.exists.return_value = True
        
        is_allowed, info = await rate_limiter.check_rate_limit(identifier, limit_type)
        
        assert is_allowed is False
        assert info["blocked"] is True
    
    @pytest.mark.asyncio
    async def test_burst_handling(self, rate_limiter):
        """Test burst capacity handling"""
        identifier = "192.168.1.100"
        limit_type = RateLimitType.GENERAL_API
        
        # Mock Redis to return burst-level requests
        mock_pipe = Mock()
        mock_pipe.execute.return_value = [None, 110, None, None]  # Within burst limit
        rate_limiter.redis_client.pipeline.return_value = mock_pipe
        rate_limiter.redis_client.exists.return_value = False
        
        is_allowed, info = await rate_limiter.check_rate_limit(identifier, limit_type)
        
        assert is_allowed is True
        assert info.get("burst_used") is True
        assert "warning" in info

class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_html_sanitization(self):
        """Test HTML content sanitization"""
        malicious_html = """
        <script>alert('xss')</script>
        <img src="x" onerror="alert('xss')">
        <p>Safe content</p>
        <a href="javascript:alert('xss')">Link</a>
        """
        
        # Without HTML allowed
        sanitized = InputSanitizer.sanitize_html(malicious_html, allow_html=False)
        assert "<script>" not in sanitized
        assert "alert('xss')" not in sanitized
        assert "Safe content" in sanitized
        
        # With safe HTML allowed
        sanitized_html = InputSanitizer.sanitize_html(malicious_html, allow_html=True)
        assert "<script>" not in sanitized_html
        assert "onerror=" not in sanitized_html
        assert "<p>Safe content</p>" in sanitized_html
    
    def test_url_sanitization(self):
        """Test URL sanitization and validation"""
        # Malicious URLs should be rejected
        malicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "file:///etc/passwd"
        ]
        
        for url in malicious_urls:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_url(url)
        
        # Safe URLs should be sanitized but allowed
        safe_url = "example.com/path"
        sanitized = InputSanitizer.sanitize_url(safe_url)
        assert sanitized.startswith("https://")
        assert "example.com/path" in sanitized
    
    def test_sql_injection_prevention(self):
        """Test SQL injection pattern removal"""
        malicious_queries = [
            "'; DROP TABLE users; --",
            "admin' OR '1'='1",
            "UNION SELECT * FROM passwords",
            "/* malicious comment */ SELECT"
        ]
        
        for query in malicious_queries:
            sanitized = InputSanitizer.sanitize_search_query(query)
            assert "DROP TABLE" not in sanitized.upper()
            assert "UNION SELECT" not in sanitized.upper()
            assert "'1'='1" not in sanitized
            assert "/*" not in sanitized
    
    def test_filename_sanitization(self):
        """Test filename sanitization"""
        malicious_filenames = [
            "../../../etc/passwd",
            "file|rm -rf /",
            "test<script>alert(1)</script>.txt",
            "file\x00.txt"
        ]
        
        for filename in malicious_filenames:
            sanitized = InputSanitizer.sanitize_filename(filename)
            assert ".." not in sanitized
            assert "/" not in sanitized
            assert "\\" not in sanitized
            assert "|" not in sanitized
            assert "<script>" not in sanitized
    
    def test_email_validation(self):
        """Test email validation"""
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user_name@domain-name.com"
        ]
        
        for email in valid_emails:
            validated = InputSanitizer.validate_email(email)
            assert "@" in validated
            assert validated == email.lower()
        
        # Invalid emails
        invalid_emails = [
            "not-an-email",
            "@domain.com",
            "user@",
            "user..double.dot@domain.com",
            "user@domain..com"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                InputSanitizer.validate_email(email)

class TestSecurityHeaders:
    """Test security headers middleware"""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request for testing"""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.url.scheme = "https"
        request.method = "GET"
        request.headers = {"user-agent": "test-client"}
        return request
    
    def test_security_headers_applied(self):
        """Test that security headers are applied correctly"""
        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)
        
        # Check that security headers are configured
        expected_headers = [
            "X-XSS-Protection",
            "X-Content-Type-Options", 
            "X-Frame-Options",
            "Referrer-Policy",
            "Permissions-Policy"
        ]
        
        for header in expected_headers:
            assert header in middleware.security_headers
    
    def test_csp_header_generation(self):
        """Test CSP header generation"""
        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app, enable_csp=True)
        
        request = Mock()
        request.url.path = "/api/test"
        
        csp_header = middleware._build_csp_header(request)
        
        assert "default-src 'self'" in csp_header
        assert "script-src" in csp_header
        assert "object-src 'none'" in csp_header
        assert "frame-ancestors 'none'" in csp_header
    
    def test_hsts_header_generation(self):
        """Test HSTS header generation"""
        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)
        
        hsts_header = middleware._build_hsts_header()
        
        assert "max-age=" in hsts_header
        assert "includeSubDomains" in hsts_header
        assert "preload" in hsts_header
    
    def test_suspicious_pattern_detection(self):
        """Test suspicious pattern detection"""
        # Create mock request with suspicious patterns
        request = Mock(spec=Request)
        request.url.path = "/api/test/../admin"
        request.query_params = Mock()
        request.query_params.__str__.return_value = "param='; DROP TABLE users; --"
        request.headers = {"user-agent": "sqlmap/1.0"}
        
        patterns = detect_suspicious_patterns(request)
        
        assert len(patterns) > 0
        assert any("Directory traversal" in pattern for pattern in patterns)
        assert any("SQL injection" in pattern for pattern in patterns) 
        assert any("Suspicious user agent" in pattern for pattern in patterns)

class TestSecurityIntegration:
    """Test integrated security features"""
    
    @pytest.mark.asyncio
    async def test_authentication_rate_limiting(self):
        """Test that authentication endpoints have rate limiting"""
        async with AsyncClient(app=asgi_app, base_url="http://testserver") as client:
            # Make multiple authentication requests
            login_data = {"username": "testuser", "password": "testpass"}
            
            responses = []
            for _ in range(15):  # Exceed auth rate limit
                response = await client.post("/auth/token", data=login_data)
                responses.append(response.status_code)
            
            # Should eventually get rate limited
            assert 429 in responses  # Too Many Requests
    
    @pytest.mark.asyncio
    async def test_security_headers_in_response(self):
        """Test that security headers are present in responses"""
        async with AsyncClient(app=asgi_app, base_url="http://testserver") as client:
            response = await client.get("/health")
            
            # Check for security headers
            security_headers = [
                "x-content-type-options",
                "x-frame-options", 
                "x-xss-protection",
                "referrer-policy"
            ]
            
            for header in security_headers:
                assert header in response.headers
    
    @pytest.mark.asyncio
    async def test_input_validation_in_endpoints(self):
        """Test that endpoints validate and sanitize input"""
        async with AsyncClient(app=asgi_app, base_url="http://testserver") as client:
            # Test with malicious search query
            malicious_query = "<script>alert('xss')</script>"
            
            response = await client.get(f"/news/search?query={malicious_query}")
            
            # Should handle malicious input gracefully
            assert response.status_code in [400, 422]  # Bad request or validation error
    
    @pytest.mark.asyncio 
    async def test_websocket_rate_limiting(self):
        """Test WebSocket connection rate limiting"""
        # This would require more complex WebSocket testing setup
        # For now, we'll test the rate limiter component directly
        
        limiter = AdvancedRateLimiter()
        limiter.redis_client = Mock()
        limiter.redis_client.exists.return_value = False
        
        mock_pipe = Mock()
        mock_pipe.execute.return_value = [None, 1001, None, None]  # Over WebSocket limit
        limiter.redis_client.pipeline.return_value = mock_pipe
        
        is_allowed, info = await limiter.check_rate_limit("test_ip", RateLimitType.WEBSOCKET)
        
        # Should be rate limited for excessive WebSocket connections
        assert is_allowed is False

class TestSecurityCompliance:
    """Test security compliance and best practices"""
    
    def test_password_requirements_met(self):
        """Test that password requirements meet security standards"""
        # Test various password requirements
        requirements = [
            ("length", "SecureP@ssw0rd123!", True),
            ("uppercase", "securep@ssw0rd123!", False),
            ("lowercase", "SECUREP@SSW0RD123!", False), 
            ("digits", "SecureP@ssword!", False),
            ("special", "SecurePassword123", False),
            ("complete", "SecureP@ssw0rd123!", True)
        ]
        
        for test_name, password, should_pass in requirements:
            is_valid, _ = validate_password_strength(password)
            if should_pass:
                assert is_valid, f"Password should pass {test_name} requirement"
            else:
                assert not is_valid, f"Password should fail {test_name} requirement"
    
    def test_session_security_configuration(self):
        """Test session and token security configuration"""
        from app.core.settings import settings
        
        # Tokens should have reasonable expiration
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 60, "Access tokens should expire within 1 hour"
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS <= 30, "Refresh tokens should expire within 30 days"
        
        # JWT algorithm should be secure
        assert settings.JWT_ALGORITHM == "HS256", "Should use secure JWT algorithm"
    
    def test_cors_security_configuration(self):
        """Test CORS security configuration"""
        from app.core.settings import settings
        
        # CORS should not allow all origins in production
        if settings.ENV == "production":
            assert "*" not in settings.CORS_ORIGINS, "Production should not allow all CORS origins"
            
            # Should not include localhost in production
            localhost_origins = [origin for origin in settings.CORS_ORIGINS if "localhost" in origin]
            assert len(localhost_origins) == 0, "Production should not include localhost origins"

@pytest.mark.asyncio
async def test_comprehensive_security_stack():
    """Test the complete security stack integration"""
    async with AsyncClient(app=asgi_app, base_url="http://testserver") as client:
        # Test security status endpoint (should be disabled in production)
        response = await client.get("/security/status")
        
        if response.status_code == 200:
            # Development environment
            security_status = response.json()
            
            # Check security components are initialized
            assert "rate_limiter_connected" in security_status
            assert "token_blacklist_connected" in security_status
            assert "security_headers_enabled" in security_status
        else:
            # Production environment - endpoint should be disabled
            assert response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__, "-v"])