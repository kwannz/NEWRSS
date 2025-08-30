import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.telegram_bot import TelegramBot

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
    async def test_start_command(self, bot, mock_update):
        """测试/start命令处理"""
        with patch.object(bot, 'register_user') as mock_register:
            await bot.start_command(mock_update, None)
        
        mock_register.assert_called_once_with(12345, "testuser")
        mock_update.message.reply_text.assert_called_once()
        
        # 检查回复消息内容
        args, kwargs = mock_update.message.reply_text.call_args
        assert "欢迎使用 NEWRSS" in args[0]
        assert "reply_markup" in kwargs

    @pytest.mark.asyncio
    async def test_subscribe_command(self, bot, mock_update):
        """测试/subscribe命令处理"""
        await bot.subscribe_command(mock_update, None)
        
        mock_update.message.reply_text.assert_called_once()
        args, _ = mock_update.message.reply_text.call_args
        assert "已订阅新闻推送" in args[0]

    @pytest.mark.asyncio
    async def test_unsubscribe_command(self, bot, mock_update):
        """测试/unsubscribe命令处理"""
        await bot.unsubscribe_command(mock_update, None)
        
        mock_update.message.reply_text.assert_called_once()
        args, _ = mock_update.message.reply_text.call_args
        assert "已取消订阅" in args[0]

    @pytest.mark.asyncio
    async def test_settings_command(self, bot, mock_update):
        """测试/settings命令处理"""
        await bot.settings_command(mock_update, None)
        
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "推送设置" in args[0]
        assert "reply_markup" in kwargs

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
    async def test_register_user(self, bot):
        """测试用户注册"""
        with patch('builtins.print') as mock_print:
            await bot.register_user(12345, "testuser")
        
        mock_print.assert_called_with("Registering user: 12345 (@testuser)")

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