from typing import List
from app.services.telegram_bot import TelegramBot
from app.models.user import User
from app.models.news import NewsItem
from app.core.settings import settings

class TelegramNotifier:
    def __init__(self):
        self.bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
    
    async def notify_urgent_news(self, news_item_dict: dict):
        """推送紧急新闻"""
        # TODO: 从数据库获取订阅用户
        user_ids = await self.get_subscribed_user_ids()
        
        if user_ids:
            await self.bot.send_news_alert(user_ids, news_item_dict)
    
    async def send_daily_digest(self):
        """发送每日新闻摘要"""
        # TODO: 实现每日摘要功能
        print("Sending daily digest...")
    
    async def get_subscribed_user_ids(self) -> List[str]:
        """获取订阅用户的 Telegram ID"""
        # TODO: 从数据库查询订阅用户
        return []
    
    def format_daily_digest(self, news_items: List[dict]) -> str:
        """格式化每日摘要"""
        message = "📊 <b>今日加密货币新闻摘要</b>\n\n"
        
        for i, item in enumerate(news_items, 1):
            message += f"{i}. <b>{item['title']}</b>\n"
            message += f"   📡 {item['source']} | ⭐ {item.get('importance_score', 1)}\n"
            message += f"   🔗 <a href='{item['url']}'>阅读</a>\n\n"
        
        return message