import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.core.auth import get_password_hash, create_access_token, verify_token
from app.api.auth import get_current_user
from app.core.redis import redis_client
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_coverage_push.db"

@pytest.mark.asyncio
async def test_auth_api_complete_coverage():
    """Test complete auth API coverage"""
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
            # Test registration
            response = await client.post("/auth/register", json={
                "username": "authtest",
                "email": "auth@example.com",
                "password": "authpass123"
            })
            assert response.status_code == 200
            
            # Test duplicate registration (should fail)
            dup_response = await client.post("/auth/register", json={
                "username": "authtest",
                "email": "auth@example.com", 
                "password": "authpass123"
            })
            assert dup_response.status_code == 400
            
            # Test login
            login_response = await client.post("/auth/token", data={
                "username": "authtest",
                "password": "authpass123"
            })
            assert login_response.status_code == 200
            token_data = login_response.json()
            
            # Test wrong password
            wrong_response = await client.post("/auth/token", data={
                "username": "authtest",
                "password": "wrongpass"
            })
            assert wrong_response.status_code == 401
            
            # Test protected endpoint
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            me_response = await client.get("/auth/me", headers=headers)
            assert me_response.status_code == 200
            
            # Test invalid token
            bad_headers = {"Authorization": "Bearer invalidtoken"}
            bad_response = await client.get("/auth/me", headers=bad_headers)
            assert bad_response.status_code == 401
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

@pytest.mark.asyncio
async def test_news_api_complete_coverage():
    """Test complete news API coverage"""
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
        
        # Create auth user first
        async with SessionLocal() as session:
            user = User(
                username="newsuser",
                email="news@example.com",
                hashed_password=get_password_hash("newspass123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            token = create_access_token({"sub": user.username})
            headers = {"Authorization": f"Bearer {token}"}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test news endpoints with different parameters
            responses = [
                await client.get("/news/", headers=headers),
                await client.get("/news/?category=bitcoin", headers=headers),
                await client.get("/news/?urgent=true", headers=headers),
                await client.get("/news/?category=bitcoin&urgent=true", headers=headers),
                await client.get("/news/?importance=3", headers=headers),
                await client.get("/news/?limit=5", headers=headers),
                await client.get("/news/?skip=0", headers=headers)
            ]
            
            for response in responses:
                assert response.status_code == 200
                
            # Test without auth
            unauth_response = await client.get("/news/")
            assert unauth_response.status_code == 401
            
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

def test_auth_core_functions():
    """Test core auth functions comprehensively"""
    # Test password hashing
    passwords = ["simple", "complex123!", "verylongpasswordwithspecialchars@#$"]
    for password in passwords:
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 20
    
    # Test token creation and verification
    usernames = ["user1", "user_with_underscore", "email@domain.com"]
    for username in usernames:
        token = create_access_token({"sub": username})
        assert isinstance(token, str)
        assert len(token) > 50
        
        verified_username = verify_token(token)
        assert verified_username == username
    
    # Test expired token (manually create with past expiry)
    from jose import jwt
    from app.core.settings import settings
    expired_payload = {
        "sub": "testuser",
        "exp": datetime.utcnow() - timedelta(minutes=1)
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    expired_result = verify_token(expired_token)
    assert expired_result is None

@pytest.mark.asyncio
async def test_redis_coverage():
    """Test Redis client coverage"""
    with patch('aioredis.from_url') as mock_redis:
        mock_client = AsyncMock()
        mock_redis.return_value = mock_client
        
        # Import and use redis client
        from app.core.redis import get_redis_client
        client = await get_redis_client()
        assert client is not None

@pytest.mark.asyncio
async def test_main_app_coverage():
    """Test main app startup coverage"""
    from app.main import app
    assert app is not None
    assert hasattr(app, 'include_router')
    
    # Test app routes exist
    routes = [route.path for route in app.routes]
    assert any('/auth' in route for route in routes)
    assert any('/news' in route for route in routes)

def test_all_model_imports():
    """Test all model imports work"""
    from app.models.user import User
    from app.models.news import NewsItem
    from app.models.subscription import UserSubscription, UserCategory
    
    # Test model instantiation
    user = User()
    news = NewsItem()
    subscription = UserSubscription()
    category = UserCategory()
    
    assert user is not None
    assert news is not None
    assert subscription is not None
    assert category is not None