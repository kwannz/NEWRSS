import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient
from app.models.news import NewsItem, NewsSource
from app.models.user import User
from app.models.subscription import UserSubscription, UserCategory
from app.core.auth import get_password_hash, create_access_token
from app.core.database import Base, get_db
from app.main import app
from datetime import datetime
import os

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_subscription.db"

@pytest.mark.asyncio
async def test_real_subscription_crud():
    """Test UserSubscription model CRUD operations with real data"""
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
                telegram_id="777777777"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create real news source
            source = NewsSource(
                name="Subscription Test Source",
                url="https://test-subscription.com/rss",
                source_type="rss",
                category="crypto",
                is_active=True,
                fetch_interval=30,
                priority=5
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
            
            # Test UserSubscription creation
            subscription = UserSubscription(
                user_id=user.id,
                source_id=source.id,
                is_active=True,
                keywords="bitcoin,ethereum,defi",
                min_importance=2,
                urgent_only=False
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            
            # Verify subscription attributes
            assert subscription.id is not None
            assert subscription.user_id == user.id
            assert subscription.source_id == source.id
            assert subscription.is_active is True
            assert subscription.keywords == "bitcoin,ethereum,defi"
            assert subscription.min_importance == 2
            assert subscription.urgent_only is False
            assert subscription.created_at is not None
            
            # Test subscription update
            subscription.keywords = "bitcoin,solana"
            subscription.min_importance = 3
            await session.commit()
            await session.refresh(subscription)
            
            assert subscription.keywords == "bitcoin,solana"
            assert subscription.min_importance == 3
            assert subscription.updated_at is not None
            
            # Test UserCategory creation
            categories = ["bitcoin", "ethereum", "defi", "nft"]
            for cat in categories:
                category = UserCategory(
                    user_id=user.id,
                    category=cat,
                    is_subscribed=cat in ["bitcoin", "ethereum"]
                )
                session.add(category)
            
            await session.commit()
            
            # Verify categories
            from sqlalchemy import select
            result = await session.execute(
                select(UserCategory).where(UserCategory.user_id == user.id)
            )
            user_categories = result.scalars().all()
            
            assert len(user_categories) == 4
            subscribed_cats = [cat.category for cat in user_categories if cat.is_subscribed]
            assert "bitcoin" in subscribed_cats
            assert "ethereum" in subscribed_cats
            assert "defi" not in subscribed_cats
            assert "nft" not in subscribed_cats
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_subscription_api_integration():
    """Test subscription functionality through API with real data"""
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
            register_response = await client.post("/auth/register", json={
                "username": "subapi",
                "email": "subapi@example.com",
                "password": "subapi123"
            })
            assert register_response.status_code == 200
            
            # Login
            login_response = await client.post("/auth/token", data={
                "username": "subapi",
                "password": "subapi123"
            })
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Create news sources and subscriptions through database
            async with SessionLocal() as session:
                # Create multiple news sources
                sources_data = [
                    ("CoinDesk", "https://feeds.coindesk.com/all", "crypto"),
                    ("CoinTelegraph", "https://cointelegraph.com/rss", "crypto"),
                    ("The Block", "https://theblock.co/rss", "defi")
                ]
                
                for name, url, category in sources_data:
                    source = NewsSource(
                        name=name,
                        url=url,
                        source_type="rss",
                        category=category,
                        is_active=True
                    )
                    session.add(source)
                
                await session.commit()
                
                # Create various news items for filtering tests
                news_data = [
                    ("Bitcoin reaches ATH", "bitcoin news content", "bitcoin", 5, True),
                    ("Ethereum upgrade", "ethereum upgrade news", "ethereum", 4, False),
                    ("DeFi protocol hack", "defi security news", "defi", 5, True),
                    ("NFT market update", "nft market analysis", "nft", 2, False),
                    ("Altcoin analysis", "general altcoin news", "altcoin", 3, False)
                ]
                
                for title, content, category, importance, urgent in news_data:
                    news = NewsItem(
                        title=title,
                        content=content,
                        url=f"https://test.com/{title.replace(' ', '-').lower()}",
                        source="Test Source",
                        category=category,
                        published_at=datetime.now(),
                        importance_score=importance,
                        is_urgent=urgent,
                        market_impact=importance
                    )
                    session.add(news)
                
                await session.commit()
            
            # Test news filtering with various parameters
            test_filters = [
                ("?category=bitcoin", lambda items: all(item["category"] == "bitcoin" for item in items)),
                ("?urgent=true", lambda items: all(item["isUrgent"] for item in items)),
                ("?importance=5", lambda items: all(item["importanceScore"] >= 5 for item in items)),
                ("?limit=3", lambda items: len(items) <= 3),
                ("?category=ethereum&urgent=false", lambda items: all(
                    item["category"] == "ethereum" and not item["isUrgent"] for item in items
                ))
            ]
            
            for filter_param, validator in test_filters:
                response = await client.get(f"/news/{filter_param}", headers=headers)
                assert response.status_code == 200
                news_data = response.json()
                assert isinstance(news_data, list)
                if news_data:
                    assert validator(news_data)
        
        app.dependency_overrides.clear()
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_subscription_relationships():
    """Test subscription model relationships with real data"""
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
            # Create user with telegram settings
            user = User(
                username="reluser",
                email="rel@example.com",
                hashed_password=get_password_hash("relpass123"),
                telegram_id="888888888",
                urgent_notifications=True,
                daily_digest=True,
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Test user attributes thoroughly
            assert user.username == "reluser"
            assert user.email == "rel@example.com"
            assert user.telegram_id == "888888888"
            assert user.urgent_notifications is True
            assert user.daily_digest is True
            assert user.is_active is True
            assert user.created_at is not None
            
            # Create multiple sources
            sources = []
            for i in range(3):
                source = NewsSource(
                    name=f"Source {i}",
                    url=f"https://source{i}.com/rss",
                    source_type="rss",
                    category="crypto",
                    is_active=i < 2,  # First 2 active, last inactive
                    fetch_interval=30 + i * 10,
                    priority=i + 1
                )
                session.add(source)
                sources.append(source)
            
            await session.commit()
            
            # Create subscriptions with different settings
            sub_settings = [
                {"keywords": "bitcoin", "min_importance": 1, "urgent_only": False},
                {"keywords": "ethereum,defi", "min_importance": 3, "urgent_only": True},
                {"keywords": None, "min_importance": 5, "urgent_only": False}
            ]
            
            for i, settings in enumerate(sub_settings):
                subscription = UserSubscription(
                    user_id=user.id,
                    source_id=sources[i].id,
                    is_active=True,
                    **settings
                )
                session.add(subscription)
            
            await session.commit()
            
            # Verify subscription relationships and attributes
            from sqlalchemy import select
            result = await session.execute(
                select(UserSubscription).where(UserSubscription.user_id == user.id)
            )
            user_subscriptions = result.scalars().all()
            
            assert len(user_subscriptions) == 3
            
            # Test different subscription configurations
            bitcoin_sub = next(sub for sub in user_subscriptions if sub.keywords == "bitcoin")
            assert bitcoin_sub.min_importance == 1
            assert bitcoin_sub.urgent_only is False
            
            urgent_sub = next(sub for sub in user_subscriptions if sub.urgent_only is True)
            assert urgent_sub.keywords == "ethereum,defi"
            assert urgent_sub.min_importance == 3
            
            high_importance_sub = next(sub for sub in user_subscriptions if sub.min_importance == 5)
            assert high_importance_sub.keywords is None
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_subscription_filtering_logic():
    """Test subscription filtering logic with real data"""
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
            # Create user and sources
            user = User(
                username="filteruser",
                email="filter@example.com",
                hashed_password=get_password_hash("filterpass123")
            )
            session.add(user)
            
            source = NewsSource(
                name="Filter Source",
                url="https://filter.com/rss",
                source_type="rss",
                category="crypto"
            )
            session.add(source)
            await session.commit()
            await session.refresh(user)
            await session.refresh(source)
            
            # Create subscription with specific filters
            subscription = UserSubscription(
                user_id=user.id,
                source_id=source.id,
                keywords="bitcoin,btc",
                min_importance=3,
                urgent_only=True
            )
            session.add(subscription)
            await session.commit()
            
            # Create news items that should match/not match filters
            test_news = [
                # Should match: bitcoin keyword, high importance, urgent
                ("Bitcoin Bull Run", "Bitcoin price surges", 5, True, True),
                # Should NOT match: no keyword match
                ("Ethereum Update", "Ethereum network upgrade", 5, True, False), 
                # Should NOT match: low importance
                ("Bitcoin Update", "Minor Bitcoin news", 2, True, False),
                # Should NOT match: not urgent
                ("Bitcoin Analysis", "BTC market analysis", 4, False, False),
                # Should match: btc keyword, high importance, urgent
                ("BTC Surge", "BTC reaches new high", 4, True, True)
            ]
            
            for title, content, importance, urgent, should_match in test_news:
                news = NewsItem(
                    title=title,
                    content=content,
                    url=f"https://test.com/{title.replace(' ', '-').lower()}",
                    source="Filter Source",
                    category="bitcoin",
                    published_at=datetime.now(),
                    importance_score=importance,
                    is_urgent=urgent,
                    market_impact=importance
                )
                session.add(news)
            
            await session.commit()
            
            # Test filtering logic by querying news
            from sqlalchemy import select, and_
            
            # Simulate subscription filtering
            query = select(NewsItem).where(
                and_(
                    NewsItem.importance_score >= subscription.min_importance,
                    NewsItem.is_urgent == subscription.urgent_only
                )
            )
            
            result = await session.execute(query)
            filtered_news = result.scalars().all()
            
            # Should have 2 matching items
            assert len(filtered_news) == 2
            
            # Verify they contain the keywords
            matching_titles = [news.title for news in filtered_news]
            assert "Bitcoin Bull Run" in matching_titles
            assert "BTC Surge" in matching_titles
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_user_category_management():
    """Test UserCategory model with real category management"""
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
            # Create user
            user = User(
                username="catuser",
                email="cat@example.com",
                hashed_password=get_password_hash("catpass123")
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create various categories
            categories_data = [
                ("bitcoin", True),
                ("ethereum", True),
                ("defi", False),
                ("nft", False),
                ("altcoin", True),
                ("stablecoin", False)
            ]
            
            for category_name, is_subscribed in categories_data:
                category = UserCategory(
                    user_id=user.id,
                    category=category_name,
                    is_subscribed=is_subscribed
                )
                session.add(category)
            
            await session.commit()
            
            # Test category queries
            from sqlalchemy import select
            
            # Get all user categories
            result = await session.execute(
                select(UserCategory).where(UserCategory.user_id == user.id)
            )
            all_categories = result.scalars().all()
            assert len(all_categories) == 6
            
            # Get only subscribed categories
            result = await session.execute(
                select(UserCategory).where(
                    and_(
                        UserCategory.user_id == user.id,
                        UserCategory.is_subscribed == True
                    )
                )
            )
            subscribed_categories = result.scalars().all()
            assert len(subscribed_categories) == 3
            
            subscribed_names = [cat.category for cat in subscribed_categories]
            assert "bitcoin" in subscribed_names
            assert "ethereum" in subscribed_names
            assert "altcoin" in subscribed_names
            assert "defi" not in subscribed_names
            
            # Test category updates
            defi_category = next(cat for cat in all_categories if cat.category == "defi")
            defi_category.is_subscribed = True
            await session.commit()
            
            # Verify update
            result = await session.execute(
                select(UserCategory).where(
                    and_(
                        UserCategory.user_id == user.id,
                        UserCategory.category == "defi"
                    )
                )
            )
            updated_defi = result.scalar_one()
            assert updated_defi.is_subscribed is True
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_subscription_edge_cases():
    """Test subscription edge cases and validation"""
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
            # Create user and source
            user = User(
                username="edgeuser",
                email="edge@example.com",
                hashed_password=get_password_hash("edgepass123")
            )
            source = NewsSource(
                name="Edge Source",
                url="https://edge.com/rss",
                source_type="rss",
                category="crypto"
            )
            session.add(user)
            session.add(source)
            await session.commit()
            await session.refresh(user)
            await session.refresh(source)
            
            # Test edge cases for UserSubscription
            edge_cases = [
                # Empty keywords
                {"keywords": "", "min_importance": 1, "urgent_only": False},
                # Very long keywords
                {"keywords": "bitcoin,ethereum,litecoin,ripple,cardano,polkadot,chainlink,uniswap,polygon,solana", "min_importance": 1, "urgent_only": False},
                # Maximum importance
                {"keywords": "bitcoin", "min_importance": 5, "urgent_only": True},
                # Minimum importance  
                {"keywords": "bitcoin", "min_importance": 1, "urgent_only": False},
                # Special characters in keywords
                {"keywords": "bitcoin,btc-usd,eth/btc", "min_importance": 3, "urgent_only": False}
            ]
            
            for i, settings in enumerate(edge_cases):
                subscription = UserSubscription(
                    user_id=user.id,
                    source_id=source.id,
                    is_active=True,
                    **settings
                )
                session.add(subscription)
            
            await session.commit()
            
            # Verify all subscriptions were created
            from sqlalchemy import select
            result = await session.execute(
                select(UserSubscription).where(UserSubscription.user_id == user.id)
            )
            subscriptions = result.scalars().all()
            assert len(subscriptions) == 5
            
            # Test inactive subscription
            inactive_subscription = UserSubscription(
                user_id=user.id,
                source_id=source.id,
                is_active=False,
                keywords="inactive",
                min_importance=1
            )
            session.add(inactive_subscription)
            await session.commit()
            
            # Query only active subscriptions
            result = await session.execute(
                select(UserSubscription).where(
                    and_(
                        UserSubscription.user_id == user.id,
                        UserSubscription.is_active == True
                    )
                )
            )
            active_subs = result.scalars().all()
            assert len(active_subs) == 5  # Original 5, not the inactive one
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()