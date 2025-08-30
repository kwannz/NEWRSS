import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.database import get_db, Base
from app.models.user import User
from app.models.news import NewsItem
from datetime import datetime

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_database_functions.db"

@pytest.mark.asyncio
async def test_database_session_creation():
    """Test database session creation and management"""
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
            assert session is not None
            assert isinstance(session, AsyncSession)
            
            # Test session operations
            user = User(
                username="dbtest1",
                email="dbtest1@example.com",
                hashed_password="hashedpass",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            assert user.id is not None
            assert user.username == "dbtest1"
            
    finally:
        await test_engine.dispose()

@pytest.mark.asyncio
async def test_get_db_dependency():
    """Test get_db dependency function"""
    db_generator = get_db()
    assert db_generator is not None

@pytest.mark.asyncio
async def test_base_model_functionality():
    """Test SQLAlchemy Base model functionality"""
    assert Base is not None
    assert hasattr(Base, 'metadata')
    assert hasattr(Base.metadata, 'create_all')

@pytest.mark.asyncio
async def test_database_crud_operations():
    """Test basic CRUD operations on database"""
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
            # CREATE
            user = User(
                username="crudtest",
                email="crud@example.com",
                hashed_password="pass123",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # READ
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.username == "crudtest"))
            found_user = result.scalar_one_or_none()
            assert found_user is not None
            assert found_user.email == "crud@example.com"
            
            # UPDATE
            found_user.is_active = False
            await session.commit()
            await session.refresh(found_user)
            assert found_user.is_active is False
            
            # DELETE
            await session.delete(found_user)
            await session.commit()
            
            result = await session.execute(select(User).where(User.username == "crudtest"))
            deleted_user = result.scalar_one_or_none()
            assert deleted_user is None
            
    finally:
        await test_engine.dispose()

@pytest.mark.asyncio
async def test_database_transactions():
    """Test database transaction management"""
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
            try:
                # Create user in transaction
                user = User(
                    username="transtest",
                    email="trans@example.com",
                    hashed_password="pass123"
                )
                session.add(user)
                await session.commit()
                
                # Verify transaction succeeded
                from sqlalchemy import select
                result = await session.execute(select(User).where(User.username == "transtest"))
                committed_user = result.scalar_one_or_none()
                assert committed_user is not None
                
            except Exception as e:
                await session.rollback()
                raise
            
    finally:
        await test_engine.dispose()

@pytest.mark.asyncio
async def test_database_constraints():
    """Test database constraint validation"""
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
            # Create first user
            user1 = User(
                username="unique1",
                email="unique1@example.com",
                hashed_password="pass123"
            )
            session.add(user1)
            await session.commit()
            
            # Try to create duplicate username (should fail)
            user2 = User(
                username="unique1",  # duplicate username
                email="unique2@example.com",
                hashed_password="pass123"
            )
            session.add(user2)
            
            with pytest.raises(Exception):  # Should raise constraint violation
                await session.commit()
                
    finally:
        await test_engine.dispose()