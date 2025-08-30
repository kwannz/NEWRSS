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
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_direct.db"

@pytest.mark.asyncio
async def test_direct_database_operations():
    """Direct database operations test using real data without fixtures"""
    # Create engine and session directly
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        SessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=AsyncSession
        )
        
        async with SessionLocal() as session:
            # Create real user
            user = User(
                username="directuser",
                email="direct@example.com",
                hashed_password=get_password_hash("directpass123"),
                telegram_id="111111111",
                urgent_notifications=True,
                daily_digest=True
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            assert user.id is not None
            assert user.username == "directuser"
            assert user.is_active is True
            
            # Create real news source
            news_source = NewsSource(
                name="Direct CoinDesk",
                url="https://feeds.coindesk.com/all",
                source_type="rss",
                category="crypto",
                is_active=True,
                fetch_interval=60,
                priority=3
            )
            
            session.add(news_source)
            await session.commit()
            await session.refresh(news_source)
            
            assert news_source.id is not None
            assert news_source.name == "Direct CoinDesk"
            
            # Create real news item
            news_item = NewsItem(
                title="Direct Bitcoin News",
                content="Bitcoin reaches new heights in direct test",
                url="https://direct-example.com/bitcoin-news",
                source="Direct CoinDesk",
                category="bitcoin",
                published_at=datetime.now(),
                importance_score=4,
                is_urgent=False,
                market_impact=3
            )
            
            session.add(news_item)
            await session.commit()
            await session.refresh(news_item)
            
            assert news_item.id is not None
            assert news_item.title == "Direct Bitcoin News"
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_direct_api_endpoints():
    """Direct API endpoints test"""
    # Create engine and session directly
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        SessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=AsyncSession
        )
        
        async def override_get_db():
            async with SessionLocal() as session:
                yield session
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. Register real user
            register_data = {
                "username": "directapi",
                "email": "directapi@example.com",
                "password": "directapi123"
            }
            
            register_response = await client.post("/auth/register", json=register_data)
            assert register_response.status_code == 200
            user_data = register_response.json()
            assert user_data["username"] == "directapi"
            assert "id" in user_data
            
            # 2. Login to get real token
            login_response = await client.post("/auth/token", data={
                "username": "directapi", 
                "password": "directapi123"
            })
            assert login_response.status_code == 200
            token_data = login_response.json()
            assert "access_token" in token_data
            assert token_data["token_type"] == "bearer"
            
            token = token_data["access_token"]
            
            # 3. Use real token to access protected endpoint
            me_response = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert me_response.status_code == 200
            me_data = me_response.json()
            assert me_data["username"] == "directapi"
        
        app.dependency_overrides.clear()
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_direct_real_rss_fetcher():
    """Direct RSS fetcher test with real data"""
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
async def test_direct_redis_operations():
    """Direct Redis operations test"""
    # Connect to real Redis
    redis_client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
    
    try:
        # Test basic operations
        await redis_client.set("direct_key", "direct_value", ex=3600)
        value = await redis_client.get("direct_key")
        assert value == "direct_value"
        
        # Test hash operations
        await redis_client.hset("direct_hash", "field1", "value1")
        hash_value = await redis_client.hget("direct_hash", "field1")
        assert hash_value == "value1"
        
        # Test duplicate checking (matching RSSFetcher logic)
        await redis_client.setex("news:hash:direct123", 86400, "1")
        exists = await redis_client.exists("news:hash:direct123")
        assert exists == 1
        
        # Test news cache operations
        await redis_client.hset("user:123:subscriptions", "bitcoin", "1")
        sub_value = await redis_client.hget("user:123:subscriptions", "bitcoin")
        assert sub_value == "1"
        
    finally:
        # Clean up test data
        await redis_client.flushdb()
        await redis_client.aclose()

@pytest.mark.asyncio
async def test_direct_ai_analyzer():
    """Direct AI analyzer test"""
    analyzer = AINewsAnalyzer()
    
    test_content = "Bitcoin price surges to new all-time high of $80000. Binance and Coinbase see increased trading volume. SEC approves new regulations."
    
    # Test key information extraction (doesn't need API key)
    key_info = await analyzer.extract_key_information(test_content)
    assert isinstance(key_info, dict)
    assert "tokens" in key_info
    assert "prices" in key_info
    assert "exchanges" in key_info
    
    # Should extract price information
    assert any("80000" in price for price in key_info["prices"])
    # Should extract exchange information
    assert 'Binance' in key_info['exchanges']
    assert 'Coinbase' in key_info['exchanges']
    
    # Test market impact calculation
    news_item = {
        'content': test_content,
        'title': 'Bitcoin Surges with SEC Approval',
        'source': 'CoinDesk'
    }
    impact = await analyzer.calculate_market_impact(news_item)
    assert isinstance(impact, int)
    assert 1 <= impact <= 5
    # Should be high impact due to SEC keyword
    assert impact >= 3

@pytest.mark.asyncio
async def test_direct_comprehensive_real_flow():
    """Complete direct flow test with real data - no fixtures"""
    # Create engine and session directly
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        SessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=AsyncSession
        )
        
        async def override_get_db():
            async with SessionLocal() as session:
                yield session
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. Create user via API
            register_data = {
                "username": "comprflow",
                "email": "comprflow@example.com", 
                "password": "comprflow123"
            }
            
            register_response = await client.post("/auth/register", json=register_data)
            assert register_response.status_code == 200
            
            # 2. Login and get token
            login_response = await client.post("/auth/token", data={
                "username": "comprflow",
                "password": "comprflow123"
            })
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # 3. Create news data directly in database
            async with SessionLocal() as session:
                for i in range(5):
                    news_item = NewsItem(
                        title=f"Comprehensive News {i}",
                        content=f"Real crypto content {i} with Bitcoin and Ethereum data",
                        url=f"https://comp.com/news/{i}",
                        source="Comprehensive Source",
                        category="bitcoin" if i % 2 == 0 else "ethereum",
                        published_at=datetime.now(),
                        importance_score=i + 1,
                        is_urgent=i == 0,
                        market_impact=3
                    )
                    session.add(news_item)
                await session.commit()
            
            # 4. Test news API with real data
            response = await client.get("/news/", headers=headers)
            assert response.status_code == 200
            news_data = response.json()
            assert len(news_data) >= 5
            
            # 5. Test filtering
            response = await client.get("/news/?category=bitcoin", headers=headers)
            assert response.status_code == 200
            bitcoin_news = response.json()
            assert all(item["category"] == "bitcoin" for item in bitcoin_news)
            
            # 6. Test urgency filter
            response = await client.get("/news/?urgent=true", headers=headers)
            assert response.status_code == 200
            urgent_news = response.json()
            assert any(item["isUrgent"] for item in urgent_news)
        
        app.dependency_overrides.clear()
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()