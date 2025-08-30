import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.core.settings import settings
import redis.asyncio as redis

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    SessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
        class_=AsyncSession
    )
    
    async with SessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session):
    """Create test client with database dependency override."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
async def redis_client():
    """Create test Redis client."""
    client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
    yield client
    await client.flushdb()
    await client.close()

@pytest.fixture
def sample_news_item():
    """Sample news item for testing."""
    return {
        "title": "Bitcoin Reaches New High",
        "content": "Bitcoin has reached a new all-time high of $50,000, marking a significant milestone for the cryptocurrency.",
        "url": "https://example.com/bitcoin-news",
        "source": "CoinDesk",
        "category": "bitcoin",
        "published_at": "2024-01-01T12:00:00Z",
        "importance_score": 4,
        "is_urgent": False,
        "market_impact": 3
    }

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }