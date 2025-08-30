import pytest
from app.services.telegram_notifier import TelegramNotifier
from app.services.telegram_webhook import telegram_lifespan
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_telegram_notifier_simple():
    """Test basic telegram notifier functionality"""
    notifier = TelegramNotifier()
    assert notifier is not None
    assert hasattr(notifier, 'bot')

@pytest.mark.asyncio 
async def test_telegram_notifier_methods():
    """Test telegram notifier methods exist"""
    notifier = TelegramNotifier()
    assert hasattr(notifier, 'notify_urgent_news')
    assert hasattr(notifier, 'send_daily_digest')
    assert hasattr(notifier, 'get_subscribed_user_ids')
    assert hasattr(notifier, 'format_daily_digest')

@pytest.mark.asyncio
async def test_telegram_format_daily_digest():
    """Test daily digest formatting"""
    notifier = TelegramNotifier()
    
    test_items = [
        {
            'title': 'Bitcoin News',
            'source': 'CoinDesk',
            'importance_score': 5,
            'url': 'https://example.com/news1'
        },
        {
            'title': 'Ethereum Update',
            'source': 'CoinTelegraph', 
            'importance_score': 3,
            'url': 'https://example.com/news2'
        }
    ]
    
    digest = notifier.format_daily_digest(test_items)
    assert isinstance(digest, str)
    assert 'Bitcoin News' in digest
    assert 'Ethereum Update' in digest
    assert 'CoinDesk' in digest
    assert '📊' in digest

@pytest.mark.asyncio
async def test_telegram_get_subscribed_users():
    """Test get subscribed users returns list"""
    notifier = TelegramNotifier()
    user_ids = await notifier.get_subscribed_user_ids()
    assert isinstance(user_ids, list)

@pytest.mark.asyncio
async def test_telegram_lifespan_context():
    """Test telegram lifespan context manager"""
    async with telegram_lifespan():
        assert True

@pytest.mark.asyncio
async def test_telegram_webhook_router_exists():
    """Test telegram webhook router is available"""
    from app.services.telegram_webhook import router
    assert router is not None
    assert hasattr(router, 'routes')