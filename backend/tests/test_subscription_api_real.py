import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.user import User
from app.models.subscription import UserSubscription, UserCategory
from app.core.database import Base, get_db
from app.main import app
from app.core.auth import get_password_hash, create_access_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_subscription_api.db"

@pytest.mark.asyncio
async def test_subscription_model_basic():
    """Test subscription model basic functionality"""
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
            # Create test user
            user = User(
                username="subuser1",
                email="sub1@example.com",
                hashed_password=get_password_hash("password123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create subscription
            subscription = UserSubscription(
                user_id=user.id,
                source_id=1,
                is_active=True,
                keywords="bitcoin",
                min_importance=2,
                urgent_only=False
            )
            session.add(subscription)
            await session.commit()
            
            assert subscription.id is not None
            assert subscription.user_id == user.id
            assert subscription.keywords == "bitcoin"
            assert subscription.min_importance == 2
            assert subscription.urgent_only is False
            
    finally:
        await engine.dispose()

@pytest.mark.asyncio 
async def test_user_category_basic():
    """Test user category model basic functionality"""
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
            # Create test user
            user = User(
                username="catuser1",
                email="cat1@example.com",
                hashed_password=get_password_hash("password123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create user category
            category = UserCategory(
                user_id=user.id,
                category="ethereum",
                is_subscribed=True
            )
            session.add(category)
            await session.commit()
            
            assert category.id is not None
            assert category.user_id == user.id
            assert category.category == "ethereum"
            assert category.is_subscribed is True
            
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_subscription_update_operations():
    """Test subscription update and status changes"""
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
            # Create test user
            user = User(
                username="updateuser1",
                email="update1@example.com",
                hashed_password=get_password_hash("password123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create subscription
            subscription = UserSubscription(
                user_id=user.id,
                source_id=2,
                is_active=True,
                keywords="defi",
                min_importance=1
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            
            # Update subscription
            subscription.is_active = False
            subscription.min_importance = 5
            subscription.keywords = "defi,ethereum"
            await session.commit()
            
            assert subscription.is_active is False
            assert subscription.min_importance == 5
            assert subscription.keywords == "defi,ethereum"
            
    finally:
        await engine.dispose()