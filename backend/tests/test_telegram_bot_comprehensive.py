import pytest
from app.services.telegram_bot import TelegramBot
from unittest.mock import patch, AsyncMock, MagicMock
from telegram import Bot, Update, Message, Chat, User as TelegramUser

@pytest.mark.asyncio
async def test_telegram_bot_initialization():
    """Test telegram bot initialization with various scenarios"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token_123")
        assert bot.bot is not None
        assert bot.app is not None

@pytest.mark.asyncio
async def test_telegram_bot_setup_handlers():
    """Test handler setup"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app
            
            bot = TelegramBot("test_token")
            bot.setup_handlers()
            
            # Verify handlers were added
            assert mock_app.add_handler.called

@pytest.mark.asyncio
async def test_telegram_bot_start_command():
    """Test start command handler"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        # Mock update and context
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        await bot.start_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_bot_help_command():
    """Test help command handler"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        await bot.help_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_bot_subscribe_command():
    """Test subscribe command handler"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["bitcoin"]
        
        await bot.subscribe_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_bot_unsubscribe_command():
    """Test unsubscribe command handler"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["bitcoin"]
        
        await bot.unsubscribe_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_bot_status_command():
    """Test status command handler"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        await bot.status_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_bot_news_command():
    """Test news command handler"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context.args = ["5"]
        
        await bot.news_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_bot_send_news_alert():
    """Test sending news alerts"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        user_ids = ["123456", "789012"]
        news_item = {
            'title': 'Breaking News',
            'content': 'Important update',
            'url': 'https://example.com',
            'source': 'Test Source'
        }
        
        await bot.send_news_alert(user_ids, news_item)
        
        # Should send message to each user
        assert mock_bot.send_message.call_count == len(user_ids)

@pytest.mark.asyncio
async def test_telegram_bot_send_daily_digest():
    """Test sending daily digest"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        user_ids = ["123456"]
        news_items = [
            {
                'title': 'News 1',
                'source': 'Source 1',
                'url': 'https://example.com/1',
                'importance_score': 4
            },
            {
                'title': 'News 2', 
                'source': 'Source 2',
                'url': 'https://example.com/2',
                'importance_score': 3
            }
        ]
        
        await bot.send_daily_digest(user_ids, news_items)
        mock_bot.send_message.assert_called_once()

def test_telegram_bot_format_news_alert():
    """Test news alert formatting"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        news_item = {
            'title': 'Alert News',
            'content': 'Alert content',
            'source': 'Alert Source',
            'url': 'https://alert.com',
            'importance_score': 5
        }
        
        formatted = bot.format_news_alert(news_item)
        assert isinstance(formatted, str)
        assert 'Alert News' in formatted
        assert 'Alert Source' in formatted

def test_telegram_bot_format_daily_digest():
    """Test daily digest formatting"""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        
        bot = TelegramBot("test_token")
        
        news_items = [
            {
                'title': 'Digest News 1',
                'source': 'Source 1',
                'url': 'https://example.com/1',
                'importance_score': 4
            }
        ]
        
        formatted = bot.format_daily_digest(news_items)
        assert isinstance(formatted, str)
        assert 'Digest News 1' in formatted