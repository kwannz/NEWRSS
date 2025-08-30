import pytest
from unittest.mock import AsyncMock, patch
from app.services.ai_analyzer import AINewsAnalyzer

class TestAINewsAnalyzer:
    
    @pytest.fixture
    def analyzer(self):
        """创建测试分析器实例"""
        return AINewsAnalyzer("test_api_key")
    
    @pytest.fixture
    def sample_news_item(self):
        """示例新闻项目"""
        return {
            'title': 'Bitcoin Reaches New High',
            'content': 'Bitcoin has reached $50000 today. SEC approval for ETF pending.',
            'source': 'CoinDesk',
            'url': 'https://example.com/news'
        }

    @pytest.mark.asyncio
    async def test_analyze_news_success(self, analyzer, sample_news_item):
        """测试新闻分析成功"""
        with patch.object(analyzer, 'generate_summary', return_value="Bitcoin涨至新高"):
            with patch.object(analyzer, 'analyze_sentiment', return_value=0.8):
                with patch.object(analyzer, 'extract_key_information', return_value={'tokens': ['BTC']}):
                    with patch.object(analyzer, 'calculate_market_impact', return_value=4):
                        result = await analyzer.analyze_news(sample_news_item)
        
        assert result['summary'] == "Bitcoin涨至新高"
        assert result['sentiment'] == 0.8
        assert result['key_info'] == {'tokens': ['BTC']}
        assert result['market_impact'] == 4

    @pytest.mark.asyncio
    async def test_analyze_news_with_exceptions(self, analyzer, sample_news_item):
        """测试分析过程中的异常处理"""
        with patch.object(analyzer, 'generate_summary', side_effect=Exception("API Error")):
            with patch.object(analyzer, 'analyze_sentiment', return_value=0.5):
                with patch.object(analyzer, 'extract_key_information', side_effect=Exception("Parse Error")):
                    with patch.object(analyzer, 'calculate_market_impact', return_value=3):
                        result = await analyzer.analyze_news(sample_news_item)
        
        assert result['summary'] == "摘要生成失败"
        assert result['sentiment'] == 0.5
        assert result['key_info'] == {}
        assert result['market_impact'] == 3

    @pytest.mark.asyncio
    async def test_generate_summary_success(self, analyzer):
        """测试摘要生成成功"""
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "测试摘要内容"
        
        with patch.object(analyzer.client.chat.completions, 'create', return_value=mock_response):
            result = await analyzer.generate_summary("Test content")
        
        assert result == "测试摘要内容"

    @pytest.mark.asyncio
    async def test_generate_summary_no_api_key(self):
        """测试没有API key的情况"""
        analyzer = AINewsAnalyzer()
        analyzer.client.api_key = None
        
        result = await analyzer.generate_summary("Test content")
        assert result == "未配置 OpenAI API Key"

    @pytest.mark.asyncio
    async def test_generate_summary_api_error(self, analyzer):
        """测试API调用错误"""
        with patch.object(analyzer.client.chat.completions, 'create', side_effect=Exception("API Error")), \
             patch('builtins.print') as mock_print:
            result = await analyzer.generate_summary("Test content")
        
        assert result == "摘要生成失败"
        mock_print.assert_called_with("Error generating summary: API Error")

    @pytest.mark.asyncio
    async def test_analyze_sentiment_success(self, analyzer):
        """测试情感分析成功"""
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "0.7"
        
        with patch.object(analyzer.client.chat.completions, 'create', return_value=mock_response):
            result = await analyzer.analyze_sentiment("Positive news content")
        
        assert result == 0.7

    @pytest.mark.asyncio
    async def test_analyze_sentiment_no_api_key(self, analyzer):
        """测试情感分析没有API key"""
        analyzer.client.api_key = None
        
        result = await analyzer.analyze_sentiment("Test content")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_analyze_sentiment_invalid_response(self, analyzer):
        """测试情感分析返回无效值"""
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "invalid"
        
        with patch.object(analyzer.client.chat.completions, 'create', return_value=mock_response), \
             patch('builtins.print') as mock_print:
            result = await analyzer.analyze_sentiment("Test content")
        
        assert result == 0.0
        assert mock_print.called

    def test_calculate_market_impact_high_keywords(self, analyzer):
        """测试高影响关键词评分"""
        news_item = {
            'title': 'SEC Regulation Announcement',
            'content': 'Federal Reserve announces new crypto regulation policy',
            'source': 'sec.gov'
        }
        
        import asyncio
        result = asyncio.run(analyzer.calculate_market_impact(news_item))
        
        # 高影响关键词 + 权威来源
        assert result >= 4

    def test_calculate_market_impact_medium_keywords(self, analyzer):
        """测试中等影响关键词评分"""
        news_item = {
            'title': 'New Partnership Announcement',
            'content': 'Company announces strategic partnership for crypto adoption',
            'source': 'CryptoNews'
        }
        
        import asyncio
        result = asyncio.run(analyzer.calculate_market_impact(news_item))
        
        assert result >= 2

    def test_calculate_market_impact_low_keywords(self, analyzer):
        """测试低影响关键词评分"""
        news_item = {
            'title': 'General Crypto Update',
            'content': 'General market update with no specific keywords',
            'source': 'Blog'
        }
        
        import asyncio
        result = asyncio.run(analyzer.calculate_market_impact(news_item))
        
        assert result == 1

    def test_extract_key_information_tokens(self, analyzer):
        """测试提取代币符号"""
        content = "BTC and ETH prices rising. XRP shows gains. CEO announces update."
        
        import asyncio
        result = asyncio.run(analyzer.extract_key_information(content))
        
        assert 'BTC' in result['tokens']
        assert 'ETH' in result['tokens']
        assert 'XRP' in result['tokens']
        assert 'CEO' not in result['tokens']  # 应被过滤

    def test_extract_key_information_prices(self, analyzer):
        """测试提取价格信息"""
        content = "Bitcoin is trading at $50,000.50 and Ethereum at 3000 USD"
        
        import asyncio
        result = asyncio.run(analyzer.extract_key_information(content))
        
        assert '$50,000.50' in result['prices']
        assert '3000 USD' in result['prices']

    def test_extract_key_information_exchanges(self, analyzer):
        """测试提取交易所名称"""
        content = "Binance and Coinbase announce new features. OKX supports the token."
        
        import asyncio
        result = asyncio.run(analyzer.extract_key_information(content))
        
        assert 'Binance' in result['exchanges']
        assert 'Coinbase' in result['exchanges']
        assert 'OKX' in result['exchanges']