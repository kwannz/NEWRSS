import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.telegram_notifier import TelegramNotifier
from app.core.settings import settings


@pytest.fixture
def telegram_notifier():
    """Create TelegramNotifier instance with mocked dependencies"""
    with patch('app.services.telegram_notifier.TelegramBot'):
        notifier = TelegramNotifier()
        notifier.logger = Mock()
        return notifier


@pytest.fixture
def sample_news_items():
    """Sample news items for testing"""
    return [
        {
            'title': 'Bitcoin Reaches New All-Time High',
            'content': 'Bitcoin has surged to a new record price of $50,000 as institutional adoption continues.',
            'url': 'https://example.com/bitcoin-ath',
            'source': 'CryptoNews',
            'category': 'bitcoin',
            'importance_score': 5,
            'published_at': '2024-01-15 10:30',
            'is_urgent': True
        },
        {
            'title': 'Ethereum 2.0 Staking Milestone',
            'content': 'Ethereum 2.0 network has reached 10 million ETH staked.',
            'url': 'https://example.com/eth2-milestone',
            'source': 'EthereumNews',
            'category': 'ethereum',
            'importance_score': 4,
            'published_at': '2024-01-15 09:15',
            'is_urgent': False
        },
        {
            'title': 'New DeFi Protocol Launch',
            'content': 'A new decentralized finance protocol offers innovative yield farming opportunities.',
            'url': 'https://example.com/defi-launch',
            'source': 'DeFiDaily',
            'category': 'defi',
            'importance_score': 3,
            'published_at': '2024-01-15 08:45',
            'is_urgent': False
        }
    ]


class TestAIDigestGeneration:
    """Test AI-powered digest generation"""

    @pytest.mark.asyncio
    async def test_generate_ai_digest_with_openai_configured(self, telegram_notifier, sample_news_items):
        """Test AI digest generation when OpenAI is configured"""
        mock_ai_response = (
            "🔥 今日要闻:\n"
            "1. BTC创历史新高$50,000\n"
            "2. ETH2.0质押突破1000万\n"
            "3. 新DeFi协议上线\n\n"
            "📊 市场趋势: 机构采用推动价格上涨\n"
            "🎯 关键要点: 持续看涨\n"
            "💡 明日关注: 监管动态"
        )
        
        with patch.object(settings, 'OPENAI_API_KEY', 'fake-key'), \
             patch.object(telegram_notifier, '_call_openai_for_digest', return_value=mock_ai_response), \
             patch.object(telegram_notifier, '_prepare_news_for_ai', return_value="news summary"):
            
            result = await telegram_notifier.generate_ai_digest(sample_news_items, "TestUser")
            
            # Verify AI-generated content is included
            assert "🤖" in result
            assert "AI智能摘要" in result
            assert "早上好, TestUser" in result
            assert "基于 3 条新闻生成" in result

    @pytest.mark.asyncio
    async def test_generate_ai_digest_without_openai(self, telegram_notifier, sample_news_items):
        """Test fallback to standard digest when OpenAI is not configured"""
        with patch.object(settings, 'OPENAI_API_KEY', None):
            result = await telegram_notifier.generate_ai_digest(sample_news_items, "TestUser")
            
            # Should fall back to standard format
            assert "📊" in result
            assert "加密货币新闻摘要" in result
            assert "🤖" not in result  # No AI indicator

    @pytest.mark.asyncio
    async def test_generate_ai_digest_api_error(self, telegram_notifier, sample_news_items):
        """Test fallback when OpenAI API call fails"""
        with patch.object(settings, 'OPENAI_API_KEY', 'fake-key'), \
             patch.object(telegram_notifier, '_call_openai_for_digest', side_effect=Exception("API Error")):
            
            result = await telegram_notifier.generate_ai_digest(sample_news_items, "TestUser")
            
            # Should fall back to standard format
            assert "📊" in result
            assert "加密货币新闻摘要" in result
            telegram_notifier.logger.error.assert_called()

    def test_prepare_news_for_ai(self, telegram_notifier, sample_news_items):
        """Test news preparation for AI analysis"""
        result = telegram_notifier._prepare_news_for_ai(sample_news_items)
        
        assert "Today's cryptocurrency news:" in result
        assert "Bitcoin Reaches New All-Time High" in result
        assert "Importance: 5/5" in result
        assert "Category: bitcoin" in result
        assert "Source: CryptoNews" in result

    def test_prepare_news_for_ai_limits_items(self, telegram_notifier):
        """Test that news preparation limits to top 10 items"""
        # Create 15 news items with different importance scores
        many_news_items = []
        for i in range(15):
            many_news_items.append({
                'title': f'News Item {i}',
                'content': f'Content for news {i}',
                'category': 'general',
                'importance_score': i % 5 + 1,  # Scores 1-5
                'source': f'Source{i}'
            })
        
        result = telegram_notifier._prepare_news_for_ai(many_news_items)
        
        # Should only include top 10 items
        lines = result.split('\n')
        news_count = len([line for line in lines if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.'))])
        assert news_count == 10

    @pytest.mark.asyncio
    async def test_call_openai_for_digest_success(self, telegram_notifier):
        """Test successful OpenAI API call"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "AI generated content"
        
        with patch('openai.AsyncOpenAI') as mock_openai, \
             patch.object(settings, 'OPENAI_API_KEY', 'fake-key'):
            
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await telegram_notifier._call_openai_for_digest("test news summary")
            
            assert result == "AI generated content"
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_openai_for_digest_api_error(self, telegram_notifier):
        """Test OpenAI API call with error"""
        with patch('openai.AsyncOpenAI') as mock_openai, \
             patch.object(settings, 'OPENAI_API_KEY', 'fake-key'):
            
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            
            result = await telegram_notifier._call_openai_for_digest("test news summary")
            
            assert result is None
            telegram_notifier.logger.error.assert_called()

    def test_format_ai_digest(self, telegram_notifier, sample_news_items):
        """Test AI digest formatting"""
        ai_summary = "🔥 重要新闻: BTC新高\n📊 市场分析: 上涨趋势\n🎯 投资要点: 长期看涨"
        
        result = telegram_notifier._format_ai_digest(ai_summary, sample_news_items, "TestUser")
        
        assert "🌅 早上好, TestUser！" in result
        assert "🤖 <b>AI智能摘要</b>" in result
        assert "🔥 重要新闻: BTC新高" in result
        assert "📊 基于 3 条新闻生成" in result
        assert "🔧 使用 /settings 调整推送设置" in result

    def test_clean_ai_response(self, telegram_notifier):
        """Test AI response cleaning"""
        # Test with normal content
        clean_input = "🔥 正常内容 📊 市场分析"
        result = telegram_notifier._clean_ai_response(clean_input)
        assert result == clean_input
        
        # Test with long content
        long_input = "a" * 1500
        result = telegram_notifier._clean_ai_response(long_input)
        assert len(result) <= 1203  # 1200 + "..."
        assert result.endswith("...")

    def test_clean_ai_response_error_handling(self, telegram_notifier):
        """Test AI response cleaning error handling"""
        with patch('re.sub', side_effect=Exception("Regex error")):
            result = telegram_notifier._clean_ai_response("test content")
            assert len(result) <= 1000  # Fallback limit
            telegram_notifier.logger.error.assert_called()


class TestEnhancedDigestWorkflow:
    """Test the complete enhanced digest workflow"""

    @pytest.mark.asyncio
    async def test_send_daily_digest_with_ai(self, telegram_notifier, sample_news_items):
        """Test send_daily_digest with AI enhancement"""
        mock_digest_users = [
            {
                'telegram_id': '12345',
                'telegram_username': 'test_user',
                'min_importance_score': 2
            }
        ]
        
        with patch.object(telegram_notifier, 'get_digest_subscribers', return_value=mock_digest_users), \
             patch.object(telegram_notifier, 'get_daily_news', return_value=sample_news_items), \
             patch.object(telegram_notifier, 'generate_ai_digest', return_value="AI digest content"), \
             patch.object(telegram_notifier.bot.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            await telegram_notifier.send_daily_digest("09:00")
            
            # Verify AI digest was generated and sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[1]['text'] == "AI digest content"
            assert call_args[1]['parse_mode'] == 'HTML'

    @pytest.mark.asyncio
    async def test_filter_news_for_user_enhanced(self, telegram_notifier, sample_news_items):
        """Test enhanced news filtering for users"""
        # Test with minimum importance 3
        filtered = telegram_notifier.filter_news_for_user(sample_news_items, 3)
        
        # Should include items with importance >= 3
        assert len(filtered) == 3
        assert all(item['importance_score'] >= 3 for item in filtered)
        
        # Should be sorted by importance (descending)
        scores = [item['importance_score'] for item in filtered]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_filter_news_for_user_limits_results(self, telegram_notifier):
        """Test that news filtering limits results to 15 items"""
        # Create 20 high-importance news items
        many_news_items = []
        for i in range(20):
            many_news_items.append({
                'title': f'News {i}',
                'importance_score': 5,
                'category': 'general'
            })
        
        filtered = telegram_notifier.filter_news_for_user(many_news_items, 1)
        
        # Should be limited to 15 items
        assert len(filtered) == 15


class TestDigestErrorHandling:
    """Test error handling in digest generation"""

    @pytest.mark.asyncio
    async def test_generate_ai_digest_empty_news_list(self, telegram_notifier):
        """Test AI digest generation with empty news list"""
        result = await telegram_notifier.generate_ai_digest([], "TestUser")
        
        # Should handle gracefully and return standard format
        assert isinstance(result, str)
        assert len(result) > 0

    def test_prepare_news_for_ai_error_handling(self, telegram_notifier):
        """Test error handling in news preparation"""
        # Test with malformed news item
        bad_news_items = [{'title': None, 'content': None}]
        
        result = telegram_notifier._prepare_news_for_ai(bad_news_items)
        
        # Should handle gracefully
        assert isinstance(result, str)
        telegram_notifier.logger.error.assert_called()

    def test_format_ai_digest_error_handling(self, telegram_notifier, sample_news_items):
        """Test error handling in AI digest formatting"""
        with patch('datetime.now', side_effect=Exception("Time error")):
            result = telegram_notifier._format_ai_digest("test content", sample_news_items)
            
            # Should fall back to standard format
            assert "📊" in result
            assert "加密货币新闻摘要" in result
            telegram_notifier.logger.error.assert_called()


class TestDigestPerformance:
    """Test performance aspects of digest generation"""

    def test_news_preparation_performance(self, telegram_notifier):
        """Test performance of news preparation with large dataset"""
        # Create large dataset
        large_news_items = []
        for i in range(100):
            large_news_items.append({
                'title': f'News Item {i}' * 10,  # Long title
                'content': f'Content for news {i}' * 50,  # Long content
                'category': 'general',
                'importance_score': (i % 5) + 1,
                'source': f'Source{i}'
            })
        
        # Test that preparation completes reasonably quickly
        import time
        start_time = time.time()
        result = telegram_notifier._prepare_news_for_ai(large_news_items)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert (end_time - start_time) < 1.0  # 1 second limit
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_digest_generation_timeout_handling(self, telegram_notifier, sample_news_items):
        """Test handling of API timeouts"""
        import asyncio
        
        async def slow_api_call(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow API
            return "slow response"
        
        with patch.object(settings, 'OPENAI_API_KEY', 'fake-key'), \
             patch.object(telegram_notifier, '_call_openai_for_digest', side_effect=slow_api_call):
            
            # Should handle timeout gracefully and fall back
            result = await telegram_notifier.generate_ai_digest(sample_news_items)
            
            # Should fall back to standard format without hanging
            assert isinstance(result, str)
            assert len(result) > 0


class TestIntegrationWithExistingSystems:
    """Test integration with existing notification systems"""

    @pytest.mark.asyncio
    async def test_ai_digest_with_user_preferences(self, telegram_notifier, sample_news_items):
        """Test AI digest generation respects user preferences"""
        # Test with high importance threshold
        filtered_news = telegram_notifier.filter_news_for_user(sample_news_items, 4)
        
        with patch.object(settings, 'OPENAI_API_KEY', 'fake-key'), \
             patch.object(telegram_notifier, '_call_openai_for_digest', return_value="AI content"):
            
            result = await telegram_notifier.generate_ai_digest(filtered_news, "TestUser")
            
            # Should include user preferences in processing
            assert "TestUser" in result
            assert "AI智能摘要" in result

    @pytest.mark.asyncio
    async def test_digest_maintains_existing_functionality(self, telegram_notifier, sample_news_items):
        """Test that enhanced digest maintains backward compatibility"""
        # Test standard digest format is still available
        standard_result = telegram_notifier.format_daily_digest(sample_news_items, "TestUser")
        
        assert "📊" in standard_result
        assert "加密货币新闻摘要" in standard_result
        assert "TestUser" in standard_result
        
        # Verify all news categories are handled
        for item in sample_news_items:
            assert item['title'][:20] in standard_result or item['title'][:60] in standard_result