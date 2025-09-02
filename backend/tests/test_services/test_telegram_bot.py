import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Bot, Update, User as TelegramUser, Message, CallbackQuery
from telegram.ext import ContextTypes
from app.services.telegram_bot import TelegramBot
from app.models.user import User

class TestTelegramBot:
    
    @pytest.fixture
    def bot(self):
        """创建测试bot实例"""
        with patch('app.services.telegram_bot.Bot') as mock_bot, \
             patch('app.services.telegram_bot.Application') as mock_app:
            mock_app_instance = MagicMock()
            mock_app_instance.add_handler = MagicMock()
            mock_app.builder.return_value.token.return_value.build.return_value = mock_app_instance
            
            bot = TelegramBot("test_token")
            bot.bot = mock_bot.return_value
            bot.app = mock_app_instance
            return bot
    
    @pytest.fixture
    def mock_update(self):
        """创建模拟的Update对象"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 12345
        update.effective_user.username = "testuser"
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_callback_query(self):
        """创建模拟的CallbackQuery对象"""
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.data = "test_data"
        return query

    def test_bot_initialization(self, bot):
        """测试bot初始化"""
        assert bot.token == "test_token"
        assert bot.bot is not None
        assert bot.app is not None

    @pytest.mark.asyncio
    async def test_start_command_new_user(self, bot, mock_update):
        """测试/start命令处理 - 新用户"""
        # Mock successful user registration
        mock_user = User(
            id=1,
            telegram_id="12345",
            telegram_username="testuser",
            is_active=True
        )
        
        with patch.object(bot, 'register_user') as mock_register:
            mock_register.return_value = mock_user
            await bot.start_command(mock_update, None)
        
        # Check user data was passed correctly
        call_args = mock_register.call_args[0][0]
        assert call_args["id"] == 12345
        assert call_args["username"] == "testuser"
        
        mock_update.message.reply_text.assert_called_once()
        
        # 检查回复消息内容
        args, kwargs = mock_update.message.reply_text.call_args
        assert "欢迎使用 NEWRSS" in args[0]
        assert "reply_markup" in kwargs
    
    @pytest.mark.asyncio
    async def test_start_command_registration_failed(self, bot, mock_update):
        """测试/start命令处理 - 注册失败"""
        with patch.object(bot, 'register_user') as mock_register:
            mock_register.return_value = None  # Registration failed
            await bot.start_command(mock_update, None)
        
        mock_update.message.reply_text.assert_called_once()
        args, _ = mock_update.message.reply_text.call_args
        assert "注册失败" in args[0]

    @pytest.mark.asyncio
    @patch('app.services.telegram_bot.SessionLocal')
    async def test_subscribe_command_success(self, mock_session, bot, mock_update):
        """测试/subscribe命令处理 - 成功"""
        # Mock database operations
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        with patch('app.services.telegram_bot.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_user_subscription_status.return_value = True
            mock_repo.update_user_activity.return_value = None
            mock_repo_class.return_value = mock_repo
            
            await bot.subscribe_command(mock_update, None)
            
            # Check database operations were called
            mock_repo.update_user_subscription_status.assert_called_once_with("12345", True)
            mock_repo.update_user_activity.assert_called_once()
            
            mock_update.message.reply_text.assert_called_once()
            args, _ = mock_update.message.reply_text.call_args
            assert "✅ 已订阅新闻推送" in args[0]
    
    @pytest.mark.asyncio
    @patch('app.services.telegram_bot.SessionLocal')
    async def test_subscribe_command_user_not_found(self, mock_session, bot, mock_update):
        """测试/subscribe命令处理 - 用户不存在"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        with patch('app.services.telegram_bot.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_user_subscription_status.return_value = False
            mock_repo_class.return_value = mock_repo
            
            await bot.subscribe_command(mock_update, None)
            
            mock_update.message.reply_text.assert_called_once()
            args, _ = mock_update.message.reply_text.call_args
            assert "❌ 订阅失败" in args[0]
            assert "/start" in args[0]

    @pytest.mark.asyncio
    @patch('app.services.telegram_bot.SessionLocal')
    async def test_unsubscribe_command_success(self, mock_session, bot, mock_update):
        """测试/unsubscribe命令处理 - 成功"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        with patch('app.services.telegram_bot.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_user_subscription_status.return_value = True
            mock_repo.update_user_activity.return_value = None
            mock_repo_class.return_value = mock_repo
            
            await bot.unsubscribe_command(mock_update, None)
            
            # Check database operations
            mock_repo.update_user_subscription_status.assert_called_once_with("12345", False)
            mock_repo.update_user_activity.assert_called_once()
            
            mock_update.message.reply_text.assert_called_once()
            args, _ = mock_update.message.reply_text.call_args
            assert "❌ 已取消订阅" in args[0]

    @pytest.mark.asyncio
    @patch('app.services.telegram_bot.SessionLocal')
    async def test_settings_command_success(self, mock_session, bot, mock_update):
        """测试/settings命令处理 - 成功"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        mock_settings = {
            "urgent_notifications": True,
            "daily_digest": False,
            "digest_time": "09:00",
            "min_importance_score": 3,
            "max_daily_notifications": 10,
            "timezone": "UTC",
            "push_settings": {}
        }
        
        with patch('app.services.telegram_bot.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_user_settings.return_value = mock_settings
            mock_repo_class.return_value = mock_repo
            
            await bot.settings_command(mock_update, None)
            
            mock_repo.get_user_settings.assert_called_once_with("12345")
            
            mock_update.message.reply_text.assert_called_once()
            args, kwargs = mock_update.message.reply_text.call_args
            assert "⚙️ 当前设置" in args[0]
            assert "reply_markup" in kwargs
    
    @pytest.mark.asyncio
    @patch('app.services.telegram_bot.SessionLocal')
    async def test_settings_command_user_not_found(self, mock_session, bot, mock_update):
        """测试/settings命令处理 - 用户不存在"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        with patch('app.services.telegram_bot.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_user_settings.return_value = None
            mock_repo_class.return_value = mock_repo
            
            await bot.settings_command(mock_update, None)
            
            mock_update.message.reply_text.assert_called_once()
            args, _ = mock_update.message.reply_text.call_args
            assert "❌ 请先使用 /start 命令注册" in args[0]

    @pytest.mark.asyncio
    async def test_button_callback_subscribe(self, bot, mock_update):
        """测试订阅按钮回调"""
        mock_update.callback_query = mock_update.mock_callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.data = "subscribe"
        
        with patch.object(bot, 'subscribe_command') as mock_subscribe:
            await bot.button_callback(mock_update, None)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_subscribe.assert_called_once_with(mock_update, None)

    @pytest.mark.asyncio
    async def test_button_callback_settings(self, bot, mock_update):
        """测试设置按钮回调"""
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.data = "settings"
        
        with patch.object(bot, 'settings_command') as mock_settings:
            await bot.button_callback(mock_update, None)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_settings.assert_called_once_with(mock_update, None)

    @pytest.mark.asyncio
    @patch('app.services.telegram_bot.SessionLocal')
    async def test_register_user_new_user(self, mock_session, bot):
        """测试用户注册 - 新用户"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        user_data = {
            "id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en"
        }
        
        mock_new_user = User(
            id=1,
            telegram_id="123456789",
            telegram_username="testuser",
            is_active=True
        )
        
        with patch('app.services.telegram_bot.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_user_by_telegram_id.return_value = None  # User doesn't exist
            mock_repo.create_telegram_user.return_value = mock_new_user
            mock_repo_class.return_value = mock_repo
            
            result = await bot.register_user(user_data)
            
            # Check new user was created
            mock_repo.create_telegram_user.assert_called_once_with(user_data)
            assert result == mock_new_user
    
    @pytest.mark.asyncio
    @patch('app.services.telegram_bot.SessionLocal')
    async def test_register_user_existing_user(self, mock_session, bot):
        """测试用户注册 - 已存在用户"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        user_data = {
            "id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en"
        }
        
        mock_existing_user = User(
            id=1,
            telegram_id="123456789",
            telegram_username="testuser",
            is_active=True
        )
        
        with patch('app.services.telegram_bot.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_user_by_telegram_id.return_value = mock_existing_user
            mock_repo.update_user_activity.return_value = None
            mock_repo_class.return_value = mock_repo
            
            result = await bot.register_user(user_data)
            
            # Check existing user was returned and activity updated
            mock_repo.update_user_activity.assert_called_once_with(mock_existing_user.id)
            assert result == mock_existing_user

    @pytest.mark.asyncio
    async def test_send_news_alert_success(self, bot):
        """测试发送新闻推送成功"""
        news_item = {
            'title': 'Test News',
            'content': 'Test content',
            'url': 'https://example.com',
            'source': 'TestSource',
            'is_urgent': True,
            'importance_score': 4
        }
        
        with patch.object(bot.bot, 'send_message') as mock_send:
            await bot.send_news_alert(['user1', 'user2'], news_item)
        
        assert mock_send.call_count == 2
        
        # 检查消息格式
        call_args = mock_send.call_args_list[0]
        assert call_args[1]['chat_id'] == 'user1'
        assert call_args[1]['parse_mode'] == 'HTML'
        assert 'Test News' in call_args[1]['text']

    @pytest.mark.asyncio
    async def test_send_news_alert_failure(self, bot):
        """测试发送新闻推送失败"""
        news_item = {
            'title': 'Test News',
            'content': 'Test content',
            'url': 'https://example.com',
            'source': 'TestSource'
        }
        
        with patch.object(bot.bot, 'send_message', side_effect=Exception("Send failed")), \
             patch('builtins.print') as mock_print:
            await bot.send_news_alert(['user1'], news_item)
        
        mock_print.assert_called_with("Failed to send message to user1: Send failed")

    def test_format_news_message_urgent(self, bot):
        """测试格式化紧急新闻消息"""
        news_item = {
            'title': 'Urgent Bitcoin News',
            'content': 'Very important content that is longer than 200 characters and should be truncated to ensure the message is not too long for Telegram',
            'url': 'https://example.com/btc',
            'source': 'CoinDesk',
            'category': 'bitcoin',
            'is_urgent': True,
            'importance_score': 5,
            'published_at': '2024-01-01 12:00:00'
        }
        
        result = bot.format_news_message(news_item)
        
        assert "🚨" in result  # 紧急新闻emoji
        assert "Urgent Bitcoin News" in result
        assert "⭐⭐⭐⭐⭐" in result  # 5星重要度
        assert "CoinDesk" in result
        assert "bitcoin" in result
        assert len(result.split('\n\n')[4]) <= 203  # 内容被截断

    def test_format_news_message_normal(self, bot):
        """测试格式化普通新闻消息"""
        news_item = {
            'title': 'Regular Crypto News',
            'content': 'Regular content',
            'url': 'https://example.com/crypto',
            'source': 'CryptoNews',
            'category': 'general',
            'is_urgent': False,
            'importance_score': 2
        }
        
        result = bot.format_news_message(news_item)
        
        assert "📰" in result  # 普通新闻emoji
        assert "Regular Crypto News" in result
        assert "⭐⭐" in result  # 2星重要度

    def test_format_news_message_missing_fields(self, bot):
        """测试缺少字段的新闻格式化"""
        news_item = {
            'title': 'News Without Details',
            'content': 'Basic content',
            'url': 'https://example.com',
            'source': 'Unknown'
        }
        
        result = bot.format_news_message(news_item)
        
        assert "📰" in result  # 默认非紧急
        assert "⭐" in result  # 默认重要度1
        assert "general" in result  # 默认分类