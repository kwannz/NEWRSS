from pydantic_settings import BaseSettings
from pydantic import AnyUrl
from typing import List

class Settings(BaseSettings):
    ENV: str = "dev"
    DATABASE_URL: str = "postgresql+asyncpg://newrss:newrss@postgres:5432/newrss"
    REDIS_URL: str = "redis://redis:6379/0"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str | None = None
    TELEGRAM_SECRET_TOKEN: str | None = None
    OPENAI_API_KEY: str | None = None
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()