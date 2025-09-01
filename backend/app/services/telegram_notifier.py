from typing import List
from app.services.telegram_bot import TelegramBot
from app.models.user import User
from app.models.news import NewsItem
from app.core.settings import settings
from app.core.logging import get_service_logger

class TelegramNotifier:
    def __init__(self):
        self.bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
        self.logger = get_service_logger("telegram_notifier")
    
    async def notify_urgent_news(self, news_item_dict: dict):
        """推送紧急新闻"""
        # Get subscribed users from database
        user_ids = await self.get_subscribed_user_ids()
        
        if user_ids:
            self.logger.info(
                "Sending urgent news notification",
                news_title=news_item_dict.get('title'),
                subscriber_count=len(user_ids),
                urgency_level="urgent"
            )
            await self.bot.send_news_alert(user_ids, news_item_dict)
        else:
            self.logger.warning(
                "No subscribed users found for urgent news notification",
                news_title=news_item_dict.get('title')
            )
    
    async def send_daily_digest(self):
        """发送每日新闻摘要"""
        # Implement daily digest functionality
        self.logger.info(
            "Preparing daily digest",
            action="daily_digest_start"
        )
        # NOTE: Daily digest implementation pending - will be added
        # when news aggregation and digest generation features are implemented
    
    async def get_subscribed_user_ids(self) -> List[str]:
        """获取订阅用户的 Telegram ID"""
        # Query subscribed users from database
        self.logger.debug("Fetching subscribed user IDs from database")
        # NOTE: Database user subscription query pending - will return actual
        # user IDs when user management system is implemented
        return []
    
    def format_daily_digest(self, news_items: List[dict]) -> str:
        """格式化每日摘要"""
        message = "📊 <b>今日加密货币新闻摘要</b>\n\n"
        
        for i, item in enumerate(news_items, 1):
            message += f"{i}. <b>{item['title']}</b>\n"
            message += f"   📡 {item['source']} | ⭐ {item.get('importance_score', 1)}\n"
            message += f"   🔗 <a href='{item['url']}'>阅读</a>\n\n"
        
        return message