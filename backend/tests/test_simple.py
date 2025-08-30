import pytest
from app.tasks.news_crawler import is_urgent_news, calculate_importance
from app.core.auth import get_password_hash, verify_password

class TestSimpleCore:
    """简化的核心功能测试，确保基本功能正常工作"""
    
    def test_password_functions(self):
        """测试密码哈希和验证功能"""
        password = "test123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
    
    def test_urgent_news_detection(self):
        """测试紧急新闻检测"""
        urgent_item = {
            'title': 'BREAKING: Bitcoin crashes',
            'content': 'Urgent market news'
        }
        normal_item = {
            'title': 'Daily market update',
            'content': 'Regular trading news'
        }
        
        assert is_urgent_news(urgent_item) is True
        assert is_urgent_news(normal_item) is False
    
    def test_importance_calculation(self):
        """测试重要性计算"""
        high_item = {
            'title': 'SEC regulation announcement',
            'content': 'ETF approval news',
            'source': 'sec'
        }
        low_item = {
            'title': 'Regular update',
            'content': 'Normal content',
            'source': 'blog'
        }
        
        high_score = calculate_importance(high_item)
        low_score = calculate_importance(low_item)
        
        assert high_score > low_score
        assert 1 <= high_score <= 5
        assert 1 <= low_score <= 5