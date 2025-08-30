import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.news import NewsItem, NewsSource
from app.models.user import User
from app.models.subscription import UserSubscription, UserCategory
from app.core.auth import get_password_hash, create_access_token
from app.services.rss_fetcher import RSSFetcher
from app.services.ai_analyzer import AINewsAnalyzer
from app.services.telegram_bot import TelegramBot
from app.services.telegram_notifier import TelegramNotifier
from app.core.database import Base, get_db
from app.main import app
from datetime import datetime
import os
import redis.asyncio as redis

# Set test OpenAI API key
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_services.db"

@pytest.mark.asyncio
async def test_real_subscription_models():
    """Test subscription models with real data"""
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
                username="subuser",
                email="sub@example.com",
                hashed_password=get_password_hash("subpass123"),
                telegram_id="555555555"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create real news source
            news_source = NewsSource(
                name="Sub CoinDesk",
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
            
            # Create real user subscription
            subscription = UserSubscription(
                user_id=user.id,
                source_id=news_source.id,
                is_active=True,
                keywords="bitcoin,ethereum",
                min_importance=3,
                urgent_only=False
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            
            assert subscription.id is not None
            assert subscription.user_id == user.id
            assert subscription.source_id == news_source.id
            assert subscription.keywords == "bitcoin,ethereum"
            
            # Create real user category
            category = UserCategory(
                user_id=user.id,
                category="bitcoin",
                is_subscribed=True
            )
            session.add(category)
            await session.commit()
            await session.refresh(category)
            
            assert category.id is not None
            assert category.user_id == user.id
            assert category.category == "bitcoin"
            assert category.is_subscribed is True
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_rss_fetcher_advanced():
    """Advanced RSS fetcher tests with real feeds"""
    async with RSSFetcher() as fetcher:
        # Test duplicate detection with Redis
        redis_client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
        
        try:
            # Clear any existing test data first
            await redis_client.flushdb()
            
            # Test is_duplicate method
            test_hash = "test_duplicate_hash_456"
            
            # First check should be False (not duplicate)
            is_dup1 = await fetcher.is_duplicate(test_hash)
            assert is_dup1 is False
            
            # Second check should be True (is duplicate)
            is_dup2 = await fetcher.is_duplicate(test_hash)
            assert is_dup2 is True
            
            # Test multiple feeds fetching
            sources = [
                {
                    "url": "https://feeds.feedburner.com/oreilly/radar",
                    "name": "O'Reilly Radar",
                    "category": "tech"
                }
            ]
            
            items = await fetcher.fetch_multiple_feeds(sources)
            assert isinstance(items, list)
            
            # Verify category assignment
            if items:
                for item in items:
                    assert "category" in item
                    assert item["category"] == "tech"
            
        finally:
            await redis_client.flushdb()
            await redis_client.aclose()

@pytest.mark.asyncio
async def test_real_ai_analyzer_full():
    """Full AI analyzer tests without API calls"""
    analyzer = AINewsAnalyzer()
    
    # Test market impact calculation with various keywords
    test_cases = [
        {
            "news_item": {
                "content": "SEC approves Bitcoin ETF application",
                "title": "SEC ETF Approval",
                "source": "sec.gov"
            },
            "expected_min_impact": 4  # High impact due to SEC + approval
        },
        {
            "news_item": {
                "content": "Binance announces new partnership",
                "title": "Partnership News",
                "source": "binance.com"
            },
            "expected_min_impact": 3  # Medium-high impact
        },
        {
            "news_item": {
                "content": "Regular Bitcoin price update",
                "title": "Price Update",
                "source": "news.com"
            },
            "expected_min_impact": 1  # Low impact
        }
    ]
    
    for test_case in test_cases:
        impact = await analyzer.calculate_market_impact(test_case["news_item"])
        assert impact >= test_case["expected_min_impact"]
    
    # Test key information extraction with complex content
    complex_content = """
    Bitcoin (BTC) surged to $95000 while Ethereum (ETH) reached $4500. 
    Major exchanges including Binance, Coinbase, and Kraken reported 
    record trading volumes. The Federal Reserve announced new policies 
    affecting cryptocurrency regulation.
    """
    
    key_info = await analyzer.extract_key_information(complex_content)
    
    # Verify token extraction
    assert "BTC" in key_info["tokens"]
    assert "ETH" in key_info["tokens"]
    
    # Verify price extraction
    assert any("95000" in price for price in key_info["prices"])
    assert any("4500" in price for price in key_info["prices"])
    
    # Verify exchange extraction
    assert "Binance" in key_info["exchanges"]
    assert "Coinbase" in key_info["exchanges"]
    assert "Kraken" in key_info["exchanges"]

@pytest.mark.asyncio
async def test_real_telegram_bot_no_api():
    """Test Telegram bot without real API calls"""
    # Test initialization without token
    bot = TelegramBot()
    assert bot.bot is None
    
    # Test webhook URL generation
    webhook_url = bot.get_webhook_url()
    assert webhook_url is None or isinstance(webhook_url, str)

@pytest.mark.asyncio  
async def test_real_telegram_notifier_no_api():
    """Test Telegram notifier without real API calls"""
    notifier = TelegramNotifier()
    
    # Test notification preparation (should handle missing token gracefully)
    news_item = {
        "title": "Test News",
        "content": "Test content for notification",
        "url": "https://test.com/news",
        "importance_score": 4
    }
    
    # This should not crash even without API token
    try:
        await notifier.send_urgent_notification("123456", news_item)
        await notifier.send_daily_digest("123456", [news_item])
    except Exception as e:
        # Should handle missing token gracefully
        assert "token" in str(e).lower() or "unauthorized" in str(e).lower()

@pytest.mark.asyncio
async def test_real_comprehensive_service_integration():
    """Comprehensive service integration test"""
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
            # 1. Register user
            register_response = await client.post("/auth/register", json={
                "username": "serviceuser",
                "email": "service@example.com",
                "password": "service123"
            })
            assert register_response.status_code == 200
            
            # 2. Login
            login_response = await client.post("/auth/token", data={
                "username": "serviceuser",
                "password": "service123"
            })
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # 3. Create news via database and test RSS fetcher integration
            async with SessionLocal() as session:
                # Create news source
                source = NewsSource(
                    name="Service Test Source",
                    url="https://test.com/rss",
                    source_type="rss",
                    category="crypto",
                    is_active=True
                )
                session.add(source)
                await session.commit()
                
                # Create subscription
                subscription = UserSubscription(
                    user_id=1,  # Should be the registered user
                    source_id=source.id,
                    keywords="bitcoin",
                    min_importance=2
                )
                session.add(subscription)
                await session.commit()
            
            # 4. Test news endpoints with real filtering
            response = await client.get("/news/?category=crypto", headers=headers)
            assert response.status_code == 200
            
            response = await client.get("/news/?limit=10", headers=headers)
            assert response.status_code == 200
            news_data = response.json()
            assert len(news_data) <= 10
            
            # 5. Test real AI analysis integration
            async with RSSFetcher() as fetcher:
                # Fetch some real data for analysis
                items = await fetcher.fetch_feed("https://feeds.feedburner.com/oreilly/radar", "Test Source")
                
                if items:
                    analyzer = AINewsAnalyzer()
                    first_item = items[0]
                    
                    # Test key extraction
                    key_info = await analyzer.extract_key_information(first_item["content"])
                    assert isinstance(key_info, dict)
                    
                    # Test market impact
                    impact = await analyzer.calculate_market_impact(first_item)
                    assert 1 <= impact <= 5
        
        app.dependency_overrides.clear()
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_error_handling_edge_cases():
    """Test real error handling edge cases"""
    # Test RSS fetcher with invalid URLs
    async with RSSFetcher() as fetcher:
        # Should handle invalid URL gracefully
        items = await fetcher.fetch_feed("https://invalid-url-that-does-not-exist.com/rss", "Invalid Source")
        assert items == []
        
        # Should handle timeout gracefully
        # Note: This might actually work if URL exists, but should not crash
        items = await fetcher.fetch_feed("https://httpstat.us/200?sleep=20000", "Timeout Test")
        assert isinstance(items, list)
    
    # Test AI analyzer with edge cases
    analyzer = AINewsAnalyzer()
    
    # Empty content
    key_info = await analyzer.extract_key_information("")
    assert isinstance(key_info, dict)
    
    # Very long content
    long_content = "Bitcoin " * 1000
    key_info = await analyzer.extract_key_information(long_content)
    assert isinstance(key_info, dict)
    assert "tokens" in key_info