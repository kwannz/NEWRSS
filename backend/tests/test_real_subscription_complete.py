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
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_subscription_complete.db"

@pytest.mark.asyncio
async def test_real_user_subscription_model_complete():
    """Complete UserSubscription model testing"""
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
                username="subtest",
                email="subtest@example.com",
                hashed_password=get_password_hash("subtest123")
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create news source
            source = NewsSource(
                name="Subscription Test Source",
                url="https://sub-test.com/rss",
                source_type="rss",
                category="crypto"
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
            
            # Test UserSubscription with all field combinations
            # Test 1: Basic subscription
            sub1 = UserSubscription(
                user_id=user.id,
                source_id=source.id
            )
            session.add(sub1)
            await session.commit()
            await session.refresh(sub1)
            
            # Verify default values
            assert sub1.is_active is True
            assert sub1.keywords is None
            assert sub1.min_importance == 1
            assert sub1.urgent_only is False
            assert sub1.created_at is not None
            
            # Test 2: Full subscription with all fields
            sub2 = UserSubscription(
                user_id=user.id,
                source_id=source.id,
                is_active=False,
                keywords="bitcoin,ethereum,defi",
                min_importance=4,
                urgent_only=True
            )
            session.add(sub2)
            await session.commit()
            await session.refresh(sub2)
            
            # Verify all fields
            assert sub2.is_active is False
            assert sub2.keywords == "bitcoin,ethereum,defi"
            assert sub2.min_importance == 4
            assert sub2.urgent_only is True
            
            # Test 3: Update subscription
            sub2.is_active = True
            sub2.keywords = "bitcoin,solana"
            sub2.min_importance = 5
            await session.commit()
            await session.refresh(sub2)
            
            assert sub2.is_active is True
            assert sub2.keywords == "bitcoin,solana"
            assert sub2.min_importance == 5
            assert sub2.updated_at is not None
            
            # Test 4: Edge case values
            sub3 = UserSubscription(
                user_id=user.id,
                source_id=source.id,
                keywords="",  # Empty keywords
                min_importance=1,  # Minimum value
                urgent_only=False
            )
            session.add(sub3)
            await session.commit()
            await session.refresh(sub3)
            
            assert sub3.keywords == ""
            assert sub3.min_importance == 1
            
            # Test 5: Maximum values
            sub4 = UserSubscription(
                user_id=user.id,
                source_id=source.id,
                keywords="bitcoin,ethereum,cardano,polkadot,chainlink,uniswap,pancakeswap,compound",
                min_importance=5,  # Maximum value
                urgent_only=True
            )
            session.add(sub4)
            await session.commit()
            await session.refresh(sub4)
            
            assert sub4.min_importance == 5
            assert sub4.urgent_only is True
            assert len(sub4.keywords.split(",")) == 8
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_user_category_model_complete():
    """Complete UserCategory model testing"""
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
                username="cattest",
                email="cattest@example.com",
                hashed_password=get_password_hash("cattest123")
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Test UserCategory with different configurations
            categories = [
                ("bitcoin", True),
                ("ethereum", True),
                ("defi", False),
                ("nft", False),
                ("altcoin", True),
                ("stablecoin", False),
                ("regulation", True),
                ("mining", False)
            ]
            
            created_categories = []
            for category_name, is_subscribed in categories:
                category = UserCategory(
                    user_id=user.id,
                    category=category_name,
                    is_subscribed=is_subscribed
                )
                session.add(category)
                created_categories.append(category)
            
            await session.commit()
            
            # Refresh all categories
            for category in created_categories:
                await session.refresh(category)
            
            # Verify all categories were created correctly
            for i, (cat_name, expected_sub) in enumerate(categories):
                category = created_categories[i]
                assert category.id is not None
                assert category.user_id == user.id
                assert category.category == cat_name
                assert category.is_subscribed == expected_sub
                assert category.created_at is not None
            
            # Test category updates
            bitcoin_category = next(cat for cat in created_categories if cat.category == "bitcoin")
            bitcoin_category.is_subscribed = False
            await session.commit()
            await session.refresh(bitcoin_category)
            
            assert bitcoin_category.is_subscribed is False
            
            # Test category queries
            from sqlalchemy import select
            
            # Query subscribed categories
            result = await session.execute(
                select(UserCategory).where(
                    UserCategory.user_id == user.id
                ).where(
                    UserCategory.is_subscribed == True
                )
            )
            subscribed = result.scalars().all()
            
            # Should have 3 subscribed (ethereum, altcoin, regulation) after bitcoin update
            assert len(subscribed) == 3
            subscribed_names = [cat.category for cat in subscribed]
            assert "ethereum" in subscribed_names
            assert "altcoin" in subscribed_names
            assert "regulation" in subscribed_names
            assert "bitcoin" not in subscribed_names  # Updated to False
            
            # Query unsubscribed categories
            result = await session.execute(
                select(UserCategory).where(
                    UserCategory.user_id == user.id
                ).where(
                    UserCategory.is_subscribed == False
                )
            )
            unsubscribed = result.scalars().all()
            assert len(unsubscribed) == 5
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_subscription_relationships():
    """Test subscription model relationships"""
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
            # Create multiple users
            users = []
            for i in range(3):
                user = User(
                    username=f"reluser{i}",
                    email=f"rel{i}@example.com",
                    hashed_password=get_password_hash(f"relpass{i}")
                )
                session.add(user)
                users.append(user)
            
            # Create multiple sources
            sources = []
            for i in range(3):
                source = NewsSource(
                    name=f"Rel Source {i}",
                    url=f"https://rel{i}.com/rss",
                    source_type="rss",
                    category="crypto"
                )
                session.add(source)
                sources.append(source)
            
            await session.commit()
            
            # Refresh all
            for user in users:
                await session.refresh(user)
            for source in sources:
                await session.refresh(source)
            
            # Create subscription matrix (each user subscribes to different sources)
            subscription_matrix = [
                (0, 0, "bitcoin", 3, True),   # User 0, Source 0
                (0, 1, "ethereum", 4, False), # User 0, Source 1
                (1, 0, "defi", 2, True),      # User 1, Source 0
                (1, 2, "nft", 5, False),      # User 1, Source 2
                (2, 1, "altcoin", 1, True),   # User 2, Source 1
                (2, 2, "regulation", 4, True) # User 2, Source 2
            ]
            
            subscriptions = []
            for user_idx, source_idx, keywords, importance, urgent in subscription_matrix:
                subscription = UserSubscription(
                    user_id=users[user_idx].id,
                    source_id=sources[source_idx].id,
                    keywords=keywords,
                    min_importance=importance,
                    urgent_only=urgent,
                    is_active=True
                )
                session.add(subscription)
                subscriptions.append(subscription)
            
            await session.commit()
            
            # Refresh subscriptions
            for sub in subscriptions:
                await session.refresh(sub)
            
            # Test relationship queries
            from sqlalchemy import select
            
            # Test user 0 subscriptions
            result = await session.execute(
                select(UserSubscription).where(UserSubscription.user_id == users[0].id)
            )
            user0_subs = result.scalars().all()
            assert len(user0_subs) == 2
            
            # Verify subscription details
            bitcoin_sub = next(sub for sub in user0_subs if sub.keywords == "bitcoin")
            assert bitcoin_sub.source_id == sources[0].id
            assert bitcoin_sub.min_importance == 3
            assert bitcoin_sub.urgent_only is True
            
            ethereum_sub = next(sub for sub in user0_subs if sub.keywords == "ethereum")
            assert ethereum_sub.source_id == sources[1].id
            assert ethereum_sub.min_importance == 4
            assert ethereum_sub.urgent_only is False
            
            # Test source subscriptions
            result = await session.execute(
                select(UserSubscription).where(UserSubscription.source_id == sources[0].id)
            )
            source0_subs = result.scalars().all()
            assert len(source0_subs) == 2  # User 0 and User 1
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_subscription_filtering_scenarios():
    """Test subscription filtering with real scenarios"""
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
                username="filtertest",
                email="filter@example.com",
                hashed_password=get_password_hash("filtertest123")
            )
            source = NewsSource(
                name="Filter Source",
                url="https://filter.com/rss",
                source_type="rss",
                category="crypto"
            )
            session.add(user)
            session.add(source)
            await session.commit()
            await session.refresh(user)
            await session.refresh(source)
            
            # Test different subscription filter combinations
            filter_scenarios = [
                # Scenario 1: Only urgent, high importance
                {
                    "keywords": "bitcoin",
                    "min_importance": 4,
                    "urgent_only": True,
                    "test_name": "urgent_high_importance"
                },
                # Scenario 2: Keywords only, any importance
                {
                    "keywords": "ethereum,defi",
                    "min_importance": 1,
                    "urgent_only": False,
                    "test_name": "keywords_any_importance"
                },
                # Scenario 3: High importance only, no keyword filter
                {
                    "keywords": None,
                    "min_importance": 5,
                    "urgent_only": False,
                    "test_name": "high_importance_only"
                },
                # Scenario 4: All news (minimal filtering)
                {
                    "keywords": None,
                    "min_importance": 1,
                    "urgent_only": False,
                    "test_name": "minimal_filtering"
                }
            ]
            
            for scenario in filter_scenarios:
                # Create subscription
                subscription = UserSubscription(
                    user_id=user.id,
                    source_id=source.id,
                    keywords=scenario["keywords"],
                    min_importance=scenario["min_importance"],
                    urgent_only=scenario["urgent_only"],
                    is_active=True
                )
                session.add(subscription)
                await session.commit()
                await session.refresh(subscription)
                
                # Verify subscription was created with correct values
                assert subscription.user_id == user.id
                assert subscription.source_id == source.id
                assert subscription.keywords == scenario["keywords"]
                assert subscription.min_importance == scenario["min_importance"]
                assert subscription.urgent_only == scenario["urgent_only"]
                assert subscription.is_active is True
                
                # Clean up for next scenario
                await session.delete(subscription)
                await session.commit()
                
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_user_category_complete():
    """Complete UserCategory model testing"""
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
            # Create multiple users
            users = []
            for i in range(3):
                user = User(
                    username=f"catuser{i}",
                    email=f"cat{i}@example.com",
                    hashed_password=get_password_hash(f"cat{i}pass")
                )
                session.add(user)
                users.append(user)
            
            await session.commit()
            for user in users:
                await session.refresh(user)
            
            # Test comprehensive category scenarios
            all_categories = [
                "bitcoin", "ethereum", "defi", "nft", "altcoin", 
                "stablecoin", "regulation", "mining", "trading", "analysis"
            ]
            
            # Create categories for each user with different preferences
            for user_idx, user in enumerate(users):
                for cat_idx, category_name in enumerate(all_categories):
                    # Different subscription patterns for each user
                    if user_idx == 0:  # User 0: subscribes to first 5 categories
                        is_subscribed = cat_idx < 5
                    elif user_idx == 1:  # User 1: subscribes to even-indexed categories
                        is_subscribed = cat_idx % 2 == 0
                    else:  # User 2: subscribes to last 3 categories
                        is_subscribed = cat_idx >= 7
                    
                    category = UserCategory(
                        user_id=user.id,
                        category=category_name,
                        is_subscribed=is_subscribed
                    )
                    session.add(category)
            
            await session.commit()
            
            # Test category queries and relationships
            from sqlalchemy import select, and_
            
            # Test user 0 subscriptions (should be 5)
            result = await session.execute(
                select(UserCategory).where(
                    and_(
                        UserCategory.user_id == users[0].id,
                        UserCategory.is_subscribed == True
                    )
                )
            )
            user0_subscribed = result.scalars().all()
            assert len(user0_subscribed) == 5
            
            # Test user 1 subscriptions (even indices: 0,2,4,6,8 = 5 categories)
            result = await session.execute(
                select(UserCategory).where(
                    and_(
                        UserCategory.user_id == users[1].id,
                        UserCategory.is_subscribed == True
                    )
                )
            )
            user1_subscribed = result.scalars().all()
            assert len(user1_subscribed) == 5
            
            # Test user 2 subscriptions (indices 7,8,9 = 3 categories)
            result = await session.execute(
                select(UserCategory).where(
                    and_(
                        UserCategory.user_id == users[2].id,
                        UserCategory.is_subscribed == True
                    )
                )
            )
            user2_subscribed = result.scalars().all()
            assert len(user2_subscribed) == 3
            
            # Test category updates
            # Update user 0's bitcoin subscription
            result = await session.execute(
                select(UserCategory).where(
                    and_(
                        UserCategory.user_id == users[0].id,
                        UserCategory.category == "bitcoin"
                    )
                )
            )
            bitcoin_category = result.scalar_one()
            
            original_subscription = bitcoin_category.is_subscribed
            bitcoin_category.is_subscribed = not original_subscription
            await session.commit()
            await session.refresh(bitcoin_category)
            
            assert bitcoin_category.is_subscribed != original_subscription
            
            # Test bulk category operations
            # Get all categories for user 1
            result = await session.execute(
                select(UserCategory).where(UserCategory.user_id == users[1].id)
            )
            user1_categories = result.scalars().all()
            
            # Update all to unsubscribed
            for category in user1_categories:
                category.is_subscribed = False
            await session.commit()
            
            # Verify all are unsubscribed
            result = await session.execute(
                select(UserCategory).where(
                    and_(
                        UserCategory.user_id == users[1].id,
                        UserCategory.is_subscribed == True
                    )
                )
            )
            remaining_subscribed = result.scalars().all()
            assert len(remaining_subscribed) == 0
            
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

@pytest.mark.asyncio
async def test_real_subscription_api_endpoints():
    """Test subscription functionality through API endpoints"""
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
            
            # Create news with subscription-relevant categories
            async with SessionLocal() as session:
                # Create diverse news items for subscription testing
                news_items_data = [
                    ("Bitcoin Surge", "Bitcoin surges to new highs", "bitcoin", 5, True),
                    ("Ethereum Update", "Ethereum network upgrade", "ethereum", 4, False),
                    ("DeFi Protocol", "New DeFi protocol launches", "defi", 3, False),
                    ("NFT Market", "NFT market sees growth", "nft", 2, False),
                    ("Regulation News", "New crypto regulations", "regulation", 5, True),
                    ("Mining Update", "Bitcoin mining difficulty", "mining", 3, False),
                    ("Altcoin Rally", "Altcoins show strong performance", "altcoin", 4, True),
                    ("Stablecoin News", "USDC maintains peg", "stablecoin", 2, False)
                ]
                
                for title, content, category, importance, urgent in news_items_data:
                    news = NewsItem(
                        title=title,
                        content=content,
                        url=f"https://test.com/{title.replace(' ', '-').lower()}",
                        source="Subscription Test Source",
                        category=category,
                        published_at=datetime.now(),
                        importance_score=importance,
                        is_urgent=urgent,
                        market_impact=importance
                    )
                    session.add(news)
                
                await session.commit()
            
            # Test subscription-based filtering through API
            subscription_tests = [
                # Test high importance filter
                ("?importance=4", lambda items: all(item["importanceScore"] >= 4 for item in items)),
                # Test urgency filter
                ("?urgent=true", lambda items: all(item["isUrgent"] for item in items)),
                # Test category filter
                ("?category=bitcoin", lambda items: all(item["category"] == "bitcoin" for item in items)),
                # Test combined filters
                ("?category=regulation&urgent=true", lambda items: all(
                    item["category"] == "regulation" and item["isUrgent"] for item in items
                )),
                # Test limit with subscription filtering
                ("?limit=3&importance=3", lambda items: len(items) <= 3 and all(
                    item["importanceScore"] >= 3 for item in items
                ))
            ]
            
            for filter_param, validator in subscription_tests:
                response = await client.get(f"/news/{filter_param}", headers=headers)
                assert response.status_code == 200
                news_data = response.json()
                assert isinstance(news_data, list)
                
                if news_data:
                    assert validator(news_data), f"Filter validation failed for: {filter_param}"
        
        app.dependency_overrides.clear()
        
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()