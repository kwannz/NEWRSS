import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.news import NewsItem
from app.core.auth import get_password_hash, create_access_token
from app.services.rss_fetcher import RSSFetcher  
from app.services.ai_analyzer import AINewsAnalyzer
from app.tasks.news_crawler import is_urgent_news, calculate_importance
from datetime import datetime
from unittest.mock import patch

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_final_comprehensive.db"

@pytest.mark.asyncio
async def test_complete_api_flow():
    """Test complete API workflow"""
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
            # Register user
            response = await client.post("/auth/register", json={
                "username": "flowuser",
                "email": "flow@example.com", 
                "password": "flowpass123"
            })
            assert response.status_code == 200
            user_data = response.json()
            assert user_data["username"] == "flowuser"
            
            # Login
            login_response = await client.post("/auth/token", data={
                "username": "flowuser",
                "password": "flowpass123"
            })
            assert login_response.status_code == 200
            token_data = login_response.json()
            assert "access_token" in token_data
            
            # Test protected endpoint
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            me_response = await client.get("/auth/me", headers=headers)
            assert me_response.status_code == 200
            me_data = me_response.json()
            assert me_data["username"] == "flowuser"
            
            # Test news endpoints
            news_response = await client.get("/news/", headers=headers)
            assert news_response.status_code == 200
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

@pytest.mark.asyncio
async def test_all_services_integration():
    """Test integration of all services"""
    # Test RSS Fetcher
    async with RSSFetcher() as fetcher:
        assert fetcher is not None
    
    # Test AI Analyzer  
    analyzer = AINewsAnalyzer()
    assert analyzer is not None
    
    # Test news analysis functions
    test_item = {
        'title': 'Breaking: Bitcoin reaches new high',
        'content': 'Urgent cryptocurrency news about bitcoin price surge',
        'source': 'coindesk.com'
    }
    
    assert is_urgent_news(test_item) is True
    importance = calculate_importance(test_item)
    assert 1 <= importance <= 5

@pytest.mark.asyncio
async def test_all_models_coverage():
    """Test coverage of all model classes"""
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
            # Test User model
            user = User(
                username="modeltest",
                email="model@example.com",
                hashed_password=get_password_hash("modelpass123"),
                telegram_id="12345",
                is_active=True,
                urgent_notifications=True,
                daily_digest=False
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Test NewsItem model
            news = NewsItem(
                title="Model Test News",
                content="Test content for model coverage",
                url="https://test.com/news",
                source="Test Source",
                category="bitcoin",
                published_at=datetime.now(),
                importance_score=4,
                is_urgent=True,
                market_impact=3,
                summary="Test summary",
                sentiment_score=0.5,
                key_tokens='["BTC", "test"]',
                key_prices='["$50000"]',
                is_processed=True
            )
            session.add(news)
            await session.commit()
            
            assert user.id is not None
            assert news.id is not None
            assert user.telegram_id == "12345"
            assert news.importance_score == 4
            
    finally:
        await engine.dispose()

def test_settings_and_auth_functions():
    """Test settings and auth utility functions"""
    from app.core.settings import settings
    assert settings is not None
    
    # Test password functions
    password = "testpass123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert len(hashed) > 20
    
    # Test token functions
    token = create_access_token({"sub": "testuser"})
    assert isinstance(token, str)
    assert len(token) > 50