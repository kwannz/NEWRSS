"""
Comprehensive E2E tests for Telegram bot user journey
Testing complete user flows from /start to news reception
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.telegram_bot import TelegramBotService
from app.models.user import User
from app.models.subscription import Subscription
from app.models.news import NewsItem
from app.repositories.user_repository import UserRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.news_repository import NewsRepository
from telegram import Update, Message, Chat, CallbackQuery
from telegram.ext import Application


@pytest.mark.asyncio
class TestTelegramBotE2EJourney:
    """
    Complete E2E tests for Telegram bot user journeys
    """
    
    @pytest.fixture
    async def bot_service(self, db_session: AsyncSession):
        """Create bot service with mocked dependencies"""
        service = TelegramBotService()
        service.user_repo = UserRepository(db_session)
        service.subscription_repo = SubscriptionRepository(db_session)
        service.news_repo = NewsRepository(db_session)
        return service

    @pytest.fixture
    def mock_update(self):
        """Create mock Telegram update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"
        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = 123456789
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        update.message.reply_photo = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock Telegram context"""
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.edit_message_text = AsyncMock()
        return context

    async def test_complete_user_onboarding_journey(self, bot_service, mock_update, mock_context, db_session):
        """
        Test complete user journey from /start to preference setup
        """
        # Step 1: User sends /start command
        mock_update.message.text = "/start"
        
        await bot_service.start_command(mock_update, mock_context)
        
        # Verify welcome message sent
        mock_update.message.reply_text.assert_called()
        welcome_call = mock_update.message.reply_text.call_args
        assert "欢迎" in welcome_call[0][0] or "Welcome" in welcome_call[0][0]
        
        # Verify user created in database
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_telegram_id(123456789)
        assert user is not None
        assert user.telegram_username == "testuser"
        assert user.is_active is True

    async def test_help_command_comprehensive_info(self, bot_service, mock_update, mock_context):
        """
        Test help command provides comprehensive information
        """
        mock_update.message.text = "/help"
        
        await bot_service.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called()
        help_message = mock_update.message.reply_text.call_args[0][0]
        
        # Verify all essential commands are mentioned
        essential_commands = ["/start", "/help", "/settings", "/status"]
        for command in essential_commands:
            assert command in help_message

    async def test_settings_command_with_inline_keyboard(self, bot_service, mock_update, mock_context, db_session):
        """
        Test settings command displays preferences with inline keyboard
        """
        # Create existing user with preferences
        user_repo = UserRepository(db_session)
        user = await user_repo.create_user(
            telegram_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User",
            preferences={
                "urgent_notifications": True,
                "daily_digest": False,
                "min_importance_score": 3,
                "max_daily_notifications": 10,
                "categories": ["bitcoin", "ethereum"]
            }
        )
        await db_session.commit()
        
        mock_update.message.text = "/settings"
        
        await bot_service.settings_command(mock_update, mock_context)
        
        # Verify settings message with keyboard
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        
        # Check if reply_markup (keyboard) was provided
        assert 'reply_markup' in call_args[1]
        settings_text = call_args[0][0]
        assert "设置" in settings_text or "Settings" in settings_text

    async def test_status_command_with_subscription_info(self, bot_service, mock_update, mock_context, db_session):
        """
        Test status command shows subscription and activity information
        """
        # Create user with subscriptions
        user_repo = UserRepository(db_session)
        subscription_repo = SubscriptionRepository(db_session)
        
        user = await user_repo.create_user(
            telegram_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # Add some subscriptions
        await subscription_repo.create_subscription(
            user_id=user.id,
            categories=["bitcoin", "ethereum"],
            min_importance_score=3,
            urgent_only=False
        )
        
        await db_session.commit()
        
        mock_update.message.text = "/status"
        
        await bot_service.status_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called()
        status_text = mock_update.message.reply_text.call_args[0][0]
        
        # Verify status includes subscription info
        assert "订阅" in status_text or "subscription" in status_text.lower()
        assert "bitcoin" in status_text or "ethereum" in status_text

    async def test_preference_update_via_callback(self, bot_service, mock_context, db_session):
        """
        Test updating preferences via inline keyboard callbacks
        """
        # Setup user
        user_repo = UserRepository(db_session)
        user = await user_repo.create_user(
            telegram_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User",
            preferences={"urgent_notifications": False}
        )
        await db_session.commit()
        
        # Create callback update
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789
        update.callback_query = MagicMock(spec=CallbackQuery)
        update.callback_query.data = "toggle_urgent_notifications"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        
        await bot_service.handle_settings_callback(update, mock_context)
        
        # Verify callback answered
        update.callback_query.answer.assert_called()
        
        # Verify user preferences updated
        updated_user = await user_repo.get_by_telegram_id(123456789)
        assert updated_user.preferences["urgent_notifications"] is True

    async def test_news_delivery_to_subscribed_user(self, bot_service, mock_context, db_session):
        """
        Test news delivery to user with matching subscription
        """
        # Setup user with specific preferences
        user_repo = UserRepository(db_session)
        subscription_repo = SubscriptionRepository(db_session)
        news_repo = NewsRepository(db_session)
        
        user = await user_repo.create_user(
            telegram_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # Create subscription for Bitcoin news
        subscription = await subscription_repo.create_subscription(
            user_id=user.id,
            categories=["bitcoin"],
            min_importance_score=3,
            urgent_only=False
        )
        
        # Create matching news item
        news_item = await news_repo.create(
            title="Bitcoin Reaches New High",
            content="Bitcoin has reached a new all-time high",
            url="https://example.com/bitcoin-news",
            source="CoinDesk",
            category="bitcoin",
            importance_score=4,
            is_urgent=False,
            published_at="2024-01-01T12:00:00Z"
        )
        
        await db_session.commit()
        
        # Mock news delivery
        with patch.object(bot_service, 'send_news_to_user') as mock_send:
            mock_send.return_value = AsyncMock()
            
            # Trigger news delivery
            await bot_service.deliver_news_to_subscribers(news_item)
            
            # Verify news was sent to user
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == user.telegram_id
            assert call_args[0][1].id == news_item.id

    async def test_urgent_news_notification_flow(self, bot_service, mock_context, db_session):
        """
        Test urgent news notification flow with special formatting
        """
        # Setup user with urgent notifications enabled
        user_repo = UserRepository(db_session)
        subscription_repo = SubscriptionRepository(db_session)
        news_repo = NewsRepository(db_session)
        
        user = await user_repo.create_user(
            telegram_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User",
            preferences={"urgent_notifications": True}
        )
        
        subscription = await subscription_repo.create_subscription(
            user_id=user.id,
            categories=["bitcoin"],
            min_importance_score=1,  # Low threshold for urgent news
            urgent_only=False
        )
        
        # Create urgent news
        urgent_news = await news_repo.create(
            title="BREAKING: Major Exchange Hacked",
            content="A major cryptocurrency exchange has been compromised",
            url="https://example.com/urgent-news",
            source="CryptoNews",
            category="bitcoin",
            importance_score=5,
            is_urgent=True,
            published_at="2024-01-01T12:00:00Z"
        )
        
        await db_session.commit()
        
        # Mock urgent news delivery
        with patch.object(bot_service, 'send_urgent_news') as mock_urgent:
            mock_urgent.return_value = AsyncMock()
            
            await bot_service.deliver_urgent_news(urgent_news)
            
            mock_urgent.assert_called_once()
            call_args = mock_urgent.call_args
            assert "BREAKING" in call_args[0][1] or "紧急" in call_args[0][1]

    async def test_user_preference_persistence(self, bot_service, mock_update, mock_context, db_session):
        """
        Test that user preferences are properly persisted and retrieved
        """
        # Initial setup
        await bot_service.start_command(mock_update, mock_context)
        
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_telegram_id(123456789)
        
        # Update preferences multiple times
        preferences_updates = [
            {"urgent_notifications": True, "daily_digest": False},
            {"min_importance_score": 4, "categories": ["ethereum"]},
            {"max_daily_notifications": 5, "urgent_notifications": False}
        ]
        
        for update_prefs in preferences_updates:
            await user_repo.update_user_preferences(user.id, update_prefs)
            await db_session.commit()
            
            # Verify persistence
            updated_user = await user_repo.get_by_telegram_id(123456789)
            for key, value in update_prefs.items():
                assert updated_user.preferences.get(key) == value

    async def test_subscription_filtering_logic(self, bot_service, db_session):
        """
        Test that news filtering works correctly for different subscription criteria
        """
        user_repo = UserRepository(db_session)
        subscription_repo = SubscriptionRepository(db_session)
        news_repo = NewsRepository(db_session)
        
        # Create user
        user = await user_repo.create_user(
            telegram_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # Create specific subscription
        subscription = await subscription_repo.create_subscription(
            user_id=user.id,
            categories=["bitcoin"],  # Only Bitcoin news
            min_importance_score=4,  # High importance only
            urgent_only=False
        )
        
        # Create various news items
        news_items = [
            # Should match: Bitcoin + High importance
            await news_repo.create(
                title="Bitcoin Major Update",
                content="Important Bitcoin development",
                url="https://example.com/bitcoin-1",
                source="CoinDesk",
                category="bitcoin",
                importance_score=5,
                is_urgent=False,
                published_at="2024-01-01T12:00:00Z"
            ),
            # Should NOT match: Wrong category
            await news_repo.create(
                title="Ethereum Update",
                content="Ethereum development",
                url="https://example.com/eth-1",
                source="CoinDesk",
                category="ethereum",
                importance_score=5,
                is_urgent=False,
                published_at="2024-01-01T12:00:00Z"
            ),
            # Should NOT match: Low importance
            await news_repo.create(
                title="Bitcoin Minor News",
                content="Small Bitcoin update",
                url="https://example.com/bitcoin-2",
                source="CoinDesk",
                category="bitcoin",
                importance_score=2,  # Below threshold
                is_urgent=False,
                published_at="2024-01-01T12:00:00Z"
            )
        ]
        
        await db_session.commit()
        
        # Test filtering logic
        matching_news = await bot_service.get_matching_news_for_user(user.telegram_id)
        
        # Should only get the first news item
        assert len(matching_news) == 1
        assert matching_news[0].title == "Bitcoin Major Update"

    async def test_error_handling_in_bot_commands(self, bot_service, mock_update, mock_context, db_session):
        """
        Test error handling for various bot command scenarios
        """
        # Test with invalid user data
        mock_update.effective_user.id = None
        
        # Should handle gracefully without crashing
        await bot_service.start_command(mock_update, mock_context)
        
        # Test with database error
        with patch.object(UserRepository, 'create_user', side_effect=Exception("Database error")):
            mock_update.effective_user.id = 123456789
            
            # Should handle database errors gracefully
            await bot_service.start_command(mock_update, mock_context)
            
            # Verify error message sent to user
            mock_update.message.reply_text.assert_called()
            error_call = mock_update.message.reply_text.call_args_list[-1]
            assert "错误" in error_call[0][0] or "error" in error_call[0][0].lower()

    async def test_news_formatting_and_display(self, bot_service, db_session):
        """
        Test news message formatting for different types of news
        """
        news_repo = NewsRepository(db_session)
        
        # Test various news formats
        test_cases = [
            # Regular news
            {
                "title": "Bitcoin Price Update",
                "content": "Bitcoin price has increased by 5% today",
                "importance_score": 3,
                "is_urgent": False,
                "key_tokens": ["BTC", "price", "increase"],
                "key_prices": ["$45000", "$47250"]
            },
            # Urgent news
            {
                "title": "BREAKING: Exchange Security Breach",
                "content": "Major security incident reported",
                "importance_score": 5,
                "is_urgent": True,
                "key_tokens": ["security", "breach", "exchange"],
                "key_prices": []
            },
            # News with special characters
            {
                "title": "Crypto Market: Bulls & Bears 📈📉",
                "content": "Market analysis shows mixed signals",
                "importance_score": 4,
                "is_urgent": False,
                "key_tokens": ["market", "analysis"],
                "key_prices": ["$40000-$50000"]
            }
        ]
        
        for case in test_cases:
            news = await news_repo.create(
                title=case["title"],
                content=case["content"],
                url="https://example.com/news",
                source="TestSource",
                category="bitcoin",
                importance_score=case["importance_score"],
                is_urgent=case["is_urgent"],
                published_at="2024-01-01T12:00:00Z",
                key_tokens=case.get("key_tokens"),
                key_prices=case.get("key_prices")
            )
            
            # Test message formatting
            formatted_message = bot_service.format_news_message(news)
            
            # Basic formatting checks
            assert case["title"] in formatted_message
            assert case["content"] in formatted_message
            
            # Urgent news should have special markers
            if case["is_urgent"]:
                assert "🚨" in formatted_message or "URGENT" in formatted_message
            
            # Key tokens should be included
            if case.get("key_tokens"):
                for token in case["key_tokens"][:3]:  # Max 3 tokens usually displayed
                    assert token in formatted_message
            
            # Key prices should be included
            if case.get("key_prices"):
                for price in case["key_prices"][:2]:  # Max 2 prices usually displayed
                    assert price in formatted_message

    async def test_daily_digest_functionality(self, bot_service, db_session):
        """
        Test daily digest creation and delivery
        """
        user_repo = UserRepository(db_session)
        subscription_repo = SubscriptionRepository(db_session)
        news_repo = NewsRepository(db_session)
        
        # Setup user with daily digest enabled
        user = await user_repo.create_user(
            telegram_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User",
            preferences={"daily_digest": True}
        )
        
        subscription = await subscription_repo.create_subscription(
            user_id=user.id,
            categories=["bitcoin", "ethereum"],
            min_importance_score=2,
            urgent_only=False
        )
        
        # Create news items for digest
        news_items = []
        for i in range(5):
            news = await news_repo.create(
                title=f"Daily News Item {i+1}",
                content=f"Content for news item {i+1}",
                url=f"https://example.com/news-{i+1}",
                source="DigestSource",
                category="bitcoin" if i % 2 == 0 else "ethereum",
                importance_score=3 + (i % 3),
                is_urgent=False,
                published_at="2024-01-01T12:00:00Z"
            )
            news_items.append(news)
        
        await db_session.commit()
        
        # Generate daily digest
        with patch.object(bot_service, 'send_daily_digest') as mock_digest:
            mock_digest.return_value = AsyncMock()
            
            await bot_service.send_daily_digest_to_subscribers()
            
            mock_digest.assert_called()
            
            # Verify digest contains multiple news items
            digest_call = mock_digest.call_args
            digest_content = digest_call[0][1]  # Assuming second arg is content
            
            # Should contain multiple news items
            assert "Daily News Item" in digest_content
            assert len(digest_content.split("Daily News Item")) > 2  # At least 2 news items

    @pytest.mark.slow
    async def test_concurrent_user_interactions(self, bot_service, db_session):
        """
        Test bot handling multiple concurrent user interactions
        """
        # Create multiple mock updates for different users
        user_updates = []
        for i in range(10):
            update = MagicMock(spec=Update)
            update.effective_user = MagicMock()
            update.effective_user.id = 1000 + i
            update.effective_user.username = f"user{i}"
            update.effective_user.first_name = f"User{i}"
            update.effective_chat = MagicMock()
            update.effective_chat.id = 1000 + i
            update.message = MagicMock(spec=Message)
            update.message.reply_text = AsyncMock()
            update.message.text = "/start"
            user_updates.append(update)
        
        context = MagicMock()
        
        # Process all updates concurrently
        tasks = [
            bot_service.start_command(update, context) 
            for update in user_updates
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all users were created
        user_repo = UserRepository(db_session)
        for i in range(10):
            user = await user_repo.get_by_telegram_id(1000 + i)
            assert user is not None
            assert user.telegram_username == f"user{i}"

    async def test_bot_rate_limiting_and_flood_protection(self, bot_service, mock_update, mock_context):
        """
        Test bot's handling of rate limiting and flood protection
        """
        # Simulate rapid consecutive commands from same user
        commands = ["/start", "/help", "/settings", "/status", "/help", "/settings"]
        
        for command in commands:
            mock_update.message.text = command
            await bot_service.handle_command(mock_update, mock_context)
        
        # Verify all commands were handled (no rate limiting in basic implementation)
        # In production, you might implement rate limiting that this test would verify
        assert mock_update.message.reply_text.call_count >= len(commands)

    async def test_subscription_update_workflow(self, bot_service, mock_context, db_session):
        """
        Test complete subscription update workflow via bot interface
        """
        user_repo = UserRepository(db_session)
        subscription_repo = SubscriptionRepository(db_session)
        
        # Create user
        user = await user_repo.create_user(
            telegram_id=123456789,
            telegram_username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # Initial subscription
        subscription = await subscription_repo.create_subscription(
            user_id=user.id,
            categories=["bitcoin"],
            min_importance_score=3,
            urgent_only=False
        )
        
        await db_session.commit()
        
        # Simulate subscription update via callback
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock()
        update.effective_user.id = 123456789
        update.callback_query = MagicMock(spec=CallbackQuery)
        update.callback_query.data = "update_categories_ethereum"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        
        await bot_service.handle_subscription_update(update, mock_context)
        
        # Verify subscription updated
        updated_subscription = await subscription_repo.get_by_user_id(user.id)
        assert "ethereum" in updated_subscription.categories or len(updated_subscription.categories) > 1