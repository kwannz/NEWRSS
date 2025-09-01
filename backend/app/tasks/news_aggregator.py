import asyncio
from celery import current_app
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.news import NewsItem
from app.models.user import User
from app.services.telegram_bot import TelegramBot
from app.core.settings import settings
from sqlalchemy import select, and_
from app.core.logging import get_task_logger

async def _aggregate_daily_news_async():
    """异步聚合每日新闻摘要"""
    logger = get_task_logger("news_aggregator")
    async for db in get_db():
        try:
            yesterday = datetime.now() - timedelta(days=1)
            
            result = await db.execute(
                select(NewsItem).where(
                    and_(
                        NewsItem.published_at >= yesterday,
                        NewsItem.importance_score >= 3
                    )
                ).order_by(NewsItem.importance_score.desc())
            )
            important_news = result.scalars().all()
            
            if not important_news:
                logger.info("No important news found for daily digest")
                return
            
            if settings.TELEGRAM_BOT_TOKEN:
                telegram_bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
                
                users_result = await db.execute(
                    select(User).where(User.is_active == True)
                )
                active_users = users_result.scalars().all()
                
                user_telegram_ids = [
                    user.username for user in active_users 
                    if user.username.isdigit()
                ]
                
                if user_telegram_ids:
                    news_data = [
                        {
                            'title': news.title,
                            'source': news.source,
                            'url': news.url,
                            'importance_score': news.importance_score
                        }
                        for news in important_news[:10]
                    ]
                    
                    await telegram_bot.send_daily_digest(user_telegram_ids, news_data)
                    logger.info(
                        "Daily digest sent successfully",
                        recipient_count=len(user_telegram_ids),
                        news_items_count=len(news_data)
                    )
                
        except Exception as e:
            logger.error(
                "Daily news aggregation failed",
                error=str(e),
                exc_info=True
            )
        finally:
            break

@current_app.task
def aggregate_daily_news():
    """聚合每日新闻摘要"""
    logger = get_task_logger("news_aggregator")
    try:
        logger.info("Starting daily news aggregation")
        asyncio.run(_aggregate_daily_news_async())
        logger.info("Daily news aggregation completed successfully")
    except Exception as e:
        logger.error(
            "Daily news aggregation task failed",
            error=str(e),
            exc_info=True
        )