import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.services.rss_fetcher import RSSFetcher

class TestRSSFetcher:
    
    @pytest.mark.asyncio
    async def test_init_and_context_manager(self):
        """测试初始化和上下文管理器"""
        fetcher = RSSFetcher()
        assert fetcher.session is None
        
        async with fetcher:
            assert fetcher.session is not None
            assert isinstance(fetcher.session, aiohttp.ClientSession)
        
        assert fetcher.session is None or fetcher.session.closed

    @pytest.mark.asyncio
    async def test_fetch_feed_success(self):
        """测试成功获取RSS feed"""
        mock_response_text = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Crypto News</title>
                <item>
                    <title>Bitcoin News</title>
                    <description>Bitcoin reaches new high</description>
                    <link>https://example.com/btc</link>
                    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_response_text)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.fetch_feed("https://example.com/feed", "TestSource")
            
            assert len(result) == 1
            assert result[0]['title'] == 'Bitcoin News'
            assert result[0]['content'] == 'Bitcoin reaches new high'
            assert result[0]['url'] == 'https://example.com/btc'
            assert result[0]['source'] == 'TestSource'
            assert 'content_hash' in result[0]
            assert isinstance(result[0]['published_at'], datetime)

    @pytest.mark.asyncio
    async def test_fetch_feed_http_error(self):
        """测试HTTP错误响应"""
        with patch('aiohttp.ClientSession.get') as mock_get, \
             patch('builtins.print') as mock_print:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.fetch_feed("https://example.com/404", "TestSource")
            
            assert result == []
            mock_print.assert_called_with("Error fetching https://example.com/404: HTTP 404")

    @pytest.mark.asyncio
    async def test_fetch_feed_timeout(self):
        """测试请求超时"""
        with patch('aiohttp.ClientSession.get') as mock_get, \
             patch('builtins.print') as mock_print:
            mock_get.side_effect = aiohttp.ServerTimeoutError()
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.fetch_feed("https://example.com/timeout", "TestSource")
            
            assert result == []
            mock_print.assert_called_with("Timeout fetching https://example.com/timeout")

    @pytest.mark.asyncio
    async def test_fetch_feed_malformed_xml(self):
        """测试格式错误的XML"""
        malformed_xml = "invalid xml content"
        
        with patch('aiohttp.ClientSession.get') as mock_get, \
             patch('builtins.print') as mock_print:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=malformed_xml)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.fetch_feed("https://example.com/malformed", "TestSource")
            
            # 仍应返回空列表，但有警告
            assert result == []
            assert mock_print.called

    @pytest.mark.asyncio
    async def test_fetch_multiple_feeds_success(self):
        """测试批量获取多个feeds成功"""
        sources = [
            {"url": "https://example.com/feed1", "name": "Source1", "category": "bitcoin"},
            {"url": "https://example.com/feed2", "name": "Source2", "category": "ethereum"}
        ]
        
        mock_items_1 = [{"title": "BTC News", "category": "bitcoin"}]
        mock_items_2 = [{"title": "ETH News", "category": "ethereum"}]
        
        with patch.object(RSSFetcher, 'fetch_feed') as mock_fetch:
            mock_fetch.side_effect = [mock_items_1, mock_items_2]
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.fetch_multiple_feeds(sources)
            
            assert len(result) == 2
            assert result[0]['title'] == "BTC News"
            assert result[0]['category'] == "bitcoin"
            assert result[1]['title'] == "ETH News"
            assert result[1]['category'] == "ethereum"

    @pytest.mark.asyncio
    async def test_fetch_multiple_feeds_with_errors(self):
        """测试批量获取时部分失败"""
        sources = [
            {"url": "https://example.com/feed1", "name": "Source1", "category": "bitcoin"},
            {"url": "https://example.com/feed2", "name": "Source2", "category": "ethereum"}
        ]
        
        mock_items = [{"title": "Success News", "category": "bitcoin"}]
        
        with patch.object(RSSFetcher, 'fetch_feed') as mock_fetch, \
             patch('builtins.print') as mock_print:
            mock_fetch.side_effect = [mock_items, Exception("Network error")]
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.fetch_multiple_feeds(sources)
            
            assert len(result) == 1
            assert result[0]['title'] == "Success News"
            mock_print.assert_called()

    @pytest.mark.asyncio
    async def test_is_duplicate_new_content(self):
        """测试新内容不重复"""
        with patch('app.core.redis.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.exists.return_value = False
            mock_redis.setex.return_value = None
            mock_get_redis.return_value = mock_redis
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.is_duplicate("test_hash")
            
            assert result is False
            mock_redis.exists.assert_called_with("news:hash:test_hash")
            mock_redis.setex.assert_called_with("news:hash:test_hash", 86400, "1")

    @pytest.mark.asyncio
    async def test_is_duplicate_existing_content(self):
        """测试重复内容检测"""
        with patch('app.core.redis.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.exists.return_value = True
            mock_get_redis.return_value = mock_redis
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.is_duplicate("existing_hash")
            
            assert result is True
            mock_redis.exists.assert_called_with("news:hash:existing_hash")

    @pytest.mark.asyncio
    async def test_fetch_feed_no_published_date(self):
        """测试没有发布日期的feed项目"""
        mock_response_text = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Crypto News</title>
                <item>
                    <title>Bitcoin News</title>
                    <description>Bitcoin content</description>
                    <link>https://example.com/btc</link>
                </item>
            </channel>
        </rss>"""
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_response_text)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with RSSFetcher() as fetcher:
                result = await fetcher.fetch_feed("https://example.com/feed", "TestSource")
            
            assert len(result) == 1
            assert isinstance(result[0]['published_at'], datetime)
            # 应该使用当前时间作为默认值