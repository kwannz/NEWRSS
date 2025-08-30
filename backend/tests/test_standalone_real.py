import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.news import NewsItem, NewsSource
from app.models.user import User
from app.core.auth import get_password_hash, create_access_token
from app.services.rss_fetcher import RSSFetcher
from app.services.ai_analyzer import AINewsAnalyzer
from app.core.database import Base, get_db
from app.main import app
from datetime import datetime
import os
import redis.asyncio as redis

# Set test OpenAI API key
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_standalone.db"

@pytest.fixture(scope="module")
async def standalone_engine():
    """Create standalone test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def standalone_session(standalone_engine):
    """Create standalone test database session."""
    SessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=standalone_engine,
        class_=AsyncSession
    )
    
    async with SessionLocal() as session:
        yield session

@pytest.fixture
async def standalone_client(standalone_session):
    """Create standalone test client."""
    async def override_get_db():
        yield standalone_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_standalone_database_operations(standalone_session):
    """Standalone database operations test using real data"""
    # Create real user
    user = User(
        username="standaloneuser",
        email="standalone@example.com",
        hashed_password=get_password_hash("standalonepass123"),
        telegram_id="987654321",
        urgent_notifications=True,
        daily_digest=True
    )
    
    standalone_session.add(user)
    await standalone_session.commit()
    await standalone_session.refresh(user)
    
    assert user.id is not None
    assert user.username == "standaloneuser"
    assert user.is_active is True
    
    # Create real news source
    news_source = NewsSource(
        name="Standalone CoinDesk",
        url="https://feeds.coindesk.com/all",
        source_type="rss",
        category="crypto",
        is_active=True,
        fetch_interval=60,
        priority=3
    )
    
    standalone_session.add(news_source)
    await standalone_session.commit()
    await standalone_session.refresh(news_source)
    
    assert news_source.id is not None
    assert news_source.name == "Standalone CoinDesk"
    
    # Create real news item
    news_item = NewsItem(
        title="Standalone Bitcoin News",
        content="Bitcoin reaches new heights in standalone test",
        url="https://standalone-example.com/bitcoin-news",
        source="Standalone CoinDesk",
        category="bitcoin",
        published_at=datetime.now(),
        importance_score=4,
        is_urgent=False,
        market_impact=3,
        content_hash="standalone123abc"
    )
    
    standalone_session.add(news_item)
    await standalone_session.commit()
    await standalone_session.refresh(news_item)
    
    assert news_item.id is not None
    assert news_item.title == "Standalone Bitcoin News"

@pytest.mark.asyncio
async def test_standalone_api_endpoints(standalone_client):
    """Standalone API endpoints test"""
    # 1. Register real user
    register_data = {
        "username": "standaloneapi",
        "email": "standaloneapi@example.com",
        "password": "standaloneapi123"
    }
    
    register_response = await standalone_client.post("/auth/register", json=register_data)
    assert register_response.status_code == 200
    user_data = register_response.json()
    assert user_data["username"] == "standaloneapi"
    assert "id" in user_data
    
    # 2. Login to get real token
    login_response = await standalone_client.post("/auth/token", data={
        "username": "standaloneapi", 
        "password": "standaloneapi123"
    })
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    token = token_data["access_token"]
    
    # 3. Use real token to access protected endpoint
    me_response = await standalone_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["username"] == "standaloneapi"

@pytest.mark.asyncio
async def test_standalone_real_rss_fetcher():
    """Standalone RSS fetcher test with real data"""
    async with RSSFetcher() as fetcher:
        # Test with real RSS feed
        items = await fetcher.fetch_feed("https://feeds.feedburner.com/oreilly/radar", "O'Reilly Radar")
        
        # Verify results
        assert isinstance(items, list)
        if items:  # If data is returned
            item = items[0]
            assert "title" in item
            assert "content" in item
            assert "url" in item
            assert "source" in item
            assert "published_at" in item
            assert "content_hash" in item

@pytest.mark.asyncio
async def test_standalone_redis_operations():
    """Standalone Redis operations test"""
    # Connect to real Redis
    redis_client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
    
    try:
        # Test basic operations
        await redis_client.set("standalone_key", "standalone_value", ex=3600)
        value = await redis_client.get("standalone_key")
        assert value == "standalone_value"
        
        # Test hash operations
        await redis_client.hset("standalone_hash", "field1", "value1")
        hash_value = await redis_client.hget("standalone_hash", "field1")
        assert hash_value == "value1"
        
        # Test duplicate checking
        await redis_client.setex("news:hash:standalone123", 86400, "1")
        exists = await redis_client.exists("news:hash:standalone123")
        assert exists == 1
        
    finally:
        # Clean up test data
        await redis_client.flushdb()
        await redis_client.aclose()

@pytest.mark.asyncio
async def test_standalone_ai_analyzer():
    """Standalone AI analyzer test"""
    analyzer = AINewsAnalyzer()
    
    test_content = "Bitcoin price surges to new all-time high of $75000. Binance and Coinbase see increased trading volume."
    
    # Test key information extraction (doesn't need API key)
    key_info = await analyzer.extract_key_information(test_content)
    assert isinstance(key_info, dict)
    assert "tokens" in key_info
    assert "prices" in key_info
    assert "exchanges" in key_info
    
    # Should extract price information
    assert any("75000" in price for price in key_info["prices"])
    # Should extract exchange information
    assert 'Binance' in key_info['exchanges']
    assert 'Coinbase' in key_info['exchanges']
    
    # Test market impact calculation
    news_item = {
        'content': test_content,
        'title': 'Bitcoin Surges',
        'source': 'CoinDesk'
    }
    impact = await analyzer.calculate_market_impact(news_item)
    assert isinstance(impact, int)
    assert 1 <= impact <= 5

@pytest.mark.asyncio
async def test_standalone_comprehensive_flow(standalone_client, standalone_session):
    """Complete standalone flow test with real data"""
    # 1. Create user directly in database
    user = User(
        username="flowuser",
        email="flow@standalone.com",
        hashed_password=get_password_hash("flowpass123")
    )
    standalone_session.add(user)
    await standalone_session.commit()
    await standalone_session.refresh(user)
    
    # 2. Create news items
    for i in range(3):
        news_item = NewsItem(
            title=f"Flow News {i}",
            content=f"Real content about crypto news {i}",
            url=f"https://flow.com/news/{i}",
            source="Flow Source",
            category="bitcoin" if i % 2 == 0 else "ethereum",
            published_at=datetime.now(),
            importance_score=i + 2,
            is_urgent=i == 0,
            market_impact=3,
            content_hash=f"flowhash{i}"
        )
        standalone_session.add(news_item)
    
    await standalone_session.commit()
    
    # 3. Test API with real token
    token = create_access_token({"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get all news
    response = await standalone_client.get("/news/", headers=headers)
    assert response.status_code == 200
    news_data = response.json()
    assert len(news_data) >= 3
    
    # Filter by category
    response = await standalone_client.get("/news/?category=bitcoin", headers=headers)
    assert response.status_code == 200
    bitcoin_news = response.json()
    assert all(item["category"] == "bitcoin" for item in bitcoin_news)
    
    # Filter by urgency
    response = await standalone_client.get("/news/?urgent=true", headers=headers)
    assert response.status_code == 200
    urgent_news = response.json()
    assert all(item["isUrgent"] for item in urgent_news)