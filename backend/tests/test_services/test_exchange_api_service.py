"""
Comprehensive tests for Exchange API Service.

Tests cover:
- Exchange API connectors (Binance, Coinbase, OKX)
- Rate limiting functionality
- Price data fetching and analysis
- Market impact analysis
- Error handling and recovery
- API mocking for reliable testing
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import aiohttp
import json

from app.services.exchange_api_service import (
    ExchangeAPIService,
    PriceDataService,
    ExchangeAnnouncement,
    PriceData,
    RateLimiter
)


class TestRateLimiter:
    """Test rate limiter functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limit(self, mock_redis):
        """Test that rate limiter allows requests within the limit"""
        # Mock Redis responses for rate limiting
        mock_redis.zremrangebyscore.return_value = 0
        mock_redis.zcard.return_value = 5  # Current count below limit
        mock_redis.zadd.return_value = 1
        mock_redis.expire.return_value = True
        
        limiter = RateLimiter("test_key", 10, 60)
        
        can_proceed = await limiter.can_proceed()
        assert can_proceed is True
        
        # Verify Redis calls
        mock_redis.zremrangebyscore.assert_called_once()
        mock_redis.zcard.assert_called_once()
        mock_redis.zadd.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_requests_over_limit(self, mock_redis):
        """Test that rate limiter blocks requests when over limit"""
        mock_redis.zremrangebyscore.return_value = 0
        mock_redis.zcard.return_value = 15  # Current count over limit of 10
        
        limiter = RateLimiter("test_key", 10, 60)
        
        can_proceed = await limiter.can_proceed()
        assert can_proceed is False
        
        # Should not add to Redis when blocked
        mock_redis.zadd.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_wait_if_needed(self, mock_redis):
        """Test wait_if_needed method with rate limiting"""
        # First call blocked, second call allowed
        mock_redis.zremrangebyscore.return_value = 0
        mock_redis.zcard.side_effect = [15, 5]  # First over limit, then under
        mock_redis.zadd.return_value = 1
        mock_redis.expire.return_value = True
        
        limiter = RateLimiter("test_key", 10, 60)
        
        with patch('asyncio.sleep') as mock_sleep:
            await limiter.wait_if_needed()
            mock_sleep.assert_called_once_with(10)


class TestExchangeAPIService:
    """Test main exchange API service functionality"""
    
    @pytest.fixture
    async def exchange_service(self):
        """Create exchange service instance for testing"""
        service = ExchangeAPIService()
        service.session = AsyncMock(spec=aiohttp.ClientSession)
        return service
    
    @pytest.mark.asyncio
    async def test_binance_announcements_fetching(self, exchange_service):
        """Test fetching Binance announcements"""
        # Mock successful Binance API response
        mock_response_data = {
            "data": {
                "catalogs": [{
                    "articles": [{
                        "id": "123",
                        "code": "test-announcement",
                        "title": "New BTC Listing",
                        "body": "Bitcoin trading is now available",
                        "releaseDate": int(datetime.now().timestamp() * 1000),
                        "type": {"name": "Trading"}
                    }]
                }]
            }
        }
        
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        exchange_service.session.post.return_value.__aenter__.return_value = mock_response
        
        # Mock rate limiter to allow request
        with patch.object(exchange_service.binance_limiter, 'wait_if_needed'):
            announcements = await exchange_service.fetch_binance_announcements(limit=5)
        
        assert len(announcements) == 1
        assert announcements[0].title == "New BTC Listing"
        assert announcements[0].exchange == "Binance"
        assert announcements[0].url.startswith("https://www.binance.com/en/support/announcement/")
        assert "BTC" in announcements[0].affected_tokens
    
    @pytest.mark.asyncio
    async def test_binance_api_error_handling(self, exchange_service):
        """Test handling of Binance API errors"""
        # Mock HTTP error response
        mock_response = AsyncMock()
        mock_response.status = 500
        
        exchange_service.session.post.return_value.__aenter__.return_value = mock_response
        
        with patch.object(exchange_service.binance_limiter, 'wait_if_needed'):
            announcements = await exchange_service.fetch_binance_announcements()
        
        assert announcements == []  # Should return empty list on error
    
    @pytest.mark.asyncio
    async def test_coinbase_rss_parsing(self, exchange_service):
        """Test Coinbase RSS feed parsing"""
        # Mock RSS content
        rss_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Coinbase Adds Support for Ethereum 2.0 Staking</title>
                    <link>https://blog.coinbase.com/eth2-staking</link>
                    <pubDate>Wed, 01 Jan 2025 12:00:00 GMT</pubDate>
                    <description>Exciting news about ETH staking rewards</description>
                </item>
            </channel>
        </rss>'''
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = rss_content
        
        exchange_service.session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(exchange_service.coinbase_limiter, 'wait_if_needed'):
            announcements = await exchange_service.fetch_coinbase_announcements()
        
        assert len(announcements) == 1
        assert announcements[0].title == "Coinbase Adds Support for Ethereum 2.0 Staking"
        assert announcements[0].exchange == "Coinbase"
        assert "ETH" in announcements[0].affected_tokens
        assert announcements[0].importance_score >= 3  # Should be high for institutional news
    
    @pytest.mark.asyncio
    async def test_okx_api_integration(self, exchange_service):
        """Test OKX API integration"""
        mock_response_data = {
            "data": [{
                "id": "456",
                "title": "OKX Lists ADA/USDT",
                "content": "Cardano trading pairs now available",
                "cTime": str(int(datetime.now().timestamp() * 1000)),
                "annType": "listing"
            }]
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        exchange_service.session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(exchange_service.okx_limiter, 'wait_if_needed'):
            announcements = await exchange_service.fetch_okx_announcements()
        
        assert len(announcements) == 1
        assert announcements[0].title == "OKX Lists ADA/USDT"
        assert announcements[0].exchange == "OKX"
        assert "ADA" in announcements[0].affected_tokens
        assert announcements[0].importance_score >= 4  # Listing should be high importance
    
    @pytest.mark.asyncio
    async def test_fetch_all_exchanges_concurrent(self, exchange_service):
        """Test concurrent fetching from all exchanges"""
        # Mock individual exchange methods
        binance_announcement = ExchangeAnnouncement(
            title="Binance Test",
            content="Test content",
            url="https://binance.com/test",
            exchange="Binance",
            category="Test",
            published_at=datetime.now(),
            importance_score=3,
            affected_tokens=["BTC"]
        )
        
        coinbase_announcement = ExchangeAnnouncement(
            title="Coinbase Test",
            content="Test content",
            url="https://coinbase.com/test",
            exchange="Coinbase",
            category="Test",
            published_at=datetime.now(),
            importance_score=4,
            affected_tokens=["ETH"]
        )
        
        with patch.object(exchange_service, 'fetch_binance_announcements', return_value=[binance_announcement]), \
             patch.object(exchange_service, 'fetch_coinbase_announcements', return_value=[coinbase_announcement]), \
             patch.object(exchange_service, 'fetch_okx_announcements', return_value=[]):
            
            all_announcements = await exchange_service.fetch_all_exchange_announcements()
        
        assert len(all_announcements) == 2
        exchanges = [ann.exchange for ann in all_announcements]
        assert "Binance" in exchanges
        assert "Coinbase" in exchanges
    
    @pytest.mark.asyncio
    async def test_announcement_deduplication(self, exchange_service):
        """Test deduplication of similar announcements"""
        # Create two similar announcements
        announcement1 = ExchangeAnnouncement(
            title="Bitcoin Listing",
            content="Bitcoin is now available",
            url="https://example1.com",
            exchange="Exchange1",
            category="Listing",
            published_at=datetime.now(),
            importance_score=4
        )
        
        announcement2 = ExchangeAnnouncement(
            title="Bitcoin Listing",  # Same title
            content="Bitcoin is now available for trading",
            url="https://example2.com",
            exchange="Exchange1",  # Same exchange
            category="Listing",
            published_at=datetime.now(),
            importance_score=4
        )
        
        announcements = [announcement1, announcement2]
        deduplicated = await exchange_service._deduplicate_announcements(announcements)
        
        assert len(deduplicated) == 1  # Should remove duplicate
    
    def test_importance_calculation_methods(self, exchange_service):
        """Test importance score calculation for different exchanges"""
        # Test Binance importance calculation
        binance_high = exchange_service._calculate_binance_importance("New Listing: BTC/USDT")
        binance_low = exchange_service._calculate_binance_importance("System Maintenance Notice")
        
        assert binance_high >= binance_low
        assert binance_high >= 4  # Listing should be high importance
        
        # Test Coinbase importance calculation
        coinbase_high = exchange_service._calculate_coinbase_importance("SEC Approves Institutional Bitcoin")
        coinbase_medium = exchange_service._calculate_coinbase_importance("New DeFi Feature Launch")
        
        assert coinbase_high >= coinbase_medium
        assert coinbase_high == 5  # SEC news should be maximum importance
        
        # Test OKX importance calculation
        okx_critical = exchange_service._calculate_okx_importance("Trading Halt Notice", "system")
        okx_medium = exchange_service._calculate_okx_importance("New Feature Release", "feature")
        
        assert okx_critical >= okx_medium
        assert okx_critical == 5  # System announcements should be critical
    
    def test_token_extraction(self, exchange_service):
        """Test cryptocurrency token extraction from text"""
        text = "New listing: BTC, ETH, and ADA tokens available for $DOGE trading"
        tokens = exchange_service._extract_tokens_from_text(text)
        
        assert "BTC" in tokens
        assert "ETH" in tokens
        assert "ADA" in tokens
        assert "DOGE" in tokens
        assert "USD" not in tokens  # Should filter out fiat currencies
    
    def test_crypto_content_filtering(self, exchange_service):
        """Test filtering for crypto-related content"""
        crypto_text = "Bitcoin price surges as DeFi adoption increases"
        non_crypto_text = "Company announces quarterly earnings report"
        
        assert exchange_service._is_crypto_related(crypto_text) is True
        assert exchange_service._is_crypto_related(non_crypto_text) is False


class TestPriceDataService:
    """Test price data service functionality"""
    
    @pytest.fixture
    async def price_service(self):
        """Create price service instance for testing"""
        service = PriceDataService()
        service.session = AsyncMock(spec=aiohttp.ClientSession)
        return service
    
    @pytest.mark.asyncio
    async def test_fetch_token_prices(self, price_service):
        """Test fetching token prices from CoinGecko API"""
        mock_response_data = {
            "bitcoin": {
                "usd": 45000.0,
                "usd_24h_change": 5.2,
                "usd_24h_vol": 28000000000
            },
            "ethereum": {
                "usd": 3200.0,
                "usd_24h_change": -2.1,
                "usd_24h_vol": 15000000000
            }
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_response_data
        
        price_service.session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(price_service.rate_limiter, 'wait_if_needed'):
            price_data = await price_service.fetch_token_prices(["bitcoin", "ethereum"])
        
        assert len(price_data) == 2
        
        btc_price = next(p for p in price_data if p.symbol == "BITCOIN")
        assert btc_price.price == 45000.0
        assert btc_price.change_percent_24h == 5.2
        assert btc_price.exchange == "coingecko"
        
        eth_price = next(p for p in price_data if p.symbol == "ETHEREUM")
        assert eth_price.price == 3200.0
        assert eth_price.change_percent_24h == -2.1
    
    @pytest.mark.asyncio
    async def test_market_impact_analysis(self, price_service):
        """Test market impact analysis functionality"""
        # Create test announcement
        announcement = ExchangeAnnouncement(
            title="Binance Lists New DeFi Token",
            content="Exciting new token listing with high trading volume",
            url="https://binance.com/listing",
            exchange="Binance",
            category="Listing",
            published_at=datetime.now(),
            importance_score=5,
            affected_tokens=["NEWTOKEN"]
        )
        
        # Create test price data with high volatility
        price_data = [
            PriceData(
                symbol="NEWTOKEN",
                price=10.0,
                change_24h=2.5,
                change_percent_24h=25.0,  # High volatility
                volume_24h=5000000,
                last_updated=datetime.utcnow(),
                exchange="coingecko"
            )
        ]
        
        impact_analysis = await price_service.analyze_market_impact(announcement, price_data)
        
        assert impact_analysis["affected_token_count"] == 1
        assert "NEWTOKEN" in impact_analysis["high_volatility_tokens"]
        assert impact_analysis["sentiment_indicator"] == "positive"  # Listing should be positive
        assert impact_analysis["recommended_alert_level"] == "critical"  # High importance + high volatility
    
    @pytest.mark.asyncio
    async def test_price_api_error_handling(self, price_service):
        """Test handling of price API errors"""
        mock_response = AsyncMock()
        mock_response.status = 429  # Rate limit error
        
        price_service.session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(price_service.rate_limiter, 'wait_if_needed'):
            price_data = await price_service.fetch_token_prices(["bitcoin"])
        
        assert price_data == []  # Should return empty list on error
    
    def test_sentiment_analysis(self, price_service):
        """Test sentiment analysis for announcements"""
        # Positive sentiment
        positive_announcement = ExchangeAnnouncement(
            title="Partnership with Major Bank",
            content="Exciting partnership announcement",
            url="https://example.com",
            exchange="Test",
            category="News",
            published_at=datetime.now(),
            importance_score=4
        )
        
        positive_sentiment = price_service._determine_sentiment(positive_announcement)
        assert positive_sentiment == "positive"
        
        # Negative sentiment
        negative_announcement = ExchangeAnnouncement(
            title="Trading Halt Due to Technical Issues",
            content="System maintenance halt in progress",
            url="https://example.com",
            exchange="Test",
            category="System",
            published_at=datetime.now(),
            importance_score=4
        )
        
        negative_sentiment = price_service._determine_sentiment(negative_announcement)
        assert negative_sentiment == "negative"
    
    def test_alert_level_calculation(self, price_service):
        """Test alert level calculation based on importance and volatility"""
        # High importance, high volatility -> Critical
        high_announcement = ExchangeAnnouncement(
            title="SEC Investigation Notice",
            content="Regulatory investigation in progress",
            url="https://example.com",
            exchange="Test",
            category="Regulatory",
            published_at=datetime.now(),
            importance_score=5
        )
        
        high_volatility_prices = [
            PriceData(
                symbol="TEST",
                price=100.0,
                change_24h=-25.0,
                change_percent_24h=-25.0,  # High negative volatility
                volume_24h=1000000,
                last_updated=datetime.utcnow(),
                exchange="test"
            )
        ]
        
        alert_level = price_service._calculate_alert_level(high_announcement, high_volatility_prices)
        assert alert_level == "critical"
        
        # Low importance, low volatility -> Low
        low_announcement = ExchangeAnnouncement(
            title="Minor Feature Update",
            content="Small UI improvement",
            url="https://example.com",
            exchange="Test",
            category="Feature",
            published_at=datetime.now(),
            importance_score=2
        )
        
        low_volatility_prices = [
            PriceData(
                symbol="TEST",
                price=100.0,
                change_24h=1.0,
                change_percent_24h=1.0,  # Low volatility
                volume_24h=1000000,
                last_updated=datetime.utcnow(),
                exchange="test"
            )
        ]
        
        alert_level = price_service._calculate_alert_level(low_announcement, low_volatility_prices)
        assert alert_level == "low"


class TestExchangeAPIIntegration:
    """Integration tests for exchange API functionality"""
    
    @pytest.mark.asyncio
    async def test_full_exchange_monitoring_pipeline(self, mock_redis, mock_db_session):
        """Test the complete exchange monitoring pipeline"""
        # This test simulates the full workflow in _monitor_exchange_announcements_async
        
        # Mock the exchange service to return test data
        test_announcement = ExchangeAnnouncement(
            title="Integration Test Announcement",
            content="Testing full pipeline",
            url="https://test.com/announcement",
            exchange="TestExchange",
            category="Test",
            published_at=datetime.now(),
            importance_score=4,
            affected_tokens=["TESTTOKEN"]
        )
        
        with patch('app.services.exchange_api_service.ExchangeAPIService') as mock_exchange_service, \
             patch('app.services.exchange_api_service.PriceDataService') as mock_price_service, \
             patch('app.services.broadcast_service.BroadcastService') as mock_broadcast_service:
            
            # Configure mocks
            mock_exchange_service.return_value.__aenter__.return_value.fetch_all_exchange_announcements.return_value = [test_announcement]
            
            mock_price_data = [
                PriceData(
                    symbol="TESTTOKEN",
                    price=50.0,
                    change_24h=5.0,
                    change_percent_24h=10.0,
                    volume_24h=1000000,
                    last_updated=datetime.utcnow(),
                    exchange="coingecko"
                )
            ]
            mock_price_service.return_value.__aenter__.return_value.fetch_token_prices.return_value = mock_price_data
            mock_price_service.return_value.__aenter__.return_value.analyze_market_impact.return_value = {
                "recommended_alert_level": "high",
                "sentiment_indicator": "positive"
            }
            
            mock_broadcast_service.return_value.process_and_broadcast_news.return_value = {
                "websocket_broadcasts": 1,
                "telegram_notifications": 1,
                "total_processed": 1
            }
            
            # Import and run the monitoring function
            from app.tasks.news_crawler import _monitor_exchange_announcements_async
            
            result = await _monitor_exchange_announcements_async()
            
            # Verify results
            assert "announcements_fetched" in result
            assert "announcements_saved" in result
            assert "price_analyses_performed" in result
            assert result.get("error") is None


@pytest.fixture
async def mock_redis():
    """Mock Redis for testing"""
    from unittest.mock import AsyncMock
    
    mock_redis_instance = AsyncMock()
    
    with patch('app.core.redis.get_redis', return_value=mock_redis_instance):
        yield mock_redis_instance


@pytest.fixture
async def mock_db_session():
    """Mock database session for testing"""
    from unittest.mock import AsyncMock
    
    mock_session = AsyncMock()
    
    async def mock_get_db():
        yield mock_session
    
    with patch('app.core.database.get_db', mock_get_db):
        yield mock_session