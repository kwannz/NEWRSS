from pydantic_settings import BaseSettings
from pydantic import AnyUrl
from typing import List, Optional, Union

class Settings(BaseSettings):
    ENV: str = "dev"
    DATABASE_URL: str = "sqlite+aiosqlite:///./newrss.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_SECRET_TOKEN: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"]
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
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
    
    # Market impact analysis settings
    PRICE_ALERT_THRESHOLD: float = 5.0  # Percent change threshold for alerts
    VOLATILITY_THRESHOLD: float = 10.0  # High volatility threshold
    MARKET_IMPACT_COOLDOWN: int = 300   # 5 minutes between impact analyses

    class Config:
        env_file = ".env"

settings = Settings()