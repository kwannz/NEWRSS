import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.news import NewsItem, NewsSource
from app.models.user import User
from app.core.auth import get_password_hash, create_access_token, verify_password
from app.core.database import Base, get_db
from app.main import app
from app.core.redis import get_redis
from app.services.rss_fetcher import RSSFetcher
from datetime import datetime
import os

# Set test OpenAI API key
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_uncovered.db"

@pytest.mark.asyncio
async def test_real_auth_functions():
    """Test authentication functions with real data"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    # Test password verification
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False
    
    # Test token creation and validation
    token_data = {"sub": "testuser"}
    token = create_access_token(token_data)
    assert isinstance(token, str)
    assert len(token) > 0

@pytest.mark.asyncio
async def test_real_database_connection():
    """Test real database connection functions"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        # Test get_db function
        session_gen = get_db()
        session = await session_gen.__anext__()
        
        # Create a test record
        user = User(
            username="dbtest",
            email="db@test.com", 
            hashed_password=get_password_hash("dbtest123")
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        assert user.id is not None
        
        # Close session
        await session_gen.aclose()
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_redis_connection():
    """Test real Redis connection"""
    redis_client = await get_redis()
    
    try:
        # Test basic Redis operations
        await redis_client.set("connection_test", "value", ex=60)
        value = await redis_client.get("connection_test")
        assert value == "value"
        
        # Test Redis exists
        exists = await redis_client.exists("connection_test")
        assert exists == 1
        
    finally:
        await redis_client.flushdb()
        await redis_client.aclose()

@pytest.mark.asyncio
async def test_real_api_error_paths():
    """Test API error paths with real requests"""
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
            # Test registration errors
            # 1. Missing username
            response = await client.post("/auth/register", json={
                "email": "test@example.com",
                "password": "test123"
            })
            assert response.status_code == 422
            
            # 2. Invalid email
            response = await client.post("/auth/register", json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "test123"
            })
            assert response.status_code == 422
            
            # 3. Weak password
            response = await client.post("/auth/register", json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "123"
            })
            assert response.status_code == 422
            
            # 4. Test login errors
            response = await client.post("/auth/token", data={
                "username": "nonexistent",
                "password": "password"
            })
            assert response.status_code == 401
            
            # 5. Test protected endpoints without auth
            response = await client.get("/news/")
            assert response.status_code == 401
        
        app.dependency_overrides.clear()
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_news_api_edge_cases():
    """Test news API edge cases with real data"""
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
            # Register and login user
            await client.post("/auth/register", json={
                "username": "newstest",
                "email": "newstest@example.com",
                "password": "newstest123"
            })
            
            login_response = await client.post("/auth/token", data={
                "username": "newstest",
                "password": "newstest123"
            })
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test various query parameters
            test_params = [
                "?limit=5",
                "?offset=0", 
                "?category=bitcoin",
                "?urgent=true",
                "?importance=3",
                "?limit=100&category=ethereum",
                "?limit=0",  # Edge case: zero limit
                "?offset=1000",  # Edge case: large offset
            ]
            
            for param in test_params:
                response = await client.get(f"/news/{param}", headers=headers)
                # Should handle all parameters gracefully
                assert response.status_code in [200, 422]
                
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, list)
        
        app.dependency_overrides.clear()
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_rss_fetcher_error_scenarios():
    """Test RSS fetcher error scenarios"""
    async with RSSFetcher() as fetcher:
        # Test timeout scenario
        items = await fetcher.fetch_feed("https://httpstat.us/200?sleep=20000", "Timeout Test")
        assert isinstance(items, list)  # Should return empty list on timeout
        
        # Test 404 error
        items = await fetcher.fetch_feed("https://httpstat.us/404", "404 Test")
        assert items == []
        
        # Test 500 error
        items = await fetcher.fetch_feed("https://httpstat.us/500", "500 Test")
        assert items == []
        
        # Test invalid XML/RSS
        items = await fetcher.fetch_feed("https://httpstat.us/200", "Invalid RSS")
        assert isinstance(items, list)

@pytest.mark.asyncio
async def test_real_ai_analyzer_comprehensive():
    """Comprehensive AI analyzer tests"""
    from app.services.ai_analyzer import AINewsAnalyzer
    
    analyzer = AINewsAnalyzer()
    
    # Test various market impact scenarios
    high_impact_news = {
        "content": "SEC lawsuit against major exchange. Federal Reserve bans cryptocurrency trading.",
        "title": "SEC Federal Reserve Ban",
        "source": "sec.gov"
    }
    
    impact = await analyzer.calculate_market_impact(high_impact_news)
    assert impact >= 4  # Should be high impact
    
    # Test edge cases for key extraction
    edge_cases = [
        "",  # Empty content
        "No crypto content here",  # No crypto terms
        "BTC ETH LTC XRP ADA DOT LINK UNI MATIC SOL",  # Many tokens
        "$1 $10 $100 $1000 $10000 USD",  # Various prices
        "binance coinbase kraken huobi okx bybit"  # Many exchanges
    ]
    
    for content in edge_cases:
        key_info = await analyzer.extract_key_information(content)
        assert isinstance(key_info, dict)
        assert all(key in key_info for key in ["tokens", "prices", "exchanges", "dates", "people"])