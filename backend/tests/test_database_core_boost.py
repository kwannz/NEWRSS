import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.database import Base, get_db, engine, SessionLocal
from app.models.user import User
from app.models.news import NewsItem
from app.core.settings import settings
from datetime import datetime
from unittest.mock import patch

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_database_core_boost.db"

@pytest.mark.asyncio
async def test_database_engine_operations():
    """Test database engine operations"""
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Test engine creation
    assert test_engine is not None
    
    # Test metadata operations
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Verify tables were created
        result = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in result.fetchall()]
        assert "users" in tables
        assert "news_items" in tables
        assert "user_subscriptions" in tables
        assert "user_categories" in tables
    
    await test_engine.dispose()

@pytest.mark.asyncio
async def test_session_factory():
    """Test session factory functionality"""
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        # Test session creation
        TestSessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=test_engine,
            class_=AsyncSession
        )
        
        # Test session usage
        async with TestSessionLocal() as session:
            assert isinstance(session, AsyncSession)
            
            # Test session operations
            user = User(
                username="sessiontest",
                email="session@example.com",
                hashed_password="sessionpass",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            assert user.id is not None
            
    finally:
        await test_engine.dispose()

def test_get_db_generator():
    """Test get_db dependency generator"""
    db_gen = get_db()
    assert db_gen is not None
    
    # Test that it's a generator
    import types
    assert isinstance(db_gen, types.GeneratorType)

@pytest.mark.asyncio
async def test_database_url_configuration():
    """Test database URL configuration"""
    # Test that database URL is properly configured
    assert settings.DATABASE_URL is not None
    assert isinstance(settings.DATABASE_URL, str)
    
    # Test engine creation with settings
    test_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    assert test_engine is not None
    await test_engine.dispose()

@pytest.mark.asyncio
async def test_database_connection_pooling():
    """Test database connection pooling"""
    test_engine = create_async_engine(
        TEST_DATABASE_URL, 
        echo=False,
        pool_size=5,
        max_overflow=10
    )
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        # Test multiple concurrent sessions
        SessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=test_engine,
            class_=AsyncSession
        )
        
        sessions = []
        for i in range(3):
            session = SessionLocal()
            sessions.append(session)
            
            user = User(
                username=f"pooltest{i}",
                email=f"pool{i}@example.com",
                hashed_password="poolpass",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            assert user.id is not None
        
        # Close all sessions
        for session in sessions:
            await session.close()
            
    finally:
        await test_engine.dispose()

@pytest.mark.asyncio
async def test_database_table_relationships():
    """Test database table relationships and foreign keys"""
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        SessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=test_engine,
            class_=AsyncSession
        )
        
        async with SessionLocal() as session:
            # Create user
            user = User(
                username="relationtest",
                email="relation@example.com",
                hashed_password="relationpass",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Test foreign key relationships work
            from app.models.subscription import UserSubscription, UserCategory
            
            subscription = UserSubscription(
                user_id=user.id,
                source_id=1,
                is_active=True,
                keywords="test",
                min_importance=1
            )
            session.add(subscription)
            
            category = UserCategory(
                user_id=user.id,
                category="bitcoin",
                is_subscribed=True
            )
            session.add(category)
            
            await session.commit()
            
            assert subscription.user_id == user.id
            assert category.user_id == user.id
            
    finally:
        await test_engine.dispose()

@pytest.mark.asyncio
async def test_database_schema_validation():
    """Test database schema and constraints"""
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Test that all expected tables exist
        result = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in result.fetchall()]
        
        expected_tables = ["users", "news_items", "user_subscriptions", "user_categories"]
        for table in expected_tables:
            assert table in tables
            
        # Test table schemas
        for table in expected_tables:
            schema_result = await conn.execute(f"PRAGMA table_info({table})")
            columns = schema_result.fetchall()
            assert len(columns) > 0
            
            # Check that each table has an id column
            column_names = [col[1] for col in columns]
            assert "id" in column_names
    
    await test_engine.dispose()