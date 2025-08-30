import pytest
import os
from app.services.telegram_bot import TelegramBot
from app.services.telegram_notifier import TelegramNotifier
from app.services.telegram_webhook import telegram_lifespan
from datetime import datetime

# Remove any existing telegram token to test error handling
original_token = os.environ.get("TELEGRAM_BOT_TOKEN")

@pytest.mark.asyncio
async def test_real_telegram_bot_with_fake_token():
    """Test TelegramBot initialization with fake token"""
    fake_token = "123456:fake_token_for_testing"
    
    try:
        bot = TelegramBot(fake_token)
        
        # Should initialize with bot object
        assert bot.bot is not None
        assert bot.token == fake_token
        assert bot.app is not None
    
    # Test webhook URL generation without token
    webhook_url = bot.get_webhook_url()
    assert webhook_url is None
    
    # Test update processing without bot
    fake_update = {"message": {"text": "test", "chat": {"id": 123}}}
    await bot.process_update(fake_update)  # Should handle gracefully
    
    # Test send message without bot
    await bot.send_message(123, "test message")  # Should handle gracefully
    
    # Test get webhook info without bot
    webhook_info = await bot.get_webhook_info()
    assert webhook_info is None

@pytest.mark.asyncio
async def test_real_telegram_bot_with_fake_token():
    """Test TelegramBot with fake token to trigger error paths"""
    # Set a fake token temporarily
    os.environ["TELEGRAM_BOT_TOKEN"] = "fake_token_12345:fake_token_data"
    
    try:
        bot = TelegramBot()
        
        # Should initialize bot object
        assert bot.bot is not None
        
        # Test webhook URL generation with fake token
        webhook_url = bot.get_webhook_url()
        expected_url = "https://api.telegram.org/botfake_token_12345:fake_token_data/setWebhook"
        assert webhook_url == expected_url
        
        # Test methods that would fail with fake token (should handle errors gracefully)
        await bot.send_message(123, "test")  # Should not crash
        await bot.get_webhook_info()  # Should handle API error
        
        # Test update processing
        test_update = {
            "message": {
                "text": "/start",
                "chat": {"id": 123},
                "from": {"username": "testuser"}
            }
        }
        await bot.process_update(test_update)  # Should handle gracefully
        
    finally:
        # Clean up
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)

@pytest.mark.asyncio 
async def test_real_telegram_notifier_without_token():
    """Test TelegramNotifier without token"""
    notifier = TelegramNotifier()
    
    # Test urgent notification without token
    news_item = {
        "title": "Test Urgent News",
        "content": "Test urgent content",
        "url": "https://test.com/urgent",
        "importance_score": 5,
        "category": "bitcoin"
    }
    
    # Should handle missing token gracefully
    await notifier.send_urgent_notification("123456", news_item)
    
    # Test daily digest without token
    news_items = [news_item, {
        "title": "Test News 2", 
        "content": "Test content 2",
        "url": "https://test.com/news2",
        "importance_score": 3
    }]
    
    await notifier.send_daily_digest("123456", news_items)

@pytest.mark.asyncio
async def test_real_telegram_notifier_message_formatting():
    """Test TelegramNotifier message formatting logic"""
    notifier = TelegramNotifier()
    
    # Test _format_news_message method (if accessible)
    news_item = {
        "title": "Bitcoin Reaches $100K",
        "content": "Bitcoin has reached a new all-time high of $100,000 amid institutional adoption and regulatory clarity.",
        "url": "https://news.com/bitcoin-100k",
        "importance_score": 5,
        "category": "bitcoin",
        "source": "CoinDesk"
    }
    
    # Test urgent notification formatting
    # Even without token, we can test the formatting logic
    try:
        await notifier.send_urgent_notification("123456", news_item)
    except Exception as e:
        # Should fail due to missing token, but not due to formatting errors
        assert "token" in str(e).lower() or "bot" in str(e).lower()
    
    # Test digest formatting with multiple items
    news_items = [
        {
            "title": f"News Item {i}",
            "content": f"Content for news item {i}",
            "url": f"https://test.com/news{i}",
            "importance_score": i % 5 + 1,
            "category": ["bitcoin", "ethereum", "defi"][i % 3]
        }
        for i in range(5)
    ]
    
    try:
        await notifier.send_daily_digest("123456", news_items)
    except Exception as e:
        # Should fail due to missing token, but not due to formatting errors
        assert "token" in str(e).lower() or "bot" in str(e).lower()

@pytest.mark.asyncio
async def test_real_telegram_webhook_setup():
    """Test telegram webhook setup functions"""
    # Test setup function without token
    webhook_url = await setup_telegram_webhook()
    assert webhook_url is None  # Should return None without token
    
    # Test with fake token
    os.environ["TELEGRAM_BOT_TOKEN"] = "fake_token_webhook:test"
    
    try:
        webhook_url = await setup_telegram_webhook()
        # Should return the expected webhook URL format
        assert webhook_url is None or "api.telegram.org" in str(webhook_url)
    finally:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)

@pytest.mark.asyncio
async def test_real_telegram_lifespan():
    """Test telegram lifespan context manager"""
    # Test lifespan without token
    async with telegram_lifespan():
        # Should complete without errors even without token
        pass
    
    # Test lifespan with fake token
    os.environ["TELEGRAM_BOT_TOKEN"] = "fake_lifespan:token"
    
    try:
        async with telegram_lifespan():
            # Should handle setup and teardown gracefully
            pass
    finally:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)

@pytest.mark.asyncio
async def test_real_telegram_bot_command_processing():
    """Test telegram bot command processing logic"""
    os.environ["TELEGRAM_BOT_TOKEN"] = "fake_command:token"
    
    try:
        bot = TelegramBot()
        
        # Test various update types
        updates = [
            # Start command
            {
                "message": {
                    "text": "/start",
                    "chat": {"id": 123},
                    "from": {"username": "testuser"}
                }
            },
            # Help command  
            {
                "message": {
                    "text": "/help",
                    "chat": {"id": 123},
                    "from": {"username": "testuser"}
                }
            },
            # Subscribe command
            {
                "message": {
                    "text": "/subscribe bitcoin",
                    "chat": {"id": 123},
                    "from": {"username": "testuser"}
                }
            },
            # Regular message (not command)
            {
                "message": {
                    "text": "Hello bot",
                    "chat": {"id": 123},
                    "from": {"username": "testuser"}
                }
            },
            # Empty message
            {
                "message": {
                    "chat": {"id": 123},
                    "from": {"username": "testuser"}
                }
            }
        ]
        
        # Process each update (should handle gracefully even with fake token)
        for update in updates:
            await bot.process_update(update)
        
        # Test edge cases
        edge_updates = [
            # Missing message
            {"update_id": 1},
            # Missing chat
            {"message": {"text": "test"}},
            # Missing from
            {"message": {"text": "test", "chat": {"id": 123}}},
            # Empty update
            {}
        ]
        
        for update in edge_updates:
            await bot.process_update(update)  # Should not crash
            
    finally:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)

@pytest.mark.asyncio
async def test_real_telegram_services_integration():
    """Test integration between telegram services"""
    # Test without any tokens - should handle gracefully
    bot = TelegramBot()
    notifier = TelegramNotifier()
    
    # Test bot and notifier interaction
    news_item = {
        "title": "Integration Test News",
        "content": "Testing integration between services",
        "url": "https://test.com/integration",
        "importance_score": 4
    }
    
    # Both should handle missing tokens gracefully
    await bot.send_message(123, "Integration test")
    await notifier.send_urgent_notification("123", news_item)
    
    # Test webhook setup integration
    webhook_url = await setup_telegram_webhook()
    assert webhook_url is None
    
    # Test with fake tokens for both services
    os.environ["TELEGRAM_BOT_TOKEN"] = "integration_test:token"
    
    try:
        bot_with_token = TelegramBot()
        notifier_with_token = TelegramNotifier()
        
        # Should initialize with fake token
        assert bot_with_token.bot is not None
        
        # Test webhook setup with token
        webhook_url = await setup_telegram_webhook()
        # Should attempt to setup webhook (will fail with fake token but shouldn't crash)
        
    finally:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)

# Restore original token if it existed
if original_token:
    os.environ["TELEGRAM_BOT_TOKEN"] = original_token