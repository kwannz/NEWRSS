import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from telegram import Update, User as TelegramUser, Message, CallbackQuery
from telegram.ext import ContextTypes

from app.services.telegram_bot import TelegramBot
from app.repositories.user_repository import UserRepository
from app.models.user import User


@pytest.fixture
def mock_telegram_user():
    """Create mock Telegram user"""
    user = Mock(spec=TelegramUser)
    user.id = 12345
    user.username = "test_user"
    user.first_name = "Test"
    user.last_name = "User"
    user.language_code = "en"
    return user


@pytest.fixture
def mock_update(mock_telegram_user):
    """Create mock Update object"""
    update = Mock(spec=Update)
    update.effective_user = mock_telegram_user
    
    # Mock message
    message = Mock(spec=Message)
    message.reply_text = AsyncMock()
    update.message = message
    
    return update


@pytest.fixture
def mock_context():
    """Create mock context"""
    return Mock(spec=ContextTypes.DEFAULT_TYPE)


@pytest.fixture
def telegram_bot():
    """Create TelegramBot instance with mocked dependencies"""
    with patch('app.services.telegram_bot.Bot'), \
         patch('app.services.telegram_bot.Application'):
        bot = TelegramBot("fake_token")
        bot.logger = Mock()
        return bot


@pytest.fixture
def mock_user_settings():
    """Mock user settings data"""
    return {
        "urgent_notifications": True,
        "daily_digest": False,
        "digest_time": "09:00",
        "min_importance_score": 3,
        "max_daily_notifications": 10,
        "timezone": "UTC",
        "push_settings": {}
    }


class TestAdvancedTelegramCommands:
    """Test advanced Telegram bot commands"""

    @pytest.mark.asyncio
    async def test_urgent_on_command_success(self, telegram_bot, mock_update, mock_context):
        """Test /urgent_on command successful execution"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'get_user_by_telegram_id', return_value=mock_user), \
             patch.object(UserRepository, 'update_user_settings', return_value=True):
            
            await telegram_bot.urgent_on_command(mock_update, mock_context)
            
            # Verify response message was sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "✅ 紧急推送已开启" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_urgent_on_command_user_not_found(self, telegram_bot, mock_update, mock_context):
        """Test /urgent_on command when user not found"""
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'get_user_by_telegram_id', return_value=None):
            
            await telegram_bot.urgent_on_command(mock_update, mock_context)
            
            # Verify error message was sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "❌ 请先使用 /start 命令注册" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_urgent_off_command_success(self, telegram_bot, mock_update, mock_context):
        """Test /urgent_off command successful execution"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'get_user_by_telegram_id', return_value=mock_user), \
             patch.object(UserRepository, 'update_user_settings', return_value=True):
            
            await telegram_bot.urgent_off_command(mock_update, mock_context)
            
            # Verify response message was sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "❌ 紧急推送已关闭" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_categories_command(self, telegram_bot, mock_update, mock_context):
        """Test /categories command"""
        with patch.object(telegram_bot, '_handle_categories') as mock_handle:
            await telegram_bot.categories_command(mock_update, mock_context)
            mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_command(self, telegram_bot, mock_update, mock_context):
        """Test /help command"""
        await telegram_bot.help_command(mock_update, mock_context)
        
        # Verify help message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "🤖" in call_args[0][0]
        assert "NEWRSS 帮助中心" in call_args[0][0]
        assert call_args[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_settings_command_enhanced_display(self, telegram_bot, mock_update, mock_context, mock_user_settings):
        """Test enhanced /settings command display"""
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'get_user_settings', return_value=mock_user_settings):
            
            await telegram_bot.settings_command(mock_update, mock_context)
            
            # Verify enhanced settings display
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            
            # Check for enhanced formatting
            assert "⚙️ <b>推送设置中心</b>" in call_args[0][0]
            assert "📋 <b>基本设置</b>" in call_args[0][0]
            assert "🎯 <b>过滤设置</b>" in call_args[0][0]
            assert call_args[1]["parse_mode"] == "HTML"


class TestCallbackHandlers:
    """Test callback query handlers"""

    @pytest.fixture
    def mock_callback_query(self, mock_telegram_user):
        """Create mock callback query"""
        query = Mock(spec=CallbackQuery)
        query.from_user = mock_telegram_user
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query

    @pytest.mark.asyncio
    async def test_digest_time_settings_callback(self, telegram_bot, mock_callback_query, mock_context):
        """Test digest time settings callback"""
        await telegram_bot._handle_digest_time_settings(mock_callback_query, mock_context)
        
        # Verify time selection keyboard was shown
        mock_callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query.edit_message_text.call_args
        assert "⏰ 选择每日摘要发送时间" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_digest_time_callback(self, telegram_bot, mock_callback_query, mock_context):
        """Test set digest time callback"""
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'update_user_settings', return_value=True):
            
            await telegram_bot._handle_set_digest_time(mock_callback_query, mock_context, "09:00")
            
            # Verify confirmation message
            mock_callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query.edit_message_text.call_args
            assert "✅ 摘要时间已设置为: ☀️ 09:00" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_notification_limit_settings_callback(self, telegram_bot, mock_callback_query, mock_context):
        """Test notification limit settings callback"""
        await telegram_bot._handle_notification_limit_settings(mock_callback_query, mock_context)
        
        # Verify limit selection keyboard was shown
        mock_callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query.edit_message_text.call_args
        assert "📱 设置每日最大推送数量" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_notification_limit_callback(self, telegram_bot, mock_callback_query, mock_context):
        """Test set notification limit callback"""
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'update_user_settings', return_value=True):
            
            await telegram_bot._handle_set_notification_limit(mock_callback_query, mock_context, 20)
            
            # Verify confirmation message
            mock_callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query.edit_message_text.call_args
            assert "✅ 每日推送限制已设置为: 20条/天" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_notification_limit_unlimited(self, telegram_bot, mock_callback_query, mock_context):
        """Test set unlimited notification limit"""
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'update_user_settings', return_value=True):
            
            await telegram_bot._handle_set_notification_limit(mock_callback_query, mock_context, 999)
            
            # Verify unlimited confirmation message
            mock_callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_query.edit_message_text.call_args
            assert "✅ 每日推送限制已设置为: 无限制" in call_args[0][0]


class TestButtonCallback:
    """Test button callback handling for new features"""

    @pytest.fixture
    def mock_callback_query(self, mock_telegram_user):
        """Create mock callback query"""
        query = Mock(spec=CallbackQuery)
        query.from_user = mock_telegram_user
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query

    @pytest.fixture
    def mock_update_with_query(self, mock_callback_query):
        """Create mock update with callback query"""
        update = Mock(spec=Update)
        update.callback_query = mock_callback_query
        update.effective_user = mock_callback_query.from_user
        return update

    @pytest.mark.asyncio
    async def test_button_callback_digest_time(self, telegram_bot, mock_update_with_query, mock_context):
        """Test button callback for digest time"""
        mock_update_with_query.callback_query.data = "digest_time"
        
        with patch.object(telegram_bot, '_handle_digest_time_settings') as mock_handler:
            await telegram_bot.button_callback(mock_update_with_query, mock_context)
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_button_callback_digest_time_set(self, telegram_bot, mock_update_with_query, mock_context):
        """Test button callback for setting digest time"""
        mock_update_with_query.callback_query.data = "digest_time_10:00"
        
        with patch.object(telegram_bot, '_handle_set_digest_time') as mock_handler:
            await telegram_bot.button_callback(mock_update_with_query, mock_context)
            mock_handler.assert_called_once_with(
                mock_update_with_query.callback_query, 
                mock_context, 
                "10:00"
            )

    @pytest.mark.asyncio
    async def test_button_callback_notification_limit(self, telegram_bot, mock_update_with_query, mock_context):
        """Test button callback for notification limit"""
        mock_update_with_query.callback_query.data = "notification_limit"
        
        with patch.object(telegram_bot, '_handle_notification_limit_settings') as mock_handler:
            await telegram_bot.button_callback(mock_update_with_query, mock_context)
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_button_callback_limit_set(self, telegram_bot, mock_update_with_query, mock_context):
        """Test button callback for setting limit"""
        mock_update_with_query.callback_query.data = "limit_50"
        
        with patch.object(telegram_bot, '_handle_set_notification_limit') as mock_handler:
            await telegram_bot.button_callback(mock_update_with_query, mock_context)
            mock_handler.assert_called_once_with(
                mock_update_with_query.callback_query, 
                mock_context, 
                50
            )

    @pytest.mark.asyncio
    async def test_button_callback_start_from_help(self, telegram_bot, mock_update_with_query, mock_context):
        """Test button callback for start from help"""
        mock_update_with_query.callback_query.data = "start"
        
        with patch.object(telegram_bot, 'start_command') as mock_handler:
            await telegram_bot.button_callback(mock_update_with_query, mock_context)
            mock_handler.assert_called_once()


class TestErrorHandling:
    """Test error handling in advanced features"""

    @pytest.fixture
    def mock_update(self, mock_telegram_user):
        update = Mock(spec=Update)
        update.effective_user = mock_telegram_user
        message = Mock(spec=Message)
        message.reply_text = AsyncMock()
        update.message = message
        return update

    @pytest.mark.asyncio
    async def test_urgent_on_command_database_error(self, telegram_bot, mock_update, mock_context):
        """Test /urgent_on command with database error"""
        with patch('app.services.telegram_bot.SessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database error")
            
            await telegram_bot.urgent_on_command(mock_update, mock_context)
            
            # Verify error handling
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "❌ 操作失败，请稍后重试" in call_args[0][0]
            
            # Verify error was logged
            telegram_bot.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_settings_command_database_error(self, telegram_bot, mock_update, mock_context):
        """Test /settings command with database error"""
        with patch('app.services.telegram_bot.SessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database error")
            
            await telegram_bot.settings_command(mock_update, mock_context)
            
            # Verify error handling
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "❌ 获取设置失败，请稍后重试" in call_args[0][0]


class TestCommandRegistration:
    """Test that all new commands are properly registered"""

    def test_handler_setup_includes_new_commands(self):
        """Test that setup_handlers includes all new command handlers"""
        with patch('app.services.telegram_bot.Bot'), \
             patch('app.services.telegram_bot.Application') as mock_app_class, \
             patch('app.services.telegram_bot.CommandHandler') as mock_command_handler:
            
            mock_app = Mock()
            mock_app_class.builder.return_value.token.return_value.build.return_value = mock_app
            
            bot = TelegramBot("fake_token")
            
            # Verify all command handlers were added
            expected_commands = [
                "start", "subscribe", "unsubscribe", "settings", 
                "status", "urgent_on", "urgent_off", "categories", "help"
            ]
            
            call_args_list = mock_command_handler.call_args_list
            registered_commands = [call[0][0] for call in call_args_list]
            
            for command in expected_commands:
                assert command in registered_commands


class TestIntegration:
    """Integration tests for the advanced Telegram features"""

    @pytest.mark.asyncio
    async def test_full_settings_workflow(self, telegram_bot, mock_update, mock_context, mock_user_settings):
        """Test complete settings workflow"""
        # Mock database interactions
        mock_user = Mock(spec=User)
        mock_user.id = 1
        
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'get_user_by_telegram_id', return_value=mock_user), \
             patch.object(UserRepository, 'get_user_settings', return_value=mock_user_settings), \
             patch.object(UserRepository, 'update_user_settings', return_value=True):
            
            # Test settings command
            await telegram_bot.settings_command(mock_update, mock_context)
            
            # Verify settings were displayed
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            
            # Check all expected sections are present
            settings_text = call_args[0][0]
            assert "推送设置中心" in settings_text
            assert "基本设置" in settings_text
            assert "过滤设置" in settings_text
            assert "紧急推送" in settings_text
            assert "每日摘要" in settings_text

    @pytest.mark.asyncio 
    async def test_urgent_toggle_workflow(self, telegram_bot, mock_update, mock_context):
        """Test urgent notification toggle workflow"""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        
        with patch('app.services.telegram_bot.SessionLocal') as mock_session, \
             patch.object(UserRepository, 'get_user_by_telegram_id', return_value=mock_user), \
             patch.object(UserRepository, 'update_user_settings', return_value=True) as mock_update_settings:
            
            # Test turning on urgent notifications
            await telegram_bot.urgent_on_command(mock_update, mock_context)
            
            # Verify the setting was updated correctly
            mock_update_settings.assert_called_once()
            call_args = mock_update_settings.call_args
            assert call_args[0][1] == {"urgent_notifications": True}
            
            # Reset mock for off command
            mock_update_settings.reset_mock()
            
            # Test turning off urgent notifications  
            await telegram_bot.urgent_off_command(mock_update, mock_context)
            
            # Verify the setting was updated correctly
            mock_update_settings.assert_called_once()
            call_args = mock_update_settings.call_args
            assert call_args[0][1] == {"urgent_notifications": False}