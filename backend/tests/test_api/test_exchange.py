"""
Tests for Exchange API endpoints.

Tests cover:
- Exchange announcements retrieval and filtering
- Price data endpoints
- Market impact analysis endpoints
- Price alerts management
- API error handling and validation
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
import json

from app.main import app
from app.models.exchange import (
    ExchangeAnnouncement,
    PriceData,
    MarketImpactAnalysis,
    PriceAlert
)


client = TestClient(app)


class TestExchangeAnnouncementsAPI:
    """Test exchange announcements API endpoints"""
    
    @pytest.fixture
    def sample_announcements(self):
        """Create sample exchange announcements for testing"""
        return [
            ExchangeAnnouncement(
                id=1,
                title="Binance Lists New Token",
                content="Exciting new token listing announcement",
                url="https://binance.com/announcement/1",
                exchange="Binance",
                category="Listing",
                published_at=datetime.utcnow() - timedelta(hours=1),
                importance_score=5,
                announcement_type="exchange_announcement",
                affected_tokens=["NEWTOKEN"],
                market_impact_level="high",
                sentiment_indicator="positive",
                created_at=datetime.utcnow()
            ),
            ExchangeAnnouncement(
                id=2,
                title="Coinbase System Maintenance",
                content="Scheduled maintenance announcement",
                url="https://coinbase.com/announcement/2",
                exchange="Coinbase",
                category="System",
                published_at=datetime.utcnow() - timedelta(hours=2),
                importance_score=3,
                announcement_type="system_announcement",
                affected_tokens=None,
                market_impact_level="low",
                sentiment_indicator="neutral",
                created_at=datetime.utcnow()
            )
        ]
    
    def test_get_announcements_success(self, sample_announcements):
        """Test successful retrieval of exchange announcements"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = sample_announcements
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/announcements")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["title"] == "Binance Lists New Token"
            assert data[0]["exchange"] == "Binance"
            assert data[0]["importance_score"] == 5
    
    def test_get_announcements_with_filters(self, sample_announcements):
        """Test announcements retrieval with query filters"""
        # Filter for Binance only
        binance_announcement = [sample_announcements[0]]  # Only Binance announcement
        
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = binance_announcement
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/announcements?exchange=Binance&importance_min=4")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["exchange"] == "Binance"
            assert data[0]["importance_score"] >= 4
    
    def test_get_announcements_pagination(self, sample_announcements):
        """Test announcements pagination"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = sample_announcements[:1]  # Only first announcement
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/announcements?limit=1&offset=0")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
    
    def test_get_single_announcement_success(self, sample_announcements):
        """Test retrieval of single announcement by ID"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = sample_announcements[0]
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/announcements/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["title"] == "Binance Lists New Token"
    
    def test_get_single_announcement_not_found(self):
        """Test 404 response for non-existent announcement"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/announcements/999")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_refresh_announcements_success(self):
        """Test manual refresh of exchange announcements"""
        mock_result = {
            "announcements_fetched": 5,
            "announcements_saved": 3,
            "price_analyses_performed": 2,
            "high_importance_broadcasted": 1
        }
        
        with patch('app.tasks.news_crawler._monitor_exchange_announcements_async', return_value=mock_result):
            response = client.post("/api/v1/exchange/announcements/refresh")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["announcements_fetched"] == 5
            assert data["data"]["announcements_saved"] == 3


class TestPriceDataAPI:
    """Test price data API endpoints"""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing"""
        return [
            PriceData(
                id=1,
                symbol="BTC",
                price_usd=45000.0,
                change_24h=2250.0,
                change_percent_24h=5.0,
                volume_24h=28000000000,
                exchange="coingecko",
                data_source="api",
                price_timestamp=datetime.utcnow(),
                created_at=datetime.utcnow()
            ),
            PriceData(
                id=2,
                symbol="ETH",
                price_usd=3200.0,
                change_24h=-64.0,
                change_percent_24h=-2.0,
                volume_24h=15000000000,
                exchange="coingecko",
                data_source="api",
                price_timestamp=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
        ]
    
    def test_get_price_data_success(self, sample_price_data):
        """Test successful retrieval of price data"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = sample_price_data
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/prices")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["symbol"] == "BTC"
            assert data[0]["price_usd"] == 45000.0
            assert data[1]["symbol"] == "ETH"
    
    def test_get_price_data_with_symbol_filter(self, sample_price_data):
        """Test price data retrieval with symbol filtering"""
        btc_only = [sample_price_data[0]]  # Only BTC
        
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = btc_only
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/prices?symbols=BTC")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["symbol"] == "BTC"
    
    def test_refresh_price_data_success(self):
        """Test manual price data refresh"""
        mock_price_data = [
            {
                "symbol": "BTC",
                "price": 45000.0,
                "change_24h": 2250.0,
                "change_percent_24h": 5.0,
                "volume_24h": 28000000000,
                "last_updated": datetime.utcnow(),
                "exchange": "coingecko"
            }
        ]
        
        with patch('app.services.exchange_api_service.PriceDataService') as mock_price_service, \
             patch('app.core.database.get_db') as mock_get_db:
            
            mock_price_service.return_value.__aenter__.return_value.fetch_token_prices.return_value = mock_price_data
            
            mock_session = AsyncMock()
            mock_session.add.return_value = None
            mock_session.commit.return_value = None
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.post("/api/v1/exchange/prices/refresh", 
                                 json={"symbols": ["bitcoin"]})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["saved_count"] >= 0


class TestMarketImpactAPI:
    """Test market impact analysis API endpoints"""
    
    @pytest.fixture
    def sample_market_analyses(self):
        """Create sample market impact analyses for testing"""
        return [
            MarketImpactAnalysis(
                id=1,
                impact_score=0.8,
                confidence_level=0.9,
                affected_token_count=2,
                high_volatility_tokens=["BTC", "ETH"],
                recommended_alert_level="high",
                sentiment_score=0.7,
                analyzed_at=datetime.utcnow()
            ),
            MarketImpactAnalysis(
                id=2,
                impact_score=0.3,
                confidence_level=0.6,
                affected_token_count=1,
                high_volatility_tokens=["ADA"],
                recommended_alert_level="medium",
                sentiment_score=0.1,
                analyzed_at=datetime.utcnow()
            )
        ]
    
    def test_get_market_impact_analyses_success(self, sample_market_analyses):
        """Test successful retrieval of market impact analyses"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = sample_market_analyses
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/market-impact")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["impact_score"] == 0.8
            assert data[0]["recommended_alert_level"] == "high"
    
    def test_get_market_impact_with_alert_filter(self, sample_market_analyses):
        """Test market impact analyses with alert level filtering"""
        high_impact_only = [sample_market_analyses[0]]  # Only high alert level
        
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = high_impact_only
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/market-impact?alert_level=high")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["recommended_alert_level"] == "high"


class TestPriceAlertsAPI:
    """Test price alerts management API endpoints"""
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing"""
        from app.models.user import User
        return User(
            id=1,
            username="testuser",
            email="test@example.com",
            telegram_id=12345,
            is_active=True,
            created_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_price_alerts(self):
        """Create sample price alerts for testing"""
        return [
            PriceAlert(
                id=1,
                user_id=1,
                token_symbol="BTC",
                alert_type="price_above",
                threshold_value=50000.0,
                is_active=True,
                notification_method="telegram",
                trigger_count=0,
                created_at=datetime.utcnow()
            ),
            PriceAlert(
                id=2,
                user_id=1,
                token_symbol="ETH",
                alert_type="price_below",
                threshold_value=3000.0,
                is_active=True,
                notification_method="websocket",
                trigger_count=2,
                last_triggered=datetime.utcnow() - timedelta(hours=1),
                created_at=datetime.utcnow()
            )
        ]
    
    def test_create_price_alert_success(self, sample_user):
        """Test successful creation of price alert"""
        alert_data = {
            "token_symbol": "BTC",
            "alert_type": "price_above",
            "threshold_value": 50000.0,
            "notification_method": "telegram"
        }
        
        new_alert = PriceAlert(
            id=1,
            user_id=1,
            **alert_data,
            is_active=True,
            trigger_count=0,
            created_at=datetime.utcnow()
        )
        
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            
            # Mock user lookup
            mock_user_result = AsyncMock()
            mock_user_result.scalar_one_or_none.return_value = sample_user
            
            # Mock alert creation
            mock_session.execute.return_value = mock_user_result
            mock_session.add.return_value = None
            mock_session.commit.return_value = None
            mock_session.refresh.return_value = None
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.post(
                "/api/v1/exchange/price-alerts?user_id=1",
                json=alert_data
            )
            
            assert response.status_code == 200
            # Note: In a real test, you'd mock the response more carefully
            # This is a simplified version for demonstration
    
    def test_create_price_alert_user_not_found(self):
        """Test price alert creation with non-existent user"""
        alert_data = {
            "token_symbol": "BTC",
            "alert_type": "price_above",
            "threshold_value": 50000.0,
            "notification_method": "telegram"
        }
        
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None  # User not found
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.post(
                "/api/v1/exchange/price-alerts?user_id=999",
                json=alert_data
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_get_user_price_alerts_success(self, sample_price_alerts):
        """Test successful retrieval of user price alerts"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = sample_price_alerts
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/price-alerts?user_id=1")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["token_symbol"] == "BTC"
            assert data[1]["token_symbol"] == "ETH"
    
    def test_delete_price_alert_success(self, sample_price_alerts):
        """Test successful deletion of price alert"""
        alert_to_delete = sample_price_alerts[0]
        
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = alert_to_delete
            mock_session.execute.return_value = mock_result
            mock_session.delete.return_value = None
            mock_session.commit.return_value = None
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.delete("/api/v1/exchange/price-alerts/1?user_id=1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "deleted" in data["message"].lower()
    
    def test_delete_price_alert_not_found(self):
        """Test deletion of non-existent price alert"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None  # Alert not found
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.delete("/api/v1/exchange/price-alerts/999?user_id=1")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestExchangeStatsAPI:
    """Test exchange statistics API endpoints"""
    
    def test_get_stats_summary_success(self):
        """Test successful retrieval of exchange statistics summary"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            
            # Mock all the count queries
            mock_announcements_result = AsyncMock()
            mock_announcements_result.scalar.return_value = 25
            
            mock_price_result = AsyncMock()
            mock_price_result.scalar.return_value = 150
            
            mock_analyses_result = AsyncMock()
            mock_analyses_result.scalar.return_value = 10
            
            mock_alerts_result = AsyncMock()
            mock_alerts_result.scalar.return_value = 5
            
            mock_high_importance_result = AsyncMock()
            mock_high_importance_result.scalar.return_value = 8
            
            # Set up the mock session to return different results for different queries
            mock_session.execute.side_effect = [
                mock_announcements_result,
                mock_price_result,
                mock_analyses_result,
                mock_alerts_result,
                mock_high_importance_result
            ]
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/stats/summary?days=7")
            
            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 7
            assert data["announcements_total"] == 25
            assert data["announcements_high_importance"] == 8
            assert data["price_data_points"] == 150
            assert data["market_analyses"] == 10
            assert data["active_price_alerts"] == 5
            assert "generated_at" in data
    
    def test_get_stats_summary_custom_period(self):
        """Test statistics summary with custom time period"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_session = AsyncMock()
            
            # Mock count queries for 30-day period
            mock_result = AsyncMock()
            mock_result.scalar.return_value = 100
            mock_session.execute.return_value = mock_result
            
            async def mock_db_generator():
                yield mock_session
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/stats/summary?days=30")
            
            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 30


class TestExchangeAPIErrorHandling:
    """Test error handling in exchange API endpoints"""
    
    def test_database_error_handling(self):
        """Test handling of database errors"""
        with patch('app.core.database.get_db') as mock_get_db:
            async def mock_db_generator():
                raise Exception("Database connection failed")
                yield  # This won't be reached, but keeps the generator structure
            
            mock_get_db.return_value = mock_db_generator()
            
            response = client.get("/api/v1/exchange/announcements")
            
            assert response.status_code == 500
            assert "Failed to retrieve" in response.json()["detail"]
    
    def test_invalid_query_parameters(self):
        """Test handling of invalid query parameters"""
        # Test invalid importance_min value
        response = client.get("/api/v1/exchange/announcements?importance_min=10")
        assert response.status_code == 422  # Validation error
        
        # Test invalid limit value
        response = client.get("/api/v1/exchange/announcements?limit=1000")
        assert response.status_code == 422  # Validation error
    
    def test_malformed_request_data(self):
        """Test handling of malformed request data"""
        # Test invalid JSON for price alert creation
        response = client.post(
            "/api/v1/exchange/price-alerts?user_id=1",
            json={
                "token_symbol": "",  # Empty symbol
                "alert_type": "invalid_type",  # Invalid alert type
                "threshold_value": "not_a_number"  # Invalid number
            }
        )
        
        assert response.status_code == 422  # Validation error


# Fixtures and utilities for all test classes

@pytest.fixture(scope="function")
def clean_db():
    """Ensure clean database state for each test"""
    # In a real implementation, you would set up and tear down test database state
    yield
    # Cleanup code would go here