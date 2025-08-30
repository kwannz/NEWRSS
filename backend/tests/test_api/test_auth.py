import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.auth import get_password_hash

class TestAuthAPI:
    
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """测试用户注册成功"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com", 
            "password": "testpass123"
        }
        
        response = await client.post("/auth/register", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, db_session: AsyncSession):
        """测试重复用户名注册失败"""
        # 先创建一个用户
        user = User(
            username="existinguser",
            email="existing@example.com",
            hashed_password=get_password_hash("password")
        )
        db_session.add(user)
        await db_session.commit()
        
        # 尝试注册相同用户名
        user_data = {
            "username": "existinguser",
            "email": "new@example.com",
            "password": "newpass123"
        }
        
        response = await client.post("/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, db_session: AsyncSession):
        """测试登录成功"""
        # 创建测试用户
        user = User(
            username="loginuser",
            email="login@example.com",
            hashed_password=get_password_hash("loginpass123")
        )
        db_session.add(user)
        await db_session.commit()
        
        # 登录
        login_data = {
            "username": "loginuser",
            "password": "loginpass123"
        }
        
        response = await client.post("/auth/token", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, db_session: AsyncSession):
        """测试错误密码登录失败"""
        user = User(
            username="wrongpassuser",
            email="wrongpass@example.com",
            hashed_password=get_password_hash("correctpass")
        )
        db_session.add(user)
        await db_session.commit()
        
        login_data = {
            "username": "wrongpassuser",
            "password": "wrongpass"
        }
        
        response = await client.post("/auth/token", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在的用户登录失败"""
        login_data = {
            "username": "nonexistent",
            "password": "password"
        }
        
        response = await client.post("/auth/token", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client: AsyncClient, db_session: AsyncSession):
        """测试获取当前用户信息成功"""
        # 创建并登录用户
        user = User(
            username="currentuser",
            email="current@example.com",
            hashed_password=get_password_hash("currentpass")
        )
        db_session.add(user)
        await db_session.commit()
        
        # 登录获取token
        login_response = await client.post("/auth/token", data={
            "username": "currentuser",
            "password": "currentpass"
        })
        token = login_response.json()["access_token"]
        
        # 获取用户信息
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "currentuser"
        assert data["email"] == "current@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """测试无效token获取用户信息失败"""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """测试没有token获取用户信息失败"""
        response = await client.get("/auth/me")
        
        assert response.status_code == 401