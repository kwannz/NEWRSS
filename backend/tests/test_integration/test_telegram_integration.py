"""
Integration tests for Telegram database integration
Tests the complete workflow from user registration to notification delivery
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.services.telegram_bot import TelegramBot
from app.services.telegram_notifier import TelegramNotifier
from app.models.user import User
from app.models.subscription import UserCategory


@pytest.fixture
def telegram_user_data():
    """Sample Telegram user data for testing"""
    return {
        "id": 123456789,
        "username": "integration_test_user",
        "first_name": "Integration",
        "last_name": "Test",
        "language_code": "en"
    }


@pytest.fixture
def sample_news_item():
    """Sample news item for testing"""
    return {
        'title': 'Bitcoin Reaches New High',
        'content': 'Bitcoin has reached a new all-time high today, driven by institutional adoption.',
        'url': 'https://example.com/bitcoin-high',
        'source': 'CryptoNews',
        'category': 'bitcoin',
        'importance_score': 4,
        'published_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'is_urgent': True
    }


class TestTelegramIntegration:
    """Integration tests for complete Telegram workflow"""

    @pytest.mark.asyncio
    async def test_complete_user_registration_workflow(self, db_session: AsyncSession, telegram_user_data):
        """Test complete user registration and verification"""
        user_repo = UserRepository(db_session)
        
        # Test initial registration
        user = await user_repo.create_telegram_user(telegram_user_data)
        
        assert user is not None
        assert user.telegram_id == str(telegram_user_data["id"])
        assert user.telegram_username == telegram_user_data["username"]
        assert user.is_telegram_user is True
        assert user.urgent_notifications is True  # Default
        assert user.daily_digest is False  # Default
        
        # Verify user can be retrieved
        retrieved_user = await user_repo.get_user_by_telegram_id(user.telegram_id)
        assert retrieved_user.id == user.id
        
        # Test subscription management
        success = await user_repo.update_user_subscription_status(user.telegram_id, True)
        assert success is True
        
        # Test category subscription
        success = await user_repo.subscribe_to_category(user.telegram_id, "bitcoin", 3)
        assert success is True
        
        # Verify category subscription
        categories = await user_repo.get_user_categories(user.telegram_id)
        assert len(categories) == 1
        assert categories[0]["category"] == "bitcoin"
        assert categories[0]["is_subscribed"] is True

    @pytest.mark.asyncio
    async def test_bot_command_integration(self, db_session: AsyncSession, telegram_user_data):
        """Test bot commands with database integration"""
        user_repo = UserRepository(db_session)
        
        # Create user first
        await user_repo.create_telegram_user(telegram_user_data)
        
        # Mock bot and Telegram objects
        with patch('app.services.telegram_bot.Bot') as mock_bot_class:
            bot = TelegramBot("test_token")
            
            # Mock Update and Message
            mock_update = MagicMock()
            mock_update.effective_user = MagicMock()
            mock_update.effective_user.id = telegram_user_data["id"]
            mock_update.effective_user.username = telegram_user_data["username"]
            mock_update.effective_user.first_name = telegram_user_data["first_name"]
            mock_update.effective_user.last_name = telegram_user_data["last_name"]
            mock_update.effective_user.language_code = telegram_user_data["language_code"]
            mock_update.message = MagicMock()
            mock_update.message.reply_text = AsyncMock()
            
            # Test /start command (existing user)
            await bot.start_command(mock_update, None)
            
            # Verify welcome message was sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "欢迎使用 NEWRSS" in call_args[0][0]
            
            # Reset mock
            mock_update.message.reply_text.reset_mock()
            
            # Test /subscribe command
            await bot.subscribe_command(mock_update, None)
            
            # Verify subscription message
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "✅ 已订阅新闻推送" in call_args[0][0]
            
            # Verify user is actually subscribed in database
            settings = await user_repo.get_user_settings(str(telegram_user_data["id"]))
            assert settings["urgent_notifications"] is True

    @pytest.mark.asyncio
    async def test_notification_workflow(self, db_session: AsyncSession, telegram_user_data, sample_news_item):
        """Test complete notification workflow from database to user"""
        user_repo = UserRepository(db_session)
        
        # Create and configure user
        user = await user_repo.create_telegram_user(telegram_user_data)
        await user_repo.update_user_subscription_status(user.telegram_id, True)
        await user_repo.subscribe_to_category(user.telegram_id, "bitcoin", 2)
        
        # Mock TelegramBot for notifier
        with patch('app.services.telegram_notifier.TelegramBot') as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_news_alert = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            notifier = TelegramNotifier()
            
            # Test urgent news notification
            await notifier.notify_urgent_news(sample_news_item)
            
            # Verify news was sent to user
            mock_bot.send_news_alert.assert_called_once()
            call_args = mock_bot.send_news_alert.call_args
            user_ids, news_item = call_args[0]
            
            assert user.telegram_id in user_ids
            assert news_item['title'] == sample_news_item['title']

    @pytest.mark.asyncio
    async def test_daily_digest_workflow(self, db_session: AsyncSession, telegram_user_data):
        """Test daily digest generation and delivery"""
        user_repo = UserRepository(db_session)
        
        # Create user with digest enabled
        user = await user_repo.create_telegram_user(telegram_user_data)
        await user_repo.update_user_settings(user.telegram_id, {
            "daily_digest": True,
            "digest_time": "09:00",
            "min_importance_score": 2
        })
        
        # Mock news data
        mock_news_items = [
            {
                'title': 'Bitcoin News 1',
                'content': 'Content 1',
                'url': 'https://example.com/1',
                'source': 'Source1',
                'category': 'bitcoin',
                'importance_score': 4,
                'published_at': '2025-01-01 10:00',
                'is_urgent': False
            },
            {
                'title': 'Ethereum News 1',
                'content': 'Content 2', 
                'url': 'https://example.com/2',
                'source': 'Source2',
                'category': 'ethereum',
                'importance_score': 3,
                'published_at': '2025-01-01 11:00',
                'is_urgent': False
            }
        ]
        
        # Mock TelegramBot and database calls
        with patch('app.services.telegram_notifier.TelegramBot') as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.bot = MagicMock()
            mock_bot.bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            notifier = TelegramNotifier()
            
            # Mock the database queries
            with patch.object(notifier, 'get_digest_subscribers') as mock_get_subscribers, \
                 patch.object(notifier, 'get_daily_news', return_value=mock_news_items) as mock_get_news:
                
                mock_get_subscribers.return_value = [{
                    'telegram_id': user.telegram_id,
                    'telegram_username': user.telegram_username,
                    'min_importance_score': 2,
                    'digest_time': '09:00'
                }]
                
                # Send daily digest
                await notifier.send_daily_digest("09:00")
                
                # Verify digest was sent
                mock_bot.bot.send_message.assert_called_once()
                call_args = mock_bot.bot.send_message.call_args
                
                assert call_args[1]['chat_id'] == user.telegram_id
                assert call_args[1]['parse_mode'] == 'HTML'
                assert '📊 今日加密货币新闻摘要' in call_args[1]['text']
                assert 'Bitcoin News 1' in call_args[1]['text']
                assert 'Ethereum News 1' in call_args[1]['text']

    @pytest.mark.asyncio
    async def test_user_preference_filtering(self, db_session: AsyncSession, telegram_user_data):
        """Test that user preferences correctly filter notifications"""
        user_repo = UserRepository(db_session)
        
        # Create user with specific preferences
        user = await user_repo.create_telegram_user(telegram_user_data)
        await user_repo.update_user_settings(user.telegram_id, {
            "urgent_notifications": True,
            "min_importance_score": 4  # High threshold
        })
        
        # Subscribe to specific category
        await user_repo.subscribe_to_category(user.telegram_id, "bitcoin", 3)
        
        # Test news filtering
        user_ids = await user_repo.get_users_for_news_notification(
            importance_score=5,
            category="bitcoin"
        )
        assert user.telegram_id in user_ids
        
        # Test with importance too low
        user_ids = await user_repo.get_users_for_news_notification(
            importance_score=2,
            category="bitcoin"
        )
        assert user.telegram_id not in user_ids
        
        # Test with wrong category
        user_ids = await user_repo.get_users_for_news_notification(
            importance_score=5,
            category="ethereum"
        )
        assert user.telegram_id not in user_ids

    @pytest.mark.asyncio
    async def test_settings_persistence_and_retrieval(self, db_session: AsyncSession, telegram_user_data):
        """Test that user settings are properly persisted and retrieved"""
        user_repo = UserRepository(db_session)
        
        # Create user
        user = await user_repo.create_telegram_user(telegram_user_data)
        
        # Update various settings
        new_settings = {
            "urgent_notifications": False,
            "daily_digest": True,
            "digest_time": "08:00",
            "min_importance_score": 3,
            "max_daily_notifications": 5,
            "timezone": "America/New_York",
            "push_settings": {
                "sounds": False,
                "vibration": True
            }
        }
        
        success = await user_repo.update_user_settings(user.telegram_id, new_settings)
        assert success is True
        
        # Retrieve and verify settings
        retrieved_settings = await user_repo.get_user_settings(user.telegram_id)
        
        assert retrieved_settings["urgent_notifications"] is False
        assert retrieved_settings["daily_digest"] is True
        assert retrieved_settings["digest_time"] == "08:00"
        assert retrieved_settings["min_importance_score"] == 3
        assert retrieved_settings["max_daily_notifications"] == 5
        assert retrieved_settings["timezone"] == "America/New_York"
        
        # Check JSON settings
        push_settings = retrieved_settings["push_settings"]
        assert push_settings["sounds"] is False
        assert push_settings["vibration"] is True

    @pytest.mark.asyncio
    async def test_category_management_workflow(self, db_session: AsyncSession, telegram_user_data):
        """Test complete category subscription management"""
        user_repo = UserRepository(db_session)
        
        # Create user
        user = await user_repo.create_telegram_user(telegram_user_data)
        
        # Subscribe to multiple categories
        categories = ["bitcoin", "ethereum", "defi", "trading"]
        importance_levels = [3, 2, 4, 1]
        
        for category, importance in zip(categories, importance_levels):
            success = await user_repo.subscribe_to_category(
                user.telegram_id, category, importance
            )
            assert success is True
        
        # Verify all categories are subscribed
        user_categories = await user_repo.get_user_categories(user.telegram_id)
        assert len(user_categories) == 4
        
        subscribed_categories = {cat["category"]: cat for cat in user_categories}
        
        assert "bitcoin" in subscribed_categories
        assert "ethereum" in subscribed_categories
        assert "defi" in subscribed_categories
        assert "trading" in subscribed_categories
        
        # Check importance levels
        assert subscribed_categories["bitcoin"]["min_importance"] == 3
        assert subscribed_categories["ethereum"]["min_importance"] == 2
        assert subscribed_categories["defi"]["min_importance"] == 4
        assert subscribed_categories["trading"]["min_importance"] == 1
        
        # Test unsubscribing from a category
        success = await user_repo.unsubscribe_from_category(user.telegram_id, "ethereum")
        assert success is True
        
        # Verify category status changed
        user_categories = await user_repo.get_user_categories(user.telegram_id)
        ethereum_category = next(
            (cat for cat in user_categories if cat["category"] == "ethereum"),
            None
        )
        assert ethereum_category is not None
        assert ethereum_category["is_subscribed"] is False

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, db_session: AsyncSession):
        """Test error handling in various scenarios"""
        user_repo = UserRepository(db_session)
        
        # Test operations on non-existent user
        settings = await user_repo.get_user_settings("999999999")
        assert settings is None
        
        success = await user_repo.update_user_subscription_status("999999999", True)
        assert success is False
        
        success = await user_repo.subscribe_to_category("999999999", "bitcoin")
        assert success is False
        
        user_ids = await user_repo.get_users_for_news_notification(3)
        # Should return empty list, not raise exception
        assert isinstance(user_ids, list)