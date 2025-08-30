import pytest
from httpx import AsyncClient
from app.main import app
from app.services.telegram_webhook import router, telegram_lifespan
from unittest.mock import patch, AsyncMock, MagicMock
import json

@pytest.mark.asyncio
async def test_telegram_webhook_endpoint():
    """Test telegram webhook endpoint"""
    with patch('app.services.telegram_webhook.settings.TELEGRAM_SECRET_TOKEN', 'test_secret'):
        with patch('app.services.telegram_webhook.telegram_app') as mock_app:
            mock_app.process_update = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test valid webhook call
                webhook_data = {
                    "update_id": 123,
                    "message": {
                        "message_id": 1,
                        "date": 1234567890,
                        "chat": {"id": 123, "type": "private"},
                        "text": "test message"
                    }
                }
                
                response = await client.post(
                    "/telegram/webhook",
                    json=webhook_data,
                    headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"}
                )
                assert response.status_code == 200
                assert response.json() == {"ok": True}

@pytest.mark.asyncio
async def test_telegram_webhook_invalid_secret():
    """Test webhook with invalid secret token"""
    with patch('app.services.telegram_webhook.settings.TELEGRAM_SECRET_TOKEN', 'correct_secret'):
        async with AsyncClient(app=app, base_url="http://test") as client:
            webhook_data = {"update_id": 123}
            
            response = await client.post(
                "/telegram/webhook",
                json=webhook_data,
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"}
            )
            assert response.status_code == 401

@pytest.mark.asyncio
async def test_telegram_webhook_no_secret():
    """Test webhook without secret token when required"""
    with patch('app.services.telegram_webhook.settings.TELEGRAM_SECRET_TOKEN', 'required_secret'):
        async with AsyncClient(app=app, base_url="http://test") as client:
            webhook_data = {"update_id": 123}
            
            response = await client.post("/telegram/webhook", json=webhook_data)
            assert response.status_code == 401

@pytest.mark.asyncio
async def test_telegram_webhook_no_app():
    """Test webhook when telegram app not initialized"""
    with patch('app.services.telegram_webhook.telegram_app', None):
        async with AsyncClient(app=app, base_url="http://test") as client:
            webhook_data = {"update_id": 123}
            
            response = await client.post("/telegram/webhook", json=webhook_data)
            assert response.status_code == 503

@pytest.mark.asyncio
async def test_telegram_lifespan_with_token():
    """Test telegram lifespan with valid token"""
    with patch('app.services.telegram_webhook.settings.TELEGRAM_BOT_TOKEN', 'test_token'):
        with patch('app.services.telegram_webhook.settings.TELEGRAM_WEBHOOK_URL', 'https://example.com/webhook'):
            with patch('app.services.telegram_webhook.settings.TELEGRAM_SECRET_TOKEN', 'secret'):
                with patch('app.services.telegram_webhook.TelegramBot') as mock_bot_class:
                    mock_bot = MagicMock()
                    mock_app = AsyncMock()
                    mock_bot.app = mock_app
                    mock_bot_class.return_value = mock_bot
                    
                    mock_app.initialize = AsyncMock()
                    mock_app.start = AsyncMock()
                    mock_app.bot.set_webhook = AsyncMock()
                    mock_app.stop = AsyncMock()
                    mock_app.shutdown = AsyncMock()
                    
                    async with telegram_lifespan():
                        mock_app.initialize.assert_called_once()
                        mock_app.start.assert_called_once()
                        mock_app.bot.set_webhook.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_lifespan_no_token():
    """Test telegram lifespan without token"""
    with patch('app.services.telegram_webhook.settings.TELEGRAM_BOT_TOKEN', None):
        async with telegram_lifespan():
            # Should complete without error
            assert True

@pytest.mark.asyncio
async def test_telegram_webhook_processing_error():
    """Test webhook error handling"""
    with patch('app.services.telegram_webhook.settings.TELEGRAM_SECRET_TOKEN', 'test_secret'):
        with patch('app.services.telegram_webhook.telegram_app') as mock_app:
            mock_app.process_update = AsyncMock(side_effect=Exception("Processing error"))
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                webhook_data = {"update_id": 123}
                
                response = await client.post(
                    "/telegram/webhook",
                    json=webhook_data,
                    headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"}
                )
                assert response.status_code == 500