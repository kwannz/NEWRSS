from celery import Celery
from datetime import datetime
import asyncio
from app.core.settings import settings
from app.core.logging import get_service_logger
from app.services.telegram_notifier import TelegramNotifier

# Create Celery instance
celery_app = Celery(
    'daily_digest',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.daily_digest']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Configure periodic tasks - Enhanced scheduling for multiple time zones
celery_app.conf.beat_schedule = {
    'send-daily-digest-08-00': {
        'task': 'app.tasks.daily_digest.send_daily_digest_task', 
        'schedule': {'hour': 8, 'minute': 0},  # Run at 08:00 UTC
        'args': ('08:00',)
    },
    'send-daily-digest-09-00': {
        'task': 'app.tasks.daily_digest.send_daily_digest_task',
        'schedule': {'hour': 9, 'minute': 0},  # Run at 09:00 UTC
        'args': ('09:00',)
    },
    'send-daily-digest-10-00': {
        'task': 'app.tasks.daily_digest.send_daily_digest_task',
        'schedule': {'hour': 10, 'minute': 0},  # Run at 10:00 UTC
        'args': ('10:00',)
    },
    'send-daily-digest-18-00': {
        'task': 'app.tasks.daily_digest.send_daily_digest_task',
        'schedule': {'hour': 18, 'minute': 0},  # Run at 18:00 UTC
        'args': ('18:00',)
    },
    'send-daily-digest-20-00': {
        'task': 'app.tasks.daily_digest.send_daily_digest_task',
        'schedule': {'hour': 20, 'minute': 0},  # Run at 20:00 UTC
        'args': ('20:00',)
    },
}

logger = get_service_logger("daily_digest_task")


@celery_app.task(bind=True, max_retries=3)
def send_daily_digest_task(self, target_time: str = None):
    """
    Celery task to send daily digest to subscribers
    
    Args:
        target_time: Target time for digest (e.g., "09:00")
    """
    try:
        logger.info(
            "Starting daily digest task",
            target_time=target_time,
            task_id=self.request.id
        )
        
        # Run async function in event loop
        asyncio.run(send_daily_digest_async(target_time))
        
        logger.info(
            "Daily digest task completed successfully",
            target_time=target_time,
            task_id=self.request.id
        )
        
        return {
            "status": "success",
            "target_time": target_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Daily digest task failed",
            target_time=target_time,
            task_id=self.request.id,
            error=str(e),
            exc_info=True
        )
        
        # Retry the task
        raise self.retry(
            exc=e,
            countdown=300,  # Retry after 5 minutes
            max_retries=3
        )


async def send_daily_digest_async(target_time: str = None):
    """
    Async function to send daily digest
    
    Args:
        target_time: Target time for digest (e.g., "09:00")
    """
    try:
        logger.info(
            "Initializing Telegram notifier for daily digest",
            target_time=target_time
        )
        
        notifier = TelegramNotifier()
        await notifier.send_daily_digest(target_time)
        
        logger.info(
            "Daily digest sent successfully",
            target_time=target_time
        )
        
    except Exception as e:
        logger.error(
            "Error in daily digest async function",
            target_time=target_time,
            error=str(e),
            exc_info=True
        )
        raise


@celery_app.task(bind=True)
def test_digest_task(self, user_telegram_id: str):
    """
    Test task to send digest to a specific user
    
    Args:
        user_telegram_id: Telegram ID of the user to send test digest
    """
    try:
        logger.info(
            "Starting test digest task",
            user_telegram_id=user_telegram_id,
            task_id=self.request.id
        )
        
        # Run test digest
        asyncio.run(send_test_digest_async(user_telegram_id))
        
        logger.info(
            "Test digest task completed",
            user_telegram_id=user_telegram_id,
            task_id=self.request.id
        )
        
        return {
            "status": "success",
            "user_telegram_id": user_telegram_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Test digest task failed",
            user_telegram_id=user_telegram_id,
            task_id=self.request.id,
            error=str(e),
            exc_info=True
        )
        raise


async def send_test_digest_async(user_telegram_id: str):
    """
    Send test digest to specific user
    
    Args:
        user_telegram_id: Telegram ID of the user
    """
    try:
        from datetime import date, timedelta
        
        notifier = TelegramNotifier()
        
        # Get yesterday's news for test
        yesterday = date.today() - timedelta(days=1)
        news_items = await notifier.get_daily_news(yesterday)
        
        if not news_items:
            # Create a test news item if no news available
            news_items = [{
                'title': 'Test Daily Digest',
                'content': 'This is a test digest to verify the system is working correctly.',
                'url': 'https://example.com/test',
                'source': 'NEWRSS System',
                'category': 'general',
                'importance_score': 3,
                'published_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'is_urgent': False
            }]
        
        # Filter news (assume min importance 1 for test)
        filtered_news = notifier.filter_news_for_user(news_items, 1)
        
        # Format and send digest
        digest_message = notifier.format_daily_digest(filtered_news, "Test User")
        
        await notifier.bot.bot.send_message(
            chat_id=user_telegram_id,
            text=digest_message,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        logger.info(
            "Test digest sent successfully",
            user_telegram_id=user_telegram_id,
            news_count=len(filtered_news)
        )
        
    except Exception as e:
        logger.error(
            "Error sending test digest",
            user_telegram_id=user_telegram_id,
            error=str(e),
            exc_info=True
        )
        raise


# Health check task
@celery_app.task
def health_check():
    """Health check task for monitoring"""
    logger.info("Daily digest health check")
    return {
        "status": "healthy",
        "service": "daily_digest",
        "timestamp": datetime.utcnow().isoformat()
    }