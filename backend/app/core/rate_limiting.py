"""
Advanced rate limiting system with Redis backend and intelligent throttling
"""
from typing import Optional, Dict, Any, Callable
import time
import asyncio
from dataclasses import dataclass
from enum import Enum
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as aioredis
from app.core.settings import settings
from app.core.logging import main_logger

class RateLimitType(Enum):
    """Different types of rate limits"""
    GENERAL_API = "general_api"
    AUTHENTICATION = "auth"
    BROADCAST = "broadcast" 
    REGISTRATION = "registration"
    PASSWORD_RESET = "password_reset"
    WEBSOCKET = "websocket"

@dataclass
class RateLimitRule:
    """Rate limit configuration"""
    requests: int
    window: int  # seconds
    burst_multiplier: float = 1.5
    block_duration: int = 300  # 5 minutes default block

# Rate limit configurations
RATE_LIMIT_RULES: Dict[RateLimitType, RateLimitRule] = {
    RateLimitType.GENERAL_API: RateLimitRule(
        requests=settings.API_RATE_LIMIT_PER_MINUTE,
        window=60,
        burst_multiplier=1.2,
        block_duration=300
    ),
    RateLimitType.AUTHENTICATION: RateLimitRule(
        requests=settings.AUTH_RATE_LIMIT_PER_MINUTE,
        window=60,
        burst_multiplier=1.0,  # No burst for auth
        block_duration=900  # 15 minutes for auth violations
    ),
    RateLimitType.BROADCAST: RateLimitRule(
        requests=settings.BROADCAST_RATE_LIMIT_PER_MINUTE,
        window=60,
        burst_multiplier=1.3,
        block_duration=180
    ),
    RateLimitType.REGISTRATION: RateLimitRule(
        requests=5,  # Very restrictive for registration
        window=300,  # 5 minutes
        burst_multiplier=1.0,
        block_duration=3600  # 1 hour
    ),
    RateLimitType.PASSWORD_RESET: RateLimitRule(
        requests=3,
        window=300,  # 5 minutes
        burst_multiplier=1.0,
        block_duration=1800  # 30 minutes
    ),
    RateLimitType.WEBSOCKET: RateLimitRule(
        requests=1000,  # High limit for websocket connections
        window=60,
        burst_multiplier=2.0,
        block_duration=60
    )
}

class AdvancedRateLimiter:
    """
    Advanced rate limiter with Redis backend and intelligent features
    """
    
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self._prefix = "rate_limit:"
        self._block_prefix = "blocked_ip:"
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8", 
                decode_responses=True
            )
            await self.redis_client.ping()
            main_logger.info("Rate limiter Redis connection established")
        except Exception as e:
            main_logger.error(f"Failed to initialize rate limiter Redis: {e}")
            self.redis_client = None
    
    def _get_key(self, identifier: str, limit_type: RateLimitType) -> str:
        """Generate Redis key for rate limit tracking"""
        return f"{self._prefix}{limit_type.value}:{identifier}"
    
    def _get_block_key(self, identifier: str, limit_type: RateLimitType) -> str:
        """Generate Redis key for IP blocking"""
        return f"{self._block_prefix}{limit_type.value}:{identifier}"
    
    async def is_blocked(self, identifier: str, limit_type: RateLimitType) -> bool:
        """Check if identifier is currently blocked"""
        if not self.redis_client:
            return False
        
        try:
            block_key = self._get_block_key(identifier, limit_type)
            is_blocked = await self.redis_client.exists(block_key)
            return bool(is_blocked)
        except Exception as e:
            main_logger.error(f"Error checking block status: {e}")
            return False
    
    async def block_identifier(self, identifier: str, limit_type: RateLimitType, duration: int):
        """Block an identifier for specified duration"""
        if not self.redis_client:
            return
        
        try:
            block_key = self._get_block_key(identifier, limit_type)
            await self.redis_client.setex(block_key, duration, "blocked")
            main_logger.warning(
                f"Blocked identifier due to rate limit violation",
                identifier=identifier[:8] + "...",  # Partial IP for privacy
                limit_type=limit_type.value,
                duration=duration
            )
        except Exception as e:
            main_logger.error(f"Error blocking identifier: {e}")
    
    async def check_rate_limit(self, identifier: str, limit_type: RateLimitType) -> tuple[bool, Dict[str, Any]]:
        """
        Check rate limit for identifier
        
        Returns:
            tuple: (is_allowed, info_dict)
        """
        rule = RATE_LIMIT_RULES[limit_type]
        
        # Check if blocked first
        if await self.is_blocked(identifier, limit_type):
            return False, {
                "error": "IP temporarily blocked due to rate limit violations",
                "retry_after": rule.block_duration,
                "blocked": True
            }
        
        if not self.redis_client:
            # Fallback: allow if Redis unavailable (maintain availability)
            main_logger.warning("Rate limit check skipped - Redis unavailable")
            return True, {"fallback": True}
        
        try:
            key = self._get_key(identifier, limit_type)
            current_time = int(time.time())
            window_start = current_time - rule.window
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry on the key
            pipe.expire(key, rule.window + 60)  # Extra buffer
            
            results = await pipe.execute()
            current_count = results[1]
            
            # Calculate dynamic limit (burst handling)
            burst_limit = int(rule.requests * rule.burst_multiplier)
            
            # Determine if request is allowed
            if current_count <= rule.requests:
                # Normal operation
                return True, {
                    "requests_made": current_count,
                    "limit": rule.requests,
                    "window": rule.window,
                    "burst_available": burst_limit - current_count
                }
            elif current_count <= burst_limit:
                # Within burst limit
                return True, {
                    "requests_made": current_count,
                    "limit": rule.requests,
                    "burst_used": True,
                    "window": rule.window,
                    "warning": "Using burst capacity"
                }
            else:
                # Rate limit exceeded - block if severe violation
                if current_count > burst_limit * 2:
                    await self.block_identifier(identifier, limit_type, rule.block_duration)
                
                return False, {
                    "error": "Rate limit exceeded",
                    "requests_made": current_count,
                    "limit": rule.requests,
                    "retry_after": rule.window,
                    "burst_limit": burst_limit
                }
                
        except Exception as e:
            main_logger.error(f"Rate limit check error: {e}")
            # On error, allow request to maintain availability
            return True, {"error_fallback": True}
    
    async def get_rate_limit_status(self, identifier: str, limit_type: RateLimitType) -> Dict[str, Any]:
        """Get current rate limit status for identifier"""
        if not self.redis_client:
            return {"status": "unavailable"}
        
        try:
            rule = RATE_LIMIT_RULES[limit_type]
            key = self._get_key(identifier, limit_type)
            current_time = int(time.time())
            window_start = current_time - rule.window
            
            # Count requests in current window
            request_count = await self.redis_client.zcount(key, window_start, current_time)
            
            # Check if blocked
            blocked = await self.is_blocked(identifier, limit_type)
            
            return {
                "requests_made": request_count,
                "limit": rule.requests,
                "window": rule.window,
                "blocked": blocked,
                "remaining": max(0, rule.requests - request_count),
                "reset_time": current_time + rule.window
            }
            
        except Exception as e:
            main_logger.error(f"Error getting rate limit status: {e}")
            return {"status": "error"}

# Global rate limiter instance
advanced_rate_limiter = AdvancedRateLimiter()

# Standard SlowAPI limiter for basic rate limiting
def get_identifier(request: Request) -> str:
    """Get identifier for rate limiting (IP address)"""
    # Try to get real IP from headers (for reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return get_remote_address(request)

# SlowAPI limiter instance
limiter = Limiter(key_func=get_identifier)

# Rate limit decorator factory
def rate_limit(limit_type: RateLimitType):
    """
    Decorator for advanced rate limiting
    """
    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            identifier = get_identifier(request)
            
            is_allowed, info = await advanced_rate_limiter.check_rate_limit(identifier, limit_type)
            
            if not is_allowed:
                # Add rate limit headers
                headers = {
                    "X-RateLimit-Limit": str(RATE_LIMIT_RULES[limit_type].requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + RATE_LIMIT_RULES[limit_type].window)
                }
                
                if info.get("blocked"):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="IP temporarily blocked due to rate limit violations",
                        headers=headers
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=info.get("error", "Rate limit exceeded"),
                        headers=headers
                    )
            
            # Add rate limit info to request
            request.state.rate_limit_info = info
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

# Custom rate limit exceeded handler
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded"""
    identifier = get_identifier(request)
    main_logger.warning(
        f"Rate limit exceeded",
        identifier=identifier[:8] + "...",  # Partial IP for privacy
        endpoint=request.url.path,
        method=request.method
    )
    
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Please slow down your requests.",
        headers={
            "X-RateLimit-Limit": str(exc.detail.split()[0]) if exc.detail else "unknown",
            "Retry-After": "60"
        }
    )

# Initialize rate limiter
async def initialize_rate_limiter():
    """Initialize the advanced rate limiter"""
    await advanced_rate_limiter.initialize()