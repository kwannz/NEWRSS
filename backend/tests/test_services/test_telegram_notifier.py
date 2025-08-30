import pytest
from unittest.mock import AsyncMock, patch
from app.services.telegram_notifier import TelegramNotifier

class TestTelegramNotifier:
    
    @pytest.fixture
    def notifier(self):
        """创建测试通知器实例"""
        with patch('app.services.telegram_notifier.TelegramBot') as mock_bot:
            return TelegramNotifier()
    
    @pytest.fixture
    def sample_news_item(self):
        """示例新闻项目"""
        return {
            'title': 'Bitcoin News',
            'content': 'Bitcoin reaches new high',
            'url': 'https://example.com/news',
            'source': 'CoinDesk',
            'importance_score': 4,
            'is_urgent': True
        }

    @pytest.mark.asyncio
    async def test_notify_urgent_news_with_users(self, notifier, sample_news_item):
        """测试推送紧急新闻给订阅用户"""
        with patch.object(notifier, 'get_subscribed_user_ids', return_value=['user1', 'user2']):
            with patch.object(notifier.bot, 'send_news_alert') as mock_send:
                await notifier.notify_urgent_news(sample_news_item)
        
        mock_send.assert_called_once_with(['user1', 'user2'], sample_news_item)

    @pytest.mark.asyncio
    async def test_notify_urgent_news_no_users(self, notifier, sample_news_item):
        """测试没有订阅用户时的推送"""
        with patch.object(notifier, 'get_subscribed_user_ids', return_value=[]):
            with patch.object(notifier.bot, 'send_news_alert') as mock_send:
                await notifier.notify_urgent_news(sample_news_item)
        
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_daily_digest(self, notifier):
        """测试发送每日摘要"""
        with patch('builtins.print') as mock_print:
            await notifier.send_daily_digest()
        
        mock_print.assert_called_with("Sending daily digest...")

    @pytest.mark.asyncio
    async def test_get_subscribed_user_ids_empty(self, notifier):
        """测试获取订阅用户ID（空列表）"""
        result = await notifier.get_subscribed_user_ids()
        assert result == []

    def test_format_daily_digest_single_item(self, notifier):
        """测试格式化单个新闻项目的每日摘要"""
        news_items = [{
            'title': 'Bitcoin News',
            'source': 'CoinDesk',
            'importance_score': 4,
            'url': 'https://example.com/news'
        }]
        
        result = notifier.format_daily_digest(news_items)
        
        assert "📊 <b>今日加密货币新闻摘要</b>" in result
        assert "Bitcoin News" in result
        assert "CoinDesk" in result
        assert "⭐ 4" in result
        assert "https://example.com/news" in result

    def test_format_daily_digest_multiple_items(self, notifier):
        """测试格式化多个新闻项目的每日摘要"""
        news_items = [
            {
                'title': 'Bitcoin News',
                'source': 'CoinDesk',
                'importance_score': 4,
                'url': 'https://example.com/btc'
            },
            {
                'title': 'Ethereum Update',
                'source': 'Decrypt',
                'importance_score': 3,
                'url': 'https://example.com/eth'
            }
        ]
        
        result = notifier.format_daily_digest(news_items)
        
        assert "1. <b>Bitcoin News</b>" in result
        assert "2. <b>Ethereum Update</b>" in result
        assert "CoinDesk" in result
        assert "Decrypt" in result

    def test_format_daily_digest_missing_importance_score(self, notifier):
        """测试没有重要性评分的新闻格式化"""
        news_items = [{
            'title': 'News Without Score',
            'source': 'TestSource',
            'url': 'https://example.com/test'
        }]
        
        result = notifier.format_daily_digest(news_items)
        
        assert "⭐ 1" in result  # 默认值为1

    def test_format_daily_digest_empty_list(self, notifier):
        """测试空新闻列表的格式化"""
        result = notifier.format_daily_digest([])
        
        assert result == "📊 <b>今日加密货币新闻摘要</b>\n\n"