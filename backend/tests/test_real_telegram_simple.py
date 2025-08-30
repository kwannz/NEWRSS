import pytest
import os
from app.services.telegram_notifier import TelegramNotifier
from app.services.telegram_webhook import telegram_lifespan

@pytest.mark.asyncio
async def test_real_telegram_notifier_init():
    """Test TelegramNotifier initialization"""
    notifier = TelegramNotifier()
    
    # Should initialize successfully
    assert notifier is not None

@pytest.mark.asyncio
async def test_real_telegram_notifier_without_token():
    """Test TelegramNotifier methods without token"""
    # Remove token temporarily
    original_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if original_token:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    
    try:
        notifier = TelegramNotifier()
        
        # Test urgent notification
        news_item = {
            "title": "Test Urgent News",
            "content": "Test urgent content",
            "url": "https://test.com/urgent",
            "importance_score": 5,
            "category": "bitcoin"
        }
        
        # Should handle missing token gracefully
        result = await notifier.send_urgent_notification("123456", news_item)
        # Should not crash, might return None or handle error gracefully
        
        # Test daily digest
        news_items = [news_item]
        result = await notifier.send_daily_digest("123456", news_items)
        # Should not crash
        
    finally:
        # Restore token
        if original_token:
            os.environ["TELEGRAM_BOT_TOKEN"] = original_token

@pytest.mark.asyncio
async def test_real_telegram_lifespan():
    """Test telegram lifespan context manager"""
    # Test without token
    original_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if original_token:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    
    try:
        async with telegram_lifespan():
            # Should complete without errors
            pass
    finally:
        if original_token:
            os.environ["TELEGRAM_BOT_TOKEN"] = original_token

@pytest.mark.asyncio
async def test_real_telegram_lifespan_with_token():
    """Test telegram lifespan with fake token"""
    original_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    os.environ["TELEGRAM_BOT_TOKEN"] = "fake123:test_token"
    
    try:
        async with telegram_lifespan():
            # Should handle setup even with fake token
            pass
    finally:
        if original_token:
            os.environ["TELEGRAM_BOT_TOKEN"] = original_token
        else:
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)

@pytest.mark.asyncio
async def test_real_telegram_message_formatting():
    """Test telegram message formatting logic"""
    notifier = TelegramNotifier()
    
    # Test with various news items
    news_items = [
        {
            "title": "Bitcoin Reaches $100K",
            "content": "Bitcoin price surges to unprecedented levels",
            "url": "https://example.com/btc-100k",
            "importance_score": 5,
            "category": "bitcoin",
            "source": "CoinDesk"
        },
        {
            "title": "Ethereum Update",
            "content": "Ethereum network upgrade successful",
            "url": "https://example.com/eth-update",
            "importance_score": 3,
            "category": "ethereum"
        },
        {
            "title": "DeFi Protocol Launch", 
            "content": "New DeFi protocol launches with innovative features",
            "url": "https://example.com/defi-launch",
            "importance_score": 4,
            "category": "defi"
        }
    ]
    
    # Test individual urgent notifications (should not crash)
    for item in news_items:
        try:
            await notifier.send_urgent_notification("123456", item)
        except Exception as e:
            # Expected to fail without real token, but should not crash due to formatting
            assert "telegram" in str(e).lower() or "token" in str(e).lower() or "bot" in str(e).lower()
    
    # Test daily digest with multiple items
    try:
        await notifier.send_daily_digest("123456", news_items)
    except Exception as e:
        # Expected to fail without real token
        assert "telegram" in str(e).lower() or "token" in str(e).lower() or "bot" in str(e).lower()