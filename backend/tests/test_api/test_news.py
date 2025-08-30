import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.news import NewsItem
from app.models.user import User
from app.core.auth import get_password_hash
import json

class TestNewsAPI:
    
    @pytest.mark.asyncio
    async def test_get_news_list_empty(self, client: AsyncClient):
        """测试获取空新闻列表"""
        response = await client.get("/news/")
        
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_news_list_with_data(self, client: AsyncClient, db_session: AsyncSession):
        """测试获取新闻列表（包含数据）"""
        # 创建测试新闻
        news_items = [
            NewsItem(
                title="Bitcoin News 1",
                content="Content 1",
                url="https://example.com/1",
                source="CoinDesk",
                category="bitcoin",
                published_at=datetime(2024, 1, 1, 12, 0, 0),
                importance_score=3,
                is_urgent=False,
                market_impact=2
            ),
            NewsItem(
                title="Ethereum News 2",
                content="Content 2", 
                url="https://example.com/2",
                source="Decrypt",
                category="ethereum",
                published_at=datetime(2024, 1, 1, 13, 0, 0),
                importance_score=4,
                is_urgent=True,
                market_impact=3
            )
        ]
        
        for item in news_items:
            db_session.add(item)
        await db_session.commit()
        
        response = await client.get("/news/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # 应该按发布时间倒序排列
        assert data[0]["title"] == "Ethereum News 2"
        assert data[1]["title"] == "Bitcoin News 1"

    @pytest.mark.asyncio
    async def test_get_news_list_with_filters(self, client: AsyncClient, db_session: AsyncSession):
        """测试带过滤条件的新闻列表"""
        # 创建测试数据
        news_items = [
            NewsItem(
                title="Bitcoin News",
                content="Bitcoin content",
                url="https://example.com/btc",
                source="CoinDesk",
                category="bitcoin",
                published_at=datetime(2024, 1, 1, 12, 0, 0),
                importance_score=5,
                is_urgent=True,
                market_impact=4
            ),
            NewsItem(
                title="Ethereum News",
                content="Ethereum content",
                url="https://example.com/eth",
                source="Decrypt",
                category="ethereum",
                published_at=datetime(2024, 1, 1, 13, 0, 0),
                importance_score=2,
                is_urgent=False,
                market_impact=1
            )
        ]
        
        for item in news_items:
            db_session.add(item)
        await db_session.commit()
        
        # 测试分类过滤
        response = await client.get("/news/?category=bitcoin")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "bitcoin"
        
        # 测试来源过滤
        response = await client.get("/news/?source=Decrypt")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "Decrypt"
        
        # 测试紧急新闻过滤
        response = await client.get("/news/?urgent_only=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["isUrgent"] is True
        
        # 测试重要性过滤
        response = await client.get("/news/?min_importance=4")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["importanceScore"] >= 4

    @pytest.mark.asyncio
    async def test_get_news_list_pagination(self, client: AsyncClient, db_session: AsyncSession):
        """测试分页功能"""
        # 创建多条测试数据
        for i in range(25):
            news_item = NewsItem(
                title=f"News {i}",
                content=f"Content {i}",
                url=f"https://example.com/{i}",
                source="TestSource",
                published_at=datetime(2024, 1, 1, i % 24, 0, 0),
                importance_score=1,
                is_urgent=False,
                market_impact=1
            )
            db_session.add(news_item)
        await db_session.commit()
        
        # 测试第一页
        response = await client.get("/news/?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        # 测试第二页
        response = await client.get("/news/?page=2&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        # 测试第三页
        response = await client.get("/news/?page=3&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_get_news_item_success(self, client: AsyncClient, db_session: AsyncSession):
        """测试获取单个新闻成功"""
        news_item = NewsItem(
            title="Test News",
            content="Test content",
            url="https://example.com/test",
            source="TestSource",
            category="test",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            importance_score=3,
            is_urgent=False,
            market_impact=2,
            key_tokens='["BTC", "ETH"]',
            key_prices='["$50000", "$3000"]'
        )
        db_session.add(news_item)
        await db_session.commit()
        await db_session.refresh(news_item)
        
        response = await client.get(f"/news/{news_item.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test News"
        assert data["content"] == "Test content"
        assert data["keyTokens"] == ["BTC", "ETH"]
        assert data["keyPrices"] == ["$50000", "$3000"]

    @pytest.mark.asyncio
    async def test_get_news_item_not_found(self, client: AsyncClient):
        """测试获取不存在的新闻"""
        response = await client.get("/news/999999")
        
        assert response.status_code == 404
        assert "News item not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_news_list_validation_errors(self, client: AsyncClient):
        """测试查询参数验证错误"""
        # 测试无效页码
        response = await client.get("/news/?page=0")
        assert response.status_code == 422
        
        # 测试无效限制
        response = await client.get("/news/?limit=0")
        assert response.status_code == 422
        
        response = await client.get("/news/?limit=1000")
        assert response.status_code == 422
        
        # 测试无效重要性
        response = await client.get("/news/?min_importance=0")
        assert response.status_code == 422
        
        response = await client.get("/news/?min_importance=10")
        assert response.status_code == 422