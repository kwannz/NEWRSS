from pydantic_settings import BaseSettings
from pydantic import AnyUrl, validator, Field
from typing import List, Optional, Union
import os
import secrets

class Settings(BaseSettings):
    ENV: str = "dev"
    DEBUG: bool = Field(default=True, description="Debug mode - auto-disabled in production")
    
    # Core Security Settings - Required in production
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT signing - MUST be changed in production"
    )
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./newrss.db",
        description="Database connection URL - MUST be configured for production"
    )
    
    # Production Host Security
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "0.0.0.0"],
        description="Allowed hosts for production deployment"
    )
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "http://localhost:8000", 
        "http://127.0.0.1:8000"
    ]
    
    # Infrastructure
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # External Service Tokens
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_SECRET_TOKEN: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # JWT Security Configuration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Shortened for security
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Separate refresh token expiration
    JWT_ALGORITHM: str = "HS256"           # Enforced algorithm
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console
    
    # Exchange API configuration
    BINANCE_API_KEY: Optional[str] = None
    COINBASE_API_KEY: Optional[str] = None
    OKX_API_KEY: Optional[str] = None
    COINGECKO_API_KEY: Optional[str] = None
    
    # Rate limiting settings
    EXCHANGE_API_RATE_LIMIT: int = 60  # requests per minute
    PRICE_UPDATE_INTERVAL: int = 30    # seconds between price updates
    
    # Security Rate Limiting
    API_RATE_LIMIT_PER_MINUTE: int = 100
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10
    BROADCAST_RATE_LIMIT_PER_MINUTE: int = 60
    
    # Market impact analysis settings
    PRICE_ALERT_THRESHOLD: float = 5.0  # Percent change threshold for alerts
    VOLATILITY_THRESHOLD: float = 10.0  # High volatility threshold
    MARKET_IMPACT_COOLDOWN: int = 300   # 5 minutes between impact analyses
    
    # Security Headers Configuration
    SECURITY_HEADERS_ENABLED: bool = True
    CSP_ENABLED: bool = True
    HSTS_MAX_AGE: int = 31536000  # 1 year
    
    # Request Security Limits
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_FIELD_SIZE: int = 1024 * 1024         # 1MB
    
    @validator('SECRET_KEY')
    def validate_secret_key_production(cls, v, values):
        """Ensure SECRET_KEY is properly configured for production"""
        env = values.get('ENV', 'dev')
        if env == 'production' and v in ['your-secret-key-change-in-production', 'dev-secret-key-change-in-production']:
            raise ValueError("SECRET_KEY must be changed for production deployment")
        if env == 'production' and len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        return v
    
    @validator('DATABASE_URL')
    def validate_database_production(cls, v, values):
        """Ensure DATABASE_URL is properly configured for production"""
        env = values.get('ENV', 'dev')
        if env == 'production' and 'sqlite' in v.lower():
            raise ValueError("SQLite is not recommended for production. Use PostgreSQL instead.")
        return v
    
    @validator('DEBUG')
    def disable_debug_in_production(cls, v, values):
        """Automatically disable debug mode in production"""
        env = values.get('ENV', 'dev')
        if env == 'production':
            return False
        return v
    
    @validator('CORS_ORIGINS')
    def validate_cors_production(cls, v, values):
        """Validate CORS origins for production"""
        env = values.get('ENV', 'dev')
        if env == 'production':
            # Remove localhost origins in production
            production_origins = [origin for origin in v if 'localhost' not in origin and '127.0.0.1' not in origin]
            if not production_origins:
                raise ValueError("CORS_ORIGINS must contain production domains, not localhost")
            return production_origins
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

# Generate secure secret key for development if none provided
def generate_secret_key() -> str:
    """Generate a secure secret key for development"""
    return secrets.token_urlsafe(32)

# Initialize settings with security validation
settings = Settings()

# Auto-generate secret key for development
if settings.ENV == "dev" and settings.SECRET_KEY == "dev-secret-key-change-in-production":
    settings.SECRET_KEY = generate_secret_key()