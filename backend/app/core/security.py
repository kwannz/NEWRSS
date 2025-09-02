"""
Enhanced security module with JWT token blacklisting and security utilities
"""
from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import redis.asyncio as aioredis
import json
import hashlib
import secrets
from app.core.settings import settings
from app.core.logging import main_logger

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenBlacklist:
    """
    Redis-backed token blacklist for secure logout and token revocation
    """
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self._prefix = "blacklisted_token:"
    
    async def initialize(self):
        """Initialize Redis connection for token blacklisting"""
        try:
            self.redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            main_logger.info("Token blacklist Redis connection established")
        except Exception as e:
            main_logger.error(f"Failed to initialize token blacklist Redis: {e}")
            self.redis_client = None
    
    def _get_token_key(self, token_hash: str) -> str:
        """Generate Redis key for blacklisted token"""
        return f"{self._prefix}{token_hash}"
    
    def _hash_token(self, token: str) -> str:
        """Create hash of token for storage (avoid storing raw tokens)"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def blacklist_token(self, token: str, expires_at: datetime) -> bool:
        """
        Add token to blacklist with expiration
        
        Args:
            token: JWT token to blacklist
            expires_at: When the token naturally expires
        
        Returns:
            bool: True if successfully blacklisted
        """
        if not self.redis_client:
            main_logger.warning("Token blacklist not available - Redis not connected")
            return False
        
        try:
            token_hash = self._hash_token(token)
            key = self._get_token_key(token_hash)
            
            # Calculate TTL (time until token naturally expires)
            now = datetime.utcnow()
            if expires_at > now:
                ttl_seconds = int((expires_at - now).total_seconds())
                await self.redis_client.setex(key, ttl_seconds, "blacklisted")
                main_logger.info(f"Token blacklisted successfully", token_hash=token_hash[:8])
                return True
            else:
                main_logger.info("Token already expired, not blacklisting", token_hash=token_hash[:8])
                return True
                
        except Exception as e:
            main_logger.error(f"Failed to blacklist token: {e}")
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted
        
        Args:
            token: JWT token to check
            
        Returns:
            bool: True if token is blacklisted
        """
        if not self.redis_client:
            # If Redis is not available, assume token is not blacklisted
            # This maintains availability but reduces security
            main_logger.warning("Token blacklist check skipped - Redis not connected")
            return False
        
        try:
            token_hash = self._hash_token(token)
            key = self._get_token_key(token_hash)
            
            result = await self.redis_client.get(key)
            is_blacklisted = result is not None
            
            if is_blacklisted:
                main_logger.info("Blocked blacklisted token access", token_hash=token_hash[:8])
            
            return is_blacklisted
            
        except Exception as e:
            main_logger.error(f"Failed to check token blacklist: {e}")
            # On error, assume token is not blacklisted to maintain availability
            return False
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from blacklist (Redis handles this automatically with TTL)
        This method is for monitoring/stats purposes
        
        Returns:
            int: Number of tokens still in blacklist
        """
        if not self.redis_client:
            return 0
        
        try:
            pattern = f"{self._prefix}*"
            keys = await self.redis_client.keys(pattern)
            return len(keys)
        except Exception as e:
            main_logger.error(f"Failed to count blacklisted tokens: {e}")
            return 0

# Global token blacklist instance
token_blacklist = TokenBlacklist()

# Enhanced JWT functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> dict:
    """
    Create JWT access token with enhanced security
    
    Returns dict with token and expiration info for blacklisting
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add security claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": secrets.token_hex(16)  # JWT ID for tracking
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return {
        "access_token": encoded_jwt,
        "expires_at": expire,
        "token_type": "bearer"
    }

def create_refresh_token(data: dict) -> dict:
    """
    Create JWT refresh token with longer expiration
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": secrets.token_hex(16)  # JWT ID for tracking
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return {
        "refresh_token": encoded_jwt,
        "expires_at": expire
    }

async def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Enhanced token verification with blacklist checking
    
    Args:
        token: JWT token to verify
        token_type: Expected token type (access/refresh)
    
    Returns:
        dict: Token payload if valid, None if invalid
    """
    try:
        if not token:
            return None
        
        # Check if token is blacklisted
        if await token_blacklist.is_token_blacklisted(token):
            main_logger.warning("Attempted use of blacklisted token")
            return None
        
        # Decode and verify token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            main_logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None
        
        # Verify required claims
        username: str = payload.get("sub")
        if username is None:
            main_logger.warning("Token missing 'sub' claim")
            return None
        
        # Verify expiration
        exp = payload.get("exp")
        if not exp or datetime.utcfromtimestamp(exp) < datetime.utcnow():
            main_logger.info("Token expired")
            return None
        
        return payload
        
    except JWTError as e:
        main_logger.warning(f"JWT verification failed: {e}")
        return None
    except Exception as e:
        main_logger.error(f"Token verification error: {e}")
        return None

async def logout_token(token: str) -> bool:
    """
    Logout by blacklisting the token
    
    Args:
        token: JWT token to logout
        
    Returns:
        bool: True if successfully logged out
    """
    try:
        # Decode token to get expiration
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        exp = payload.get("exp")
        
        if exp:
            expires_at = datetime.utcfromtimestamp(exp)
            return await token_blacklist.blacklist_token(token, expires_at)
        else:
            main_logger.error("Token missing expiration claim")
            return False
            
    except JWTError as e:
        main_logger.warning(f"Cannot logout invalid token: {e}")
        return False
    except Exception as e:
        main_logger.error(f"Logout error: {e}")
        return False

# Security utility functions
def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, ""

# Initialize token blacklist on module import
async def initialize_security():
    """Initialize security components"""
    await token_blacklist.initialize()