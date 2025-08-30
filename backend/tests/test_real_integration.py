import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.news import NewsItem, NewsSource
from app.models.user import User
from app.core.auth import get_password_hash, create_access_token
from app.services.rss_fetcher import RSSFetcher
from app.services.ai_analyzer import AINewsAnalyzer
from datetime import datetime
import os
import redis.asyncio as redis

# Set test OpenAI API key
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

@pytest.mark.asyncio
async def test_real_database_operations(db_session):
    """真实数据库操作测试"""
    # 创建真实用户
    user = User(
        username="realuser",
        email="real@example.com",
        hashed_password=get_password_hash("realpass123"),
        telegram_id="123456789",
        urgent_notifications=True,
        daily_digest=True
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    assert user.id is not None
    assert user.username == "realuser"
    assert user.is_active is True
    
    # 创建真实新闻源
    news_source = NewsSource(
        name="Real CoinDesk",
        url="https://feeds.coindesk.com/all",
        source_type="rss",
        category="crypto",
        is_active=True,
        fetch_interval=60,
        priority=3
    )
    
    db_session.add(news_source)
    await db_session.commit()
    await db_session.refresh(news_source)
    
    assert news_source.id is not None
    assert news_source.name == "Real CoinDesk"
    
    # 创建真实新闻项
    news_item = NewsItem(
        title="Real Bitcoin News",
        content="Bitcoin reaches new heights in real market conditions",
        url="https://real-example.com/bitcoin-news",
        source="Real CoinDesk",
        category="bitcoin",
        published_at=datetime.now(),
        importance_score=4,
        is_urgent=False,
        market_impact=3,
        content_hash="real123abc"
    )
    
    db_session.add(news_item)
    await db_session.commit()
    await db_session.refresh(news_item)
    
    assert news_item.id is not None
    assert news_item.title == "Real Bitcoin News"

@pytest.mark.asyncio
async def test_real_api_endpoints(client, db_session):
    """真实API端点测试"""
    # 1. 注册真实用户
    register_data = {
        "username": "apiuser",
        "email": "api@example.com",
        "password": "apipass123"
    }
    
    register_response = await client.post("/auth/register", json=register_data)
    assert register_response.status_code == 200
    user_data = register_response.json()
    assert user_data["username"] == "apiuser"
    assert "id" in user_data
    
    # 2. 登录获取真实token
    login_response = await client.post("/auth/token", data={
        "username": "apiuser", 
        "password": "apipass123"
    })
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    token = token_data["access_token"]
    
    # 3. 使用真实token访问受保护端点
    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["username"] == "apiuser"

@pytest.mark.asyncio
async def test_real_rss_fetcher():
    """真实RSS获取器测试"""
    async with RSSFetcher() as fetcher:
        # 使用真实RSS源测试
        items = await fetcher.fetch_feed("https://feeds.feedburner.com/oreilly/radar", "O'Reilly Radar")
        
        # 验证返回结果
        assert isinstance(items, list)
        if items:  # 如果有数据返回
            item = items[0]
            assert "title" in item
            assert "content" in item
            assert "url" in item
            assert "source" in item
            assert "published_at" in item
            assert "content_hash" in item

@pytest.mark.asyncio
async def test_real_ai_analyzer_without_api_key():
    """测试AI分析器不使用真实API key"""
    # 暂时移除API key以测试错误处理
    original_key = os.environ.get("OPENAI_API_KEY")
    os.environ.pop("OPENAI_API_KEY", None)
    
    try:
        analyzer = AINewsAnalyzer()
        
        # 测试摘要生成（应该返回错误信息）
        summary = await analyzer.generate_summary("Test news content")
        assert summary == "未配置 OpenAI API Key"
        
        # 测试情感分析（应该返回0.0）
        sentiment = await analyzer.analyze_sentiment("Test news content")
        assert sentiment == 0.0
        
    finally:
        # 恢复API key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

@pytest.mark.asyncio
async def test_real_news_crud_operations(client, db_session):
    """真实新闻CRUD操作测试"""
    # 创建测试用户和token
    user = User(
        username="newsuser",
        email="news@example.com",
        hashed_password=get_password_hash("newspass123")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # 创建真实新闻数据
    news_items = []
    for i in range(5):
        news_item = NewsItem(
            title=f"Real News {i}",
            content=f"Real content about Bitcoin news {i}",
            url=f"https://example.com/news/{i}",
            source="Real Source",
            category="bitcoin" if i % 2 == 0 else "ethereum",
            published_at=datetime.now(),
            importance_score=i + 1,
            is_urgent=i % 3 == 0,
            market_impact=3,
            content_hash=f"realhash{i}"
        )
        news_items.append(news_item)
        db_session.add(news_item)
    
    await db_session.commit()
    
    # 测试新闻API端点
    token = create_access_token({"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取所有新闻
    response = await client.get("/news/", headers=headers)
    assert response.status_code == 200
    news_data = response.json()
    assert len(news_data) >= 5
    
    # 按类别过滤
    response = await client.get("/news/?category=bitcoin", headers=headers)
    assert response.status_code == 200
    bitcoin_news = response.json()
    assert all(item["category"] == "bitcoin" for item in bitcoin_news)

@pytest.mark.asyncio
async def test_real_redis_operations():
    """真实Redis操作测试"""
    # 连接真实Redis
    redis_client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
    
    try:
        # 测试基本操作
        await redis_client.set("test_key", "test_value", ex=3600)
        value = await redis_client.get("test_key")
        assert value == "test_value"
        
        # 测试Hash操作
        await redis_client.hset("test_hash", "field1", "value1")
        await redis_client.hset("test_hash", "field2", "value2")
        hash_value = await redis_client.hget("test_hash", "field1")
        assert hash_value == "value1"
        
        # 测试List操作
        await redis_client.lpush("test_list", "item1", "item2", "item3")
        list_length = await redis_client.llen("test_list")
        assert list_length == 3
        
        # 测试Set操作
        await redis_client.sadd("test_set", "member1", "member2", "member3")
        set_size = await redis_client.scard("test_set")
        assert set_size == 3
        
        is_member = await redis_client.sismember("test_set", "member1")
        assert is_member == 1
        
        # 测试计数器
        count1 = await redis_client.incr("test_counter")
        assert count1 == 1
        count2 = await redis_client.incr("test_counter")
        assert count2 == 2
        
    finally:
        # 清理测试数据
        await redis_client.flushdb()
        await redis_client.close()

@pytest.mark.asyncio
async def test_real_rss_fetcher_operations():
    """真实RSS获取器操作测试"""
    async with RSSFetcher() as fetcher:
        # 测试多个RSS源获取
        sources = [
            {
                "url": "https://feeds.feedburner.com/oreilly/radar",
                "name": "O'Reilly Radar",
                "category": "tech"
            }
        ]
        
        items = await fetcher.fetch_multiple_feeds(sources)
        assert isinstance(items, list)
        
        # 如果有数据，验证结构
        if items:
            item = items[0]
            assert "category" in item
            assert item["category"] == "tech"

@pytest.mark.asyncio  
async def test_real_ai_analyzer_functions():
    """测试AI分析器功能"""
    analyzer = AINewsAnalyzer()
    
    test_content = "Bitcoin price surges to new all-time high of $60000"
    
    # 测试关键信息提取（不需要API key）
    key_info = await analyzer.extract_key_information(test_content)
    assert isinstance(key_info, dict)
    assert "tokens" in key_info
    assert "prices" in key_info
    assert "exchanges" in key_info
    
    # 应该提取到价格信息
    assert any("60000" in price for price in key_info["prices"])

@pytest.mark.asyncio
async def test_comprehensive_error_handling(client, db_session):
    """全面的错误处理测试"""
    # 测试各种API错误情况
    
    # 1. 认证错误
    unauth_response = await client.get("/auth/me")
    assert unauth_response.status_code == 401
    
    # 2. 无效token
    invalid_response = await client.get(
        "/auth/me", 
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert invalid_response.status_code == 401
    
    # 3. 测试各种无效参数
    invalid_params = [
        "category=invalid_category",
        "limit=-1",
        "importance=6",
        "urgent=invalid_bool"
    ]
    
    for param in invalid_params:
        response = await client.get(f"/news/?{param}")
        # 应该优雅处理错误，不崩溃
        assert response.status_code in [200, 400, 422]