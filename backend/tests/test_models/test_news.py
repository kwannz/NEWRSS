import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.news import NewsItem, NewsSource

class TestNewsItem:
    
    @pytest.mark.asyncio
    async def test_create_news_item(self, db_session: AsyncSession):
        """测试创建新闻项目"""
        news_item = NewsItem(
            title="Test Bitcoin News",
            content="Bitcoin reaches new high of $50000",
            url="https://example.com/btc-news",
            source="CoinDesk",
            category="bitcoin",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            importance_score=4,
            is_urgent=True,
            market_impact=3,
            sentiment_score=0.8,
            key_tokens='["BTC", "Bitcoin"]',
            key_prices='["$50000"]',
            is_processed=True
        )
        
        db_session.add(news_item)
        await db_session.commit()
        await db_session.refresh(news_item)
        
        assert news_item.id is not None
        assert news_item.title == "Test Bitcoin News"
        assert news_item.content == "Bitcoin reaches new high of $50000"
        assert news_item.url == "https://example.com/btc-news"
        assert news_item.source == "CoinDesk"
        assert news_item.category == "bitcoin"
        assert news_item.importance_score == 4
        assert news_item.is_urgent is True
        assert news_item.market_impact == 3
        assert news_item.sentiment_score == 0.8
        assert news_item.key_tokens == '["BTC", "Bitcoin"]'
        assert news_item.key_prices == '["$50000"]'
        assert news_item.is_processed is True
        assert news_item.created_at is not None
        assert news_item.updated_at is None

    @pytest.mark.asyncio
    async def test_news_item_defaults(self, db_session: AsyncSession):
        """测试新闻项目默认值"""
        news_item = NewsItem(
            title="Minimal News",
            content="Minimal content",
            url="https://example.com/minimal",
            source="TestSource",
            published_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        db_session.add(news_item)
        await db_session.commit()
        await db_session.refresh(news_item)
        
        assert news_item.importance_score == 1
        assert news_item.is_urgent is False
        assert news_item.market_impact == 1
        assert news_item.sentiment_score is None
        assert news_item.is_processed is False
        assert news_item.category is None

    @pytest.mark.asyncio
    async def test_news_item_unique_url(self, db_session: AsyncSession):
        """测试URL唯一性约束"""
        url = "https://example.com/duplicate"
        
        news_item1 = NewsItem(
            title="First News",
            content="First content",
            url=url,
            source="Source1",
            published_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        news_item2 = NewsItem(
            title="Second News",
            content="Second content",
            url=url,  # 相同URL
            source="Source2",
            published_at=datetime(2024, 1, 1, 13, 0, 0)
        )
        
        db_session.add(news_item1)
        await db_session.commit()
        
        db_session.add(news_item2)
        with pytest.raises(Exception):  # 应该抛出唯一性约束异常
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_news_item_validation_ranges(self, db_session: AsyncSession):
        """测试字段值范围验证"""
        # 测试正常范围
        news_item = NewsItem(
            title="Valid News",
            content="Valid content",
            url="https://example.com/valid",
            source="ValidSource",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            importance_score=3,
            market_impact=4,
            sentiment_score=0.5
        )
        
        db_session.add(news_item)
        await db_session.commit()
        await db_session.refresh(news_item)
        
        assert 1 <= news_item.importance_score <= 5
        assert 1 <= news_item.market_impact <= 5
        assert -1 <= news_item.sentiment_score <= 1

class TestNewsSource:
    
    @pytest.mark.asyncio
    async def test_create_news_source(self, db_session: AsyncSession):
        """测试创建新闻源"""
        news_source = NewsSource(
            name="CoinDesk RSS",
            url="https://feeds.coindesk.com/all",
            source_type="rss",
            category="general",
            is_active=True,
            fetch_interval=60,
            priority=5
        )
        
        db_session.add(news_source)
        await db_session.commit()
        await db_session.refresh(news_source)
        
        assert news_source.id is not None
        assert news_source.name == "CoinDesk RSS"
        assert news_source.url == "https://feeds.coindesk.com/all"
        assert news_source.source_type == "rss"
        assert news_source.category == "general"
        assert news_source.is_active is True
        assert news_source.fetch_interval == 60
        assert news_source.priority == 5
        assert news_source.created_at is not None
        assert news_source.last_fetched is None

    @pytest.mark.asyncio
    async def test_news_source_defaults(self, db_session: AsyncSession):
        """测试新闻源默认值"""
        news_source = NewsSource(
            name="Minimal Source",
            url="https://example.com/feed",
            source_type="rss"
        )
        
        db_session.add(news_source)
        await db_session.commit()
        await db_session.refresh(news_source)
        
        assert news_source.is_active is True
        assert news_source.fetch_interval == 30
        assert news_source.priority == 1
        assert news_source.category is None

    @pytest.mark.asyncio
    async def test_news_source_unique_constraints(self, db_session: AsyncSession):
        """测试新闻源唯一性约束"""
        # 测试名称唯一性
        source1 = NewsSource(
            name="Duplicate Name",
            url="https://example.com/feed1",
            source_type="rss"
        )
        
        source2 = NewsSource(
            name="Duplicate Name",  # 相同名称
            url="https://example.com/feed2",
            source_type="rss"
        )
        
        db_session.add(source1)
        await db_session.commit()
        
        db_session.add(source2)
        with pytest.raises(Exception):  # 名称唯一性约束
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_news_source_url_unique(self, db_session: AsyncSession):
        """测试新闻源URL唯一性"""
        url = "https://example.com/same-feed"
        
        source1 = NewsSource(
            name="Source One",
            url=url,
            source_type="rss"
        )
        
        source2 = NewsSource(
            name="Source Two",
            url=url,  # 相同URL
            source_type="api"
        )
        
        db_session.add(source1)
        await db_session.commit()
        
        db_session.add(source2)
        with pytest.raises(Exception):  # URL唯一性约束
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_news_source_update_last_fetched(self, db_session: AsyncSession):
        """测试更新最后获取时间"""
        news_source = NewsSource(
            name="Update Test Source",
            url="https://example.com/update-test",
            source_type="rss"
        )
        
        db_session.add(news_source)
        await db_session.commit()
        await db_session.refresh(news_source)
        
        assert news_source.last_fetched is None
        
        # 更新最后获取时间
        fetch_time = datetime(2024, 1, 1, 12, 0, 0)
        news_source.last_fetched = fetch_time
        await db_session.commit()
        await db_session.refresh(news_source)
        
        assert news_source.last_fetched == fetch_time