import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.subscription import UserSubscription, UserCategory
from app.models.user import User
from app.core.database import Base
from datetime import datetime

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_subscription_simple.db"

@pytest.mark.asyncio
async def test_subscription_model_creation():
    """Test subscription model creation"""
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
                username="testuser",
                email="test@example.com", 
                hashed_password="hashedpass",
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
                keywords="bitcoin,BTC",
                min_importance=3
            )
            session.add(subscription)
            await session.commit()
            
            assert subscription.id is not None
            assert subscription.user_id == user.id
            assert subscription.keywords == "bitcoin,BTC"
            
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_user_category_model():
    """Test user category model"""
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
                username="categoryuser",
                email="category@example.com",
                hashed_password="hashedpass",
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
async def test_subscription_status_update():
    """Test subscription status updates"""
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
                username="statususer",
                email="status@example.com",
                hashed_password="hashedpass"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create subscription
            subscription = UserSubscription(
                user_id=user.id,
                source_id=2,
                is_active=True,
                keywords="defi,DeFi",
                urgent_only=False
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            
            # Update status
            subscription.is_active = False
            await session.commit()
            
            assert subscription.is_active is False
            
    finally:
        await engine.dispose()