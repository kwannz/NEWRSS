import pytest
from app.core.auth import get_password_hash, verify_password, create_access_token, verify_token
from app.core.database import get_db
from app.core.redis import redis_client
from app.models.user import User
from app.models.news import NewsItem  
from app.models.subscription import UserSubscription, UserCategory
from app.api.auth import UserCreate, UserResponse, Token
from app.api.news import NewsItemResponse
from app.services.telegram_bot import TelegramBot
from app.services.telegram_notifier import TelegramNotifier
from app.services.telegram_webhook import telegram_lifespan, router
from app.tasks.news_crawler import is_urgent_news, calculate_importance, celery_app
from datetime import datetime
from unittest.mock import patch, MagicMock

def test_password_hashing():
    """Test password hashing and verification"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_token_operations():
    """Test JWT token creation and verification"""
    token = create_access_token({"sub": "testuser"})
    assert isinstance(token, str)
    assert len(token) > 0
    
    username = verify_token(token)
    assert username == "testuser"

def test_user_model_attributes():
    """Test User model has all required attributes"""
    user = User()
    assert hasattr(user, 'id')
    assert hasattr(user, 'username')
    assert hasattr(user, 'email')
    assert hasattr(user, 'hashed_password')
    assert hasattr(user, 'is_active')
    assert hasattr(user, 'telegram_id')

def test_news_model_attributes():
    """Test NewsItem model has all required attributes"""
    news = NewsItem()
    assert hasattr(news, 'id')
    assert hasattr(news, 'title')
    assert hasattr(news, 'content')
    assert hasattr(news, 'url')
    assert hasattr(news, 'source')
    assert hasattr(news, 'category')
    assert hasattr(news, 'importance_score')

def test_subscription_model_attributes():
    """Test subscription models have required attributes"""
    subscription = UserSubscription()
    assert hasattr(subscription, 'id')
    assert hasattr(subscription, 'user_id')
    assert hasattr(subscription, 'source_id')
    assert hasattr(subscription, 'is_active')
    
    category = UserCategory()
    assert hasattr(category, 'id')
    assert hasattr(category, 'user_id')
    assert hasattr(category, 'category')
    assert hasattr(category, 'is_subscribed')

def test_pydantic_models():
    """Test Pydantic model instantiation"""
    user_create = UserCreate(username="test", email="test@example.com", password="pass123")
    assert user_create.username == "test"
    
    user_response = UserResponse(id=1, username="test", email="test@example.com", is_active=True)
    assert user_response.id == 1
    
    token = Token(access_token="token123", token_type="bearer")
    assert token.access_token == "token123"

def test_news_urgency_detection():
    """Test news urgency detection function"""
    urgent_keywords = ['breaking', 'urgent', 'sec', 'hack', 'pump']
    
    for keyword in urgent_keywords:
        item = {'title': f'News with {keyword}', 'content': 'test content'}
        assert is_urgent_news(item) is True
    
    normal_item = {'title': 'Regular news', 'content': 'normal content'}
    assert is_urgent_news(normal_item) is False

def test_importance_calculation():
    """Test news importance scoring"""
    high_item = {
        'title': 'SEC regulation announcement',
        'content': 'federal regulation news',
        'source': 'sec.gov'
    }
    
    medium_item = {
        'title': 'Partnership announcement',
        'content': 'company partnership',
        'source': 'company.com'
    }
    
    low_item = {
        'title': 'Daily update',
        'content': 'regular update',
        'source': 'blog.com'
    }
    
    high_score = calculate_importance(high_item)
    medium_score = calculate_importance(medium_item)
    low_score = calculate_importance(low_item)
    
    assert 1 <= high_score <= 5
    assert 1 <= medium_score <= 5
    assert 1 <= low_score <= 5
    assert high_score >= medium_score >= low_score

@patch('app.services.telegram_bot.settings.TELEGRAM_BOT_TOKEN', 'mock_token')
def test_telegram_bot_mock():
    """Test telegram bot with mocked token"""
    with patch('telegram.Bot') as mock_bot:
        mock_bot.return_value = MagicMock()
        bot = TelegramBot('mock_token')
        assert bot is not None
        assert hasattr(bot, 'bot')

def test_telegram_notifier_format():
    """Test telegram notifier digest formatting without token"""
    with patch('app.services.telegram_notifier.settings.TELEGRAM_BOT_TOKEN', 'mock_token'):
        with patch('telegram.Bot'):
            notifier = TelegramNotifier()
            
            test_items = [
                {
                    'title': 'Test News',
                    'source': 'Test Source',
                    'importance_score': 3,
                    'url': 'https://example.com'
                }
            ]
            
            digest = notifier.format_daily_digest(test_items)
            assert isinstance(digest, str)
            assert 'Test News' in digest

def test_celery_app_configuration():
    """Test Celery app is properly configured"""
    assert celery_app is not None
    assert hasattr(celery_app, 'conf')
    assert hasattr(celery_app.conf, 'beat_schedule')
    assert 'crawl-news-every-30-seconds' in celery_app.conf.beat_schedule

@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection function exists"""
    db_gen = get_db()
    assert db_gen is not None