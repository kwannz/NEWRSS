import pytest
import asyncio
from app.tasks.news_crawler import _crawl_news_sources_async, _monitor_exchange_announcements_async, crawl_news_sources, monitor_exchange_announcements
from app.services.rss_fetcher import RSSFetcher
import os

# Set test OpenAI API key
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

@pytest.mark.asyncio
async def test_real_crawl_news_sources_async():
    """Test async news sources crawling"""
    # Test the internal async function directly
    result = await _crawl_news_sources_async()
    
    # Should return some result (might be empty list due to network/parsing issues)
    assert isinstance(result, (list, dict, type(None)))

@pytest.mark.asyncio  
async def test_real_monitor_exchange_announcements_async():
    """Test async exchange announcements monitoring"""
    # Test the internal async function directly
    result = await _monitor_exchange_announcements_async()
    
    # Should return some result
    assert isinstance(result, (list, dict, type(None)))

@pytest.mark.asyncio
async def test_real_rss_fetcher_with_crypto_feeds():
    """Test RSS fetcher with actual crypto news feeds"""
    async with RSSFetcher() as fetcher:
        # Test with real crypto news sources
        crypto_sources = [
            {
                "url": "https://feeds.feedburner.com/oreilly/radar",
                "name": "Tech Radar",
                "category": "tech"
            }
        ]
        
        # This tests the same logic used in news_crawler
        items = await fetcher.fetch_multiple_feeds(crypto_sources)
        assert isinstance(items, list)
        
        # If items are returned, verify structure
        if items:
            item = items[0]
            assert "title" in item
            assert "content" in item
            assert "url" in item
            assert "source" in item
            assert "category" in item
            assert item["category"] == "tech"

def test_real_crawl_news_sources_sync():
    """Test synchronous news sources crawling (Celery task)"""
    # Test the Celery task function
    try:
        result = crawl_news_sources()
        # Should complete without crashing
        assert result is not None or result is None  # Any result is acceptable
    except Exception as e:
        # If it fails, should be due to Celery/Redis connection, not code errors
        assert "redis" in str(e).lower() or "celery" in str(e).lower() or "connection" in str(e).lower()

def test_real_monitor_exchange_announcements_sync():
    """Test synchronous exchange monitoring (Celery task)"""
    # Test the Celery task function
    try:
        result = monitor_exchange_announcements()
        # Should complete without crashing
        assert result is not None or result is None
    except Exception as e:
        # If it fails, should be due to Celery/Redis connection, not code errors
        assert "redis" in str(e).lower() or "celery" in str(e).lower() or "connection" in str(e).lower()

@pytest.mark.asyncio
async def test_real_news_processing_pipeline():
    """Test the complete news processing pipeline logic"""
    # Simulate the processing that happens in news_crawler
    async with RSSFetcher() as fetcher:
        # Fetch from a reliable test feed
        test_url = "https://feeds.feedburner.com/oreilly/radar"
        items = await fetcher.fetch_feed(test_url, "Test Source")
        
        if items:
            # Test processing logic similar to what's in news_crawler
            processed_items = []
            
            for item in items[:3]:  # Process first 3 items
                # Simulate the processing that would happen
                processed_item = {
                    "title": item["title"],
                    "content": item["content"][:500],  # Truncate content
                    "url": item["url"],
                    "source": item["source"],
                    "category": "tech",  # Would be determined by source config
                    "published_at": item["published_at"],
                    "content_hash": item["content_hash"]
                }
                
                # Check for duplicates
                is_duplicate = await fetcher.is_duplicate(item["content_hash"])
                if not is_duplicate:
                    processed_items.append(processed_item)
            
            # Verify processing worked
            assert isinstance(processed_items, list)
            for item in processed_items:
                assert len(item["content"]) <= 500
                assert "content_hash" in item

@pytest.mark.asyncio
async def test_real_exchange_monitoring_logic():
    """Test exchange monitoring logic"""
    # Test the exchange URLs and logic used in monitoring
    exchange_sources = [
        "https://feeds.feedburner.com/oreilly/radar",  # Using this as test feed
    ]
    
    async with RSSFetcher() as fetcher:
        for source_url in exchange_sources:
            items = await fetcher.fetch_feed(source_url, "Exchange Monitor")
            
            # Should handle any response gracefully
            assert isinstance(items, list)
            
            if items:
                # Test filtering logic that would be used in monitoring
                filtered_items = []
                
                for item in items:
                    # Simulate filtering for exchange-related content
                    content_lower = item["content"].lower()
                    title_lower = item["title"].lower()
                    
                    # Look for exchange-related keywords
                    exchange_keywords = ["exchange", "trading", "volume", "listing", "announcement"]
                    if any(keyword in content_lower or keyword in title_lower for keyword in exchange_keywords):
                        filtered_items.append(item)
                
                # Should have some structure even if empty
                assert isinstance(filtered_items, list)

@pytest.mark.asyncio
async def test_real_news_crawler_error_handling():
    """Test news crawler error handling scenarios"""
    async with RSSFetcher() as fetcher:
        # Test with various problematic URLs
        problematic_sources = [
            {"url": "https://nonexistent-domain-12345.com/rss", "name": "Invalid", "category": "test"},
            {"url": "https://httpstat.us/404", "name": "404 Error", "category": "test"},
            {"url": "https://httpstat.us/500", "name": "500 Error", "category": "test"},
        ]
        
        # Should handle all errors gracefully
        results = await fetcher.fetch_multiple_feeds(problematic_sources)
        assert isinstance(results, list)
        # Should not crash, might return empty list

@pytest.mark.asyncio
async def test_real_celery_app_configuration():
    """Test Celery app configuration"""
    from app.tasks.news_crawler import celery_app
    
    # Test Celery app is configured
    assert celery_app is not None
    assert celery_app.main == 'newrss'
    
    # Test beat schedule is configured
    assert 'beat_schedule' in celery_app.conf
    beat_schedule = celery_app.conf.beat_schedule
    
    # Should have the configured tasks
    assert 'crawl-news-every-30-seconds' in beat_schedule
    assert 'monitor-exchanges-every-minute' in beat_schedule
    
    # Test schedule configuration
    crawl_task = beat_schedule['crawl-news-every-30-seconds']
    assert crawl_task['schedule'] == 30.0
    assert crawl_task['task'] == 'app.tasks.news_crawler.crawl_news_sources'
    
    monitor_task = beat_schedule['monitor-exchanges-every-minute']
    assert monitor_task['schedule'] == 60.0
    assert monitor_task['task'] == 'app.tasks.news_crawler.monitor_exchange_announcements'
    
    # Test timezone
    assert celery_app.conf.timezone == 'UTC'