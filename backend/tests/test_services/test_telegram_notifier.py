import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from app.services.telegram_notifier import TelegramNotifier
from app.models.news import NewsItem

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
        with patch.object(notifier, 'get_users_for_notification', return_value=['user1', 'user2']):
            with patch.object(notifier.bot, 'send_news_alert') as mock_send:
                await notifier.notify_urgent_news(sample_news_item)
        
        mock_send.assert_called_once_with(['user1', 'user2'], sample_news_item)

    @pytest.mark.asyncio
    async def test_notify_urgent_news_no_users(self, notifier, sample_news_item):
        """测试没有订阅用户时的推送"""
        with patch.object(notifier, 'get_users_for_notification', return_value=[]):
            with patch.object(notifier.bot, 'send_news_alert') as mock_send:
                await notifier.notify_urgent_news(sample_news_item)
        
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_daily_digest_success(self, notifier):
        """测试发送每日摘要 - 成功"""
        digest_users = [
            {
                'telegram_id': '12345',
                'telegram_username': 'user1',
                'min_importance_score': 2,
                'digest_time': '09:00'
            }
        ]
        
        news_items = [
            {
                'title': 'Bitcoin News',
                'content': 'Content',
                'url': 'https://example.com',
                'source': 'CoinDesk',
                'category': 'bitcoin',
                'importance_score': 3,
                'published_at': '2025-01-01 10:00',
                'is_urgent': False
            }
        ]
        
        with patch.object(notifier, 'get_digest_subscribers', return_value=digest_users), \
             patch.object(notifier, 'get_daily_news', return_value=news_items), \
             patch.object(notifier, 'filter_news_for_user', return_value=news_items), \
             patch.object(notifier.bot.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            await notifier.send_daily_digest()
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[1]['chat_id'] == '12345'
            assert call_args[1]['parse_mode'] == 'HTML'
            assert 'Bitcoin News' in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_send_daily_digest_no_subscribers(self, notifier):
        """测试发送每日摘要 - 无订阅者"""
        with patch.object(notifier, 'get_digest_subscribers', return_value=[]):
            # Should not raise exception
            await notifier.send_daily_digest()
    
    @pytest.mark.asyncio
    async def test_send_daily_digest_no_news(self, notifier):
        """测试发送每日摘要 - 无新闻"""
        digest_users = [{'telegram_id': '12345', 'min_importance_score': 2}]
        
        with patch.object(notifier, 'get_digest_subscribers', return_value=digest_users), \
             patch.object(notifier, 'get_daily_news', return_value=[]):
            
            # Should not raise exception
            await notifier.send_daily_digest()

    @pytest.mark.asyncio
    @patch('app.services.telegram_notifier.SessionLocal')
    async def test_get_subscribed_user_ids_empty(self, mock_session, notifier):
        """测试获取订阅用户ID（空列表）"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        with patch('app.services.telegram_notifier.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_subscribed_user_ids.return_value = []
            mock_repo_class.return_value = mock_repo
            
            result = await notifier.get_subscribed_user_ids()
            assert result == []
    
    @pytest.mark.asyncio
    @patch('app.services.telegram_notifier.SessionLocal')
    async def test_get_subscribed_user_ids_with_users(self, mock_session, notifier):
        """测试获取订阅用户ID（有用户）"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        with patch('app.services.telegram_notifier.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_subscribed_user_ids.return_value = ['user1', 'user2']
            mock_repo_class.return_value = mock_repo
            
            result = await notifier.get_subscribed_user_ids()
            assert result == ['user1', 'user2']
            mock_repo.get_subscribed_user_ids.assert_called_once_with(False)  # urgent_only=False

    def test_format_daily_digest_single_item(self, notifier):
        """测试格式化单个新闻项目的每日摘要"""
        news_items = [{
            'title': 'Bitcoin News',
            'source': 'CoinDesk',
            'importance_score': 4,
            'url': 'https://example.com/news',
            'category': 'bitcoin'
        }]
        
        result = notifier.format_daily_digest(news_items)
        
        assert "📊 <b>今日加密货币新闻摘要</b>" in result
        assert "Bitcoin News" in result
        assert "CoinDesk" in result
        assert "⭐⭐⭐⭐" in result  # 4 stars
        assert "https://example.com/news" in result
        assert "比特币" in result  # Category in Chinese

    def test_format_daily_digest_multiple_items(self, notifier):
        """测试格式化多个新闻项目的每日摘要"""
        news_items = [
            {
                'title': 'Bitcoin News',
                'source': 'CoinDesk',
                'importance_score': 4,
                'url': 'https://example.com/btc',
                'category': 'bitcoin'
            },
            {
                'title': 'Ethereum Update',
                'source': 'Decrypt',
                'importance_score': 3,
                'url': 'https://example.com/eth',
                'category': 'ethereum'
            }
        ]
        
        result = notifier.format_daily_digest(news_items)
        
        # Should be grouped by category
        assert "Bitcoin News" in result
        assert "Ethereum Update" in result
        assert "CoinDesk" in result
        assert "Decrypt" in result
        assert "比特币" in result  # Bitcoin category
        assert "以太坊" in result  # Ethereum category

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
        
        assert "📊 <b>今日加密货币新闻摘要</b>" in result
        assert "😴 今天暂无重要新闻更新" in result
    
    def test_format_daily_digest_with_username(self, notifier):
        """测试带用户名的每日摘要格式化"""
        news_items = [{
            'title': 'Test News',
            'source': 'TestSource',
            'importance_score': 2,
            'url': 'https://example.com',
            'category': 'general'
        }]
        
        result = notifier.format_daily_digest(news_items, "TestUser")
        
        assert "🌅 早上好, TestUser！" in result
    
    def test_filter_news_for_user(self, notifier):
        """测试为用户过滤新闻"""
        news_items = [
            {'title': 'Low importance', 'importance_score': 1},
            {'title': 'Medium importance', 'importance_score': 3},
            {'title': 'High importance', 'importance_score': 5}
        ]
        
        # Filter with min importance 3
        filtered = notifier.filter_news_for_user(news_items, 3)
        
        assert len(filtered) == 2
        assert filtered[0]['title'] == 'High importance'  # Sorted by importance desc
        assert filtered[1]['title'] == 'Medium importance'
    
    @pytest.mark.asyncio
    @patch('app.services.telegram_notifier.SessionLocal')
    async def test_get_daily_news(self, mock_session, notifier):
        """测试获取每日新闻"""
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock news item
        mock_news_item = MagicMock()
        mock_news_item.title = 'Test News'
        mock_news_item.content = 'Test content'
        mock_news_item.url = 'https://example.com'
        mock_news_item.category = 'bitcoin'
        mock_news_item.importance_score = 3
        mock_news_item.is_urgent = False
        mock_news_item.published_at = datetime.now()
        mock_news_item.source = MagicMock()
        mock_news_item.source.name = 'TestSource'
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_news_item]
        mock_db.execute.return_value = mock_result
        
        news_items = await notifier.get_daily_news(date.today())
        
        assert len(news_items) == 1
        assert news_items[0]['title'] == 'Test News'
        assert news_items[0]['source'] == 'TestSource'
        assert news_items[0]['importance_score'] == 3
    
    @pytest.mark.asyncio
    async def test_send_regular_news_notification_high_importance(self, notifier):
        """测试发送常规新闻通知 - 高重要度"""
        news_item = {
            'title': 'Important News',
            'importance_score': 4,  # High enough for regular notifications
            'category': 'bitcoin'
        }
        
        with patch.object(notifier, 'get_users_for_notification', return_value=['user1']) as mock_get_users, \
             patch.object(notifier.bot, 'send_news_alert') as mock_send:
            
            await notifier.send_regular_news_notification(news_item)
            
            mock_get_users.assert_called_once_with(
                importance_score=4,
                category='bitcoin',
                urgent_only=False
            )
            mock_send.assert_called_once_with(['user1'], news_item)
    
    @pytest.mark.asyncio
    async def test_send_regular_news_notification_low_importance(self, notifier):
        """测试发送常规新闻通知 - 低重要度"""
        news_item = {
            'title': 'Low Importance News',
            'importance_score': 2,  # Too low for regular notifications
            'category': 'general'
        }
        
        with patch.object(notifier.bot, 'send_news_alert') as mock_send:
            await notifier.send_regular_news_notification(news_item)
            
            # Should not send notification
            mock_send.assert_not_called()