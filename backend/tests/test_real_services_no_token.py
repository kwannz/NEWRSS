import pytest
from unittest.mock import patch, MagicMock
from app.services.telegram_bot import TelegramBot
from app.services.rss_fetcher import RSSFetcher
from app.services.ai_analyzer import AINewsAnalyzer
from app.tasks.news_crawler import is_urgent_news, calculate_importance

@pytest.mark.asyncio
async def test_rss_fetcher_initialization():
    """Test RSS fetcher can be initialized"""
    async with RSSFetcher() as fetcher:
        assert fetcher is not None
        assert hasattr(fetcher, 'session')

@pytest.mark.asyncio
async def test_ai_analyzer_initialization():
    """Test AI analyzer can be initialized"""
    analyzer = AINewsAnalyzer()
    assert analyzer is not None
    assert hasattr(analyzer, 'client')

def test_is_urgent_news_function():
    """Test urgent news detection function"""
    urgent_item = {
        'title': 'BREAKING: SEC Approves Bitcoin ETF',
        'content': 'Urgent news about regulation'
    }
    
    normal_item = {
        'title': 'Daily Market Update',
        'content': 'Regular market analysis'
    }
    
    assert is_urgent_news(urgent_item) is True
    assert is_urgent_news(normal_item) is False

def test_calculate_importance_function():
    """Test importance calculation function"""
    high_importance = {
        'title': 'SEC Regulation Update',
        'content': 'Federal regulation news',
        'source': 'sec.gov'
    }
    
    low_importance = {
        'title': 'Daily Update',
        'content': 'Regular news',
        'source': 'blog.example.com'
    }
    
    high_score = calculate_importance(high_importance)
    low_score = calculate_importance(low_importance)
    
    assert isinstance(high_score, int)
    assert isinstance(low_score, int)
    assert 1 <= high_score <= 5
    assert 1 <= low_score <= 5
    assert high_score >= low_score

@patch('app.services.telegram_bot.settings.TELEGRAM_BOT_TOKEN', 'test_token')
def test_telegram_bot_with_token():
    """Test telegram bot with mocked token"""
    with patch('telegram.Bot') as mock_bot:
        mock_bot.return_value = MagicMock()
        bot = TelegramBot('test_token')
        assert bot is not None

@pytest.mark.asyncio
async def test_ai_analyzer_methods_exist():
    """Test AI analyzer methods exist"""
    analyzer = AINewsAnalyzer()
    assert hasattr(analyzer, 'analyze_news')
    assert hasattr(analyzer, 'extract_key_information')
    assert hasattr(analyzer, 'calculate_market_impact')
    assert hasattr(analyzer, 'analyze_sentiment')

@pytest.mark.asyncio
async def test_rss_fetcher_methods_exist():
    """Test RSS fetcher methods exist"""
    async with RSSFetcher() as fetcher:
        assert hasattr(fetcher, 'fetch_feed')
        assert hasattr(fetcher, 'fetch_multiple_feeds')
        assert hasattr(fetcher, 'is_duplicate')
        assert hasattr(fetcher, 'process_feed_entry')