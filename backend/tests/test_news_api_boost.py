import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.news import NewsItem
from app.core.auth import get_password_hash, create_access_token
from datetime import datetime
from sqlalchemy import select

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_news_api_boost.db"

@pytest.mark.asyncio
async def test_news_api_all_parameters():
    """Test news API with all parameter combinations"""
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
        
        # Create test user and news items
        async with SessionLocal() as session:
            user = User(
                username="newsapitest",
                email="newsapi@example.com",
                hashed_password=get_password_hash("newspass123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create test news items
            categories = ["bitcoin", "ethereum", "defi", "nft"]
            for i in range(10):
                news = NewsItem(
                    title=f"News Item {i}",
                    content=f"Content for news {i}",
                    url=f"https://example.com/news{i}",
                    source=f"Source {i % 3}",
                    category=categories[i % len(categories)],
                    published_at=datetime.now(),
                    importance_score=(i % 5) + 1,
                    is_urgent=i % 3 == 0,
                    market_impact=(i % 5) + 1,
                    sentiment_score=(i - 5) / 5.0,
                    is_processed=True
                )
                session.add(news)
            await session.commit()
            
            token = create_access_token({"sub": user.username})
            headers = {"Authorization": f"Bearer {token}"}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test all parameter combinations
            test_cases = [
                "/news/",
                "/news/?category=bitcoin",
                "/news/?category=ethereum", 
                "/news/?category=defi",
                "/news/?urgent=true",
                "/news/?urgent=false",
                "/news/?importance=1",
                "/news/?importance=3",
                "/news/?importance=5",
                "/news/?limit=5",
                "/news/?limit=3",
                "/news/?skip=2",
                "/news/?skip=5",
                "/news/?category=bitcoin&urgent=true",
                "/news/?category=ethereum&importance=3",
                "/news/?urgent=true&limit=3",
                "/news/?importance=4&skip=1",
                "/news/?category=bitcoin&urgent=true&limit=5&skip=0"
            ]
            
            for endpoint in test_cases:
                response = await client.get(endpoint, headers=headers)
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, list)
            
            # Test unauthorized access
            unauth_response = await client.get("/news/")
            assert unauth_response.status_code == 401
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

@pytest.mark.asyncio
async def test_news_api_filtering_logic():
    """Test news API filtering logic comprehensively"""
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
        
        # Create test user and specific news items
        async with SessionLocal() as session:
            user = User(
                username="filtertest",
                email="filter@example.com", 
                hashed_password=get_password_hash("filterpass123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            
            # Create specific test cases
            news_items = [
                NewsItem(
                    title="Urgent Bitcoin News",
                    content="Urgent bitcoin content",
                    url="https://bitcoin1.com",
                    source="Bitcoin Source",
                    category="bitcoin",
                    published_at=datetime.now(),
                    importance_score=5,
                    is_urgent=True,
                    market_impact=5,
                    is_processed=True
                ),
                NewsItem(
                    title="Regular Ethereum Update",
                    content="Regular ethereum content",
                    url="https://ethereum1.com",
                    source="Ethereum Source",
                    category="ethereum",
                    published_at=datetime.now(),
                    importance_score=2,
                    is_urgent=False,
                    market_impact=2,
                    is_processed=True
                ),
                NewsItem(
                    title="High Impact DeFi News",
                    content="High impact defi content",
                    url="https://defi1.com",
                    source="DeFi Source",
                    category="defi",
                    published_at=datetime.now(),
                    importance_score=4,
                    is_urgent=False,
                    market_impact=4,
                    is_processed=True
                )
            ]
            
            for news in news_items:
                session.add(news)
            await session.commit()
            
            token = create_access_token({"sub": user.username})
            headers = {"Authorization": f"Bearer {token}"}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test category filtering
            bitcoin_response = await client.get("/news/?category=bitcoin", headers=headers)
            assert bitcoin_response.status_code == 200
            bitcoin_data = bitcoin_response.json()
            for item in bitcoin_data:
                assert item["category"] == "bitcoin"
            
            # Test urgent filtering
            urgent_response = await client.get("/news/?urgent=true", headers=headers)
            assert urgent_response.status_code == 200
            urgent_data = urgent_response.json()
            for item in urgent_data:
                assert item["isUrgent"] is True
            
            # Test importance filtering
            high_imp_response = await client.get("/news/?importance=4", headers=headers)
            assert high_imp_response.status_code == 200
            high_imp_data = high_imp_response.json()
            for item in high_imp_data:
                assert item["importanceScore"] >= 4
            
            # Test limit functionality
            limit_response = await client.get("/news/?limit=2", headers=headers)
            assert limit_response.status_code == 200
            limit_data = limit_response.json()
            assert len(limit_data) <= 2
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

@pytest.mark.asyncio
async def test_news_api_error_handling():
    """Test news API error handling scenarios"""
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
        
        async with SessionLocal() as session:
            user = User(
                username="errortest",
                email="error@example.com",
                hashed_password=get_password_hash("errorpass123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            
            token = create_access_token({"sub": user.username})
            headers = {"Authorization": f"Bearer {token}"}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test invalid parameters
            invalid_params = [
                "/news/?importance=10",  # Out of range
                "/news/?importance=-1",  # Negative
                "/news/?limit=-5",      # Negative limit
                "/news/?skip=-1",       # Negative skip
                "/news/?urgent=invalid", # Invalid boolean
                "/news/?category=",     # Empty category
            ]
            
            for endpoint in invalid_params:
                response = await client.get(endpoint, headers=headers)
                # Should handle gracefully (200 with empty results or 422 validation error)
                assert response.status_code in [200, 422]
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()