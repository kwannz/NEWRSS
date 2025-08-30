import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.news import NewsItem
from app.models.user import User  
from app.core.auth import get_password_hash
from datetime import datetime

class TestIntegration:
    """集成测试，提高API覆盖率"""
    
    @pytest.mark.asyncio
    async def test_complete_user_flow(self, client: AsyncClient, db_session: AsyncSession):
        """完整用户流程测试"""
        # 1. 注册用户
        register_data = {
            "username": "flowuser",
            "email": "flow@example.com",
            "password": "flowpass123"
        }
        
        register_response = await client.post("/auth/register", json=register_data)
        assert register_response.status_code == 200
        user_data = register_response.json()
        assert user_data["username"] == "flowuser"
        
        # 2. 登录获取token
        login_response = await client.post("/auth/token", data={
            "username": "flowuser",
            "password": "flowpass123"
        })
        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data["access_token"]
        
        # 3. 访问受保护的用户信息
        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["username"] == "flowuser"
        
    @pytest.mark.asyncio
    async def test_news_api_comprehensive(self, client: AsyncClient, db_session: AsyncSession):
        """全面的新闻API测试"""
        # 创建测试新闻数据
        news_items = []
        for i in range(15):
            news_item = NewsItem(
                title=f"News {i}",
                content=f"Content {i}",
                url=f"https://example.com/{i}",
                source="TestSource",
                category="bitcoin" if i % 2 == 0 else "ethereum",
                published_at=datetime(2024, 1, 1, i % 24, 0, 0),
                importance_score=(i % 5) + 1,
                is_urgent=i % 3 == 0,
                market_impact=(i % 5) + 1,
                key_tokens=f'["TOKEN{i}"]',
                key_prices=f'["${i}000"]'
            )
            db_session.add(news_item)
            news_items.append(news_item)
        
        await db_session.commit()
        
        # 刷新所有项目以获取ID
        for item in news_items:
            await db_session.refresh(item)
        
        # 测试无过滤的新闻列表
        response = await client.get("/news/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 15
        
        # 测试分页
        response = await client.get("/news/?page=1&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        
        # 测试过滤 - 分类
        response = await client.get("/news/?category=bitcoin")
        assert response.status_code == 200
        data = response.json()
        assert all(item["category"] == "bitcoin" for item in data)
        
        # 测试过滤 - 来源
        response = await client.get("/news/?source=TestSource")
        assert response.status_code == 200
        data = response.json()
        assert all(item["source"] == "TestSource" for item in data)
        
        # 测试过滤 - 紧急新闻
        response = await client.get("/news/?urgent_only=true")
        assert response.status_code == 200
        data = response.json()
        assert all(item["isUrgent"] is True for item in data)
        
        # 测试过滤 - 重要性
        response = await client.get("/news/?min_importance=4")
        assert response.status_code == 200
        data = response.json()
        assert all(item["importanceScore"] >= 4 for item in data)
        
        # 测试获取单个新闻
        news_id = news_items[0].id
        response = await client.get(f"/news/{news_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == news_id
        assert data["title"] == "News 0"
        
    @pytest.mark.asyncio
    async def test_error_cases(self, client: AsyncClient):
        """错误情况测试"""
        # 测试无效的新闻ID
        response = await client.get("/news/999999")
        assert response.status_code == 404
        
        # 测试无效的查询参数
        response = await client.get("/news/?page=0")
        assert response.status_code == 422
        
        response = await client.get("/news/?limit=1000")
        assert response.status_code == 422
        
        response = await client.get("/news/?min_importance=10")
        assert response.status_code == 422
        
        # 测试重复注册
        user_data = {
            "username": "duplicate",
            "email": "duplicate@example.com",
            "password": "password123"
        }
        
        response1 = await client.post("/auth/register", json=user_data)
        assert response1.status_code == 200
        
        response2 = await client.post("/auth/register", json=user_data)
        assert response2.status_code == 400
        
        # 测试错误登录
        response = await client.post("/auth/token", data={
            "username": "nonexistent",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        
        # 测试无效token
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401