import pytest
from app.services.ai_analyzer import AINewsAnalyzer
from unittest.mock import patch, AsyncMock, MagicMock
import json

@pytest.mark.asyncio
async def test_ai_analyzer_init_with_key():
    """Test AI analyzer initialization with API key"""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        
        analyzer = AINewsAnalyzer("test_api_key")
        assert analyzer.client is not None

@pytest.mark.asyncio
async def test_ai_analyzer_analyze_news():
    """Test comprehensive news analysis"""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        
        # Mock responses for different analysis tasks
        mock_client.chat.completions.create.side_effect = [
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content="Test summary"))]),
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content="0.5"))]),
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content='{"tokens": ["BTC"], "prices": ["50000"]}'))])
        ]
        
        analyzer = AINewsAnalyzer("test_key")
        news_item = {
            'title': 'Bitcoin reaches new high',
            'content': 'Bitcoin price surged to $50,000 today amid regulatory news'
        }
        
        result = await analyzer.analyze_news(news_item)
        assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_generate_summary():
    """Test summary generation"""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="Generated summary"))]
        )
        
        analyzer = AINewsAnalyzer("test_key")
        summary = await analyzer.generate_summary("Long news content here")
        assert summary == "Generated summary"

@pytest.mark.asyncio
async def test_analyze_sentiment():
    """Test sentiment analysis"""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="0.8"))]
        )
        
        analyzer = AINewsAnalyzer("test_key")
        sentiment = await analyzer.analyze_sentiment("Positive news content")
        assert sentiment == 0.8

@pytest.mark.asyncio 
async def test_extract_key_information():
    """Test key information extraction"""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content='{"tokens": ["BTC", "ETH"], "prices": ["50000", "3000"]}'))]
        )
        
        analyzer = AINewsAnalyzer("test_key")
        info = await analyzer.extract_key_information("Bitcoin and Ethereum prices")
        assert isinstance(info, dict)
        assert "tokens" in info
        assert "prices" in info

@pytest.mark.asyncio
async def test_calculate_market_impact():
    """Test market impact calculation"""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="4"))]
        )
        
        analyzer = AINewsAnalyzer("test_key")
        impact = await analyzer.calculate_market_impact("Major regulatory news")
        assert impact == 4

def test_extract_crypto_tokens():
    """Test crypto token extraction from text"""
    analyzer = AINewsAnalyzer()
    
    text1 = "Bitcoin and Ethereum are leading cryptocurrencies"
    tokens1 = analyzer.extract_crypto_tokens(text1)
    assert "bitcoin" in tokens1 or "ethereum" in tokens1
    
    text2 = "No crypto mentions here"
    tokens2 = analyzer.extract_crypto_tokens(text2)
    assert isinstance(tokens2, list)

def test_extract_price_mentions():
    """Test price mention extraction"""
    analyzer = AINewsAnalyzer()
    
    text1 = "Bitcoin reached $50,000 and Ethereum hit $3,000"
    prices1 = analyzer.extract_price_mentions(text1)
    assert "$50,000" in prices1 or "$3,000" in prices1
    
    text2 = "No prices mentioned"
    prices2 = analyzer.extract_price_mentions(text2)
    assert isinstance(prices2, list)

def test_calculate_urgency_score():
    """Test urgency score calculation"""
    analyzer = AINewsAnalyzer()
    
    urgent_news = {
        'title': 'BREAKING: SEC announces new regulations',
        'content': 'Urgent regulatory announcement affecting cryptocurrency markets'
    }
    
    normal_news = {
        'title': 'Daily market update',
        'content': 'Regular market analysis and trends'
    }
    
    urgent_score = analyzer.calculate_urgency_score(urgent_news)
    normal_score = analyzer.calculate_urgency_score(normal_news)
    
    assert isinstance(urgent_score, (int, float))
    assert isinstance(normal_score, (int, float))
    assert urgent_score >= normal_score

def test_detect_market_events():
    """Test market event detection"""
    analyzer = AINewsAnalyzer()
    
    event_news = {
        'title': 'Bitcoin ETF approved by SEC',
        'content': 'Major approval for cryptocurrency exchange-traded fund'
    }
    
    regular_news = {
        'title': 'Market analysis',
        'content': 'Daily price movements and trends'
    }
    
    events1 = analyzer.detect_market_events(event_news)
    events2 = analyzer.detect_market_events(regular_news)
    
    assert isinstance(events1, list)
    assert isinstance(events2, list)

def test_categorize_news():
    """Test news categorization"""
    analyzer = AINewsAnalyzer()
    
    test_cases = [
        {"content": "Bitcoin blockchain technology", "expected_contains": "bitcoin"},
        {"content": "Ethereum smart contracts", "expected_contains": "ethereum"},
        {"content": "DeFi protocol launch", "expected_contains": "defi"},
        {"content": "NFT marketplace", "expected_contains": "nft"}
    ]
    
    for case in test_cases:
        category = analyzer.categorize_news(case["content"])
        assert isinstance(category, str)
        assert len(category) > 0