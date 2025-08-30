import pytest
import asyncio
from app.services.rss_fetcher import RSSFetcher
from app.services.ai_analyzer import AINewsAnalyzer
from datetime import datetime
import os
import redis.asyncio as redis

# Set test OpenAI API key
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

@pytest.mark.asyncio
async def test_real_rss_fetcher_comprehensive():
    """Comprehensive RSS fetcher testing with real data"""
    async with RSSFetcher() as fetcher:
        # Test session management
        assert fetcher.session is not None
        
        # Test invalid URLs (should return empty list)
        empty_result = await fetcher.fetch_feed("https://invalid-nonexistent-url-12345.com/rss", "Invalid")
        assert empty_result == []
        
        # Test HTTP error responses
        error_result = await fetcher.fetch_feed("https://httpstat.us/404", "404 Error")
        assert error_result == []
        
        # Test timeout handling (this URL delays response)
        timeout_result = await fetcher.fetch_feed("https://httpstat.us/200?sleep=16000", "Timeout Test")
        assert isinstance(timeout_result, list)
        
        # Test successful RSS fetch with real feed
        real_items = await fetcher.fetch_feed("https://feeds.feedburner.com/oreilly/radar", "O'Reilly")
        assert isinstance(real_items, list)
        
        if real_items:
            item = real_items[0]
            # Verify all required fields are present
            required_fields = ['title', 'content', 'url', 'source', 'published_at', 'content_hash', 'raw_entry']
            for field in required_fields:
                assert field in item
            
            # Verify content hash is generated
            assert len(item['content_hash']) == 32  # MD5 hash length
            assert item['source'] == "O'Reilly"
        
        # Test multiple feeds functionality
        sources = [
            {"url": "https://feeds.feedburner.com/oreilly/radar", "name": "O'Reilly", "category": "tech"},
            {"url": "https://httpstat.us/404", "name": "Error Source", "category": "error"}
        ]
        
        multi_items = await fetcher.fetch_multiple_feeds(sources)
        assert isinstance(multi_items, list)
        
        # Should contain category info for successful fetches
        if multi_items:
            assert all("category" in item for item in multi_items)
            tech_items = [item for item in multi_items if item.get("category") == "tech"]
            assert len(tech_items) > 0

@pytest.mark.asyncio
async def test_real_rss_fetcher_duplicate_detection():
    """Test RSS fetcher duplicate detection with real Redis"""
    redis_client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
    
    try:
        # Clear any existing data
        await redis_client.flushdb()
        
        async with RSSFetcher() as fetcher:
            # Test first time (should not be duplicate)
            test_hash1 = "real_test_hash_001"
            is_dup1 = await fetcher.is_duplicate(test_hash1)
            assert is_dup1 is False
            
            # Test second time (should be duplicate)
            is_dup2 = await fetcher.is_duplicate(test_hash1)
            assert is_dup2 is True
            
            # Test different hash (should not be duplicate)
            test_hash2 = "real_test_hash_002" 
            is_dup3 = await fetcher.is_duplicate(test_hash2)
            assert is_dup3 is False
            
            # Verify Redis cache was set correctly
            exists1 = await redis_client.exists(f"news:hash:{test_hash1}")
            exists2 = await redis_client.exists(f"news:hash:{test_hash2}")
            assert exists1 == 1
            assert exists2 == 1
            
    finally:
        await redis_client.flushdb()
        await redis_client.aclose()

@pytest.mark.asyncio
async def test_real_ai_analyzer_market_impact():
    """Test AI analyzer market impact calculation with real scenarios"""
    analyzer = AINewsAnalyzer()
    
    # Test high impact scenarios
    high_impact_cases = [
        {
            "content": "SEC sues major cryptocurrency exchange for securities violations",
            "title": "SEC Lawsuit",
            "source": "SEC",
            "expected_min": 4
        },
        {
            "content": "Federal Reserve announces ban on cryptocurrency trading by banks",
            "title": "Fed Ban",
            "source": "Federal Reserve",
            "expected_min": 5
        },
        {
            "content": "Major exchange hacked, $100M in Bitcoin stolen",
            "title": "Exchange Hack",
            "source": "CoinDesk",
            "expected_min": 4
        }
    ]
    
    for case in high_impact_cases:
        impact = await analyzer.calculate_market_impact(case)
        assert impact >= case["expected_min"], f"Expected {case['expected_min']}+, got {impact} for {case['title']}"
    
    # Test medium impact scenarios
    medium_impact_cases = [
        {
            "content": "Binance announces new partnership with major bank",
            "title": "Partnership",
            "source": "Binance",
            "expected_range": (2, 4)
        },
        {
            "content": "New cryptocurrency exchange launches with advanced features",
            "title": "Exchange Launch",
            "source": "TechCrunch",
            "expected_range": (1, 3)
        }
    ]
    
    for case in medium_impact_cases:
        impact = await analyzer.calculate_market_impact(case)
        min_exp, max_exp = case["expected_range"]
        assert min_exp <= impact <= max_exp, f"Expected {min_exp}-{max_exp}, got {impact} for {case['title']}"
    
    # Test low impact scenarios
    low_impact_case = {
        "content": "Bitcoin price remains stable at current levels",
        "title": "Price Stable",
        "source": "Random Blog",
    }
    
    impact = await analyzer.calculate_market_impact(low_impact_case)
    assert 1 <= impact <= 3

@pytest.mark.asyncio
async def test_real_ai_analyzer_key_extraction():
    """Test AI analyzer key information extraction with comprehensive cases"""
    analyzer = AINewsAnalyzer()
    
    # Test comprehensive content with all types of information
    comprehensive_content = """
    Breaking: Bitcoin (BTC) surges to $95,000 while Ethereum (ETH) hits $4,200.
    Major exchanges Binance, Coinbase, and Kraken report record volumes.
    Polygon (MATIC) and Chainlink (LINK) also show gains.
    Trading at 1,500 USD and 25.50 USD respectively.
    The Federal Reserve and SEC are monitoring the situation.
    Elon Musk and Michael Saylor commented on the developments.
    """
    
    key_info = await analyzer.extract_key_information(comprehensive_content)
    
    # Verify token extraction
    expected_tokens = ["BTC", "ETH", "MATIC", "LINK"]
    for token in expected_tokens:
        assert token in key_info["tokens"], f"Missing token: {token}"
    
    # Verify price extraction
    expected_prices = ["95,000", "4,200", "1,500", "25.50"]
    extracted_prices = " ".join(key_info["prices"])
    for price in expected_prices:
        assert price in extracted_prices, f"Missing price: {price}"
    
    # Verify exchange extraction
    expected_exchanges = ["Binance", "Coinbase", "Kraken"]
    for exchange in expected_exchanges:
        assert exchange in key_info["exchanges"], f"Missing exchange: {exchange}"
    
    # Test edge cases
    edge_cases = [
        # No crypto content
        "The weather is nice today",
        # Only numbers (no prices)
        "The number 12345 and 67890 are not prices",
        # Mixed content
        "SEC approval of BTC ETF leads to $100,000 target price on Coinbase",
        # Empty content
        "",
        # Special characters
        "BTC/USD trading pair on Binance shows $50,000.50 resistance"
    ]
    
    for content in edge_cases:
        key_info = await analyzer.extract_key_information(content)
        assert isinstance(key_info, dict)
        # Verify all expected keys exist
        expected_keys = ["tokens", "prices", "dates", "exchanges", "people"]
        for key in expected_keys:
            assert key in key_info
            assert isinstance(key_info[key], list)

@pytest.mark.asyncio
async def test_real_ai_analyzer_sentiment_without_api():
    """Test AI analyzer sentiment analysis without real API"""
    analyzer = AINewsAnalyzer()
    
    # Remove API key to test error handling
    original_key = os.environ.get("OPENAI_API_KEY")
    if original_key:
        os.environ.pop("OPENAI_API_KEY", None)
    
    try:
        # Test sentiment analysis without API key
        sentiment = await analyzer.analyze_sentiment("Bitcoin price increases")
        assert sentiment == 0.0
        
        # Test summary generation without API key
        summary = await analyzer.generate_summary("Bitcoin reaches new highs")
        assert summary == "未配置 OpenAI API Key"
        
        # Test full analysis without API key
        news_item = {
            "content": "Bitcoin price surges to new all-time high",
            "title": "Bitcoin ATH",
            "source": "CoinDesk"
        }
        
        analysis = await analyzer.analyze_news(news_item)
        assert isinstance(analysis, dict)
        assert "summary" in analysis
        assert "sentiment" in analysis 
        assert "key_info" in analysis
        assert "market_impact" in analysis
        
        # Summary should show error message
        assert analysis["summary"] == "摘要生成失败"
        # Sentiment should be 0.0 (neutral)
        assert analysis["sentiment"] == 0.0
        # Market impact should still work
        assert isinstance(analysis["market_impact"], int)
        assert 1 <= analysis["market_impact"] <= 5
        
    finally:
        # Restore API key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

@pytest.mark.asyncio
async def test_real_rss_fetcher_session_management():
    """Test RSS fetcher session management"""
    # Test context manager lifecycle
    fetcher = RSSFetcher()
    assert fetcher.session is None
    
    # Test entering context
    async with fetcher as f:
        assert f.session is not None
        assert f is fetcher
        
        # Test session is working
        async with f.session.get("https://httpstat.us/200") as response:
            assert response.status == 200
    
    # After context exit, session should be None
    assert fetcher.session is None or fetcher.session.closed

@pytest.mark.asyncio
async def test_real_rss_feedparser_edge_cases():
    """Test RSS feed parsing edge cases"""
    async with RSSFetcher() as fetcher:
        # Test with RSS feed that might have parsing issues (bozo flag)
        items = await fetcher.fetch_feed("https://httpstat.us/200", "Plain Text Response")
        assert isinstance(items, list)
        # Should handle non-RSS content gracefully
        
        # Test feed with empty entries
        items = await fetcher.fetch_feed("https://feeds.feedburner.com/oreilly/radar", "Real Feed")
        if items:
            # Test published_at parsing
            for item in items[:3]:  # Test first 3 items
                assert "published_at" in item
                assert isinstance(item["published_at"], datetime)
                
                # Test content hash generation
                assert "content_hash" in item
                assert len(item["content_hash"]) == 32
                
                # Test raw_entry preservation
                assert "raw_entry" in item
                assert item["raw_entry"] is not None

@pytest.mark.asyncio
async def test_real_ai_analyzer_error_handling():
    """Test AI analyzer error handling scenarios"""
    analyzer = AINewsAnalyzer()
    
    # Test with various content types
    test_contents = [
        "",  # Empty
        "a" * 10000,  # Very long
        "123!@#$%^&*()",  # Special characters
        "非常长的中文内容测试" * 100,  # Chinese characters
        None,  # This should be handled gracefully
    ]
    
    for i, content in enumerate(test_contents):
        if content is None:
            continue
            
        try:
            # Test key extraction
            key_info = await analyzer.extract_key_information(content)
            assert isinstance(key_info, dict)
            
            # Test market impact
            news_item = {
                "content": content,
                "title": f"Test {i}",
                "source": "Test Source"
            }
            impact = await analyzer.calculate_market_impact(news_item)
            assert 1 <= impact <= 5
            
        except Exception as e:
            pytest.fail(f"Unexpected error with content {i}: {e}")

@pytest.mark.asyncio
async def test_real_combined_services_workflow():
    """Test combined services workflow with real data"""
    # Test complete workflow: RSS fetch -> AI analysis -> Redis caching
    redis_client = redis.from_url("redis://localhost:6379/1", decode_responses=True)
    
    try:
        await redis_client.flushdb()
        
        async with RSSFetcher() as fetcher:
            # Fetch real RSS data
            items = await fetcher.fetch_feed("https://feeds.feedburner.com/oreilly/radar", "Tech News")
            
            if items:
                analyzer = AINewsAnalyzer()
                
                # Process first item through complete pipeline
                item = items[0]
                
                # 1. Check if duplicate (should be false first time)
                is_duplicate_before = await fetcher.is_duplicate(item["content_hash"])
                assert is_duplicate_before is False
                
                # 2. Analyze with AI
                key_info = await analyzer.extract_key_information(item["content"])
                market_impact = await analyzer.calculate_market_impact(item)
                
                # 3. Cache results in Redis
                cache_key = f"analysis:{item['content_hash']}"
                analysis_data = {
                    "key_info": str(key_info),
                    "market_impact": market_impact,
                    "processed_at": datetime.now().isoformat()
                }
                
                for key, value in analysis_data.items():
                    await redis_client.hset(cache_key, key, str(value))
                
                # 4. Verify caching worked
                cached_impact = await redis_client.hget(cache_key, "market_impact")
                assert int(cached_impact) == market_impact
                
                # 5. Check duplicate again (should be true now)
                is_duplicate_after = await fetcher.is_duplicate(item["content_hash"])
                assert is_duplicate_after is True
                
    finally:
        await redis_client.flushdb()
        await redis_client.aclose()

@pytest.mark.asyncio
async def test_real_rss_fetcher_content_processing():
    """Test RSS fetcher content processing details"""
    async with RSSFetcher() as fetcher:
        # Fetch real feed to test processing
        items = await fetcher.fetch_feed("https://feeds.feedburner.com/oreilly/radar", "O'Reilly")
        
        if items:
            item = items[0]
            
            # Test content hash generation logic
            import hashlib
            expected_hash = hashlib.md5(
                f"{item.get('title', '')}{item.get('url', '')}".encode()
            ).hexdigest()
            
            # The hash in the item should match our calculation
            # Note: This tests the actual hash generation logic
            raw_entry = item["raw_entry"]
            actual_title = raw_entry.get('title', '')
            actual_link = raw_entry.get('link', '')
            recalc_hash = hashlib.md5(f"{actual_title}{actual_link}".encode()).hexdigest()
            
            assert item["content_hash"] == recalc_hash
            
            # Test content extraction logic
            # Should prefer summary over description
            if hasattr(raw_entry, 'summary') and raw_entry.summary:
                assert item["content"] == raw_entry.summary
            elif hasattr(raw_entry, 'description') and raw_entry.description:
                assert item["content"] == raw_entry.description
            
            # Test source assignment
            assert item["source"] == "O'Reilly"
            
            # Test published_at handling
            assert isinstance(item["published_at"], datetime)

@pytest.mark.asyncio
async def test_real_ai_analyzer_token_filtering():
    """Test AI analyzer token filtering logic"""
    analyzer = AINewsAnalyzer()
    
    # Test content with excluded words mixed with real tokens
    test_content = "The SEC CEO announced that BTC and ETH are not securities. The USA CFO disagrees with the API FAQ regarding ATH and ATL prices."
    
    key_info = await analyzer.extract_key_information(test_content)
    
    # Should extract real tokens
    assert "BTC" in key_info["tokens"]
    assert "ETH" in key_info["tokens"]
    
    # Should exclude common non-token words
    excluded_words = {'SEC', 'CEO', 'CTO', 'CFO', 'USA', 'USD', 'API', 'FAQ', 'ATH', 'ATL'}
    for excluded in excluded_words:
        assert excluded not in key_info["tokens"], f"Should not include excluded word: {excluded}"

@pytest.mark.asyncio
async def test_real_ai_analyzer_price_patterns():
    """Test AI analyzer price pattern extraction"""
    analyzer = AINewsAnalyzer()
    
    # Test various price formats
    price_test_content = """
    Bitcoin trades at $50,000.50 while Ethereum is 3,500 USD.
    Other prices include 25000美元 and various amounts like $1,000,000.
    Small amounts: $5.99, $10, $0.50 are also valid.
    """
    
    key_info = await analyzer.extract_key_information(price_test_content)
    
    # Should extract various price formats
    prices_str = " ".join(key_info["prices"])
    
    expected_prices = ["50,000.50", "3,500", "25000", "1,000,000", "5.99"]
    for price in expected_prices:
        assert price in prices_str, f"Missing price pattern: {price}"

@pytest.mark.asyncio
async def test_real_ai_analyzer_exchange_detection():
    """Test AI analyzer exchange detection"""
    analyzer = AINewsAnalyzer()
    
    # Test content with various exchange mentions
    exchange_content = "Major exchanges including binance, COINBASE, okx, and Kraken reported issues. FTX and bitfinex were also affected. Gate.io and KuCoin remain stable."
    
    key_info = await analyzer.extract_key_information(exchange_content)
    
    # Should detect exchanges regardless of case
    expected_exchanges = ["Binance", "Coinbase", "OKX", "Kraken", "Bitfinex", "Gate.io", "KuCoin"]
    for exchange in expected_exchanges:
        assert exchange in key_info["exchanges"], f"Missing exchange: {exchange}"
    
    # Test deduplication
    duplicate_content = "Binance Binance BINANCE binance reports on Coinbase and coinbase trading"
    key_info_dup = await analyzer.extract_key_information(duplicate_content)
    
    # Should have unique exchanges only
    assert key_info_dup["exchanges"].count("Binance") == 1
    assert key_info_dup["exchanges"].count("Coinbase") == 1