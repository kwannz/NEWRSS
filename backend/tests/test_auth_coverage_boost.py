import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.core.auth import get_password_hash, create_access_token, verify_token
from app.api.auth import get_current_user
from unittest.mock import patch
from datetime import datetime, timedelta

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_auth_boost.db"

@pytest.mark.asyncio
async def test_auth_registration_edge_cases():
    """Test auth registration with various edge cases"""
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
            # Test valid registration
            response = await client.post("/auth/register", json={
                "username": "validuser1",
                "email": "valid1@example.com",
                "password": "validpass123"
            })
            assert response.status_code == 200
            
            # Test duplicate username
            dup_response = await client.post("/auth/register", json={
                "username": "validuser1",
                "email": "different@example.com",
                "password": "validpass123"
            })
            assert dup_response.status_code == 400
            
            # Test duplicate email
            dup_email_response = await client.post("/auth/register", json={
                "username": "differentuser",
                "email": "valid1@example.com",
                "password": "validpass123"
            })
            assert dup_email_response.status_code == 400
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

@pytest.mark.asyncio
async def test_auth_login_scenarios():
    """Test various login scenarios"""
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
        
        # Create test user directly in database
        async with SessionLocal() as session:
            user = User(
                username="logintest",
                email="login@example.com",
                hashed_password=get_password_hash("loginpass123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test valid login
            response = await client.post("/auth/token", data={
                "username": "logintest",
                "password": "loginpass123"
            })
            assert response.status_code == 200
            token_data = response.json()
            assert "access_token" in token_data
            assert token_data["token_type"] == "bearer"
            
            # Test wrong username
            wrong_user_response = await client.post("/auth/token", data={
                "username": "wronguser",
                "password": "loginpass123"
            })
            assert wrong_user_response.status_code == 401
            
            # Test wrong password
            wrong_pass_response = await client.post("/auth/token", data={
                "username": "logintest",
                "password": "wrongpass"
            })
            assert wrong_pass_response.status_code == 401
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

@pytest.mark.asyncio
async def test_protected_endpoint_coverage():
    """Test protected endpoint scenarios"""
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
        
        # Create test user
        async with SessionLocal() as session:
            user = User(
                username="protectedtest",
                email="protected@example.com",
                hashed_password=get_password_hash("protectedpass123"),
                is_active=True,
                telegram_id="123456789"
            )
            session.add(user)
            await session.commit()
        
        token = create_access_token({"sub": "protectedtest"})
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test valid token
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get("/auth/me", headers=headers)
            assert response.status_code == 200
            user_data = response.json()
            assert user_data["username"] == "protectedtest"
            assert user_data["telegram_id"] == "123456789"
            
            # Test missing token
            no_token_response = await client.get("/auth/me")
            assert no_token_response.status_code == 422
            
            # Test invalid token format
            bad_headers = {"Authorization": "Bearer invalidtoken"}
            bad_response = await client.get("/auth/me", headers=bad_headers)
            assert bad_response.status_code == 401
            
            # Test malformed header
            malformed_headers = {"Authorization": "InvalidFormat token"}
            malformed_response = await client.get("/auth/me", headers=malformed_headers)
            assert malformed_response.status_code == 422
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

def test_token_verification_edge_cases():
    """Test token verification with edge cases"""
    # Test invalid token
    invalid_result = verify_token("completely_invalid_token")
    assert invalid_result is None
    
    # Test empty token
    empty_result = verify_token("")
    assert empty_result is None
    
    # Test None token
    none_result = verify_token(None)
    assert none_result is None

@pytest.mark.asyncio
async def test_get_current_user_scenarios():
    """Test get_current_user dependency scenarios"""
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
                username="currentusertest",
                email="currentuser@example.com",
                hashed_password=get_password_hash("currentpass123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Test valid token scenario
            valid_token = create_access_token({"sub": "currentusertest"})
            current_user = await get_current_user(valid_token, session)
            assert current_user is not None
            assert current_user.username == "currentusertest"
            
            # Test token for non-existent user
            nonexistent_token = create_access_token({"sub": "nonexistentuser"})
            with pytest.raises(Exception):  # Should raise HTTPException
                await get_current_user(nonexistent_token, session)
            
    finally:
        await engine.dispose()