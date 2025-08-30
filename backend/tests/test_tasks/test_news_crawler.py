import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tasks.news_crawler import (
    _crawl_news_sources_async,
    is_urgent_news,
    calculate_importance,
    crawl_news_sources,
    _monitor_exchange_announcements_async,
    monitor_exchange_announcements
)

class TestNewsCrawler:
    
    @pytest.mark.asyncio
    async def test_crawl_news_sources_async_success(self):
        """测试异步新闻抓取成功"""
        mock_items = [
            {
                'title': 'Bitcoin News',
                'content': 'Bitcoin content',
                'content_hash': 'hash1',
                'source': 'CoinDesk'
            },
            {
                'title': 'Ethereum News',
                'content': 'Ethereum content',
                'content_hash': 'hash2',
                'source': 'Decrypt'
            }
        ]
        
        with patch('app.tasks.news_crawler.RSSFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_multiple_feeds.return_value = mock_items
            mock_fetcher.is_duplicate.side_effect = [False, False]  # 都不重复
            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher
            
            with patch('builtins.print') as mock_print:
                result = await _crawl_news_sources_async()
            
            assert len(result) == 2
            assert result[0]['title'] == 'Bitcoin News'
            assert result[1]['title'] == 'Ethereum News'
            mock_print.assert_called_with("Processed 2 new items")

    @pytest.mark.asyncio
    async def test_crawl_news_sources_async_with_duplicates(self):
        """测试异步新闻抓取包含重复项"""
        mock_items = [
            {
                'title': 'Bitcoin News',
                'content': 'Bitcoin content',
                'content_hash': 'hash1',
                'source': 'CoinDesk'
            },
            {
                'title': 'Duplicate News',
                'content': 'Duplicate content',
                'content_hash': 'hash2',
                'source': 'Decrypt'
            }
        ]
        
        with patch('app.tasks.news_crawler.RSSFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_multiple_feeds.return_value = mock_items
            mock_fetcher.is_duplicate.side_effect = [False, True]  # 第二个重复
            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher
            
            with patch('builtins.print') as mock_print:
                result = await _crawl_news_sources_async()
            
            assert len(result) == 1
            assert result[0]['title'] == 'Bitcoin News'
            mock_print.assert_called_with("Processed 1 new items")

    def test_is_urgent_news_true(self):
        """测试紧急新闻检测 - 正面案例"""
        urgent_items = [
            {
                'title': 'BREAKING: Bitcoin crashes below $30k',
                'content': 'Market in panic'
            },
            {
                'title': 'SEC announces new regulation',
                'content': 'Urgent regulatory update'
            },
            {
                'title': '突发：交易所被黑客攻击',
                'content': '紧急情况通报'
            }
        ]
        
        for item in urgent_items:
            assert is_urgent_news(item) is True

    def test_is_urgent_news_false(self):
        """测试紧急新闻检测 - 负面案例"""
        normal_items = [
            {
                'title': 'Daily market update',
                'content': 'Regular trading volume'
            },
            {
                'title': 'New feature announcement',
                'content': 'Platform improvement'
            }
        ]
        
        for item in normal_items:
            assert is_urgent_news(item) is False

    def test_calculate_importance_high_score(self):
        """测试高重要性评分"""
        high_importance_item = {
            'title': 'SEC approves Bitcoin ETF regulation',
            'content': 'Federal Reserve announces new regulatory framework',
            'source': 'sec.gov'
        }
        
        score = calculate_importance(high_importance_item)
        assert score >= 4  # 高权威来源 + 高影响关键词

    def test_calculate_importance_medium_score(self):
        """测试中等重要性评分"""
        medium_importance_item = {
            'title': 'New partnership announcement',
            'content': 'Company launches new crypto adoption program',
            'source': 'CryptoNews'
        }
        
        score = calculate_importance(medium_importance_item)
        assert 2 <= score <= 3

    def test_calculate_importance_low_score(self):
        """测试低重要性评分"""
        low_importance_item = {
            'title': 'General market update',
            'content': 'Daily trading summary',
            'source': 'Blog'
        }
        
        score = calculate_importance(low_importance_item)
        assert score == 1

    def test_calculate_importance_max_cap(self):
        """测试重要性评分最大值限制"""
        max_score_item = {
            'title': 'SEC regulation ETF approval ban listing',
            'content': 'Federal Reserve regulation ETF approval',
            'source': 'sec federal reserve coinbase binance'
        }
        
        score = calculate_importance(max_score_item)
        assert score == 5  # 不应超过5

    def test_crawl_news_sources_sync_task_success(self):
        """测试Celery同步任务包装成功"""
        with patch('app.tasks.news_crawler._crawl_news_sources_async') as mock_async:
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = None
                
                crawl_news_sources()
                
                mock_run.assert_called_once_with(mock_async.return_value)

    def test_crawl_news_sources_sync_task_error(self):
        """测试Celery同步任务异常处理"""
        with patch('asyncio.run', side_effect=Exception("Async error")), \
             patch('builtins.print') as mock_print:
            
            crawl_news_sources()
            
            mock_print.assert_called_with("Error in crawl_news_sources: Async error")

    @pytest.mark.asyncio
    async def test_monitor_exchange_announcements_async(self):
        """测试异步监控交易所公告"""
        with patch('builtins.print') as mock_print:
            await _monitor_exchange_announcements_async()
        
        mock_print.assert_called_with("Monitoring exchange announcements...")

    def test_monitor_exchange_announcements_sync_task(self):
        """测试监控交易所公告同步任务包装"""
        with patch('app.tasks.news_crawler._monitor_exchange_announcements_async') as mock_async:
            with patch('asyncio.run') as mock_run:
                
                monitor_exchange_announcements()
                
                mock_run.assert_called_once_with(mock_async.return_value)

    def test_monitor_exchange_announcements_sync_task_error(self):
        """测试监控交易所公告异常处理"""
        with patch('asyncio.run', side_effect=Exception("Monitor error")), \
             patch('builtins.print') as mock_print:
            
            monitor_exchange_announcements()
            
            mock_print.assert_called_with("Error in monitor_exchange_announcements: Monitor error")

    @pytest.mark.asyncio
    async def test_crawl_news_sources_async_empty_result(self):
        """测试异步新闻抓取空结果"""
        with patch('app.tasks.news_crawler.RSSFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_multiple_feeds.return_value = []
            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher
            
            with patch('builtins.print') as mock_print:
                result = await _crawl_news_sources_async()
            
            assert result == []
            mock_print.assert_called_with("Processed 0 new items")

    @pytest.mark.asyncio
    async def test_crawl_news_sources_async_with_processing(self):
        """测试异步新闻抓取包含处理逻辑"""
        mock_items = [
            {
                'title': 'BREAKING Bitcoin hack',
                'content': 'Urgent hack news',
                'content_hash': 'hash1',
                'source': 'CoinDesk'
            }
        ]
        
        with patch('app.tasks.news_crawler.RSSFetcher') as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.fetch_multiple_feeds.return_value = mock_items
            mock_fetcher.is_duplicate.return_value = False
            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher
            
            result = await _crawl_news_sources_async()
            
            assert len(result) == 1
            assert result[0]['is_urgent'] is True  # 因为包含'breaking'和'hack'
            assert result[0]['importance_score'] >= 2  # 应该有较高重要性评分